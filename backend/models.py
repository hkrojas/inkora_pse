import uuid
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Numeric, Text, JSON
from sqlalchemy.orm import backref, relationship
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

    # --- SaaS CONTROL & SUNAT (Fase 13) ---
    plan_type = Column(String, default="Free") # Free, Pro, Premium
    plan_start_date = Column(DateTime, default=datetime.now)
    plan_end_date = Column(DateTime, nullable=True)
    invoice_limit = Column(Integer, default=50)
    invoices_used = Column(Integer, default=0)

    # Credenciales SUNAT Reales
    sunat_usuario_sol = Column(String, nullable=True)
    sunat_clave_sol = Column(String, nullable=True)
    sunat_cert_password = Column(String, nullable=True)
    sunat_cert_url = Column(String, nullable=True)

    # --- Relaciones inversas (navegación ORM) ---
    users = relationship("User", back_populates="tenant")
    clientes = relationship("Cliente", back_populates="tenant")
    productos = relationship("Producto", back_populates="tenant")
    cotizaciones = relationship("Cotizacion", back_populates="tenant")
    guias_remision = relationship("GuiaRemision", back_populates="tenant")
    pagos = relationship("Pago", back_populates="tenant")
    insumos = relationship("Insumo", back_populates="tenant")
    recetas = relationship("RecetaBOM", back_populates="tenant")
    ordenes_produccion = relationship("OrdenProduccion", back_populates="tenant")
    proveedores = relationship("Proveedor", back_populates="tenant")
    subscription = relationship("Subscription", back_populates="tenant", uselist=False)
    subscription_payments = relationship("SubscriptionPayment", back_populates="tenant")


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
    is_superadmin = Column(Boolean, default=False)

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
    razon_social = Column(String, index=True)
    nombre_comercial = Column(String, nullable=True)
    direccion = Column(String, nullable=True)          # Dirección fiscal
    ubigeo = Column(String, nullable=True)
    email = Column(String, nullable=True)
    telefono = Column(String, nullable=True)

    # --- FASE 6: Campos de enriquecimiento para launch scope ---
    whatsapp = Column(String, nullable=True)           # Número WhatsApp (puede diferir del telefono)
    contacto = Column(String, nullable=True)           # Nombre del contacto principal
    condicion_pago = Column(String, nullable=True)     # contado | credito_7 | credito_15 | credito_30 | credito_60
    direccion_entrega = Column(String, nullable=True)  # Dirección de entrega (puede diferir de fiscal)
    observaciones = Column(Text, nullable=True)        # Notas internas sobre el cliente

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

    # MRP: Receta (BOM - Lista de Materiales)
    receta = relationship("RecetaBOM", back_populates="producto", cascade="all, delete-orphan")

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
    uuid_publico = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    document_kind = Column(String, default="quotation", nullable=False, index=True)
    internal_order_number = Column(String, nullable=True, index=True)
    source_quote_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True, index=True)

    # --- MULTITENANCIA ---
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="cotizaciones")

    # Relaciones operativas
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    cliente = relationship("Cliente", back_populates="cotizaciones")

    usuario_id = Column(Integer, ForeignKey("users.id"))
    usuario = relationship("User", back_populates="cotizaciones")
    source_quote = relationship(
        "Cotizacion",
        foreign_keys=[source_quote_id],
        remote_side="Cotizacion.id",
        backref=backref("derived_documents", lazy="selectin"),
    )

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
    nota_referencia = relationship(
        "Cotizacion",
        foreign_keys=[nota_referencia_id],
        remote_side="Cotizacion.id",
        backref=backref("notas_emitidas", lazy="selectin"),
    )

    # --- FASE 6: Campos operativos de cotización ---
    observaciones = Column(Text, nullable=True)        # Notas visibles en PDF / internas
    condicion_pago = Column(String, nullable=True)     # Override por cotización (hereda del cliente si no se especifica)

    # --- MOTOR FINANCIERO (Pagos / Adelantos) ---
    monto_pagado = Column(Numeric(12, 2), default=0.0)
    saldo_pendiente = Column(Numeric(12, 2), default=0.0)
    pagos = relationship(
        "Pago",
        back_populates="cotizacion",
        foreign_keys="Pago.cotizacion_id",
        cascade="all, delete-orphan",
    )

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
        """
        Estados de cobranza:
          pagado   — monto_pagado >= total_venta
          parcial  — hay pago pero aún queda saldo
          vencido  — sin pago completo y fecha de vencimiento superada
          pendiente — sin pago y sin vencimiento superado (o sin vencimiento)
        """
        from decimal import Decimal as _D
        total_venta = self.total_venta or _D("0")
        monto_pagado = self.monto_pagado or _D("0")

        if monto_pagado >= total_venta and total_venta > 0:
            return "pagado"

        # Verificar vencimiento
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
    cotizacion = relationship("Cotizacion", foreign_keys=[cotizacion_id])
    source_quote_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True)
    fiscal_document_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True)
    internal_order_number = Column(String, nullable=True, index=True)

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
    cotizacion = relationship(
        "Cotizacion",
        back_populates="pagos",
        foreign_keys=[cotizacion_id],
    )
    source_quote_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True)
    fiscal_document_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True)
    internal_order_number = Column(String, nullable=True, index=True)

    # Datos del pago
    monto_pagado = Column(Numeric(12, 2), nullable=False)
    metodo_pago = Column(String, nullable=False)  # Yape, Transferencia, Efectivo, etc.
    fecha_pago = Column(DateTime, default=datetime.now)
    referencia_operacion = Column(String, nullable=True)  # Nro de operación bancaria
    tipo = Column(String, default="adelanto")  # adelanto, pago_parcial, liquidacion

# ==========================================
# MOTOR DE PRODUCCIÓN (MRP LIGERO / BOM)
# ==========================================

class Insumo(Base):
    """Materia prima o insumo (ej. Papel, Tinta, Plancha)"""
    __tablename__ = "insumos"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="insumos")

    nombre = Column(String, index=True)
    unidad_compra = Column(String)  # ej: Milla, Resma, Litro
    unidad_consumo = Column(String) # ej: Hoja, Pliego, Mililitro
    factor_conversion = Column(Numeric(12, 4)) # 1 unidad_compra = X unidad_consumo
    costo_promedio = Column(Numeric(12, 2), default=0)
    stock_actual = Column(Numeric(12, 2), default=0)
    umbral_minimo = Column(Numeric(12, 2), default=50.0) # FASE 8: Alertas de stock

    # Relacion MRP
    recetas = relationship("RecetaBOM", back_populates="insumo")

class RecetaBOM(Base):
    """Bill of Materials: Cuánto insumo requiere un producto"""
    __tablename__ = "recetas_bom"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="recetas")

    producto_id = Column(Integer, ForeignKey("productos.id"))
    producto = relationship("Producto", back_populates="receta")

    insumo_id = Column(Integer, ForeignKey("insumos.id"))
    insumo = relationship("Insumo", back_populates="recetas")

    cantidad_base_necesaria = Column(Numeric(12, 4)) # ej: 0.1 hojas por cada 1 unidad de producto
    porcentaje_merma_estandar = Column(Numeric(5, 2), default=0.0) # ej: 5.0 (5% merma)

class Proveedor(Base):
    """Proveedores / Talleres tercerizados (Broker)"""
    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="proveedores")

    razon_social = Column(String, index=True)
    ruc = Column(String, index=True)
    direccion = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    email = Column(String, nullable=True)
    tipo_servicio = Column(String, index=True) # Impresión, Acabado, Troquelado, etc.

class OrdenProduccion(Base):
    """Cabecera de la Orden de Trabajo / Producción"""
    __tablename__ = "ordenes_produccion"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="ordenes_produccion")

    cotizacion_id = Column(Integer, ForeignKey("cotizaciones.id"))
    cotizacion = relationship("Cotizacion")

    estado = Column(String, default="en_cola") # en_cola, en_proceso, finalizada, cancelada
    fecha_inicio = Column(DateTime, default=datetime.now)
    fecha_fin = Column(DateTime, nullable=True)
    
    # --- FASE 7: TERCERIZACIÓN (BROKER) ---
    tipo_produccion = Column(String, default="interna") # interna, tercerizada
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True)
    proveedor = relationship("Proveedor")
    costo_tercerizado = Column(Numeric(12, 2), nullable=True)

    detalles = relationship("OrdenProduccionDetalle", back_populates="orden", cascade="all, delete-orphan")

class OrdenProduccionDetalle(Base):
    """Necesidades de material por Orden de Producción (Calculadas)"""
    __tablename__ = "ordenes_produccion_detalle"

    id = Column(Integer, primary_key=True, index=True)
    orden_id = Column(Integer, ForeignKey("ordenes_produccion.id"))
    orden = relationship("OrdenProduccion", back_populates="detalles")

    insumo_id = Column(Integer, ForeignKey("insumos.id"))
    insumo = relationship("Insumo")

    cantidad_requerida_neta = Column(Numeric(12, 4))
    cantidad_merma = Column(Numeric(12, 4))
    cantidad_total_descontar = Column(Numeric(12, 4)) # neta + merma

class AlertaInventario(Base):
    """Alertas del sistema para quiebres de stock (Fase 8)"""
    __tablename__ = "alertas_inventario"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant")

    insumo_id = Column(Integer, ForeignKey("insumos.id"))
    insumo = relationship("Insumo")

    mensaje = Column(String)
    fecha_creacion = Column(DateTime, default=datetime.now)
    resuelta = Column(Boolean, default=False)

# ==========================================
# AUDITORÍA (FASE 13)
# ==========================================

class AuditLog(Base):
    """Log de auditoría paraSuperadmin - registra acciones administrativas."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now)
    
    # Usuario que realizó la acción
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User")
    
    # Tipo de acción
    action = Column(String)  # create, update, delete, login, logout, config_change
    
    # Entidad afectada
    entity_type = Column(String)  # tenant, user, config
    entity_id = Column(Integer, nullable=True)
    
    # Detalles
    details = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)


# ==========================================
# SUSCRIPCION SaaS (FASE 5)
# ==========================================
# Control interno de PrintFlow sobre el acceso de cada tenant.
# Separado del dominio operativo del tenant (cobros a sus clientes).

SUBSCRIPTION_STATUS_ACTIVE = "active"
SUBSCRIPTION_STATUS_SUSPENDED = "suspended"
SUBSCRIPTION_STATUS_TRIAL = "trial"
SUBSCRIPTION_STATUS_EXPIRED = "expired"
SUBSCRIPTION_STATUS_CANCELLED = "cancelled"

ONBOARDING_STATUS_NOT_STARTED = "not_started"
ONBOARDING_STATUS_IN_PROGRESS = "in_progress"
ONBOARDING_STATUS_COMPLETED = "completed"

class Subscription(Base):
    """Suscripcion SaaS de un tenant a PrintFlow."""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, unique=True, index=True)
    tenant = relationship("Tenant", back_populates="subscription")

    # Estado y plan
    status = Column(String, default=SUBSCRIPTION_STATUS_TRIAL, nullable=False, index=True)
    plan_code = Column(String, default="launch", nullable=False)
    current_price = Column(Numeric(10, 2), nullable=True)
    founder_price = Column(Numeric(10, 2), nullable=True)

    # Fechas de ciclo
    billing_started_at = Column(DateTime, nullable=True)
    billing_due_at = Column(DateTime, nullable=True)
    grace_until = Column(DateTime, nullable=True)

    # Limites operativos
    max_users = Column(Integer, default=5, nullable=True)
    max_documents = Column(Integer, default=500, nullable=True)
    documents_used = Column(Integer, default=0, nullable=False)

    # Onboarding
    onboarding_status = Column(String, default=ONBOARDING_STATUS_NOT_STARTED, nullable=False)

    # Control interno
    notes_internal = Column(Text, nullable=True)
    # Fase 9: marca explícita de cliente piloto de la beta cerrada
    is_pilot = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class SubscriptionPayment(Base):
    """Pago de suscripcion SaaS recibido por PrintFlow de un tenant.

    SEPARACION DE DOMINIOS: Este modelo es exclusivo para pagos SaaS
    (tenant -> PrintFlow). No confundir con Pago (cliente -> tenant).
    """
    __tablename__ = "subscription_payments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    tenant = relationship("Tenant", back_populates="subscription_payments")

    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, default="PEN", nullable=False)
    method = Column(String, nullable=False)
    reference = Column(String, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    validated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    validated_by = relationship("User")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
