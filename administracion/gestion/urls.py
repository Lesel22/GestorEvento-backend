from django.urls import path
from .views import (registro,
                    validar_usuario,
                    GestionEventos,
                    GestionEvento,
                    eliminarImagen,
                    GestionInscripciones,
                    obtenerInscripciones,
                    EstadoInscripcionEvento,
                    CustomTokenObtainPairView
                    )  
from rest_framework_simplejwt.views import TokenObtainSlidingView, TokenRefreshSlidingView

urlpatterns = [ 
    path('registro', registro),
    path('login', CustomTokenObtainPairView.as_view()),
    path('validar-usuario', validar_usuario),
    path('eventos', GestionEventos.as_view()),
    path('evento/<pk>', GestionEvento.as_view()),
    path('evento/eliminar-imagen/<id>', eliminarImagen),
    path('inscripciones', GestionInscripciones.as_view()),
    path('inscripciones/<id>', obtenerInscripciones),
    path('inscripciones/<evento_id>/estado',EstadoInscripcionEvento.as_view() ),
    # path('participantes', GestionParticipantes.as_view()),
    # path('participante/<pk>', GestionParticipante.as_view()),
    # path('participaciones', GestionParticipaciones.as_view()),
    # path('inscripciones/<pk>', obtenerInscripciones),
    # path('participacion/<pk>', EliminarParticipacion.as_view()),
    # path('evento/<id>/participantes', obtenerParticipaciones),
]