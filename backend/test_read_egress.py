"""Read contracts and SQL budgets; no external services or fiscal emissions."""
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
import os
import uuid

import pytest
from sqlalchemy import event
from sqlalchemy.orm import joinedload

import crud
import models
import schemas
from conftest import make_tenant, make_user, make_cliente, make_quote_via_crud
from crud.guias import _build_guias_query, _tab_filter, get_guias_remision_page
from test_guias import _guia_data
from crud._cotizaciones_shared import _apply_quote_user_scope


@pytest.fixture
def db_session():
    """Same contracts on SQLite by default, or an explicitly local disposable PG schema."""
    from conftest import db_session as sqlite_session
    from database import Base
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url
    from sqlalchemy.orm import Session
    value = os.getenv("INKORA_READ_POSTGRES_URL")
    if not value:
        yield from sqlite_session.__wrapped__()
        return
    url = make_url(value)
    assert url.drivername.startswith("postgresql")
    assert url.host in {"localhost", "127.0.0.1", "::1"}
    assert (url.database or "").startswith("inkora_read_")
    schema = "read_test_" + uuid.uuid4().hex
    admin = create_engine(url)
    with admin.begin() as conn:
        conn.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        Base.metadata.create_all(engine)
        with Session(engine, expire_on_commit=False, autoflush=False) as db:
            yield db
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        admin.dispose()


@contextmanager
def statements(db):
    recorded = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            recorded.append(statement)
    event.listen(db.bind, "before_cursor_execute", capture)
    try:
        yield recorded
    finally:
        event.remove(db.bind, "before_cursor_execute", capture)


@pytest.fixture
def guide_data(db_session):
    db = db_session
    tenant = make_tenant(db, "EGR01")
    user = make_user(db, tenant, email="egress@test.com")
    client = make_cliente(db, tenant, "EGR01")
    quote = make_quote_via_crud(db, tenant, user, client)
    for index, status in enumerate(["pendiente", "pendiente_smartpse", "emitida", "anulada", "en_transito", "EMITIDA_ANULADA"]):
        guide = crud.create_guia_remision(db, _guia_data(quote.id), user.id, tenant.id)
        guide.estado = status
        guide.sunat_xml_content = "x" * 100000
        guide.provider_response = {"large": "y" * 100000}
        guide.fecha_traslado = datetime(2026, 9, 10 + index)
    db.commit()
    scope = SimpleNamespace(id=user.id, tenant_id=tenant.id, rol=user.rol, is_superadmin=False)
    db.expunge_all()
    return scope


@pytest.mark.parametrize("tab", ["all", "pending", "smartpse", "transit", "emitted", "cancelled", "voided"])
@pytest.mark.parametrize("skip,limit", [(0, 15), (5, 100), (100, 15)])
def test_guides_match_legacy_and_use_two_queries(db_session, guide_data, tab, skip, limit):
    db = db_session
    base = _build_guias_query(db, guide_data)
    old_counts = {name: _tab_filter(base, name).count() for name in
                  ["all", "pending", "smartpse", "transit", "emitted", "cancelled", "voided"]}
    old_rows = _tab_filter(base, tab).options(
        joinedload(models.GuiaRemision.cliente),
        joinedload(models.GuiaRemision.cotizacion).joinedload(models.Cotizacion.cliente),
    ).order_by(models.GuiaRemision.id.desc()).offset(skip).limit(limit).all()
    expected = [schemas.GuiaRemisionListResponse.model_validate(row).model_dump(mode="json") for row in old_rows]
    db.expunge_all()
    with statements(db) as sql:
        result = schemas.GuiaRemisionPageResponse.model_validate(
            get_guias_remision_page(db, guide_data, tab=tab, skip=skip, limit=limit)
        ).model_dump(mode="json")
    assert len(sql) == 2
    assert result["items"] == expected
    assert result["counts"] == old_counts
    assert result["counts"] == {"all": 6, "pending": 2, "smartpse": 1,
                                "transit": 1, "emitted": 2, "cancelled": 2, "voided": 2}
    assert result["total"] == old_counts[tab]
    assert all("sunat_xml_content" not in query and "provider_response" not in query for query in sql)


def test_guide_filters_and_scope(db_session, guide_data):
    db = db_session
    guide = db.query(models.GuiaRemision).filter_by(tenant_id=guide_data.tenant_id).first()
    guide.cliente_id = None  # Legacy guides derive the customer from their quotation.
    db.commit()
    assert get_guias_remision_page(db, guide_data)["items"][-1]["cliente_nombre"] == "Cliente EGR01"
    for filters in [{"q": "no-match"}, {"tipo_documento": "31"},
                    {"desde": datetime(2026, 9, 12), "hasta": datetime(2026, 9, 13)},
                    {"motivo": "01", "modalidad": "02", "estado": "pendiente"}]:
        base = _build_guias_query(db, guide_data, **filters)
        expected = [r.id for r in base.order_by(models.GuiaRemision.id.desc()).all()]
        with statements(db) as sql:
            result = get_guias_remision_page(db, guide_data, **filters)
        assert [r["id"] for r in result["items"]] == expected
        assert len(sql) == 2


def test_list_roles_and_cross_tenant_references(db_session, guide_data):
    db = db_session
    admin = guide_data
    other = make_tenant(db, "SCOPE")
    other_user = make_user(db, other, email="scope@test.com")
    foreign_client = make_cliente(db, other, "SCOPE", numero_documento="20987654321")
    foreign_quote = make_quote_via_crud(db, other, other_user, foreign_client)
    foreign_guide = crud.create_guia_remision(db, _guia_data(foreign_quote.id), other_user.id, other.id)
    own_guide = db.query(models.GuiaRemision).filter_by(tenant_id=admin.tenant_id).first()
    own_quote = db.query(models.Cotizacion).filter_by(tenant_id=admin.tenant_id).first()
    quote_id = own_quote.id
    # Even a malformed historical cross-tenant reference must not leak customer data.
    own_guide.cliente_id = foreign_client.id
    own_guide.cotizacion_id = foreign_quote.id
    own_quote.cliente_id = foreign_client.id
    foreign_fiscal = models.Cotizacion(tenant_id=other.id, usuario_id=other_user.id,
        cliente_id=foreign_client.id, source_quote_id=quote_id, serie="FX01", correlativo=1,
        document_kind="fiscal_document", estado="facturada")
    db.add(foreign_fiscal)
    db.commit()
    own_guide_id, foreign_guide_id = own_guide.id, foreign_guide.id
    db.expunge_all()
    for role, own_id, expected_guides, expected_quotes in [
        ("admin", admin.id, 6, 1), ("operador", 9999, 6, 1),
        ("vendedor", admin.id, 6, 1), ("vendedor", 9999, 0, 0),
    ]:
        scope = SimpleNamespace(id=own_id, tenant_id=admin.tenant_id, rol=role, is_superadmin=False)
        result = crud.get_cotizaciones_page(db, scope)
        assert result["total"] == expected_quotes
        if expected_quotes:
            assert result["items"][0].cliente is None
            assert result["items"][0].linked_fiscal_document_id is None
        guides = get_guias_remision_page(db, scope)
        assert guides["total"] == expected_guides
        assert foreign_guide_id not in [item["id"] for item in guides["items"]]
        for item in guides["items"]:
            if item["id"] == own_guide_id:
                assert item["cliente_nombre"] is None
                assert item["cliente_documento"] is None
        assert crud.get_cotizaciones_page(db, scope, q="20987654321")["total"] == 0
        assert get_guias_remision_page(db, scope, q="20987654321")["total"] == 0
    outsider = SimpleNamespace(id=999999, tenant_id=999999, rol="admin", is_superadmin=False)
    assert get_guias_remision_page(db, outsider)["total"] == 0


def test_monthly_excel_matches_legacy_and_has_constant_query_budget(db_session, monkeypatch):
    from decimal import Decimal
    from routers import reportes
    from test_reportes import _issue_fiscal_from_quote, _make_collection_note, _download_report_workbook
    from services.fiscal_balance_service import get_fiscal_document_balance

    db = db_session
    tenant = make_tenant(db, "REG")
    user = make_user(db, tenant, email="reg@test.com")
    client = make_cliente(db, tenant, "REG")
    scope = SimpleNamespace(id=user.id, tenant_id=tenant.id, rol=user.rol, is_superadmin=False)
    now = datetime.now()
    for i in range(8):
        quote = make_quote_via_crud(db, tenant, user, client, precio="500.00")
        fiscal = _issue_fiscal_from_quote(db, quote, user)
        fiscal.sunat_xml_content = "x" * 100000
        fiscal.sunat_qr_svg = "x" * 100000
        for kind, code, total, serie, state in [
            ("credit_note", "07", "100.00", "NCRE", "facturada"),
            ("debit_note", "08", "50.00", "NDRE", "facturada"),
            ("credit_note", "07", "200.00", "NCRX", "rechazada"),
        ]:
            note = _make_collection_note(db, fiscal, user, document_kind=kind, tipo_comprobante=code,
                total=total, serie=serie, correlativo=i+1, estado=state)
            # Balances include notes outside the exported month.
            note.fecha_emision = datetime(2020, 1, 1)
        for fiscal_id, kind, amount in [(fiscal.id, "pago", "150.00"),
                                       (None, "pago", "25.00"), (None, "adelanto", "80.00")]:
            db.add(models.Pago(tenant_id=tenant.id, cotizacion_id=quote.id, source_quote_id=quote.id,
                fiscal_document_id=fiscal_id, monto_pagado=Decimal(amount), tipo=kind, metodo_pago="Efectivo"))
        db.commit()
    db.expunge_all()
    with statements(db) as sql:
        actual = _download_report_workbook(db, scope, anio=now.year, mes=now.month)
    assert len(sql) == 2
    assert all("sunat_xml_content" not in q and "cotizacion_items" not in q and "sunat_qr_svg" not in q for q in sql)

    def old_docs(db, tenant_id, anio, mes):
        start = datetime(anio, mes, 1)
        end = datetime(anio+1, 1, 1) if mes == 12 else datetime(anio, mes+1, 1)
        return db.query(models.Cotizacion).options(joinedload(models.Cotizacion.cliente),
            joinedload(models.Cotizacion.items)).filter(models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.document_kind.in_(["fiscal_document", "credit_note", "debit_note"]),
            models.Cotizacion.estado == "facturada", models.Cotizacion.fecha_emision >= start,
            models.Cotizacion.fecha_emision < end).order_by(models.Cotizacion.fecha_emision.asc()).all()

    def old_amounts(db, tenant_id, doc):
        if doc.document_kind == "fiscal_document" and doc.tipo_comprobante in {"01", "03"}:
            balance = get_fiscal_document_balance(db, tenant_id, doc.id)
            return balance.payments_total, balance.saldo_pendiente
        if doc.document_kind in {"credit_note", "debit_note"}:
            return Decimal("0.00"), Decimal("0.00")
        return reportes._report_decimal(doc.monto_pagado), reportes._report_decimal(doc.saldo_pendiente)

    monkeypatch.setattr(crud, "get_reporte_mensual", old_docs)
    monkeypatch.setattr(reportes, "_monthly_collection_amounts", old_amounts)
    expected = _download_report_workbook(db, scope, anio=now.year, mes=now.month)
    for actual_row, expected_row in zip(actual.active, expected.active, strict=True):
        for a, e in zip(actual_row, expected_row, strict=True):
            assert (a.value, a.number_format, a.style_id) == (e.value, e.number_format, e.style_id)


def test_quotes_match_legacy_without_loading_documents(db_session):
    db = db_session
    tenant = make_tenant(db, "QEG")
    user = make_user(db, tenant, email="qeg@test.com")
    client = make_cliente(db, tenant, "QEG", numero_documento="20123456781")
    scope = SimpleNamespace(id=user.id, tenant_id=tenant.id, rol=user.rol, is_superadmin=False)
    for i, (url, content, verification, error) in enumerate([
        (None, None, None, None), ("", "", "", ""),
        ("https://example.test/file", None, "verified", None),
        (None, "x" * 100000, "verified", ""),
        ("url", "x" * 100000, "pending", None), (None, " ", None, "error"),
    ]):
        quote = make_quote_via_crud(db, tenant, user, client)
        quote.sunat_xml_url = quote.sunat_cdr_url = url
        quote.sunat_xml_content = quote.sunat_cdr_content = content
        quote.provider_verification_status = verification
        quote.sunat_error = error
        quote.fecha_emision = datetime(2026, 9, 10 + i)
        quote.monto_pagado = i * 30
        quote.provider_response = {"large": "x" * 100000}
        for j, status in enumerate(["facturada", "pendiente_confirmacion", "anulada"]):
            linked = models.Cotizacion(tenant_id=tenant.id, usuario_id=user.id, cliente_id=client.id,
                document_kind="fiscal_document", estado=status, source_quote_id=quote.id,
                serie="F001", correlativo=i * 3 + j + 1)
            db.add(linked)
            if i == 0 and j == 1:
                linked.estado = None
                linked.serie = ""
        db.commit()
    other = make_tenant(db, "QEG2")
    outsider = make_user(db, other, email="qeg2@test.com")
    other_client = make_cliente(db, other, "QEG2")
    make_quote_via_crud(db, other, outsider, other_client)
    for skip, limit in [(0, 15), (5, 100), (100, 15)]:
        db.expunge_all()
        baseline = _apply_quote_user_scope(db.query(models.Cotizacion).filter(
            models.Cotizacion.source_quote_id.is_(None)), scope).order_by(models.Cotizacion.id.desc())
        expected = [schemas.CotizacionListResponse.model_validate(row).model_dump(mode="json")
                    for row in baseline.offset(skip).limit(limit).all()]
        db.expunge_all()
        with statements(db) as sql:
            actual = [schemas.CotizacionListResponse.model_validate(row).model_dump(mode="json")
                      for row in crud.get_cotizaciones(db, scope, skip=skip, limit=limit)]
        assert actual == expected
        assert len(sql) == 1
        assert "provider_response" not in sql[0]
        with statements(db) as sql:
            page = schemas.CotizacionPageResponse.model_validate(
                crud.get_cotizaciones_page(db, scope, skip=skip, limit=limit)).model_dump(mode="json")
        assert page["items"] == expected
        assert page["total"] == 6
        assert len(sql) == 2
    for filters, total in [({"q": "no-match"}, 0), ({"q": "Cliente QEG"}, 6),
                           ({"date_from": datetime(2026, 9, 12), "date_to": datetime(2026, 9, 13)}, 2)]:
        with statements(db) as sql:
            page = crud.get_cotizaciones_page(db, scope, **filters)
        assert page["total"] == total
        assert len(sql) == 2


@pytest.mark.parametrize("count", [0, 1, 30])
def test_monthly_empty_and_tenant_balances(db_session, count):
    from decimal import Decimal
    from test_reportes import _download_report_workbook
    from services.fiscal_balance_service import get_fiscal_document_balance
    db = db_session
    tenant = make_tenant(db, "MBOUND")
    user = make_user(db, tenant, email="mbound@test.com")
    client = make_cliente(db, tenant, "MBOUND")
    other = make_tenant(db, "MOTHER")
    other_user = make_user(db, other, email="mother@test.com")
    other_client = make_cliente(db, other, "MOTHER")
    own_ids = []
    for i in range(count):
        doc = models.Cotizacion(tenant_id=tenant.id, usuario_id=user.id, cliente_id=client.id,
            serie="F001", correlativo=i+1, document_kind="fiscal_document", tipo_comprobante="01",
            estado="facturada", fecha_emision=datetime(2026, 12, 31, 23, 59, i), total_venta=Decimal("0.30"),
            monto_pagado=0, saldo_pendiente=Decimal("0.30"))
        db.add(doc)
        db.flush()
        own_ids.append(doc.id)
        for owner, amount in [(tenant, "0.10"), (other, "999.00")]:
            db.add(models.Pago(tenant_id=owner.id, cotizacion_id=doc.id, fiscal_document_id=doc.id,
                monto_pagado=Decimal(amount), tipo="pago", metodo_pago="Efectivo"))
        db.add(models.Cotizacion(tenant_id=other.id, usuario_id=other_user.id, cliente_id=other_client.id,
            serie="FC01", correlativo=i+1, document_kind="credit_note", tipo_comprobante="07",
            estado="facturada", fecha_emision=datetime(2026, 12, 1), nota_referencia_id=doc.id, total_venta=999))
    db.commit()
    scope = SimpleNamespace(id=user.id, tenant_id=tenant.id, rol=user.rol, is_superadmin=False)
    db.expunge_all()
    with statements(db) as sql:
        book = _download_report_workbook(db, scope, anio=2026, mes=12)
    assert len(sql) == 2
    assert book.active.cell(row=5+count, column=16).value == float(Decimal("0.10") * count)
    assert book.active.cell(row=5+count, column=17).value == float(Decimal("0.20") * count)
    rows = crud.get_reporte_mensual(db, scope.tenant_id, 2026, 12)
    assert [row.id for row in rows] == own_ids
    for row in rows:
        baseline = get_fiscal_document_balance(db, scope.tenant_id, row.id)
        assert row.collection_paid == baseline.payments_total == Decimal("0.10")
        assert row.collection_balance == baseline.saldo_pendiente == Decimal("0.20")
    assert crud.get_reporte_mensual(db, scope.tenant_id, 2027, 1) == []


