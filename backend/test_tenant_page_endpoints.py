from decimal import Decimal

import models
from conftest import make_tenant, make_user
from routers import clientes as clientes_router
from routers import productos as productos_router


def _make_cliente(db, tenant, index, **overrides):
    cliente = models.Cliente(
        tenant_id=tenant.id,
        tipo_documento=overrides.pop("tipo_documento", "6"),
        numero_documento=overrides.pop("numero_documento", f"20{index:09d}"),
        razon_social=overrides.pop("razon_social", f"Cliente Paginado {index:04d}"),
        email=overrides.pop("email", f"cliente{index}@test.com"),
        telefono=overrides.pop("telefono", "999888777"),
        condicion_pago=overrides.pop("condicion_pago", "contado"),
        **overrides,
    )
    db.add(cliente)
    return cliente


def _make_producto(db, tenant, index, **overrides):
    producto = models.Producto(
        tenant_id=tenant.id,
        nombre=overrides.pop("nombre", f"Producto Paginado {index:04d}"),
        codigo_interno=overrides.pop("codigo_interno", f"SKU-{index:04d}"),
        precio_unitario=overrides.pop("precio_unitario", Decimal("118.00")),
        valor_unitario=overrides.pop("valor_unitario", Decimal("100.00")),
        unidad_medida=overrides.pop("unidad_medida", "NIU"),
        tipo_afectacion_igv=overrides.pop("tipo_afectacion_igv", "10"),
        **overrides,
    )
    db.add(producto)
    return producto


def test_clientes_page_usa_limit_offset_conteos_y_tenant(db_session):
    tenant = make_tenant(db_session, "TP01")
    other_tenant = make_tenant(db_session, "TP02")
    user = make_user(db_session, tenant, email="tenant-page@test.com")
    for index in range(1, 31):
        _make_cliente(
            db_session,
            tenant,
            index,
            tipo_documento="1" if index % 3 == 0 else "6",
            numero_documento=f"{index:08d}" if index % 3 == 0 else f"20{index:09d}",
            condicion_pago="credito_30" if index % 5 == 0 else "contado",
            email=None if index == 7 else f"cliente{index}@test.com",
        )
    _make_cliente(db_session, other_tenant, 999, razon_social="Cliente de otro tenant")
    db_session.commit()

    page = clientes_router.read_clientes_page(
        skip=15,
        limit=15,
        q=None,
        segment="all",
        db=db_session,
        current_user=user,
    )

    assert page["total"] == 30
    assert len(page["items"]) == 15
    assert page["counts"]["all"] == 30
    assert page["counts"]["credito"] == 6
    assert all(item.tenant_id == tenant.id for item in page["items"])


def test_clientes_page_busqueda_y_segmento(db_session):
    tenant = make_tenant(db_session, "TP03")
    user = make_user(db_session, tenant, email="tenant-search@test.com")
    _make_cliente(db_session, tenant, 1, razon_social="Editorial Andina", condicion_pago="credito_15")
    _make_cliente(db_session, tenant, 2, razon_social="Cliente Contado")
    db_session.commit()

    page = clientes_router.read_clientes_page(
        skip=0,
        limit=15,
        q="Andina",
        segment="credito",
        db=db_session,
        current_user=user,
    )

    assert page["total"] == 1
    assert page["items"][0].razon_social == "Editorial Andina"
    assert page["counts"]["all"] == 1
    assert page["counts"]["credito"] == 1


def test_productos_page_usa_limit_offset_conteos_y_segmentos(db_session):
    tenant = make_tenant(db_session, "TP04")
    other_tenant = make_tenant(db_session, "TP05")
    user = make_user(db_session, tenant, email="products-page@test.com")
    for index in range(1, 41):
        _make_producto(
            db_session,
            tenant,
            index,
            unidad_medida="ZZ" if index % 4 == 0 else "NIU",
            codigo_interno=None if index == 3 else f"SKU-{index:04d}",
        )
    _make_producto(db_session, other_tenant, 999)
    db_session.commit()

    page = productos_router.read_productos_page(
        skip=0,
        limit=15,
        q=None,
        segment="servicios",
        db=db_session,
        current_user=user,
    )

    assert page["total"] == 10
    assert len(page["items"]) == 10
    assert page["counts"]["all"] == 40
    assert page["counts"]["productos"] == 30
    assert page["counts"]["servicios"] == 10
    assert page["counts"]["con_sku"] == 39
    assert all(item.unidad_medida == "ZZ" for item in page["items"])

