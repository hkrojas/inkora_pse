from fastapi import APIRouter, Depends, HTTPException
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

router = APIRouter(tags=["auth"])


@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = security.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(401, "Credenciales invalidas")
    assert_login_allowed(user)

    access_token = security.create_access_token_with_claims(user)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=schemas.UserResponse)
def register_user(
    user: schemas.UserRegisterRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_provisioning_token),
):
    if crud.get_user_by_email(db, user.email):
        raise HTTPException(400, "Email registrado")

    tenant = crud.get_tenant(db, user.tenant_id)
    if not tenant:
        raise HTTPException(400, "Empresa (tenant) no encontrada")
    if not tenant.is_active:
        raise HTTPException(403, "No se puede registrar usuarios en una empresa inactiva.")

    return crud.create_user(
        db=db,
        user=user,
        forced_role="vendedor",
        is_superadmin=False,
    )


@router.get("/users/me/", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user


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
