from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import Evento, Participacion, Usuario
from .utils import generar_url_firmada, generar_url_cloudinary

# usuarios/serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class UsuarioSerializer(ModelSerializer):
    class Meta:
        model = Usuario
        exclude = ['groups', 'user_permissions', 'is_active', 'is_superuser', 'last_login']
        extra_kwargs = {
            'password': {'write_only': True}
        }

class EventoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Evento
        #exclude = ['imagen']
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Agregar un campo temporal
        data['imagen'] = generar_url_cloudinary(instance) if instance.imagen else None
        return data

class ParticipacionSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source='eventoId.nombre')
    fecha = serializers.CharField(source='eventoId.fecha')
    tipoUsuario_display = serializers.CharField(
        source='get_tipoUsuario_display',
        read_only=True
    )

    class Meta:
        model = Participacion
        fields = ['id', 'eventoId', 'tipoUsuario_display', 'nombre', 'fecha']


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        print(user.nombre)
        print(user.apellido)
        print(user.correo)
        print(str(user.id))
        token = super().get_token(user)

        # Información extra dentro del token (opcional)
        token['nombre'] = user.nombre
        token['apellido'] = user.apellido
        token['correo'] = user.correo
        token['id'] = str(user.id)

        print(token)

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # Información extra fuera del token (respuesta JSON)
        # data['user'] = {
        #     "id": str(self.user.id),
        #     "nombre": self.user.nombre,
        #     "apellido": self.user.apellido,
        #     "correo": self.user.correo
        # }
        # data['user'] = {
        #     "id": str(self.user.id),
        #     "nombre": self.user.nombre,
        #     "apellido": self.user.apellido,
        #     "correo": self.user.correo
        # }
        data['id'] = str(self.user.id)
        data['nombre'] = self.user.nombre
        data['apellido'] = self.user.apellido
        data['correo'] = self.user.correo

        return data