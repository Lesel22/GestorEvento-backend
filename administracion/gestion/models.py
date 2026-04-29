from django.db import models
from uuid import uuid4
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
import secrets
from django.utils import timezone
from datetime import timedelta
from datetime import datetime
from django.utils.timezone import now, make_aware

# Profundizar superuser ROOT
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

class EventoManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(eliminado=False)
    
class Evento(models.Model):
    objects = EventoManager()
    all_objects = models.Manager()  # acceso total
    
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    imagen = models.URLField(blank=True, null=True) # Cambio de ImageField
    imagen_public_id = models.CharField(max_length=255, null=True)
    nombre = models.CharField(max_length=255)
    lugar = models.CharField(max_length=255)
    latitud = models.FloatField(null=True, blank=True)
    longitud = models.FloatField(null=True, blank=True)
    referencia = models.CharField(null=True, blank=True) 
    fecha = models.DateField()
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    limite_participantes = models.PositiveIntegerField(null=True, blank=True)
    descripcion = models.TextField(null=True)
    estado = models.CharField(
        max_length=20,
        choices=[
            ('activo', 'Activo'),
            ('cancelado', 'Cancelado'),
            ('finalizado', 'Finalizado')
        ],
        default='activo'
    )
    eliminado = models.BooleanField(default=False)
    created_at = models.DateTimeField(null=False, auto_now_add=True)
    updated_at = models.DateTimeField(null=False, auto_now=True)

    propietario = models.ForeignKey(to=Usuario,
                                    db_column='organizador_id',
                                    on_delete=models.PROTECT,
                                    related_name='eventos')
    
    @property
    def estado_evento(self):
        if self.estado == "cancelado":
            return "Cancelado"

        fecha_evento = make_aware(datetime.combine(self.fecha, self.hora_inicio))

        if fecha_evento < now():
            return "Finalizado"

        return "Activo"
    
    # @property
    # def duracion(self):
    #     if self.estado == "cancelado":
    #         return "Cancelado"

    #     fecha_evento = make_aware(datetime.combine(self.fecha, self.hora_inicio))

    #     if fecha_evento < now():
    #         return "Finalizado"

    #     return "Activo"

    class Meta:
        db_table = 'eventos'

class Participacion(models.Model):
    TIPO_PARTICIPACION = [
        ('1','Colaborador'),
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


#Algun dia si hay ganas
# class EventoImagen(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

#     evento = models.ForeignKey(
#         Evento,
#         on_delete=models.CASCADE,
#         related_name="imagenes"
#     )

#     url = models.TextField()

#     orden = models.IntegerField(default=0)
#     es_portada = models.BooleanField(default=False)

#     createdAt = models.DateTimeField(auto_now_add=True)