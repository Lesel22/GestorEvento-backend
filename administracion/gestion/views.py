from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView, CreateAPIView, DestroyAPIView
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import Evento,  Participacion, Usuario, EmailVerificationToken
from .serializers import EventoSerializer,  ParticipacionSerializer, UsuarioSerializer, CustomTokenObtainPairSerializer
from django.db import transaction
from boto3 import session
from os import environ
from datetime import datetime
import json
from .utils import enviar_correo_validacion, noExtension
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
import cloudinary
import cloudinary.uploader
import cloudinary.api

from django.contrib.auth import authenticate

from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator

@method_decorator(ensure_csrf_cookie, name='dispatch')
class LoginView(APIView):
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

        return response

from rest_framework_simplejwt.authentication import JWTAuthentication

from rest_framework_simplejwt.authentication import JWTAuthentication

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        raw_token = request.COOKIES.get("access")
        if not raw_token:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token

class MeView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    def get(self, request):
        if request.user and request.user.is_authenticated:
            return Response({
                "id": request.user.id,
                "email": request.user.correo,
            })
        return Response({ "id": None })

class RefreshView(APIView):
    def post(self, request):
        refresh_token = request.COOKIES.get("refresh")

        if not refresh_token:
            return Response(status=401)

        refresh = RefreshToken(refresh_token)
        access = refresh.access_token

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



class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


import threading

@api_view(['POST'])
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
        threading.Thread(
            target=enviar_correo_validacion,
            args=(usuario.correo, token.token)
        ).start()

        return Response({
            'message': 'Usuario registrado. Revisa tu correo para validar la cuenta.'
        }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
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

    def get_permissions(self):
        # GET → Todos pueden leer
        if self.request.method == 'GET':
            return [AllowAny()]  
        
        # POST → Solo admin o personal
        return [IsAuthenticated()]

    def list(self, request):
        fecha = request.query_params.get('fecha', None)
        search = request.query_params.get('search', None)

        params = {}

        if fecha:
            params['fecha__date'] = fecha

        if search:
            params['nombre__icontains'] = search

        eventos = Evento.objects.filter(**params).order_by('-nombre')

        serializer = EventoSerializer(eventos, many=True)

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
                "message": "Error al crear evento",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():

                # 1️⃣ Crear evento
                evento = serializer.save()

                # 2️⃣ Subir imagen (si existe)
                if archivo:
                    evento.imagen = archivo.name
                    evento.save()

                    cloudinary.uploader.upload(
                        archivo,
                        public_id=noExtension(archivo.name),
                        folder=str(evento.id),
                        resource_type='image'
                    )

                # 3️⃣ Crear participación (PROPIETARIO)
                Participacion.objects.create(
                    usuarioId=request.user,
                    eventoId=evento,
                    tipoUsuario='1'  # propietario
                )

                return Response({
                    "message": "Evento y participación creados con éxito",
                    "content": EventoSerializer(evento).data
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                "message": "Error al crear evento",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class GestionEvento(RetrieveUpdateDestroyAPIView):
    queryset = Evento.objects.all()
    serializer_class = EventoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object() 
    
        try:
            with transaction.atomic():
                instance.delete()  # ✅ borrar registro

            # 🔹 Solo tocar Cloudinary si hay imagen
            if instance.imagen:
                folder = str(instance.id)
                public_id = f"{folder}/{noExtension(instance.imagen)}"
                cloudinary.uploader.destroy(
                    public_id,
                    resource_type="image"
                )
                cloudinary.api.delete_folder(folder)

            return Response(
                {"message": "Evento eliminado correctamente"},
                status=status.HTTP_204_NO_CONTENT
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            

    def update(self, request, *args, **kwargs):
        archivo = request.FILES.get('imagen')
        metadata_raw = request.data.get('data')
        data = json.loads(metadata_raw) if metadata_raw else {}

        instance = self.get_object() # obtiene el pk automaticamente
        serializer = self.get_serializer(instance, data=data, partial=kwargs.get('partial', False))

        if serializer.is_valid():
            imagen_previa = instance.imagen
            if archivo:
                try:
                    resultado = cloudinary.uploader.upload(
                        archivo,
                        public_id= noExtension(archivo.name),
                        folder= str(instance.id),
                        resource_type='image'
                    )
                except Exception as e:
                    return Response({
                        "message": "Error subiendo la nueva imagen",
                        "error": str(e)
                    }, status=400)

                # 2) Guardar cambios en BD con atomicidad
                try:
                    with transaction.atomic():
                        evento = serializer.save(imagen=archivo.name)
                except Exception as e:
                    # Deshacer “manualmente” la subida
                    if archivo:
                        cloudinary.uploader.destroy(
                            f"{instance.id}/{noExtension(archivo.name)}",
                            resource_type="image"
                        )
                    return Response({"message": "Error en BD", "error": str(e)}, status=400)

                # 3) Eliminar la imagen anterior (no afecta consistencia)
                if imagen_previa:
                    try:
                        cloudinary.uploader.destroy(
                            f"{instance.id}/{noExtension(imagen_previa)}",
                            resource_type="image"
                        )
                    except:
                        pass  # Solo se pierde limpieza, pero no consistencia
            

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

@api_view(['PUT'])
def eliminarImagen(request,id):
    eventoEncontrado = Evento.objects.filter(id=id).first()
    if eventoEncontrado:
        if eventoEncontrado.imagen:
            try:
                cloudinary.uploader.destroy(
                    f"{str(eventoEncontrado.id)}/{noExtension(eventoEncontrado.imagen)}",
                    resource_type="image"
                )
            except Exception as e:
                return Response({
                    'message': 'Error eliminando imagen en Cloudinary',
                    'error': str(e)
                }, status=500)
            
            eventoEncontrado.imagen = None
            eventoEncontrado.save(update_fields=['imagen'])

            return Response(data={
                    'message': 'Imagen eliminada exitosamente'
                })
        else:
            return Response({
                'message':'Evento no contiene imagen'
            })
    else:
        return Response({
            'message':'Evento no existe'
        })

class GestionInscripciones(ListCreateAPIView):
    serializer_class = ParticipacionSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request):
        fecha = request.query_params.get('fecha', None)
        search = request.query_params.get('search', None)

        params = {}

        if fecha:
            params['fecha__date'] = fecha

        if search:
            params['nombre__icontains'] = search

        participaciones = Participacion.objects.filter(
            usuarioId=self.request.user
        )

        serializer = ParticipacionSerializer(participaciones, many=True)

        return Response({
            'message': 'Eventos encontrados',
            'content': serializer.data
        })

    def create(self, request, *args, **kwargs):
        # Sobrescribimos create para agregar tu lógica personalizada
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        evento = serializer.validated_data.get('eventoId')
        usuario = request.user  # participante real

        # 1️⃣ Verificar si la participación ya existe
        participacion = Participacion.objects.filter(
            eventoId=evento,
            usuarioId=usuario
        ).first()

        if participacion:
            return Response({
                'message': 'Participación ya existe'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 2️⃣ Guardar participación automáticamente con el usuario autenticado
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtenerInscripciones(request,id):
    if str(request.user.id) != id:
        return Response(
            {'message': 'No autorizado'},
            status=403
        )
    participaciones = Participacion.objects.filter(usuarioId=id)
    eventos = [p.eventoId for p in participaciones]
    resultado = EventoSerializer(eventos, many=True) 
    return Response(data={
        'message': 'Inscripciones son',
        'content': resultado.data
    })

class EstadoInscripcionEvento(APIView):
    # permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, evento_id):
        usuario_id = request.user.id

        inscripcion = Participacion.objects.filter(
            usuarioId=usuario_id,
            eventoId=evento_id
        ).first()


        return Response(data = {
            "estado": inscripcion.tipoUsuario if inscripcion else None
        })