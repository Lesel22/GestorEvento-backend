from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from gestion.models import Usuario, Evento, Participacion
from datetime import date


class Command(BaseCommand):
    help = "Seed de datos demo (usuarios, eventos, participaciones)"

    def handle(self, *args, **kwargs):

        # 🔹 1. USUARIOS DEMO
        owner, created_owner = Usuario.objects.get_or_create(
            correo="owner@test.com",
            defaults={
                "nombre": "Owner",
                "apellido": "Demo",
                "password": make_password("123456"),
                "is_active": True
            }
        )

        user, created_user = Usuario.objects.get_or_create(
            correo="user@test.com",
            defaults={
                "nombre": "User",
                "apellido": "Demo",
                "password": make_password("123456"),
                "is_active": True
            }
        )

        self.stdout.write("✔ Usuarios listos")

        # 🔹 2. EVITAR DUPLICAR EVENTOS
        if Evento.objects.exists():
            self.stdout.write("⚠️ Eventos ya existen, skip")
            return

        # 🔹 3. CREAR EVENTOS
        evento1 = Evento.objects.create(
            nombre="Conferencia Tech Arequipa",
            lugar="Arequipa",
            fecha=date(2026, 5, 10),
            descripcion="Evento de tecnología con charlas y networking",
            propietario=owner
        )

        evento2 = Evento.objects.create(
            nombre="Meetup Python",
            lugar="Lima",
            fecha=date(2026, 6, 15),
            descripcion="Reunión de desarrolladores Python",
            propietario=owner
        )

        self.stdout.write("✔ Eventos creados")

        # 🔹 4. CREAR PARTICIPACIONES
        Participacion.objects.get_or_create(
            usuarioId=user,
            eventoId=evento1,
            defaults={
                "tipoUsuario": "2"  # Asistente
            }
        )

        Participacion.objects.get_or_create(
            usuarioId=user,
            eventoId=evento2,
            defaults={
                "tipoUsuario": "3"  # Participante
            }
        )

        self.stdout.write("✔ Participaciones creadas")

        self.stdout.write(self.style.SUCCESS("🔥 Seed completado correctamente"))