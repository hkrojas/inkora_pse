"""schemas/auth.py — User, Token schemas."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from schemas._base import StrictInputModel
from schemas.tenants import TenantSummaryResponse


class UserIdentity(BaseModel):
    email: EmailStr
    nombre_completo: Optional[str] = None


class UserRegisterRequest(StrictInputModel):
    email: EmailStr
    nombre_completo: Optional[str] = None
    password: str
    tenant_id: int


class UserUpdateProfile(StrictInputModel):
    nombre_completo: Optional[str] = None


class UserAdminUpdate(StrictInputModel):
    nombre_completo: Optional[str] = None
    rol: Optional[str] = None
    tenant_id: Optional[int] = None
    is_superadmin: Optional[bool] = None


class UserResponse(UserIdentity):
    id: int
    rol: str = "vendedor"
    is_superadmin: bool = False
    tenant_id: int
    tenant: Optional[TenantSummaryResponse] = None

    model_config = ConfigDict(from_attributes=True)


class SuperadminUserCreate(StrictInputModel):
    """Schema para que el superadmin cree un usuario en un tenant específico."""
    email: EmailStr
    nombre_completo: Optional[str] = None
    password: str
    rol: str = "admin"


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
