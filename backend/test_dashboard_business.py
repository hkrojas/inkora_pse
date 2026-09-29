"""Business dashboard analytics: fiscal semantics and tenant isolation."""

import os
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import models
import fiscal_time
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event
from api_dependencies import get_current_user, get_db_tenant
from conftest import make_cliente, make_producto, make_tenant, make_user
from crud.dashboard_business import get_business_dashboard
from routers import dashboard as dashboard_router
from services.document_flow_service import (
    DOCUMENT_KIND_CREDIT_NOTE,
    DOCUMENT_KIND_DEBIT_NOTE,
    DOCUMENT_KIND_FISCAL_DOCUMENT,
    DOCUMENT_KIND_QUOTATION,
    DOCUMENT_STATUS_ISSUED,
    DOCUMENT_STATUS_PENDING,
)


@pytest.fixture(autouse=True)
def dashboard_clock(monkeypatch):
    monkeypatch.setattr(fiscal_time, "today_lima", lambda: date(2026, 9, 28))


def _document(
    db,
    tenant,
    user,
    client,
    *,
    issued_at: datetime,
    amount: str,
    state: str = DOCUMENT_STATUS_ISSUED,
    kind: str = DOCUMENT_KIND_FISCAL_DOCUMENT,
    type_code: str = "01",
    reference_id: int | None = None,
    due_at: datetime | None = None,
    sunat_error: str | None = None,
    series: str | None = None,
    correlative: int | None = None,
    source_quote_id: int | None = None,
):
    if series is None:
        series = {
            DOCUMENT_KIND_FISCAL_DOCUMENT: "F001",
            DOCUMENT_KIND_CREDIT_NOTE: "FC01",
            DOCUMENT_KIND_DEBIT_NOTE: "FD01",
            DOCUMENT_KIND_QUOTATION: "COT",
        }[kind]
    if correlative is None:
        correlative = (
            db.query(models.Cotizacion)
            .filter(
                models.Cotizacion.tenant_id == tenant.id,
                models.Cotizacion.serie == series,
            )
            .count()
            + 1
        )
    row = models.Cotizacion(
        tenant_id=tenant.id,
        usuario_id=user.id,
        cliente_id=client.id,
        serie=series,
        correlativo=correlative,
        fecha_emision=issued_at,
        fecha_vencimiento=due_at,
        moneda="PEN",
        estado=state,
        document_kind=kind,
        tipo_comprobante=type_code,
        nota_referencia_id=reference_id,
        source_quote_id=source_quote_id,
        total_gravada=Decimal(amount),
        total_igv=Decimal("0.00"),
        total_venta=Decimal(amount),
        saldo_pendiente=Decimal(amount),
        sunat_error=sunat_error,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _item(db, document, product, *, amount: str, quantity: str):
    row = models.CotizacionItem(
        cotizacion_id=document.id,
        producto_id=product.id,
        descripcion=product.nombre,
        cantidad=Decimal(quantity),
        precio_unitario=Decimal(amount),
        valor_unitario=Decimal(amount),
        total_base_igv=Decimal(amount),
        total_igv=Decimal("0.00"),
        total_item=Decimal(amount),
        unidad_medida="NIU",
        tipo_afectacion_igv="10",
    )
    db.add(row)
    db.commit()
    return row


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


def test_business_dashboard_uses_real_fiscal_semantics(db_session):
    tenant = make_tenant(db_session, "DASH01")
    user = make_user(db_session, tenant, email="dashboard@test.com")
    returning = make_cliente(db_session, tenant, "RETURN")
    new_client = make_cliente(db_session, tenant, "NEW")
    paper = make_producto(db_session, tenant, "PAPER")
    ink = make_producto(db_session, tenant, "INK")

    previous = _document(
        db_session,
        tenant,
        user,
        returning,
        issued_at=datetime(2026, 8, 10, 10, 0),
        amount="400.00",
    )
    _item(db_session, previous, paper, amount="400.00", quantity="4")

    accepted = _document(
        db_session,
        tenant,
        user,
        returning,
        issued_at=datetime(2026, 9, 5, 10, 0),
        due_at=datetime(2026, 9, 20, 10, 0),
        amount="500.00",
    )
    _item(db_session, accepted, paper, amount="500.00", quantity="5")
    accepted.sunat_error = "Error historico ya resuelto"
    db_session.add(
        models.CotizacionItem(
            cotizacion_id=accepted.id,
            producto_id=None,
            descripcion="Linea libre sin producto de catalogo",
            cantidad=Decimal("1"),
            precio_unitario=Decimal("9999.00"),
            valor_unitario=Decimal("9999.00"),
            total_base_igv=Decimal("9999.00"),
            total_igv=Decimal("0.00"),
            total_item=Decimal("9999.00"),
            unidad_medida="NIU",
            tipo_afectacion_igv="10",
        )
    )
    db_session.commit()

    pending = _document(
        db_session,
        tenant,
        user,
        new_client,
        issued_at=datetime(2026, 9, 15, 10, 0),
        amount="200.00",
        state=DOCUMENT_STATUS_PENDING,
        sunat_error="Proveedor temporalmente no disponible",
    )
    _item(db_session, pending, ink, amount="200.00", quantity="2")

    draft = _document(
        db_session,
        tenant,
        user,
        new_client,
        issued_at=datetime(2026, 9, 16, 10, 0),
        amount="900.00",
        state="borrador",
        sunat_error="Borrador aun no enviado",
    )
    _item(db_session, draft, ink, amount="900.00", quantity="9")

    credit = _document(
        db_session,
        tenant,
        user,
        returning,
        issued_at=datetime(2026, 9, 18, 10, 0),
        amount="100.00",
        kind=DOCUMENT_KIND_CREDIT_NOTE,
        type_code="07",
        reference_id=accepted.id,
    )
    _item(db_session, credit, paper, amount="100.00", quantity="1")
    debit = _document(
        db_session,
        tenant,
        user,
        returning,
        issued_at=datetime(2026, 9, 19, 10, 0),
        amount="50.00",
        kind=DOCUMENT_KIND_DEBIT_NOTE,
        type_code="08",
        reference_id=accepted.id,
    )
    _item(db_session, debit, paper, amount="50.00", quantity="0.5")

    warehouse = models.Warehouse(
        tenant_id=tenant.id,
        code="MAIN",
        name="Principal",
        is_default=True,
        is_active=True,
    )
    db_session.add(warehouse)
    db_session.commit()
    db_session.add(
        models.InventoryBalance(
            tenant_id=tenant.id,
            warehouse_id=warehouse.id,
            product_id=paper.id,
            on_hand=Decimal("1"),
            committed=Decimal("0"),
            minimum_stock=Decimal("2"),
        )
    )
    db_session.commit()

    dashboard_tenant_id = tenant.id
    with _SelectCapture(db_session) as capture:
        payload = get_business_dashboard(
            db_session,
            dashboard_tenant_id,
            start=datetime(2026, 9, 1).date(),
            end=datetime(2026, 9, 28).date(),
        )

    assert payload["summary"] == {
        "sales_amount": Decimal("650.00"),
        "sales_count": 2,
        "pending_sunat_amount": Decimal("200.00"),
        "sales_change_percent": Decimal("62.5"),
        "customers_count": 2,
        "new_customers_count": 1,
        "returning_customers_count": 1,
        "average_sale": Decimal("325.00"),
        "overdue_amount": Decimal("450.00"),
        "overdue_customers_count": 1,
    }
    september = payload["history"][-1]
    assert september["sales_amount"] == Decimal("650.00")
    assert september["is_partial"] is True
    assert september["previous_matched_sales"] == Decimal("400.00")
    assert payload["products"][0]["name"] == paper.nombre
    assert payload["products"][0]["amount"] == Decimal("450.00")
    assert all(row["id"] is not None for row in payload["products"])
    assert next(row for row in payload["products"] if row["id"] == ink.id)[
        "amount"
    ] == Decimal("200.00")
    assert payload["clients"][0]["name"] == returning.razon_social
    assert payload["clients"][0]["amount"] == Decimal("450.00")
    assert payload["pending"] == {
        "low_stock_products": 1,
        "fiscal_documents_with_errors": 1,
    }
    assert payload["conversion"]["available"] is True
    assert payload["conversion"]["quote_count"] == 0
    assert payload["conversion"]["rate_percent"] is None
    assert payload["follow_up"]["quotes"]["available"] is True
    assert all(row["quoted_amount"] == Decimal("0.00") for row in payload["history"])
    assert payload["meta"]["period"]["label"] == "1–28 sep 2026"
    assert payload["meta"]["comparison"]["label"] == "1–28 ago 2026"
    assert len(capture.statements) <= 6

    ink_id = ink.id
    with _SelectCapture(db_session) as filtered_capture:
        product_filtered = get_business_dashboard(
            db_session,
            dashboard_tenant_id,
            start=datetime(2026, 9, 1).date(),
            end=datetime(2026, 9, 28).date(),
            product_id=ink_id,
        )
    assert product_filtered["summary"]["overdue_amount"] == Decimal("450.00")
    assert product_filtered["summary"]["overdue_customers_count"] == 1
    assert len(filtered_capture.statements) <= 6


def test_business_dashboard_isolates_tenants(db_session):
    tenant = make_tenant(db_session, "DASH02")
    other_tenant = make_tenant(db_session, "DASH03")
    user = make_user(db_session, tenant, email="one@test.com")
    other_user = make_user(db_session, other_tenant, email="two@test.com")
    client = make_cliente(db_session, tenant, "ONE")
    other_client = make_cliente(db_session, other_tenant, "TWO")

    _document(
        db_session,
        tenant,
        user,
        client,
        issued_at=datetime(2026, 9, 8, 10, 0),
        amount="120.00",
    )
    _document(
        db_session,
        other_tenant,
        other_user,
        other_client,
        issued_at=datetime(2026, 9, 8, 10, 0),
        amount="9999.00",
    )

    payload = get_business_dashboard(
        db_session,
        tenant.id,
        start=datetime(2026, 9, 1).date(),
        end=datetime(2026, 9, 28).date(),
    )

    assert payload["summary"]["sales_amount"] == Decimal("120.00")
    assert payload["summary"]["sales_count"] == 1
    assert payload["summary"]["customers_count"] == 1


def test_business_dashboard_keeps_true_declines_and_ignores_recent_notes_for_inactivity(
    db_session,
):
    tenant = make_tenant(db_session, "DASH04")
    user = make_user(db_session, tenant, email="ranking@test.com")
    active_client = make_cliente(db_session, tenant, "ACTIVE")
    inactive_client = make_cliente(db_session, tenant, "INACTIVE")
    today = fiscal_time.today_lima()
    current_day = min(today.day, 10)
    current_at = datetime(today.year, today.month, current_day, 10, 0)
    previous_last_day = today.replace(day=1) - timedelta(days=1)
    previous_at = datetime(
        previous_last_day.year,
        previous_last_day.month,
        min(current_day, previous_last_day.day),
        10,
        0,
    )

    declining_product = None
    for index in range(11):
        product = make_producto(db_session, tenant, f"RANK{index:02d}")
        previous = _document(
            db_session,
            tenant,
            user,
            active_client,
            issued_at=previous_at,
            amount="100.00",
        )
        _item(db_session, previous, product, amount="100.00", quantity="1")
        current_amount = "1.00" if index == 10 else str(200 + index)
        current = _document(
            db_session,
            tenant,
            user,
            active_client,
            issued_at=current_at,
            amount=current_amount,
        )
        _item(db_session, current, product, amount=current_amount, quantity="1")
        if index == 10:
            declining_product = product

    old_sale = _document(
        db_session,
        tenant,
        user,
        inactive_client,
        issued_at=datetime.combine(today - timedelta(days=75), datetime.min.time()),
        amount="300.00",
    )
    recent_credit = _document(
        db_session,
        tenant,
        user,
        inactive_client,
        issued_at=datetime.combine(today - timedelta(days=2), datetime.min.time()),
        amount="50.00",
        kind=DOCUMENT_KIND_CREDIT_NOTE,
        type_code="07",
        reference_id=old_sale.id,
    )
    assert recent_credit.id

    payload = get_business_dashboard(db_session, tenant.id)

    product_ids = {row["id"] for row in payload["products"]}
    assert declining_product.id in product_ids
    declining = next(
        row for row in payload["products"] if row["id"] == declining_product.id
    )
    assert declining["change_percent"] == Decimal("-99.0")

    inactive_rows = payload["follow_up"]["inactive"]["rows"]
    inactive = next(row for row in inactive_rows if row["client_id"] == inactive_client.id)
    assert inactive["amount"] == Decimal("300.00")
    assert inactive["age_days"] >= 60


def _dashboard_http_client(db_session, user) -> TestClient:
    app = FastAPI()
    app.include_router(dashboard_router.router)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_tenant] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _business_dashboard_contract_payload() -> dict:
    return {
        "meta": {
            "generated_at": datetime(2026, 9, 28, 12, 30),
            "currency": "PEN",
            "period": {
                "start": datetime(2026, 9, 1).date(),
                "end": datetime(2026, 9, 28).date(),
                "label": "1–28 sep 2026",
            },
            "comparison": {
                "start": datetime(2026, 8, 1).date(),
                "end": datetime(2026, 8, 28).date(),
                "label": "1–28 aug 2026",
            },
            "history": {
                "start": datetime(2026, 1, 1).date(),
                "end": datetime(2026, 9, 28).date(),
                "label": "2026-01-01 – 2026-09-28",
            },
            "client_id": 7,
            "product_id": 11,
        },
        "summary": {
            "sales_amount": Decimal("650.25"),
            "sales_count": 2,
            "pending_sunat_amount": Decimal("200.00"),
            "sales_change_percent": Decimal("62.5"),
            "customers_count": 2,
            "new_customers_count": 1,
            "returning_customers_count": 1,
            "average_sale": Decimal("325.13"),
            "overdue_amount": Decimal("450.00"),
            "overdue_customers_count": 1,
        },
        "history": [
            {
                "year": 2026,
                "month": 9,
                "sales_amount": Decimal("650.25"),
                "quoted_amount": Decimal("800.00"),
                "is_partial": True,
                "cutoff_day": 28,
                "previous_matched_sales": Decimal("400.00"),
            }
        ],
        "conversion": {
            "available": True,
            "reason": None,
            "quote_count": 5,
            "linked_sales_count": 2,
            "rate_percent": Decimal("40.0"),
        },
        "products": [
            {
                "id": 11,
                "name": "Papel bond A4",
                "unit": "NIU",
                "quantity": Decimal("5.00"),
                "amount": Decimal("450.00"),
                "previous_amount": Decimal("300.00"),
                "change_percent": Decimal("50.0"),
            }
        ],
        "clients": [
            {
                "id": 7,
                "name": "Comercial Norte",
                "amount": Decimal("450.00"),
                "purchases": 2,
                "last_purchase": datetime(2026, 9, 25).date(),
                "share_percent": Decimal("69.2"),
                "previous_amount": Decimal("300.00"),
                "change_percent": Decimal("50.0"),
            }
        ],
        "follow_up": {
            "quotes": {
                "available": True,
                "reason": None,
                "count": 1,
                "rows": [
                    {
                        "client_id": 7,
                        "client": "Comercial Norte",
                        "reference": "COT-000318",
                        "amount": Decimal("200.00"),
                        "age_days": 16,
                    }
                ],
            },
            "declining": {
                "available": True,
                "reason": None,
                "count": 0,
                "rows": [],
            },
            "inactive": {
                "available": False,
                "reason": "No hay historial suficiente.",
                "count": 0,
                "rows": [],
            },
        },
        "pending": {
            "low_stock_products": 3,
            "fiscal_documents_with_errors": 1,
        },
    }


def test_business_dashboard_http_contract_serializes_and_forwards_filters(
    db_session,
    monkeypatch,
):
    tenant = make_tenant(db_session, "DASHHTTP01")
    user = make_user(db_session, tenant, email="dashboard-http@test.com")
    captured = {}

    def fake_dashboard(db, tenant_id, **filters):
        captured.update({"db": db, "tenant_id": tenant_id, **filters})
        return _business_dashboard_contract_payload()

    monkeypatch.setattr(
        dashboard_router.crud,
        "get_business_dashboard",
        fake_dashboard,
    )

    response = _dashboard_http_client(db_session, user).get(
        "/analytics/dashboard/business",
        params={
            "desde": "2026-09-01",
            "hasta": "2026-09-28",
            "client_id": 7,
            "product_id": 11,
            "currency": "PEN",
        },
    )

    assert response.status_code == 200
    assert captured == {
        "db": db_session,
        "tenant_id": tenant.id,
        "start": datetime(2026, 9, 1).date(),
        "end": datetime(2026, 9, 28).date(),
        "client_id": 7,
        "product_id": 11,
        "currency": "PEN",
    }
    body = response.json()
    assert set(body) == {
        "meta",
        "summary",
        "history",
        "conversion",
        "products",
        "clients",
        "follow_up",
        "pending",
    }
    assert body["meta"]["period"] == {
        "start": "2026-09-01",
        "end": "2026-09-28",
        "label": "1–28 sep 2026",
    }
    assert body["summary"]["sales_amount"] == "650.25"
    assert body["summary"]["sales_change_percent"] == "62.5"
    assert body["history"][0]["is_partial"] is True
    assert body["products"][0]["quantity"] == "5.00"
    assert body["follow_up"]["inactive"]["available"] is False


def test_business_dashboard_http_maps_domain_validation_to_400(
    db_session,
    monkeypatch,
):
    tenant = make_tenant(db_session, "DASHHTTP02")
    user = make_user(db_session, tenant, email="dashboard-invalid@test.com")

    def reject_period(*_args, **_kwargs):
        raise ValueError("La fecha inicial no puede ser posterior a la fecha final.")

    monkeypatch.setattr(
        dashboard_router.crud,
        "get_business_dashboard",
        reject_period,
    )
    response = _dashboard_http_client(db_session, user).get(
        "/analytics/dashboard/business?desde=2026-09-28&hasta=2026-09-01",
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "La fecha inicial no puede ser posterior a la fecha final."
    }


@pytest.mark.parametrize(
    "query",
    [
        "client_id=0",
        "product_id=0",
        "currency=USD",
        "desde=no-es-fecha",
    ],
)
def test_business_dashboard_http_rejects_invalid_query_before_crud(
    db_session,
    monkeypatch,
    query,
):
    tenant = make_tenant(db_session, f"DASHHTTP{abs(hash(query)) % 10000:04d}")
    user = make_user(
        db_session,
        tenant,
        email=f"dashboard-query-{abs(hash(query))}@test.com",
    )
    called = False

    def should_not_run(*_args, **_kwargs):
        nonlocal called
        called = True
        return _business_dashboard_contract_payload()

    monkeypatch.setattr(
        dashboard_router.crud,
        "get_business_dashboard",
        should_not_run,
    )
    response = _dashboard_http_client(db_session, user).get(
        f"/analytics/dashboard/business?{query}",
    )

    assert response.status_code == 422
    assert called is False


def test_business_dashboard_http_requires_authentication():
    app = FastAPI()
    app.include_router(dashboard_router.router)

    response = TestClient(app).get("/analytics/dashboard/business")

    assert response.status_code == 401


def test_quote_conversion_uses_distinct_tenant_safe_links_and_real_followup(db_session):
    tenant = make_tenant(db_session, "QUOTES01")
    user = make_user(db_session, tenant, email="quotes@test.com")
    client = make_cliente(db_session, tenant, "QUOTES01")
    other = make_tenant(db_session, "QUOTES02")
    other_user = make_user(db_session, other, email="other-quotes@test.com")
    other_client = make_cliente(db_session, other, "QUOTES02")
    product = make_producto(db_session, tenant, "QUOTEPRODUCT")

    quotes = [
        _document(db_session, tenant, user, client, issued_at=datetime(2026, 9, day),
                  amount="100.00", kind=DOCUMENT_KIND_QUOTATION, type_code="00",
                  state=DOCUMENT_STATUS_PENDING)
        for day in range(1, 7)
    ]
    _item(db_session, quotes[0], product, amount="100.00", quantity="1")
    # Multiple sales for one quotation must still count as one converted quotation.
    for state in (DOCUMENT_STATUS_ISSUED, DOCUMENT_STATUS_PENDING):
        _document(db_session, tenant, user, client, issued_at=datetime(2026, 9, 20),
                  amount="100.00", source_quote_id=quotes[0].id, state=state)
    quotes[0].estado = DOCUMENT_STATUS_ISSUED
    db_session.commit()
    _document(db_session, tenant, user, client, issued_at=datetime(2026, 9, 20),
              amount="100.00", type_code="03", source_quote_id=quotes[1].id,
              state=DOCUMENT_STATUS_PENDING)
    for quote, state in ((quotes[2], "anulada"), (quotes[3], "borrador")):
        _document(db_session, tenant, user, client, issued_at=datetime(2026, 9, 20),
                  amount="100.00", source_quote_id=quote.id, state=state)
    # Even a corrupt cross-tenant source ID must not mark our quote as converted.
    _document(db_session, other, other_user, other_client, issued_at=datetime(2026, 9, 20),
              amount="9999.00", source_quote_id=quotes[4].id)
    _document(db_session, tenant, user, client, issued_at=datetime(2026, 10, 1),
              amount="100.00", source_quote_id=quotes[5].id)
    # Quote status alone is not proof of a linked sale.
    previously_invoiced_quote = _document(
        db_session, tenant, user, client, issued_at=datetime(2026, 9, 7),
        amount="100.00", kind=DOCUMENT_KIND_QUOTATION, type_code="00",
    )
    _document(db_session, tenant, user, client, issued_at=datetime(2026, 9, 20),
              amount="100.00", source_quote_id=previously_invoiced_quote.id, state="anulada")
    for state in ("anulada", "borrador"):
        _document(db_session, tenant, user, client, issued_at=datetime(2026, 9, 8),
                  amount="100.00", kind=DOCUMENT_KIND_QUOTATION, type_code="00", state=state)
    _document(db_session, tenant, user, client, issued_at=datetime(2026, 10, 1),
              amount="100.00", kind=DOCUMENT_KIND_QUOTATION, type_code="00")
    _document(db_session, other, other_user, other_client, issued_at=datetime(2026, 9, 1),
              amount="9999.00", kind=DOCUMENT_KIND_QUOTATION, type_code="00")
    older_quote = _document(db_session, tenant, user, client, issued_at=datetime(2026, 8, 10),
                            amount="150.00", kind=DOCUMENT_KIND_QUOTATION, type_code="00")
    _document(db_session, tenant, user, client, issued_at=datetime(2026, 9, 20),
              amount="150.00", source_quote_id=older_quote.id)

    tenant_id = tenant.id
    with _SelectCapture(db_session) as capture:
        payload = get_business_dashboard(db_session, tenant_id)
    assert payload["conversion"] == {
        "available": True, "reason": None, "quote_count": 7,
        "linked_sales_count": 2, "rate_percent": Decimal("28.6"),
    }
    assert payload["history"][-1]["quoted_amount"] == Decimal("700.00")
    followup = payload["follow_up"]["quotes"]
    assert followup["count"] == 5
    assert [row["quote_id"] for row in followup["rows"]] == [quote.id for quote in quotes[2:5]]
    assert followup["rows"][0]["reference"] == "COT-000003"
    assert followup["rows"][0]["age_days"] == 25
    assert len(capture.statements) == 6
    filtered = get_business_dashboard(db_session, tenant_id, product_id=product.id)
    assert filtered["conversion"]["quote_count"] == 1
    assert filtered["conversion"]["linked_sales_count"] == 1
    assert filtered["follow_up"]["quotes"]["count"] == 0
    older_cohort = get_business_dashboard(db_session, tenant_id, start=date(2026, 8, 1), end=date(2026, 8, 31))
    assert older_cohort["conversion"]["quote_count"] == 1
    assert older_cohort["conversion"]["linked_sales_count"] == 1
    assert older_cohort["conversion"]["rate_percent"] == Decimal("100.0")
    assert older_cohort["follow_up"]["quotes"]["count"] == 0
    # A quote marked invoiced can need follow-up again when its only sale was voided.
    annulled_sale_cohort = get_business_dashboard(
        db_session, tenant_id, start=date(2026, 9, 7), end=date(2026, 9, 7),
    )
    assert annulled_sale_cohort["conversion"]["linked_sales_count"] == 0
    assert annulled_sale_cohort["follow_up"]["quotes"]["count"] == 1
    assert annulled_sale_cohort["follow_up"]["quotes"]["rows"][0]["quote_id"] == previously_invoiced_quote.id
    # API schema must retain the direct-navigation ID.
    body = _dashboard_http_client(db_session, user).get("/analytics/dashboard/business").json()
    assert body["follow_up"]["quotes"]["rows"][0]["quote_id"] == quotes[2].id


def test_history_starts_at_real_activity_and_compares_matching_days_independently(db_session):
    tenant = make_tenant(db_session, "HISTORY01")
    user = make_user(db_session, tenant, email="history@test.com")
    client = make_cliente(db_session, tenant, "HISTORY01")
    other = make_tenant(db_session, "HISTORY02")
    other_user = make_user(db_session, other, email="history-other@test.com")
    other_client = make_cliente(db_session, other, "HISTORY02")
    _document(db_session, other, other_user, other_client, issued_at=datetime(2020, 1, 1), amount="9000")
    for kind in (DOCUMENT_KIND_QUOTATION, DOCUMENT_KIND_FISCAL_DOCUMENT):
        for state in ("borrador", "anulada"):
            _document(db_session, tenant, user, client, issued_at=datetime(2021, 1, 1),
                      amount="9000", kind=kind, state=state)
    _document(db_session, tenant, user, client, issued_at=datetime(2024, 12, 15),
              amount="300", kind=DOCUMENT_KIND_QUOTATION, type_code="00",
              state=DOCUMENT_STATUS_PENDING)
    for issued_at, amount in ((datetime(2026, 8, 10), "100"),
                              (datetime(2026, 8, 31), "900"),
                              (datetime(2026, 9, 10), "200")):
        _document(db_session, tenant, user, client, issued_at=issued_at, amount=amount)

    payload = get_business_dashboard(db_session, tenant.id, start=date(2026, 8, 1), end=date(2026, 8, 31))
    assert payload["meta"]["history"]["start"] == date(2024, 12, 15)
    assert payload["meta"]["history"]["end"] == date(2026, 9, 28)
    assert len(payload["history"]) == 22
    assert payload["history"][0]["quoted_amount"] == Decimal("300.00")
    assert payload["history"][1]["sales_amount"] == Decimal("0.00")
    assert payload["history"][-2]["sales_amount"] == Decimal("1000.00")
    assert payload["history"][-2]["is_partial"] is False
    assert payload["history"][-1]["sales_amount"] == Decimal("200.00")
    assert payload["history"][-1]["previous_matched_sales"] == Decimal("100.00")
    assert payload["history"][-1]["cutoff_day"] == 28
    assert payload["summary"]["sales_amount"] == Decimal("1000.00")


def test_empty_business_history_has_no_invented_months(db_session):
    tenant = make_tenant(db_session, "HISTORYEMPTY")
    payload = get_business_dashboard(db_session, tenant.id)
    assert payload["history"] == []
    assert payload["meta"]["history"]["start"] == date(2026, 9, 28)
    assert payload["meta"]["history"]["end"] == date(2026, 9, 28)
    assert payload["conversion"]["quote_count"] == 0
    assert payload["conversion"]["rate_percent"] is None
