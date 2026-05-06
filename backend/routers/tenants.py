import uuid

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import crud
import models
import schemas
from api_dependencies import (
    get_current_user,
    get_db,
    get_db_tenant,
    require_admin,
    require_internal_provisioning_token,
)
from api_utils import raise_internal_server_error, read_validated_upload
from config import settings
from security import validate_password_strength
from services.beta_feature_flags import normalize_fiscal_feature_flags
from services import storage_service

router = APIRouter(tags=["tenants"])


class SubscriptionStatusPublic(BaseModel):
    status: str
    billing_due_at: Optional[datetime] = None
    grace_until: Optional[datetime] = None
    emission_blocked: bool = False
    message: Optional[str] = None
    fiscal_feature_flags: dict[str, bool] = Field(default_factory=dict)


@router.get("/tenant/", response_model=schemas.TenantResponse)
def get_my_tenant(
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    tenant = crud.get_tenant(db, current_user.tenant_id)
    if not tenant:
        raise HTTPException(404, "Empresa no encontrada")
    return tenant


@router.get("/tenant/subscription-status", response_model=SubscriptionStatusPublic)
def get_my_subscription_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Estado simplificado de suscripción para el tenant. Usado por el banner de la UI."""
    if current_user.is_superadmin:
        return SubscriptionStatusPublic(
            status="active",
            emission_blocked=False,
            fiscal_feature_flags=normalize_fiscal_feature_flags(None),
        )

    sub = db.query(models.Subscription).filter(
        models.Subscription.tenant_id == current_user.tenant_id
    ).first()

    if not sub:
        return SubscriptionStatusPublic(
            status="active",
            emission_blocked=False,
            fiscal_feature_flags=normalize_fiscal_feature_flags(None),
        )

    BLOCKED_STATUSES = ("payment_required", "suspended")
    emission_blocked = sub.status in BLOCKED_STATUSES

    messages = {
        "trial": None,
        "active": None,
        "grace": f"Tu pago vence el {sub.billing_due_at.strftime('%d/%m/%Y') if sub.billing_due_at else '—'}. Regulariza para seguir emitiendo.",
        "payment_required": "La emisión fiscal está bloqueada por pago pendiente. Las cotizaciones siguen disponibles. Contacta a soporte.",
        "suspended": "Cuenta suspendida. Contacta a soporte para reactivar tu acceso.",
        "expired": "Tu suscripción ha expirado. Contacta a soporte.",
        "cancelled": "Tu suscripción fue cancelada. Contacta a soporte.",
    }

    return SubscriptionStatusPublic(
        status=sub.status,
        billing_due_at=sub.billing_due_at,
        grace_until=sub.grace_until,
        emission_blocked=emission_blocked,
        message=messages.get(sub.status),
        fiscal_feature_flags=normalize_fiscal_feature_flags(sub.beta_feature_flags),
    )


@router.put("/tenant/", response_model=schemas.TenantResponse)
def update_my_tenant(
    data: schemas.TenantAdminUpdate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_admin),
):
    """Actualiza campos operativos del tenant para admin local.
    Incluye razon social, domicilio fiscal, contacto seguro y preferencias de PDF.
    RUC y credenciales fiscales solo son editables por superadmin porque identifican
    al emisor ante SUNAT/APISPeru.
    """
    tenant = crud.update_tenant(db, current_user.tenant_id, data)
    if not tenant:
        raise HTTPException(404, "Empresa no encontrada")
    return tenant


@router.post("/tenants/", response_model=schemas.TenantResponse)
def create_tenant(
    tenant: schemas.TenantCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_provisioning_token),
):
    try:
        return crud.create_tenant(db, tenant)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise_internal_server_error(
            "create_tenant",
            "No se pudo crear la empresa.",
            exc,
        )


# ============================================================
# FASE 8: CHECKLIST DE ONBOARDING
# ============================================================


@router.get(
    "/onboarding/estado",
    response_model=schemas.OnboardingEstadoResponse,
    summary="Estado de onboarding del tenant",
)
def get_onboarding_estado(
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """
    Devuelve el checklist de onboarding del tenant con estado actual.
    Computa dinámicamente desde los datos reales del tenant.

    Items del checklist:
    1. empresa_configurada  — RUC, nombre y dirección cargados
    2. apisperu_configurado — Token de facturación electrónica activo
    3. primer_cliente       — Al menos un cliente registrado
    4. primer_producto      — Al menos un producto en el catálogo
    5. primer_documento     — Primera factura o boleta emitida
    """
    tenant_id = current_user.tenant_id
    tenant = crud.get_tenant(db, tenant_id)
    sub = crud.get_or_create_subscription(db, tenant_id)

    tiene_clientes = (
        db.query(models.Cliente)
        .filter(models.Cliente.tenant_id == tenant_id)
        .first()
    ) is not None

    tiene_productos = (
        db.query(models.Producto)
        .filter(models.Producto.tenant_id == tenant_id)
        .first()
    ) is not None

    tiene_documento_emitido = (
        db.query(models.Cotizacion)
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.document_kind == "fiscal_document",
        )
        .first()
    ) is not None

    empresa_configurada = bool(
        tenant
        and tenant.business_ruc
        and tenant.business_name
        and tenant.business_address
    )

    apisperu_configurado = bool(
        tenant and tenant.apisperu_token
    )

    checklist = [
        schemas.OnboardingChecklistItem(
            item="empresa_configurada",
            titulo="Configurar datos de empresa",
            descripcion="RUC, nombre y dirección fiscal completos",
            completado=empresa_configurada,
        ),
        schemas.OnboardingChecklistItem(
            item="apisperu_configurado",
            titulo="Configurar token de facturación",
            descripcion="Token ApisPeru para emisión de comprobantes electrónicos",
            completado=apisperu_configurado,
        ),
        schemas.OnboardingChecklistItem(
            item="primer_cliente",
            titulo="Registrar primer cliente",
            descripcion="Al menos un cliente registrado en el sistema",
            completado=tiene_clientes,
        ),
        schemas.OnboardingChecklistItem(
            item="primer_producto",
            titulo="Registrar primer producto",
            descripcion="Al menos un producto o servicio en el catálogo",
            completado=tiene_productos,
        ),
        schemas.OnboardingChecklistItem(
            item="primer_documento",
            titulo="Emitir primer documento fiscal",
            descripcion="Primera factura o boleta emitida con éxito a SUNAT",
            completado=tiene_documento_emitido,
        ),
    ]

    completados = sum(1 for c in checklist if c.completado)
    total = len(checklist)

    return schemas.OnboardingEstadoResponse(
        onboarding_status=sub.onboarding_status,
        completados=completados,
        total=total,
        porcentaje=int(completados / total * 100),
        checklist=checklist,
    )


@router.get("/users/", response_model=list[schemas.UserResponse])
def list_tenant_users(
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_admin),
):
    """Lista los usuarios del propio tenant. Solo admins."""
    return (
        db.query(models.User)
        .filter(models.User.tenant_id == current_user.tenant_id)
        .all()
    )


@router.post("/users/", response_model=schemas.CreateUserWithPasswordResponse)
def create_tenant_user(
    data: schemas.SuperadminUserCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_admin),
):
    """Admin del tenant crea un usuario en su propio tenant."""
    from access_control import normalize_role
    role = normalize_role(data.rol)
    if role == "superadmin":
        raise HTTPException(403, "No puedes crear usuarios superadmin.")
    # Admin solo puede crear roles ≤ admin
    role_rank = {"vendedor": 0, "operador": 1, "admin": 2}
    requester_rank = role_rank.get(current_user.rol, 0)
    target_rank = role_rank.get(role, 0)
    if target_rank > requester_rank:
        raise HTTPException(403, f"No puedes crear usuarios con rol '{role}'.")

    if crud.get_user_by_email_global(db, data.email):
        raise HTTPException(400, "Ya existe un usuario con ese email.")

    user_req = schemas.UserRegisterRequest(
        email=data.email,
        nombre_completo=data.nombre_completo,
        tenant_id=current_user.tenant_id,
    )
    try:
        db_user, temp_password = crud.create_user(db, user_req, forced_role=role)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return schemas.CreateUserWithPasswordResponse(
        user=db_user,
        temp_password=temp_password,
        message="Usuario creado. Comparte la contraseña temporal de forma segura — no se puede recuperar después.",
    )


@router.post("/users/{user_id}/reset-password", response_model=schemas.ResetPasswordResponse)
def admin_reset_user_password(
    user_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_admin),
):
    """Admin del tenant resetea la contraseña de un usuario de su propio tenant."""
    target = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.tenant_id == current_user.tenant_id,
    ).first()
    if not target:
        raise HTTPException(404, "Usuario no encontrado en tu empresa.")
    if target.is_superadmin:
        raise HTTPException(403, "No puedes resetear la contraseña de un superadmin.")

    result = crud.reset_user_password(db, user_id)
    crud.log_auth_event(
        db, "user.password_reset",
        user_id=current_user.id, entity_id=user_id,
        details=f"reset_by=admin:{current_user.email}",
    )
    return result


@router.post("/users/upload-logo")
async def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_admin),
):
    try:
        ext, validated_file_content = await read_validated_upload(
            file,
            allowed_extensions={"png", "jpg", "jpeg", "webp"},
            allowed_content_types={"image/png", "image/jpeg", "image/webp"},
            max_size_bytes=settings.MAX_LOGO_UPLOAD_BYTES,
        )

        unique_filename = f"logo_{uuid.uuid4()}.{ext}"
        public_url = await storage_service.upload_to_storage(
            file_bytes=validated_file_content,
            folder_name="logos",
            filename=unique_filename,
            content_type=file.content_type or "",
            return_public_url=True,
        )

        tenant = crud.get_tenant(db, current_user.tenant_id)
        if tenant:
            tenant.logo_filename = public_url
            db.commit()

        return {"url": public_url}
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise_internal_server_error(
            "upload_logo",
            "No se pudo subir el logo.",
            exc,
        )
