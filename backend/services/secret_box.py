from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from config import settings


SECRET_PREFIX = "enc:v1:"


class SecretBoxError(ValueError):
    """Raised when a stored application secret cannot be encrypted/decrypted."""


def is_encrypted_secret(value: str | None) -> bool:
    return bool(str(value or "").startswith(SECRET_PREFIX))


def _derived_local_key() -> bytes:
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _fernet() -> Fernet:
    configured = (settings.FIELD_ENCRYPTION_KEY or "").strip()
    if configured:
        key = configured.encode("utf-8")
    elif settings.is_local:
        key = _derived_local_key()
    else:
        raise SecretBoxError("FIELD_ENCRYPTION_KEY es obligatorio para cifrar secretos en este entorno.")
    try:
        return Fernet(key)
    except Exception as exc:
        raise SecretBoxError("FIELD_ENCRYPTION_KEY no es una llave Fernet valida.") from exc


def encrypt_secret(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if is_encrypted_secret(text):
        return text
    token = _fernet().encrypt(text.encode("utf-8")).decode("ascii")
    return f"{SECRET_PREFIX}{token}"


def decrypt_secret(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if not is_encrypted_secret(text):
        return text
    token = text[len(SECRET_PREFIX):]
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise SecretBoxError("No se pudo descifrar un secreto almacenado.") from exc
