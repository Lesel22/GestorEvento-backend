from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import Evento, Participacion, Usuario
from .utils import generar_url_firmada, generar_url_cloudinary
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class UsuarioSerializer(ModelSerializer):
    class Meta:
        model = Usuario
        exclude = ['groups', 'user_permissions', 'is_active', 'is_superuser', 'last_login']
        extra_kwargs = {
            'password': {'write_only': True}
        }

class EventoSerializer(serializers.ModelSerializer):
    participantes_count = serializers.IntegerField(
        source='inscripciones.count',
        read_only=True
    )
    estado_usuario = serializers.SerializerMethodField()

    def get_estado_usuario(self, obj):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return None
        user = request.user

        if obj.propietario_id == user.id:
            return "0"

        if hasattr(obj, "user_participacion") and obj.user_participacion:
            return obj.user_participacion[0].tipoUsuario

        return None

    class Meta:
        model = Evento
        fields = '__all__'

class ParticipacionSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source='eventoId.nombre', read_only=True)
    fecha = serializers.CharField(source='eventoId.fecha', read_only=True)
    tipoUsuario_display = serializers.CharField(
        source='get_tipoUsuario_display',
        read_only=True
    )

    class Meta:
        model = Participacion
        fields = ['id','usuarioId', 'eventoId', 'tipoUsuario', 'tipoUsuario_display', 'nombre', 'fecha']

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
