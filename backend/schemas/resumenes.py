"""Schemas para resumen diario de boletas."""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from schemas._base import StrictInputModel


_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SERIE_NRO_RE = re.compile(r"^[A-Z0-9]{4}-\d{1,8}$")
_BATCH_CORRELATIVO_RE = re.compile(r"^\d{8}-\d+(?:-\d+)?$")


def _normalize_datetime(value: Any) -> Any:
    if isinstance(value, str):
        cleaned = value.strip()
        if _DATE_ONLY_RE.match(cleaned):
            return f"{cleaned}T00:00:00-05:00"
        return cleaned
    return value


class ResumenDiarioDocReferencia(StrictInputModel):
    tipoDoc: str = Field(..., min_length=2, max_length=2)
    nroDoc: str = Field(..., min_length=3, max_length=20)

    @field_validator("tipoDoc")
    @classmethod
    def validate_tipo_doc(cls, value: str) -> str:
        normalized = str(value or "").strip().zfill(2)
        if normalized not in {"03", "07", "08"}:
            raise ValueError("El documento de referencia debe ser boleta o nota vinculada a boleta.")
        return normalized

    @field_validator("nroDoc")
    @classmethod
    def validate_nro_doc(cls, value: str) -> str:
        normalized = str(value or "").strip().upper()
        if not _SERIE_NRO_RE.match(normalized):
            raise ValueError("El numero referenciado debe usar formato SERIE-NUMERO.")
        return normalized


class ResumenDiarioPercepcion(StrictInputModel):
    codReg: str = Field(..., min_length=2, max_length=2)
    tasa: Decimal = Field(..., ge=0)
    mtoBase: Decimal = Field(..., ge=0)
    mto: Decimal = Field(..., ge=0)
    mtoTotal: Decimal = Field(..., ge=0)


class ResumenDiarioDetalleCreate(StrictInputModel):
    tipoDoc: str = Field(default="03", min_length=2, max_length=2)
    serieNro: str = Field(..., min_length=6, max_length=20)
    clienteTipo: str = Field(default="1", min_length=1, max_length=1)
    clienteNro: str = Field(default="00000000", min_length=1, max_length=15)
    docReferencia: Optional[ResumenDiarioDocReferencia] = None
    percepcion: Optional[ResumenDiarioPercepcion] = None
    estado: str = Field(default="1", min_length=1, max_length=1)
    total: Decimal = Field(..., ge=0)
    mtoOperGravadas: Decimal = Field(default=Decimal("0.00"), ge=0)
    mtoOperInafectas: Decimal = Field(default=Decimal("0.00"), ge=0)
    mtoOperExoneradas: Decimal = Field(default=Decimal("0.00"), ge=0)
    mtoOperExportacion: Decimal = Field(default=Decimal("0.00"), ge=0)
    mtoOperGratuitas: Decimal = Field(default=Decimal("0.00"), ge=0)
    mtoOtrosCargos: Decimal = Field(default=Decimal("0.00"), ge=0)
    mtoIGV: Decimal = Field(default=Decimal("0.00"), ge=0)
    mtoIvap: Decimal = Field(default=Decimal("0.00"), ge=0)
    mtoIcbper: Decimal = Field(default=Decimal("0.00"), ge=0)
    mtoISC: Decimal = Field(default=Decimal("0.00"), ge=0)
    mtoOtrosTributos: Decimal = Field(default=Decimal("0.00"), ge=0)
    desMotivoBaja: Optional[str] = Field(default=None, max_length=250)

    @field_validator("tipoDoc")
    @classmethod
    def validate_tipo_doc(cls, value: str) -> str:
        normalized = str(value or "").strip().zfill(2)
        if normalized not in {"03", "07", "08"}:
            raise ValueError("El resumen diario solo admite boletas y notas asociadas a boletas.")
        return normalized

    @field_validator("serieNro")
    @classmethod
    def validate_serie_nro(cls, value: str) -> str:
        normalized = str(value or "").strip().upper()
        if not _SERIE_NRO_RE.match(normalized):
            raise ValueError("Use formato SERIE-NUMERO, por ejemplo B001-000001.")
        return normalized

    @field_validator("clienteTipo")
    @classmethod
    def validate_cliente_tipo(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if normalized not in {"0", "1", "4", "6", "7"}:
            raise ValueError("Tipo de documento de cliente invalido para resumen diario.")
        return normalized

    @field_validator("clienteNro")
    @classmethod
    def normalize_cliente_nro(cls, value: str) -> str:
        return str(value or "").strip() or "00000000"

    @field_validator("estado")
    @classmethod
    def validate_estado(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if normalized not in {"1", "2", "3"}:
            raise ValueError("Estado de resumen invalido. Use 1, 2 o 3.")
        return normalized

    @model_validator(mode="after")
    def validate_reference_for_notes(self):
        if self.tipoDoc in {"07", "08"} and not self.docReferencia:
            raise ValueError("Las notas 07/08 en resumen diario requieren documento de referencia.")
        return self


class ResumenDiarioCreate(StrictInputModel):
    correlativo: str = Field(..., min_length=1, max_length=24)
    fecGeneracion: datetime
    fecResumen: datetime
    moneda: str = Field(default="PEN", min_length=3, max_length=3)
    details: list[ResumenDiarioDetalleCreate] = Field(..., min_length=1, max_length=500)

    @field_validator("fecGeneracion", "fecResumen", mode="before")
    @classmethod
    def normalize_dates(cls, value: Any) -> Any:
        return _normalize_datetime(value)

    @field_validator("correlativo", mode="before")
    @classmethod
    def normalize_correlativo(cls, value: Any) -> str:
        normalized = str(value or "").strip().upper()
        if normalized.startswith("RC-"):
            normalized = normalized[3:]
        if not (normalized.isdigit() or _BATCH_CORRELATIVO_RE.match(normalized)):
            raise ValueError("El correlativo del resumen debe ser numerico o usar formato RC-YYYYMMDD-N.")
        return normalized

    @field_validator("moneda")
    @classmethod
    def validate_moneda(cls, value: str) -> str:
        normalized = str(value or "PEN").strip().upper()
        if normalized not in {"PEN", "USD"}:
            raise ValueError("Moneda invalida para resumen diario.")
        return normalized


class ResumenDiarioResponse(BaseModel):
    id: int
    correlativo: str
    fec_generacion: datetime
    fec_resumen: datetime
    moneda: str
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


class ResumenDiarioPageResponse(BaseModel):
    items: List[ResumenDiarioResponse]
    total: int
    skip: int
    limit: int
    counts: Dict[str, int]
