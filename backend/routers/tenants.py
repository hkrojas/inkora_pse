import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
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
from services import storage_service

router = APIRouter(tags=["tenants"])


@router.get("/tenant/", response_model=schemas.TenantResponse)
def get_my_tenant(
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    tenant = crud.get_tenant(db, current_user.tenant_id)
    if not tenant:
        raise HTTPException(404, "Empresa no encontrada")
    return tenant


@router.put("/tenant/", response_model=schemas.TenantResponse)
def update_my_tenant(
    data: schemas.TenantAdminUpdate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_admin),
):
    """Actualiza campos de contacto del tenant.
    Credenciales fiscales y datos maestros de empresa solo son editables por superadmin.
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
        (tenant and tenant.apisperu_token)
        or (current_user.apisperu_token)
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
