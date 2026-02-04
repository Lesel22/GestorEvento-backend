from boto3 import session
from os import environ
import os

from django.core.mail import EmailMultiAlternatives
from django.conf import settings

from cloudinary.utils import cloudinary_url
import time

def noExtension(str):
    # return str.rsplit(".", 1)[0] 
    return str.rsplit(".", 1)[0] if str is not None else None

def generar_url_firmada(instancia):
    s3 = session.Session(
        aws_access_key_id=environ.get('S3_ACCESS_KEY'),
        aws_secret_access_key=environ.get('S3_SECRET_KEY'),
        region_name=environ.get('S3_REGION')
    ).client('s3')
    url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
            "Bucket" : environ.get('S3_BUCKET'),
            "Key" : f"{str(instancia.id)}/{instancia.imagen}"
            },
            ExpiresIn=3600
    )
    return url

def generar_url_cloudinary(instancia):
    print(instancia.imagen)
    public_id = f"{str(instancia.id)}/{noExtension(instancia.imagen)}"

    print(public_id)
    url, options = cloudinary_url(
        public_id,
        resource_type="image",      # image / video / raw
        type="upload",       # obligatorio para privadas
        # sign_url=True,              # genera la firma
        secure=True,                # https
        # transformation=[{"width":800,"crop":"scale"}], # opcional
        # expires_at=int(time.time()) + 3600             # URL expira en 1 hora
    )

    return url

def get_content_type(filename):
    CONTENT_TYPES = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png'
    }
    _, ext = os.path.splitext(filename.lower())
    return CONTENT_TYPES.get(ext, 'application/octet-stream')

def enviar_correo_validacion(destinatario, token):
    link = f"{settings.FRONTEND_URL}/habilitar-usuario?token={token}"

    subject = 'Valida tu cuenta'
    from_email = settings.DEFAULT_FROM_EMAIL
    to = [destinatario]

    text_content = f"""
    Bienvenido.
    Valida tu cuenta aquí:
    {link}
    """

    html_content = f"""
    <h3>Bienvenido</h3>
    <p>
        Haz click en el siguiente
        <a href="{link}">enlace</a>
        para validar tu cuenta.
    </p>
    """

    email = EmailMultiAlternatives(subject, text_content, from_email, to)
    email.attach_alternative(html_content, "text/html")
    email.send()
