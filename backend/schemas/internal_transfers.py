"""Schemas for national transfers between establishments of one tenant."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from fiscal_catalogs import normalize_internal_product_code, normalize_sunat_unit_code
from schemas.guias import SaleDispatchGuideData


class EstablishmentCreate(BaseModel):
    sunat_code: str = Field(..., pattern=r"^\d{4}$")
    name: str = Field(..., min_length=2, max_length=120)
    ubigeo: str = Field(..., pattern=r"^\d{6}$")
    address: str = Field(..., min_length=3, max_length=500)
    is_main: bool = False

    @field_validator("name", "address")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class EstablishmentUpdate(EstablishmentCreate):
    is_active: bool = True


class EstablishmentVerify(BaseModel):
    note: str = Field(..., min_length=10, max_length=500)


class EstablishmentResponse(EstablishmentUpdate):
    id: int
    verified_at: Optional[datetime] = None
    verification_note: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class InternalTransferLineCreate(BaseModel):
    product_id: Optional[int] = None
    description: Optional[str] = Field(default=None, max_length=500)
    product_code: Optional[str] = Field(default=None, max_length=100)
    unit_code: str = "NIU"
    quantity: Decimal = Field(..., gt=0, max_digits=18, decimal_places=4)
    manual_goods_confirmed: bool = False

    @field_validator("unit_code")
    @classmethod
    def normalize_unit(cls, value: str) -> str:
        return normalize_sunat_unit_code(value)

    @field_validator("product_code")
    @classmethod
    def normalize_code(cls, value: Optional[str]) -> Optional[str]:
        return normalize_internal_product_code(value)

    @model_validator(mode="after")
    def validate_manual_goods(self):
        if self.product_id is None:
            if not (self.description or "").strip():
                raise ValueError("Describe el bien manual")
            if not self.manual_goods_confirmed:
                raise ValueError("Confirma que la línea manual corresponde a un bien sin control de stock")
        return self


class InternalTransferCreate(BaseModel):
    source_establishment_id: int
    destination_establishment_id: int
    source_warehouse_id: Optional[int] = None
    destination_warehouse_id: Optional[int] = None
    reason: str = Field(..., min_length=3, max_length=500)
    idempotency_key: str = Field(..., min_length=8, max_length=120)
    lines: List[InternalTransferLineCreate] = Field(..., min_length=1, max_length=500)


class InternalTransferUpdate(BaseModel):
    version: int = Field(..., ge=1)
    reason: str = Field(..., min_length=3, max_length=500)
    source_establishment_id: int
    destination_establishment_id: int
    source_warehouse_id: Optional[int] = None
    destination_warehouse_id: Optional[int] = None
    lines: List[InternalTransferLineCreate] = Field(..., min_length=1, max_length=500)


class InternalTransferDispatchLineCreate(BaseModel):
    transfer_line_id: int
    quantity: Decimal = Field(..., gt=0, max_digits=18, decimal_places=4)


class InternalTransferDispatchCreate(BaseModel):
    idempotency_key: str = Field(..., min_length=8, max_length=120)
    lines: List[InternalTransferDispatchLineCreate] = Field(..., min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_unique_lines(self):
        ids = [line.transfer_line_id for line in self.lines]
        if len(ids) != len(set(ids)):
            raise ValueError("Cada línea de transferencia debe aparecer una sola vez")
        return self


class InternalTransferGuideCreate(SaleDispatchGuideData):
    dispatch_id: int
    idempotency_key: str = Field(..., min_length=8, max_length=120)


class InternalTransferDepartureConfirm(BaseModel):
    idempotency_key: str = Field(..., min_length=8, max_length=120)


class InternalTransferReceiptLineCreate(BaseModel):
    dispatch_line_id: int
    quantity: Decimal = Field(..., gt=0, max_digits=18, decimal_places=4)


class InternalTransferReceiptCreate(BaseModel):
    idempotency_key: str = Field(..., min_length=8, max_length=120)
    note: Optional[str] = Field(default=None, max_length=500)
    lines: List[InternalTransferReceiptLineCreate] = Field(..., min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_unique_lines(self):
        ids = [line.dispatch_line_id for line in self.lines]
        if len(ids) != len(set(ids)):
            raise ValueError("Cada línea de despacho debe aparecer una sola vez")
        return self
