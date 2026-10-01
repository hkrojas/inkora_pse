from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

import models
from api_dependencies import get_current_user, get_db_tenant
from conftest import make_cliente, make_tenant, make_user
from routers import inventory, reportes
from test_inventory import _activate


def _client(db, user):
    app = FastAPI()
    app.include_router(reportes.router)
    app.include_router(inventory.router)
    app.dependency_overrides[get_current_user] = lambda: user
    def session():
        yield db
    app.dependency_overrides[get_db_tenant] = session
    return TestClient(app)


def _document(tenant, user, client, index, **kwargs):
    return models.Cotizacion(
        tenant_id=tenant.id, usuario_id=user.id, cliente_id=client.id,
        tipo_comprobante='01', document_kind='fiscal_document', estado='facturada',
        serie='PAG1', correlativo=index + 1, internal_order_number=f'ORD-PAG-{index:03}',
        fecha_emision=datetime.now(), total_venta=Decimal('118'),
        total_gravada=Decimal('100'), total_igv=Decimal('18'), moneda='PEN', **kwargs,
    )


def test_collection_pages_reach_beyond_fifty_and_counts_follow_search(db_session):
    tenant = make_tenant(db_session, 'PAGR1')
    user = make_user(db_session, tenant, email='pag-read-one@test.pe')
    client = make_cliente(db_session, tenant, 'PAGR1')
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    docs = []
    for index in range(61):
        age = 1 if index < 40 else 31 if index < 45 else 0 if index < 51 else -5
        docs.append(_document(tenant, user, client, index, fecha_vencimiento=today - timedelta(days=age)))
    db_session.add_all(docs)
    other = make_tenant(db_session, 'PAGR2')
    other_user = make_user(db_session, other, email='pag-read-other@test.pe')
    other_client = make_cliente(db_session, other, 'PAGR2')
    db_session.add(_document(other, other_user, other_client, 100, fecha_vencimiento=today - timedelta(days=90)))
    db_session.commit()
    http = _client(db_session, user)
    first = http.get('/cobranza/vencidas/page').json()
    assert first['total'] == 61 and len(first['items']) == 15
    assert first['counts'] == {'all': 61, 'vencidos': 45, 'criticos': 5, 'hoy': 6, 'proximos': 10}
    pages = [http.get(f'/cobranza/vencidas/page?skip={skip}&limit=15').json() for skip in (0, 15, 30, 45, 60)]
    ids = [item['id'] for page in pages for item in page['items']]
    assert len(ids) == len(set(ids)) == 61
    assert set(ids) == {doc.id for doc in docs}
    assert len(pages[-1]['items']) == 1
    selected = http.get('/cobranza/vencidas/page?q=ORD-PAG-060&segment=proximos').json()
    assert selected['total'] == 1 and selected['counts']['all'] == 1
    assert selected['items'][0]['id'] == docs[-1].id
    assert selected['items'][0]['saldo_pendiente'] == '118.00'
    for term in ('PAG1-000061', 'pag1-000061', '000061'):
        by_folio = http.get('/cobranza/vencidas/page', params={'q': term}).json()
        assert by_folio['total'] == 1
        assert by_folio['items'][0]['id'] == docs[-1].id
    legacy = http.get('/cobranza/vencidas?scope=active&limit=15').json()
    assert isinstance(legacy, list) and legacy == first['items']
    assert http.get('/cobranza/vencidas/page?segment=invalid').status_code == 422
    assert http.get('/cobranza/vencidas/page?skip=-1').status_code == 422
    assert http.get('/cobranza/vencidas/page?limit=101').status_code == 422


def test_return_pages_total_and_oldest_record_are_tenant_isolated(db_session):
    tenant = make_tenant(db_session, 'PAGR3')
    user = make_user(db_session, tenant, email='pag-return-one@test.pe')
    client = make_cliente(db_session, tenant, 'PAGR3')
    warehouse = _activate(db_session, tenant)
    docs = [_document(tenant, user, client, index) for index in range(37)]
    db_session.add_all(docs)
    db_session.flush()
    now = datetime.now()
    returns = [models.InventoryReturn(tenant_id=tenant.id, credit_note_id=doc.id,
        warehouse_id=warehouse.id, created_at=now - timedelta(days=index)) for index, doc in enumerate(docs)]
    db_session.add_all(returns)
    other = make_tenant(db_session, 'PAGR4')
    other_user = make_user(db_session, other, email='pag-return-other@test.pe')
    other_client = make_cliente(db_session, other, 'PAGR4')
    other_warehouse = _activate(db_session, other)
    other_doc = _document(other, other_user, other_client, 100)
    db_session.add(other_doc)
    db_session.flush()
    db_session.add(models.InventoryReturn(tenant_id=other.id, credit_note_id=other_doc.id, warehouse_id=other_warehouse.id))
    db_session.commit()
    http = _client(db_session, user)
    pages = [http.get(f'/inventario/devoluciones/page?skip={skip}&limit=15').json() for skip in (0, 15, 30)]
    assert [len(page['items']) for page in pages] == [15, 15, 7]
    assert all(page['total'] == 37 for page in pages)
    ids = [item['id'] for page in pages for item in page['items']]
    assert ids == [row.id for row in returns]
    assert len(set(ids)) == 37
    assert http.get('/inventario/devoluciones?skip=30&limit=15').json() == pages[-1]['items']
    assert http.get('/inventario/devoluciones/page?skip=45').json()['items'] == []
    assert http.get('/inventario/devoluciones/page?skip=-1').status_code == 422
    assert http.get('/inventario/devoluciones/page?limit=0').status_code == 422
