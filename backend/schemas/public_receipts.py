from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from schemas._base import StrictInputModel


PublicReceiptType = Literal["01", "03", "07", "08"]
PublicReceiptStatus = Literal["ACEPTADO", "ANULADO", "RECHAZADO", "EN_PROCESO"]


class PublicReceiptLookup(StrictInputModel):
    ruc: str = Field(..., min_length=11, max_length=11)
    tipo_comprobante: PublicReceiptType
    serie: str = Field(..., min_length=4, max_length=4)
    correlativo: str = Field(..., min_length=1, max_length=8)
    fecha_emision: date
    importe_total: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)

    @field_validator("ruc")
    @classmethod
    def validate_ruc(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.isdigit():
            raise ValueError("El RUC debe contener exactamente 11 dígitos.")
        return normalized

    @field_validator("serie")
    @classmethod
    def validate_serie(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized.isalnum():
            raise ValueError("La serie debe contener cuatro letras o números.")
        return normalized

    @field_validator("correlativo")
    @classmethod
    def validate_correlativo(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.isdigit() or int(normalized) <= 0:
            raise ValueError("El correlativo debe contener entre 1 y 8 dígitos.")
        return normalized


class PublicReceiptEvidence(BaseModel):
    pdf: bool
    xml: bool
    cdr: bool


class PublicReceiptResponse(BaseModel):
    encontrado: Literal[True] = True
    emisor: str
    tipo_comprobante: PublicReceiptType
    numero: str
    fecha_emision: date
    moneda: str
    importe_total: Decimal
    estado: PublicReceiptStatus
    evidencias: PublicReceiptEvidence
