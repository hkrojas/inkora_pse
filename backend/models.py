from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Boolean, JSON, Numeric
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    nombre_completo = Column(String)
    rol = Column(String, default="vendedor")
    
    # Perfil de Empresa (Emisor)
    business_name = Column(String, nullable=True)
    business_ruc = Column(String, nullable=True)
    business_address = Column(String, nullable=True)
    business_phone = Column(String, nullable=True)
    logo_filename = Column(String, nullable=True)
    
    # Configuración Visual PDF
    primary_color = Column(String, default="#2563EB") # Azul por defecto
    pdf_note_1 = Column(Text, nullable=True) # Nota roja (ej: Cuentas)
    pdf_note_1_color = Column(String, default="#FF0000")
    pdf_note_2 = Column(Text, nullable=True) # Nota negra pie de página
    
    # Datos Bancarios (JSON)
    # Estructura: [{"banco": "BCP", "moneda": "Soles", "cuenta": "...", "cci": "..."}]
    bank_accounts = Column(JSON, nullable=True)

    # Configuración Facturación (ApisPeru)
    apisperu_token = Column(String, nullable=True)
    apisperu_url = Column(String, nullable=True) # Opcional si usas uno privado

    cotizaciones = relationship("Cotizacion", back_populates="usuario")

class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    tipo_documento = Column(String, default="1") # 1: DNI, 6: RUC
    numero_documento = Column(String, index=True)
    razon_social = Column(String)
    nombre_comercial = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    email = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    
    cotizaciones = relationship("Cotizacion", back_populates="cliente")

class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    codigo_interno = Column(String, nullable=True)
    nombre = Column(String, index=True)
    descripcion = Column(Text, nullable=True)
    precio_unitario = Column(Numeric(12, 2)) # Precio FINAL (con IGV)
    valor_unitario = Column(Numeric(12, 2))  # Valor BASE (sin IGV) - Calculado
    unidad_medida = Column(String, default="NIU") # NIU = Unidad
    tipo_afectacion_igv = Column(String, default="10") # 10 = Gravado

class Cotizacion(Base):
    __tablename__ = "cotizaciones"

    id = Column(Integer, primary_key=True, index=True)
    serie = Column(String, default="COT") 
    correlativo = Column(Integer)
    fecha_emision = Column(DateTime, default=datetime.now)
    fecha_vencimiento = Column(DateTime, nullable=True)
    moneda = Column(String, default="PEN") # PEN o USD
    estado = Column(String, default="pendiente") # pendiente, facturada, anulada
    
    # Relaciones
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

    # --- CAMPOS NUEVOS PARA FACTURACIÓN ELECTRÓNICA ---
    tipo_comprobante = Column(String, default="00") # 00: Cotización, 01: Factura, 03: Boleta
    
    # Enlaces devueltos por la API (ApisPeru)
    sunat_xml_url = Column(String, nullable=True)
    sunat_pdf_url = Column(String, nullable=True) # PDF generado por SUNAT (opcional, usamos el nuestro)
    sunat_cdr_url = Column(String, nullable=True) # Constancia de Recepción
    
    # Control de errores
    sunat_error = Column(Text, nullable=True) # Si SUNAT rechaza

    # --- CAMPOS NUEVOS PARA UBL 2.1 ---
    # Control Bimonetario
    tipo_de_cambio = Column(Numeric(10, 4), nullable=True)
    
    # Detracciones (SPOT)
    sujeta_detraccion = Column(Boolean, default=False)
    porcentaje_detraccion = Column(Numeric(5, 2), nullable=True)
    monto_detraccion = Column(Numeric(12, 2), nullable=True)
    cuenta_banco_nacion = Column(String, nullable=True)
    
    # Manejo de Anticipos (Señas)
    anticipos_deducidos = Column(JSON, nullable=True)
    total_anticipos = Column(Numeric(12, 2), default=0.0)

    # --- REFERENCIA PARA NOTAS DE CRÉDITO/DÉBITO ---
    # FK auto-referencial: apunta al comprobante original que esta nota afecta.
    # NULL si el registro es una cotización/factura/boleta normal.
    nota_referencia_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True)
    notas = relationship("Cotizacion", backref="documento_afectado", remote_side="Cotizacion.id")

class CotizacionItem(Base):
    __tablename__ = "cotizacion_items"

    id = Column(Integer, primary_key=True, index=True)
    cotizacion_id = Column(Integer, ForeignKey("cotizaciones.id"))
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=True)
    
    descripcion = Column(String)
    cantidad = Column(Numeric(12, 2))
    
    # Montos por Ítem
    precio_unitario = Column(Numeric(12, 2)) # Precio Unitario con IGV (del momento)
    valor_unitario = Column(Numeric(12, 2))  # Valor Unitario sin IGV
    
    total_base_igv = Column(Numeric(12, 2)) # Base imponible total item
    total_igv = Column(Numeric(12, 2))      # IGV total item
    total_item = Column(Numeric(12, 2))     # Precio total item (venta)

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
    estado = Column(String, default="pendiente")  # pendiente, emitida, anulada

    # Relación con cotización/factura de origen
    cotizacion_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True)
    cotizacion = relationship("Cotizacion")

    # Propietario
    usuario_id = Column(Integer, ForeignKey("users.id"))
    usuario = relationship("User")

    # --- DATOS LOGÍSTICOS UBL 2.1 ---
    motivo_traslado = Column(String, default="01")  # Catálogo 20: 01=Venta, 04=Traslado entre establecimientos
    descripcion_motivo = Column(String, nullable=True)
    peso_bruto_total = Column(Numeric(12, 3))  # En KGM
    unidad_medida_peso = Column(String, default="KGM")
    numero_bultos = Column(Integer, nullable=True)
    
    # Modalidad de Transporte (Catálogo 18)
    modalidad_traslado = Column(String, default="01")  # 01=Público, 02=Privado

    # --- TRANSPORTISTA (Modo Público - 01) ---
    transportista_ruc = Column(String, nullable=True)
    transportista_razon_social = Column(String, nullable=True)

    # --- CONDUCTOR / VEHÍCULO (Modo Privado - 02) ---
    conductor_tipo_doc = Column(String, nullable=True, default="1")  # 1=DNI
    conductor_nro_doc = Column(String, nullable=True)
    conductor_nombres = Column(String, nullable=True)
    conductor_apellidos = Column(String, nullable=True)
    conductor_licencia = Column(String, nullable=True)
    vehiculo_placa = Column(String, nullable=True)

    # --- DIRECCIÓN DE PARTIDA ---
    partida_ubigeo = Column(String, nullable=True)
    partida_direccion = Column(String, nullable=True)

    # --- DIRECCIÓN DE LLEGADA ---
    llegada_ubigeo = Column(String, nullable=True)
    llegada_direccion = Column(String, nullable=True)

    # --- RESPUESTA SUNAT ---
    sunat_xml_url = Column(String, nullable=True)
    sunat_pdf_url = Column(String, nullable=True)
    sunat_cdr_url = Column(String, nullable=True)
    sunat_error = Column(Text, nullable=True)

    # Relación con items
    items = relationship("GuiaRemisionItem", back_populates="guia", cascade="all, delete-orphan")


class GuiaRemisionItem(Base):
    __tablename__ = "guia_remision_items"

    id = Column(Integer, primary_key=True, index=True)
    guia_id = Column(Integer, ForeignKey("guias_remision.id"))

    descripcion = Column(String)
    cantidad = Column(Numeric(12, 2))
    unidad_medida = Column(String, default="NIU")
    codigo_producto = Column(String, nullable=True)
    peso_item = Column(Numeric(12, 3), nullable=True)  # Peso individual en KGM

    guia = relationship("GuiaRemision", back_populates="items")