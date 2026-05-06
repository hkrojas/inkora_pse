from config import settings
from supabase_client import get_supabase_client


PRIVATE_STORAGE_SCHEME = "supabase-private"
DEFAULT_SIGNED_URL_TTL_SECONDS = 3600


def build_storage_path(folder_name: str, filename: str) -> str:
    folder = (folder_name or "").strip().strip("/")
    name = (filename or "").strip().lstrip("/")
    if not name:
        raise ValueError("El archivo debe incluir un nombre valido.")
    return f"{folder}/{name}" if folder else name


def build_private_storage_reference(path: str, *, bucket: str | None = None) -> str:
    resolved_bucket = (bucket or settings.SUPABASE_STORAGE_BUCKET).strip()
    normalized_path = (path or "").strip().lstrip("/")
    if not resolved_bucket or not normalized_path:
        raise ValueError("No se pudo construir la referencia privada de storage.")
    return f"{PRIVATE_STORAGE_SCHEME}://{resolved_bucket}/{normalized_path}"


def parse_private_storage_reference(value: str | None) -> tuple[str, str] | None:
    if not value:
        return None
    prefix = f"{PRIVATE_STORAGE_SCHEME}://"
    if not value.startswith(prefix):
        return None
    remainder = value[len(prefix):]
    bucket, separator, path = remainder.partition("/")
    if not bucket or separator != "/" or not path:
        return None
    return bucket, path


def is_private_storage_reference(value: str | None) -> bool:
    return parse_private_storage_reference(value) is not None


def is_remote_url(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    return normalized.startswith(("http://", "https://"))


def _resolve_bucket_and_path(value: str) -> tuple[str, str]:
    parsed = parse_private_storage_reference(value)
    if parsed:
        return parsed
    normalized = (value or "").strip().lstrip("/")
    if not normalized:
        raise ValueError("No hay una ruta de storage para firmar.")
    return settings.SUPABASE_STORAGE_BUCKET, normalized


def create_signed_storage_url(
    value: str,
    *,
    expires_in_seconds: int = DEFAULT_SIGNED_URL_TTL_SECONDS,
) -> str:
    bucket, path = _resolve_bucket_and_path(value)
    client = get_supabase_client()
    signed = client.storage.from_(bucket).create_signed_url(path, expires_in_seconds)
    return signed.get("signedURL") or signed.get("signedUrl") or ""


def resolve_storage_download_url(
    value: str | None,
    *,
    expires_in_seconds: int = DEFAULT_SIGNED_URL_TTL_SECONDS,
) -> str | None:
    if not value:
        return None
    if is_remote_url(value):
        return value
    return create_signed_storage_url(value, expires_in_seconds=expires_in_seconds)


async def upload_to_storage(
    file_bytes: bytes,
    folder_name: str,
    filename: str,
    content_type: str,
    *,
    return_public_url: bool = False,
):
    """
    Sube un archivo al bucket configurado.

    - `return_public_url=True`: retorna URL publica (ej. logos).
    - `return_public_url=False`: retorna referencia privada para luego firmarla.
    """
    if not file_bytes:
        raise ValueError("No se puede subir un archivo vacio.")
    if not content_type:
        raise ValueError("El archivo debe incluir un content_type valido.")

    client = get_supabase_client()
    bucket = settings.SUPABASE_STORAGE_BUCKET
    path = build_storage_path(folder_name, filename)

    client.storage.from_(bucket).upload(
        path=path,
        file=file_bytes,
        file_options={"content-type": content_type, "x-upsert": "true"},
    )

    if return_public_url:
        return client.storage.from_(bucket).get_public_url(path)

    return build_private_storage_reference(path, bucket=bucket)
