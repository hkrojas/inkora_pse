"""schemas/clientes.py — Cliente schemas."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


CONDICION_PAGO_VALORES = {
    "contado", "credito_7", "credito_15", "credito_30", "credito_60",
}


class ClienteBase(BaseModel):
    tipo_documento: str = "1"
    numero_documento: str = Field(..., min_length=8, max_length=15)
    razon_social: str = Field(...)
    nombre_comercial: Optional[str] = None
    direccion: Optional[str] = None
    ubigeo: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    whatsapp: Optional[str] = None
    contacto: Optional[str] = None
    condicion_pago: Optional[str] = None
    direccion_entrega: Optional[str] = None
    observaciones: Optional[str] = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    tipo_documento: Optional[str] = None
    numero_documento: Optional[str] = Field(default=None, min_length=8, max_length=15)
    razon_social: Optional[str] = None
    nombre_comercial: Optional[str] = None
    direccion: Optional[str] = None
    ubigeo: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    whatsapp: Optional[str] = None
    contacto: Optional[str] = None
    condicion_pago: Optional[str] = None
    direccion_entrega: Optional[str] = None
    observaciones: Optional[str] = None


class ClienteResponse(ClienteBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
