"""Commercial inventory ledger, isolated from the frozen MRP domain."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
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
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    location = Column(Text, nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    balances = relationship("InventoryBalance", back_populates="warehouse")


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
