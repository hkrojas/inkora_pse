"""Uses the isolated quote database fixture, never a remote database."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import models
from conftest import make_tenant, make_user, make_producto
from schemas.inventory import BulkInventoryAdjustmentCreate, BulkInventoryLine
from services import inventory_service
from test_inventory import _activate, _inventory_product
from test_cotizaciones_postgres import pg_session_factory  # noqa: F401


def test_concurrent_bulk_replay_has_one_receipt_and_one_movement(pg_session_factory):
    with pg_session_factory() as db:
        tenant = make_tenant(db, 'RPGB')
        user = make_user(db, tenant, email='bulk-pg@example.test')
        product = make_producto(db, tenant, 'RPGB')
        warehouse = _activate(db, tenant)
        _inventory_product(db, tenant, product, warehouse, user, stock='10')
        tenant_id, user_id, product_id, warehouse_id = tenant.id, user.id, product.id, warehouse.id
    payload = BulkInventoryAdjustmentCreate(
        warehouse_id=warehouse_id, mode='add', reason='Prueba concurrente aislada',
        idempotency_key='recovery-postgres-duplicate',
        items=[BulkInventoryLine(product_id=product_id, quantity=5)],
    )
    barrier = Barrier(2)
    def apply():
        with pg_session_factory() as db:
            barrier.wait(timeout=10)
            return inventory_service.bulk_adjust_stock(db, tenant_id, payload, user_id)
    with ThreadPoolExecutor(max_workers=2) as pool:
        one, two = pool.submit(apply), pool.submit(apply)
        assert one.result(timeout=20) == two.result(timeout=20)
    with pg_session_factory() as db:
        assert inventory_service.list_stock(db, tenant_id)[0]['on_hand'] == 15
        assert db.query(models.AuditLog).filter_by(entity_id=tenant_id, entity_type='inventory_bulk').count() == 1
