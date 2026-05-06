"""Schemas para reversiones fiscales APISPeru/SUNAT."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from schemas._base import StrictInputModel


_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SERIE_RE = re.compile(r"^[A-Z0-9]{4}$")


def _normalize_datetime(value: Any) -> Any:
    if isinstance(value, str):
        cleaned = value.strip()
        if _DATE_ONLY_RE.match(cleaned):
            return f"{cleaned}T00:00:00-05:00"
        return cleaned
    return value


class ReversionDetalleCreate(StrictInputModel):
    tipoDoc: str = Field(..., min_length=2, max_length=2)
    serie: str = Field(..., min_length=4, max_length=4)
    correlativo: str = Field(..., min_length=1, max_length=8)
    desMotivoBaja: str = Field(..., min_length=3, max_length=250)

    @field_validator("tipoDoc")
    @classmethod
    def validate_tipo_doc(cls, value: str) -> str:
        normalized = str(value or "").strip().zfill(2)
        if normalized not in {"20", "40"}:
            raise ValueError("Las reversiones APISPeru solo admiten retenciones (20) o percepciones (40).")
        return normalized

    @field_validator("serie")
    @classmethod
    def validate_serie(cls, value: str) -> str:
        normalized = str(value or "").strip().upper()
        if not _SERIE_RE.match(normalized):
            raise ValueError("La serie debe tener 4 caracteres alfanumericos.")
        return normalized

    @field_validator("correlativo")
    @classmethod
    def validate_correlativo(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized.isdigit():
            raise ValueError("El correlativo del documento a revertir debe ser numerico.")
        return normalized

    @field_validator("desMotivoBaja")
    @classmethod
    def validate_motivo(cls, value: str) -> str:
        return str(value or "").strip().upper()

    @model_validator(mode="after")
    def validate_serie_prefix(self):
        if self.tipoDoc == "20" and not self.serie.startswith("R"):
            raise ValueError("Las retenciones tipo 20 deben usar serie Rxxx.")
        if self.tipoDoc == "40" and not self.serie.startswith("P"):
            raise ValueError("Las percepciones tipo 40 deben usar serie Pxxx.")
        return self


class ReversionCreate(StrictInputModel):
    correlativo: str = Field(..., min_length=1, max_length=8)
    fecGeneracion: datetime
    fecComunicacion: datetime
    details: list[ReversionDetalleCreate] = Field(..., min_length=1, max_length=500)

    @field_validator("fecGeneracion", "fecComunicacion", mode="before")
    @classmethod
    def normalize_dates(cls, value: Any) -> Any:
        return _normalize_datetime(value)

    @field_validator("correlativo", mode="before")
    @classmethod
    def normalize_correlativo(cls, value: Any) -> str:
        normalized = str(value or "").strip().upper()
        if normalized.startswith("RR-"):
            normalized = normalized.split("-")[-1]
        if not normalized.isdigit():
            raise ValueError("El correlativo de la reversion debe ser numerico; APISPeru construye el prefijo RR.")
        return normalized


class ReversionResponse(BaseModel):
    id: int
    correlativo: str
    fec_generacion: datetime
    fec_comunicacion: datetime
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


class ReversionPageResponse(BaseModel):
    items: List[ReversionResponse]
    total: int
    skip: int
    limit: int
    counts: Dict[str, int]
