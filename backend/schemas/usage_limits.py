"""schemas/usage_limits.py — Limites de emision por tenant/usuario."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.tenants import USAGE_LIMIT_KINDS, USAGE_LIMIT_PERIODS
from schemas._base import StrictInputModel


class UsageLimitBase(StrictInputModel):
    user_id: Optional[int] = None
    document_kind: str
    period: str = "month"
    max_count: int = Field(gt=0)
    notify_at_pct: Optional[int] = Field(default=80, ge=0, le=100)
    enabled: bool = True

    @field_validator("document_kind")
    @classmethod
    def validate_kind(cls, v: str) -> str:
        if v == "quotation":
            raise ValueError(
                "Las cotizaciones no admiten limites: siempre son ilimitadas."
            )
        if v not in USAGE_LIMIT_KINDS:
            raise ValueError(
                f"document_kind invalido. Permitidos: {', '.join(USAGE_LIMIT_KINDS)}"
            )
        return v

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        if v not in USAGE_LIMIT_PERIODS:
            raise ValueError(
                f"period invalido. Permitidos: {', '.join(USAGE_LIMIT_PERIODS)}"
            )
        return v


class UsageLimitCreate(UsageLimitBase):
    pass


class UsageLimitResponse(BaseModel):
    id: int
    tenant_id: int
    user_id: Optional[int] = None
    document_kind: str
    period: str
    max_count: int
    notify_at_pct: Optional[int] = 80
    enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UsageLimitsBulkUpsert(StrictInputModel):
    limits: List[UsageLimitCreate] = Field(default_factory=list)


class UsageLimitUsageItem(BaseModel):
    limit_id: int
    tenant_id: int
    user_id: Optional[int] = None
    document_kind: str
    period: str
    max_count: int
    used: int
    pct: int
    would_block: bool
    enabled: bool

    model_config = ConfigDict(from_attributes=True)


class UsageLimitsWithUsage(BaseModel):
    limits: List[UsageLimitResponse]
    usage: List[UsageLimitUsageItem]
