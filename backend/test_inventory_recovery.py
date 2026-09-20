from decimal import Decimal
from fastapi import HTTPException
import pytest
import models
from conftest import make_tenant, make_user, make_producto
from test_inventory import _activate, _inventory_product
from schemas.inventory import BulkInventoryAdjustmentCreate, BulkInventoryLine
from services import inventory_service as service
from services.import_service import parse_inventory_stock


def test_receipt_prevents_reusing_zero_delta_count_or_different_products(db_session):
    tenant = make_tenant(db_session, '931')
    user = make_user(db_session, tenant, email='receipt@test.pe')
    warehouse = _activate(db_session, tenant)
    a = make_producto(db_session, tenant, 'R-A')
    b = make_producto(db_session, tenant, 'R-B')
    for product in (a, b):
        _inventory_product(db_session, tenant, product, warehouse, user, stock='10')
    payload = BulkInventoryAdjustmentCreate(
        warehouse_id=warehouse.id, mode='set', reason='Conteo aislado', idempotency_key='receipt-931',
        items=[BulkInventoryLine(product_id=a.id, quantity=10)],
    )
    response = service.bulk_adjust_stock(db_session, tenant.id, payload, user.id)
    assert response == {'movement_ids': [], 'applied': 0, 'skipped': 1}
    balance = service._balance(db_session, tenant.id, warehouse.id, a.id)
    balance.on_hand = Decimal('7')
    db_session.commit()
    assert service.bulk_adjust_stock(db_session, tenant.id, payload, user.id) == response
    db_session.refresh(balance)
    assert balance.on_hand == 7
    with pytest.raises(HTTPException) as caught:
        service.bulk_adjust_stock(db_session, tenant.id, payload.model_copy(update={
            'items': [BulkInventoryLine(product_id=b.id, quantity=10)],
        }), user.id)
    assert caught.value.status_code == 409
    assert db_session.query(models.AuditLog).filter_by(entity_type='inventory_bulk').count() == 1


@pytest.mark.parametrize('quantity', ['NaN', 'Infinity', '-1', '0.00001', '100000000000000'])
def test_stock_import_rejects_nonfinite_or_unrepresentable_quantity(quantity):
    rows, errors = parse_inventory_stock('csv', f'codigo,cantidad\nSKU,{quantity}\n'.encode())
    assert not rows
    assert len(errors) == 1
