from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import List, Optional, Any
from datetime import datetime
from decimal import Decimal

# ==========================================
# TENANT (Empresa / Organización)
# ==========================================

class TenantBase(BaseModel):
    business_name: str
    business_ruc: str

class TenantCreate(TenantBase):
    business_address: Optional[str] = None
    business_phone: Optional[str] = None
    apisperu_token: Optional[str] = None

class TenantUpdate(BaseModel):
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

class TenantResponse(BaseModel):
    id: int
    is_active: bool = True
    business_name: str
    business_ruc: str
    business_address: Optional[str] = None
    business_phone: Optional[str] = None
    logo_filename: Optional[str] = None
    primary_color: Optional[str] = None
    pdf_note_1: Optional[str] = None
    pdf_note_1_color: Optional[str] = None
    pdf_note_2: Optional[str] = None
    bank_accounts: Optional[Any] = None
    apisperu_token: Optional[str] = None
    apisperu_url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# USUARIOS (Autenticación y Perfil)
# ==========================================

class UserBase(BaseModel):
    email: EmailStr
    nombre_completo: Optional[str] = None
    rol: str = "vendedor"

class UserCreate(UserBase):
    password: str
    tenant_id: int  # Obligatorio: a qué empresa pertenece

class UserUpdateProfile(BaseModel):
    """Solo campos del usuario. Los datos de empresa se actualizan vía TenantUpdate."""
    nombre_completo: Optional[str] = None

class UserResponse(UserBase):
    id: int
    tenant_id: int
    tenant: Optional[TenantResponse] = None  # Anidado para acceso directo
    
    # --- CAMPOS LEGACY (temporales para compatibilidad frontend) ---
    business_name: Optional[str] = None
    business_ruc: Optional[str] = None
    business_address: Optional[str] = None
    business_phone: Optional[str] = None
    primary_color: Optional[str] = None
    logo_filename: Optional[str] = None
    pdf_note_1: Optional[str] = None
    pdf_note_1_color: Optional[str] = None
    bank_accounts: Optional[Any] = None
    apisperu_token: Optional[str] = None
    apisperu_url: Optional[str] = None
    
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

    model_config = ConfigDict(from_attributes=True)

# --- NUEVOS ESQUEMAS PARA FACTURACIÓN ---

class FacturarPayload(BaseModel):
    tipo_comprobante: str # '01' Factura, '03' Boleta

class NotaCreate(BaseModel):
    comprobante_afectado_id: int
    tipo_nota: str # 'credito' o 'debito'
    cod_motivo: str # Ej: '01', '07'
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
    modalidad_traslado: str = "01"  # 01=Público, 02=Privado
    
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