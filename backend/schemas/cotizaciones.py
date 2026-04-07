"""schemas/cotizaciones.py — Cotizacion, Pago, Cobranza, Facturación schemas."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from schemas._base import StrictInputModel
from schemas.auth import UserResponse
from schemas.clientes import ClienteResponse


class CotizacionItemCreate(BaseModel):
    producto_id: Optional[int] = None
    descripcion: str
    cantidad: Decimal = Field(..., gt=0)
    precio_unitario: Decimal = Field(..., gt=0)
    unidad_medida: Optional[str] = None
    tipo_afectacion_igv: Optional[str] = None


class CotizacionItemResponse(BaseModel):
    id: int
    producto_id: Optional[int] = None
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    valor_unitario: Decimal
    total_base_igv: Decimal
    total_igv: Decimal
    total_item: Decimal
    unidad_medida: str
    tipo_afectacion_igv: str
    model_config = ConfigDict(from_attributes=True)


class CotizacionCreate(BaseModel):
    cliente_id: int
    fecha_vencimiento: Optional[datetime] = None
    moneda: str = "PEN"
    tipo_comprobante: str = "00"
    observaciones: Optional[str] = None
    condicion_pago: Optional[str] = None
    items: List[CotizacionItemCreate]


class PagoCreate(StrictInputModel):
    monto_pagado: Decimal = Field(..., gt=0)
    metodo_pago: str
    fecha_pago: Optional[datetime] = None
    referencia_operacion: Optional[str] = None
    tipo: str = "adelanto"


class PagoResponse(BaseModel):
    id: int
    cotizacion_id: int
    source_quote_id: Optional[int] = None
    fiscal_document_id: Optional[int] = None
    internal_order_number: Optional[str] = None
    monto_pagado: Decimal
    metodo_pago: str
    fecha_pago: datetime
    referencia_operacion: Optional[str] = None
    tipo: str
    model_config = ConfigDict(from_attributes=True)


class CotizacionResponse(BaseModel):
    id: int
    uuid_publico: Optional[str] = None
    serie: str
    correlativo: Optional[int] = 0
    fecha_emision: datetime
    fecha_vencimiento: Optional[datetime]
    moneda: str = "PEN"
    estado: str
    document_kind: str = "quotation"
    source_quote_id: Optional[int] = None
    internal_order_number: Optional[str] = None
    document_number: Optional[str] = None
    linked_fiscal_document_id: Optional[int] = None
    linked_fiscal_document_number: Optional[str] = None
    linked_fiscal_document_status: Optional[str] = None
    payment_status: str = "pendiente"
    observaciones: Optional[str] = None
    condicion_pago: Optional[str] = None
    cliente: ClienteResponse
    usuario: UserResponse
    items: List[CotizacionItemResponse]
    total_gravada: Decimal
    total_igv: Decimal
    total_venta: Decimal

    tipo_comprobante: str
    sunat_xml_url: Optional[str] = None
    sunat_pdf_url: Optional[str] = None
    sunat_cdr_url: Optional[str] = None
    sunat_error: Optional[str] = None

    monto_pagado: Decimal = Decimal("0.00")
    saldo_pendiente: Decimal = Decimal("0.00")
    pagos: List[PagoResponse] = []

    model_config = ConfigDict(from_attributes=True)


class CobranzaResumenResponse(BaseModel):
    total_por_cobrar: Decimal
    total_vencido: Decimal
    total_pagado_mes: Decimal
    documentos_pendientes: int
    documentos_vencidos: int
    documentos_pagados_mes: int


class CobranzaVencidaItem(BaseModel):
    cotizacion_id: int
    document_number: Optional[str] = None
    internal_order_number: Optional[str] = None
    cliente_nombre: str
    cliente_documento: str
    fecha_vencimiento: Optional[datetime] = None
    total_venta: Decimal
    monto_pagado: Decimal
    saldo_pendiente: Decimal
    dias_vencido: int
    model_config = ConfigDict(from_attributes=True)


class FacturarPayload(StrictInputModel):
    tipo_comprobante: str


class NotaCreate(StrictInputModel):
    comprobante_afectado_id: int
    tipo_nota: str
    cod_motivo: str
    descripcion_motivo: str


class AnulacionCreate(StrictInputModel):
    comprobante_id: int
    motivo: str


class DescargaArchivoPayload(StrictInputModel):
    comprobante_id: int
