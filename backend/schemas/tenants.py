"""schemas/tenants.py — Tenant schemas."""
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field

from schemas._base import StrictInputModel


class TenantBase(StrictInputModel):
    business_name: str
    business_ruc: str


class TenantCreate(TenantBase):
    business_address: Optional[str] = None
    business_phone: Optional[str] = None


class TenantUpdate(StrictInputModel):
    """Schema completo de actualización — solo para uso interno/superadmin."""
    business_name: Optional[str] = None
    business_ruc: Optional[str] = None
    business_address: Optional[str] = None
    business_phone: Optional[str] = None
    primary_color: Optional[str] = None
    pdf_note_1: Optional[str] = None
    pdf_note_1_color: Optional[str] = None
    pdf_note_2: Optional[str] = None
    bank_accounts: Optional[List[dict]] = None
    apisperu_token: Optional[str] = None
    apisperu_url: Optional[str] = None


class TenantAdminUpdate(StrictInputModel):
    """Schema restringido para admin del tenant.
    Solo permite editar campos de contacto seguros.
    Campos fiscales y datos maestros de empresa son de solo lectura para el tenant.
    """
    business_phone: Optional[str] = None


class TenantSummaryResponse(BaseModel):
    id: int
    is_active: bool = True
    business_name: str
    business_ruc: str
    model_config = ConfigDict(from_attributes=True)


class TenantResponse(TenantSummaryResponse):
    business_address: Optional[str] = None
    business_phone: Optional[str] = None
    logo_filename: Optional[str] = None
    primary_color: Optional[str] = None
    pdf_note_1: Optional[str] = None
    pdf_note_1_color: Optional[str] = None
    pdf_note_2: Optional[str] = None
    bank_accounts: Optional[Any] = None

    # apisperu_url y apisperu_token NO se exponen al tenant — solo el estado booleano
    apisperu_token_secret: Optional[str] = Field(
        default=None, alias="apisperu_token", exclude=True, repr=False
    )

    plan_type: Optional[str] = "Free"
    invoice_limit: Optional[int] = 50
    invoices_used: Optional[int] = 0

    # Credenciales SUNAT — excluidas de la respuesta, solo se expone el estado
    sunat_usuario_sol_secret: Optional[str] = Field(
        default=None, alias="sunat_usuario_sol", exclude=True, repr=False
    )
    sunat_clave_sol_secret: Optional[str] = Field(
        default=None, alias="sunat_clave_sol", exclude=True, repr=False
    )
    sunat_cert_url_secret: Optional[str] = Field(
        default=None, alias="sunat_cert_url", exclude=True, repr=False
    )

    model_config = ConfigDict(from_attributes=True)

    @computed_field(return_type=bool)
    @property
    def has_apisperu_token(self) -> bool:
        return bool(self.apisperu_token_secret)

    @computed_field(return_type=bool)
    @property
    def has_sunat_credentials(self) -> bool:
        return bool(self.sunat_usuario_sol_secret and self.sunat_cert_url_secret)

    @computed_field(return_type=bool)
    @property
    def has_sunat_cert(self) -> bool:
        return bool(self.sunat_cert_url_secret)


class TenantSaaSUpdate(StrictInputModel):
    plan_type: Optional[str] = None
    plan_start_date: Optional[datetime] = None
    plan_end_date: Optional[datetime] = None
    invoice_limit: Optional[int] = None
    sunat_usuario_sol: Optional[str] = None
    sunat_clave_sol: Optional[str] = None
    sunat_cert_password: Optional[str] = None
    sunat_cert_url: Optional[str] = None


class SuperadminTenantResponse(TenantResponse):
    plan_start_date: Optional[datetime] = None
    plan_end_date: Optional[datetime] = None
    sunat_usuario_sol_secret: Optional[str] = Field(
        default=None, alias="sunat_usuario_sol", exclude=True, repr=False
    )
    sunat_clave_sol_secret: Optional[str] = Field(
        default=None, alias="sunat_clave_sol", exclude=True, repr=False
    )
    sunat_cert_password_secret: Optional[str] = Field(
        default=None, alias="sunat_cert_password", exclude=True, repr=False
    )
    sunat_cert_url_secret: Optional[str] = Field(
        default=None, alias="sunat_cert_url", exclude=True, repr=False
    )

    @computed_field(return_type=bool)
    @property
    def has_sunat_usuario_sol(self) -> bool:
        return bool(self.sunat_usuario_sol_secret)

    @computed_field(return_type=bool)
    @property
    def has_sunat_cert_password(self) -> bool:
        return bool(self.sunat_cert_password_secret)

    @computed_field(return_type=bool)
    @property
    def has_sunat_cert_url(self) -> bool:
        return bool(self.sunat_cert_url_secret)

    @computed_field(return_type=bool)
    @property
    def has_sunat_credentials(self) -> bool:
        return (
            self.has_sunat_usuario_sol
            and self.has_sunat_cert_password
            and self.has_sunat_cert_url
        )
