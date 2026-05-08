"""schemas/clientes.py — Cliente schemas."""
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from services.phone_validation import normalize_and_validate_optional_peru_mobile


CONDICION_PAGO_VALORES = {
    "contado", "credito_7", "credito_15", "credito_30", "credito_60",
}
TIPO_DOCUMENTO_VALORES = {"0", "1", "4", "6", "7", "A"}


class ClienteBase(BaseModel):
    tipo_documento: str = "1"
    numero_documento: str
    razon_social: str
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

    @field_validator("tipo_documento")
    @classmethod
    def validate_tipo_documento(cls, value: str) -> str:
        normalized = str(value or "").strip().upper()
        if normalized not in TIPO_DOCUMENTO_VALORES:
            raise ValueError("tipo_documento no es valido.")
        return normalized

    @field_validator("numero_documento")
    @classmethod
    def validate_numero_documento(cls, value: str, info) -> str:
        numero = str(value or "").strip().upper().replace(" ", "")
        tipo_documento = (
            str(info.data.get("tipo_documento", "")).strip().upper()
            if info.data else ""
        )

        if not numero:
            raise ValueError("numero_documento es obligatorio.")
        if tipo_documento == "6" and not numero.isdigit():
            raise ValueError("RUC debe contener solo digitos.")
        if tipo_documento == "6" and len(numero) != 11:
            raise ValueError("RUC debe tener exactamente 11 digitos.")
        if tipo_documento == "1" and not numero.isdigit():
            raise ValueError("DNI debe contener solo digitos.")
        if tipo_documento == "1" and len(numero) != 8:
            raise ValueError("DNI debe tener exactamente 8 digitos.")
        if len(numero) < 3 or len(numero) > 15:
            raise ValueError("numero_documento debe tener entre 3 y 15 caracteres.")
        return numero

    @field_validator("razon_social")
    @classmethod
    def validate_razon_social(cls, value: str) -> str:
        razon_social = str(value or "").strip()
        if not razon_social:
            raise ValueError("razon_social es obligatoria.")
        return razon_social

    @field_validator("ubigeo")
    @classmethod
    def validate_ubigeo(cls, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return None
        ubigeo = str(value).strip()
        if not ubigeo.isdigit() or len(ubigeo) != 6:
            raise ValueError("Ubigeo debe tener exactamente 6 digitos.")
        return ubigeo


class ClienteCreate(ClienteBase):
    @field_validator("telefono", "whatsapp")
    @classmethod
    def validate_mobile_fields(cls, value: Optional[str], info) -> Optional[str]:
        label = "WhatsApp" if info.field_name == "whatsapp" else "Telefono"
        return normalize_and_validate_optional_peru_mobile(value, label)


class ClienteUpdate(BaseModel):
    tipo_documento: Optional[str] = None
    numero_documento: Optional[str] = None
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

    @field_validator("telefono", "whatsapp")
    @classmethod
    def validate_mobile_fields(cls, value: Optional[str], info) -> Optional[str]:
        label = "WhatsApp" if info.field_name == "whatsapp" else "Telefono"
        return normalize_and_validate_optional_peru_mobile(value, label)

    @field_validator("tipo_documento")
    @classmethod
    def validate_tipo_documento(cls, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return value
        normalized = str(value).strip().upper()
        if normalized not in TIPO_DOCUMENTO_VALORES:
            raise ValueError("tipo_documento no es valido.")
        return normalized

    @field_validator("numero_documento")
    @classmethod
    def validate_numero_documento(cls, value: Optional[str], info) -> Optional[str]:
        if value in (None, ""):
            return value
        numero = str(value).strip().upper().replace(" ", "")
        tipo_documento = (
            str(info.data.get("tipo_documento", "")).strip().upper()
            if info.data else ""
        )
        if tipo_documento == "6" and not numero.isdigit():
            raise ValueError("RUC debe contener solo digitos.")
        if tipo_documento == "6" and len(numero) != 11:
            raise ValueError("RUC debe tener exactamente 11 digitos.")
        if tipo_documento == "1" and not numero.isdigit():
            raise ValueError("DNI debe contener solo digitos.")
        if tipo_documento == "1" and len(numero) != 8:
            raise ValueError("DNI debe tener exactamente 8 digitos.")
        if len(numero) < 3 or len(numero) > 15:
            raise ValueError("numero_documento debe tener entre 3 y 15 caracteres.")
        return numero

    @field_validator("razon_social")
    @classmethod
    def validate_razon_social(cls, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return value
        razon_social = str(value).strip()
        if not razon_social:
            raise ValueError("razon_social es obligatoria.")
        return razon_social

    @field_validator("ubigeo")
    @classmethod
    def validate_ubigeo(cls, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return value
        ubigeo = str(value).strip()
        if not ubigeo.isdigit() or len(ubigeo) != 6:
            raise ValueError("Ubigeo debe tener exactamente 6 digitos.")
        return ubigeo


class ClienteResponse(ClienteBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class ClienteSearchResponse(BaseModel):
    id: int
    tipo_documento: Optional[str] = None
    numero_documento: Optional[str] = None
    razon_social: Optional[str] = None
    nombre_comercial: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    whatsapp: Optional[str] = None
    direccion: Optional[str] = None
    ubigeo: Optional[str] = None
    condicion_pago: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ClientePageResponse(BaseModel):
    items: List[ClienteResponse]
    total: int
    skip: int
    limit: int
    counts: Dict[str, int]
