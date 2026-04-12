"""models/guias.py — GuiaRemision, GuiaRemisionItem."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from database import Base


class GuiaRemision(Base):
    __tablename__ = "guias_remision"

    id = Column(Integer, primary_key=True, index=True)
    serie = Column(String, default="T001")
    correlativo = Column(Integer)
    fecha_emision = Column(DateTime, default=datetime.now)
    fecha_traslado = Column(DateTime)
    estado = Column(String, default="pendiente")

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="guias_remision")

    cotizacion_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True)
    cotizacion = relationship("Cotizacion", foreign_keys=[cotizacion_id])
    source_quote_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True)
    fiscal_document_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True)
    internal_order_number = Column(String, nullable=True, index=True)

    usuario_id = Column(Integer, ForeignKey("users.id"))
    usuario = relationship("User")

    motivo_traslado = Column(String, default="01")
    descripcion_motivo = Column(String, nullable=True)
    peso_bruto_total = Column(Numeric(12, 3))
    unidad_medida_peso = Column(String, default="KGM")
    numero_bultos = Column(Integer, nullable=True)
    modalidad_traslado = Column(String, default="01")
    sustento_peso = Column(String, nullable=True)
    ind_transbordo = Column(Boolean, nullable=True, default=False)
    num_contenedor = Column(String, nullable=True)
    cod_puerto = Column(String, nullable=True)

    transportista_ruc = Column(String, nullable=True)
    transportista_razon_social = Column(String, nullable=True)
    transportista_nro_mtc = Column(String, nullable=True)

    conductor_tipo_doc = Column(String, nullable=True, default="1")
    conductor_nro_doc = Column(String, nullable=True)
    conductor_nombres = Column(String, nullable=True)
    conductor_apellidos = Column(String, nullable=True)
    conductor_licencia = Column(String, nullable=True)
    vehiculo_placa = Column(String, nullable=True)
    vehiculo_nro_circulacion = Column(String, nullable=True)
    vehiculo_cod_emisor = Column(String, nullable=True)
    vehiculo_nro_autorizacion = Column(String, nullable=True)

    partida_ubigeo = Column(String, nullable=True)
    partida_direccion = Column(String, nullable=True)

    llegada_ubigeo = Column(String, nullable=True)
    llegada_direccion = Column(String, nullable=True)

    sunat_xml_url = Column(String, nullable=True)
    sunat_pdf_url = Column(String, nullable=True)
    sunat_cdr_url = Column(String, nullable=True)
    sunat_error = Column(Text, nullable=True)

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
