from django.db import models
from uuid import uuid4
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin

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
    TIPO_USUARIO = [
        ('1','ADMIN'),
        ('2','PERSONAL'),
        ('3','USUARIO')
    ]
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    nombre = models.TextField(null=False)
    apellido = models.TextField()
    correo = models.EmailField(unique=True, null=False)
    password = models.TextField(null=False)
    tipoUsuario = models.TextField(db_column='tipo_usuario', choices=TIPO_USUARIO)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = 'correo'
    REQUIRED_FIELDS = ['nombre']

    objects = ManejadorUsuario()

    class Meta:
        db_table = 'usuarios'


class Evento(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    imagen = models.TextField(null=True) # Cambio de ImageField
    nombre = models.TextField()
    fecha = models.DateTimeField()
    lugar = models.TextField()
    descripcion = models.TextField(null=True)
    createdAt = models.DateTimeField(null=False, auto_now_add=True)
    updatedAt = models.DateTimeField(null=False, auto_now=True)

    class Meta:
        db_table = 'eventos'

class Participacion(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    usuarioId = models.ForeignKey(to=Usuario,
                                     db_column='participante_id',
                                     on_delete=models.PROTECT,
                                     related_name='participaciones')
    eventoId = models.ForeignKey(to=Evento,
                               db_column='evento_id',
                               on_delete=models.PROTECT,
                               related_name='inscripciones')

    createdAt = models.DateTimeField(null=False, auto_now_add=True)
    updatedAt = models.DateTimeField(null=False, auto_now=True)

    class Meta:
        db_table = 'participaciones'