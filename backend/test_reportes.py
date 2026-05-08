"""
test_reportes.py — Cobranza y reporte mensual del launch scope
==============================================================
"""
import os
import sys
from io import BytesIO
from datetime import datetime, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event

import crud
import models
import schemas
from api_dependencies import get_current_user, get_db_tenant
from conftest import make_tenant, make_user, make_cliente, make_quote_via_crud
from routers import reportes
from services.document_flow_service import (
    DOCUMENT_KIND_CREDIT_NOTE,
    DOCUMENT_KIND_DEBIT_NOTE,
    DOCUMENT_STATUS_ISSUED,
    DOCUMENT_STATUS_VOIDED,
)

openpyxl = pytest.importorskip("openpyxl")


def _make_report_doc(
    db_session,
    tenant,
    user,
    cliente,
    *,
    document_kind: str,
    tipo_comprobante: str,
    serie: str,
    correlativo: int,
    total_gravada: str,
    total_exonerada: str,
    total_inafecta: str,
    total_igv: str,
    total_venta: str,
    fecha_emision: datetime,
) -> models.Cotizacion:
    doc = models.Cotizacion(
        tenant_id=tenant.id,
        cliente_id=cliente.id,
        usuario_id=user.id,
        serie=serie,
        correlativo=correlativo,
        fecha_emision=fecha_emision,
        moneda="PEN",
        tipo_comprobante=tipo_comprobante,
        estado="facturada",
        document_kind=document_kind,
        total_gravada=Decimal(total_gravada),
        total_exonerada=Decimal(total_exonerada),
        total_inafecta=Decimal(total_inafecta),
        total_igv=Decimal(total_igv),
        total_venta=Decimal(total_venta),
        monto_pagado=Decimal("0.00"),
        saldo_pendiente=Decimal(total_venta),
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


def _issue_fiscal_from_quote(
    db_session,
    quote,
    user,
    *,
    fecha_vencimiento: datetime | None = None,
):
    fiscal = crud.create_fiscal_document_from_quote(
        db_session,
        quote,
        user.id,
        "01",
    )
    fiscal.estado = DOCUMENT_STATUS_ISSUED
    fiscal.fecha_vencimiento = fecha_vencimiento
    db_session.commit()
    db_session.refresh(fiscal)
    return fiscal


def _make_collection_note(
    db_session,
    fiscal_document,
    user,
    *,
    document_kind: str,
    tipo_comprobante: str,
    total: str,
    serie: str,
    correlativo: int,
    estado: str = DOCUMENT_STATUS_ISSUED,
):
    note = models.Cotizacion(
        tenant_id=fiscal_document.tenant_id,
        cliente_id=fiscal_document.cliente_id,
        usuario_id=user.id,
        serie=serie,
        correlativo=correlativo,
        fecha_emision=datetime.now().replace(microsecond=0),
        moneda=fiscal_document.moneda,
        document_kind=document_kind,
        tipo_comprobante=tipo_comprobante,
        estado=estado,
        source_quote_id=fiscal_document.source_quote_id,
        nota_referencia_id=fiscal_document.id,
        total_gravada=Decimal(total),
        total_exonerada=Decimal("0.00"),
        total_inafecta=Decimal("0.00"),
        total_igv=Decimal("0.00"),
        total_venta=Decimal(total),
        monto_pagado=Decimal("0.00"),
        saldo_pendiente=Decimal(total),
    )
    db_session.add(note)
    db_session.commit()
    db_session.refresh(note)
    return note


def _download_report_workbook(db_session, user, *, anio: int, mes: int):
    app = FastAPI()
    app.include_router(reportes.router)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_tenant] = override_db
    app.dependency_overrides[get_current_user] = lambda: user

    response = TestClient(app).get(f"/reporte/mensual?anio={anio}&mes={mes}")
    assert response.status_code == 200
    return openpyxl.load_workbook(BytesIO(response.content), data_only=True)


def _row_for_series(ws, serie: str) -> dict:
    headers = [ws.cell(row=4, column=i).value for i in range(1, ws.max_column + 1)]
    for row in ws.iter_rows(min_row=5, values_only=True):
        if row[1] == serie:
            return dict(zip(headers, row))
    raise AssertionError(f"No se encontro la serie {serie} en el reporte mensual.")


class _SelectCapture:
    def __init__(self, db_session):
        self.engine = db_session.get_bind()
        self.statements = []

    def _before_cursor_execute(
        self,
        conn,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ):
        if statement.lstrip().lower().startswith("select"):
            self.statements.append(statement)

    def __enter__(self):
        event.listen(self.engine, "before_cursor_execute", self._before_cursor_execute)
        return self

    def __exit__(self, exc_type, exc, tb):
        event.remove(self.engine, "before_cursor_execute", self._before_cursor_execute)


def test_cobranza_resumen_documentos_pagados_mes_filtra_por_mes_actual(db_session):
    tenant = make_tenant(db_session, "REP01")
    user = make_user(db_session, tenant, email="rep01@test.com")
    cliente = make_cliente(db_session, tenant, "REP01")

    quote_paid_this_month = make_quote_via_crud(
        db_session, tenant, user, cliente, precio="118.00"
    )
    quote_paid_last_month = make_quote_via_crud(
        db_session, tenant, user, cliente, precio="118.00"
    )

    now = datetime.now().replace(microsecond=0)
    last_month = (now.replace(day=1) - timedelta(days=1)).replace(hour=10, minute=0)
    _issue_fiscal_from_quote(db_session, quote_paid_this_month, user)
    _issue_fiscal_from_quote(db_session, quote_paid_last_month, user)

    crud.registrar_pago(
        db_session,
        quote_paid_this_month.id,
        schemas.PagoCreate(
            monto_pagado=Decimal("118.00"),
            metodo_pago="Transferencia",
            fecha_pago=now,
            tipo="pago",
        ),
        tenant.id,
    )
    crud.registrar_pago(
        db_session,
        quote_paid_last_month.id,
        schemas.PagoCreate(
            monto_pagado=Decimal("118.00"),
            metodo_pago="Transferencia",
            fecha_pago=last_month,
            tipo="pago",
        ),
        tenant.id,
    )

    resumen = crud.get_cobranza_resumen(db_session, tenant.id)

    assert resumen["documentos_pagados_mes"] == 1


def test_cobranza_resumen_usa_agregaciones_sql_acotadas(db_session):
    tenant = make_tenant(db_session, "REPQ1")
    user = make_user(db_session, tenant, email="repq1@test.com")
    cliente = make_cliente(db_session, tenant, "REPQ1")
    now = datetime.now().replace(microsecond=0)

    for idx in range(8):
        quote = make_quote_via_crud(
            db_session,
            tenant,
            user,
            cliente,
            precio="100.00",
        )
        fiscal = _issue_fiscal_from_quote(
            db_session,
            quote,
            user,
            fecha_vencimiento=now - timedelta(days=idx + 1),
        )
        if idx % 3 == 0:
            crud.registrar_pago(
                db_session,
                quote.id,
                schemas.PagoCreate(
                    monto_pagado=Decimal("25.00"),
                    metodo_pago="Transferencia",
                    tipo="pago",
                ),
                tenant.id,
            )
        if idx == 1:
            _make_collection_note(
                db_session,
                fiscal,
                user,
                document_kind=DOCUMENT_KIND_CREDIT_NOTE,
                tipo_comprobante="07",
                total="10.00",
                serie="NCQ1",
                correlativo=1,
            )

    with _SelectCapture(db_session) as capture:
        resumen = crud.get_cobranza_resumen(db_session, tenant.id)

    assert resumen["documentos_vencidos"] == 8
    assert resumen["total_por_cobrar"] == Decimal("715.00")
    assert len(capture.statements) <= 3


def test_cobranza_resumen_usa_saldo_fiscal_neto_factura_nc_nd_pagos(db_session):
    tenant = make_tenant(db_session, "REP02")
    user = make_user(db_session, tenant, email="rep02@test.com")
    cliente = make_cliente(db_session, tenant, "REP02")
    vencida = datetime.now().replace(microsecond=0) - timedelta(days=5)
    quote = make_quote_via_crud(db_session, tenant, user, cliente, precio="500.00")
    fiscal = _issue_fiscal_from_quote(
        db_session,
        quote,
        user,
        fecha_vencimiento=vencida,
    )
    _make_collection_note(
        db_session,
        fiscal,
        user,
        document_kind=DOCUMENT_KIND_CREDIT_NOTE,
        tipo_comprobante="07",
        total="100.00",
        serie="NC02",
        correlativo=1,
    )
    _make_collection_note(
        db_session,
        fiscal,
        user,
        document_kind=DOCUMENT_KIND_DEBIT_NOTE,
        tipo_comprobante="08",
        total="50.00",
        serie="ND02",
        correlativo=1,
    )
    crud.registrar_pago(
        db_session,
        quote.id,
        schemas.PagoCreate(
            monto_pagado=Decimal("200.00"),
            metodo_pago="Transferencia",
            tipo="pago",
        ),
        tenant.id,
    )

    resumen = crud.get_cobranza_resumen(db_session, tenant.id)

    assert resumen["total_por_cobrar"] == Decimal("250.00")
    assert resumen["total_vencido"] == Decimal("250.00")
    assert resumen["documentos_vencidos"] == 1
    assert resumen["clientes_con_deuda"] == 1


def test_cobranza_vencida_lista_saldo_fiscal_neto_con_notas_y_pagos(db_session):
    tenant = make_tenant(db_session, "REP03")
    user = make_user(db_session, tenant, email="rep03@test.com")
    cliente = make_cliente(db_session, tenant, "REP03")
    vencida = datetime.now().replace(microsecond=0) - timedelta(days=3)
    quote = make_quote_via_crud(db_session, tenant, user, cliente, precio="500.00")
    fiscal = _issue_fiscal_from_quote(
        db_session,
        quote,
        user,
        fecha_vencimiento=vencida,
    )
    _make_collection_note(
        db_session,
        fiscal,
        user,
        document_kind=DOCUMENT_KIND_CREDIT_NOTE,
        tipo_comprobante="07",
        total="100.00",
        serie="NC03",
        correlativo=1,
    )
    _make_collection_note(
        db_session,
        fiscal,
        user,
        document_kind=DOCUMENT_KIND_DEBIT_NOTE,
        tipo_comprobante="08",
        total="50.00",
        serie="ND03",
        correlativo=1,
    )
    crud.registrar_pago(
        db_session,
        quote.id,
        schemas.PagoCreate(
            monto_pagado=Decimal("200.00"),
            metodo_pago="Transferencia",
            tipo="pago",
        ),
        tenant.id,
    )

    vencidas = crud.get_cobranza_vencida(
        db_session,
        tenant.id,
        scope="overdue",
    )

    assert len(vencidas) == 1
    row = vencidas[0]
    assert row.id == fiscal.id
    assert row.document_kind == "fiscal_document"
    assert row.total_venta == Decimal("450.00")
    assert row.monto_pagado == Decimal("200.00")
    assert row.saldo_pendiente == Decimal("250.00")


def test_cobranza_vencida_pagina_en_sql_con_consultas_acotadas(db_session):
    tenant = make_tenant(db_session, "REPQ2")
    user = make_user(db_session, tenant, email="repq2@test.com")
    cliente = make_cliente(db_session, tenant, "REPQ2")
    now = datetime.now().replace(microsecond=0)
    fiscales = []

    for idx in range(10):
        quote = make_quote_via_crud(
            db_session,
            tenant,
            user,
            cliente,
            precio="100.00",
        )
        fiscal = _issue_fiscal_from_quote(
            db_session,
            quote,
            user,
            fecha_vencimiento=now - timedelta(days=10 - idx),
        )
        fiscales.append(fiscal)

    expected = [
        fiscal.id
        for fiscal in sorted(fiscales, key=lambda item: item.fecha_vencimiento)[2:5]
    ]

    with _SelectCapture(db_session) as capture:
        rows = crud.get_cobranza_vencida(
            db_session,
            tenant.id,
            skip=2,
            limit=3,
            scope="overdue",
        )

    assert [row.id for row in rows] == expected
    assert len(rows) == 3
    assert len(capture.statements) <= 3


def test_cobranza_excluye_anulados_cotizaciones_y_no_aplica_nota_rechazada(db_session):
    tenant = make_tenant(db_session, "REP04")
    user = make_user(db_session, tenant, email="rep04@test.com")
    cliente = make_cliente(db_session, tenant, "REP04")
    vencida = datetime.now().replace(microsecond=0) - timedelta(days=2)

    quote_sin_fiscal = make_quote_via_crud(
        db_session,
        tenant,
        user,
        cliente,
        precio="900.00",
    )
    quote_sin_fiscal.fecha_vencimiento = vencida
    quote_anulada = make_quote_via_crud(
        db_session,
        tenant,
        user,
        cliente,
        precio="300.00",
    )
    fiscal_anulado = _issue_fiscal_from_quote(
        db_session,
        quote_anulada,
        user,
        fecha_vencimiento=vencida,
    )
    fiscal_anulado.estado = DOCUMENT_STATUS_VOIDED

    quote_activa = make_quote_via_crud(
        db_session,
        tenant,
        user,
        cliente,
        precio="300.00",
    )
    fiscal_activo = _issue_fiscal_from_quote(
        db_session,
        quote_activa,
        user,
        fecha_vencimiento=vencida,
    )
    _make_collection_note(
        db_session,
        fiscal_activo,
        user,
        document_kind=DOCUMENT_KIND_CREDIT_NOTE,
        tipo_comprobante="07",
        total="200.00",
        serie="NC04",
        correlativo=1,
        estado="rechazada",
    )
    db_session.commit()

    vencidas = crud.get_cobranza_vencida(
        db_session,
        tenant.id,
        scope="overdue",
    )
    resumen = crud.get_cobranza_resumen(db_session, tenant.id)

    assert [row.id for row in vencidas] == [fiscal_activo.id]
    assert vencidas[0].saldo_pendiente == Decimal("300.00")
    assert resumen["total_por_cobrar"] == Decimal("300.00")
    assert resumen["documentos_vencidos"] == 1


def test_adelanto_pre_fiscal_no_aparece_como_factura_vencida(db_session):
    tenant = make_tenant(db_session, "REP05")
    user = make_user(db_session, tenant, email="rep05@test.com")
    cliente = make_cliente(db_session, tenant, "REP05")
    quote = make_quote_via_crud(db_session, tenant, user, cliente, precio="500.00")
    quote.fecha_vencimiento = datetime.now().replace(microsecond=0) - timedelta(days=10)
    db_session.commit()

    crud.registrar_pago(
        db_session,
        quote.id,
        schemas.PagoCreate(
            monto_pagado=Decimal("100.00"),
            metodo_pago="Yape",
            tipo="adelanto",
        ),
        tenant.id,
    )

    resumen = crud.get_cobranza_resumen(db_session, tenant.id)
    vencidas = crud.get_cobranza_vencida(
        db_session,
        tenant.id,
        scope="overdue",
    )

    assert resumen["total_por_cobrar"] == Decimal("0.00")
    assert resumen["total_pagado_mes"] == Decimal("0.00")
    assert resumen["documentos_vencidos"] == 0
    assert vencidas == []


def test_dashboard_no_cuenta_cotizacion_sin_fiscal_aceptado_como_saldo_vencido(db_session):
    tenant = make_tenant(db_session, "REP06")
    user = make_user(db_session, tenant, email="rep06@test.com")
    cliente = make_cliente(db_session, tenant, "REP06")
    quote = make_quote_via_crud(db_session, tenant, user, cliente, precio="800.00")
    quote.fecha_vencimiento = datetime.now().replace(microsecond=0) - timedelta(days=7)
    db_session.commit()

    stats = crud.get_dashboard_stats(db_session, tenant.id)

    assert stats["saldos_por_cobrar"] == Decimal("0.00")
    assert stats["saldo_vencido"] == Decimal("0.00")
    assert stats["documentos_vencidos"] == 0


def test_dashboard_refleja_saldo_fiscal_neto_con_nc_nd_y_pagos(db_session):
    tenant = make_tenant(db_session, "REP07")
    user = make_user(db_session, tenant, email="rep07@test.com")
    cliente = make_cliente(db_session, tenant, "REP07")
    quote = make_quote_via_crud(db_session, tenant, user, cliente, precio="500.00")
    fiscal = _issue_fiscal_from_quote(
        db_session,
        quote,
        user,
        fecha_vencimiento=datetime.now().replace(microsecond=0) - timedelta(days=4),
    )
    _make_collection_note(
        db_session,
        fiscal,
        user,
        document_kind=DOCUMENT_KIND_CREDIT_NOTE,
        tipo_comprobante="07",
        total="100.00",
        serie="NC07",
        correlativo=1,
    )
    _make_collection_note(
        db_session,
        fiscal,
        user,
        document_kind=DOCUMENT_KIND_DEBIT_NOTE,
        tipo_comprobante="08",
        total="50.00",
        serie="ND07",
        correlativo=1,
    )
    crud.registrar_pago(
        db_session,
        quote.id,
        schemas.PagoCreate(
            monto_pagado=Decimal("200.00"),
            metodo_pago="Transferencia",
            tipo="pago",
        ),
        tenant.id,
    )

    stats = crud.get_dashboard_stats(db_session, tenant.id)

    assert stats["saldos_por_cobrar"] == Decimal("250.00")
    assert stats["saldo_vencido"] == Decimal("250.00")
    assert stats["documentos_vencidos"] == 1


def test_dashboard_no_muestra_saldo_de_fiscal_anulado(db_session):
    tenant = make_tenant(db_session, "REP08")
    user = make_user(db_session, tenant, email="rep08@test.com")
    cliente = make_cliente(db_session, tenant, "REP08")
    quote = make_quote_via_crud(db_session, tenant, user, cliente, precio="300.00")
    fiscal = _issue_fiscal_from_quote(
        db_session,
        quote,
        user,
        fecha_vencimiento=datetime.now().replace(microsecond=0) - timedelta(days=2),
    )
    fiscal.estado = DOCUMENT_STATUS_VOIDED
    db_session.commit()

    stats = crud.get_dashboard_stats(db_session, tenant.id)

    assert stats["saldos_por_cobrar"] == Decimal("0.00")
    assert stats["saldo_vencido"] == Decimal("0.00")
    assert stats["documentos_vencidos"] == 0


def test_adelanto_con_fiscal_pendiente_no_contamina_cobranza_dashboard_ni_excel(db_session):
    tenant = make_tenant(db_session, "REP09")
    user = make_user(db_session, tenant, email="rep09@test.com")
    cliente = make_cliente(db_session, tenant, "REP09")
    quote = make_quote_via_crud(db_session, tenant, user, cliente, precio="500.00")
    fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
    fiscal.serie = "F909"
    fiscal.correlativo = 1
    fiscal.fecha_emision = datetime(2026, 4, 15, 10, 0, 0)
    fiscal.fecha_vencimiento = datetime.now().replace(microsecond=0) - timedelta(days=5)
    db_session.commit()

    pago = crud.registrar_pago(
        db_session,
        fiscal.id,
        schemas.PagoCreate(
            monto_pagado=Decimal("100.00"),
            metodo_pago="Yape",
            fecha_pago=datetime(2026, 4, 16, 10, 0, 0),
            tipo="pago",
        ),
        tenant.id,
    )

    resumen = crud.get_cobranza_resumen(db_session, tenant.id)
    vencidas = crud.get_cobranza_vencida(db_session, tenant.id, scope="overdue")
    stats = crud.get_dashboard_stats(db_session, tenant.id)
    wb = _download_report_workbook(db_session, user, anio=2026, mes=4)

    assert pago.tipo == "adelanto"
    assert pago.fiscal_document_id is None
    assert resumen["total_pagado_mes"] == Decimal("0.00")
    assert resumen["total_por_cobrar"] == Decimal("0.00")
    assert vencidas == []
    assert stats["saldos_por_cobrar"] == Decimal("0.00")
    assert stats["saldo_vencido"] == Decimal("0.00")
    with pytest.raises(AssertionError):
        _row_for_series(wb.active, "F909")


def test_reporte_mensual_excel_factura_con_nc_y_pago_muestra_saldo_neto(db_session):
    tenant = make_tenant(db_session, "REP12")
    user = make_user(db_session, tenant, email="rep12@test.com")
    cliente = make_cliente(db_session, tenant, "REP12")
    fecha = datetime(2026, 4, 15, 10, 0, 0)
    quote = make_quote_via_crud(db_session, tenant, user, cliente, precio="500.00")
    fiscal = _issue_fiscal_from_quote(db_session, quote, user)
    fiscal.fecha_emision = fecha
    fiscal.serie = "F912"
    fiscal.correlativo = 1

    credit_note = _make_collection_note(
        db_session,
        fiscal,
        user,
        document_kind=DOCUMENT_KIND_CREDIT_NOTE,
        tipo_comprobante="07",
        total="100.00",
        serie="NC12",
        correlativo=1,
    )
    credit_note.fecha_emision = fecha
    db_session.commit()

    crud.registrar_pago(
        db_session,
        quote.id,
        schemas.PagoCreate(
            monto_pagado=Decimal("200.00"),
            metodo_pago="Transferencia",
            fecha_pago=datetime(2026, 4, 16, 10, 0, 0),
            tipo="pago",
        ),
        tenant.id,
    )

    wb = _download_report_workbook(db_session, user, anio=2026, mes=4)
    fiscal_row = _row_for_series(wb.active, "F912")
    credit_row = _row_for_series(wb.active, "NC12")

    assert Decimal(str(fiscal_row["Monto Pagado"])) == Decimal("200.00")
    assert Decimal(str(fiscal_row["Saldo Pendiente"])) == Decimal("200.00")
    assert Decimal(str(credit_row["Monto Pagado"])) == Decimal("0.00")
    assert Decimal(str(credit_row["Saldo Pendiente"])) == Decimal("0.00")
    assert credit_row["Estado Pago"] == "ajuste"


def test_reporte_mensual_excel_nota_debito_aumenta_saldo_del_documento_base(db_session):
    tenant = make_tenant(db_session, "REP13")
    user = make_user(db_session, tenant, email="rep13@test.com")
    cliente = make_cliente(db_session, tenant, "REP13")
    fecha = datetime(2026, 4, 15, 10, 0, 0)
    quote = make_quote_via_crud(db_session, tenant, user, cliente, precio="500.00")
    fiscal = _issue_fiscal_from_quote(db_session, quote, user)
    fiscal.fecha_emision = fecha
    fiscal.serie = "F913"
    fiscal.correlativo = 1

    debit_note = _make_collection_note(
        db_session,
        fiscal,
        user,
        document_kind=DOCUMENT_KIND_DEBIT_NOTE,
        tipo_comprobante="08",
        total="100.00",
        serie="ND13",
        correlativo=1,
    )
    debit_note.fecha_emision = fecha
    db_session.commit()

    wb = _download_report_workbook(db_session, user, anio=2026, mes=4)
    fiscal_row = _row_for_series(wb.active, "F913")
    debit_row = _row_for_series(wb.active, "ND13")

    assert Decimal(str(fiscal_row["Monto Pagado"])) == Decimal("0.00")
    assert Decimal(str(fiscal_row["Saldo Pendiente"])) == Decimal("600.00")
    assert Decimal(str(debit_row["Monto Pagado"])) == Decimal("0.00")
    assert Decimal(str(debit_row["Saldo Pendiente"])) == Decimal("0.00")
    assert debit_row["Estado Pago"] == "ajuste"


@pytest.mark.parametrize(
    "case",
    [
        {
            "id": "factura_exonerada_igv_cero",
            "document_kind": "fiscal_document",
            "tipo_comprobante": "01",
            "serie": "FE01",
            "total_gravada": "0.00",
            "total_exonerada": "150.00",
            "total_inafecta": "0.00",
            "total_igv": "0.00",
            "total_venta": "150.00",
            "signo": 1,
        },
        {
            "id": "factura_mixta",
            "document_kind": "fiscal_document",
            "tipo_comprobante": "01",
            "serie": "FM01",
            "total_gravada": "100.00",
            "total_exonerada": "50.00",
            "total_inafecta": "20.00",
            "total_igv": "18.00",
            "total_venta": "188.00",
            "signo": 1,
        },
        {
            "id": "nota_credito_resta",
            "document_kind": "credit_note",
            "tipo_comprobante": "07",
            "serie": "NC01",
            "total_gravada": "100.00",
            "total_exonerada": "0.00",
            "total_inafecta": "0.00",
            "total_igv": "18.00",
            "total_venta": "118.00",
            "signo": -1,
        },
        {
            "id": "nota_debito_suma",
            "document_kind": "debit_note",
            "tipo_comprobante": "08",
            "serie": "ND01",
            "total_gravada": "100.00",
            "total_exonerada": "0.00",
            "total_inafecta": "0.00",
            "total_igv": "18.00",
            "total_venta": "118.00",
            "signo": 1,
        },
    ],
    ids=lambda case: case["id"],
)
def test_reporte_mensual_excel_usa_totales_persistidos_y_signo_fiscal(db_session, case):
    tenant = make_tenant(db_session, f"R{case['serie']}")
    user = make_user(db_session, tenant, email=f"{case['serie'].lower()}@test.com")
    cliente = make_cliente(db_session, tenant, f"R{case['serie']}")
    fecha = datetime(2026, 4, 15, 10, 0, 0)

    _make_report_doc(
        db_session,
        tenant,
        user,
        cliente,
        document_kind=case["document_kind"],
        tipo_comprobante=case["tipo_comprobante"],
        serie=case["serie"],
        correlativo=1,
        total_gravada=case["total_gravada"],
        total_exonerada=case["total_exonerada"],
        total_inafecta=case["total_inafecta"],
        total_igv=case["total_igv"],
        total_venta=case["total_venta"],
        fecha_emision=fecha,
    )

    wb = _download_report_workbook(db_session, user, anio=2026, mes=4)
    row = _row_for_series(wb.active, case["serie"])
    sign = Decimal(case["signo"])

    assert row["Signo Fiscal"] == case["signo"]
    assert Decimal(str(row["Gravada"])) == Decimal(case["total_gravada"]) * sign
    assert Decimal(str(row["Exonerada"])) == Decimal(case["total_exonerada"]) * sign
    assert Decimal(str(row["Inafecta"])) == Decimal(case["total_inafecta"]) * sign
    assert Decimal(str(row["IGV"])) == Decimal(case["total_igv"]) * sign
    assert Decimal(str(row["Total"])) == Decimal(case["total_venta"]) * sign


def test_reporte_mensual_incluye_factura_y_notas_emitidas(db_session):
    tenant = make_tenant(db_session, "REP11")
    user = make_user(db_session, tenant, email="rep11@test.com")
    cliente = make_cliente(db_session, tenant, "REP11")
    quote = make_quote_via_crud(db_session, tenant, user, cliente, precio="118.00")

    fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
    fiscal.estado = "facturada"
    fiscal.fecha_emision = datetime.now().replace(microsecond=0)
    db_session.commit()

    credit_note = crud.crear_nota_credito_debito(
        db_session,
        fiscal,
        user.id,
        "credito",
        "01",
        "Nota de credito de prueba",
    )
    credit_note.estado = "facturada"
    credit_note.fecha_emision = fiscal.fecha_emision

    debit_note = crud.crear_nota_credito_debito(
        db_session,
        fiscal,
        user.id,
        "debito",
        "02",
        "Nota de debito de prueba",
    )
    debit_note.estado = "facturada"
    debit_note.fecha_emision = fiscal.fecha_emision
    db_session.commit()

    docs = crud.get_reporte_mensual(
        db_session,
        tenant.id,
        fiscal.fecha_emision.year,
        fiscal.fecha_emision.month,
    )

    assert {doc.document_kind for doc in docs} == {
        "fiscal_document",
        "credit_note",
        "debit_note",
    }
