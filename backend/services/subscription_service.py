"""
subscription_service.py — Fase 5: Superadmin / SaaS Billing Domain

Lógica de negocio para control interno de acceso y pagos SaaS de Inkora.

SEPARACIÓN DE DOMINIOS:
  - Este servicio opera sobre Subscription y SubscriptionPayment.
  - Subscription/SubscriptionPayment → Inkora cobra al tenant (SaaS).
  - Pago                             → tenant cobra a su cliente (operativo).
  Nunca mezclar estos dos dominios.
"""

from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

import crud
import models
import schemas


# ---------------------------------------------------------------------------
# Constantes de estado (sincronizadas con models.py)
# ---------------------------------------------------------------------------

STATUS_ACTIVE = models.SUBSCRIPTION_STATUS_ACTIVE
STATUS_SUSPENDED = models.SUBSCRIPTION_STATUS_SUSPENDED
STATUS_TRIAL = models.SUBSCRIPTION_STATUS_TRIAL
STATUS_EXPIRED = models.SUBSCRIPTION_STATUS_EXPIRED
STATUS_CANCELLED = models.SUBSCRIPTION_STATUS_CANCELLED

ONBOARDING_COMPLETED = models.ONBOARDING_STATUS_COMPLETED
ONBOARDING_IN_PROGRESS = models.ONBOARDING_STATUS_IN_PROGRESS
ONBOARDING_NOT_STARTED = models.ONBOARDING_STATUS_NOT_STARTED

VALID_STATUSES = {STATUS_ACTIVE, STATUS_SUSPENDED, STATUS_TRIAL, STATUS_EXPIRED, STATUS_CANCELLED}


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _get_tenant_or_404(db: Session, tenant_id: int) -> models.Tenant:
    tenant = crud.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")
    return tenant


def _get_subscription_or_create(db: Session, tenant_id: int) -> models.Subscription:
    return crud.get_or_create_subscription(db, tenant_id)


# ---------------------------------------------------------------------------
# Operaciones de acceso
# ---------------------------------------------------------------------------

def activate_tenant(
    db: Session,
    tenant_id: int,
    request: schemas.ActivateTenantRequest,
    admin_user: models.User,
) -> models.Subscription:
    """
    Activa un tenant: marca is_active=True en Tenant y status=active en Subscription.
    Opcionalmente fija la fecha de vencimiento del ciclo de facturación.
    """
    tenant = _get_tenant_or_404(db, tenant_id)

    tenant.is_active = True

    updates: dict = {"status": STATUS_ACTIVE}
    if request.billing_due_at is not None:
        updates["billing_due_at"] = request.billing_due_at
    if request.notes_internal is not None:
        updates["notes_internal"] = request.notes_internal
    if not crud.get_subscription_by_tenant(db, tenant_id) or \
            crud.get_subscription_by_tenant(db, tenant_id).billing_started_at is None:
        updates["billing_started_at"] = datetime.now()

    db.commit()
    return crud.update_subscription_fields(db, tenant_id, updates)


def suspend_tenant(
    db: Session,
    tenant_id: int,
    request: schemas.SuspendTenantRequest,
    admin_user: models.User,
) -> models.Subscription:
    """
    Suspende un tenant: marca is_active=False en Tenant y status=suspended en Subscription.
    El tenant no podrá acceder al sistema hasta ser reactivado.
    """
    tenant = _get_tenant_or_404(db, tenant_id)

    tenant.is_active = False

    updates: dict = {"status": STATUS_SUSPENDED}
    if request.notes_internal is not None:
        updates["notes_internal"] = request.notes_internal

    db.commit()
    return crud.update_subscription_fields(db, tenant_id, updates)


def extend_access(
    db: Session,
    tenant_id: int,
    request: schemas.ExtendAccessRequest,
    admin_user: models.User,
) -> models.Subscription:
    """
    Extiende el acceso de un tenant fijando una nueva fecha de vencimiento.
    Si el tenant estaba suspendido por vencimiento, lo reactiva.
    """
    tenant = _get_tenant_or_404(db, tenant_id)
    sub = _get_subscription_or_create(db, tenant_id)

    updates: dict = {"billing_due_at": request.billing_due_at}
    if request.grace_until is not None:
        updates["grace_until"] = request.grace_until
    if request.notes_internal is not None:
        updates["notes_internal"] = request.notes_internal

    # Si estaba suspendido/expirado, reactivar automáticamente al extender
    if sub.status in (STATUS_SUSPENDED, STATUS_EXPIRED):
        updates["status"] = STATUS_ACTIVE
        tenant.is_active = True
        db.commit()

    return crud.update_subscription_fields(db, tenant_id, updates)


# ---------------------------------------------------------------------------
# Precios fundador
# ---------------------------------------------------------------------------

def set_founder_pricing(
    db: Session,
    tenant_id: int,
    request: schemas.SetFounderPricingRequest,
    admin_user: models.User,
) -> models.Subscription:
    """
    Fija el precio fundador (y opcionalmente el precio actual) de un tenant.
    El precio fundador es el precio especial de early adopters: una vez fijado,
    no debe subir aunque el producto aumente de precio.
    """
    _get_tenant_or_404(db, tenant_id)

    updates: dict = {"founder_price": request.founder_price}
    if request.current_price is not None:
        updates["current_price"] = request.current_price
    else:
        # Si no se especifica current_price, hereda del founder_price
        updates["current_price"] = request.founder_price
    if request.notes_internal is not None:
        updates["notes_internal"] = request.notes_internal

    return crud.update_subscription_fields(db, tenant_id, updates)


# ---------------------------------------------------------------------------
# Pagos SaaS
# ---------------------------------------------------------------------------

def register_saas_payment(
    db: Session,
    tenant_id: int,
    data: schemas.SubscriptionPaymentCreate,
    admin_user: models.User,
) -> models.SubscriptionPayment:
    """
    Registra un pago SaaS recibido de un tenant a Inkora.

    DOMINIO: tenant → Inkora (SaaS). No es un cobro del tenant a sus clientes.
    """
    _get_tenant_or_404(db, tenant_id)
    return crud.register_subscription_payment(db, tenant_id, data, admin_user.id)


def get_saas_payments(
    db: Session,
    tenant_id: int,
    skip: int = 0,
    limit: int = 50,
) -> list[models.SubscriptionPayment]:
    """Lista los pagos SaaS registrados para un tenant."""
    _get_tenant_or_404(db, tenant_id)
    return crud.get_subscription_payments(db, tenant_id, skip, limit)


# ---------------------------------------------------------------------------
# Consulta de estado
# ---------------------------------------------------------------------------

def get_subscription_status(
    db: Session,
    tenant_id: int,
) -> models.Subscription:
    """
    Devuelve el estado completo de la suscripcion de un tenant.
    Si no existe, la crea en estado trial.
    """
    _get_tenant_or_404(db, tenant_id)
    return crud.get_or_create_subscription(db, tenant_id)


def update_subscription_general(
    db: Session,
    tenant_id: int,
    request: schemas.UpdateSubscriptionRequest,
    admin_user: models.User,
) -> models.Subscription:
    """
    Actualización general de campos de suscripcion (uso admin avanzado).
    Valida que el status, si se especifica, sea uno de los valores permitidos.
    """
    _get_tenant_or_404(db, tenant_id)

    updates = request.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Estado invalido. Valores permitidos: {', '.join(sorted(VALID_STATUSES))}.",
        )

    return crud.update_subscription_fields(db, tenant_id, updates)
