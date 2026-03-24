from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Boolean, JSON, Numeric
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

# ==========================================
# TENANT (Empresa / Organización)
# ==========================================
# Entidad raíz de la multitenancia. Toda entidad operativa
# (User, Cliente, Producto, Cotizacion, GuiaRemision) pertenece
# a un Tenant específico, garantizando aislamiento de datos.

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)

    # Datos de la Empresa (Emisor)
    business_name = Column(String, nullable=False)
    business_ruc = Column(String, nullable=False, unique=True, index=True)
    business_address = Column(String, nullable=True)
    business_phone = Column(String, nullable=True)
    logo_filename = Column(String, nullable=True)

    # Configuración Visual PDF
    primary_color = Column(String, default="#2563EB")
    pdf_note_1 = Column(Text, nullable=True)
    pdf_note_1_color = Column(String, default="#FF0000")
    pdf_note_2 = Column(Text, nullable=True)

    # Datos Bancarios (JSON)
    # Estructura: [{"banco": "BCP", "moneda": "Soles", "cuenta": "...", "cci": "..."}]
    bank_accounts = Column(JSON, nullable=True)

    # Configuración Facturación (ApisPeru) — por Tenant
    apisperu_token = Column(String, nullable=True)
    apisperu_url = Column(String, nullable=True)

    # --- Relaciones inversas (navegación ORM) ---
    users = relationship("User", back_populates="tenant")
    clientes = relationship("Cliente", back_populates="tenant")
    productos = relationship("Producto", back_populates="tenant")
    cotizaciones = relationship("Cotizacion", back_populates="tenant")
    guias_remision = relationship("GuiaRemision", back_populates="tenant")
    pagos = relationship("Pago", back_populates="tenant")


# ==========================================
# USER (Empleado / Vendedor)
# ==========================================
# Representa al usuario individual (empleado) dentro de un Tenant.
# Ya NO contiene datos de empresa — esos viven en Tenant.

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    nombre_completo = Column(String)
    rol = Column(String, default="vendedor")  # vendedor, admin, superadmin

    # --- MULTITENANCIA ---
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="users")

    # --- CAMPOS LEGACY (se mantienen temporalmente para compatibilidad) ---
    # Estos campos se eliminarán en una fase posterior cuando todos los
    # consumidores (frontend, services) lean desde Tenant.
    business_name = Column(String, nullable=True)
    business_ruc = Column(String, nullable=True)
    business_address = Column(String, nullable=True)
    business_phone = Column(String, nullable=True)
    logo_filename = Column(String, nullable=True)
    primary_color = Column(String, default="#2563EB")
    pdf_note_1 = Column(Text, nullable=True)
    pdf_note_1_color = Column(String, default="#FF0000")
    pdf_note_2 = Column(Text, nullable=True)
    bank_accounts = Column(JSON, nullable=True)
    apisperu_token = Column(String, nullable=True)
    apisperu_url = Column(String, nullable=True)

    # Relaciones
    cotizaciones = relationship("Cotizacion", back_populates="usuario")


# ==========================================
# CLIENTE
# ==========================================

class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    tipo_documento = Column(String, default="1")  # 1: DNI, 6: RUC
    numero_documento = Column(String, index=True)
    razon_social = Column(String)
    nombre_comercial = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    ubigeo = Column(String, nullable=True)
    email = Column(String, nullable=True)
    telefono = Column(String, nullable=True)

    # --- MULTITENANCIA ---
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="clientes")

    cotizaciones = relationship("Cotizacion", back_populates="cliente")


# ==========================================
# PRODUCTO
# ==========================================

class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    codigo_interno = Column(String, nullable=True)
    nombre = Column(String, index=True)
    descripcion = Column(Text, nullable=True)
    precio_unitario = Column(Numeric(12, 2))  # Precio FINAL (con IGV)
    valor_unitario = Column(Numeric(12, 2))   # Valor BASE (sin IGV) - Calculado
    unidad_medida = Column(String, default="NIU")
    tipo_afectacion_igv = Column(String, default="10")

    # --- MULTITENANCIA ---
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="productos")


# ==========================================
# COTIZACIÓN / COMPROBANTE
# ==========================================

class Cotizacion(Base):
    __tablename__ = "cotizaciones"

    id = Column(Integer, primary_key=True, index=True)
    serie = Column(String, default="COT")
    correlativo = Column(Integer)
    fecha_emision = Column(DateTime, default=datetime.now)
    fecha_vencimiento = Column(DateTime, nullable=True)
    moneda = Column(String, default="PEN")
    estado = Column(String, default="pendiente")  # pendiente, facturada, anulada

    # --- MULTITENANCIA ---
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="cotizaciones")

    # Relaciones operativas
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    cliente = relationship("Cliente", back_populates="cotizaciones")

    usuario_id = Column(Integer, ForeignKey("users.id"))
    usuario = relationship("User", back_populates="cotizaciones")

    items = relationship("CotizacionItem", back_populates="cotizacion", cascade="all, delete-orphan")

    # Totales Globales
    total_gravada = Column(Numeric(12, 2), default=0.0)
    total_exonerada = Column(Numeric(12, 2), default=0.0)
    total_inafecta = Column(Numeric(12, 2), default=0.0)
    total_igv = Column(Numeric(12, 2), default=0.0)
    total_venta = Column(Numeric(12, 2), default=0.0)

    # --- FACTURACIÓN ELECTRÓNICA ---
    tipo_comprobante = Column(String, default="00")
    sunat_xml_url = Column(String, nullable=True)
    sunat_pdf_url = Column(String, nullable=True)
    sunat_cdr_url = Column(String, nullable=True)
    sunat_error = Column(Text, nullable=True)

    # --- UBL 2.1 ---
    tipo_de_cambio = Column(Numeric(10, 4), nullable=True)
    sujeta_detraccion = Column(Boolean, default=False)
    porcentaje_detraccion = Column(Numeric(5, 2), nullable=True)
    monto_detraccion = Column(Numeric(12, 2), nullable=True)
    cuenta_banco_nacion = Column(String, nullable=True)
    anticipos_deducidos = Column(JSON, nullable=True)
    total_anticipos = Column(Numeric(12, 2), default=0.0)

    # --- REFERENCIA PARA NOTAS DE CRÉDITO/DÉBITO ---
    nota_referencia_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True)
    notas = relationship("Cotizacion", backref="documento_afectado", remote_side="Cotizacion.id")

    # --- MOTOR FINANCIERO (Pagos / Adelantos) ---
    monto_pagado = Column(Numeric(12, 2), default=0.0)
    saldo_pendiente = Column(Numeric(12, 2), default=0.0)
    pagos = relationship("Pago", back_populates="cotizacion", cascade="all, delete-orphan")


# ==========================================
# ITEM DE COTIZACIÓN
# ==========================================

class CotizacionItem(Base):
    __tablename__ = "cotizacion_items"

    id = Column(Integer, primary_key=True, index=True)
    cotizacion_id = Column(Integer, ForeignKey("cotizaciones.id"))
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=True)

    descripcion = Column(String)
    cantidad = Column(Numeric(12, 2))
    precio_unitario = Column(Numeric(12, 2))
    valor_unitario = Column(Numeric(12, 2))
    total_base_igv = Column(Numeric(12, 2))
    total_igv = Column(Numeric(12, 2))
    total_item = Column(Numeric(12, 2))

    unidad_medida = Column(String, default="NIU")
    tipo_afectacion_igv = Column(String, default="10")

    cotizacion = relationship("Cotizacion", back_populates="items")


# ==========================================
# GUÍAS DE REMISIÓN ELECTRÓNICAS (GRE - 09)
# ==========================================

class GuiaRemision(Base):
    __tablename__ = "guias_remision"

    id = Column(Integer, primary_key=True, index=True)
    serie = Column(String, default="T001")
    correlativo = Column(Integer)
    fecha_emision = Column(DateTime, default=datetime.now)
    fecha_traslado = Column(DateTime)
    estado = Column(String, default="pendiente")

    # --- MULTITENANCIA ---
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="guias_remision")

    # Relación con cotización/factura de origen
    cotizacion_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True)
    cotizacion = relationship("Cotizacion")

    # Propietario
    usuario_id = Column(Integer, ForeignKey("users.id"))
    usuario = relationship("User")

    # --- DATOS LOGÍSTICOS UBL 2.1 ---
    motivo_traslado = Column(String, default="01")
    descripcion_motivo = Column(String, nullable=True)
    peso_bruto_total = Column(Numeric(12, 3))
    unidad_medida_peso = Column(String, default="KGM")
    numero_bultos = Column(Integer, nullable=True)
    modalidad_traslado = Column(String, default="01")

    # Transportista (Modo Público - 01)
    transportista_ruc = Column(String, nullable=True)
    transportista_razon_social = Column(String, nullable=True)

    # Conductor / Vehículo (Modo Privado - 02)
    conductor_tipo_doc = Column(String, nullable=True, default="1")
    conductor_nro_doc = Column(String, nullable=True)
    conductor_nombres = Column(String, nullable=True)
    conductor_apellidos = Column(String, nullable=True)
    conductor_licencia = Column(String, nullable=True)
    vehiculo_placa = Column(String, nullable=True)

    # Dirección de Partida
    partida_ubigeo = Column(String, nullable=True)
    partida_direccion = Column(String, nullable=True)

    # Dirección de Llegada
    llegada_ubigeo = Column(String, nullable=True)
    llegada_direccion = Column(String, nullable=True)

    # Respuesta SUNAT
    sunat_xml_url = Column(String, nullable=True)
    sunat_pdf_url = Column(String, nullable=True)
    sunat_cdr_url = Column(String, nullable=True)
    sunat_error = Column(Text, nullable=True)

    # Items
    items = relationship("GuiaRemisionItem", back_populates="guia", cascade="all, delete-orphan")


class GuiaRemisionItem(Base):
    __tablename__ = "guia_remision_items"

    id = Column(Integer, primary_key=True, index=True)
    guia_id = Column(Integer, ForeignKey("guias_remision.id"))

    descripcion = Column(String)
    cantidad = Column(Numeric(12, 2))
    unidad_medida = Column(String, default="NIU")
    codigo_producto = Column(String, nullable=True)
    peso_item = Column(Numeric(12, 3), nullable=True)

    guia = relationship("GuiaRemision", back_populates="items")


# ==========================================
# PAGOS / ADELANTOS
# ==========================================

class Pago(Base):
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True)

    # --- MULTITENANCIA ---
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="pagos")

    # Relación con cotización/comprobante
    cotizacion_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=False)
    cotizacion = relationship("Cotizacion", back_populates="pagos")

    # Datos del pago
    monto_pagado = Column(Numeric(12, 2), nullable=False)
    metodo_pago = Column(String, nullable=False)  # Yape, Transferencia, Efectivo, etc.
    fecha_pago = Column(DateTime, default=datetime.now)
    referencia_operacion = Column(String, nullable=True)  # Nro de operación bancaria
    tipo = Column(String, default="adelanto")  # adelanto, pago_parcial, liquidacion