"""schemas/guias.py — Guia de Remision schemas."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class GuiaRemisionItemCreate(BaseModel):
    descripcion: str
    cantidad: Decimal = Field(..., gt=0)
    unidad_medida: str = "NIU"
    codigo_producto: Optional[str] = None
    peso_item: Optional[Decimal] = None


class GuiaRemisionCreate(BaseModel):
    cotizacion_id: Optional[int] = None
    fecha_traslado: datetime
    motivo_traslado: str = "01"
    descripcion_motivo: Optional[str] = None
    peso_bruto_total: Decimal = Field(..., gt=0)
    unidad_medida_peso: str = "KGM"
    numero_bultos: Optional[int] = None
    modalidad_traslado: str = "01"

    transportista_ruc: Optional[str] = None
    transportista_razon_social: Optional[str] = None

    conductor_tipo_doc: Optional[str] = "1"
    conductor_nro_doc: Optional[str] = None
    conductor_nombres: Optional[str] = None
    conductor_apellidos: Optional[str] = None
    conductor_licencia: Optional[str] = None
    vehiculo_placa: Optional[str] = None

    partida_ubigeo: Optional[str] = None
    partida_direccion: str
    llegada_ubigeo: Optional[str] = None
    llegada_direccion: str

    items: List[GuiaRemisionItemCreate]


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
    conductor_nombres: Optional[str] = None
    conductor_apellidos: Optional[str] = None
    conductor_licencia: Optional[str] = None
    vehiculo_placa: Optional[str] = None
    partida_ubigeo: Optional[str] = None
    partida_direccion: Optional[str] = None
    llegada_ubigeo: Optional[str] = None
    llegada_direccion: Optional[str] = None
    sunat_xml_url: Optional[str] = None
    sunat_pdf_url: Optional[str] = None
    sunat_cdr_url: Optional[str] = None
    sunat_error: Optional[str] = None
    items: List[GuiaRemisionItemResponse] = []
    model_config = ConfigDict(from_attributes=True)
