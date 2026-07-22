from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from schemas._base import StrictInputModel
from services.phone_validation import normalize_and_validate_optional_peru_mobile


class AccessRequestCreate(StrictInputModel):
    business_ruc: str = Field(..., min_length=11, max_length=11)
    business_name: str = Field(..., min_length=2, max_length=255)
    business_address: Optional[str] = Field(default=None, max_length=500)
    business_phone: Optional[str] = None
    contact_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=10, max_length=64)
    confirm_password: str = Field(..., min_length=10, max_length=64)

    @field_validator("business_ruc")
    @classmethod
    def validate_ruc(cls, value: str) -> str:
        normalized = "".join(character for character in str(value) if character.isdigit())
        if len(normalized) != 11 or not normalized.startswith("20"):
            raise ValueError("Ingresa un RUC válido de 11 dígitos que empiece por 20")
        return normalized

    @field_validator("business_name", "contact_name")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if len(normalized) < 2:
            raise ValueError("Este campo debe tener al menos 2 caracteres")
        return normalized

    @field_validator("business_address")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        normalized = " ".join(str(value or "").strip().split())
        return normalized or None

    @field_validator("business_phone")
    @classmethod
    def validate_phone(cls, value: Optional[str]) -> Optional[str]:
        return normalize_and_validate_optional_peru_mobile(value, "Teléfono operativo")

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden")
        return self


class AccessRequestCreated(BaseModel):
    status: str
    request_token: str
    message: str


class AccessRequestStatusLookup(StrictInputModel):
    request_token: str = Field(..., min_length=32, max_length=255)


class AccessRequestPublicStatus(BaseModel):
    status: str
    business_name: str
    email: EmailStr
    review_notes: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AccessRequestReview(StrictInputModel):
    review_notes: Optional[str] = Field(default=None, max_length=500)


class AccessRequestAdminResponse(BaseModel):
    id: int
    business_ruc: str
    business_name: str
    business_address: Optional[str] = None
    business_phone: Optional[str] = None
    contact_name: str
    email: EmailStr
    status: str
    review_notes: Optional[str] = None
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    tenant_id: Optional[int] = None
    user_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccessRequestPageResponse(BaseModel):
    items: list[AccessRequestAdminResponse]
    total: int
    skip: int
    limit: int
