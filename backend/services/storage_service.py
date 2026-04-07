from config import settings
from supabase_client import get_supabase_client


async def upload_to_storage(
    file_bytes: bytes,
    folder_name: str,
    filename: str,
    content_type: str,
):
    """
    Sube un archivo al bucket configurado y retorna la URL publica.
    """
    if not file_bytes:
        raise ValueError("No se puede subir un archivo vacio.")
    if not content_type:
        raise ValueError("El archivo debe incluir un content_type valido.")

    client = get_supabase_client()
    bucket = settings.SUPABASE_STORAGE_BUCKET
    path = f"{folder_name}/{filename}"

    client.storage.from_(bucket).upload(
        path=path,
        file=file_bytes,
        file_options={"content-type": content_type, "x-upsert": "true"},
    )

    return client.storage.from_(bucket).get_public_url(path)
