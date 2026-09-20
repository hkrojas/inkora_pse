"""models/guias.py — GuiaRemision, GuiaRemisionItem."""
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


DISPATCH_STATUS_PROVISIONAL = "provisional"
DISPATCH_STATUS_DRAFT = "draft"
DISPATCH_STATUS_GUIDE_PENDING = "guide_pending"
DISPATCH_STATUS_GUIDE_ACCEPTED = "guide_accepted"
DISPATCH_STATUS_GUIDE_REJECTED = "guide_rejected"
DISPATCH_STATUS_DEPARTED = "departed"
DISPATCH_STATUS_CANCELLED = "cancelled"
DISPATCH_STATUS_BLOCKED = "blocked"

DISPATCH_RESERVATION_PROVISIONAL = "provisional"
DISPATCH_RESERVATION_ACTIVE = "active"
DISPATCH_RESERVATION_COVERED = "covered"
DISPATCH_RESERVATION_RELEASED = "released"


class SaleDispatch(Base):
    """Operational shipment created from one accepted sales fiscal document."""

    __tablename__ = "sale_dispatches"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_sale_dispatches_tenant_idempotency"),
        Index("ix_sale_dispatches_invoice_status", "tenant_id", "fiscal_document_id", "status"),
        Index("ix_sale_dispatches_source_summary", "tenant_id", "source_summary_id"),
        CheckConstraint("version >= 1", name="ck_sale_dispatches_version_positive"),
        CheckConstraint("source_document_type IN ('01', '03')", name="ck_sale_dispatches_source_document_type"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    fiscal_document_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=False)
    source_document_type = Column(String, nullable=False, default="01", server_default="01")
    source_summary_id = Column(Integer, ForeignKey("resumenes_diarios.id"), nullable=True)
    source_acceptance_evidence = Column(JSON, nullable=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, nullable=False, default=DISPATCH_STATUS_DRAFT)
    version = Column(Integer, nullable=False, default=1)
    idempotency_key = Column(String, nullable=False)
    request_fingerprint = Column(String, nullable=False)
    provisional_invoice_fingerprint = Column(String, nullable=True)
    logistical_block_code = Column(String, nullable=True)
    logistical_block_detail = Column(Text, nullable=True)
    departure_confirmed_at = Column(DateTime, nullable=True)
    departure_confirmed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    fiscal_document = relationship("Cotizacion", foreign_keys=[fiscal_document_id])
    source_summary = relationship("ResumenDiario", foreign_keys=[source_summary_id])
    warehouse = relationship("Warehouse")
    lines = relationship("SaleDispatchLine", back_populates="dispatch", cascade="all, delete-orphan")
    guides = relationship("GuiaRemision", back_populates="dispatch")


class SaleDispatchLine(Base):
    """Permanent allocation of one invoice line to one dispatch."""

    __tablename__ = "sale_dispatch_lines"
    __table_args__ = (
        UniqueConstraint("dispatch_id", "fiscal_document_item_id", name="uq_sale_dispatch_lines_invoice_line"),
        Index("ix_sale_dispatch_lines_availability", "tenant_id", "fiscal_document_item_id", "reservation_status"),
        CheckConstraint("quantity > 0", name="ck_sale_dispatch_lines_quantity_positive"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    dispatch_id = Column(Integer, ForeignKey("sale_dispatches.id"), nullable=False)
    fiscal_document_item_id = Column(Integer, ForeignKey("cotizacion_items.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("productos.id"), nullable=True)
    inventory_movement_id = Column(Integer, ForeignKey("inventory_movements.id"), nullable=True)
    quantity = Column(Numeric(18, 4), nullable=False)
    unit_code = Column(String, nullable=False)
    product_code = Column(String, nullable=True)
    description = Column(String, nullable=False)
    confirmed_as_goods = Column(Boolean, nullable=False, default=False)
    reservation_status = Column(String, nullable=False, default=DISPATCH_RESERVATION_ACTIVE)
    reserved_at = Column(DateTime, nullable=True)
    covered_at = Column(DateTime, nullable=True)
    released_at = Column(DateTime, nullable=True)

    dispatch = relationship("SaleDispatch", back_populates="lines")
    fiscal_document_item = relationship("CotizacionItem")
    inventory_movement = relationship("InventoryMovement")


class GuideExternalReference(Base):
    """Tenant-owned evidence for GRE or invoices issued by another company."""

    __tablename__ = "guide_external_references"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "document_type", "issuer_ruc", "series", "number",
            name="uq_guide_external_reference_identity",
        ),
        Index("ix_guide_external_reference_tenant_type", "tenant_id", "document_type"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    document_type = Column(String, nullable=False)
    issuer_ruc = Column(String, nullable=False)
    series = Column(String, nullable=False)
    number = Column(String, nullable=False)
    source = Column(String, nullable=False, default="manual")
    verification_status = Column(String, nullable=False, default="unverified")
    evidence = Column(JSON, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class GuiaRemision(Base):
    __tablename__ = "guias_remision"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "serie",
            "correlativo",
            name="uq_guias_remision_tenant_serie_correlativo",
        ),
        Index("ix_guias_remision_tenant_estado_fecha", "tenant_id", "estado", "fecha_emision"),
        Index("ix_guias_remision_tenant_sunat_ticket", "tenant_id", "sunat_ticket"),
        UniqueConstraint("tenant_id", "creation_idempotency_key", name="uq_guias_tenant_creation_idempotency"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tipo_documento = Column(String, nullable=False, default="09", server_default="09")
    serie = Column(String, default="T001")
    correlativo = Column(Integer)
    fecha_emision = Column(DateTime, default=datetime.now)
    fecha_traslado = Column(DateTime)
    estado = Column(String, default="pendiente")

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="guias_remision")

    cotizacion_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True)
    cotizacion = relationship("Cotizacion", foreign_keys=[cotizacion_id])
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)
    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    source_quote_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True)
    fiscal_document_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True)
    dispatch_id = Column(Integer, ForeignKey("sale_dispatches.id"), nullable=True, index=True)
    related_guide_id = Column(Integer, ForeignKey("guias_remision.id"), nullable=True, index=True)
    external_gre_reference_id = Column(Integer, ForeignKey("guide_external_references.id"), nullable=True)
    goods_invoice_reference_id = Column(Integer, ForeignKey("guide_external_references.id"), nullable=True)
    freight_invoice_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True)
    internal_order_number = Column(String, nullable=True, index=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    creation_idempotency_key = Column(String, nullable=True)

    usuario_id = Column(Integer, ForeignKey("users.id"))
    usuario = relationship("User", foreign_keys=[usuario_id])

    motivo_traslado = Column(String, default="01")
    descripcion_motivo = Column(String, nullable=True)
    peso_bruto_total = Column(Numeric(12, 3))
    unidad_medida_peso = Column(String, default="KGM")
    numero_bultos = Column(Integer, nullable=True)
    modalidad_traslado = Column(String, default="01")
    fecha_entrega_transportista = Column(DateTime, nullable=True)
    indicador_m1_l = Column(Boolean, nullable=False, default=False, server_default="0")
    registrar_vehiculo_transportista = Column(Boolean, nullable=False, default=False, server_default="0")
    transportista_acuerdo_confirmado_at = Column(DateTime, nullable=True)
    transportista_acuerdo_confirmado_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    transportista_acuerdo_confirmado_by = relationship(
        "User",
        foreign_keys=[transportista_acuerdo_confirmado_by_user_id],
    )
    observaciones = Column(Text, nullable=True)
    sustento_peso = Column(String, nullable=True)
    ind_transbordo = Column(Boolean, nullable=True, default=False)
    num_contenedor = Column(String, nullable=True)
    cod_puerto = Column(String, nullable=True)

    transportista_ruc = Column(String, nullable=True)
    transportista_razon_social = Column(String, nullable=True)
    transportista_nro_mtc = Column(String, nullable=True)

    remitente_tipo_doc = Column(String, nullable=True)
    remitente_nro_doc = Column(String, nullable=True)
    remitente_razon_social = Column(String, nullable=True)
    destinatario_tipo_doc = Column(String, nullable=True)
    destinatario_nro_doc = Column(String, nullable=True)
    destinatario_razon_social = Column(String, nullable=True)
    pagador_flete_tipo = Column(String, nullable=True)
    pagador_tipo_doc = Column(String, nullable=True)
    pagador_nro_doc = Column(String, nullable=True)
    pagador_razon_social = Column(String, nullable=True)

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
    sunat_xml_content = Column(Text, nullable=True)
    sunat_hash = Column(String, nullable=True)
    sunat_ticket = Column(String, nullable=True)
    provider_response = Column(JSON, nullable=True)
    provider_endpoint = Column(String, nullable=True)
    provider_status_code = Column(Integer, nullable=True)
    sunat_status_checked_at = Column(DateTime, nullable=True)
    sunat_error = Column(Text, nullable=True)
    frozen_payload = Column(JSON, nullable=True)
    frozen_xml = Column(Text, nullable=True)
    emission_environment = Column(String, nullable=True)
    rejected_at = Column(DateTime, nullable=True)

    items = relationship("GuiaRemisionItem", back_populates="guia", cascade="all, delete-orphan")
    dispatch = relationship("SaleDispatch", back_populates="guides")
    related_guide = relationship("GuiaRemision", remote_side=[id], foreign_keys=[related_guide_id])
    external_gre_reference = relationship("GuideExternalReference", foreign_keys=[external_gre_reference_id])
    goods_invoice_reference = relationship("GuideExternalReference", foreign_keys=[goods_invoice_reference_id])

    @property
    def cdr_disponible(self) -> bool:
        """Indica si existe evidencia CDR sin exponer la respuesta del proveedor."""
        if self.sunat_cdr_url:
            return True

        def has_cdr(value):
            if not isinstance(value, dict):
                return False
            if value.get("cdr"):
                return True
            return any(
                has_cdr(value.get(key))
                for key in ("process", "verification", "data", "sunat_response")
            )

        return has_cdr(self.provider_response or {})

    @property
    def xml_disponible(self) -> bool:
        return bool(self.sunat_xml_url or self.sunat_xml_content)

    @property
    def cliente_nombre(self):
        if self.cliente:
            return self.cliente.razon_social or self.cliente.nombre or None
        if self.cotizacion and self.cotizacion.cliente:
            c = self.cotizacion.cliente
            return c.razon_social or c.nombre or None
        return None

    @property
    def cliente_documento(self):
        if self.cliente:
            return self.cliente.numero_documento or None
        if self.cotizacion and self.cotizacion.cliente:
            return self.cotizacion.cliente.numero_documento or None
        return None


class GuiaRemisionItem(Base):
    __tablename__ = "guia_remision_items"

    id = Column(Integer, primary_key=True, index=True)
    guia_id = Column(Integer, ForeignKey("guias_remision.id"))
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=True, index=True)
    dispatch_line_id = Column(Integer, ForeignKey("sale_dispatch_lines.id"), nullable=True, index=True)
    fiscal_document_item_id = Column(Integer, ForeignKey("cotizacion_items.id"), nullable=True, index=True)

    descripcion = Column(String)
    cantidad = Column(Numeric(18, 4))
    unidad_medida = Column(String, default="NIU")
    codigo_producto = Column(String, nullable=True)
    peso_item = Column(Numeric(12, 3), nullable=True)

    guia = relationship("GuiaRemision", back_populates="items")
    dispatch_line = relationship("SaleDispatchLine")
