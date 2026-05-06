"""crud/auth.py — Usuarios y autenticación."""
import random
import string
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

import models
import schemas
from access_control import normalize_role
from crud._base import pwd_context
from database import without_tenant_filter

# Chars sin ambigüedades: sin 0/O, 1/l/I
_SAFE_CHARS = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_temp_password(length: int = 12) -> str:
    return "".join(random.choices(_SAFE_CHARS, k=length))


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).options(joinedload(models.User.tenant)).filter(models.User.email == email).first()


def get_user_by_email_global(db: Session, email: str):
    query = db.query(models.User).options(joinedload(models.User.tenant)).filter(
        models.User.email == email
    )
    return without_tenant_filter(query).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).options(joinedload(models.User.tenant)).filter(models.User.id == user_id).first()


def _is_duplicate_email_error(exc: IntegrityError) -> bool:
    message = str(getattr(exc, "orig", exc)).lower()
    return "email" in message and (
        "unique" in message or "duplicate" in message
    )


def create_user(
    db: Session,
    user: schemas.UserRegisterRequest,
    *,
    forced_role: str = "vendedor",
    is_superadmin: bool = False,
) -> tuple[models.User, str]:
    """Crea usuario con password auto-generada. Devuelve (user, temp_password)."""
    temp_password = generate_temp_password()
    hashed_password = pwd_context.hash(temp_password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        nombre_completo=user.nombre_completo,
        rol=normalize_role(forced_role),
        is_superadmin=is_superadmin,
        tenant_id=user.tenant_id,
        must_change_password=True,
    )
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return get_user_by_id(db, db_user.id), temp_password
    except IntegrityError as exc:
        db.rollback()
        if _is_duplicate_email_error(exc):
            raise ValueError("Ya existe un usuario con ese email.") from exc
        raise


def change_user_password(db: Session, user: models.User, new_password: str) -> None:
    """Actualiza el hash del usuario y limpia el flag de cambio forzado."""
    user.hashed_password = pwd_context.hash(new_password)
    user.must_change_password = False
    user.password_changed_at = utc_now_naive()
    db.commit()


def log_auth_event(
    db: Session,
    action: str,
    user_id: int | None = None,
    entity_id: int | None = None,
    details: str | None = None,
    ip_address: str | None = None,
) -> None:
    """Registra un evento de seguridad en audit_logs."""
    entry = models.AuditLog(
        user_id=user_id,
        action=action,
        entity_type="user",
        entity_id=entity_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    try:
        db.commit()
    except Exception:
        db.rollback()
