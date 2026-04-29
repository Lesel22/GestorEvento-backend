from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from gestion.models import Usuario, Evento, Participacion
from datetime import date, time


class Command(BaseCommand):
    help = "Seed de datos demo (usuarios, eventos, participaciones)"

    def handle(self, *args, **kwargs):

        # =========================================================
        # 1. USUARIOS DEMO
        # =========================================================

        owner, created_owner = Usuario.objects.get_or_create(
            correo="owner@test.com",
            defaults={
                "nombre": "Owner",
                "apellido": "Demo",
                "password": make_password("123456"),
                "is_active": True,
            }
        )

        user, created_user = Usuario.objects.get_or_create(
            correo="user@test.com",
            defaults={
                "nombre": "User",
                "apellido": "Demo",
                "password": make_password("123456"),
                "is_active": True,
            }
        )

        self.stdout.write(self.style.SUCCESS("✔ Usuarios listos"))

        # =========================================================
        # 2. EVITAR DUPLICAR EVENTOS
        # =========================================================

        if Evento.all_objects.exists():
            self.stdout.write("⚠️ Eventos ya existen, skip")
            return

        # =========================================================
        # 3. CREAR EVENTOS
        # =========================================================

        evento1 = Evento.objects.create(
            nombre="Conferencia Tech Arequipa",
            lugar="Arequipa",
            latitud=-16.4090,
            longitud=-71.5375,
            referencia="Cerca de la Plaza de Armas",
            fecha=date(2026, 5, 10),
            hora_inicio=time(9, 0),
            hora_fin=time(13, 0),
            limite_participantes=150,
            descripcion="Evento de tecnología con charlas y networking",
            estado="activo",
            # imagen="https://picsum.photos/800/400",
            # imagen_public_id="demo_evento_1",
            propietario=owner,
        )

        evento2 = Evento.objects.create(
            nombre="Meetup Python Lima",
            lugar="Lima",
            latitud=-12.0464,
            longitud=-77.0428,
            referencia="Centro empresarial de San Isidro",
            fecha=date(2026, 6, 15),
            hora_inicio=time(18, 0),
            hora_fin=time(21, 0),
            limite_participantes=80,
            descripcion="Reunión de desarrolladores Python",
            estado="activo",
            # imagen="https://picsum.photos/800/401",
            # imagen_public_id="demo_evento_2",
            propietario=owner,
        )

        self.stdout.write(self.style.SUCCESS("✔ Eventos creados"))

        # =========================================================
        # 4. CREAR PARTICIPACIONES
        # =========================================================

        Participacion.objects.get_or_create(
            usuarioId=user,
            eventoId=evento1,
            defaults={
                "tipoUsuario": "2",  # Asistente
            }
        )

        Participacion.objects.get_or_create(
            usuarioId=user,
            eventoId=evento2,
            defaults={
                "tipoUsuario": "3",  # Participante
            }
        )

        self.stdout.write(self.style.SUCCESS("✔ Participaciones creadas"))

        self.stdout.write(
            self.style.SUCCESS("🔥 Seed completado correctamente")
        )