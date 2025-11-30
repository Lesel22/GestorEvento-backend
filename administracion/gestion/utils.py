

from boto3 import session
from os import environ
import os


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

def get_content_type(filename):
    CONTENT_TYPES = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png'
    }
    _, ext = os.path.splitext(filename.lower())
    return CONTENT_TYPES.get(ext, 'application/octet-stream')