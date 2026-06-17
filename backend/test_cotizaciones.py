from datetime import datetime, timedelta, timezone
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
            quote_payment_methods=[
                {
                    "tipo": "bank",
                    "banco": "BCP",
                    "tipo_cuenta": "Cta Corriente",
                    "moneda": "Soles",
                    "cuenta": "1919870450013",
                    "cci": "00219100987045001355",
                }
            ],
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
    assert copia.quote_payment_methods == original.quote_payment_methods
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


def test_actualizar_cotizacion_pendiente_recalcula_y_limpia_pdf(db_session):
    tenant = make_tenant(db_session, "COT02U")
    user = make_user(db_session, tenant, email="cot02u@test.com")
    cliente = make_cliente(db_session, tenant, "COT02U")
    quote = make_quote_via_crud(db_session, tenant, user, cliente)
    original_number = quote.document_number
    quote.sunat_pdf_url = "supabase-private://inkora-private/cotizaciones/demo.pdf"
    quote.sunat_xml_url = "legacy.xml"
    db_session.commit()

    updated = crud.update_cotizacion(
        db_session,
        quote.id,
        schemas.CotizacionUpdate(
            cliente_id=cliente.id,
            moneda="PEN",
            tipo_comprobante="00",
            observaciones="Version corregida",
            condicion_pago="contado",
            items=[
                schemas.CotizacionItemCreate(
                    descripcion="Servicio actualizado",
                    cantidad=Decimal("2"),
                    precio_unitario=Decimal("118.00"),
                    unidad_medida="NIU",
                    tipo_afectacion_igv="10",
                ),
            ],
        ),
        user,
    )

    assert updated.id == quote.id
    assert updated.document_number == original_number
    assert updated.observaciones == "Version corregida"
    assert updated.total_venta == Decimal("236.00")
    assert updated.saldo_pendiente == Decimal("236.00")
    assert len(updated.items) == 1
    assert updated.items[0].descripcion == "Servicio actualizado"
    assert updated.sunat_pdf_url is None
    assert updated.sunat_xml_url is None


def test_crear_cotizacion_persiste_snapshot_cliente_del_documento(db_session):
    tenant = make_tenant(db_session, "COTSNAP")
    user = make_user(db_session, tenant, email="cotsnap@test.com")
    cliente = make_cliente(db_session, tenant, "COTSNAP", numero_documento="20999999991")

    quote = crud.create_cotizacion(
        db_session,
        schemas.CotizacionCreate(
            cliente_id=cliente.id,
            cliente_snapshot={
                "tipo_documento": "6",
                "numero_documento": cliente.numero_documento,
                "razon_social": "Cliente editado solo para documento",
                "direccion": "Jr. Snapshot 123",
                "email": "snapshot@test.com",
                "telefono": "987654321",
                "whatsapp": "987654321",
            },
            moneda="PEN",
            tipo_comprobante="00",
            items=[
                schemas.CotizacionItemCreate(
                    descripcion="Servicio con snapshot",
                    cantidad=Decimal("1"),
                    precio_unitario=Decimal("118.00"),
                ),
            ],
        ),
        user.id,
        tenant.id,
    )

    assert quote.cliente_snapshot["razon_social"] == "Cliente editado solo para documento"
    assert quote.cliente_snapshot["direccion"] == "Jr. Snapshot 123"
    assert quote.cliente_snapshot["email"] == "snapshot@test.com"
    assert quote.cliente.razon_social == "Cliente COTSNAP"

    payload = schemas.CotizacionResponse.model_validate(
        quote,
        from_attributes=True,
    ).model_dump()
    assert payload["cliente_snapshot"]["telefono"] == "987654321"


def test_crear_cotizacion_persiste_metodos_bancarios_visibles_en_pdf(db_session):
    tenant = make_tenant(db_session, "COTBANK")
    user = make_user(db_session, tenant, email="cotbank@test.com")
    cliente = make_cliente(db_session, tenant, "COTBANK", numero_documento="20999999993")

    quote = crud.create_cotizacion(
        db_session,
        schemas.CotizacionCreate(
            cliente_id=cliente.id,
            moneda="PEN",
            tipo_comprobante="00",
            quote_payment_methods=[
                {
                    "tipo": "bank",
                    "banco": "BCP",
                    "tipo_cuenta": "Cta Corriente",
                    "moneda": "Soles",
                    "cuenta": "1919870450013",
                    "cci": "00219100987045001355",
                },
                {
                    "tipo": "bank",
                    "banco": "Banco de la Nacion",
                    "tipo_cuenta": "Cuenta Detraccion",
                    "moneda": "Soles",
                    "cuenta": "00045115666",
                    "cci": "01804500004511566655",
                },
            ],
            items=[
                schemas.CotizacionItemCreate(
                    descripcion="Servicio con bancos visibles",
                    cantidad=Decimal("1"),
                    precio_unitario=Decimal("118.00"),
                ),
            ],
        ),
        user.id,
        tenant.id,
    )

    assert [method["banco"] for method in quote.quote_payment_methods] == [
        "BCP",
        "Banco de la Nacion",
    ]

    payload = schemas.CotizacionResponse.model_validate(
        quote,
        from_attributes=True,
    ).model_dump()
    assert payload["quote_payment_methods"][0]["banco"] == "BCP"


def test_facturar_cotizacion_copia_snapshot_cliente(db_session):
    tenant = make_tenant(db_session, "COTSNAPF")
    user = make_user(db_session, tenant, email="cotsnapf@test.com")
    cliente = make_cliente(db_session, tenant, "COTSNAPF", numero_documento="20999999992")

    quote = crud.create_cotizacion(
        db_session,
        schemas.CotizacionCreate(
            cliente_id=cliente.id,
            cliente_snapshot={
                "tipo_documento": "6",
                "numero_documento": cliente.numero_documento,
                "razon_social": "Cliente fiscal congelado",
                "direccion": "Av. Fiscal Snapshot 456",
            },
            moneda="PEN",
            tipo_comprobante="00",
            items=[
                schemas.CotizacionItemCreate(
                    descripcion="Servicio facturable",
                    cantidad=Decimal("1"),
                    precio_unitario=Decimal("118.00"),
                ),
            ],
        ),
        user.id,
        tenant.id,
    )

    fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")

    assert fiscal.cliente_snapshot == quote.cliente_snapshot
    assert fiscal.cliente_snapshot["razon_social"] == "Cliente fiscal congelado"


def test_actualizar_cotizacion_rechaza_si_tiene_pagos(db_session):
    tenant = make_tenant(db_session, "COT02P")
    user = make_user(db_session, tenant, email="cot02p@test.com")
    cliente = make_cliente(db_session, tenant, "COT02P")
    quote = make_quote_via_crud(db_session, tenant, user, cliente)
    quote.monto_pagado = Decimal("10.00")
    quote.saldo_pendiente = quote.total_venta - Decimal("10.00")
    db_session.commit()

    with pytest.raises(ValueError, match="pagos asociados"):
        crud.update_cotizacion(
            db_session,
            quote.id,
            schemas.CotizacionUpdate(
                cliente_id=cliente.id,
                moneda="PEN",
                tipo_comprobante="00",
                items=[
                    schemas.CotizacionItemCreate(
                        descripcion="No debe cambiar",
                        cantidad=Decimal("1"),
                        precio_unitario=Decimal("118.00"),
                    ),
                ],
            ),
            user,
        )


def test_actualizar_cotizacion_permte_quitar_todos_los_bancos_visibles(db_session):
    tenant = make_tenant(db_session, "COT02BANK")
    user = make_user(db_session, tenant, email="cot02bank@test.com")
    cliente = make_cliente(db_session, tenant, "COT02BANK")
    quote = make_quote_via_crud(db_session, tenant, user, cliente)
    quote.quote_payment_methods = [
        {
            "tipo": "bank",
            "banco": "BCP",
            "tipo_cuenta": "Cta Corriente",
            "moneda": "Soles",
            "cuenta": "1919870450013",
            "cci": "00219100987045001355",
        }
    ]
    db_session.commit()

    updated = crud.update_cotizacion(
        db_session,
        quote.id,
        schemas.CotizacionUpdate(
            cliente_id=cliente.id,
            moneda="PEN",
            tipo_comprobante="00",
            quote_payment_methods=[],
            items=[
                schemas.CotizacionItemCreate(
                    descripcion="Documento sin bancos",
                    cantidad=Decimal("1"),
                    precio_unitario=Decimal("118.00"),
                ),
            ],
        ),
        user,
    )

    assert updated.quote_payment_methods == []


def test_actualizar_cotizacion_rechaza_si_tiene_fiscal_vinculado(db_session):
    tenant = make_tenant(db_session, "COT02F")
    user = make_user(db_session, tenant, email="cot02f@test.com")
    cliente = make_cliente(db_session, tenant, "COT02F")
    quote = make_quote_via_crud(db_session, tenant, user, cliente)
    crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")

    with pytest.raises(ValueError, match="comprobante fiscal asociado"):
        crud.update_cotizacion(
            db_session,
            quote.id,
            schemas.CotizacionUpdate(
                cliente_id=cliente.id,
                moneda="PEN",
                tipo_comprobante="00",
                items=[
                    schemas.CotizacionItemCreate(
                        descripcion="No debe cambiar",
                        cantidad=Decimal("1"),
                        precio_unitario=Decimal("118.00"),
                    ),
                ],
            ),
            user,
        )


def test_cotizacion_exonerada_no_genera_igv(db_session):
    tenant = make_tenant(db_session, "COT02B")
    user = make_user(db_session, tenant, email="cot02b@test.com")
    cliente = make_cliente(db_session, tenant, "COT02B")

    quote = crud.create_cotizacion(
        db_session,
        schemas.CotizacionCreate(
            cliente_id=cliente.id,
            moneda="PEN",
            tipo_comprobante="00",
            items=[
                schemas.CotizacionItemCreate(
                    descripcion="Servicio exonerado",
                    cantidad=Decimal("2"),
                    precio_unitario=Decimal("100.00"),
                    unidad_medida="ZZ",
                    tipo_afectacion_igv="20",
                ),
            ],
        ),
        user.id,
        tenant.id,
    )

    assert quote.total_gravada == Decimal("0.00")
    assert quote.total_exonerada == Decimal("200.00")
    assert quote.total_inafecta == Decimal("0.00")
    assert quote.total_igv == Decimal("0.00")
    assert quote.total_venta == Decimal("200.00")


def test_cotizacion_con_producto_persiste_sku_fiscal(db_session):
    tenant = make_tenant(db_session, "COT02C")
    user = make_user(db_session, tenant, email="cot02c@test.com")
    cliente = make_cliente(db_session, tenant, "COT02C")
    producto = make_producto(db_session, tenant, "COT02C")
    producto.codigo_interno = "IMP-A4-FC"
    db_session.commit()

    quote = crud.create_cotizacion(
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
                ),
            ],
        ),
        user.id,
        tenant.id,
    )

    assert quote.items[0].codigo_producto == "IMP-A4-FC"


def test_cotizacion_nueva_usa_credito_15_y_vencimiento_por_defecto(db_session):
    tenant = make_tenant(db_session, "COT02C15")
    user = make_user(db_session, tenant, email="cot02c15@test.com")
    cliente = make_cliente(db_session, tenant, "COT02C15")
    fecha_emision = datetime(2026, 6, 16, 0, 0, tzinfo=timezone.utc)

    quote = crud.create_cotizacion(
        db_session,
        schemas.CotizacionCreate(
            cliente_id=cliente.id,
            fecha_emision=fecha_emision,
            moneda="PEN",
            tipo_comprobante="00",
            items=[
                schemas.CotizacionItemCreate(
                    descripcion="Cotizacion comercial base",
                    cantidad=Decimal("1"),
                    precio_unitario=Decimal("118.00"),
                    unidad_medida="NIU",
                    tipo_afectacion_igv="10",
                ),
            ],
        ),
        user.id,
        tenant.id,
    )

    assert quote.condicion_pago == "credito_15"
    assert quote.fecha_vencimiento is not None
    assert quote.fecha_vencimiento.date() == (fecha_emision + timedelta(days=15)).date()


def test_documento_fiscal_conserva_fecha_emision_de_la_cotizacion(db_session):
    tenant = make_tenant(db_session, "COT02D")
    user = make_user(db_session, tenant, email="cot02d@test.com")
    cliente = make_cliente(db_session, tenant, "COT02D")
    fecha_emision = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)

    quote = crud.create_cotizacion(
        db_session,
        schemas.CotizacionCreate(
            cliente_id=cliente.id,
            fecha_emision=fecha_emision,
            moneda="PEN",
            tipo_comprobante="00",
            items=[
                schemas.CotizacionItemCreate(
                    descripcion="Servicio con fecha fiscal seleccionada",
                    cantidad=Decimal("1"),
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

    assert quote.fecha_emision.date() == fecha_emision.date()
    assert fiscal.fecha_emision.date() == fecha_emision.date()


def test_documento_fiscal_conserva_cuotas_pago_de_la_cotizacion(db_session):
    tenant = make_tenant(db_session, "COT02E")
    user = make_user(db_session, tenant, email="cot02e@test.com")
    cliente = make_cliente(db_session, tenant, "COT02E")
    fecha_emision = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)

    quote = crud.create_cotizacion(
        db_session,
        schemas.CotizacionCreate(
            cliente_id=cliente.id,
            fecha_emision=fecha_emision,
            fecha_vencimiento=fecha_emision + timedelta(days=30),
            moneda="PEN",
            tipo_comprobante="00",
            condicion_pago="credito_30",
            cuotas_pago=[
                schemas.CuotaPagoCreate(
                    fecha_pago=fecha_emision + timedelta(days=15),
                    monto=Decimal("59.00"),
                ),
                schemas.CuotaPagoCreate(
                    fecha_pago=fecha_emision + timedelta(days=30),
                    monto=Decimal("59.00"),
                ),
            ],
            items=[
                schemas.CotizacionItemCreate(
                    descripcion="Servicio con cuotas",
                    cantidad=Decimal("1"),
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

    assert quote.cuotas_pago[0]["monto"] == "59.00"
    assert len(fiscal.cuotas_pago) == 2
    assert fiscal.cuotas_pago[1]["monto"] == "59.00"


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


def test_cotizacion_response_tolera_usuario_historico_faltante(db_session):
    tenant = make_tenant(db_session, "COT06")
    user = make_user(db_session, tenant, email="cot06@test.com")
    cliente = make_cliente(
        db_session,
        tenant,
        "COT06",
        numero_documento="20123456789",
    )
    quote = make_quote_via_crud(db_session, tenant, user, cliente)

    quote.usuario_id = None
    db_session.commit()
    db_session.refresh(quote)

    loaded = crud.get_cotizacion(db_session, quote.id, user)
    payload = schemas.CotizacionResponse.model_validate(loaded).model_dump()

    assert payload["usuario"] is None
    assert payload["cliente"]["id"] == cliente.id


def test_cotizacion_list_response_no_carga_detalle_pesado(db_session):
    tenant = make_tenant(db_session, "COT07")
    user = make_user(db_session, tenant, email="cot07@test.com")
    cliente = make_cliente(
        db_session,
        tenant,
        "COT07",
        numero_documento="20123456780",
    )
    make_quote_via_crud(db_session, tenant, user, cliente)

    rows = crud.get_cotizaciones(db_session, user)
    db_session.expunge_all()

    payload = [
        schemas.CotizacionListResponse.model_validate(row).model_dump()
        for row in rows
    ]

    assert len(payload) == 1
    assert payload[0]["cliente"]["id"] == cliente.id
    assert "items" not in payload[0]
    assert "pagos" not in payload[0]
