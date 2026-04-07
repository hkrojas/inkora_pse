from fastapi import HTTPException, UploadFile

from logging_utils import get_logger

logger = get_logger(__name__)


def log_unexpected_error(context: str, exc: Exception) -> None:
    logger.exception(
        "unexpected_error",
        extra={"context": context},
        exc_info=exc,
    )


def raise_internal_server_error(context: str, user_message: str, exc: Exception):
    log_unexpected_error(context, exc)
    raise HTTPException(status_code=500, detail=user_message)


async def read_validated_upload(
    file: UploadFile,
    *,
    allowed_extensions: set[str],
    allowed_content_types: set[str],
    max_size_bytes: int,
) -> tuple[str, bytes]:
    filename = (file.filename or "").strip()
    if not filename or "." not in filename:
        raise HTTPException(400, "Archivo invalido.")

    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(400, "Formato de archivo no permitido.")

    if file.content_type not in allowed_content_types:
        raise HTTPException(400, "Tipo MIME de archivo no permitido.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(400, "El archivo esta vacio.")
    if len(file_bytes) > max_size_bytes:
        raise HTTPException(413, "El archivo excede el tamano maximo permitido.")

    return ext, file_bytes
