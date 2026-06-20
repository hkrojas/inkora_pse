"""models/cotizaciones.py — Cotizacion, CotizacionItem."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import backref, relationship

from database import Base


class Cotizacion(Base):
    __tablename__ = "cotizaciones"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "serie",
            "correlativo",
            name="uq_cotizaciones_tenant_serie_correlativo",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    serie = Column(String, default="COT")
    correlativo = Column(Integer)
    fecha_emision = Column(DateTime, default=datetime.now)
    fecha_vencimiento = Column(DateTime, nullable=True)
    moneda = Column(String, default="PEN")
    estado = Column(String, default="pendiente")
    uuid_publico = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    document_kind = Column(String, default="quotation", nullable=False, index=True)
    internal_order_number = Column(String, nullable=True, index=True)
    source_quote_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True, index=True)

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="cotizaciones")

    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    cliente = relationship("Cliente", back_populates="cotizaciones")
    cliente_snapshot = Column(JSON, nullable=True)

    usuario_id = Column(Integer, ForeignKey("users.id"))
    usuario = relationship("User", back_populates="cotizaciones")
    source_quote = relationship(
        "Cotizacion",
        foreign_keys=[source_quote_id],
        remote_side="Cotizacion.id",
        backref=backref("derived_documents", lazy="selectin"),
    )

    items = relationship("CotizacionItem", back_populates="cotizacion", cascade="all, delete-orphan")

    total_gravada = Column(Numeric(12, 2), default=0.0)
    total_exonerada = Column(Numeric(12, 2), default=0.0)
    total_inafecta = Column(Numeric(12, 2), default=0.0)
    total_igv = Column(Numeric(12, 2), default=0.0)
    total_venta = Column(Numeric(12, 2), default=0.0)

    tipo_comprobante = Column(String, default="00")
    sunat_xml_url = Column(String, nullable=True)
    sunat_pdf_url = Column(String, nullable=True)
    sunat_cdr_url = Column(String, nullable=True)
    sunat_error = Column(Text, nullable=True)
    sunat_xml_content = Column(Text, nullable=True)
    sunat_cdr_content = Column(Text, nullable=True)
    sunat_hash = Column(String, nullable=True)
    sunat_qr_payload = Column(JSON, nullable=True)
    sunat_qr_svg = Column(Text, nullable=True)
    provider_response = Column(JSON, nullable=True)
    provider_endpoint = Column(String, nullable=True)
    provider_status_code = Column(Integer, nullable=True)

    tipo_de_cambio = Column(Numeric(10, 4), nullable=True)
    sujeta_detraccion = Column(Boolean, default=False)
    porcentaje_detraccion = Column(Numeric(5, 2), nullable=True)
    monto_detraccion = Column(Numeric(12, 2), nullable=True)
    cuenta_banco_nacion = Column(String, nullable=True)
    anticipos_deducidos = Column(JSON, nullable=True)
    total_anticipos = Column(Numeric(12, 2), default=0.0)

    nota_referencia_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True)
    nota_referencia = relationship(
        "Cotizacion",
        foreign_keys=[nota_referencia_id],
        remote_side="Cotizacion.id",
        backref=backref("notas_emitidas", lazy="selectin"),
    )
    nota_motivo_codigo = Column(String, nullable=True)
    nota_motivo_descripcion = Column(Text, nullable=True)

    observaciones = Column(Text, nullable=True)
    condicion_pago = Column(String, nullable=True)
    cuotas_pago = Column(JSON, nullable=True)
    quote_payment_methods = Column(JSON, nullable=True)
    quote_selected_wallet_id = Column(String, nullable=True)

    monto_pagado = Column(Numeric(12, 2), default=0.0)
    saldo_pendiente = Column(Numeric(12, 2), default=0.0)
    pagos = relationship(
        "Pago",
        back_populates="cotizacion",
        foreign_keys="Pago.cotizacion_id",
        cascade="all, delete-orphan",
    )

    @property
    def sunat_accepted(self):
        return bool((self.sunat_cdr_url or self.sunat_cdr_content) and not self.sunat_error)

    @property
    def linked_fiscal_document(self):
        if self.document_kind != "quotation":
            return None
        fiscal_documents = [
            document
            for document in getattr(self, "derived_documents", []) or []
            if getattr(document, "document_kind", None) == "fiscal_document"
            and getattr(document, "estado", None) != "anulada"
        ]
        if not fiscal_documents:
            return None
        return max(fiscal_documents, key=lambda document: document.id)

    @property
    def linked_fiscal_document_id(self):
        document = self.linked_fiscal_document
        return getattr(document, "id", None)

    @property
    def linked_fiscal_document_number(self):
        document = self.linked_fiscal_document
        if not document or not document.serie or document.correlativo is None:
            return None
        return f"{document.serie}-{str(document.correlativo).zfill(6)}"

    @property
    def linked_fiscal_document_status(self):
        document = self.linked_fiscal_document
        return getattr(document, "estado", None)

    @property
    def payment_status(self):
        from decimal import Decimal as _D
        total_venta = self.total_venta or _D("0")
        monto_pagado = self.monto_pagado or _D("0")

        if monto_pagado >= total_venta and total_venta > 0:
            return "pagado"

        if self.fecha_vencimiento is not None:
            from datetime import datetime as _dt
            if _dt.now() > self.fecha_vencimiento:
                return "vencido"

        if monto_pagado > 0:
            return "parcial"
        return "pendiente"

    @property
    def document_number(self):
        if not self.serie or self.correlativo is None:
            return None
        return f"{self.serie}-{str(self.correlativo).zfill(6)}"


class CotizacionItem(Base):
    __tablename__ = "cotizacion_items"

    id = Column(Integer, primary_key=True, index=True)
    cotizacion_id = Column(Integer, ForeignKey("cotizaciones.id"))
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=True)
    codigo_producto = Column(String, nullable=True)

    descripcion = Column(String)
    cantidad = Column(Numeric(12, 2))
    precio_unitario = Column(Numeric(18, 4))
    valor_unitario = Column(Numeric(18, 10))
    total_base_igv = Column(Numeric(12, 2))
    total_igv = Column(Numeric(12, 2))
    total_item = Column(Numeric(12, 2))

    unidad_medida = Column(String, default="NIU")
    tipo_afectacion_igv = Column(String, default="10")

    cotizacion = relationship("Cotizacion", back_populates="items")
