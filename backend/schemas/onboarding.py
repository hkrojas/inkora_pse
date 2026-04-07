"""schemas/onboarding.py — Importación masiva y checklist de onboarding."""
from typing import List

from pydantic import BaseModel


class ImportErrorDetail(BaseModel):
    fila: int
    campo: str
    mensaje: str


class ImportResultResponse(BaseModel):
    importados: int
    omitidos: int
    errores: List[ImportErrorDetail]


class OnboardingChecklistItem(BaseModel):
    item: str
    titulo: str
    descripcion: str
    completado: bool


class OnboardingEstadoResponse(BaseModel):
    onboarding_status: str
    completados: int
    total: int
    porcentaje: int
    checklist: List[OnboardingChecklistItem]
