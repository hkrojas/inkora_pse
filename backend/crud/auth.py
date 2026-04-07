"""crud/auth.py — Usuarios y autenticación."""
from sqlalchemy.orm import Session, joinedload

import models
import schemas
from access_control import normalize_role
from crud._base import pwd_context


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).options(joinedload(models.User.tenant)).filter(models.User.email == email).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).options(joinedload(models.User.tenant)).filter(models.User.id == user_id).first()


def create_user(
    db: Session,
    user: schemas.UserRegisterRequest,
    *,
    forced_role: str = "vendedor",
    is_superadmin: bool = False,
):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        nombre_completo=user.nombre_completo,
        rol=normalize_role(forced_role),
        is_superadmin=is_superadmin,
        tenant_id=user.tenant_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return get_user_by_id(db, db_user.id)
