from decimal import Decimal

import crud
import schemas
from conftest import make_tenant
from services.import_service import parse_productos


def test_create_producto_con_precio_ingresado_con_igv(db_session):
    tenant = make_tenant(db_session, "PR01")

    producto = crud.create_producto(
        db_session,
        schemas.ProductoCreate(
            nombre="Producto con IGV",
            precio_unitario=Decimal("118.00"),
            precio_incluye_igv=True,
        ),
        tenant.id,
    )

    assert producto.precio_unitario == Decimal("118.00")
    assert producto.valor_unitario == Decimal("100.00")


def test_create_producto_con_precio_ingresado_sin_igv(db_session):
    tenant = make_tenant(db_session, "PR02")

    producto = crud.create_producto(
        db_session,
        schemas.ProductoCreate(
            nombre="Producto sin IGV",
            precio_unitario=Decimal("100.00"),
            precio_incluye_igv=False,
        ),
        tenant.id,
    )

    assert producto.precio_unitario == Decimal("118.00")
    assert producto.valor_unitario == Decimal("100.00")


def test_update_producto_recalcula_desde_precio_base_sin_igv(db_session):
    tenant = make_tenant(db_session, "PR03")
    producto = crud.create_producto(
        db_session,
        schemas.ProductoCreate(
            nombre="Producto editable",
            precio_unitario=Decimal("118.00"),
            precio_incluye_igv=True,
        ),
        tenant.id,
    )

    actualizado = crud.update_producto(
        db_session,
        producto.id,
        schemas.ProductoCreate(
            nombre="Producto editable",
            precio_unitario=Decimal("200.00"),
            precio_incluye_igv=False,
        ),
        tenant.id,
    )

    assert actualizado is not None
    assert actualizado.precio_unitario == Decimal("236.00")
    assert actualizado.valor_unitario == Decimal("200.00")


def test_parse_productos_acepta_columna_precio_incluye_igv(db_session):
    raw = (
        "nombre,precio_unitario,precio_incluye_igv,codigo_interno\n"
        "Servicio de diseño,100.00,false,DIS-001\n"
    ).encode("utf-8")

    validas, errores = parse_productos("csv", raw)

    assert errores == []
    assert len(validas) == 1
    assert validas[0].precio_unitario == Decimal("100.00")
    assert validas[0].precio_incluye_igv is False
