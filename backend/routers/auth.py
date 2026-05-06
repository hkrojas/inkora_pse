from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from access_control import assert_login_allowed
import crud
import models
import schemas
import security
from api_dependencies import (
    get_current_user,
    get_db,
    require_internal_provisioning_token,
)
from api_utils import raise_internal_server_error
from rate_limit import limiter
from security import validate_password_strength

router = APIRouter(tags=["auth"])


@router.post("/token", response_model=schemas.Token)
@limiter.limit("10/minute")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = security.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        crud.log_auth_event(
            db, "user.login.failed",
            details=f"email={form_data.username}",
            ip_address=request.client.host if request.client else None,
        )
        raise HTTPException(401, "Credenciales invalidas")
    assert_login_allowed(user)

    user.last_login_at = datetime.now()
    db.commit()

    crud.log_auth_event(
        db, "user.login.success",
        user_id=user.id, entity_id=user.id,
        ip_address=request.client.host if request.client else None,
    )

    access_token = security.create_access_token_with_claims(user)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=schemas.CreateUserWithPasswordResponse)
def register_user(
    user: schemas.UserRegisterRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_provisioning_token),
):
    if crud.get_user_by_email_global(db, user.email):
        raise HTTPException(400, "Email registrado")

    tenant = crud.get_tenant(db, user.tenant_id)
    if not tenant:
        raise HTTPException(400, "Empresa (tenant) no encontrada")
    if not tenant.is_active:
        raise HTTPException(403, "No se puede registrar usuarios en una empresa inactiva.")

    try:
        db_user, temp_password = crud.create_user(
            db=db,
            user=user,
            forced_role="vendedor",
            is_superadmin=False,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return schemas.CreateUserWithPasswordResponse(
        user=db_user,
        temp_password=temp_password,
        message="Usuario creado. Comparte la contraseña temporal de forma segura — no se puede recuperar después.",
    )


@router.get("/users/me/", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.post("/users/me/change-password", status_code=200)
def change_password(
    data: schemas.ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Cambia la contraseña del usuario autenticado. Requiere la contraseña actual."""
    if data.new_password != data.confirm_password:
        raise HTTPException(400, "Las contraseñas nuevas no coinciden.")

    error = validate_password_strength(data.new_password, current_user.email)
    if error:
        raise HTTPException(400, error)

    if not security.verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(400, "La contraseña actual es incorrecta.")

    if security.verify_password(data.new_password, current_user.hashed_password):
        raise HTTPException(400, "La nueva contraseña debe ser diferente a la actual.")

    crud.change_user_password(db, current_user, data.new_password)
    crud.log_auth_event(db, "user.password_changed", user_id=current_user.id, entity_id=current_user.id)
    new_token = security.create_access_token_with_claims(current_user)
    return {"message": "Contraseña actualizada correctamente.", "access_token": new_token, "token_type": "bearer"}


@router.put("/users/profile", response_model=schemas.UserResponse)
async def update_user_profile(
    data: schemas.UserUpdateProfile,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)

    try:
        db.commit()
        db.refresh(current_user)
        return current_user
    except Exception as exc:
        db.rollback()
        raise_internal_server_error(
            "update_user_profile",
            "No se pudo actualizar el perfil.",
            exc,
        )
