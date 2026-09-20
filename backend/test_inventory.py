from decimal import Decimal
from datetime import datetime, timedelta
from types import SimpleNamespace
import pytest
from fastapi import HTTPException

import models
from conftest import make_cliente, make_producto, make_tenant, make_user
from schemas.inventory import InventoryActivation, InventoryAdjustmentCreate, ProductInventoryConfig, TransferCreate, TransferLine
from schemas.inventory import (
    BulkInventoryAdjustmentCreate,
    BulkInventoryLine,
    WarehouseCreate,
    WarehouseFiscalVerify,
    WarehouseResponse,
    WarehouseUpdate,
)
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


def test_warehouse_manages_its_sunat_location_atomically(db_session):
    tenant = make_tenant(db_session, "700A")
    user = make_user(db_session, tenant, email="warehouse700a@test.pe")

    warehouse = inventory_service.create_warehouse(
        db_session,
        tenant.id,
        WarehouseCreate(
            code="principal",
            name="Almacén principal",
            location="Av. Lima 100",
            is_default=True,
            sunat_code="0000",
            ubigeo="150101",
            is_sunat_main=True,
        ),
    )

    assert warehouse.establishment_id is not None
    assert warehouse.establishment.sunat_code == "0000"
    assert warehouse.establishment.ubigeo == "150101"
    assert warehouse.establishment.address == "Av. Lima 100"
    assert warehouse.establishment.verified_at is None
    serialized = WarehouseResponse.model_validate(warehouse)
    assert serialized.establishment.sunat_code == "0000"

    inventory_service.verify_warehouse_fiscal_location(
        db_session,
        tenant.id,
        warehouse.id,
        user.id,
        WarehouseFiscalVerify(note="Contrastado con la ficha RUC de SUNAT."),
    )
    assert warehouse.establishment.verified_at is not None

    inventory_service.update_warehouse(
        db_session,
        tenant.id,
        warehouse.id,
        WarehouseUpdate(
            name="Almacén principal",
            location="Av. Lima 200",
            is_default=True,
            sunat_code="0000",
            ubigeo="150101",
            is_sunat_main=True,
        ),
    )
    assert warehouse.establishment.address == "Av. Lima 200"
    assert warehouse.establishment.verified_at is None


def test_warehouse_sunat_code_is_unique_and_tenant_scoped(db_session):
    owner = make_tenant(db_session, "700B")
    other = make_tenant(db_session, "700C")
    first = inventory_service.create_warehouse(
        db_session,
        owner.id,
        WarehouseCreate(
            code="A",
            name="Sede A",
            location="Av. A 100",
            sunat_code="0001",
            ubigeo="150101",
        ),
    )

    with pytest.raises(HTTPException) as exc:
        inventory_service.create_warehouse(
            db_session,
            owner.id,
            WarehouseCreate(
                code="B",
                name="Sede B",
                location="Av. B 200",
                sunat_code="0001",
                ubigeo="150102",
            ),
        )
    assert exc.value.status_code == 409

    with pytest.raises(HTTPException) as exc:
        inventory_service.verify_warehouse_fiscal_location(
            db_session,
            other.id,
            first.id,
            999,
            WarehouseFiscalVerify(note="Intento desde otra empresa autenticada."),
        )
    assert exc.value.status_code == 404


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


def test_document_availability_aggregates_repeated_products_without_writes(db_session):
    tenant = make_tenant(db_session, "702A")
    user = make_user(db_session, tenant, email="inv702a@test.pe")
    client = make_cliente(db_session, tenant, "702A")
    product = make_producto(db_session, tenant, "702A")
    warehouse = _activate(db_session, tenant)
    _inventory_product(db_session, tenant, product, warehouse, user, "5")
    quote = models.Cotizacion(
        tenant_id=tenant.id, usuario_id=user.id, cliente_id=client.id,
        serie="COT", correlativo=1, document_kind="quotation",
        tipo_comprobante="00", estado="pendiente", warehouse_id=warehouse.id,
        total_venta=Decimal("6"),
    )
    for quantity in (Decimal("3"), Decimal("3")):
        quote.items.append(models.CotizacionItem(
            producto_id=product.id, descripcion="Producto repetido", cantidad=quantity,
            precio_unitario=Decimal("1"), valor_unitario=Decimal("1"),
            total_base_igv=quantity, total_igv=Decimal("0"), total_item=quantity,
            unidad_medida="NIU", tipo_afectacion_igv="10",
        ))
    db_session.add(quote)
    db_session.commit()
    movement_count = db_session.query(models.InventoryMovement).count()
    balance_count = db_session.query(models.InventoryBalance).count()

    result = inventory_service.check_document_availability(db_session, tenant.id, quote.id)

    assert result["inventory_enabled"] is True
    assert result["sufficient"] is False
    assert len(result["items"]) == 1
    assert result["items"][0]["requested"] == Decimal("6.0000")
    assert result["items"][0]["available"] == Decimal("5.0000")
    assert db_session.query(models.InventoryMovement).count() == movement_count
    assert db_session.query(models.InventoryBalance).count() == balance_count


def test_document_availability_distinguishes_disabled_and_missing_warehouse(db_session):
    tenant = make_tenant(db_session, "702B")
    user = make_user(db_session, tenant, email="inv702b@test.pe")
    client = make_cliente(db_session, tenant, "702B")
    quote = models.Cotizacion(
        tenant_id=tenant.id, usuario_id=user.id, cliente_id=client.id,
        serie="COT", correlativo=1, document_kind="quotation",
        tipo_comprobante="00", estado="pendiente", total_venta=Decimal("1"),
    )
    db_session.add(quote)
    db_session.commit()
    disabled = inventory_service.check_document_availability(db_session, tenant.id, quote.id)
    assert disabled["configuration_status"] == "disabled"
    assert disabled["sufficient"] is True

    tenant.inventory_enabled = True
    db_session.commit()
    missing = inventory_service.check_document_availability(db_session, tenant.id, quote.id)
    assert missing["configuration_status"] == "warehouse_required"
    assert missing["sufficient"] is False


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
    assert inventory_service.count_movements(db_session, tenant.id) == 4
    assert inventory_service.count_movements(db_session, tenant.id, direction="entry") == 3
    assert inventory_service.count_movements(db_session, tenant.id, direction="exit") == 1
    page = inventory_service.list_movements(db_session, tenant.id, skip=1, limit=2)
    assert len(page) == 2


def test_movement_count_is_tenant_scoped(db_session):
    t1, t2 = make_tenant(db_session, "703A"), make_tenant(db_session, "703B")
    u1 = make_user(db_session, t1, email="inv703a@test.pe")
    u2 = make_user(db_session, t2, email="inv703b@test.pe")
    p1, p2 = make_producto(db_session, t1, "703A"), make_producto(db_session, t2, "703B")
    w1, w2 = _activate(db_session, t1), _activate(db_session, t2)
    _inventory_product(db_session, t1, p1, w1, u1)
    _inventory_product(db_session, t2, p2, w2, u2)

    assert inventory_service.count_movements(db_session, t1.id) == 1
    assert inventory_service.count_movements(db_session, t2.id) == 1


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


def test_inventory_filters_warehouse_status_product_and_dates(db_session):
    tenant = make_tenant(db_session, "707")
    user = make_user(db_session, tenant, email="inv-filters@test.pe")
    product = make_producto(db_session, tenant, "FILTER")
    warehouse = _activate(db_session, tenant)
    _inventory_product(db_session, tenant, product, warehouse, user, stock="5")

    page = inventory_service.list_stock_page(
        db_session, tenant.id, warehouse_id=warehouse.id, status="available", skip=0, limit=15,
    )
    assert page["total"] == 1
    assert page["items"][0]["product_id"] == product.id

    movement = db_session.query(models.InventoryMovement).filter_by(
        tenant_id=tenant.id, product_id=product.id,
    ).one()
    movement.created_at = datetime.now() - timedelta(days=2)
    db_session.commit()

    assert inventory_service.count_movements(
        db_session, tenant.id, product_id=product.id,
        date_from=datetime.now() - timedelta(days=3),
        date_to=datetime.now() - timedelta(days=1),
        direction="entry",
    ) == 1
    assert inventory_service.count_movements(
        db_session, tenant.id, date_from=datetime.now() - timedelta(hours=1),
    ) == 0


def test_warehouse_update_is_tenant_scoped_and_switches_default(db_session):
    tenant = make_tenant(db_session, "708")
    other = make_tenant(db_session, "709")
    principal = _activate(db_session, tenant)
    secondary = inventory_service.create_warehouse(
        db_session, tenant.id,
        SimpleNamespace(code="TIENDA", name="Tienda", location=None, is_default=False),
    )

    updated = inventory_service.update_warehouse(
        db_session, tenant.id, secondary.id,
        WarehouseUpdate(name="Tienda Centro", location="Av. Lima 123", is_default=True),
    )
    db_session.refresh(principal)
    assert updated.name == "Tienda Centro"
    assert updated.location == "Av. Lima 123"
    assert updated.is_default is True
    assert principal.is_default is False

    with pytest.raises(HTTPException, match="no encontrado"):
        inventory_service.update_warehouse(
            db_session, other.id, secondary.id,
            WarehouseUpdate(name="Intruso", location=None, is_default=True),
        )


def test_bulk_inventory_add_set_and_idempotency(db_session):
    tenant = make_tenant(db_session, "710")
    user = make_user(db_session, tenant, email="inv-bulk@test.pe")
    warehouse = _activate(db_session, tenant)
    first = make_producto(db_session, tenant, "BULK-A")
    second = make_producto(db_session, tenant, "BULK-B")
    _inventory_product(db_session, tenant, first, warehouse, user, stock="2")
    _inventory_product(db_session, tenant, second, warehouse, user, stock="3")

    payload = BulkInventoryAdjustmentCreate(
        warehouse_id=warehouse.id, mode="add", reason="Carga inicial del local",
        idempotency_key="bulk-test-710",
        items=[
            BulkInventoryLine(product_id=first.id, quantity=Decimal("5")),
            BulkInventoryLine(product_id=second.id, quantity=Decimal("7")),
        ],
    )
    result = inventory_service.bulk_adjust_stock(db_session, tenant.id, payload, user.id)
    repeated = inventory_service.bulk_adjust_stock(db_session, tenant.id, payload, user.id)
    assert result == repeated
    with pytest.raises(HTTPException, match="idempotencia"):
        inventory_service.bulk_adjust_stock(
            db_session, tenant.id,
            payload.model_copy(update={
                "items": [
                    BulkInventoryLine(product_id=first.id, quantity=Decimal("6")),
                    BulkInventoryLine(product_id=second.id, quantity=Decimal("7")),
                ],
            }), user.id,
        )
    stock = {row["product_id"]: row for row in inventory_service.list_stock(db_session, tenant.id)}
    assert stock[first.id]["on_hand"] == Decimal("7.0000")
    assert stock[second.id]["on_hand"] == Decimal("10.0000")

    counted = inventory_service.bulk_adjust_stock(
        db_session, tenant.id,
        BulkInventoryAdjustmentCreate(
            warehouse_id=warehouse.id, mode="set", reason="Conteo fisico de cierre",
            idempotency_key="count-test-710",
            items=[
                BulkInventoryLine(product_id=first.id, quantity=Decimal("6")),
                BulkInventoryLine(product_id=second.id, quantity=Decimal("10")),
            ],
        ), user.id,
    )
    assert counted["applied"] == 1
    assert counted["skipped"] == 1


def test_bulk_inventory_rolls_back_when_count_conflicts_with_committed(db_session):
    tenant = make_tenant(db_session, "711")
    user = make_user(db_session, tenant, email="inv-bulk-rollback@test.pe")
    warehouse = _activate(db_session, tenant)
    first = make_producto(db_session, tenant, "ROLL-A")
    second = make_producto(db_session, tenant, "ROLL-B")
    _inventory_product(db_session, tenant, first, warehouse, user, stock="5")
    _inventory_product(db_session, tenant, second, warehouse, user, stock="5")
    balance = inventory_service._balance(db_session, tenant.id, warehouse.id, second.id)
    balance.committed = Decimal("4")
    db_session.commit()

    with pytest.raises(HTTPException, match="comprometido"):
        inventory_service.bulk_adjust_stock(
            db_session, tenant.id,
            BulkInventoryAdjustmentCreate(
                warehouse_id=warehouse.id, mode="set", reason="Conteo invalido",
                idempotency_key="rollback-711",
                items=[
                    BulkInventoryLine(product_id=first.id, quantity=Decimal("8")),
                    BulkInventoryLine(product_id=second.id, quantity=Decimal("2")),
                ],
            ), user.id,
        )
    stock = {row["product_id"]: row for row in inventory_service.list_stock(db_session, tenant.id)}
    assert stock[first.id]["on_hand"] == Decimal("5.0000")
    assert stock[second.id]["on_hand"] == Decimal("5.0000")
