"""schemas/guias.py — Guia de Remision schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fiscal_catalogs import (
    PRODUCT_INTERNAL_CODE_MAX_LENGTH,
    normalize_internal_product_code,
    normalize_sunat_unit_code,
)


class GuiaRemisionItemCreate(BaseModel):
    descripcion: str = Field(..., min_length=1, max_length=500)
    cantidad: Decimal = Field(..., gt=0)
    unidad_medida: str = "NIU"
    codigo_producto: Optional[str] = Field(
        default=None,
        max_length=PRODUCT_INTERNAL_CODE_MAX_LENGTH,
    )
    peso_item: Optional[Decimal] = None

    @field_validator("descripcion")
    @classmethod
    def normalize_descripcion(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("La descripcion del bien es obligatoria")
        return normalized

    @field_validator("unidad_medida")
    @classmethod
    def validate_unidad_medida(cls, value: str) -> str:
        return normalize_sunat_unit_code(value)

    @field_validator("codigo_producto")
    @classmethod
    def normalize_codigo_producto(cls, value: Optional[str]) -> Optional[str]:
        return normalize_internal_product_code(value)


class GuiaRemisionCreate(BaseModel):
    cotizacion_id: Optional[int] = None
    cliente_id: Optional[int] = None
    fecha_traslado: datetime
    motivo_traslado: str = "01"
    descripcion_motivo: Optional[str] = None
    peso_bruto_total: Decimal = Field(..., gt=0)
    unidad_medida_peso: str = "KGM"
    numero_bultos: Optional[int] = None
    modalidad_traslado: str = "01"
    sustento_peso: Optional[str] = None
    ind_transbordo: Optional[bool] = False
    num_contenedor: Optional[str] = None
    cod_puerto: Optional[str] = None

    transportista_ruc: Optional[str] = None
    transportista_razon_social: Optional[str] = None
    transportista_nro_mtc: Optional[str] = None

    conductor_tipo_doc: Optional[str] = "1"
    conductor_nro_doc: Optional[str] = None
    conductor_nombres: Optional[str] = None
    conductor_apellidos: Optional[str] = None
    conductor_licencia: Optional[str] = None
    vehiculo_placa: Optional[str] = None
    vehiculo_nro_circulacion: Optional[str] = None
    vehiculo_cod_emisor: Optional[str] = None
    vehiculo_nro_autorizacion: Optional[str] = None

    partida_ubigeo: Optional[str] = None
    partida_direccion: str
    llegada_ubigeo: Optional[str] = None
    llegada_direccion: str

    items: List[GuiaRemisionItemCreate]

    @field_validator("unidad_medida_peso")
    @classmethod
    def validate_unidad_medida_peso(cls, value: str) -> str:
        return normalize_sunat_unit_code(value)


class GuiaRemisionItemResponse(BaseModel):
    id: int
    descripcion: str
    cantidad: Decimal
    unidad_medida: str
    codigo_producto: Optional[str] = None
    peso_item: Optional[Decimal] = None
    model_config = ConfigDict(from_attributes=True)


class EtiquetaGuiaResponse(BaseModel):
    guia_id: int
    numero_guia: Optional[str] = None
    fecha_traslado: Optional[datetime] = None
    remitente_nombre: str
    remitente_ruc: str
    remitente_direccion: Optional[str] = None
    destinatario_nombre: Optional[str] = None
    destinatario_documento: Optional[str] = None
    destinatario_direccion: Optional[str] = None
    partida_direccion: Optional[str] = None
    llegada_direccion: Optional[str] = None
    peso_bruto_total: Optional[Decimal] = None
    numero_bultos: Optional[int] = None
    motivo_traslado: str
    items: List[GuiaRemisionItemResponse] = []
    model_config = ConfigDict(from_attributes=True)


class GuiaRemisionResponse(BaseModel):
    id: int
    serie: str
    correlativo: Optional[int] = 0
    fecha_emision: datetime
    fecha_traslado: datetime
    estado: str
    cotizacion_id: Optional[int] = None
    cliente_id: Optional[int] = None
    source_quote_id: Optional[int] = None
    fiscal_document_id: Optional[int] = None
    internal_order_number: Optional[str] = None
    motivo_traslado: str
    descripcion_motivo: Optional[str] = None
    peso_bruto_total: Decimal
    unidad_medida_peso: str
    modalidad_traslado: str
    sustento_peso: Optional[str] = None
    ind_transbordo: Optional[bool] = None
    num_contenedor: Optional[str] = None
    cod_puerto: Optional[str] = None
    transportista_ruc: Optional[str] = None
    transportista_razon_social: Optional[str] = None
    transportista_nro_mtc: Optional[str] = None
    conductor_nro_doc: Optional[str] = None
    conductor_nombres: Optional[str] = None
    conductor_apellidos: Optional[str] = None
    conductor_licencia: Optional[str] = None
    vehiculo_placa: Optional[str] = None
    vehiculo_nro_circulacion: Optional[str] = None
    vehiculo_cod_emisor: Optional[str] = None
    vehiculo_nro_autorizacion: Optional[str] = None
    partida_ubigeo: Optional[str] = None
    partida_direccion: Optional[str] = None
    llegada_ubigeo: Optional[str] = None
    llegada_direccion: Optional[str] = None
    cliente_nombre: Optional[str] = None
    cliente_documento: Optional[str] = None
    sunat_xml_url: Optional[str] = None
    sunat_pdf_url: Optional[str] = None
    sunat_cdr_url: Optional[str] = None
    sunat_hash: Optional[str] = None
    sunat_ticket: Optional[str] = None
    provider_endpoint: Optional[str] = None
    provider_status_code: Optional[int] = None
    sunat_status_checked_at: Optional[datetime] = None
    sunat_error: Optional[str] = None
    items: List[GuiaRemisionItemResponse] = []
    model_config = ConfigDict(from_attributes=True)


class GuiaRemisionListResponse(BaseModel):
    id: int
    serie: str
    correlativo: Optional[int] = 0
    fecha_emision: datetime
    fecha_traslado: datetime
    estado: str
    cotizacion_id: Optional[int] = None
    cliente_id: Optional[int] = None
    source_quote_id: Optional[int] = None
    fiscal_document_id: Optional[int] = None
    internal_order_number: Optional[str] = None
    motivo_traslado: str
    descripcion_motivo: Optional[str] = None
    peso_bruto_total: Decimal
    unidad_medida_peso: str
    modalidad_traslado: str
    transportista_ruc: Optional[str] = None
    transportista_razon_social: Optional[str] = None
    conductor_nro_doc: Optional[str] = None
    conductor_licencia: Optional[str] = None
    vehiculo_placa: Optional[str] = None
    partida_ubigeo: Optional[str] = None
    partida_direccion: Optional[str] = None
    llegada_ubigeo: Optional[str] = None
    llegada_direccion: Optional[str] = None
    cliente_nombre: Optional[str] = None
    cliente_documento: Optional[str] = None
    sunat_hash: Optional[str] = None
    sunat_ticket: Optional[str] = None
    provider_endpoint: Optional[str] = None
    provider_status_code: Optional[int] = None
    sunat_status_checked_at: Optional[datetime] = None
    sunat_xml_url: Optional[str] = None
    sunat_pdf_url: Optional[str] = None
    sunat_cdr_url: Optional[str] = None
    sunat_error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class GuiaRemisionCountsResponse(BaseModel):
    all: int = 0
    pending: int = 0
    smartpse: int = 0
    transit: int = 0
    emitted: int = 0
    cancelled: int = 0
    voided: int = 0


class GuiaRemisionPageResponse(BaseModel):
    items: List[GuiaRemisionListResponse]
    total: int
    skip: int
    limit: int
    counts: GuiaRemisionCountsResponse


class SmartPSEGuideReconcileRequest(BaseModel):
    mark_as_emitida: bool = False
    cdr_url: Optional[str] = None
    sunat_hash: Optional[str] = None
    sunat_ticket: Optional[str] = None
    provider_response: Optional[Dict[str, Any]] = None
    note: Optional[str] = Field(default=None, max_length=500)

    model_config = ConfigDict(extra="forbid")
