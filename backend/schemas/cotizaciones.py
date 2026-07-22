"""schemas/cotizaciones.py — Cotizacion, Pago, Cobranza, Facturación schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from fiscal_catalogs import (
    PRODUCT_INTERNAL_CODE_MAX_LENGTH,
    normalize_internal_product_code,
    normalize_sunat_unit_code,
    normalize_tax_affectation_code,
)
from schemas._base import StrictInputModel
from schemas.auth import UserResponse
from schemas.clientes import ClienteResponse
from services.bank_account_validation import validate_and_normalize_quote_payment_methods


class CotizacionItemCreate(BaseModel):
    producto_id: Optional[int] = None
    codigo_producto: Optional[str] = Field(
        default=None,
        max_length=PRODUCT_INTERNAL_CODE_MAX_LENGTH,
    )
    descripcion: str = Field(..., min_length=1, max_length=500)
    cantidad: Decimal = Field(..., gt=0)
    precio_unitario: Decimal = Field(..., gt=0)
    unidad_medida: Optional[str] = None
    tipo_afectacion_igv: Optional[str] = None

    @field_validator("descripcion")
    @classmethod
    def normalize_descripcion(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("La descripcion del item es obligatoria")
        return normalized

    @field_validator("codigo_producto")
    @classmethod
    def normalize_codigo_producto(cls, value: Optional[str]) -> Optional[str]:
        return normalize_internal_product_code(value)

    @field_validator("unidad_medida")
    @classmethod
    def validate_unidad_medida(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return normalize_sunat_unit_code(value)

    @field_validator("tipo_afectacion_igv")
    @classmethod
    def validate_tipo_afectacion_igv(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return normalize_tax_affectation_code(value)


class CotizacionItemResponse(BaseModel):
    id: int
    producto_id: Optional[int] = None
    codigo_producto: Optional[str] = None
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


class CuotaPagoCreate(BaseModel):
    fecha_pago: datetime
    monto: Decimal = Field(..., gt=0)


class ClienteSnapshot(BaseModel):
    id: Optional[int] = None
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


class CotizacionCreate(BaseModel):
    cliente_id: int
    warehouse_id: Optional[int] = None
    cliente_snapshot: Optional[ClienteSnapshot] = None
    quote_payment_methods: Optional[List[dict]] = None
    fecha_emision: Optional[datetime] = None
    fecha_vencimiento: Optional[datetime] = None
    moneda: str = "PEN"
    tipo_comprobante: str = "00"
    observaciones: Optional[str] = None
    condicion_pago: Optional[str] = None
    quote_selected_wallet_id: Optional[str] = None
    cuotas_pago: List[CuotaPagoCreate] = Field(default_factory=list)
    items: List[CotizacionItemCreate]

    @field_validator("cuotas_pago", mode="before")
    @classmethod
    def normalize_cuotas_pago(cls, value):
        return value or []

    @field_validator("quote_payment_methods")
    @classmethod
    def validate_quote_payment_methods(cls, value: Optional[List[dict]]) -> Optional[List[dict]]:
        return validate_and_normalize_quote_payment_methods(value)


class CotizacionUpdate(CotizacionCreate):
    pass


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
    warehouse_id: Optional[int] = None
    document_number: Optional[str] = None
    linked_fiscal_document_id: Optional[int] = None
    linked_fiscal_document_number: Optional[str] = None
    linked_fiscal_document_status: Optional[str] = None
    payment_status: str = "pendiente"
    observaciones: Optional[str] = None
    condicion_pago: Optional[str] = None
    quote_payment_methods: Optional[List[dict]] = None
    quote_selected_wallet_id: Optional[str] = None
    cuotas_pago: List[CuotaPagoCreate] = Field(default_factory=list)
    cliente_snapshot: Optional[ClienteSnapshot] = None
    cliente: Optional[ClienteResponse] = None
    usuario: Optional[UserResponse] = None
    items: List[CotizacionItemResponse]
    total_gravada: Decimal
    total_igv: Decimal
    total_venta: Decimal

    tipo_comprobante: str
    sunat_xml_url: Optional[str] = None
    sunat_pdf_url: Optional[str] = None
    sunat_cdr_url: Optional[str] = None
    sunat_error: Optional[str] = None
    provider_document_name: Optional[str] = None
    provider_verified_at: Optional[datetime] = None
    provider_verification_status: Optional[str] = None
    cdr_artifact_status: Optional[str] = None
    pdf_artifact_status: Optional[str] = None

    monto_pagado: Decimal = Decimal("0.00")
    saldo_pendiente: Decimal = Decimal("0.00")
    pagos: List[PagoResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("sunat_pdf_url")
    def serialize_sunat_pdf_url(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return value

        from services import storage_service

        try:
            return storage_service.resolve_storage_download_url(value)
        except Exception:
            return None

    @field_validator("cuotas_pago", mode="before")
    @classmethod
    def normalize_cuotas_pago(cls, value):
        return value or []


class CotizacionListResponse(BaseModel):
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
    cuotas_pago: List[CuotaPagoCreate] = Field(default_factory=list)
    cliente_snapshot: Optional[ClienteSnapshot] = None
    cliente: Optional[ClienteResponse] = None
    total_gravada: Decimal
    total_igv: Decimal
    total_venta: Decimal
    tipo_comprobante: str
    sunat_xml_url: Optional[str] = None
    sunat_pdf_url: Optional[str] = None
    sunat_cdr_url: Optional[str] = None
    sunat_error: Optional[str] = None
    provider_endpoint: Optional[str] = None
    provider_status_code: Optional[int] = None
    provider_document_name: Optional[str] = None
    provider_verified_at: Optional[datetime] = None
    provider_verification_status: Optional[str] = None
    cdr_artifact_status: Optional[str] = None
    pdf_artifact_status: Optional[str] = None
    sunat_accepted: bool = False
    has_sunat_xml: bool = False
    has_sunat_cdr: bool = False
    monto_pagado: Decimal = Decimal("0.00")
    saldo_pendiente: Decimal = Decimal("0.00")

    model_config = ConfigDict(from_attributes=True)

    @field_validator("cuotas_pago", mode="before")
    @classmethod
    def normalize_cuotas_pago(cls, value):
        return value or []


class ClienteDocumentoListResponse(BaseModel):
    id: int
    tipo_documento: Optional[str] = None
    numero_documento: Optional[str] = None
    razon_social: Optional[str] = None
    nombre_comercial: Optional[str] = None
    nombre: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FiscalDocumentListResponse(BaseModel):
    id: int
    uuid_publico: Optional[str] = None
    serie: str
    correlativo: Optional[int] = 0
    fecha_emision: datetime
    fecha_vencimiento: Optional[datetime] = None
    moneda: str = "PEN"
    estado: str
    document_kind: str = "fiscal_document"
    source_quote_id: Optional[int] = None
    internal_order_number: Optional[str] = None
    document_number: Optional[str] = None
    payment_status: str = "pendiente"
    observaciones: Optional[str] = None
    condicion_pago: Optional[str] = None
    cliente: Optional[ClienteDocumentoListResponse] = None
    total_gravada: Decimal
    total_igv: Decimal
    total_venta: Decimal
    tipo_comprobante: str
    sujeta_detraccion: bool = False
    sunat_xml_url: Optional[str] = None
    sunat_pdf_url: Optional[str] = None
    sunat_cdr_url: Optional[str] = None
    sunat_error: Optional[str] = None
    provider_endpoint: Optional[str] = None
    provider_status_code: Optional[int] = None
    provider_document_name: Optional[str] = None
    provider_verified_at: Optional[datetime] = None
    provider_verification_status: Optional[str] = None
    cdr_artifact_status: Optional[str] = None
    pdf_artifact_status: Optional[str] = None
    sunat_accepted: bool = False
    has_sunat_xml: bool = False
    has_sunat_cdr: bool = False
    monto_pagado: Decimal = Decimal("0.00")
    saldo_pendiente: Decimal = Decimal("0.00")

    model_config = ConfigDict(from_attributes=True)


class FiscalDocumentPageResponse(BaseModel):
    items: List[FiscalDocumentListResponse]
    total: int
    skip: int
    limit: int
    counts: Dict[str, int]


class NoteReferenceDocumentListResponse(BaseModel):
    id: int
    serie: str
    correlativo: Optional[int] = 0
    fecha_emision: datetime
    moneda: str = "PEN"
    estado: str
    document_kind: str = "fiscal_document"
    document_number: Optional[str] = None
    total_venta: Decimal
    tipo_comprobante: str
    sunat_xml_url: Optional[str] = None
    sunat_error: Optional[str] = None
    provider_endpoint: Optional[str] = None
    provider_status_code: Optional[int] = None
    sunat_accepted: bool = False
    has_sunat_xml: bool = False
    has_sunat_cdr: bool = False

    model_config = ConfigDict(from_attributes=True)


class FiscalNoteListResponse(BaseModel):
    id: int
    uuid_publico: Optional[str] = None
    serie: str
    correlativo: Optional[int] = 0
    fecha_emision: datetime
    fecha_vencimiento: Optional[datetime] = None
    moneda: str = "PEN"
    estado: str
    document_kind: str
    source_quote_id: Optional[int] = None
    nota_referencia_id: Optional[int] = None
    internal_order_number: Optional[str] = None
    document_number: Optional[str] = None
    cliente: Optional[ClienteDocumentoListResponse] = None
    source_quote: Optional[NoteReferenceDocumentListResponse] = None
    nota_referencia: Optional[NoteReferenceDocumentListResponse] = None
    total_gravada: Decimal
    total_igv: Decimal
    total_venta: Decimal
    tipo_comprobante: str
    nota_motivo_codigo: Optional[str] = None
    nota_motivo_descripcion: Optional[str] = None
    sunat_xml_url: Optional[str] = None
    sunat_pdf_url: Optional[str] = None
    sunat_cdr_url: Optional[str] = None
    sunat_error: Optional[str] = None
    provider_endpoint: Optional[str] = None
    provider_status_code: Optional[int] = None
    sunat_accepted: bool = False
    has_sunat_xml: bool = False
    has_sunat_cdr: bool = False

    model_config = ConfigDict(from_attributes=True)


class FiscalNotePageResponse(BaseModel):
    items: List[FiscalNoteListResponse]
    total: int
    skip: int
    limit: int
    counts: Dict[str, int]


class CobranzaResumenResponse(BaseModel):
    total_por_cobrar: Decimal
    total_vencido: Decimal
    total_pagado_mes: Decimal
    documentos_pendientes: int
    documentos_vencidos: int
    documentos_pagados_mes: int
    clientes_con_deuda: int = 0


class _CobranzaVencidaCliente(BaseModel):
    """Cliente anidado compatible con el renderer del dashboard."""
    razon_social: Optional[str] = None
    nombre: Optional[str] = None
    numero_documento: Optional[str] = None


class CobranzaVencidaItem(BaseModel):
    """Item de cobranza vencida con la forma que espera el dashboard frontend.

    El frontend consume estos campos directamente:
      - id, estado, serie, correlativo  → keys y badges
      - cliente.razon_social / nombre   → nombre del cliente
      - document_kind                   → etiqueta COT/FACTURA/BOLETA
      - fecha_emision / fecha_vencimiento
      - moneda, total_venta, saldo_pendiente, monto_pagado
      - payment_status                  → estado de pago textual
    """
    id: int
    cotizacion_id: Optional[int] = None
    estado: str
    serie: Optional[str] = None
    correlativo: Optional[int] = None
    document_number: Optional[str] = None
    internal_order_number: Optional[str] = None
    cliente_nombre: Optional[str] = None
    cliente_documento: Optional[str] = None
    cliente: Optional[_CobranzaVencidaCliente] = None
    document_kind: Optional[str] = None
    fecha_emision: Optional[datetime] = None
    fecha_vencimiento: Optional[datetime] = None
    moneda: Optional[str] = "PEN"
    total_venta: Decimal
    monto_pagado: Decimal
    saldo_pendiente: Decimal
    dias_vencido: int
    payment_status: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class FacturarPayload(StrictInputModel):
    tipo_comprobante: str
    tipo_operacion: Optional[str] = None
    serie_override: Optional[str] = None

    @field_validator("tipo_comprobante")
    @classmethod
    def normalize_tipo_comprobante(cls, value: str) -> str:
        return str(value or "").strip()

    @field_validator("tipo_operacion")
    @classmethod
    def normalize_tipo_operacion(cls, value: Optional[str]) -> Optional[str]:
        normalized = str(value or "").strip()
        return normalized or None

    @field_validator("serie_override")
    @classmethod
    def normalize_serie_override(cls, value: Optional[str]) -> Optional[str]:
        normalized = str(value or "").strip().upper()
        return normalized or None


_NOTE_TYPE_ALIASES = {
    "07": "credito",
    "credito": "credito",
    "credit_note": "credito",
    "nota_credito": "credito",
    "nc": "credito",
    "08": "debito",
    "debito": "debito",
    "debit_note": "debito",
    "nota_debito": "debito",
    "nd": "debito",
}

_NOTE_MOTIVES = {
    "credito": {"01", "02", "03", "04", "05", "06", "07", "08", "09", "13"},
    "debito": {"01", "02", "03"},
}


class NotaCreate(StrictInputModel):
    comprobante_afectado_id: int
    tipo_nota: str
    cod_motivo: str = Field(..., min_length=2, max_length=2)
    descripcion_motivo: str = Field(..., min_length=3, max_length=250)
    items: Optional[List[CotizacionItemCreate]] = None

    @field_validator("tipo_nota")
    @classmethod
    def normalize_tipo_nota(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        normalized = _NOTE_TYPE_ALIASES.get(normalized)
        if not normalized:
            raise ValueError("Tipo de nota invalido. Use 07/credito o 08/debito.")
        return normalized

    @field_validator("cod_motivo")
    @classmethod
    def normalize_cod_motivo(cls, value: str) -> str:
        code = str(value or "").strip().zfill(2)
        if not code.isdigit():
            raise ValueError("El codigo de motivo de nota debe ser numerico.")
        return code

    @field_validator("descripcion_motivo")
    @classmethod
    def normalize_descripcion_motivo(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("La descripcion del motivo es obligatoria.")
        return normalized

    @model_validator(mode="after")
    def validate_motivo_por_tipo(self):
        allowed = _NOTE_MOTIVES.get(self.tipo_nota, set())
        if self.cod_motivo not in allowed:
            raise ValueError(
                "Motivo SUNAT invalido para el tipo de nota seleccionado."
            )
        return self


class AnulacionCreate(StrictInputModel):
    comprobante_id: int
    motivo: str


class DescargaArchivoPayload(StrictInputModel):
    comprobante_id: int
