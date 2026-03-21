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