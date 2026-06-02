from config import settings
from logging_utils import get_logger
from supabase_client import get_supabase_client


PRIVATE_STORAGE_SCHEME = "supabase-private"
DEFAULT_SIGNED_URL_TTL_SECONDS = 3600
logger = get_logger(__name__)


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


def download_private_storage_reference(value: str) -> bytes:
    parsed = parse_private_storage_reference(value)
    if not parsed:
        raise ValueError("La referencia no apunta a storage privado.")
    bucket, path = parsed
    content = get_supabase_client().storage.from_(bucket).download(path)
    if isinstance(content, bytes):
        return content
    if hasattr(content, "content"):
        return content.content
    raise ValueError("Storage no devolvio bytes para el archivo solicitado.")


def upload_to_storage(
    file_bytes: bytes,
    folder_name: str,
    filename: str,
    content_type: str,
    *,
    return_public_url: bool = False,
    allow_overwrite: bool = True,
):
    """
    Sube un archivo al bucket configurado de forma sincrona.

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

    import time

    started_at = time.perf_counter()
    file_options = {"content-type": content_type}
    if allow_overwrite:
        file_options["upsert"] = "true"

    try:
        client.storage.from_(bucket).upload(
            path=path,
            file=file_bytes,
            file_options=file_options,
        )
    except Exception:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.exception(
            "storage_upload_failed",
            extra={
                "event": "storage_upload_failed",
                "duration_ms": duration_ms,
                "context": f"bucket={bucket} path={path} bytes={len(file_bytes)}",
            },
        )
        raise
    else:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            "storage_upload_completed",
            extra={
                "event": "storage_upload_completed",
                "duration_ms": duration_ms,
                "context": f"bucket={bucket} path={path} bytes={len(file_bytes)}",
            },
        )

    if return_public_url:
        return client.storage.from_(bucket).get_public_url(path)

    return build_private_storage_reference(path, bucket=bucket)


def check_storage_ready() -> dict:
    if not settings.has_supabase_storage:
        return {
            "ok": False,
            "configured": False,
            "bucket": settings.SUPABASE_STORAGE_BUCKET,
        }

    client = get_supabase_client()
    bucket = settings.SUPABASE_STORAGE_BUCKET
    bucket_accessible = False
    bucket_error = None
    objects_listable = False
    list_error = None

    try:
        client.storage.get_bucket(bucket)
        bucket_accessible = True
    except Exception as exc:
        bucket_error = type(exc).__name__

    if bucket_accessible:
        try:
            client.storage.from_(bucket).list("", {"limit": 1})
            objects_listable = True
        except Exception as exc:
            list_error = type(exc).__name__

    return {
        "ok": bucket_accessible,
        "configured": True,
        "bucket": bucket,
        "uses_server_key": bool(settings.SUPABASE_SERVICE_ROLE_KEY.strip()),
        "bucket_accessible": bucket_accessible,
        "bucket_error": bucket_error,
        "objects_listable": objects_listable,
        "list_error": list_error,
    }
