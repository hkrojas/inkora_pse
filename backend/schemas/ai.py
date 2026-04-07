"""schemas/ai.py — AI / Gemini schemas."""
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


class AIItemCotizacion(BaseModel):
    descripcion: str
    cantidad: Decimal
    material: Optional[str] = None


class AIParsedCotizacionResponse(BaseModel):
    cliente_sugerido: Optional[str] = None
    items: List[AIItemCotizacion]


class AIInsumoFactura(BaseModel):
    nombre: str
    cantidad: Decimal


class AIParsedFacturaResponse(BaseModel):
    insumos: List[AIInsumoFactura]
