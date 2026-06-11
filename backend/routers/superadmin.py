from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from access_control import ROLE_SUPERADMIN, normalize_role
import crud
import models
import schemas
from api_dependencies import get_db, get_superadmin
from api_utils import raise_internal_server_error
from services import (
    beta_feature_flags,
    facturacion_service,
    secret_box,
    smartpse_client,
    smartpse_gre_credentials,
    subscription_service,
)

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


def _log_superadmin_action(
    db: Session,
    admin: models.User,
    action: str,
    *,
    entity_type: str,
    entity_id: int | None = None,
    details: str | None = None,
) -> None:
    crud.create_audit_log(
        db,
        user_id=admin.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )


def _normalize_tenant_user_role(role: str | None) -> str:
    normalized = normalize_role(role)
    if normalized == ROLE_SUPERADMIN:
        raise HTTPException(
            status_code=403,
            detail="No se pueden crear o actualizar usuarios tenant con rol superadmin.",
        )
    return normalized


def _update_user_as_superadmin(
    user_id: int,
    updates: schemas.SuperadminTenantUserUpdate,
    db: Session,
    admin: models.User,
):
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    update_data = updates.model_dump(exclude_unset=True)
    if "rol" in update_data and update_data["rol"] is not None:
        update_data["rol"] = _normalize_tenant_user_role(update_data["rol"])

    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    _log_superadmin_action(
        db,
        admin,
        "superadmin.user.updated",
        entity_type="user",
        entity_id=user.id,
        details=f"fields={','.join(sorted(update_data.keys()))}; target_tenant_id={user.tenant_id}",
    )
    return user


def _delete_user_as_superadmin(
    user_id: int,
    db: Session,
    admin: models.User,
):
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    target_email = user.email
    target_tenant_id = user.tenant_id
    try:
        db.delete(user)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise_internal_server_error(
            "delete_user_endpoint",
            "No se pudo eliminar el usuario.",
            exc,
        )

    _log_superadmin_action(
        db,
        admin,
        "superadmin.user.deleted",
        entity_type="user",
        entity_id=user_id,
        details=f"email={target_email}; target_tenant_id={target_tenant_id}",
    )
    return {"message": "Usuario eliminado correctamente"}


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


def _smartpse_environment(value: str | None) -> str:
    normalized = (value or "demo").strip().lower()
    if normalized not in {"demo", "produccion"}:
        raise HTTPException(status_code=422, detail="environment debe ser 'demo' o 'produccion'.")
    return normalized


def _update_smartpse_status(
    db: Session,
    tenant_id: int,
    *,
    status: str,
) -> models.Tenant:
    return crud.update_tenant_saas(
        db,
        tenant_id,
        {
            "smartpse_status": status,
            "smartpse_checked_at": datetime.now(),
        },
    )


def _parse_smartpse_date(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _coerce_optional_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _sanitize_smartpse_company(company: dict | None) -> dict:
    source = company or {}
    return {
        "id": str(source.get("id")) if source.get("id") is not None else None,
        "ruc": source.get("ruc"),
        "razon_social": source.get("razon_social") or source.get("business_name"),
        "environment": source.get("environment"),
        "active": source.get("active"),
        "estado": source.get("estado") or source.get("status"),
        "start_date": source.get("start_date") or source.get("fecha_inicio"),
        "end_date": source.get("end_date") or source.get("fecha_fin"),
        "firmas_usadas": _coerce_optional_int(
            source.get("firmas_usadas")
            or source.get("signatures_used")
            or source.get("firmas")
        ),
        "synced_at": datetime.now(),
    }


def _apply_smartpse_company_to_tenant(
    db: Session,
    tenant: models.Tenant,
    company: dict,
    *,
    fallback_environment: str | None = None,
):
    credentials = company.get("credenciales_cpe") or {}
    if company.get("id") is not None:
        tenant.smartpse_company_id = str(company.get("id"))
    tenant.smartpse_environment = (
        company.get("environment")
        or fallback_environment
        or tenant.smartpse_environment
        or "demo"
    )
    if credentials.get("usuario_secundaria"):
        tenant.smartpse_usuario_secundaria = credentials["usuario_secundaria"]
    if credentials.get("token_acceso"):
        tenant.smartpse_token_acceso = credentials["token_acceso"]
    if credentials.get("usuario_secundaria") and credentials.get("token_acceso"):
        tenant.smartpse_status = models.SMARTPSE_STATUS_OK
        tenant.smartpse_checked_at = datetime.now()
    tenant.smartpse_remote_active = company.get("active")
    tenant.smartpse_remote_estado = company.get("estado") or company.get("status")
    tenant.smartpse_remote_synced_at = datetime.now()
    tenant.smartpse_start_date = _parse_smartpse_date(
        company.get("start_date") or company.get("fecha_inicio")
    )
    tenant.smartpse_end_date = _parse_smartpse_date(
        company.get("end_date") or company.get("fecha_fin")
    )
    tenant.smartpse_firmas_usadas = _coerce_optional_int(
        company.get("firmas_usadas")
        or company.get("signatures_used")
        or company.get("firmas")
    )
    db.commit()
    db.refresh(tenant)
    return tenant


def _clear_smartpse_company_from_tenant(db: Session, tenant: models.Tenant) -> models.Tenant:
    tenant.smartpse_company_id = None
    tenant.smartpse_usuario_secundaria = None
    tenant.smartpse_token_acceso = None
    tenant.smartpse_status = models.SMARTPSE_STATUS_UNCHECKED
    tenant.smartpse_checked_at = None
    tenant.smartpse_remote_active = None
    tenant.smartpse_remote_estado = None
    tenant.smartpse_remote_synced_at = None
    tenant.smartpse_start_date = None
    tenant.smartpse_end_date = None
    tenant.smartpse_firmas_usadas = None
    db.commit()
    db.refresh(tenant)
    return tenant


def _require_smartpse_company_id(tenant: models.Tenant) -> str:
    company_id = str(tenant.smartpse_company_id or "").strip()
    if not company_id:
        raise HTTPException(
            status_code=400,
            detail="Tenant sin empresa Smart PSE asociada. Primero aprovisiona o sincroniza CPE.",
        )
    return company_id


def _find_smartpse_company_for_tenant(client, tenant: models.Tenant) -> dict:
    company_id = str(tenant.smartpse_company_id or "").strip()
    if company_id:
        return client.get_company(company_id)

    page = client.list_companies(search=tenant.business_ruc, page=1, per_page=1)
    companies = page.get("data") or []
    if not companies:
        raise HTTPException(status_code=404, detail="Empresa Smart PSE no encontrada para el tenant.")
    return companies[0]


def _update_smartpse_gre_status(
    db: Session,
    tenant: models.Tenant,
    *,
    status: str,
) -> models.Tenant:
    tenant.smartpse_gre_status = status
    tenant.smartpse_gre_checked_at = datetime.now()
    db.commit()
    db.refresh(tenant)
    return tenant


@router.post(
    "/superadmin/validate/smartpse-credentials",
    response_model=schemas.SmartPSECredentialsValidationResponse,
    summary="Validar credenciales Smart PSE",
)
def validate_smartpse_credentials_endpoint(
    data: schemas.SmartPSECredentialsValidationRequest,
    admin: models.User = Depends(get_superadmin),
):
    tenant_stub = type(
        "SmartPSETenantStub",
        (),
        {
            "id": data.business_ruc or "validation",
            "business_ruc": data.business_ruc,
            "smartpse_usuario_secundaria": data.usuario_secundaria,
            "smartpse_token_acceso": data.token_acceso,
        },
    )()
    return smartpse_client.get_default_client().validate_tenant_credentials(tenant_stub)


@router.post(
    "/superadmin/tenants/{tenant_id}/smartpse/provision",
    response_model=schemas.SuperadminTenantResponse,
    summary="Aprovisionar empresa Smart PSE",
)
def provision_tenant_smartpse_endpoint(
    tenant_id: int,
    data: schemas.SmartPSEProvisionRequest,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")

    environment = _smartpse_environment(data.environment)
    try:
        company = smartpse_client.get_default_client().provision_company(
            ruc=tenant.business_ruc,
            razon_social=tenant.business_name,
            environment=environment,
            start_date=data.start_date,
            end_date=data.end_date,
        )
    except smartpse_client.SmartPSEException as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    credentials = company.get("credenciales_cpe") or {}
    usuario_secundaria = credentials.get("usuario_secundaria")
    token_acceso = credentials.get("token_acceso")
    if not usuario_secundaria or not token_acceso:
        raise HTTPException(
            status_code=502,
            detail="Smart PSE no devolvio credenciales CPE para la empresa.",
        )

    updated_tenant = _apply_smartpse_company_to_tenant(
        db,
        tenant,
        company,
        fallback_environment=environment,
    )
    _log_superadmin_action(
        db,
        admin,
        "superadmin.tenant.smartpse_provisioned",
        entity_type="tenant",
        entity_id=tenant_id,
        details=f"environment={environment}; company_id={company.get('id')}",
    )
    return updated_tenant


@router.get(
    "/superadmin/smartpse/companies",
    response_model=schemas.SmartPSECompanyPageResponse,
    summary="Listar empresas Smart PSE",
)
def list_smartpse_companies_endpoint(
    search: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    admin: models.User = Depends(get_superadmin),
):
    try:
        result = smartpse_client.get_default_client().list_companies(
            search=search,
            page=page,
            per_page=per_page,
        )
    except smartpse_client.SmartPSEException as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        **result,
        "data": [_sanitize_smartpse_company(company) for company in result.get("data", [])],
    }


@router.post(
    "/superadmin/smartpse/companies",
    response_model=schemas.SmartPSECompanyResponse,
    status_code=201,
    summary="Crear empresa Smart PSE independiente",
)
def create_smartpse_company_endpoint(
    data: schemas.SmartPSECompanyCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    try:
        company = smartpse_client.get_default_client().provision_company(
            ruc=data.ruc,
            razon_social=data.razon_social,
            environment=data.environment,
            start_date=data.start_date,
            end_date=data.end_date,
        )
    except smartpse_client.SmartPSEException as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    sanitized = _sanitize_smartpse_company(company)
    _log_superadmin_action(
        db,
        admin,
        "superadmin.smartpse_company.created",
        entity_type="smartpse_company",
        entity_id=None,
        details=f"ruc={sanitized.get('ruc')}; company_id={sanitized.get('id')}; environment={sanitized.get('environment')}",
    )
    return sanitized


@router.post(
    "/superadmin/smartpse/sync-all",
    response_model=schemas.SmartPSESyncAllResponse,
    summary="Sincronizar todas las empresas Smart PSE asociadas",
)
def sync_all_smartpse_companies_endpoint(
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    tenants = (
        db.query(models.Tenant)
        .filter(models.Tenant.smartpse_company_id.isnot(None))
        .order_by(models.Tenant.id.asc())
        .all()
    )
    client = smartpse_client.get_default_client()
    items: list[dict] = []
    synced = 0
    failed = 0

    for tenant in tenants:
        company_id = str(tenant.smartpse_company_id or "").strip()
        if not company_id:
            continue
        try:
            company = _find_smartpse_company_for_tenant(client, tenant)
            updated = _apply_smartpse_company_to_tenant(db, tenant, company)
            synced += 1
            items.append(
                {
                    "tenant_id": tenant.id,
                    "company_id": updated.smartpse_company_id,
                    "status": "synced",
                    "message": None,
                }
            )
        except Exception:
            failed += 1
            db.rollback()
            items.append(
                {
                    "tenant_id": tenant.id,
                    "company_id": company_id,
                    "status": "failed",
                    "message": "No se pudo sincronizar empresa Smart PSE.",
                }
            )

    _log_superadmin_action(
        db,
        admin,
        "superadmin.smartpse_companies.sync_all",
        entity_type="smartpse_company",
        entity_id=None,
        details=f"total={len(tenants)}; synced={synced}; failed={failed}",
    )
    return {"total": len(tenants), "synced": synced, "failed": failed, "items": items}


@router.get(
    "/superadmin/tenants/{tenant_id}/smartpse/company",
    response_model=schemas.SmartPSECompanyResponse,
    summary="Ver empresa Smart PSE del tenant",
)
def get_tenant_smartpse_company_endpoint(
    tenant_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")
    try:
        company = _find_smartpse_company_for_tenant(smartpse_client.get_default_client(), tenant)
    except smartpse_client.SmartPSEException as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _sanitize_smartpse_company(company)


@router.get(
    "/superadmin/tenants/{tenant_id}/smartpse/audit-logs",
    response_model=List[AuditLogResponse],
    summary="Listar auditoria Smart PSE del tenant",
)
def list_tenant_smartpse_audit_logs_endpoint(
    tenant_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")
    return (
        db.query(models.AuditLog)
        .filter(
            models.AuditLog.entity_type == "tenant",
            models.AuditLog.entity_id == tenant_id,
            models.AuditLog.action.ilike("%smartpse%"),
        )
        .order_by(models.AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )


@router.post(
    "/superadmin/tenants/{tenant_id}/smartpse/sync",
    response_model=schemas.SuperadminTenantResponse,
    summary="Sincronizar empresa Smart PSE del tenant",
)
def sync_tenant_smartpse_company_endpoint(
    tenant_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")
    try:
        company = _find_smartpse_company_for_tenant(smartpse_client.get_default_client(), tenant)
    except smartpse_client.SmartPSEException as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    updated_tenant = _apply_smartpse_company_to_tenant(db, tenant, company)
    _log_superadmin_action(
        db,
        admin,
        "superadmin.tenant.smartpse_synced",
        entity_type="tenant",
        entity_id=tenant_id,
        details=f"company_id={updated_tenant.smartpse_company_id}; environment={updated_tenant.smartpse_environment}",
    )
    return updated_tenant


@router.put(
    "/superadmin/tenants/{tenant_id}/smartpse/credentials",
    response_model=schemas.SuperadminTenantResponse,
    summary="Rotar credenciales CPE Smart PSE del tenant",
)
def update_tenant_smartpse_credentials_endpoint(
    tenant_id: int,
    data: schemas.SmartPSETenantCredentialsUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")

    if data.company_id is not None:
        tenant.smartpse_company_id = data.company_id
    if data.environment is not None:
        tenant.smartpse_environment = _smartpse_environment(data.environment)
    elif not tenant.smartpse_environment:
        tenant.smartpse_environment = "demo"
    tenant.smartpse_usuario_secundaria = data.usuario_secundaria
    tenant.smartpse_token_acceso = data.token_acceso
    tenant.smartpse_status = models.SMARTPSE_STATUS_UNCHECKED
    tenant.smartpse_checked_at = None
    db.commit()
    db.refresh(tenant)

    _log_superadmin_action(
        db,
        admin,
        "superadmin.tenant.smartpse_credentials_rotated",
        entity_type="tenant",
        entity_id=tenant_id,
        details=f"company_id={tenant.smartpse_company_id}; environment={tenant.smartpse_environment}",
    )
    return tenant


@router.patch(
    "/superadmin/tenants/{tenant_id}/smartpse/company",
    response_model=schemas.SuperadminTenantResponse,
    summary="Actualizar empresa Smart PSE del tenant",
)
def update_tenant_smartpse_company_endpoint(
    tenant_id: int,
    data: schemas.SmartPSECompanyUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")
    company_id = _require_smartpse_company_id(tenant)
    payload = data.model_dump(exclude_unset=True)
    try:
        company = smartpse_client.get_default_client().update_company(company_id, payload)
    except smartpse_client.SmartPSEException as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    updated_tenant = _apply_smartpse_company_to_tenant(db, tenant, company)
    _log_superadmin_action(
        db,
        admin,
        "superadmin.tenant.smartpse_company_updated",
        entity_type="tenant",
        entity_id=tenant_id,
        details=f"fields={','.join(sorted(payload.keys()))}; company_id={company_id}",
    )
    return updated_tenant


@router.delete(
    "/superadmin/tenants/{tenant_id}/smartpse/company",
    response_model=schemas.SmartPSEDeleteResponse,
    summary="Eliminar empresa Smart PSE asociada al tenant",
)
def delete_tenant_smartpse_company_endpoint(
    tenant_id: int,
    confirm_company_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")
    company_id = _require_smartpse_company_id(tenant)
    if str(confirm_company_id).strip() != company_id:
        raise HTTPException(status_code=422, detail="Confirmacion de company id no coincide.")

    try:
        smartpse_client.get_default_client().delete_company(company_id)
    except smartpse_client.SmartPSEException as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    _clear_smartpse_company_from_tenant(db, tenant)
    _log_superadmin_action(
        db,
        admin,
        "superadmin.tenant.smartpse_company_deleted",
        entity_type="tenant",
        entity_id=tenant_id,
        details=f"company_id={company_id}",
    )
    return {"deleted": True, "company_id": company_id}


@router.post(
    "/superadmin/tenants/{tenant_id}/smartpse/activation",
    response_model=schemas.SuperadminTenantResponse,
    summary="Activar o desactivar empresa Smart PSE del tenant",
)
def toggle_tenant_smartpse_activation_endpoint(
    tenant_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")
    company_id = _require_smartpse_company_id(tenant)
    try:
        company = smartpse_client.get_default_client().toggle_company_activation(company_id)
    except smartpse_client.SmartPSEException as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    updated_tenant = _apply_smartpse_company_to_tenant(db, tenant, company)
    _log_superadmin_action(
        db,
        admin,
        "superadmin.tenant.smartpse_activation_toggled",
        entity_type="tenant",
        entity_id=tenant_id,
        details=f"company_id={company_id}; active={updated_tenant.smartpse_remote_active}",
    )
    return updated_tenant


@router.post(
    "/superadmin/tenants/{tenant_id}/smartpse/check",
    response_model=schemas.SmartPSECredentialsValidationResponse,
    summary="Verificar credenciales Smart PSE del tenant",
)
def check_tenant_smartpse_endpoint(
    tenant_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")

    result = smartpse_client.get_default_client().validate_tenant_credentials(tenant)
    _update_smartpse_status(
        db,
        tenant_id,
        status=models.SMARTPSE_STATUS_OK if result.get("valid") else models.SMARTPSE_STATUS_INVALID,
    )
    _log_superadmin_action(
        db,
        admin,
        "superadmin.tenant.smartpse_checked",
        entity_type="tenant",
        entity_id=tenant_id,
        details=f"valid={result.get('valid')}",
    )
    return result


@router.put(
    "/superadmin/tenants/{tenant_id}/smartpse/gre-credentials",
    response_model=schemas.SuperadminTenantResponse,
    summary="Guardar credenciales SUNAT GRE para Smart PSE",
)
def update_tenant_smartpse_gre_credentials_endpoint(
    tenant_id: int,
    data: schemas.SmartPSEGreCredentialsUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")

    try:
        tenant.smartpse_gre_sol_username = smartpse_gre_credentials.normalize_sol_username(
            data.sol_username
        )
        tenant.smartpse_gre_sol_password_enc = secret_box.encrypt_secret(data.sol_password)
        tenant.smartpse_gre_client_id = data.client_id.strip()
        tenant.smartpse_gre_client_secret_enc = secret_box.encrypt_secret(data.client_secret)
        tenant.smartpse_gre_status = models.SMARTPSE_GRE_STATUS_UNCHECKED
        tenant.smartpse_gre_checked_at = None
        db.commit()
        db.refresh(tenant)
    except secret_box.SecretBoxError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    _log_superadmin_action(
        db,
        admin,
        "superadmin.tenant.smartpse_gre_credentials_updated",
        entity_type="tenant",
        entity_id=tenant_id,
        details="fields=sol_username,sol_password,client_id,client_secret",
    )
    return tenant


@router.post(
    "/superadmin/tenants/{tenant_id}/smartpse/gre-credentials/check",
    response_model=schemas.SmartPSEGreCredentialsValidationResponse,
    summary="Verificar credenciales SUNAT GRE para Smart PSE",
)
def check_tenant_smartpse_gre_credentials_endpoint(
    tenant_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")

    result = smartpse_gre_credentials.validate_tenant_gre_credentials(tenant)
    _update_smartpse_gre_status(
        db,
        tenant,
        status=models.SMARTPSE_GRE_STATUS_OK
        if result.get("valid")
        else models.SMARTPSE_GRE_STATUS_INVALID,
    )
    _log_superadmin_action(
        db,
        admin,
        "superadmin.tenant.smartpse_gre_checked",
        entity_type="tenant",
        entity_id=tenant_id,
        details=f"valid={result.get('valid')}",
    )
    return result


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
        _log_superadmin_action(
            db,
            admin,
            "superadmin.tenant.created",
            entity_type="tenant",
            entity_id=tenant.id,
            details=f"business_ruc={tenant.business_ruc}",
        )
        return tenant
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise_internal_server_error("create_tenant_endpoint", "No se pudo crear el tenant.", exc)


@router.post(
    "/superadmin/tenants/{tenant_id}/users",
    response_model=schemas.CreateUserWithPasswordResponse,
    status_code=201,
    summary="Crear usuario para un tenant",
)
def create_tenant_user_endpoint(
    tenant_id: int,
    data: schemas.SuperadminUserCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """Crea un usuario para un tenant. Genera la contraseña temporal automáticamente."""
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")

    existing = crud.get_user_by_email_global(db, data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese email.")

    rol = _normalize_tenant_user_role(data.rol) if data.rol else "admin"
    try:
        user_req = schemas.UserRegisterRequest(
            email=data.email,
            nombre_completo=data.nombre_completo,
            tenant_id=tenant_id,
        )
        new_user, temp_password = crud.create_user(
            db,
            user_req,
            forced_role=rol,
        )
        _log_superadmin_action(
            db,
            admin,
            "superadmin.user.created",
            entity_type="user",
            entity_id=new_user.id,
            details=f"target_tenant_id={tenant_id}; role={rol}",
        )
        return schemas.CreateUserWithPasswordResponse(
            user=new_user,
            temp_password=temp_password,
            message="Usuario creado. Comparte la contraseña temporal de forma segura — no se puede recuperar después.",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise_internal_server_error("create_tenant_user_endpoint", "No se pudo crear el usuario.", exc)


@router.get("/superadmin/tenants", response_model=List[schemas.SuperadminTenantResponse])
def list_all_tenants_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=1000),
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    return crud.get_all_tenants(db, skip, limit)


@router.get(
    "/superadmin/tenants-page",
    response_model=schemas.SuperadminTenantPageResponse,
)
def list_tenants_page_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    q: str | None = Query(default=None, max_length=100),
    gre_status: str | None = Query(default=None),
    active_status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    return crud.get_tenants_page(
        db,
        skip=skip,
        limit=limit,
        q=q,
        gre_status=gre_status,
        active_status=active_status,
    )


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
    _log_superadmin_action(
        db,
        admin,
        "superadmin.tenant.updated",
        entity_type="tenant",
        entity_id=tenant_id,
        details=f"fields={','.join(sorted(updates.model_dump(exclude_unset=True).keys()))}",
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
        _log_superadmin_action(
            db,
            admin,
            "superadmin.tenant.deleted",
            entity_type="tenant",
            entity_id=tenant_id,
        )
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


@router.patch("/superadmin/users/{user_id}", response_model=schemas.UserResponse)
def update_superadmin_user_endpoint(
    user_id: int,
    updates: schemas.SuperadminTenantUserUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    return _update_user_as_superadmin(user_id, updates, db, admin)


@router.patch(
    "/users/{user_id}",
    response_model=schemas.UserResponse,
    deprecated=True,
    include_in_schema=False,
)
def update_user_legacy_endpoint(
    user_id: int,
    updates: schemas.SuperadminTenantUserUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    return _update_user_as_superadmin(user_id, updates, db, admin)


@router.delete("/superadmin/users/{user_id}")
def delete_superadmin_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    return _delete_user_as_superadmin(user_id, db, admin)


@router.delete(
    "/users/{user_id}",
    deprecated=True,
    include_in_schema=False,
)
def delete_user_legacy_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    return _delete_user_as_superadmin(user_id, db, admin)


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
# operan sobre el dominio SaaS (Inkora → tenant).
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
    subscription = subscription_service.activate_tenant(db, tenant_id, request, admin)
    _log_superadmin_action(
        db,
        admin,
        "superadmin.subscription.activated",
        entity_type="tenant",
        entity_id=tenant_id,
        details=f"status={subscription.status}",
    )
    return subscription


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
    subscription = subscription_service.suspend_tenant(db, tenant_id, request, admin)
    _log_superadmin_action(
        db,
        admin,
        "superadmin.subscription.suspended",
        entity_type="tenant",
        entity_id=tenant_id,
        details=f"status={subscription.status}",
    )
    return subscription


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
    subscription = subscription_service.extend_access(db, tenant_id, request, admin)
    _log_superadmin_action(
        db,
        admin,
        "superadmin.subscription.extended",
        entity_type="tenant",
        entity_id=tenant_id,
        details=f"billing_due_at={subscription.billing_due_at}",
    )
    return subscription


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
    subscription = subscription_service.set_founder_pricing(db, tenant_id, request, admin)
    _log_superadmin_action(
        db,
        admin,
        "superadmin.subscription.pricing_updated",
        entity_type="tenant",
        entity_id=tenant_id,
        details=f"founder_price={subscription.founder_price}; current_price={subscription.current_price}",
    )
    return subscription


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
    subscription = subscription_service.update_subscription_general(db, tenant_id, request, admin)
    _log_superadmin_action(
        db,
        admin,
        "superadmin.subscription.updated",
        entity_type="tenant",
        entity_id=tenant_id,
        details=f"fields={','.join(sorted(request.model_dump(exclude_unset=True).keys()))}",
    )
    return subscription


@router.get(
    "/superadmin/tenants/{tenant_id}/fiscal-flags",
    response_model=schemas.FiscalFeatureFlagsResponse,
    summary="Ver flags fiscales beta de un tenant",
)
def get_tenant_fiscal_flags_endpoint(
    tenant_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")
    subscription = crud.get_or_create_subscription(db, tenant_id)
    return schemas.FiscalFeatureFlagsResponse(
        tenant_id=tenant_id,
        flags=beta_feature_flags.subscription_feature_flags(subscription),
        definitions=beta_feature_flags.feature_definitions_payload(),
    )


@router.put(
    "/superadmin/tenants/{tenant_id}/fiscal-flags",
    response_model=schemas.FiscalFeatureFlagsResponse,
    summary="Actualizar flags fiscales beta de un tenant",
)
def update_tenant_fiscal_flags_endpoint(
    tenant_id: int,
    request: schemas.UpdateFiscalFeatureFlagsRequest,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")

    try:
        flags = beta_feature_flags.validate_fiscal_feature_flags(request.flags)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    subscription = crud.update_subscription_fields(
        db,
        tenant_id,
        {"beta_feature_flags": flags},
    )
    enabled_keys = sorted(key for key, enabled in flags.items() if enabled)
    _log_superadmin_action(
        db,
        admin,
        "superadmin.subscription.fiscal_flags_updated",
        entity_type="tenant",
        entity_id=tenant_id,
        details=f"enabled={','.join(enabled_keys) if enabled_keys else 'none'}",
    )
    return schemas.FiscalFeatureFlagsResponse(
        tenant_id=tenant_id,
        flags=beta_feature_flags.subscription_feature_flags(subscription),
        definitions=beta_feature_flags.feature_definitions_payload(),
    )


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
    Registra un pago SaaS recibido de un tenant a Inkora.

    DOMINIO: tenant → Inkora (SaaS). No es un cobro del tenant a sus clientes.
    Ver schemas.PagoCreate/PagoResponse para el dominio operativo del tenant.
    """
    payment = subscription_service.register_saas_payment(db, tenant_id, data, admin)
    _log_superadmin_action(
        db,
        admin,
        "superadmin.subscription_payment.created",
        entity_type="subscription_payment",
        entity_id=payment.id,
        details=f"tenant_id={tenant_id}; amount={payment.amount}",
    )
    return payment


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
    """Lista todos los pagos SaaS registrados para un tenant (Inkora cobra al tenant)."""
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
    subscription = crud.update_subscription_fields(db, tenant_id, updates)
    _log_superadmin_action(
        db,
        admin,
        "superadmin.subscription.notes_updated",
        entity_type="tenant",
        entity_id=tenant_id,
        details=f"fields={','.join(sorted(updates.keys()))}",
    )
    return subscription


# ============================================================
# USUARIOS POR TENANT — VISIBILIDAD Y GESTIÓN
# ============================================================


@router.get(
    "/superadmin/tenants/{tenant_id}/users-detail",
    response_model=List[schemas.UserDetailResponse],
    summary="Usuarios del tenant con métricas de emisión",
)
def get_tenant_users_detail_endpoint(
    tenant_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """Lista los usuarios de un tenant con sus conteos de documentos por tipo."""
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")
    return crud.get_tenant_users_with_metrics(db, tenant_id)


@router.patch(
    "/superadmin/users/{user_id}/toggle-active",
    response_model=schemas.UserResponse,
    summary="Activar o bloquear un usuario",
)
def toggle_user_active_endpoint(
    user_id: int,
    request: schemas.ToggleUserActiveRequest,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """Activa o bloquea el acceso de un usuario sin eliminarlo."""
    user = crud.toggle_user_active(db, user_id, request.is_active)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    _log_superadmin_action(
        db,
        admin,
        "superadmin.user.active_changed",
        entity_type="user",
        entity_id=user_id,
        details=f"is_active={request.is_active}; target_tenant_id={user.tenant_id}",
    )
    return user


@router.post(
    "/superadmin/users/{user_id}/reset-password",
    response_model=schemas.ResetPasswordResponse,
    summary="Resetear contraseña de un usuario",
)
def reset_user_password_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """Genera una contraseña temporal aleatoria para el usuario. Mostrarla al cliente de forma segura."""
    result = crud.reset_user_password(db, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    _log_superadmin_action(
        db,
        admin,
        "superadmin.user.password_reset",
        entity_type="user",
        entity_id=user_id,
        details=f"reset_by={admin.email}",
    )
    return result


# ============================================================
# EMISSION ERRORS Y HEALTH CHECK APISPERU
# ============================================================


@router.get(
    "/superadmin/tenants/{tenant_id}/emission-errors",
    response_model=List[schemas.EmissionErrorResponse],
    summary="Últimos errores de emisión de un tenant",
)
def get_tenant_emission_errors_endpoint(
    tenant_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """Devuelve los jobs de emisión fallidos más recientes del tenant."""
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")
    return crud.get_tenant_emission_errors(db, tenant_id, limit)


@router.post(
    "/superadmin/tenants/{tenant_id}/check-token-health",
    response_model=schemas.TokenHealthResponse,
    summary="Verificar token ApisPeru de un tenant",
)
def check_tenant_token_health_endpoint(
    tenant_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """Llama a ApisPeru con el token guardado del tenant y actualiza su estado de salud."""
    return crud.check_apisperu_token_health(db, tenant_id)


@router.post(
    "/superadmin/check-all-tokens",
    response_model=List[schemas.TokenHealthResponse],
    summary="Verificar todos los tokens ApisPeru",
)
def check_all_tokens_health_endpoint(
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """Verifica el token ApisPeru de todos los tenants que tienen uno configurado."""
    return crud.check_all_apisperu_tokens(db)


# ============================================================
# FASE 2 — Limites de emision por tenant/usuario
# ============================================================


@router.get(
    "/superadmin/tenants/{tenant_id}/limits",
    response_model=schemas.UsageLimitsWithUsage,
    summary="Listar limites del tenant con uso actual",
)
def list_tenant_limits_endpoint(
    tenant_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """Devuelve limites configurados y uso actual de cada uno."""
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")
    limits = crud.get_tenant_limits(db, tenant_id)
    usage = crud.build_tenant_usage_report(db, tenant_id)
    return {"limits": limits, "usage": usage}


@router.put(
    "/superadmin/tenants/{tenant_id}/limits",
    response_model=List[schemas.UsageLimitResponse],
    summary="Upsert bulk de limites del tenant",
)
def upsert_tenant_limits_endpoint(
    tenant_id: int,
    payload: schemas.UsageLimitsBulkUpsert,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    """Crea o actualiza multiples limites para el tenant. max_count<=0 elimina el limite."""
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")

    user_ids = {item.user_id for item in payload.limits if item.user_id is not None}
    if user_ids:
        owned_user_ids = {
            row[0]
            for row in db.query(models.User.id).filter(
                models.User.tenant_id == tenant_id,
                models.User.id.in_(user_ids),
            ).all()
        }
        missing = user_ids - owned_user_ids
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Los usuarios {sorted(missing)} no pertenecen al tenant {tenant_id}.",
            )

    items = [item.model_dump() for item in payload.limits]
    limits = crud.upsert_tenant_limits(db, tenant_id, items)
    _log_superadmin_action(
        db,
        admin,
        "superadmin.usage_limits.upserted",
        entity_type="tenant",
        entity_id=tenant_id,
        details=f"count={len(items)}",
    )
    return limits


@router.delete(
    "/superadmin/limits/{limit_id}",
    summary="Eliminar un limite de emision",
)
def delete_limit_endpoint(
    limit_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    removed = crud.delete_limit(db, limit_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Limite no encontrado.")
    _log_superadmin_action(
        db,
        admin,
        "superadmin.usage_limit.deleted",
        entity_type="usage_limit",
        entity_id=limit_id,
    )
    return {"deleted": True, "limit_id": limit_id}


@router.post(
    "/superadmin/guias/{guia_id}/smartpse/reconcile",
    response_model=schemas.GuiaRemisionResponse,
    summary="Conciliar manualmente una guia Smart PSE",
)
def reconcile_smartpse_guia_endpoint(
    guia_id: int,
    request: schemas.SmartPSEGuideReconcileRequest,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    guia = db.query(models.GuiaRemision).filter(models.GuiaRemision.id == guia_id).first()
    if not guia:
        raise HTTPException(status_code=404, detail="Guia de remision no encontrada.")

    if request.mark_as_emitida and not (request.cdr_url or "").strip():
        raise HTTPException(
            status_code=422,
            detail="Para marcar la guia como emitida se requiere cdr_url.",
        )

    if request.sunat_hash is not None:
        guia.sunat_hash = request.sunat_hash.strip() or None
    if request.sunat_ticket is not None:
        guia.sunat_ticket = request.sunat_ticket.strip() or None
    if request.cdr_url is not None:
        guia.sunat_cdr_url = request.cdr_url.strip() or None
    if request.provider_response is not None:
        guia.provider_response = request.provider_response

    guia.sunat_status_checked_at = datetime.now()
    if request.mark_as_emitida:
        guia.estado = "emitida"
    elif guia.estado != "emitida":
        guia.estado = "pendiente_smartpse"

    db.commit()
    db.refresh(guia)
    _log_superadmin_action(
        db,
        admin,
        "superadmin.guia.smartpse_reconciled",
        entity_type="guia_remision",
        entity_id=guia.id,
        details=(
            f"tenant_id={guia.tenant_id}; estado={guia.estado}; "
            f"has_cdr={bool(guia.sunat_cdr_url)}"
        ),
    )
    return guia
