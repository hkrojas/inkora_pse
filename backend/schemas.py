from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field


class StrictInputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ==========================================
# TENANT (Empresa / Organización)
# ==========================================


class TenantBase(StrictInputModel):
    business_name: str
    business_ruc: str


class TenantCreate(TenantBase):
    business_address: Optional[str] = None
    business_phone: Optional[str] = None


class TenantUpdate(StrictInputModel):
    business_name: Optional[str] = None
    business_ruc: Optional[str] = None
    business_address: Optional[str] = None
    business_phone: Optional[str] = None
    primary_color: Optional[str] = None
    pdf_note_1: Optional[str] = None
    pdf_note_1_color: Optional[str] = None
    pdf_note_2: Optional[str] = None
    bank_accounts: Optional[List[dict]] = None
    apisperu_token: Optional[str] = None
    apisperu_url: Optional[str] = None


class TenantSummaryResponse(BaseModel):
    id: int
    is_active: bool = True
    business_name: str
    business_ruc: str
    model_config = ConfigDict(from_attributes=True)


class TenantResponse(TenantSummaryResponse):
    business_address: Optional[str] = None
    business_phone: Optional[str] = None
    logo_filename: Optional[str] = None
    primary_color: Optional[str] = None
    pdf_note_1: Optional[str] = None
    pdf_note_1_color: Optional[str] = None
    pdf_note_2: Optional[str] = None
    bank_accounts: Optional[Any] = None
    apisperu_url: Optional[str] = None
    apisperu_token_secret: Optional[str] = Field(
        default=None, alias="apisperu_token", exclude=True, repr=False
    )

    # SaaS & SUNAT (sin exponer secretos)
    plan_type: Optional[str] = "Free"
    invoice_limit: Optional[int] = 50
    invoices_used: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)

    @computed_field(return_type=bool)
    @property
    def has_apisperu_token(self) -> bool:
        return bool(self.apisperu_token_secret)


class TenantSaaSUpdate(StrictInputModel):
    plan_type: Optional[str] = None
    plan_start_date: Optional[datetime] = None
    plan_end_date: Optional[datetime] = None
    invoice_limit: Optional[int] = None
    sunat_usuario_sol: Optional[str] = None
    sunat_clave_sol: Optional[str] = None
    sunat_cert_password: Optional[str] = None
    sunat_cert_url: Optional[str] = None


class SuperadminTenantResponse(TenantResponse):
    plan_start_date: Optional[datetime] = None
    plan_end_date: Optional[datetime] = None
    sunat_usuario_sol_secret: Optional[str] = Field(
        default=None, alias="sunat_usuario_sol", exclude=True, repr=False
    )
    sunat_clave_sol_secret: Optional[str] = Field(
        default=None, alias="sunat_clave_sol", exclude=True, repr=False
    )
    sunat_cert_password_secret: Optional[str] = Field(
        default=None, alias="sunat_cert_password", exclude=True, repr=False
    )
    sunat_cert_url_secret: Optional[str] = Field(
        default=None, alias="sunat_cert_url", exclude=True, repr=False
    )

    @computed_field(return_type=bool)
    @property
    def has_sunat_usuario_sol(self) -> bool:
        return bool(self.sunat_usuario_sol_secret)

    @computed_field(return_type=bool)
    @property
    def has_sunat_cert_password(self) -> bool:
        return bool(self.sunat_cert_password_secret)

    @computed_field(return_type=bool)
    @property
    def has_sunat_cert_url(self) -> bool:
        return bool(self.sunat_cert_url_secret)

    @computed_field(return_type=bool)
    @property
    def has_sunat_credentials(self) -> bool:
        return (
            self.has_sunat_usuario_sol
            and self.has_sunat_cert_password
            and self.has_sunat_cert_url
        )


# ==========================================
# USUARIOS (Autenticación y Perfil)
# ==========================================


class UserIdentity(BaseModel):
    email: EmailStr
    nombre_completo: Optional[str] = None


class UserRegisterRequest(StrictInputModel):
    email: EmailStr
    nombre_completo: Optional[str] = None
    password: str
    tenant_id: int


class UserUpdateProfile(StrictInputModel):
    """Solo datos personales del usuario autenticado."""

    nombre_completo: Optional[str] = None


class UserAdminUpdate(StrictInputModel):
    """Schema para que el superadmin actualice usuarios."""

    nombre_completo: Optional[str] = None
    rol: Optional[str] = None
    tenant_id: Optional[int] = None
    is_superadmin: Optional[bool] = None


class UserResponse(UserIdentity):
    id: int
    rol: str = "vendedor"
    is_superadmin: bool = False
    tenant_id: int
    tenant: Optional[TenantSummaryResponse] = None

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# ==========================================
# CLIENTES
# ==========================================


CONDICION_PAGO_VALORES = {
    "contado", "credito_7", "credito_15", "credito_30", "credito_60",
}


class ClienteBase(BaseModel):
    tipo_documento: str = "1"
    numero_documento: str = Field(..., min_length=8, max_length=15)
    razon_social: str = Field(...)
    nombre_comercial: Optional[str] = None
    direccion: Optional[str] = None          # Dirección fiscal
    ubigeo: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    # --- Fase 6: campos enriquecidos ---
    whatsapp: Optional[str] = None
    contacto: Optional[str] = None
    condicion_pago: Optional[str] = None     # contado | credito_7 | credito_15 | credito_30 | credito_60
    direccion_entrega: Optional[str] = None
    observaciones: Optional[str] = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    """Actualización parcial de cliente (PATCH)."""
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


# ==========================================
# PRODUCTOS
# ==========================================


class ProductoBase(BaseModel):
    codigo_interno: Optional[str] = None
    nombre: str
    descripcion: Optional[str] = None
    precio_unitario: Decimal = Field(..., gt=0)
    unidad_medida: str = "NIU"
    tipo_afectacion_igv: str = "10"


class ProductoCreate(ProductoBase):
    pass


class ProductoResponse(ProductoBase):
    id: int
    valor_unitario: Decimal
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# MOTOR DE PRODUCCIÓN (MRP / BOM)
# ==========================================


class InsumoBase(BaseModel):
    nombre: str
    unidad_compra: str
    unidad_consumo: str
    factor_conversion: Decimal = Field(..., gt=0)
    costo_promedio: Decimal = Decimal("0.00")
    stock_actual: Decimal = Decimal("0.00")
    umbral_minimo: Decimal = Decimal("50.00")


class InsumoCreate(InsumoBase):
    pass


class InsumoResponse(InsumoBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class RecetaBOMBase(BaseModel):
    insumo_id: int
    cantidad_base_necesaria: Decimal = Field(..., gt=0)
    porcentaje_merma_estandar: Decimal = Decimal("0.00")


class RecetaBOMCreate(RecetaBOMBase):
    producto_id: int


class RecetaBOMResponse(RecetaBOMBase):
    id: int
    producto_id: int
    insumo: Optional[InsumoResponse] = None
    model_config = ConfigDict(from_attributes=True)


class AlertaInventarioResponse(BaseModel):
    id: int
    insumo: Optional[InsumoResponse] = None
    mensaje: str
    fecha_creacion: datetime
    resuelta: bool
    model_config = ConfigDict(from_attributes=True)


class DashboardStatsResponse(BaseModel):
    ingresos_totales: Decimal
    saldos_por_cobrar: Decimal
    saldo_vencido: Decimal = Decimal("0.00")
    costos_tercerizacion: Decimal
    documentos_emitidos_mes: int = 0
    documentos_vencidos: int = 0
    top_productos: List[str]



class ProveedorBase(BaseModel):
    razon_social: str
    ruc: str
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    tipo_servicio: str


class ProveedorCreate(ProveedorBase):
    pass


class ProveedorUpdate(BaseModel):
    razon_social: Optional[str] = None
    ruc: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    tipo_servicio: Optional[str] = None


class ProveedorResponse(ProveedorBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class OrdenProduccionDetalleResponse(BaseModel):
    id: int
    insumo_id: int
    insumo: Optional[InsumoResponse] = None
    cantidad_requerida_neta: Decimal
    cantidad_merma: Decimal
    cantidad_total_descontar: Decimal
    model_config = ConfigDict(from_attributes=True)


class OrdenProduccionResponse(BaseModel):
    id: int
    cotizacion_id: int
    estado: str
    fecha_inicio: datetime
    fecha_fin: Optional[datetime] = None
    tipo_produccion: str
    proveedor_id: Optional[int] = None
    proveedor: Optional[ProveedorResponse] = None
    costo_tercerizado: Optional[Decimal] = None
    detalles: List[OrdenProduccionDetalleResponse] = []
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# COTIZACIONES Y COMPROBANTES
# ==========================================


class CotizacionItemCreate(BaseModel):
    producto_id: Optional[int] = None
    descripcion: str
    cantidad: Decimal = Field(..., gt=0)
    precio_unitario: Decimal = Field(..., gt=0)
    unidad_medida: Optional[str] = None          # Si None, hereda del producto o usa "NIU"
    tipo_afectacion_igv: Optional[str] = None    # Si None, hereda del producto o usa "10" (gravado)


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
    condicion_pago: Optional[str] = None         # override; si None hereda del cliente
    items: List[CotizacionItemCreate]


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

    # Datos SUNAT
    tipo_comprobante: str
    sunat_xml_url: Optional[str] = None
    sunat_pdf_url: Optional[str] = None
    sunat_cdr_url: Optional[str] = None
    sunat_error: Optional[str] = None

    # Motor Financiero
    monto_pagado: Decimal = Decimal("0.00")
    saldo_pendiente: Decimal = Decimal("0.00")
    pagos: List["PagoResponse"] = []

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# PAGOS / ADELANTOS
# ==========================================


class PagoCreate(StrictInputModel):
    monto_pagado: Decimal = Field(..., gt=0)
    metodo_pago: str
    fecha_pago: Optional[datetime] = None       # Si None, se usa la fecha actual
    referencia_operacion: Optional[str] = None
    tipo: str = "adelanto"                      # adelanto | pago_parcial | liquidacion


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


class CobranzaResumenResponse(BaseModel):
    """Resumen de cobranza del tenant para el dashboard."""
    total_por_cobrar: Decimal
    total_vencido: Decimal
    total_pagado_mes: Decimal
    documentos_pendientes: int
    documentos_vencidos: int
    documentos_pagados_mes: int


class CobranzaVencidaItem(BaseModel):
    """Item de documento vencido para vista de cobranza."""
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


CotizacionResponse.model_rebuild()


# --- NUEVOS ESQUEMAS PARA FACTURACIÓN ---


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


# ==========================================
# GUÍAS DE REMISIÓN ELECTRÓNICAS (GRE)
# ==========================================


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

    # Transportista (Público)
    transportista_ruc: Optional[str] = None
    transportista_razon_social: Optional[str] = None

    # Conductor/Vehículo (Privado)
    conductor_tipo_doc: Optional[str] = "1"
    conductor_nro_doc: Optional[str] = None
    conductor_nombres: Optional[str] = None
    conductor_apellidos: Optional[str] = None
    conductor_licencia: Optional[str] = None
    vehiculo_placa: Optional[str] = None

    # Direcciones
    partida_ubigeo: str
    partida_direccion: str
    llegada_ubigeo: str
    llegada_direccion: str

    # Items
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
    """Datos estructurados para imprimir la etiqueta de despacho de una guía."""
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


# ==========================================
# FASE 9: INTELIGENCIA ARTIFICIAL (GEMINI)
# ==========================================


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


# ==========================================
# FASE 5: SUPERADMIN / SUSCRIPCION SaaS
# ==========================================
# SEPARACION DE DOMINIOS:
# - SubscriptionPaymentCreate/Response → pago de tenant a PrintFlow (SaaS)
# - PagoCreate/PagoResponse           → pago de cliente al tenant (negocio)
# Nunca mezclar estos dos dominios.


class SubscriptionResponse(BaseModel):
    """Estado actual de la suscripcion SaaS de un tenant."""
    id: int
    tenant_id: int
    status: str
    plan_code: str
    current_price: Optional[Decimal] = None
    founder_price: Optional[Decimal] = None
    billing_started_at: Optional[datetime] = None
    billing_due_at: Optional[datetime] = None
    grace_until: Optional[datetime] = None
    max_users: Optional[int] = None
    max_documents: Optional[int] = None
    documents_used: int = 0
    onboarding_status: str
    notes_internal: Optional[str] = None
    is_pilot: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriptionPaymentCreate(StrictInputModel):
    """Registrar un pago SaaS recibido de un tenant. Dominio: PrintFlow cobra al tenant."""
    amount: Decimal = Field(..., gt=0)
    currency: str = "PEN"
    method: str
    reference: Optional[str] = None
    paid_at: Optional[datetime] = None
    notes: Optional[str] = None


class SubscriptionPaymentResponse(BaseModel):
    id: int
    tenant_id: int
    amount: Decimal
    currency: str
    method: str
    reference: Optional[str] = None
    paid_at: Optional[datetime] = None
    validated_by_user_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivateTenantRequest(StrictInputModel):
    """Activar un tenant. Opcionalmente fija la fecha de vencimiento."""
    billing_due_at: Optional[datetime] = None
    notes_internal: Optional[str] = None


class SuspendTenantRequest(StrictInputModel):
    """Suspender un tenant. El acceso queda bloqueado inmediatamente."""
    notes_internal: Optional[str] = None


class ExtendAccessRequest(StrictInputModel):
    """Extender el acceso de un tenant (nueva fecha de vencimiento)."""
    billing_due_at: datetime
    grace_until: Optional[datetime] = None
    notes_internal: Optional[str] = None


class SetFounderPricingRequest(StrictInputModel):
    """Fijar precio fundador y/o precio actual para un tenant."""
    founder_price: Decimal = Field(..., gt=0)
    current_price: Optional[Decimal] = Field(default=None, gt=0)
    notes_internal: Optional[str] = None


class UpdateSubscriptionRequest(StrictInputModel):
    """Actualización general de campos de suscripcion (uso admin avanzado)."""
    status: Optional[str] = None
    plan_code: Optional[str] = None
    billing_started_at: Optional[datetime] = None
    billing_due_at: Optional[datetime] = None
    grace_until: Optional[datetime] = None
    current_price: Optional[Decimal] = None
    founder_price: Optional[Decimal] = None
    max_users: Optional[int] = None
    max_documents: Optional[int] = None
    onboarding_status: Optional[str] = None
    notes_internal: Optional[str] = None
    is_pilot: Optional[bool] = None


class SuperadminTenantDetailResponse(BaseModel):
    """Vista completa de un tenant para el superadmin: estado operativo + suscripcion."""
    id: int
    is_active: bool
    business_name: str
    business_ruc: str
    business_address: Optional[str] = None
    business_phone: Optional[str] = None
    plan_type: Optional[str] = None
    subscription: Optional[SubscriptionResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# FASE 8: IMPORTACIÓN MASIVA (ONBOARDING)
# ==========================================


class ImportErrorDetail(BaseModel):
    """Error de una fila durante la importación."""
    fila: int
    campo: str
    mensaje: str


class ImportResultResponse(BaseModel):
    """Resultado de una importación masiva de clientes o productos."""
    importados: int
    omitidos: int
    errores: List[ImportErrorDetail]


# ==========================================
# FASE 8: CHECKLIST DE ONBOARDING
# ==========================================


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


# ==========================================
# FASE 9: BETA CERRADA — CONTROL OPERATIVO
# ==========================================


class UpdateNotasRequest(StrictInputModel):
    """Actualización rápida de notas internas de un tenant (uso superadmin en llamadas de soporte)."""
    notes_internal: Optional[str] = None
    is_pilot: Optional[bool] = None


class TenantActividadResponse(BaseModel):
    """Métricas de uso operativo de un tenant para seguimiento de beta."""
    tenant_id: int
    business_name: str
    business_ruc: str
    # Conteos de entidades
    clientes_count: int
    productos_count: int
    usuarios_count: int
    # Documentos
    cotizaciones_count: int
    documentos_fiscales_count: int
    documentos_fiscales_ultimo_mes: int
    guias_count: int
    pagos_count: int
    # Actividad
    ultimo_documento_fiscal_fecha: Optional[datetime] = None
    # Suscripción
    subscription_status: Optional[str] = None
    onboarding_status: Optional[str] = None
    documents_used: int = 0
    max_documents: Optional[int] = None


class BetaTenantSummary(BaseModel):
    """Vista resumida de un tenant piloto para el panel de operaciones beta."""
    tenant_id: int
    business_name: str
    business_ruc: str
    is_active: bool
    is_pilot: bool = False
    subscription_status: Optional[str] = None
    onboarding_status: Optional[str] = None
    plan_code: Optional[str] = None
    current_price: Optional[Decimal] = None
    founder_price: Optional[Decimal] = None
    billing_due_at: Optional[datetime] = None
    documents_used: int = 0
    max_documents: Optional[int] = None
    # Conteos rápidos
    clientes_count: int = 0
    productos_count: int = 0
    usuarios_count: int = 0
    # Último pago SaaS
    ultimo_pago_saas_fecha: Optional[datetime] = None
    ultimo_pago_saas_monto: Optional[Decimal] = None
    # Notas internas
    notes_internal: Optional[str] = None
