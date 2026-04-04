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
    apisperu_token: Optional[str] = None


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


class ClienteBase(BaseModel):
    tipo_documento: str = "1"
    numero_documento: str = Field(..., min_length=8, max_length=15)
    razon_social: str = Field(...)
    nombre_comercial: Optional[str] = None
    direccion: Optional[str] = None
    ubigeo: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None


class ClienteCreate(ClienteBase):
    pass


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
    costos_tercerizacion: Decimal
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


class CotizacionItemResponse(CotizacionItemCreate):
    id: int
    valor_unitario: Decimal
    total_base_igv: Decimal
    total_igv: Decimal
    total_item: Decimal
    model_config = ConfigDict(from_attributes=True)


class CotizacionCreate(BaseModel):
    cliente_id: int
    fecha_vencimiento: Optional[datetime] = None
    moneda: str = "PEN"
    tipo_comprobante: str = "00"
    items: List[CotizacionItemCreate]


class CotizacionResponse(BaseModel):
    id: int
    serie: str
    correlativo: Optional[int] = 0
    fecha_emision: datetime
    fecha_vencimiento: Optional[datetime]
    estado: str
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


class PagoCreate(BaseModel):
    monto_pagado: Decimal = Field(..., gt=0)
    metodo_pago: str
    referencia_operacion: Optional[str] = None
    tipo: str = "adelanto"


class PagoResponse(BaseModel):
    id: int
    cotizacion_id: int
    monto_pagado: Decimal
    metodo_pago: str
    fecha_pago: datetime
    referencia_operacion: Optional[str] = None
    tipo: str
    model_config = ConfigDict(from_attributes=True)


CotizacionResponse.model_rebuild()


# --- NUEVOS ESQUEMAS PARA FACTURACIÓN ---


class FacturarPayload(BaseModel):
    tipo_comprobante: str


class NotaCreate(BaseModel):
    comprobante_afectado_id: int
    tipo_nota: str
    cod_motivo: str
    descripcion_motivo: str


class AnulacionCreate(BaseModel):
    comprobante_id: int
    motivo: str


class DescargaArchivoPayload(BaseModel):
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


class GuiaRemisionResponse(BaseModel):
    id: int
    serie: str
    correlativo: Optional[int] = 0
    fecha_emision: datetime
    fecha_traslado: datetime
    estado: str
    cotizacion_id: Optional[int] = None
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
