"""schemas/subscriptions.py — Subscription SaaS, superadmin, beta schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from schemas._base import StrictInputModel


class SubscriptionResponse(BaseModel):
    id: int
    tenant_id: int
    status: str
    plan_code: str
    current_price: Optional[Decimal] = None
    founder_price: Optional[Decimal] = None
    billing_started_at: Optional[datetime] = None
    billing_due_at: Optional[datetime] = None
    grace_until: Optional[datetime] = None
    max_users: Optional[int] = None
    max_documents: Optional[int] = None
    documents_used: int = 0
    onboarding_status: str
    notes_internal: Optional[str] = None
    is_pilot: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriptionPaymentCreate(StrictInputModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = "PEN"
    method: str
    reference: Optional[str] = None
    paid_at: Optional[datetime] = None
    notes: Optional[str] = None


class SubscriptionPaymentResponse(BaseModel):
    id: int
    tenant_id: int
    amount: Decimal
    currency: str
    method: str
    reference: Optional[str] = None
    paid_at: Optional[datetime] = None
    validated_by_user_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivateTenantRequest(StrictInputModel):
    billing_due_at: Optional[datetime] = None
    notes_internal: Optional[str] = None


class SuspendTenantRequest(StrictInputModel):
    notes_internal: Optional[str] = None


class ExtendAccessRequest(StrictInputModel):
    billing_due_at: datetime
    grace_until: Optional[datetime] = None
    notes_internal: Optional[str] = None


class SetFounderPricingRequest(StrictInputModel):
    founder_price: Decimal = Field(..., gt=0)
    current_price: Optional[Decimal] = Field(default=None, gt=0)
    notes_internal: Optional[str] = None


class UpdateSubscriptionRequest(StrictInputModel):
    status: Optional[str] = None
    plan_code: Optional[str] = None
    billing_started_at: Optional[datetime] = None
    billing_due_at: Optional[datetime] = None
    grace_until: Optional[datetime] = None
    current_price: Optional[Decimal] = None
    founder_price: Optional[Decimal] = None
    max_users: Optional[int] = None
    max_documents: Optional[int] = None
    onboarding_status: Optional[str] = None
    notes_internal: Optional[str] = None
    is_pilot: Optional[bool] = None


class SuperadminTenantDetailResponse(BaseModel):
    id: int
    is_active: bool
    business_name: str
    business_ruc: str
    business_address: Optional[str] = None
    business_phone: Optional[str] = None
    plan_type: Optional[str] = None
    subscription: Optional[SubscriptionResponse] = None

    model_config = ConfigDict(from_attributes=True)


class UpdateNotasRequest(StrictInputModel):
    notes_internal: Optional[str] = None
    is_pilot: Optional[bool] = None


class TenantActividadResponse(BaseModel):
    tenant_id: int
    business_name: str
    business_ruc: str
    clientes_count: int
    productos_count: int
    usuarios_count: int
    cotizaciones_count: int
    documentos_fiscales_count: int
    documentos_fiscales_ultimo_mes: int
    guias_count: int
    pagos_count: int
    ultimo_documento_fiscal_fecha: Optional[datetime] = None
    subscription_status: Optional[str] = None
    onboarding_status: Optional[str] = None
    documents_used: int = 0
    max_documents: Optional[int] = None


class BetaTenantSummary(BaseModel):
    tenant_id: int
    business_name: str
    business_ruc: str
    is_active: bool
    is_pilot: bool = False
    subscription_status: Optional[str] = None
    onboarding_status: Optional[str] = None
    plan_code: Optional[str] = None
    current_price: Optional[Decimal] = None
    founder_price: Optional[Decimal] = None
    billing_due_at: Optional[datetime] = None
    documents_used: int = 0
    max_documents: Optional[int] = None
    clientes_count: int = 0
    productos_count: int = 0
    usuarios_count: int = 0
    ultimo_pago_saas_fecha: Optional[datetime] = None
    ultimo_pago_saas_monto: Optional[Decimal] = None
    notes_internal: Optional[str] = None
