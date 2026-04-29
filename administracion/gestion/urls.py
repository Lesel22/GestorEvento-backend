from django.urls import path
from .views import (registro,
                    validar_usuario,
                    GestionEventos,
                    GestionEvento,
                    GestionInscripciones,
                    GestionInscripcion,
                    GestionParticipaciones,
                    EstadoInscripcionEvento,
                    LoginView,
                    RefreshView,
                    LogoutView,
                    MeView
                    )  
from rest_framework_simplejwt.views import TokenObtainSlidingView, TokenRefreshSlidingView

auth = "auth/"

urlpatterns = [ 

    #Rutas nuevo login
    path(auth + "login", LoginView.as_view(), name="login"),
    path(auth + "me", MeView.as_view(), name="me"),
    path(auth + "refresh", RefreshView.as_view(), name="refresh"),
    path(auth + "logout", LogoutView.as_view(), name="logout"),
    path(auth + "register", registro, name="register"),
    path(auth + 'validar-usuario', validar_usuario, name="validate"),

    
    path('eventos', GestionEventos.as_view()),
    path('evento/<pk>', GestionEvento.as_view()),
    path('evento/<pk>/participaciones', GestionParticipaciones.as_view()),
    path('inscripciones', GestionInscripciones.as_view()),
    path('inscripciones/<pk>', GestionInscripcion.as_view()),
    path('inscripciones/<evento_id>/estado',EstadoInscripcionEvento.as_view() ),
]