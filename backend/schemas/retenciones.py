"""Schemas para comprobantes de retencion APISPeru/SUNAT."""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from schemas._base import StrictInputModel


_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SERIE_RETENCION_RE = re.compile(r"^R[A-Z0-9]{3}$")
_NUM_DOC_REL_RE = re.compile(r"^[A-Z0-9]{4}-\d{1,8}$")
_RUC_RE = re.compile(r"^(10|15|17|20)\d{9}$")
_RETENTION_DOC_TYPES = {"01", "07", "08"}
_CURRENCY_CODES = {"PEN", "USD"}


def _normalize_datetime(value: Any) -> Any:
    if isinstance(value, str):
        cleaned = value.strip()
        if _DATE_ONLY_RE.match(cleaned):
            return f"{cleaned}T00:00:00-05:00"
        return cleaned
    return value


def _normalize_money(value: Any) -> Decimal:
    return Decimal(str(value or "0")).quantize(Decimal("0.01"))


class RetencionClientCreate(StrictInputModel):
    tipoDoc: str = Field(default="6", min_length=1, max_length=1)
    numDoc: str = Field(..., min_length=11, max_length=11)
    rznSocial: str = Field(..., min_length=2, max_length=180)

    @field_validator("tipoDoc")
    @classmethod
    def validate_tipo_doc(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if normalized != "6":
            raise ValueError("El proveedor de una retencion debe identificarse con RUC SUNAT tipo 6.")
        return normalized

    @field_validator("numDoc")
    @classmethod
    def validate_ruc(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if not _RUC_RE.match(normalized):
            raise ValueError("El RUC del proveedor debe tener 11 digitos y empezar con 10, 15, 17 o 20.")
        return normalized

    @field_validator("rznSocial")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return str(value or "").strip()


class RetencionPaymentCreate(StrictInputModel):
    moneda: str = Field(default="PEN", min_length=3, max_length=3)
    importe: Decimal = Field(..., gt=0)
    fecha: datetime

    @field_validator("fecha", mode="before")
    @classmethod
    def normalize_date(cls, value: Any) -> Any:
        return _normalize_datetime(value)

    @field_validator("moneda")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        normalized = str(value or "").strip().upper()
        if normalized not in _CURRENCY_CODES:
            raise ValueError("Moneda no soportada para retenciones. Usa PEN o USD.")
        return normalized


class RetencionExchangeCreate(StrictInputModel):
    monedaRef: str = Field(default="PEN", min_length=3, max_length=3)
    monedaObj: str = Field(default="PEN", min_length=3, max_length=3)
    factor: Decimal = Field(default=Decimal("1"), gt=0)
    fecha: datetime

    @field_validator("fecha", mode="before")
    @classmethod
    def normalize_date(cls, value: Any) -> Any:
        return _normalize_datetime(value)

    @field_validator("monedaRef", "monedaObj")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        normalized = str(value or "").strip().upper()
        if normalized not in _CURRENCY_CODES:
            raise ValueError("Moneda no soportada para tipo de cambio de retencion.")
        return normalized


class RetencionDetalleCreate(StrictInputModel):
    tipoDoc: str = Field(..., min_length=2, max_length=2)
    numDoc: str = Field(..., min_length=6, max_length=13)
    fechaEmision: datetime
    impTotal: Decimal = Field(..., gt=0)
    moneda: str = Field(default="PEN", min_length=3, max_length=3)
    pagos: list[RetencionPaymentCreate] = Field(..., min_length=1, max_length=50)
    fechaRetencion: datetime
    impRetenido: Decimal = Field(..., ge=0)
    impPagar: Decimal = Field(..., gt=0)
    tipoCambio: Optional[RetencionExchangeCreate] = None

    @field_validator("fechaEmision", "fechaRetencion", mode="before")
    @classmethod
    def normalize_dates(cls, value: Any) -> Any:
        return _normalize_datetime(value)

    @field_validator("tipoDoc")
    @classmethod
    def validate_tipo_doc(cls, value: str) -> str:
        normalized = str(value or "").strip().zfill(2)
        if normalized not in _RETENTION_DOC_TYPES:
            raise ValueError("La retencion solo debe referenciar facturas o notas: 01, 07 u 08.")
        return normalized

    @field_validator("numDoc")
    @classmethod
    def validate_num_doc(cls, value: str) -> str:
        normalized = str(value or "").strip().upper()
        if not _NUM_DOC_REL_RE.match(normalized):
            raise ValueError("El documento relacionado debe tener formato SERIE-CORRELATIVO, ej. F001-123.")
        return normalized

    @field_validator("moneda")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        normalized = str(value or "").strip().upper()
        if normalized not in _CURRENCY_CODES:
            raise ValueError("Moneda no soportada para retenciones. Usa PEN o USD.")
        return normalized

    @model_validator(mode="after")
    def validate_amounts(self):
        imp_total = _normalize_money(self.impTotal)
        imp_pagar = _normalize_money(self.impPagar)
        imp_retenido = _normalize_money(self.impRetenido)
        if imp_retenido <= 0:
            raise ValueError("El monto retenido debe ser mayor a cero.")
        if imp_pagar + imp_retenido > imp_total + Decimal("0.02"):
            raise ValueError("El importe a pagar mas la retencion no debe exceder el total del comprobante.")
        return self


class RetencionCreate(StrictInputModel):
    serie: str = Field(..., min_length=4, max_length=4)
    correlativo: str = Field(..., min_length=1, max_length=8)
    fechaEmision: datetime
    proveedor: RetencionClientCreate
    regimen: str = Field(default="01", min_length=2, max_length=2)
    tasa: Decimal = Field(default=Decimal("3"), gt=0)
    impRetenido: Decimal = Field(..., gt=0)
    impPagado: Decimal = Field(..., gt=0)
    observacion: Optional[str] = Field(default=None, max_length=250)
    details: list[RetencionDetalleCreate] = Field(..., min_length=1, max_length=500)

    @field_validator("fechaEmision", mode="before")
    @classmethod
    def normalize_date(cls, value: Any) -> Any:
        return _normalize_datetime(value)

    @field_validator("serie")
    @classmethod
    def validate_serie(cls, value: str) -> str:
        normalized = str(value or "").strip().upper()
        if not _SERIE_RETENCION_RE.match(normalized):
            raise ValueError("La serie de retencion debe tener 4 caracteres y empezar con R, ej. R001.")
        return normalized

    @field_validator("correlativo")
    @classmethod
    def validate_correlativo(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized.isdigit():
            raise ValueError("El correlativo de retencion debe ser numerico.")
        return normalized

    @field_validator("regimen")
    @classmethod
    def validate_regimen(cls, value: str) -> str:
        normalized = str(value or "").strip().zfill(2)
        if normalized != "01":
            raise ValueError("SUNAT mantiene el regimen de retencion IGV vigente como codigo 01.")
        return normalized

    @field_validator("tasa")
    @classmethod
    def validate_tasa(cls, value: Decimal) -> Decimal:
        normalized = Decimal(str(value)).quantize(Decimal("0.01"))
        if normalized != Decimal("3.00"):
            raise ValueError("La tasa vigente de retencion IGV es 3%.")
        return normalized

    @field_validator("observacion")
    @classmethod
    def normalize_observacion(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class RetencionResponse(BaseModel):
    id: int
    serie: str
    correlativo: str
    fecha_emision: datetime
    proveedor_tipo_doc: str
    proveedor_num_doc: str
    proveedor_rzn_social: str
    regimen: str
    tasa: float
    imp_retenido: float
    imp_pagado: float
    details_count: int
    status: str
    success: bool
    ticket: Optional[str] = None
    sunat_error: Optional[str] = None
    sunat_hash: Optional[str] = None
    provider_endpoint: Optional[str] = None
    provider_status_code: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RetencionPageResponse(BaseModel):
    items: List[RetencionResponse]
    total: int
    skip: int
    limit: int
    counts: Dict[str, int]
