from secrets import compare_digest
from typing import Optional

from fastapi import Depends, Header, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from access_control import (
    DOCUMENT_EMITTER_ROLES,
    PAYMENT_MANAGER_ROLES,
    TENANT_ADMIN_ROLES,
    assert_active_tenant_access,
    assert_user_has_roles,
)
import models
import security
from config import settings
from database import apply_tenant_context, get_db, reset_tenant_context

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """Valida el JWT y retorna el usuario actual."""
    user = security.get_current_user(db, token)
    return assert_active_tenant_access(user)


def get_db_tenant(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Sincroniza el tenant_id del JWT con la sesion SQL actual.
    """
    if not current_user.tenant_id:
        raise HTTPException(403, "El usuario autenticado no tiene tenant asociado.")

    apply_tenant_context(db, current_user.tenant_id)
    try:
        yield db
    finally:
        # No llamamos reset_tenant_context(token) porque el token fue creado
        # en un contexto async distinto (anyio threadpool) y reset() lanzaría
        # ValueError. Simplemente limpiamos el ContextVar directamente.
        from database import current_tenant_id
        current_tenant_id.set(None)


def require_admin(current_user: models.User = Depends(get_current_user)):
    assert_active_tenant_access(current_user)
    return assert_user_has_roles(
        current_user,
        TENANT_ADMIN_ROLES,
        detail="Solo administradores pueden realizar esta accion.",
    )


def require_document_emitter(
    current_user: models.User = Depends(get_current_user),
):
    assert_active_tenant_access(current_user)
    return assert_user_has_roles(
        current_user,
        DOCUMENT_EMITTER_ROLES,
        detail="No tiene permisos para emitir o anular documentos.",
    )


def require_payment_manager(
    current_user: models.User = Depends(get_current_user),
):
    assert_active_tenant_access(current_user)
    return assert_user_has_roles(
        current_user,
        PAYMENT_MANAGER_ROLES,
        detail="No tiene permisos para registrar pagos.",
    )


def require_internal_provisioning_token(
    x_internal_provisioning_token: Optional[str] = Header(
        default=None,
        alias="X-Internal-Provisioning-Token",
    ),
    x_internal_registration_token: Optional[str] = Header(
        default=None,
        alias="X-Internal-Registration-Token",
    ),
):
    configured_token = (
        settings.INTERNAL_PROVISIONING_TOKEN
        or settings.INTERNAL_REGISTRATION_TOKEN
        or ""
    ).strip()
    if not configured_token:
        raise HTTPException(
            status_code=403,
            detail=(
                "Registro publico deshabilitado. Use el flujo interno de aprovisionamiento."
            ),
        )

    provided_token = (
        x_internal_provisioning_token or x_internal_registration_token or ""
    )
    if not compare_digest(provided_token, configured_token):
        raise HTTPException(
            status_code=403,
            detail=(
                "Registro publico deshabilitado. Use el flujo interno de aprovisionamiento."
            ),
        )


def get_superadmin(current_user: models.User = Depends(get_current_user)):
    """Valida que el usuario tenga privilegios de Superadmin Global."""
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado: Se requieren privilegios de Superadmin.",
        )
    return current_user


def require_emission_allowed(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Bloquea la emisión fiscal si la suscripción del tenant está en mora o suspendida.
    Las cotizaciones nunca se bloquean (este guard solo se aplica a rutas de emisión fiscal).
    Superadmin siempre pasa.
    """
    if current_user.is_superadmin:
        return current_user

    from models.tenants import SUBSCRIPTION_STATUS_ACTIVE, SUBSCRIPTION_STATUS_TRIAL
    sub = db.query(models.Subscription).filter(
        models.Subscription.tenant_id == current_user.tenant_id
    ).first()

    if sub is None:
        return current_user  # sin suscripción configurada, no bloqueamos

    if sub.status in (SUBSCRIPTION_STATUS_ACTIVE, SUBSCRIPTION_STATUS_TRIAL, "grace"):
        return current_user

    if sub.status == "payment_required":
        raise HTTPException(
            status_code=402,
            detail={
                "code": "EMISSION_BLOCKED_PAYMENT_REQUIRED",
                "message": "La emisión de documentos fiscales está bloqueada por pago pendiente. Las cotizaciones siguen disponibles.",
                "subscription_status": sub.status,
                "contact": "contacto@inkora.pe",
            },
        )

    if sub.status == "suspended":
        raise HTTPException(
            status_code=402,
            detail={
                "code": "EMISSION_BLOCKED_SUSPENDED",
                "message": "Cuenta suspendida. Contacta a soporte para reactivar.",
                "subscription_status": sub.status,
                "contact": "contacto@inkora.pe",
            },
        )

    return current_user
