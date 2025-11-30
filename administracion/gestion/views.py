from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView, CreateAPIView, DestroyAPIView
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import Evento,  Participacion, Usuario
from .serializers import EventoSerializer,  ParticipacionSerializer, UsuarioSerializer, CustomTokenObtainPairSerializer
from django.db import transaction
from boto3 import session
from os import environ
from datetime import datetime
import json
from .utils import get_content_type
from .permissions import EsAdminOrPersonal


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

@api_view(['POST'])
def registro(request):
    print(request.data)
    serializador= UsuarioSerializer(data=request.data)
    if serializador.is_valid():
        print(serializador.validated_data)
        nombre = serializador.validated_data.get('nombre')
        correo = serializador.validated_data.get('correo')
        apellido = serializador.validated_data.get('apellido')
        password = serializador.validated_data.get('password')
        tipoUsuario = serializador.validated_data.get('tipoUsuario')

        nuevoUsuario = Usuario(nombre=nombre, correo=correo, apellido=apellido, tipoUsuario=tipoUsuario)
        nuevoUsuario.set_password(password)
        nuevoUsuario.save()
        return Response(data={
            'message':'Usuario registrado exitosamente'
        }, status=status.HTTP_201_CREATED)
    else:
        return Response(data={
            'message':'Error al crear',
            'content': serializador.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
class GestionEventos(ListCreateAPIView):
    queryset = Evento.objects.all()
    serializer_class = EventoSerializer

    def get_permissions(self):
        # GET → Todos pueden leer
        if self.request.method == 'GET':
            return [AllowAny()]  
        
        # POST → Solo admin o personal
        return [IsAuthenticated(), EsAdminOrPersonal()]

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
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    if archivo:
                        serializer.validated_data['imagen'] = archivo.name
                        evento = serializer.save()

                        s3 = session.Session(
                            aws_access_key_id=environ.get('S3_ACCESS_KEY'),
                            aws_secret_access_key=environ.get('S3_SECRET_KEY'),
                            region_name=environ.get('S3_REGION')
                        ).client('s3')
                        s3.upload_fileobj(
                            archivo,
                            environ.get('S3_BUCKET'),
                            f"{str(evento.id)}/{archivo.name}",
                            ExtraArgs={'ContentType': archivo.content_type}
                        )
                        return Response({
                            "message": "Evento creado con éxito",
                            "content": serializer.data,
                        }, status=status.HTTP_201_CREATED)
                        
            except Exception as e:
                # Si falla la subida a S3 o cualquier otra cosa, se revierte la transacción
                return Response({
                    "message": "Error al crear imagen",
                    "error": str(e)
                }, status=status.HTTP_400_BAD_REQUEST)

            serializer.save()

            return Response({
                "message": "Evento creado con éxito",
                "content": serializer.data,
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "message": "Error al crear evento"
            }, status=status.HTTP_400_BAD_REQUEST)

class GestionEvento(RetrieveUpdateDestroyAPIView):
    queryset = Evento.objects.all()
    serializer_class = EventoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def update(self, request, *args, **kwargs):
        archivo = request.FILES.get('imagen')
        metadata_raw = request.data.get('data')
        data = json.loads(metadata_raw) if metadata_raw else {}

        instance = self.get_object() # obtiene el pk automaticamente
        serializer = self.get_serializer(instance, data=data, partial=kwargs.get('partial', False))

        if serializer.is_valid():
            imagen_previa = instance.imagen
            print('archivo: ---',archivo)

            s3 = session.Session(
                aws_access_key_id=environ.get('S3_ACCESS_KEY'),
                aws_secret_access_key=environ.get('S3_SECRET_KEY'),
                region_name=environ.get('S3_REGION')
            ).client('s3')
            if archivo:
                print('imprent:',archivo.name)
                try:
                    s3.upload_fileobj(
                        archivo,
                        environ.get('S3_BUCKET'),
                        f"{instance.id}/{archivo.name}",
                        ExtraArgs={'ContentType': archivo.content_type}
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
                        s3.delete_object(
                            Bucket=environ.get('S3_BUCKET'),
                            Key=f"{instance.id}/{archivo.name}"
                        )
                    return Response({"message": "Error en BD", "error": str(e)}, status=400)

                # 3) Eliminar la imagen anterior (no afecta consistencia)
                if imagen_previa:
                    try:
                        s3.delete_object(
                            Bucket=environ.get('S3_BUCKET'),
                            Key=f"{instance.id}/{imagen_previa}"
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
            s3 = session.Session(
                aws_access_key_id=environ.get('S3_ACCESS_KEY'),
                aws_secret_access_key=environ.get('S3_SECRET_KEY'),
                region_name=environ.get('S3_REGION')
            ).client('s3')
            try:
                # Borrar archivo en S3
                s3.delete_object(
                    Bucket=environ.get('S3_BUCKET'),
                    Key=f"{eventoEncontrado.id}/{eventoEncontrado.imagen}"
                )
            except Exception as e:
                return Response({
                    'message': 'Error eliminando imagen en S3',
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
    
# class GestionParticipantes(ListCreateAPIView):
#     queryset = Participante.objects.all()
#     serializer_class = ParticipanteSerializer

# class GestionParticipante(RetrieveUpdateDestroyAPIView):
#     queryset = Participante.objects.all()
#     serializer_class = ParticipanteSerializer
    
# class GestionParticipaciones(ListCreateAPIView):
#     queryset = Participacion.objects.all()
#     serializer_class = ParticipacionSerializer

    # def create(self, request):
    #     serializer = ParticipacionSerializer(data=request.data)
    #     if serializer.is_valid():
    #         evento = serializer.validated_data.get('eventoId')
    #         participante = serializer.validated_data.get('participanteId')
    #         participacionEncontrada = Participacion.objects.filter(eventoId=evento,participanteId=participante).first()
    #         if participacionEncontrada:
    #             return Response({
    #             'message':'Participacion ya existe',
    #         }, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    #         serializer.save()

    #         return Response({
    #             'message':'Creacion exitosa',
    #             'content' : serializer.data
    #         })
            
    #     else:
    #         return Response({
    #             'message':'Error crear participacion',
    #             'content' : serializer.errors
    #         })

# class EliminarParticipacion(DestroyAPIView):
#     queryset = Participacion.objects.all()
#     serializer_class = ParticipacionSerializer
       
# @api_view(['GET'])
# def obtenerParticipaciones(request,id):
#     eventoEncontrado = Evento.objects.filter(id=id).first()
#     if eventoEncontrado:
#         participaciones = Participacion.objects.filter(eventoId=eventoEncontrado.id)
#         resultado = ParticipanteSerializer(instance=[p.participanteId for p in participaciones], many=True)
#         print(resultado)
#         return Response(data={
#                 'message': 'Los participantes son',
#                 'content': resultado.data
#             })
#     else:
#         return Response({
#             'message':'Evento no existe'
#         })

class GestionInscripciones(ListCreateAPIView):
    serializer_class = ParticipacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Listar solo las inscripciones del usuario autenticado
        return Participacion.objects.filter(usuarioId=self.request.user)

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
    
    # def perform_create(self, serializer):
    #     # Crear inscripción asociada automáticamente al usuario
    #     serializer.save(usuarioId=self.request.user)

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

