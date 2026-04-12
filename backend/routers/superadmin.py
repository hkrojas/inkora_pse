from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from access_control import normalize_role
import crud
import models
import schemas
from api_dependencies import get_db, get_superadmin
from api_utils import raise_internal_server_error
from security import get_password_hash
from services import facturacion_service, subscription_service

router = APIRouter(tags=["superadmin"])


class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    user_id: Optional[int] = None
    action: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


def _raise_token_validation_error(validation: dict) -> None:
    detail = validation.get("message") or "El token de ApisPeru no es valido."
    provider_detail = validation.get("provider_detail")
    if provider_detail:
        detail = f"{detail} Detalle proveedor: {provider_detail}"
    raise HTTPException(status_code=400, detail=detail)


@router.post(
    "/superadmin/validate/apisperu-token",
    response_model=schemas.ApisPeruTokenValidationResponse,
    summary="Validar token de ApisPeru",
)
def validate_apisperu_token_endpoint(
    data: schemas.ApisPeruTokenValidationRequest,
    admin: models.User = Depends(get_superadmin),
):
    """
    Valida un token de ApisPeru sin guardar cambios en BD ni emitir documentos.

    La validacion se infiere a partir de una llamada de prueba no destructiva
    al proveedor fiscal.
    """
    return facturacion_service.validate_apisperu_token(
        token=data.token,
        api_url=data.api_url,
        business_ruc=data.business_ruc,
    )


@router.post(
    "/superadmin/tenants",
    response_model=schemas.SuperadminTenantResponse,
    status_code=201,
    summary="Crear nuevo tenant",
)
def create_tenant_endpoint(
    data: schemas.SuperadminTenantCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """Crea un nuevo tenant (empresa). El superadmin puede incluir el token ApisPeru."""
    try:
        if data.apisperu_token and data.apisperu_token.strip():
            validation = facturacion_service.validate_apisperu_token(
                token=data.apisperu_token,
                api_url=data.apisperu_url,
                business_ruc=data.business_ruc,
            )
            if not validation["valid"]:
                _raise_token_validation_error(validation)

        tenant_create = schemas.TenantCreate(
            business_name=data.business_name,
            business_ruc=data.business_ruc,
            business_address=data.business_address,
        )
        tenant = crud.create_tenant(db, tenant_create)
        # Si se proporcionaron credenciales ApisPeru, actualizarlas de inmediato
        if data.apisperu_token or data.apisperu_url:
            extra = {}
            if data.apisperu_token:
                extra["apisperu_token"] = data.apisperu_token
            if data.apisperu_url:
                extra["apisperu_url"] = data.apisperu_url
            tenant = crud.update_tenant_saas(db, tenant.id, extra)
        return tenant
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise_internal_server_error("create_tenant_endpoint", "No se pudo crear el tenant.", exc)


@router.post(
    "/superadmin/tenants/{tenant_id}/users",
    response_model=schemas.UserResponse,
    status_code=201,
    summary="Crear usuario para un tenant",
)
def create_tenant_user_endpoint(
    tenant_id: int,
    data: schemas.SuperadminUserCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """Crea un usuario admin (u otro rol) para un tenant específico."""
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")

    existing = db.query(models.User).filter(models.User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese email.")

    rol = normalize_role(data.rol) if data.rol else "admin"
    new_user = models.User(
        email=data.email,
        nombre_completo=data.nombre_completo,
        hashed_password=get_password_hash(data.password),
        rol=rol,
        tenant_id=tenant_id,
    )
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as exc:
        db.rollback()
        raise_internal_server_error("create_tenant_user_endpoint", "No se pudo crear el usuario.", exc)


@router.get("/superadmin/tenants", response_model=List[schemas.SuperadminTenantResponse])
def list_all_tenants_endpoint(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    return crud.get_all_tenants(db, skip, limit)


@router.patch("/superadmin/tenants/{tenant_id}", response_model=schemas.SuperadminTenantResponse)
def update_tenant_saas_endpoint(
    tenant_id: int,
    updates: schemas.TenantSaaSUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    current_tenant = crud.get_tenant(db, tenant_id)
    if not current_tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")

    target_ruc = updates.business_ruc or current_tenant.business_ruc
    target_url = (
        updates.apisperu_url.strip()
        if updates.apisperu_url is not None and updates.apisperu_url.strip()
        else current_tenant.apisperu_url
    )
    token_was_provided = updates.apisperu_token is not None
    target_token = (
        updates.apisperu_token.strip()
        if token_was_provided and updates.apisperu_token is not None
        else current_tenant.apisperu_token
    )

    should_validate_token = False
    if token_was_provided and target_token:
        should_validate_token = True
    elif not token_was_provided and updates.business_ruc is not None and current_tenant.apisperu_token:
        should_validate_token = True
    elif not token_was_provided and updates.apisperu_url is not None and current_tenant.apisperu_token:
        should_validate_token = True

    if should_validate_token:
        validation = facturacion_service.validate_apisperu_token(
            token=target_token,
            api_url=target_url,
            business_ruc=target_ruc,
        )
        if not validation["valid"]:
            _raise_token_validation_error(validation)

    updated_tenant = crud.update_tenant_saas(
        db,
        tenant_id,
        updates.model_dump(exclude_unset=True),
    )
    return updated_tenant


@router.delete("/superadmin/tenants/{tenant_id}")
def delete_tenant_endpoint(
    tenant_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    try:
        result = crud.delete_tenant(db, tenant_id)
        if not result:
            raise HTTPException(status_code=404, detail="Tenant no encontrado.")
        return {"message": "Tenant eliminado correctamente"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise_internal_server_error(
            "delete_tenant_endpoint",
            "No se pudo eliminar el tenant.",
            exc,
        )


@router.get("/superadmin/usuarios", response_model=List[schemas.UserResponse])
def list_all_users_endpoint(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    return crud.get_all_users(db, skip, limit)


@router.patch("/users/{user_id}", response_model=schemas.UserResponse)
def update_user_endpoint(
    user_id: int,
    updates: schemas.UserAdminUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    update_data = updates.model_dump(exclude_unset=True)
    if "rol" in update_data and update_data["rol"] is not None:
        update_data["rol"] = normalize_role(update_data["rol"])
    if "tenant_id" in update_data and update_data["tenant_id"] is not None:
        tenant = crud.get_tenant(db, update_data["tenant_id"])
        if not tenant:
            raise HTTPException(status_code=400, detail="Tenant destino no encontrado")
    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
def delete_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    try:
        db.delete(user)
        db.commit()
        return {"message": "Usuario eliminado correctamente"}
    except Exception as exc:
        db.rollback()
        raise_internal_server_error(
            "delete_user_endpoint",
            "No se pudo eliminar el usuario.",
            exc,
        )


@router.get("/superadmin/audit-logs", response_model=List[AuditLogResponse])
def list_audit_logs_endpoint(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    return crud.get_audit_logs(db, skip, limit)


# ============================================================
# FASE 5: SUPERADMIN — CONTROL DE SUSCRIPCIONES SaaS
# ============================================================
# Todos los endpoints bajo /superadmin/tenants/{id}/...
# operan sobre el dominio SaaS (PrintFlow → tenant).
# No mezclar con el dominio operativo del tenant (Pago/cotizacion).


@router.get(
    "/superadmin/tenants/{tenant_id}/subscription",
    response_model=schemas.SubscriptionResponse,
    summary="Consultar estado de suscripcion de un tenant",
)
def get_tenant_subscription_endpoint(
    tenant_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """Devuelve el estado completo de la suscripcion SaaS de un tenant."""
    return subscription_service.get_subscription_status(db, tenant_id)


@router.post(
    "/superadmin/tenants/{tenant_id}/activate",
    response_model=schemas.SubscriptionResponse,
    summary="Activar tenant",
)
def activate_tenant_endpoint(
    tenant_id: int,
    request: schemas.ActivateTenantRequest,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """
    Activa el tenant: habilita acceso (is_active=True) y marca la suscripcion como active.
    Opcionalmente fija la fecha de vencimiento del ciclo de facturación.
    """
    return subscription_service.activate_tenant(db, tenant_id, request, admin)


@router.post(
    "/superadmin/tenants/{tenant_id}/suspend",
    response_model=schemas.SubscriptionResponse,
    summary="Suspender tenant",
)
def suspend_tenant_endpoint(
    tenant_id: int,
    request: schemas.SuspendTenantRequest,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """
    Suspende el tenant: bloquea acceso (is_active=False) y marca suscripcion como suspended.
    Los usuarios del tenant recibirán 403 hasta que sea reactivado.
    """
    return subscription_service.suspend_tenant(db, tenant_id, request, admin)


@router.post(
    "/superadmin/tenants/{tenant_id}/extend-access",
    response_model=schemas.SubscriptionResponse,
    summary="Extender acceso de tenant",
)
def extend_access_endpoint(
    tenant_id: int,
    request: schemas.ExtendAccessRequest,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """
    Extiende el acceso de un tenant fijando nueva fecha de vencimiento.
    Si el tenant estaba suspendido/expirado, se reactiva automáticamente.
    """
    return subscription_service.extend_access(db, tenant_id, request, admin)


@router.put(
    "/superadmin/tenants/{tenant_id}/founder-pricing",
    response_model=schemas.SubscriptionResponse,
    summary="Fijar precio fundador",
)
def set_founder_pricing_endpoint(
    tenant_id: int,
    request: schemas.SetFounderPricingRequest,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """
    Fija el precio fundador de un tenant (early adopter price).
    El precio fundador queda registrado y no debe subir al aumentar el precio público.
    """
    return subscription_service.set_founder_pricing(db, tenant_id, request, admin)


@router.patch(
    "/superadmin/tenants/{tenant_id}/subscription",
    response_model=schemas.SubscriptionResponse,
    summary="Actualizar suscripcion (admin avanzado)",
)
def update_subscription_endpoint(
    tenant_id: int,
    request: schemas.UpdateSubscriptionRequest,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """Actualización general de campos de suscripcion. Para uso admin avanzado."""
    return subscription_service.update_subscription_general(db, tenant_id, request, admin)


@router.post(
    "/superadmin/tenants/{tenant_id}/payments",
    response_model=schemas.SubscriptionPaymentResponse,
    status_code=201,
    summary="Registrar pago SaaS",
)
def register_saas_payment_endpoint(
    tenant_id: int,
    data: schemas.SubscriptionPaymentCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """
    Registra un pago SaaS recibido de un tenant a PrintFlow.

    DOMINIO: tenant → PrintFlow (SaaS). No es un cobro del tenant a sus clientes.
    Ver schemas.PagoCreate/PagoResponse para el dominio operativo del tenant.
    """
    return subscription_service.register_saas_payment(db, tenant_id, data, admin)


@router.get(
    "/superadmin/tenants/{tenant_id}/payments",
    response_model=List[schemas.SubscriptionPaymentResponse],
    summary="Listar pagos SaaS de un tenant",
)
def list_saas_payments_endpoint(
    tenant_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """Lista todos los pagos SaaS registrados para un tenant (PrintFlow cobra al tenant)."""
    return subscription_service.get_saas_payments(db, tenant_id, skip, limit)


@router.get(
    "/superadmin/tenants-detail",
    response_model=List[schemas.SuperadminTenantDetailResponse],
    summary="Listar tenants con estado de suscripcion",
)
def list_tenants_with_subscription_endpoint(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """
    Lista todos los tenants junto con su suscripcion SaaS actual.
    Útil para el panel superadmin de control de acceso.
    """
    return crud.get_all_tenants_with_subscription(db, skip, limit)


# ============================================================
# FASE 9: BETA CERRADA — PANEL OPERATIVO
# ============================================================


@router.get(
    "/superadmin/beta/resumen",
    response_model=List[schemas.BetaTenantSummary],
    summary="Panel de operaciones beta — resumen de todos los tenants",
)
def get_beta_resumen_endpoint(
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """
    Vista consolidada de todos los tenants para operar la beta cerrada.

    Devuelve en una sola llamada: estado de suscripcion, precios, uso de documentos,
    conteos de clientes/productos/usuarios, último pago SaaS y notas internas.

    Diseñado para 5-10 tenants piloto. No para analytics avanzados.
    """
    return crud.get_beta_resumen_data(db)


@router.get(
    "/superadmin/tenants/{tenant_id}/actividad",
    response_model=schemas.TenantActividadResponse,
    summary="Actividad operativa de un tenant piloto",
)
def get_tenant_actividad_endpoint(
    tenant_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """
    Devuelve métricas de uso detalladas de un tenant: cantidad de cotizaciones,
    documentos fiscales emitidos (total y último mes), guías, pagos, usuarios,
    clientes, productos y fecha del último documento.

    Útil para monitorear el avance de un cliente piloto en el launch workflow.
    """
    data = crud.get_tenant_actividad(db, tenant_id)
    if not data:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")
    return data


@router.patch(
    "/superadmin/tenants/{tenant_id}/notas",
    response_model=schemas.SubscriptionResponse,
    summary="Actualizar notas internas de un tenant",
)
def update_tenant_notas_endpoint(
    tenant_id: int,
    request: schemas.UpdateNotasRequest,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """
    Actualiza rápidamente las notas internas y/o el flag is_pilot de un tenant.

    Pensado para uso durante llamadas de soporte con clientes piloto:
    anota observaciones sin tener que enviar el payload completo de suscripcion.
    """
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")

    updates = request.model_dump(exclude_unset=True)
    return crud.update_subscription_fields(db, tenant_id, updates)
