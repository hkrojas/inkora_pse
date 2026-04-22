from decimal import Decimal

import pytest

from conftest import make_cliente, make_producto, make_tenant, make_user, make_quote_via_crud
import crud
import schemas


def test_duplicar_cotizacion_crea_copia_con_nueva_orden_y_mismos_items(db_session):
    tenant = make_tenant(db_session, "COT01")
    user = make_user(db_session, tenant, email="cot01@test.com")
    cliente = make_cliente(db_session, tenant, "COT01")
    producto = make_producto(db_session, tenant, "COT01")

    original = crud.create_cotizacion(
        db_session,
        schemas.CotizacionCreate(
            cliente_id=cliente.id,
            moneda="PEN",
            tipo_comprobante="00",
            observaciones="Duplicar esta cotizacion",
            condicion_pago="credito_15",
            items=[
                schemas.CotizacionItemCreate(
                    producto_id=producto.id,
                    descripcion="Impresion offset A4",
                    cantidad=Decimal("2"),
                    precio_unitario=Decimal("118.00"),
                    unidad_medida="NIU",
                    tipo_afectacion_igv="10",
                ),
            ],
        ),
        user.id,
        tenant.id,
    )

    copia = crud.duplicate_cotizacion(db_session, original.id, user)

    assert copia is not None
    assert copia.id != original.id
    assert copia.internal_order_number != original.internal_order_number
    assert copia.cliente_id == original.cliente_id
    assert copia.document_kind == "quotation"
    assert copia.estado == "pendiente"
    assert copia.condicion_pago == original.condicion_pago
    assert copia.observaciones == original.observaciones
    assert len(copia.items) == len(original.items)
    assert copia.items[0].producto_id == original.items[0].producto_id
    assert copia.items[0].descripcion == original.items[0].descripcion
    assert copia.items[0].cantidad == original.items[0].cantidad
    assert copia.items[0].precio_unitario == original.items[0].precio_unitario


def test_eliminar_cotizacion_permitido_si_esta_pendiente_y_sin_fiscal(db_session):
    tenant = make_tenant(db_session, "COT02")
    user = make_user(db_session, tenant, email="cot02@test.com")
    cliente = make_cliente(db_session, tenant, "COT02")
    quote = make_quote_via_crud(db_session, tenant, user, cliente)

    result = crud.delete_cotizacion(db_session, quote.id, user)

    assert result is True
    assert crud.get_cotizacion(db_session, quote.id, user) is None


def test_eliminar_cotizacion_rechaza_estado_no_pendiente(db_session):
    tenant = make_tenant(db_session, "COT03")
    user = make_user(db_session, tenant, email="cot03@test.com")
    cliente = make_cliente(db_session, tenant, "COT03")
    quote = make_quote_via_crud(db_session, tenant, user, cliente)
    quote.estado = "facturada"
    db_session.commit()

    with pytest.raises(ValueError, match="estado pendiente"):
        crud.delete_cotizacion(db_session, quote.id, user)


def test_eliminar_cotizacion_rechaza_si_tiene_documento_fiscal_vinculado(db_session):
    tenant = make_tenant(db_session, "COT04")
    user = make_user(db_session, tenant, email="cot04@test.com")
    cliente = make_cliente(db_session, tenant, "COT04")
    quote = make_quote_via_crud(db_session, tenant, user, cliente)

    crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")

    with pytest.raises(ValueError, match="comprobante fiscal asociado"):
        crud.delete_cotizacion(db_session, quote.id, user)


def test_documento_fiscal_conserva_contexto_comercial_de_la_cotizacion(db_session):
    tenant = make_tenant(db_session, "COT05")
    user = make_user(db_session, tenant, email="cot05@test.com")
    cliente = make_cliente(db_session, tenant, "COT05")
    producto = make_producto(db_session, tenant, "COT05")

    quote = crud.create_cotizacion(
        db_session,
        schemas.CotizacionCreate(
            cliente_id=cliente.id,
            moneda="PEN",
            tipo_comprobante="00",
            observaciones="Mantener observacion comercial",
            condicion_pago="credito_30",
            items=[
                schemas.CotizacionItemCreate(
                    producto_id=producto.id,
                    descripcion="Millar de volantes couche",
                    cantidad=Decimal("3"),
                    precio_unitario=Decimal("118.00"),
                    unidad_medida="NIU",
                    tipo_afectacion_igv="10",
                ),
            ],
        ),
        user.id,
        tenant.id,
    )

    fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")

    assert fiscal.document_kind == "fiscal_document"
    assert fiscal.source_quote_id == quote.id
    assert fiscal.internal_order_number == quote.internal_order_number
    assert fiscal.observaciones == quote.observaciones
    assert fiscal.condicion_pago == quote.condicion_pago
    assert len(fiscal.items) == 1
    assert fiscal.items[0].id != quote.items[0].id
    assert fiscal.items[0].descripcion == quote.items[0].descripcion
    assert fiscal.items[0].cantidad == quote.items[0].cantidad
    assert fiscal.items[0].precio_unitario == quote.items[0].precio_unitario
