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
    public_id = f"{str(instancia.id)}/{noExtension(instancia.imagen)}"
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


from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def enviar_correo_validacion(destinatario: str, token: str):
    link = f"{settings.FRONTEND_URL}/habilitar-usuario?token={token}"

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background:#f4f4f4; padding:20px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td align="center">
            <table width="600" style="background:white; padding:30px; border-radius:8px;">
              <tr>
                <td align="center">
                  <h2 style="color:#333;">Bienvenido a Calenda 🎉</h2>
                  <p style="color:#555;">
                    Gracias por registrarte. Para activar tu cuenta haz clic en el botón:
                  </p>

                  <a href="{link}"
                     style="display:inline-block;
                            background:#4CAF50;
                            color:white;
                            padding:12px 24px;
                            text-decoration:none;
                            border-radius:5px;
                            margin:20px 0;">
                    Verificar cuenta
                  </a>

                  <p style="color:#777; font-size:14px;">
                    Si el botón no funciona, copia y pega este enlace en tu navegador:
                  </p>

                  <p style="font-size:12px; color:#999;">
                    {link}
                  </p>

                  <hr style="margin:30px 0;">
                  <p style="font-size:12px; color:#aaa;">
                    Si no solicitaste esta cuenta, puedes ignorar este correo.
                  </p>
                  <p style="font-size:12px; color:#aaa;">
                    © 2026 Calenda
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    text_content = f"""
    Bienvenido a Calenda

    Para activar tu cuenta visita:
    {link}

    Si no solicitaste esta cuenta, ignora este mensaje.

    © 2026 Calenda
    """

    mensaje = Mail(
        from_email=settings.EMAIL_FROM,
        to_emails=destinatario,
        subject="Verifica tu cuenta en Calenda",
        html_content=html_content,
        plain_text_content=text_content,
    )

    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        respuesta = sg.send(mensaje)
        print("Email enviado. Status:", respuesta.status_code)
        return respuesta.status_code
    except Exception as e:
        print("Error enviando correo:", str(e))
        return None


# def enviar_correo_validacion(destinatario, token):
#     link = f"{settings.FRONTEND_URL}/habilitar-usuario?token={token}"

#     subject = 'Valida tu cuenta'
#     from_email = settings.DEFAULT_FROM_EMAIL
#     to = [destinatario]

#     text_content = f"""
#     Bienvenido.
#     Valida tu cuenta aquí:
#     {link}
#     """

#     html_content = f"""
#     <h3>Bienvenido</h3>
#     <p>
#         Haz click en el siguiente
#         <a href="{link}">enlace</a>
#         para validar tu cuenta.
#     </p>
#     """

#     email = EmailMultiAlternatives(subject, text_content, from_email, to)
#     email.attach_alternative(html_content, "text/html")
#     email.send()
