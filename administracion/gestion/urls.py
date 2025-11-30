from django.urls import path
from .views import (registro,
                    GestionEventos,
                    GestionEvento,
                    eliminarImagen,
                    GestionInscripciones,
                    obtenerInscripciones,
                    # GestionParticipantes,
                    # GestionParticipante,
                    # GestionParticipaciones,
                    # obtenerParticipaciones,
                    # EliminarParticipacion,
                    # obtenerInscripciones,
                    CustomTokenObtainPairView
                    )  
from rest_framework_simplejwt.views import TokenObtainPairView

urlpatterns = [ 
    path('registro', registro),
    path('login', CustomTokenObtainPairView.as_view()),
    path('eventos', GestionEventos.as_view()),
    path('evento/<pk>', GestionEvento.as_view()),
    path('evento/eliminar-imagen/<id>', eliminarImagen),
    path('inscripciones', GestionInscripciones.as_view()),
    path('inscripciones/<id>', obtenerInscripciones),
    # path('participantes', GestionParticipantes.as_view()),
    # path('participante/<pk>', GestionParticipante.as_view()),
    # path('participaciones', GestionParticipaciones.as_view()),
    # path('inscripciones/<pk>', obtenerInscripciones),
    # path('participacion/<pk>', EliminarParticipacion.as_view()),
    # path('evento/<id>/participantes', obtenerParticipaciones),
]