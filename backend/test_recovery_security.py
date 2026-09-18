from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

import crud
import models
import schemas
from conftest import make_tenant, make_user
from routers import superadmin
from services import inventory_service
from test_smartpse_superadmin import _client_for_user


def test_smartpse_sync_rejects_other_ruc(db_session):
    tenant = make_tenant(db_session, 'REC01')
    tenant.smartpse_company_id = '88'
    db_session.commit()
    client = MagicMock()
    client.get_company.return_value = {'id': 88, 'ruc': '20999999999'}
    with pytest.raises(HTTPException) as caught:
        superadmin._find_smartpse_company_for_tenant(client, tenant)
    assert caught.value.status_code == 409


def test_smartpse_sync_never_takes_first_fuzzy_result(db_session):
    tenant = make_tenant(db_session, 'REC02')
    client = MagicMock()
    client.list_companies.return_value = {'data': [{'id': 88, 'ruc': '20999999999'}]}
    with pytest.raises(HTTPException):
        superadmin._find_smartpse_company_for_tenant(client, tenant)


def test_tenant_cannot_administer_smartpse(db_session):
    tenant = make_tenant(db_session, 'REC03')
    user = make_user(db_session, tenant, email='rec03@example.test')
    client = _client_for_user(db_session, user)
    with patch('routers.superadmin.smartpse_client.get_default_client') as provider:
        result = client.post(f'/superadmin/tenants/{tenant.id}/smartpse/sync')
    assert result.status_code == 403
    provider.assert_not_called()


def test_product_opening_stock_is_persisted_atomically(db_session):
    tenant = make_tenant(db_session, 'REC04')
    product = crud.create_producto(db_session, schemas.ProductoCreate(
        nombre='Producto recuperado', precio_unitario=Decimal('0.0350'),
        inventario_inicial=schemas.ProductoInventarioInicial(opening_stock='12.3456', minimum_stock='2.5000'),
    ), tenant.id)
    stock = inventory_service.list_stock(db_session, tenant.id)
    assert stock[0]['product_id'] == product.id
    assert stock[0]['on_hand'] == Decimal('12.3456')
    assert product.precio_unitario == Decimal('0.0350')
    assert db_session.query(models.InventoryMovement).filter_by(product_id=product.id).count() == 1


def test_product_opening_stock_rejects_foreign_warehouse(db_session):
    tenant = make_tenant(db_session, 'REC05')
    other = make_tenant(db_session, 'REC06')
    foreign = models.Warehouse(tenant_id=other.id, code='OTHER', name='Other', is_active=True)
    db_session.add(foreign)
    db_session.commit()
    with pytest.raises(HTTPException):
        crud.create_producto(db_session, schemas.ProductoCreate(
            nombre='No debe persistir', precio_unitario=1,
            inventario_inicial=schemas.ProductoInventarioInicial(warehouse_id=foreign.id, opening_stock=10),
        ), tenant.id)
    assert db_session.query(models.Producto).filter_by(tenant_id=tenant.id).count() == 0
