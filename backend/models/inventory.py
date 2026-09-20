"""Commercial inventory ledger, isolated from the frozen MRP domain."""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from database import Base


class Warehouse(Base):
    __tablename__ = "warehouses"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_warehouses_tenant_code"),
        Index("ix_warehouses_tenant_active", "tenant_id", "is_active"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    establishment_id = Column(Integer, ForeignKey("tenant_establishments.id"), nullable=True, index=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    location = Column(Text, nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    balances = relationship("InventoryBalance", back_populates="warehouse")
    establishment = relationship("TenantEstablishment", back_populates="warehouses")


class TenantEstablishment(Base):
    """SUNAT establishment owned by one tenant.

    Warehouses remain operational inventory locations.  More than one warehouse
    may belong to the same fiscal establishment and therefore move stock without
    requiring a GRE.
    """

    __tablename__ = "tenant_establishments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "sunat_code", name="uq_tenant_establishments_code"),
        Index("ix_tenant_establishments_active", "tenant_id", "is_active"),
        Index(
            "uq_tenant_establishments_main",
            "tenant_id",
            unique=True,
            postgresql_where=text("is_main IS TRUE"),
            sqlite_where=text("is_main = 1"),
        ),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    sunat_code = Column(String(4), nullable=False)
    name = Column(String(120), nullable=False)
    ubigeo = Column(String(6), nullable=False)
    address = Column(Text, nullable=False)
    is_main = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    verified_at = Column(DateTime, nullable=True)
    verified_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verification_note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    warehouses = relationship("Warehouse", back_populates="establishment")


class InventoryBalance(Base):
    __tablename__ = "inventory_balances"
    __table_args__ = (
        UniqueConstraint("tenant_id", "warehouse_id", "product_id", name="uq_inventory_balance_scope"),
        Index("ix_inventory_balances_tenant_product", "tenant_id", "product_id"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    on_hand = Column(Numeric(18, 4), nullable=False, default=0)
    committed = Column(Numeric(18, 4), nullable=False, default=0)
    minimum_stock = Column(Numeric(18, 4), nullable=False, default=0)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    warehouse = relationship("Warehouse", back_populates="balances")
    product = relationship("Producto")

    @property
    def available(self):
        return (self.on_hand or 0) - (self.committed or 0)


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_inventory_movement_idempotency"),
        Index("ix_inventory_movements_scope_date", "tenant_id", "warehouse_id", "product_id", "created_at"),
        Index("ix_inventory_movements_source", "tenant_id", "source_type", "source_id"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    movement_type = Column(String, nullable=False)
    quantity = Column(Numeric(18, 4), nullable=False)
    balance_before = Column(Numeric(18, 4), nullable=False)
    balance_after = Column(Numeric(18, 4), nullable=False)
    source_type = Column(String, nullable=False)
    source_id = Column(Integer, nullable=True)
    source_line_id = Column(Integer, nullable=True)
    related_movement_id = Column(Integer, ForeignKey("inventory_movements.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reason = Column(Text, nullable=True)
    idempotency_key = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    warehouse = relationship("Warehouse")
    product = relationship("Producto")


class InventoryHold(Base):
    __tablename__ = "inventory_holds"
    __table_args__ = (
        UniqueConstraint("tenant_id", "document_id", "document_item_id", name="uq_inventory_hold_document_line"),
        Index("ix_inventory_holds_tenant_status", "tenant_id", "status", "created_at"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=False)
    document_item_id = Column(Integer, ForeignKey("cotizacion_items.id"), nullable=False)
    quantity = Column(Numeric(18, 4), nullable=False)
    status = Column(String, nullable=False, default="active")
    negative_override = Column(Boolean, nullable=False, default=False)
    override_reason = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    resolved_at = Column(DateTime, nullable=True)


class InventoryTransfer(Base):
    __tablename__ = "inventory_transfers"
    __table_args__ = (Index("ix_inventory_transfers_tenant_date", "tenant_id", "created_at"),)

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    source_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    destination_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    status = Column(String, nullable=False, default="completed")
    lifecycle_mode = Column(String, nullable=False, default="legacy_immediate")
    reason = Column(Text, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    items = relationship("InventoryTransferItem", cascade="all, delete-orphan")


class InventoryTransferItem(Base):
    __tablename__ = "inventory_transfer_items"

    id = Column(Integer, primary_key=True)
    transfer_id = Column(Integer, ForeignKey("inventory_transfers.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    quantity = Column(Numeric(18, 4), nullable=False)


class InternalTransferOrder(Base):
    """Planned national movement between establishments of the same tenant."""

    __tablename__ = "internal_transfer_orders"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_internal_transfer_order_idempotency"),
        Index("ix_internal_transfer_order_status", "tenant_id", "status", "created_at"),
        CheckConstraint("version >= 1", name="ck_internal_transfer_order_version"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    source_establishment_id = Column(Integer, ForeignKey("tenant_establishments.id"), nullable=False)
    destination_establishment_id = Column(Integer, ForeignKey("tenant_establishments.id"), nullable=False)
    source_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    destination_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    status = Column(String, nullable=False, default="draft")
    reason = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    idempotency_key = Column(String(120), nullable=False)
    request_fingerprint = Column(String(64), nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    source_establishment = relationship("TenantEstablishment", foreign_keys=[source_establishment_id])
    destination_establishment = relationship("TenantEstablishment", foreign_keys=[destination_establishment_id])
    source_warehouse = relationship("Warehouse", foreign_keys=[source_warehouse_id])
    destination_warehouse = relationship("Warehouse", foreign_keys=[destination_warehouse_id])
    lines = relationship("InternalTransferOrderLine", back_populates="transfer", cascade="all, delete-orphan")
    dispatches = relationship("InternalTransferDispatch", back_populates="transfer", cascade="all, delete-orphan")


class InternalTransferOrderLine(Base):
    __tablename__ = "internal_transfer_order_lines"
    __table_args__ = (
        Index("ix_internal_transfer_order_line_product", "tenant_id", "product_id"),
        CheckConstraint("quantity > 0", name="ck_internal_transfer_order_line_quantity"),
        CheckConstraint(
            "cancelled_quantity >= 0 AND cancelled_quantity <= quantity",
            name="ck_internal_transfer_order_line_cancelled_quantity",
        ),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    transfer_id = Column(Integer, ForeignKey("internal_transfer_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("productos.id"), nullable=True)
    description = Column(String(500), nullable=False)
    product_code = Column(String(100), nullable=True)
    unit_code = Column(String(10), nullable=False)
    quantity = Column(Numeric(18, 4), nullable=False)
    cancelled_quantity = Column(Numeric(18, 4), nullable=False, default=0)
    inventory_controlled = Column(Boolean, nullable=False, default=False)

    transfer = relationship("InternalTransferOrder", back_populates="lines")
    product = relationship("Producto")
    dispatch_lines = relationship("InternalTransferDispatchLine", back_populates="transfer_line")


class InternalTransferDispatch(Base):
    __tablename__ = "internal_transfer_dispatches"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_internal_transfer_dispatch_idempotency"),
        UniqueConstraint(
            "tenant_id",
            "departure_idempotency_key",
            name="uq_internal_transfer_departure_idempotency",
        ),
        Index("ix_internal_transfer_dispatch_status", "tenant_id", "status", "created_at"),
        CheckConstraint("version >= 1", name="ck_internal_transfer_dispatch_version"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    transfer_id = Column(Integer, ForeignKey("internal_transfer_orders.id"), nullable=False)
    status = Column(String, nullable=False, default="reserved")
    version = Column(Integer, nullable=False, default=1)
    idempotency_key = Column(String(120), nullable=False)
    request_fingerprint = Column(String(64), nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    departure_idempotency_key = Column(String(120), nullable=True)
    departure_confirmed_at = Column(DateTime, nullable=True)
    departure_confirmed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    transfer = relationship("InternalTransferOrder", back_populates="dispatches")
    lines = relationship("InternalTransferDispatchLine", back_populates="dispatch", cascade="all, delete-orphan")
    guides = relationship("GuiaRemision", back_populates="internal_transfer_dispatch")
    receipts = relationship("InternalTransferReceipt", back_populates="dispatch", cascade="all, delete-orphan")


class InternalTransferDispatchLine(Base):
    __tablename__ = "internal_transfer_dispatch_lines"
    __table_args__ = (
        UniqueConstraint("dispatch_id", "transfer_line_id", name="uq_internal_transfer_dispatch_line"),
        CheckConstraint("quantity > 0", name="ck_internal_transfer_dispatch_line_quantity"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    dispatch_id = Column(Integer, ForeignKey("internal_transfer_dispatches.id"), nullable=False)
    transfer_line_id = Column(Integer, ForeignKey("internal_transfer_order_lines.id"), nullable=False)
    quantity = Column(Numeric(18, 4), nullable=False)
    reservation_status = Column(String, nullable=False, default="active")
    reserved_at = Column(DateTime, nullable=False, default=datetime.now)
    covered_at = Column(DateTime, nullable=True)
    released_at = Column(DateTime, nullable=True)
    departed_quantity = Column(Numeric(18, 4), nullable=False, default=0)
    received_quantity = Column(Numeric(18, 4), nullable=False, default=0)
    source_movement_id = Column(Integer, ForeignKey("inventory_movements.id"), nullable=True)

    dispatch = relationship("InternalTransferDispatch", back_populates="lines")
    transfer_line = relationship("InternalTransferOrderLine", back_populates="dispatch_lines")
    source_movement = relationship("InventoryMovement", foreign_keys=[source_movement_id])


class InternalTransferReceipt(Base):
    __tablename__ = "internal_transfer_receipts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_internal_transfer_receipt_idempotency"),
        Index("ix_internal_transfer_receipt_dispatch", "tenant_id", "dispatch_id", "received_at"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    dispatch_id = Column(Integer, ForeignKey("internal_transfer_dispatches.id"), nullable=False)
    idempotency_key = Column(String(120), nullable=False)
    request_fingerprint = Column(String(64), nullable=False)
    note = Column(Text, nullable=True)
    received_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    received_at = Column(DateTime, nullable=False, default=datetime.now)

    dispatch = relationship("InternalTransferDispatch", back_populates="receipts")
    lines = relationship("InternalTransferReceiptLine", back_populates="receipt", cascade="all, delete-orphan")


class InternalTransferReceiptLine(Base):
    __tablename__ = "internal_transfer_receipt_lines"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_internal_transfer_receipt_line_quantity"),)

    id = Column(Integer, primary_key=True)
    receipt_id = Column(Integer, ForeignKey("internal_transfer_receipts.id"), nullable=False)
    dispatch_line_id = Column(Integer, ForeignKey("internal_transfer_dispatch_lines.id"), nullable=False)
    quantity = Column(Numeric(18, 4), nullable=False)
    destination_movement_id = Column(Integer, ForeignKey("inventory_movements.id"), nullable=True)

    receipt = relationship("InternalTransferReceipt", back_populates="lines")
    dispatch_line = relationship("InternalTransferDispatchLine")
    destination_movement = relationship("InventoryMovement", foreign_keys=[destination_movement_id])


class InventoryReturn(Base):
    __tablename__ = "inventory_returns"
    __table_args__ = (UniqueConstraint("tenant_id", "credit_note_id", name="uq_inventory_return_note"),)

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    credit_note_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    received_at = Column(DateTime, nullable=True)
    received_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    items = relationship("InventoryReturnItem", cascade="all, delete-orphan")


class InventoryReturnItem(Base):
    __tablename__ = "inventory_return_items"

    id = Column(Integer, primary_key=True)
    return_id = Column(Integer, ForeignKey("inventory_returns.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    note_item_id = Column(Integer, ForeignKey("cotizacion_items.id"), nullable=False)
    authorized_quantity = Column(Numeric(18, 4), nullable=False)
    received_quantity = Column(Numeric(18, 4), nullable=False, default=0)
