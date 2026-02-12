from django.urls import path
from .views import (registro,
                    validar_usuario,
                    GestionEventos,
                    GestionEvento,
                    eliminarImagen,
                    GestionInscripciones,
                    obtenerInscripciones,
                    EstadoInscripcionEvento,
                    CustomTokenObtainPairView,
                    LoginView,
                    MeView,
                    RefreshView,
                    LogoutView
                    )  
from rest_framework_simplejwt.views import TokenObtainSlidingView, TokenRefreshSlidingView

auth = "auth/"

urlpatterns = [ 

    #Rutas nuevo login
    path(auth + "login", LoginView.as_view(), name="login"),
    path(auth + "me", MeView.as_view(), name="me"),
    path(auth + "refresh", RefreshView.as_view(), name="refresh"),
    path(auth + "logout", LogoutView.as_view(), name="logout"),
    path(auth + "register", registro, name="logout"),



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