"""models/tenants.py — Tenant, User, AuditLog, Subscription, SubscriptionPayment."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import relationship

from database import Base

# ==========================================
# TENANT
# ==========================================

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)

    business_name = Column(String, nullable=False)
    business_ruc = Column(String, nullable=False, unique=True, index=True)
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

    plan_type = Column(String, default="Free")
    plan_start_date = Column(DateTime, default=datetime.now)
    plan_end_date = Column(DateTime, nullable=True)
    invoice_limit = Column(Integer, default=50)
    invoices_used = Column(Integer, default=0)

    sunat_usuario_sol = Column(String, nullable=True)
    sunat_clave_sol = Column(String, nullable=True)
    sunat_cert_password = Column(String, nullable=True)
    sunat_cert_url = Column(String, nullable=True)

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
# USER
# ==========================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    nombre_completo = Column(String)
    rol = Column(String, default="vendedor")
    is_superadmin = Column(Boolean, default=False)

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="users")

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

    cotizaciones = relationship("Cotizacion", back_populates="usuario")


# ==========================================
# AUDIT LOG
# ==========================================

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now)

    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User")

    action = Column(String)
    entity_type = Column(String)
    entity_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)


# ==========================================
# SUBSCRIPCION SAAS
# ==========================================

SUBSCRIPTION_STATUS_ACTIVE = "active"
SUBSCRIPTION_STATUS_SUSPENDED = "suspended"
SUBSCRIPTION_STATUS_TRIAL = "trial"
SUBSCRIPTION_STATUS_EXPIRED = "expired"
SUBSCRIPTION_STATUS_CANCELLED = "cancelled"

ONBOARDING_STATUS_NOT_STARTED = "not_started"
ONBOARDING_STATUS_IN_PROGRESS = "in_progress"
ONBOARDING_STATUS_COMPLETED = "completed"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, unique=True, index=True)
    tenant = relationship("Tenant", back_populates="subscription")

    status = Column(String, default=SUBSCRIPTION_STATUS_TRIAL, nullable=False, index=True)
    plan_code = Column(String, default="launch", nullable=False)
    current_price = Column(Numeric(10, 2), nullable=True)
    founder_price = Column(Numeric(10, 2), nullable=True)

    billing_started_at = Column(DateTime, nullable=True)
    billing_due_at = Column(DateTime, nullable=True)
    grace_until = Column(DateTime, nullable=True)

    max_users = Column(Integer, default=5, nullable=True)
    max_documents = Column(Integer, default=500, nullable=True)
    documents_used = Column(Integer, default=0, nullable=False)

    onboarding_status = Column(String, default=ONBOARDING_STATUS_NOT_STARTED, nullable=False)
    notes_internal = Column(Text, nullable=True)
    is_pilot = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class SubscriptionPayment(Base):
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
