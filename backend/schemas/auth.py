"""schemas/auth.py — User, Token schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from schemas._base import StrictInputModel
from schemas.tenants import TenantSummaryResponse


class UserIdentity(BaseModel):
    email: str
    nombre_completo: Optional[str] = None


class UserRegisterRequest(StrictInputModel):
    email: EmailStr
    nombre_completo: Optional[str] = None
    tenant_id: int


class UserUpdateProfile(StrictInputModel):
    nombre_completo: Optional[str] = None


class UserAdminUpdate(StrictInputModel):
    nombre_completo: Optional[str] = None
    rol: Optional[str] = None
    tenant_id: Optional[int] = None
    is_superadmin: Optional[bool] = None


class SuperadminTenantUserUpdate(StrictInputModel):
    nombre_completo: Optional[str] = None
    rol: Optional[str] = None


class UserResponse(UserIdentity):
    id: int
    rol: str = "vendedor"
    is_superadmin: bool = False
    is_active: bool = True
    must_change_password: bool = False
    tenant_id: int
    tenant: Optional[TenantSummaryResponse] = None
    last_login_at: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserMetrics(BaseModel):
    cotizaciones_total: int = 0
    cotizaciones_mes_actual: int = 0
    facturas_total: int = 0
    facturas_mes_actual: int = 0
    boletas_total: int = 0
    boletas_mes_actual: int = 0
    notas_credito_total: int = 0
    notas_debito_total: int = 0
    guias_total: int = 0
    guias_mes_actual: int = 0
    ultimo_documento_at: Optional[datetime] = None


class UserDetailResponse(UserResponse):
    metrics: UserMetrics = UserMetrics()


class ResetPasswordResponse(BaseModel):
    user_id: int
    email: str
    temp_password: str
    message: str


class ToggleUserActiveRequest(StrictInputModel):
    is_active: bool


class SuperadminUserCreate(StrictInputModel):
    """Schema para que el superadmin cree un usuario en un tenant específico."""
    email: EmailStr
    nombre_completo: Optional[str] = None
    rol: str = "admin"


class ChangePasswordRequest(StrictInputModel):
    current_password: str
    new_password: str
    confirm_password: str


class CreateUserWithPasswordResponse(BaseModel):
    """Respuesta de creación de usuario que incluye la contraseña temporal una sola vez."""
    user: UserResponse
    temp_password: str
    message: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
