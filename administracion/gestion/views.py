from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import Evento,  Participacion, Usuario, EmailVerificationToken
from .serializers import EventoSerializer,  ParticipacionSerializer, UsuarioSerializer, ParticipacionSerializer2, ParticipacionUsuarioSerializer
from django.db import transaction
from django.db.models import Prefetch
import json
from .utils import enviar_verificacion, noExtension
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
import cloudinary
import cloudinary.uploader
import uuid

from django.contrib.auth import authenticate

from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.conf import settings

@method_decorator(ensure_csrf_cookie, name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        user = authenticate(request, username=email, password=password)

        if not user:
            return Response(
                {"detail": "Correo o contraseña incorrectos"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        response = Response({
            "user": {
                "id": user.id,
                "email": user.correo,
            }
        })

        response.set_cookie(
            key="access",
            value=str(access),
            httponly=True,
            secure=True,
            samesite="None",
        )

        response.set_cookie(
            key="refresh",
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite="None",
        )

        print(settings.DEBUG)

        return response

class MeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if request.user and request.user.is_authenticated:
            return Response({
                "id": request.user.id,
                "email": request.user.correo,
            })
        return Response({ "id": None })

class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    def post(self, request):
        refresh_token = request.COOKIES.get("refresh")

        if not refresh_token:
            return Response(status=401)

        try:
            refresh = RefreshToken(refresh_token)
            access = refresh.access_token
        except Exception:
            return Response({"error": "Invalid refresh"}, status=401)

        response = Response()
        response.set_cookie(
            "access",
            str(access),
            httponly=True,
            secure=True,
            samesite="None"
        )

        return response

class LogoutView(APIView):
    permission_classes = [IsAuthenticated] ##cambio
    def post(self, request):
        response = Response()

        response.delete_cookie(
            key="access",
            path="/",
            samesite="None",
        )

        response.delete_cookie(
            key="refresh",
            path="/",
            samesite="None",
        )
        return response

@api_view(['POST'])
@permission_classes([AllowAny])
def registro(request):
    serializador= UsuarioSerializer(data=request.data)
    if not serializador.is_valid():
        return Response(data={
            'message':'Error al crear',
            'content': serializador.errors
        }, status=status.HTTP_400_BAD_REQUEST)   
    else:
        #usuario = serializador.save()
        usuario = Usuario(
            nombre=serializador.validated_data['nombre'],
            apellido=serializador.validated_data['apellido'],
            correo=serializador.validated_data['correo']
        )
        usuario.set_password(serializador.validated_data['password'])
        usuario.save()

        token = EmailVerificationToken.objects.create(
            user=usuario,
            token=EmailVerificationToken.generate_token(),
            expires_at=EmailVerificationToken.expiration_time()
        )

        # enviar_correo_validacion(usuario.correo, token.token)
        # threading.Thread(
        #     target=enviar_verificacion,
        #     args=(usuario.correo, token.token)
        # ).start()
        enviar_verificacion(usuario, token.token)

        if not settings.USE_REAL_EMAIL:
            return Response({
                'message': 'Usuario registrado. Revisa tu correo para validar la cuenta.',
                'email': usuario.correo,
                'verification_token': token.token #Solo en dev VULNERABLE

            }, status=status.HTTP_201_CREATED)
        else: 
            return Response({
                'message': 'Usuario registrado. Revisa tu correo para validar la cuenta.',

            }, status=status.HTTP_201_CREATED)

        

        # return Response({
        #     'message': 'Usuario registrado. Revisa tu correo para validar la cuenta.'
        # }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([AllowAny])
def validar_usuario(request):
    token_str = request.data
    if not token_str:
        return Response({'message': 'Token requerido'}, status=400)

    try:
        token_obj = EmailVerificationToken.objects.select_related('user').get(
            token=token_str,
            is_used=False
        )
    except EmailVerificationToken.DoesNotExist:
        return Response({'message': 'Token inválido o ya usado'}, status=400)

    # Verifica expiración
    if token_obj.expires_at < timezone.now():
        return Response({'message': 'Token expirado'}, status=400)

    # Activa usuario
    usuario = token_obj.user
    usuario.is_active = True
    usuario.save()

    # Marca token como usado
    token_obj.is_used = True
    token_obj.save()

    # Generar JWT
    refresh = RefreshToken.for_user(usuario)
    access = refresh.access_token

    response = Response({
        'message': 'Cuenta validada correctamente',
        'user': {
            'id': usuario.id,
            'email': usuario.correo,
        }
    })

    # 👇 Igual que en tu LoginView
    response.set_cookie(
        key="access",
        value=str(access),
        httponly=True,
        secure=True,
        samesite="None",
    )

    response.set_cookie(
        key="refresh",
        value=str(refresh),
        httponly=True,
        secure=True,
        samesite="None",
    )

    return response

class GestionEventos(ListCreateAPIView):
    queryset = Evento.objects.all()
    serializer_class = EventoSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Evento.objects.all()

        if user.is_authenticated:
            queryset = queryset.prefetch_related(
                Prefetch(
                    'inscripciones',
                    queryset=Participacion.objects.filter(usuarioId=user),
                    to_attr='user_participacion'
                )
            )

        return queryset

    def list(self, request):
        fecha = request.query_params.get('fecha', None)
        search = request.query_params.get('search', None)
        own = request.query_params.get('own',None)

        params = {}
        if fecha:
            params['fecha__date'] = fecha
        if search:
            params['nombre__icontains'] = search
        if own == 'True' and request.user.is_authenticated:
            params['propietario'] = request.user

        eventos = self.get_queryset().filter(**params).order_by('-nombre')
        serializer = EventoSerializer(eventos, many=True, context={"request":request})

        return Response({
            'message': 'Eventos encontrados',
            'content': serializer.data
        })
    
    def create(self, request):
        archivo = request.FILES.get('imagen')
        metadata_raw = request.data.get('data')
        data = json.loads(metadata_raw)
        serializer = self.get_serializer(data=data)

        if not serializer.is_valid():
            return Response({
                "message": "Error al crear evento al serealizar",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                evento = serializer.save()

                if archivo:
                    public_id = str(uuid.uuid4()) 
                    
                    cloudinary.uploader.upload(
                        archivo,
                        public_id=public_id,
                        folder= f"eventos/{str(evento.id)}",
                        resource_type='image'
                    )

                    evento.imagen = cloudinary.CloudinaryImage(f"eventos/{evento.id}/{public_id}").build_url()
                    evento.imagen_public_id = public_id
                    evento.save()

                return Response({
                    "message": "Evento y participación creados con éxito",
                    "content": EventoSerializer(evento).data
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                "message": "Error al crear evento: detalles",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class GestionEvento(RetrieveUpdateDestroyAPIView):
    queryset = Evento.objects.all()
    serializer_class = EventoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    #Soft delete
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.eliminado = True
        instance.save()

        return Response({"message": "Evento eliminado"}, status=204)
    
    #Hard delete
    # def destroy(self, request, *args, **kwargs):
    #     instance = self.get_object()

    #     try:
    #         # 🔹 1. borrar imagen primero (si existe)
    #         if instance.imagen and instance.imagen_public_id:
    #             folder = f"eventos/{instance.id}"
    #             public_id = f"{folder}/{instance.imagen_public_id}"

    #             cloudinary.uploader.destroy(
    #                 public_id,
    #                 resource_type="image"
    #             )

    #             cloudinary.api.delete_folder(folder)

    #         # 🔹 2. ahora sí DB (atomic por seguridad)
    #         with transaction.atomic():
    #             instance.delete()

    #         return Response(
    #             {"message": "Evento eliminado correctamente"},
    #             status=status.HTTP_204_NO_CONTENT
    #         )

    #     except Exception as e:
    #         return Response(
    #             {"error": str(e)},
    #             status=status.HTTP_500_INTERNAL_SERVER_ERROR
    #         )
            

    def update(self, request, *args, **kwargs):
        archivo = request.FILES.get('imagen')
        metadata_raw = request.data.get('data')
        data = json.loads(metadata_raw) if metadata_raw else {}
        remove_imagen = data.pop("removeImage", False)
        instance = self.get_object() # obtiene el pk automaticamente
        serializer = self.get_serializer(instance, data=data, partial=kwargs.get('partial', False))

        if serializer.is_valid():
            imagen_previa = instance.imagen_public_id
            if archivo:
                public_id = str(uuid.uuid4()) 
                try:
                    resultado = cloudinary.uploader.upload(
                        archivo,
                        public_id=public_id,
                        folder= f"eventos/{str(instance.id)}",
                        resource_type='image'
                    )

                except Exception as e:
                    return Response({
                        "message": "Error subiendo la nueva imagen",
                        "error": str(e)
                    }, status=400)

                try:
                    with transaction.atomic():
                        evento = serializer.save(
                            imagen=cloudinary.CloudinaryImage(f"eventos/{instance.id}/{public_id}").build_url(),
                            imagen_public_id = public_id
                            )
                except Exception as e:
                    # Deshacer “manualmente” la subida
                    if archivo:
                        cloudinary.uploader.destroy(
                            f"eventos/{instance.id}/{public_id}",
                            resource_type="image"
                        )
                    return Response({"message": "Error en BD", "error": str(e)}, status=400)

                # 3) Eliminar la imagen anterior (no afecta consistencia)
                if imagen_previa:
                    try:
                        cloudinary.uploader.destroy(
                            f"eventos/{instance.id}/{imagen_previa}",
                            resource_type="image"
                        )
                    except:
                        pass  
            elif remove_imagen:
                print(f"eventos/{instance.id}/{imagen_previa}")
                try:
                    cloudinary.uploader.destroy(
                        f"eventos/{instance.id}/{imagen_previa}",
                        resource_type="image"
                    )
                    with transaction.atomic():
                        evento = serializer.save(
                            imagen=None,
                            imagen_public_id = None
                        )
                except:
                    pass  

            else:
                serializer.save()

            return Response({
                "message": "Evento actualizado con éxito",
                "content": serializer.data,
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "message": "Error al actualizar evento",
                "content" : serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

class GestionInscripciones(ListCreateAPIView):
    serializer_class = ParticipacionSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        fecha = request.query_params.get('fecha', None)
        search = request.query_params.get('search', None)
        own = request.query_params.get('own',None)
        params = {}

        if fecha:
            params['eventoId__fecha'] = fecha
        if search:
            params['eventoId__nombre__icontains'] = search
        if own == 'True' and request.user.is_authenticated:
            params['usuarioId_id'] = request.user

        participaciones = Participacion.objects.filter(**params).select_related('eventoId')
        serializer = ParticipacionSerializer(participaciones, many=True)

        return Response({
            'message': 'Eventos encontrados',
            'content': serializer.data
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evento = serializer.validated_data.get('eventoId')
        usuario = request.user  

        # Verificar si la participación ya existe
        participacion = Participacion.objects.filter(
            eventoId=evento,
            usuarioId=usuario
        ).first()

        if participacion:
            return Response({
                'message': 'Participación ya existe'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Guardar participación automáticamente con el usuario autenticado
        serializer.save(usuarioId=usuario)

        return Response({
            'message': 'Creación exitosa',
            'content': serializer.data
        }, status=status.HTTP_201_CREATED)
    
class GestionInscripcion(RetrieveUpdateDestroyAPIView):
    serializer_class = ParticipacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Participacion.objects.filter(usuarioId=self.request.user.id)

class EstadoInscripcionEvento(APIView):

    def get(self, request, evento_id):
        usuario_id = request.user.id

        # Si es participante habra coincidencia
        inscripcion = Participacion.objects.filter(
            usuarioId=usuario_id,
            eventoId=evento_id
        ).first()

        relacion = inscripcion.tipoUsuario if inscripcion else None
        
        #puede ser el propietario
        if (not relacion):
            propietario = Evento.objects.filter(
                id=evento_id,
                propietario=usuario_id
            ).first()

            if propietario: 
                relacion = '0'
        

        return Response(data = {
            "estado": relacion
        })
    
class GestionParticipaciones(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        evento = Evento.objects.filter(id=pk).first()
        if not evento:
            return Response({"message": "Evento no encontrado"}, status=404)

        if evento.propietario != request.user:
            return Response(
                {"message": "No autorizado"},
                status=403
            )

        participantes = Participacion.objects.filter(
            eventoId=evento
        ).select_related('usuarioId', 'eventoId')

        data = [
            {
                "id": p.usuarioId.id,
                "nombre": p.usuarioId.nombre,
                "tipo": p.tipoUsuario
            }
            for p in participantes
        ]

        serializer = ParticipacionUsuarioSerializer(participantes, many=True, context={"request":request})

        return Response({
            'message': 'Eventos encontrados',
            'content': serializer.data
        })