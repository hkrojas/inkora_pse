"""Schemas para comprobantes de percepcion APISPeru/SUNAT."""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from schemas._base import StrictInputModel


_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SERIE_PERCEPCION_RE = re.compile(r"^P[A-Z0-9]{3}$")
_NUM_DOC_REL_RE = re.compile(r"^[A-Z0-9]{4}-\d{1,8}$")
_DOC_NUMBER_RE = re.compile(r"^\d{8,11}$")
_PERCEPTION_DOC_TYPES = {"01", "03", "07", "08"}
_CURRENCY_CODES = {"PEN", "USD"}
_REGIMEN_TASA = {
    "01": Decimal("2.00"),
    "02": Decimal("1.00"),
    "03": Decimal("3.50"),
}


def _normalize_datetime(value: Any) -> Any:
    if isinstance(value, str):
        cleaned = value.strip()
        if _DATE_ONLY_RE.match(cleaned):
            return f"{cleaned}T00:00:00-05:00"
        return cleaned
    return value


def _normalize_money(value: Any) -> Decimal:
    return Decimal(str(value or "0")).quantize(Decimal("0.01"))


class PercepcionClientCreate(StrictInputModel):
    tipoDoc: str = Field(default="6", min_length=1, max_length=1)
    numDoc: str = Field(..., min_length=8, max_length=11)
    rznSocial: str = Field(..., min_length=2, max_length=180)

    @field_validator("tipoDoc")
    @classmethod
    def validate_tipo_doc(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if normalized not in {"1", "6"}:
            raise ValueError("El cliente de una percepcion debe usar DNI (1) o RUC (6).")
        return normalized

    @field_validator("numDoc")
    @classmethod
    def validate_num_doc(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if not _DOC_NUMBER_RE.match(normalized):
            raise ValueError("El documento del cliente debe tener 8 a 11 digitos.")
        return normalized

    @model_validator(mode="after")
    def validate_doc_length(self):
        if self.tipoDoc == "1" and len(self.numDoc) != 8:
            raise ValueError("El DNI debe tener 8 digitos.")
        if self.tipoDoc == "6" and len(self.numDoc) != 11:
            raise ValueError("El RUC debe tener 11 digitos.")
        return self

    @field_validator("rznSocial")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return str(value or "").strip()


class PercepcionPaymentCreate(StrictInputModel):
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
            raise ValueError("Moneda no soportada para percepciones. Usa PEN o USD.")
        return normalized


class PercepcionExchangeCreate(StrictInputModel):
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
            raise ValueError("Moneda no soportada para tipo de cambio de percepcion.")
        return normalized


class PercepcionDetalleCreate(StrictInputModel):
    tipoDoc: str = Field(..., min_length=2, max_length=2)
    numDoc: str = Field(..., min_length=6, max_length=13)
    fechaEmision: datetime
    impTotal: Decimal = Field(..., gt=0)
    moneda: str = Field(default="PEN", min_length=3, max_length=3)
    cobros: list[PercepcionPaymentCreate] = Field(..., min_length=1, max_length=50)
    fechaPercepcion: datetime
    impPercibido: Decimal = Field(..., ge=0)
    impCobrar: Decimal = Field(..., gt=0)
    tipoCambio: Optional[PercepcionExchangeCreate] = None

    @field_validator("fechaEmision", "fechaPercepcion", mode="before")
    @classmethod
    def normalize_dates(cls, value: Any) -> Any:
        return _normalize_datetime(value)

    @field_validator("tipoDoc")
    @classmethod
    def validate_tipo_doc(cls, value: str) -> str:
        normalized = str(value or "").strip().zfill(2)
        if normalized not in _PERCEPTION_DOC_TYPES:
            raise ValueError("La percepcion solo debe referenciar comprobantes 01, 03, 07 u 08.")
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
            raise ValueError("Moneda no soportada para percepciones. Usa PEN o USD.")
        return normalized

    @model_validator(mode="after")
    def validate_amounts(self):
        imp_total = _normalize_money(self.impTotal)
        imp_cobrar = _normalize_money(self.impCobrar)
        imp_percibido = _normalize_money(self.impPercibido)
        if imp_percibido <= 0:
            raise ValueError("El monto percibido debe ser mayor a cero.")
        if imp_cobrar < imp_total:
            raise ValueError("El importe a cobrar debe incluir el total del comprobante mas la percepcion.")
        if imp_cobrar < imp_total + imp_percibido - Decimal("0.02"):
            raise ValueError("El importe a cobrar debe incluir la percepcion.")
        return self


class PercepcionCreate(StrictInputModel):
    serie: str = Field(..., min_length=4, max_length=4)
    correlativo: str = Field(..., min_length=1, max_length=8)
    fechaEmision: datetime
    proveedor: PercepcionClientCreate
    regimen: str = Field(default="01", min_length=2, max_length=2)
    tasa: Decimal = Field(default=Decimal("2"), gt=0)
    impPercibido: Decimal = Field(..., gt=0)
    impCobrado: Decimal = Field(..., gt=0)
    observacion: Optional[str] = Field(default=None, max_length=250)
    details: list[PercepcionDetalleCreate] = Field(..., min_length=1, max_length=500)

    @field_validator("fechaEmision", mode="before")
    @classmethod
    def normalize_date(cls, value: Any) -> Any:
        return _normalize_datetime(value)

    @field_validator("serie")
    @classmethod
    def validate_serie(cls, value: str) -> str:
        normalized = str(value or "").strip().upper()
        if not _SERIE_PERCEPCION_RE.match(normalized):
            raise ValueError("La serie de percepcion debe tener 4 caracteres y empezar con P, ej. P001.")
        return normalized

    @field_validator("correlativo")
    @classmethod
    def validate_correlativo(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized.isdigit():
            raise ValueError("El correlativo de percepcion debe ser numerico.")
        return normalized

    @field_validator("regimen")
    @classmethod
    def validate_regimen(cls, value: str) -> str:
        normalized = str(value or "").strip().zfill(2)
        if normalized not in _REGIMEN_TASA:
            raise ValueError("Regimen de percepcion no soportado. Usa 01, 02 o 03.")
        return normalized

    @model_validator(mode="after")
    def validate_tasa_por_regimen(self):
        expected = _REGIMEN_TASA[self.regimen]
        actual = Decimal(str(self.tasa)).quantize(Decimal("0.01"))
        if actual != expected:
            raise ValueError(f"La tasa del regimen {self.regimen} debe ser {expected}%.")
        return self

    @field_validator("observacion")
    @classmethod
    def normalize_observacion(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class PercepcionResponse(BaseModel):
    id: int
    serie: str
    correlativo: str
    fecha_emision: datetime
    cliente_tipo_doc: str
    cliente_num_doc: str
    cliente_rzn_social: str
    regimen: str
    tasa: float
    imp_percibido: float
    imp_cobrado: float
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


class PercepcionPageResponse(BaseModel):
    items: List[PercepcionResponse]
    total: int
    skip: int
    limit: int
    counts: Dict[str, int]
