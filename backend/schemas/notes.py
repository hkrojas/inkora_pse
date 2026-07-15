from __future__ import annotations

from decimal import Decimal
from typing import Any, List, Optional

from pydantic import Field, field_validator, model_validator

from schemas._base import StrictInputModel


CREDIT_NOTE_MOTIVES = {
    "01", "02", "03", "04", "05", "06", "07",
    "08", "09", "10", "11", "12", "13",
}
DEBIT_NOTE_MOTIVES = {"01", "02", "03", "13"}
NOTE_ADJUSTMENT_MODES = {"full", "global", "lines", "payment_terms", "charge"}


class NoteAdjustmentLine(StrictInputModel):
    source_item_id: Optional[int] = None
    quantity: Optional[Decimal] = Field(default=None, gt=0)
    amount: Optional[Decimal] = Field(default=None, ge=0)
    percentage: Optional[Decimal] = Field(default=None, gt=0, le=100)
    description: Optional[str] = Field(default=None, max_length=500)
    tax_affectation: Optional[str] = Field(default=None, max_length=2)


class FiscalNoteDraftCreate(StrictInputModel):
    comprobante_afectado_id: int
    tipo_nota: str
    cod_motivo: str = Field(..., min_length=2, max_length=2)
    descripcion_motivo: str = Field(..., min_length=3, max_length=250)
    adjustment_mode: str
    input_type: Optional[str] = None
    input_value: Optional[Decimal] = Field(default=None, ge=0)
    lines: List[NoteAdjustmentLine] = Field(default_factory=list)
    payment_terms: Optional[dict[str, Any]] = None
    inventory_impact: str = "none"
    inventory_return_warehouse_id: Optional[int] = None

    @field_validator("tipo_nota")
    @classmethod
    def normalize_note_type(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        aliases = {"07": "credito", "nc": "credito", "08": "debito", "nd": "debito"}
        normalized = aliases.get(normalized, normalized)
        if normalized not in {"credito", "debito"}:
            raise ValueError("Tipo de nota invalido.")
        return normalized

    @field_validator("cod_motivo")
    @classmethod
    def normalize_motive(cls, value: str) -> str:
        return str(value or "").strip().zfill(2)

    @field_validator("descripcion_motivo")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        return str(value or "").strip()

    @field_validator("adjustment_mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in NOTE_ADJUSTMENT_MODES:
            raise ValueError("Modalidad de ajuste invalida.")
        return normalized

    @field_validator("input_type")
    @classmethod
    def validate_input_type(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = str(value).strip().lower()
        if normalized not in {"amount", "percentage"}:
            raise ValueError("Tipo de importe invalido.")
        return normalized

    @field_validator("inventory_impact")
    @classmethod
    def validate_inventory_impact(cls, value: str) -> str:
        normalized = str(value or "none").strip().lower()
        if normalized not in {"none", "undelivered", "physical_return"}:
            raise ValueError("Impacto de inventario invalido.")
        return normalized

    @model_validator(mode="after")
    def validate_contract(self):
        allowed = CREDIT_NOTE_MOTIVES if self.tipo_nota == "credito" else DEBIT_NOTE_MOTIVES
        if self.cod_motivo not in allowed:
            raise ValueError("Motivo SUNAT invalido para el tipo de nota seleccionado.")
        if self.tipo_nota == "debito" and self.inventory_impact != "none":
            raise ValueError("Las notas de debito no afectan inventario.")
        if self.inventory_impact != "none" and self.cod_motivo not in {"01", "06", "07"}:
            raise ValueError("El motivo seleccionado no puede modificar inventario.")
        if self.inventory_impact == "physical_return" and not self.inventory_return_warehouse_id:
            raise ValueError("Seleccione el almacen que recibira la devolucion fisica.")
        return self


class FiscalNoteDraftUpdate(FiscalNoteDraftCreate):
    comprobante_afectado_id: int
