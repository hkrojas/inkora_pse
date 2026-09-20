"""schemas/guias.py — Guia de Remision schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from fiscal_catalogs import (
    PRODUCT_INTERNAL_CODE_MAX_LENGTH,
    normalize_internal_product_code,
    normalize_sunat_unit_code,
)


class GuiaRemisionItemCreate(BaseModel):
    producto_id: Optional[int] = None
    descripcion: str = Field(..., min_length=1, max_length=500)
    cantidad: Decimal = Field(..., gt=0)
    unidad_medida: str = "NIU"
    codigo_producto: Optional[str] = Field(
        default=None,
        max_length=PRODUCT_INTERNAL_CODE_MAX_LENGTH,
    )
    peso_item: Optional[Decimal] = None
    fiscal_document_item_id: Optional[int] = None

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

    items: List[GuiaRemisionItemCreate] = Field(..., min_length=1)

    @field_validator("unidad_medida_peso")
    @classmethod
    def validate_unidad_medida_peso(cls, value: str) -> str:
        return normalize_sunat_unit_code(value)


class DispatchLineSelection(BaseModel):
    fiscal_document_item_id: int
    quantity: Decimal = Field(..., gt=0, max_digits=18, decimal_places=4)
    confirmed_as_goods: bool = False


class SaleDispatchGuideData(BaseModel):
    fecha_traslado: datetime
    peso_bruto_total: Decimal = Field(..., gt=0, max_digits=15, decimal_places=3)
    unidad_medida_peso: str = "KGM"
    numero_bultos: Optional[int] = Field(default=None, ge=1)
    modalidad_traslado: str = Field(default="02", pattern="^(01|02)$")
    fecha_entrega_transportista: Optional[datetime] = None
    indicador_m1_l: bool = False
    registrar_vehiculo_transportista: bool = False
    transportista_acuerdo_confirmado: bool = False
    observaciones: Optional[str] = Field(default=None, max_length=500)
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
    partida_ubigeo: str = Field(..., pattern=r"^\d{6}$")
    partida_direccion: str = Field(..., min_length=3, max_length=500)
    llegada_ubigeo: str = Field(..., pattern=r"^\d{6}$")
    llegada_direccion: str = Field(..., min_length=3, max_length=500)

    @field_validator("unidad_medida_peso")
    @classmethod
    def validate_weight_unit(cls, value: str) -> str:
        normalized = normalize_sunat_unit_code(value)
        if normalized not in {"KGM", "TNE"}:
            raise ValueError("La unidad de peso debe ser KGM o TNE")
        return normalized

    @field_validator("conductor_tipo_doc")
    @classmethod
    def validate_driver_document_type(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = str(value).strip().upper()
        if normalized not in {"0", "1", "4", "6", "7", "A", "B", "C", "D", "E"}:
            raise ValueError("Tipo de documento del conductor no admitido por el catálogo 06")
        return normalized


class SaleDispatchFromInvoiceCreate(SaleDispatchGuideData):
    fiscal_document_id: int
    idempotency_key: str = Field(..., min_length=8, max_length=120)
    lines: List[DispatchLineSelection] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_unique_lines(self):
        line_ids = [line.fiscal_document_item_id for line in self.lines]
        if len(line_ids) != len(set(line_ids)):
            raise ValueError("Cada linea de factura debe aparecer una sola vez")
        return self


class SaleDispatchFromDocumentCreate(SaleDispatchFromInvoiceCreate):
    """Neutral request used by invoice 01 and receipt 03 dispatches."""


class SaleDispatchUpdate(SaleDispatchGuideData):
    version: int = Field(..., ge=1)
    lines: List[DispatchLineSelection] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_unique_lines(self):
        line_ids = [line.fiscal_document_item_id for line in self.lines]
        if len(line_ids) != len(set(line_ids)):
            raise ValueError("Cada linea de factura debe aparecer una sola vez")
        return self


class ExternalDocumentReferenceInput(BaseModel):
    document_type: str = Field(..., pattern="^(01|03|09|31)$")
    issuer_ruc: str = Field(..., pattern=r"^\d{11}$")
    series: str = Field(..., min_length=4, max_length=4)
    number: str = Field(..., pattern=r"^\d{1,8}$")
    evidence: Optional[Dict[str, Any]] = None


class TransportGuideCreate(SaleDispatchGuideData):
    modalidad_traslado: str = Field(default="01", pattern="^01$")
    idempotency_key: str = Field(..., min_length=8, max_length=120)
    gre_remitente: ExternalDocumentReferenceInput
    goods_invoice: ExternalDocumentReferenceInput
    remitente_tipo_doc: str = "6"
    remitente_nro_doc: str
    remitente_razon_social: str
    destinatario_tipo_doc: str
    destinatario_nro_doc: str
    destinatario_razon_social: str
    pagador_flete_tipo: str = Field(default="Remitente", pattern="^(Remitente|Tercero)$")
    pagador_tipo_doc: Optional[str] = None
    pagador_nro_doc: Optional[str] = None
    pagador_razon_social: Optional[str] = None
    lines: List[GuiaRemisionItemCreate] = Field(..., min_length=1)


class GuideExternalRegistration(BaseModel):
    guide: ExternalDocumentReferenceInput


class ExternalGuideVerification(BaseModel):
    environment: str = Field(..., pattern="^(demo|production)$")
    signed_xml: str = Field(..., min_length=20, max_length=5_000_000)
    cdr: str = Field(..., min_length=20, max_length=5_000_000)
    provider_document_name: Optional[str] = Field(default=None, max_length=200)
    note: str = Field(..., min_length=10, max_length=500)


class GuideExternalReferenceResponse(BaseModel):
    id: int
    document_type: str
    issuer_ruc: str
    series: str
    number: str
    source: str
    verification_status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DispatchDepartureConfirm(BaseModel):
    idempotency_key: str = Field(..., min_length=8, max_length=120)


class HistoricalDispatchReconciliation(BaseModel):
    confirmed_no_prior_dispatch: bool
    note: str = Field(..., min_length=10, max_length=500)


class GuiaRemisionItemResponse(BaseModel):
    id: int
    descripcion: str
    cantidad: Decimal
    unidad_medida: str
    codigo_producto: Optional[str] = None
    peso_item: Optional[Decimal] = None
    dispatch_line_id: Optional[int] = None
    internal_transfer_dispatch_line_id: Optional[int] = None
    fiscal_document_item_id: Optional[int] = None
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
    tipo_documento: str = "09"
    serie: str
    correlativo: Optional[int] = 0
    fecha_emision: datetime
    fecha_traslado: datetime
    estado: str
    cotizacion_id: Optional[int] = None
    cliente_id: Optional[int] = None
    source_quote_id: Optional[int] = None
    fiscal_document_id: Optional[int] = None
    dispatch_id: Optional[int] = None
    internal_transfer_dispatch_id: Optional[int] = None
    related_guide_id: Optional[int] = None
    external_gre_reference_id: Optional[int] = None
    goods_invoice_reference_id: Optional[int] = None
    freight_invoice_id: Optional[int] = None
    version: int = 1
    internal_order_number: Optional[str] = None
    motivo_traslado: str
    descripcion_motivo: Optional[str] = None
    peso_bruto_total: Decimal
    unidad_medida_peso: str
    modalidad_traslado: str
    fecha_entrega_transportista: Optional[datetime] = None
    indicador_m1_l: bool = False
    registrar_vehiculo_transportista: bool = False
    transportista_acuerdo_confirmado_at: Optional[datetime] = None
    transportista_acuerdo_confirmado_by_user_id: Optional[int] = None
    observaciones: Optional[str] = None
    sustento_peso: Optional[str] = None
    ind_transbordo: Optional[bool] = None
    num_contenedor: Optional[str] = None
    cod_puerto: Optional[str] = None
    transportista_ruc: Optional[str] = None
    transportista_razon_social: Optional[str] = None
    transportista_nro_mtc: Optional[str] = None
    conductor_tipo_doc: Optional[str] = None
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
    partida_codigo_local: Optional[str] = None
    llegada_ubigeo: Optional[str] = None
    llegada_direccion: Optional[str] = None
    llegada_codigo_local: Optional[str] = None
    cliente_nombre: Optional[str] = None
    cliente_documento: Optional[str] = None
    sunat_xml_url: Optional[str] = None
    xml_disponible: bool = False
    sunat_pdf_url: Optional[str] = None
    sunat_cdr_url: Optional[str] = None
    cdr_disponible: bool = False
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
    tipo_documento: str = "09"
    serie: str
    correlativo: Optional[int] = 0
    fecha_emision: datetime
    fecha_traslado: datetime
    estado: str
    cotizacion_id: Optional[int] = None
    cliente_id: Optional[int] = None
    source_quote_id: Optional[int] = None
    fiscal_document_id: Optional[int] = None
    dispatch_id: Optional[int] = None
    internal_transfer_dispatch_id: Optional[int] = None
    related_guide_id: Optional[int] = None
    external_gre_reference_id: Optional[int] = None
    goods_invoice_reference_id: Optional[int] = None
    freight_invoice_id: Optional[int] = None
    version: int = 1
    creation_idempotency_key: Optional[str] = None
    internal_order_number: Optional[str] = None
    motivo_traslado: str
    descripcion_motivo: Optional[str] = None
    peso_bruto_total: Decimal
    unidad_medida_peso: str
    modalidad_traslado: str
    fecha_entrega_transportista: Optional[datetime] = None
    indicador_m1_l: bool = False
    registrar_vehiculo_transportista: bool = False
    transportista_acuerdo_confirmado_at: Optional[datetime] = None
    transportista_acuerdo_confirmado_by_user_id: Optional[int] = None
    observaciones: Optional[str] = None
    transportista_ruc: Optional[str] = None
    transportista_razon_social: Optional[str] = None
    conductor_tipo_doc: Optional[str] = None
    conductor_nro_doc: Optional[str] = None
    conductor_licencia: Optional[str] = None
    vehiculo_placa: Optional[str] = None
    partida_ubigeo: Optional[str] = None
    partida_direccion: Optional[str] = None
    partida_codigo_local: Optional[str] = None
    llegada_ubigeo: Optional[str] = None
    llegada_direccion: Optional[str] = None
    llegada_codigo_local: Optional[str] = None
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


class GuideActionAvailability(BaseModel):
    enabled: bool
    code: Optional[str] = None
    reason: Optional[str] = None


class GuideEmissionJobSummary(BaseModel):
    id: int
    action: str
    status: str
    attempts: int
    provider_ticket: Optional[str] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class GuiaRemisionDetailResponse(GuiaRemisionResponse):
    internal_transfer_id: Optional[int] = None
    dispatch_status: Optional[str] = None
    reservation_status: Optional[str] = None
    departure_confirmed_at: Optional[datetime] = None
    external_gre_reference: Optional[GuideExternalReferenceResponse] = None
    goods_invoice_reference: Optional[GuideExternalReferenceResponse] = None
    actions: Dict[str, GuideActionAvailability]
    emission_job: Optional[GuideEmissionJobSummary] = None


class SaleDispatchLineResponse(BaseModel):
    id: int
    fiscal_document_item_id: int
    product_id: Optional[int] = None
    quantity: Decimal
    unit_code: str
    product_code: Optional[str] = None
    description: str
    confirmed_as_goods: bool
    reservation_status: str
    inventory_movement_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class SaleDispatchResponse(BaseModel):
    id: int
    fiscal_document_id: int
    source_document_type: str = "01"
    source_summary_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    status: str
    version: int
    departure_confirmed_at: Optional[datetime] = None
    logistical_block_code: Optional[str] = None
    logistical_block_detail: Optional[str] = None
    lines: List[SaleDispatchLineResponse]
    guides: List[GuiaRemisionListResponse]
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
