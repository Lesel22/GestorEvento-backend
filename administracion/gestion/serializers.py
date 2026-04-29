from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import Evento, Participacion, Usuario
from .utils import generar_url_firmada, generar_url_cloudinary
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from datetime import datetime
from django.utils.timezone import now, localtime
from datetime import datetime, timedelta
from django.conf import settings

class UsuarioSerializer(ModelSerializer):
    class Meta:
        model = Usuario
        exclude = ['groups', 'user_permissions', 'is_active', 'is_superuser', 'last_login']
        extra_kwargs = {
            'password': {'write_only': True}
        }

class EventoSerializer(serializers.ModelSerializer):
    hora_inicio = serializers.TimeField(format="%H:%M")
    hora_fin = serializers.TimeField(format="%H:%M")
    eliminado = serializers.BooleanField(source='eventoId.eliminado', read_only=True)
    participantes_count = serializers.IntegerField(
        source='inscripciones.count',
        read_only=True
    )
    estado_usuario = serializers.SerializerMethodField()
    estado_evento = serializers.ReadOnlyField()

    def get_estado_usuario(self, obj):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return None
        
        user = request.user

        if obj.propietario_id == user.id:
            return {
                "tipo": "0",
                "id": None
            }

        if hasattr(obj, "user_participacion") and obj.user_participacion:
            p = obj.user_participacion[0]

            return {
                "tipo": p.tipoUsuario,
                "id": p.id
            }

        return None

    class Meta:
        model = Evento
        fields = '__all__'
        read_only_fields = [
            'created_at',
            'updated_at',
            'eliminado',
            'propietario'
        ]

        # 🔹 VALIDACIÓN DE CAMPOS INDIVIDUALES

    def validate_nombre(self, value):
        if len(value.strip()) < 3 or len(value.strip()) > 100:
            raise serializers.ValidationError("Nombre muy corto")
        return value

    def validate_limite_participantes(self, value):
        if value is not None and value == 0 and value > 1000:
            raise serializers.ValidationError("Debe ser mayor a 0 y menor a 1000")
        return value

    def validate_fecha(self, value):
        print("value:", value)
        print("now:", now())
        print("now.date:", now().date())
        if value <  localtime(now()).date():
            print(localtime(now()).date())
            print(now())
            print(now().date())
            print(settings.TIME_ZONE)
            raise serializers.ValidationError("No puedes crear eventos en el pasado")
        return value

    def validate_estado(self, value):
        # 🔒 NO permitir crear con estados manuales
        if self.instance is None:
            if value != "activo":
                raise serializers.ValidationError(
                    "Un evento nuevo siempre inicia como activo"
                )

        # 🔒 Nunca permitir asignar "finalizado" manualmente
        if value == "finalizado":
            raise serializers.ValidationError(
                "Estado no asignable manualmente"
            )

        return value

    def validate_descripcion(self, value):
        if value and len(value.strip()) < 30:
            raise serializers.ValidationError("Descripción muy corta")
        return value
    
    def validate_referencia(self, value):
        if value == "":
            return None
        return value

    # 🔹 VALIDACIÓN GLOBAL (relaciones entre campos)

    def validate(self, data):
        hi = data.get("hora_inicio")
        hf = data.get("hora_fin")
        fecha = data.get("fecha")
        lat = data.get("latitud")
        lon = data.get("longitud")
        img = data.get("imagen")
        pub = data.get("imagen_public_id")

        # 🕒 Validar horas
        if hi and hf and hi >= hf:
            raise serializers.ValidationError("Hora inicio debe ser menor a hora fin")

        # 🕒 Validar creación mínima anticipada
        if fecha and hi:
            fecha_hora_inicio = datetime.combine(fecha, hi)

            ahora = localtime(now())
            minimo_permitido = ahora + timedelta(minutes=60)

            # convertir a timezone aware
            fecha_hora_inicio = fecha_hora_inicio.replace(
                tzinfo=ahora.tzinfo
            )

            if fecha_hora_inicio < minimo_permitido:
                raise serializers.ValidationError(
                    "El evento debe crearse al menos 1 hora antes de iniciar"
                )
        

        # 🌍 Validar coordenadas
        if (lat is None) != (lon is None):
            raise serializers.ValidationError("Latitud y longitud deben ir juntas")

        if lat is not None:
            if not (-90 <= lat <= 90):
                raise serializers.ValidationError("Latitud inválida")
            if not (-180 <= lon <= 180):
                raise serializers.ValidationError("Longitud inválida")

        # 🖼 Validar imagen
        if img and not pub:
            raise serializers.ValidationError("Falta imagen_public_id")

        return data
    
    # 🔹 FORZAR PROPIETARIO (seguridad)

    def create(self, validated_data):
        validated_data["propietario"] = self.context["request"].user
        validated_data["estado"] = "activo"
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Evitar que cambien el propietario manualmente
        validated_data.pop("propietario", None)

        nuevo_estado = validated_data.get("estado")
        if nuevo_estado and nuevo_estado not in ["cancelado", "activo"]:
            raise serializers.ValidationError("Estado no permitido")
        
        return super().update(instance, validated_data)
  
class ParticipacionSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source='eventoId.nombre', read_only=True)
    fecha = serializers.CharField(source='eventoId.fecha', read_only=True)
    eliminado = serializers.BooleanField(source='eventoId.eliminado', read_only=True)
    estado_evento = serializers.CharField(source='eventoId.estado_evento', read_only=True)
    tipoUsuario_display = serializers.CharField(
        source='get_tipoUsuario_display',
        read_only=True
    )

    class Meta:
        model = Participacion
        fields = ['id','usuarioId', 'eventoId', 'tipoUsuario', 'tipoUsuario_display', 'nombre', 'fecha', 'estado_evento', 'eliminado']
         # fields = ['nombre', 'fecha', 'eliminado', 'participantes_count', 'estado_usuario']

    #Evita duplicidad y sobrepasar limite participantes
    def validate(self, data):
        evento = data.get("eventoId")
        usuario = self.context["request"].user

        if not evento:
            raise serializers.ValidationError(
                "Evento requerido"
            )

        # 🚫 No permitir eventos finalizados
        if evento.estado == "finalizado":
            raise serializers.ValidationError(
                "No puedes inscribirte a un evento finalizado"
            )

        # 🚫 No permitir eventos cancelados
        if evento.estado == "cancelado":
            raise serializers.ValidationError(
                "No puedes inscribirte a un evento cancelado"
            )

         # 🚫 Evitar doble inscripción
        if Participacion.objects.filter(
            eventoId=evento,
            usuarioId=usuario
        ).exists():
            raise serializers.ValidationError(
                "Ya estás inscrito en este evento"
            )

        # 🚫 Validar límite
        limite = evento.limite_participantes

        if limite is not None:
            participantes_actuales = Participacion.objects.filter(
                eventoId=evento
            ).count()

            if participantes_actuales >= limite:
                raise serializers.ValidationError(
                    "El evento alcanzó su límite de participantes"
                )

        return data

class UsuarioMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'nombre', 'correo']

class EventoMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evento
        fields = ['id', 'nombre', 'fecha']

class ParticipacionSerializer2(serializers.ModelSerializer):
    usuario = UsuarioMiniSerializer(source='usuarioId')
    evento = EventoMiniSerializer(source='eventoId')

    class Meta:
        model = Participacion
        fields = ['id', 'usuario', 'evento', 'tipoUsuario']

class ParticipacionUsuarioSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source='usuarioId.nombre', read_only=True)
    correo = serializers.CharField(source='usuarioId.correo', read_only=True)
    tipoUsuario_display = serializers.CharField(
        source='get_tipoUsuario_display',
        read_only=True
    )

    class Meta:
        model = Participacion
        fields = ['id', 'usuarioId', 'tipoUsuario', 'tipoUsuario_display', 'nombre', 'correo']
