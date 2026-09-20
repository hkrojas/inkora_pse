from decimal import Decimal

import pytest
from pydantic import ValidationError

import crud
import schemas
from conftest import make_cliente, make_tenant, make_user
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


def test_create_producto_inafecto_no_calcula_igv(db_session):
    tenant = make_tenant(db_session, "PR02B")

    producto = crud.create_producto(
        db_session,
        schemas.ProductoCreate(
            nombre="Producto inafecto",
            precio_unitario=Decimal("100.00"),
            precio_incluye_igv=True,
            tipo_afectacion_igv="30",
        ),
        tenant.id,
    )

    assert producto.precio_unitario == Decimal("100.00")
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


def test_create_producto_persist_moneda(db_session):
    tenant = make_tenant(db_session, "PR04")

    producto = crud.create_producto(
        db_session,
        schemas.ProductoCreate(
            nombre="Producto en dolares",
            moneda="USD",
            precio_unitario=Decimal("50.00"),
            precio_incluye_igv=True,
        ),
        tenant.id,
    )

    assert producto.moneda == "USD"


def test_parse_productos_acepta_columna_precio_incluye_igv(db_session):
    raw = (
        "nombre,precio_unitario,moneda,precio_incluye_igv,codigo_interno\n"
        "Servicio de diseño,100.00,USD,false,DIS-001\n"
    ).encode("utf-8")

    validas, errores = parse_productos("csv", raw)

    assert errores == []
    assert len(validas) == 1
    assert validas[0].precio_unitario == Decimal("100.00")
    assert validas[0].moneda == "USD"
    assert validas[0].precio_incluye_igv is False


def test_producto_create_normaliza_campos_comerciales():
    producto = schemas.ProductoCreate(
        nombre="  Impresion laser  ",
        codigo_interno=" imp-laser ",
        moneda="usd",
        unidad_medida="niu",
        tipo_afectacion_igv="10",
        precio_unitario=Decimal("12.00"),
    )

    assert producto.nombre == "Impresion laser"
    assert producto.codigo_interno == "IMP-LASER"
    assert producto.moneda == "USD"
    assert producto.unidad_medida == "NIU"


def test_producto_create_normaliza_millar_sunat():
    producto = schemas.ProductoCreate(
        nombre="Volante por millar",
        codigo_interno="vol-1m",
        unidad_medida="mil",
        precio_unitario=Decimal("120.00"),
    )

    assert producto.codigo_interno == "VOL-1M"
    assert producto.unidad_medida == "MLL"


def test_producto_create_rechaza_unidad_no_sunat():
    with pytest.raises(ValidationError, match="Catalogo SUNAT 03"):
        schemas.ProductoCreate(
            nombre="Unidad invalida",
            unidad_medida="BAD",
            precio_unitario=Decimal("10.00"),
        )


def test_producto_create_rechaza_codigo_interno_largo():
    with pytest.raises(ValidationError):
        schemas.ProductoCreate(
            nombre="Codigo largo",
            codigo_interno="X" * 31,
            precio_unitario=Decimal("10.00"),
        )


def test_delete_producto_usado_en_cotizacion_no_borra_historial(db_session):
    tenant = make_tenant(db_session, "PR05")
    user = make_user(db_session, tenant, email="producto-pr05@test.com")
    cliente = make_cliente(db_session, tenant, "PR05")
    producto = crud.create_producto(
        db_session,
        schemas.ProductoCreate(
            nombre="Producto usado",
            precio_unitario=Decimal("118.00"),
            precio_incluye_igv=True,
        ),
        tenant.id,
    )

    crud.create_cotizacion(
        db_session,
        schemas.CotizacionCreate(
            cliente_id=cliente.id,
            moneda="PEN",
            tipo_comprobante="00",
            items=[
                schemas.CotizacionItemCreate(
                    producto_id=producto.id,
                    descripcion=producto.nombre,
                    cantidad=Decimal("1"),
                    precio_unitario=Decimal("118.00"),
                )
            ],
        ),
        user.id,
        tenant.id,
    )

    with pytest.raises(crud.ProductoEnUsoError):
        crud.delete_producto(db_session, producto.id, tenant.id)

    assert crud.get_producto_for_tenant(db_session, producto.id, tenant.id) is not None
