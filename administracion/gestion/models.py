from django.db import models
from uuid import uuid4
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
import secrets
from django.utils import timezone
from datetime import timedelta

class ManejadorUsuario(BaseUserManager):
    def create_superuser(self, nombre, correo, password):
        if not correo:
            raise ValueError('El correo es obligatorio')
        correoNormalizado = self.normalize_email(correo)
        nuevoUsuario = self.model(correo=correoNormalizado, nombre=nombre)
        nuevoUsuario.set_password(password)
        nuevoUsuario.is_superuser = True
        nuevoUsuario.is_staff = True
        nuevoUsuario.save()

class Usuario(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    nombre = models.TextField(null=False)
    apellido = models.TextField()
    correo = models.EmailField(unique=True, null=False)
    password = models.TextField(null=False)

    is_active = models.BooleanField(default=False) #VALIDACION SMTP

    USERNAME_FIELD = 'correo'
    REQUIRED_FIELDS = ['nombre']

    objects = ManejadorUsuario()

    class Meta:
        db_table = 'usuarios'

class EmailVerificationToken(models.Model):
    user = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    token = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)

    @staticmethod
    def expiration_time():
        return timezone.now() + timedelta(hours=24)

class Evento(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    imagen = models.TextField(null=True) # Cambio de ImageField
    nombre = models.TextField()
    fecha = models.DateTimeField()
    lugar = models.TextField()
    descripcion = models.TextField(null=True)
    createdAt = models.DateTimeField(null=False, auto_now_add=True)
    updatedAt = models.DateTimeField(null=False, auto_now=True)

    usuarioId = models.ForeignKey(to=Usuario,
                                    db_column='organizador_id',
                                    on_delete=models.PROTECT,
                                    related_name='organizaciones')

    class Meta:
        db_table = 'eventos'

class Participacion(models.Model):
    TIPO_PARTICIPACION = [
        ('1','Propietario'),
        ('2','Asistente'),
        ('3','Participante')
    ]
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    tipoUsuario = models.TextField(db_column='tipo_usuario', choices=TIPO_PARTICIPACION)

    usuarioId = models.ForeignKey(to=Usuario,
                                     db_column='participante_id',
                                     on_delete=models.PROTECT,
                                     related_name='participaciones')
    eventoId = models.ForeignKey(to=Evento,
                               db_column='evento_id',
                               on_delete=models.CASCADE,
                               related_name='inscripciones')

    createdAt = models.DateTimeField(null=False, auto_now_add=True)
    updatedAt = models.DateTimeField(null=False, auto_now=True)

    class Meta:
        db_table = 'participaciones'