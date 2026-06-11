"""schemas/tenants.py — Tenant schemas."""
from datetime import datetime
import re
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from schemas._base import StrictInputModel
from services.bank_account_validation import validate_and_normalize_bank_accounts
from services.phone_validation import normalize_and_validate_optional_peru_mobile


class TenantBase(StrictInputModel):
    business_name: str
    business_ruc: str


class TenantCreate(TenantBase):
    business_address: Optional[str] = None
    business_phone: Optional[str] = None

    @field_validator("business_phone")
    @classmethod
    def validate_business_phone(cls, value: Optional[str]) -> Optional[str]:
        return normalize_and_validate_optional_peru_mobile(value, "Telefono de contacto")


HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _normalize_optional_hex_color(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    if not HEX_COLOR_RE.fullmatch(normalized):
        raise ValueError("El color debe usar formato hexadecimal #RRGGBB.")
    return normalized.upper()


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
    smartpse_company_id: Optional[str] = None
    smartpse_environment: Optional[str] = None
    smartpse_usuario_secundaria: Optional[str] = None
    smartpse_token_acceso: Optional[str] = None

    @field_validator("bank_accounts")
    @classmethod
    def validate_bank_accounts(cls, value: Optional[List[dict]]) -> Optional[List[dict]]:
        return validate_and_normalize_bank_accounts(value)

    @field_validator("business_phone")
    @classmethod
    def validate_business_phone(cls, value: Optional[str]) -> Optional[str]:
        return normalize_and_validate_optional_peru_mobile(value, "Telefono de contacto")

    @field_validator("primary_color", "pdf_note_1_color", mode="before")
    @classmethod
    def validate_pdf_colors(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_optional_hex_color(value)


def _normalize_optional_business_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return " ".join(str(value).strip().split())


class TenantAdminUpdate(StrictInputModel):
    """Schema restringido para admin del tenant.
    Permite editar datos visibles en comprobantes/PDF que no cambian la identidad fiscal.
    El RUC y credenciales fiscales son de solo lectura para el tenant.
    """
    business_name: Optional[str] = Field(default=None, min_length=2, max_length=180)
    business_address: Optional[str] = Field(default=None, min_length=5, max_length=250)
    business_phone: Optional[str] = None
    primary_color: Optional[str] = None
    pdf_note_1: Optional[str] = None
    pdf_note_1_color: Optional[str] = None
    pdf_note_2: Optional[str] = None
    bank_accounts: Optional[List[dict]] = None

    @field_validator("business_name", "business_address", mode="before")
    @classmethod
    def normalize_business_identity(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_optional_business_text(value)

    @field_validator("bank_accounts")
    @classmethod
    def validate_bank_accounts(cls, value: Optional[List[dict]]) -> Optional[List[dict]]:
        return validate_and_normalize_bank_accounts(value)

    @field_validator("business_phone")
    @classmethod
    def validate_business_phone(cls, value: Optional[str]) -> Optional[str]:
        return normalize_and_validate_optional_peru_mobile(value, "Telefono de contacto")

    @field_validator("primary_color", "pdf_note_1_color", mode="before")
    @classmethod
    def validate_pdf_colors(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_optional_hex_color(value)


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
    payment_qr_filename: Optional[str] = None
    primary_color: Optional[str] = None
    pdf_note_1: Optional[str] = None
    pdf_note_1_color: Optional[str] = None
    pdf_note_2: Optional[str] = None
    bank_accounts: Optional[Any] = None
    apisperu_token_status: Optional[str] = None
    apisperu_token_checked_at: Optional[datetime] = None
    smartpse_company_id: Optional[str] = None
    smartpse_environment: Optional[str] = None
    smartpse_status: Optional[str] = None
    smartpse_checked_at: Optional[datetime] = None
    smartpse_remote_active: Optional[bool] = None
    smartpse_remote_estado: Optional[str] = None
    smartpse_remote_synced_at: Optional[datetime] = None
    smartpse_start_date: Optional[datetime] = None
    smartpse_end_date: Optional[datetime] = None
    smartpse_firmas_usadas: Optional[int] = None
    smartpse_gre_status: Optional[str] = None
    smartpse_gre_checked_at: Optional[datetime] = None

    # apisperu_url y apisperu_token NO se exponen al tenant — solo el estado booleano
    apisperu_token_secret: Optional[str] = Field(
        default=None, alias="apisperu_token", exclude=True, repr=False
    )
    smartpse_usuario_secundaria_secret: Optional[str] = Field(
        default=None, alias="smartpse_usuario_secundaria", exclude=True, repr=False
    )
    smartpse_token_acceso_secret: Optional[str] = Field(
        default=None, alias="smartpse_token_acceso", exclude=True, repr=False
    )
    # GRE credentials — ocultas, solo se expone el estado booleano
    sunat_gre_client_id_secret: Optional[str] = Field(
        default=None, alias="sunat_gre_client_id", exclude=True, repr=False
    )
    sunat_gre_client_secret_secret: Optional[str] = Field(
        default=None, alias="sunat_gre_client_secret", exclude=True, repr=False
    )
    smartpse_gre_sol_username_secret: Optional[str] = Field(
        default=None, alias="smartpse_gre_sol_username", exclude=True, repr=False
    )
    smartpse_gre_sol_password_secret: Optional[str] = Field(
        default=None, alias="smartpse_gre_sol_password_enc", exclude=True, repr=False
    )
    smartpse_gre_client_id_secret: Optional[str] = Field(
        default=None, alias="smartpse_gre_client_id", exclude=True, repr=False
    )
    smartpse_gre_client_secret_secret: Optional[str] = Field(
        default=None, alias="smartpse_gre_client_secret_enc", exclude=True, repr=False
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
    sunat_cert_password_secret: Optional[str] = Field(
        default=None, alias="sunat_cert_password", exclude=True, repr=False
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
    def has_smartpse_credentials(self) -> bool:
        return bool(self.smartpse_usuario_secundaria_secret and self.smartpse_token_acceso_secret)

    @computed_field(return_type=bool)
    @property
    def has_gre_credentials(self) -> bool:
        return self.has_smartpse_gre_credentials or bool(
            self.sunat_gre_client_id_secret and self.sunat_gre_client_secret_secret
        )

    @computed_field(return_type=bool)
    @property
    def has_smartpse_gre_credentials(self) -> bool:
        return bool(
            self.smartpse_gre_sol_username_secret
            and self.smartpse_gre_sol_password_secret
            and self.smartpse_gre_client_id_secret
            and self.smartpse_gre_client_secret_secret
        )

    @computed_field(return_type=bool)
    @property
    def has_sunat_credentials(self) -> bool:
        return bool(
            self.sunat_usuario_sol_secret
            and self.sunat_clave_sol_secret
            and self.sunat_cert_password_secret
            and self.sunat_cert_url_secret
        )

    @computed_field(return_type=bool)
    @property
    def has_sunat_cert(self) -> bool:
        return bool(self.sunat_cert_url_secret)


class TenantSaaSUpdate(StrictInputModel):
    # Datos maestros de empresa (solo superadmin)
    business_name: Optional[str] = None
    business_ruc: Optional[str] = None
    business_address: Optional[str] = None
    is_active: Optional[bool] = None
    # Plan / suscripción
    plan_type: Optional[str] = None
    plan_start_date: Optional[datetime] = None
    plan_end_date: Optional[datetime] = None
    invoice_limit: Optional[int] = None
    # ApisPeru — token de empresa (sin expiración)
    apisperu_token: Optional[str] = None
    apisperu_url: Optional[str] = None
    smartpse_company_id: Optional[str] = None
    smartpse_environment: Optional[str] = None
    smartpse_usuario_secundaria: Optional[str] = None
    smartpse_token_acceso: Optional[str] = None
    # Credenciales SUNAT Nueva GRE (requeridas para guía de remisión electrónica)
    sunat_gre_client_id: Optional[str] = None
    sunat_gre_client_secret: Optional[str] = None
    # Credenciales SUNAT directas
    sunat_usuario_sol: Optional[str] = None
    sunat_clave_sol: Optional[str] = None
    sunat_cert_password: Optional[str] = None
    sunat_cert_url: Optional[str] = None


class SuperadminTenantCreate(StrictInputModel):
    """Schema para que el superadmin cree un nuevo tenant desde el panel."""
    business_name: str
    business_ruc: str
    business_address: Optional[str] = None
    apisperu_token: Optional[str] = None
    apisperu_url: Optional[str] = None
    smartpse_environment: Optional[str] = None


class EmissionErrorResponse(BaseModel):
    job_id: int
    action: str
    resource_type: str
    resource_id: int
    last_error: Optional[str] = None
    attempts: int
    finished_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenHealthResponse(BaseModel):
    tenant_id: int
    status: str
    checked_at: Optional[datetime] = None
    message: str


class ApisPeruTokenValidationRequest(StrictInputModel):
    token: str
    api_url: Optional[str] = None
    business_ruc: Optional[str] = None


class ApisPeruTokenValidationResponse(BaseModel):
    valid: bool
    message: str
    provider_status_code: Optional[int] = None
    provider_detail: Optional[str] = None
    token_company_ruc: Optional[str] = None
    matches_business_ruc: Optional[bool] = None


class SmartPSECredentialsValidationRequest(StrictInputModel):
    usuario_secundaria: str
    token_acceso: str
    business_ruc: Optional[str] = None


class SmartPSECredentialsValidationResponse(BaseModel):
    valid: bool
    message: str
    provider_status_code: Optional[int] = None
    provider_detail: Optional[str] = None
    token_preview: Optional[str] = None


class SmartPSEProvisionRequest(StrictInputModel):
    environment: str = "demo"
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class SmartPSECompanyUpdate(StrictInputModel):
    razon_social: Optional[str] = Field(default=None, min_length=2, max_length=180)
    environment: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in {"demo", "produccion"}:
            raise ValueError("environment debe ser 'demo' o 'produccion'.")
        return normalized


class SmartPSECompanyResponse(BaseModel):
    id: Optional[str] = None
    ruc: Optional[str] = None
    razon_social: Optional[str] = None
    environment: Optional[str] = None
    active: Optional[bool] = None
    estado: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    firmas_usadas: Optional[int] = None
    synced_at: Optional[datetime] = None


class SmartPSECompanyPageResponse(BaseModel):
    data: List[SmartPSECompanyResponse]
    total: Optional[int] = None
    current_page: Optional[int] = None
    last_page: Optional[int] = None


class SmartPSEGreCredentialsUpdate(StrictInputModel):
    sol_username: str = Field(..., min_length=1, max_length=80)
    sol_password: str = Field(..., min_length=1, max_length=250)
    client_id: str = Field(..., min_length=1, max_length=120)
    client_secret: str = Field(..., min_length=1, max_length=500)

    @field_validator("sol_username")
    @classmethod
    def normalize_sol_username(cls, value: str) -> str:
        return " ".join(value.strip().upper().split())

    @field_validator("sol_password", "client_id", "client_secret")
    @classmethod
    def normalize_secret_text(cls, value: str) -> str:
        return value.strip()


class SmartPSEGreCredentialsValidationResponse(BaseModel):
    valid: bool
    message: str
    provider_status_code: Optional[int] = None
    provider_detail: Optional[str] = None


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
    def has_sunat_clave_sol(self) -> bool:
        return bool(self.sunat_clave_sol_secret)

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
            and self.has_sunat_clave_sol
            and self.has_sunat_cert_password
            and self.has_sunat_cert_url
        )


class SuperadminTenantPageMetrics(BaseModel):
    total: int
    active: int
    smartpse_gre: int
    smartpse_gre_pending: int


class SuperadminTenantPageResponse(BaseModel):
    items: List[SuperadminTenantResponse]
    total: int
    skip: int
    limit: int
    metrics: SuperadminTenantPageMetrics
