from decimal import Decimal
from types import SimpleNamespace

import models
from conftest import make_cliente, make_producto, make_tenant, make_user
from schemas.inventory import InventoryActivation, InventoryAdjustmentCreate, ProductInventoryConfig, TransferCreate, TransferLine
from services import inventory_service


def _activate(db, tenant):
    return inventory_service.activate_inventory(db, tenant.id, InventoryActivation())


def _inventory_product(db, tenant, product, warehouse, user, stock="10"):
    inventory_service.configure_product(
        db, tenant.id, product.id,
        ProductInventoryConfig(
            item_type="inventory", inventory_enabled=True,
            warehouse_id=warehouse.id, opening_stock=Decimal(stock), minimum_stock=Decimal("2"),
        ), user.id,
    )
    db.refresh(product)


def test_inventory_is_tenant_scoped(db_session):
    t1, t2 = make_tenant(db_session, "701"), make_tenant(db_session, "702")
    u1 = make_user(db_session, t1, email="inv1@test.pe")
    u2 = make_user(db_session, t2, email="inv2@test.pe")
    p1, p2 = make_producto(db_session, t1, "A"), make_producto(db_session, t2, "B")
    w1, w2 = _activate(db_session, t1), _activate(db_session, t2)
    _inventory_product(db_session, t1, p1, w1, u1)
    _inventory_product(db_session, t2, p2, w2, u2, "25")

    stock = inventory_service.list_stock(db_session, t1.id)
    assert len(stock) == 1
    assert stock[0]["product_id"] == p1.id
    assert stock[0]["on_hand"] == Decimal("10.0000")


def test_adjustment_and_transfer_are_atomic_ledger_entries(db_session):
    tenant = make_tenant(db_session, "703")
    user = make_user(db_session, tenant, email="inv3@test.pe")
    product = make_producto(db_session, tenant, "C")
    source = _activate(db_session, tenant)
    destination = inventory_service.create_warehouse(
        db_session, tenant.id,
        SimpleNamespace(code="TIENDA", name="Tienda", location=None, is_default=False),
    )
    _inventory_product(db_session, tenant, product, source, user)
    inventory_service.adjust_stock(
        db_session, tenant.id,
        InventoryAdjustmentCreate(
            warehouse_id=source.id, product_id=product.id,
            quantity=Decimal("5"), reason="Compra recibida",
        ), user.id,
    )
    inventory_service.transfer_stock(
        db_session, tenant.id,
        TransferCreate(
            source_warehouse_id=source.id, destination_warehouse_id=destination.id,
            reason="Reposicion de tienda", items=[TransferLine(product_id=product.id, quantity=Decimal("4"))],
        ), user.id,
    )
    rows = inventory_service.list_stock(db_session, tenant.id)
    by_warehouse = {row["warehouse_id"]: row for row in rows}
    assert by_warehouse[source.id]["on_hand"] == Decimal("11.0000")
    assert by_warehouse[destination.id]["on_hand"] == Decimal("4.0000")
    assert len(inventory_service.list_movements(db_session, tenant.id, limit=20)) == 4


def test_sunat_acceptance_converts_hold_once(db_session):
    tenant = make_tenant(db_session, "704")
    user = make_user(db_session, tenant, email="inv4@test.pe")
    client = make_cliente(db_session, tenant, "704")
    product = make_producto(db_session, tenant, "D")
    warehouse = _activate(db_session, tenant)
    _inventory_product(db_session, tenant, product, warehouse, user)
    document = models.Cotizacion(
        tenant_id=tenant.id, usuario_id=user.id, cliente_id=client.id,
        serie="F001", correlativo=7, document_kind="fiscal_document",
        tipo_comprobante="01", estado="pendiente", warehouse_id=warehouse.id,
        total_venta=Decimal("10"),
    )
    item = models.CotizacionItem(
        producto_id=product.id, descripcion="Producto", cantidad=Decimal("3"),
        precio_unitario=Decimal("1"), valor_unitario=Decimal("1"),
        total_base_igv=Decimal("3"), total_igv=Decimal("0"), total_item=Decimal("3"),
        unidad_medida="NIU", tipo_afectacion_igv="10",
    )
    document.items.append(item)
    db_session.add(document)
    db_session.commit()
    inventory_service.create_document_holds(db_session, document, user.id)
    db_session.commit()
    assert inventory_service.list_stock(db_session, tenant.id)[0]["committed"] == Decimal("3.0000")

    inventory_service.finalize_document_inventory(db_session, document)
    inventory_service.finalize_document_inventory(db_session, document)
    db_session.commit()
    stock = inventory_service.list_stock(db_session, tenant.id)[0]
    assert stock["on_hand"] == Decimal("7.0000")
    assert stock["committed"] == Decimal("0.0000")
    sales = [row for row in inventory_service.list_movements(db_session, tenant.id, limit=20) if row["movement_type"] == "sale_out"]
    assert len(sales) == 1


def test_rejected_document_releases_hold(db_session):
    tenant = make_tenant(db_session, "705")
    user = make_user(db_session, tenant, email="inv5@test.pe")
    client = make_cliente(db_session, tenant, "705")
    product = make_producto(db_session, tenant, "E")
    warehouse = _activate(db_session, tenant)
    _inventory_product(db_session, tenant, product, warehouse, user)
    document = models.Cotizacion(
        tenant_id=tenant.id, usuario_id=user.id, cliente_id=client.id,
        serie="F001", correlativo=8, document_kind="fiscal_document",
        tipo_comprobante="01", estado="pendiente", warehouse_id=warehouse.id,
        total_venta=Decimal("10"),
    )
    document.items.append(models.CotizacionItem(
        producto_id=product.id, descripcion="Producto", cantidad=Decimal("2"),
        precio_unitario=1, valor_unitario=1, total_base_igv=2, total_igv=0,
        total_item=2, unidad_medida="NIU", tipo_afectacion_igv="10",
    ))
    db_session.add(document); db_session.commit()
    inventory_service.create_document_holds(db_session, document, user.id); db_session.commit()
    inventory_service.release_document_holds(db_session, document); db_session.commit()
    row = inventory_service.list_stock(db_session, tenant.id)[0]
    assert row["on_hand"] == Decimal("10.0000")
    assert row["committed"] == Decimal("0.0000")


def test_credit_note_distinguishes_undelivered_and_physical_return(db_session):
    tenant = make_tenant(db_session, "706")
    user = make_user(db_session, tenant, email="inv6@test.pe")
    client = make_cliente(db_session, tenant, "706")
    product = make_producto(db_session, tenant, "F")
    warehouse = _activate(db_session, tenant)
    _inventory_product(db_session, tenant, product, warehouse, user)
    original = models.Cotizacion(
        tenant_id=tenant.id, usuario_id=user.id, cliente_id=client.id,
        serie="F001", correlativo=9, document_kind="fiscal_document",
        tipo_comprobante="01", estado="facturada", warehouse_id=warehouse.id,
        total_venta=10,
    )
    original_item = models.CotizacionItem(
        producto_id=product.id, descripcion="Producto", cantidad=4,
        precio_unitario=1, valor_unitario=1, total_base_igv=4, total_igv=0,
        total_item=4, unidad_medida="NIU", tipo_afectacion_igv="10",
    )
    original.items.append(original_item); db_session.add(original); db_session.commit()
    balance = inventory_service._balance(db_session, tenant.id, warehouse.id, product.id)
    inventory_service._record_movement(
        db_session, balance, Decimal("-4"), "sale_out", "fiscal_document",
        original.id, original_item.id, user.id, "Venta", f"sale:{original.id}:{original_item.id}",
    ); db_session.commit()

    note = models.Cotizacion(
        tenant_id=tenant.id, usuario_id=user.id, cliente_id=client.id,
        serie="FC01", correlativo=1, document_kind="credit_note",
        tipo_comprobante="07", estado="facturada", warehouse_id=warehouse.id,
        nota_referencia_id=original.id, inventory_impact="undelivered", total_venta=2,
    )
    note.items.append(models.CotizacionItem(
        producto_id=product.id, inventory_source_item_id=original_item.id,
        descripcion="Producto", cantidad=2, precio_unitario=1, valor_unitario=1,
        total_base_igv=2, total_igv=0, total_item=2,
        unidad_medida="NIU", tipo_afectacion_igv="10",
    ))
    db_session.add(note); db_session.commit()
    inventory_service.apply_credit_note_inventory(db_session, note)
    inventory_service.apply_credit_note_inventory(db_session, note)
    db_session.commit()
    assert inventory_service.list_stock(db_session, tenant.id)[0]["on_hand"] == Decimal("8.0000")

    physical = models.Cotizacion(
        tenant_id=tenant.id, usuario_id=user.id, cliente_id=client.id,
        serie="FC01", correlativo=2, document_kind="credit_note",
        tipo_comprobante="07", estado="facturada", warehouse_id=warehouse.id,
        inventory_return_warehouse_id=warehouse.id,
        nota_referencia_id=original.id, inventory_impact="physical_return", total_venta=1,
    )
    physical.items.append(models.CotizacionItem(
        producto_id=product.id, inventory_source_item_id=original_item.id,
        descripcion="Producto", cantidad=1, precio_unitario=1, valor_unitario=1,
        total_base_igv=1, total_igv=0, total_item=1,
        unidad_medida="NIU", tipo_afectacion_igv="10",
    ))
    db_session.add(physical); db_session.commit()
    pending = inventory_service.apply_credit_note_inventory(db_session, physical); db_session.commit()
    assert pending.status == "pending"
    assert inventory_service.list_stock(db_session, tenant.id)[0]["on_hand"] == Decimal("8.0000")
