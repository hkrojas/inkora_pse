"""Totals and tenant-safe pagination for dashboard detail windows."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import make_cliente, make_producto, make_tenant, make_user
from crud.dashboard_business import get_business_dashboard
from crud.dashboard_records import get_business_dashboard_records
from routers import dashboard as dashboard_router
from services.document_flow_service import (
    DOCUMENT_KIND_CREDIT_NOTE,
    DOCUMENT_KIND_DEBIT_NOTE,
    DOCUMENT_KIND_QUOTATION,
    DOCUMENT_STATUS_PENDING,
)
from test_dashboard_business import (
    _dashboard_http_client,
    _document,
    _item,
    _SelectCapture,
    dashboard_clock,  # noqa: F401: reuse the fixed Lima clock fixture
)


@pytest.fixture
def selection(db_session):
    tenant = make_tenant(db_session, "RECORDS")
    user = make_user(db_session, tenant, email="records@test.com")
    client = make_cliente(db_session, tenant, "BUYER")
    paper = make_producto(db_session, tenant, "PAPER")
    ink = make_producto(db_session, tenant, "INK")
    return tenant, user, client, paper, ink


def _records(db_session, tenant_id, **params):
    return get_business_dashboard_records(
        db_session, tenant_id,
        start=params.pop("start", date(2026, 9, 1)),
        end=params.pop("end", date(2026, 9, 28)),
        **params,
    )


def test_document_and_product_details_explain_different_totals(db_session, selection):
    tenant, user, client, paper, ink = selection
    accepted = _document(db_session, tenant, user, client, issued_at=datetime(2026, 9, 2), amount="100")
    _item(db_session, accepted, paper, amount="20", quantity="2")
    _item(db_session, accepted, paper, amount="30", quantity="3")
    _item(db_session, accepted, ink, amount="50", quantity="5")
    pending = _document(db_session, tenant, user, client, issued_at=datetime(2026, 9, 3), amount="40", state=DOCUMENT_STATUS_PENDING, type_code="03")
    _item(db_session, pending, paper, amount="40", quantity="4")
    credit = _document(db_session, tenant, user, client, issued_at=datetime(2026, 9, 4), amount="10", kind=DOCUMENT_KIND_CREDIT_NOTE, type_code="07", reference_id=accepted.id)
    _item(db_session, credit, paper, amount="10", quantity="1")
    debit = _document(db_session, tenant, user, client, issued_at=datetime(2026, 9, 5), amount="5", kind=DOCUMENT_KIND_DEBIT_NOTE, type_code="08", reference_id=accepted.id)
    _item(db_session, debit, paper, amount="5", quantity="0.5")
    for state, kind in [("borrador", None), ("anulada", None), (DOCUMENT_STATUS_PENDING, DOCUMENT_KIND_CREDIT_NOTE), (DOCUMENT_STATUS_PENDING, DOCUMENT_KIND_QUOTATION)]:
        extra = {"kind": kind, "type_code": "07" if kind == DOCUMENT_KIND_CREDIT_NOTE else "00"} if kind else {}
        row = _document(db_session, tenant, user, client, issued_at=datetime(2026, 9, 6), amount="999", state=state, **extra)
        _item(db_session, row, paper, amount="999", quantity="99")
    tenant_id, paper_id = tenant.id, paper.id
    with _SelectCapture(db_session) as capture:
        documents = _records(db_session, tenant_id, product_id=paper_id)
    assert len(capture.statements) == 2
    assert documents["total"] == 4
    assert documents["total_amount"] == Decimal("135.00")
    assert next(row for row in documents["items"] if row["document_id"] == pending.id)["state"] == DOCUMENT_STATUS_PENDING
    assert next(row for row in documents["items"] if row["document_id"] == credit.id)["amount"] == Decimal("-10.00")
    with _SelectCapture(db_session) as capture:
        product = _records(db_session, tenant_id, product_id=paper_id, measure="product", product_unit="NIU")
    assert len(capture.statements) == 2
    assert product["total"] == 4
    assert product["total_amount"] == Decimal("85.00")
    assert sum(row["quantity"] for row in product["items"]) == Decimal("8.5")
    assert next(row for row in product["items"] if row["document_id"] == accepted.id)["amount"] == Decimal("50.00")
    dashboard = get_business_dashboard(db_session, tenant_id, start=date(2026, 9, 1), end=date(2026, 9, 28), product_id=paper_id)
    assert dashboard["summary"]["sales_amount"] == documents["total_amount"]
    assert next(row for row in dashboard["products"] if row["id"] == paper_id)["amount"] == product["total_amount"]


def test_product_contains_filter_and_units_preserve_ranking_context(db_session, selection):
    tenant, user, client, paper, ink = selection
    mixed = _document(db_session, tenant, user, client, issued_at=datetime(2026, 9, 2), amount="100")
    _item(db_session, mixed, paper, amount="10", quantity="1")
    _item(db_session, mixed, ink, amount="20", quantity="2")
    other_unit = _item(db_session, mixed, ink, amount="70", quantity="7")
    other_unit.unidad_medida = "KGM"
    db_session.commit()
    only_ink = _document(db_session, tenant, user, client, issued_at=datetime(2026, 9, 3), amount="99")
    _item(db_session, only_ink, ink, amount="99", quantity="9")
    response = _records(db_session, tenant.id, product_id=ink.id, contains_product_id=paper.id, product_unit="NIU", measure="product")
    assert response["total"] == 1
    assert response["total_amount"] == Decimal("20.00")
    assert response["items"][0]["quantity"] == Decimal("2")
    assert response["items"][0]["unit"] == "NIU"
    assert response["meta"]["contains_product_id"] == paper.id
    all_units = _records(db_session, tenant.id, product_id=ink.id, contains_product_id=paper.id, measure="product")
    assert all_units["total_amount"] == Decimal("90.00")
    assert all_units["items"][0]["quantity"] is None
    assert all_units["items"][0]["unit"] is None


def test_null_and_niu_units_share_one_ranking_and_matching_detail(db_session, selection):
    tenant, user, client, paper, _ = selection
    previous = _document(db_session, tenant, user, client, issued_at=datetime(2026, 8, 2), amount="30")
    previous_item = _item(db_session, previous, paper, amount="30", quantity="3")
    previous_item.unidad_medida = None
    current = _document(db_session, tenant, user, client, issued_at=datetime(2026, 9, 2), amount="120")
    historic_item = _item(db_session, current, paper, amount="20", quantity="2")
    historic_item.unidad_medida = None
    standard_item = _item(db_session, current, paper, amount="30", quantity="3")
    kilogram_item = _item(db_session, current, paper, amount="70", quantity="7")
    kilogram_item.unidad_medida = "KGM"
    db_session.commit()

    dashboard = get_business_dashboard(db_session, tenant.id, start=date(2026, 9, 1), end=date(2026, 9, 28))
    unit_rows = [row for row in dashboard["products"] if row["id"] == paper.id and row["unit"] == "NIU"]
    assert len(unit_rows) == 1
    assert unit_rows[0]["amount"] == Decimal("50.00")
    assert unit_rows[0]["previous_amount"] == Decimal("30.00")
    assert unit_rows[0]["quantity"] == Decimal("5")
    detail = _records(db_session, tenant.id, product_id=paper.id, product_unit="NIU", measure="product")
    assert detail["total_amount"] == unit_rows[0]["amount"]
    assert detail["items"][0]["quantity"] == unit_rows[0]["quantity"]
    assert detail["items"][0]["unit"] == "NIU"

    # A NULL unit is an NIU line, so it must not be ignored when detecting
    # incompatible quantities alongside another unit in the same document.
    db_session.delete(standard_item)
    db_session.commit()
    all_units = _records(db_session, tenant.id, product_id=paper.id, measure="product")
    assert all_units["total_amount"] == Decimal("90.00")
    assert all_units["items"][0]["quantity"] is None
    assert all_units["items"][0]["unit"] is None


def test_records_scope_dates_clients_currency_and_first_activity(db_session, selection):
    tenant, user, client, paper, _ = selection
    other_client = make_cliente(db_session, tenant, "OTHER")
    for timestamp, selected_client, currency in [
        (datetime(2022, 1, 1), client, "PEN"),
        (datetime(2026, 9, 9, 23, 59, 59), client, "PEN"),
        (datetime(2026, 9, 10, 0, 0), client, "PEN"),
        (datetime(2026, 9, 10, 23, 59, 59), client, "PEN"),
        (datetime(2026, 9, 11, 0, 0), client, "PEN"),
        (datetime(2026, 9, 10), other_client, "PEN"),
        (datetime(2026, 9, 10), client, "USD"),
        (datetime(2026, 9, 29), client, "PEN"),
    ]:
        row = _document(db_session, tenant, user, selected_client, issued_at=timestamp, amount="10")
        row.moneda = currency
        db_session.commit()
        _item(db_session, row, paper, amount="10", quantity="1")
    response = _records(db_session, tenant.id, client_id=client.id, start=date(2026, 9, 10), end=date(2026, 9, 10))
    assert response["total"] == 2
    assert response["total_amount"] == Decimal("20.00")
    assert response["meta"]["period"]["end"] == date(2026, 9, 10)
    all_history = _records(db_session, tenant.id, start=date(2022, 1, 1), end=date(2030, 1, 1))
    assert all_history["total"] == 6
    assert all_history["meta"]["period"]["end"] == date(2026, 9, 28)


def test_records_ownership_and_unknown_ids_are_empty(db_session, selection):
    tenant, user, client, paper, _ = selection
    other_tenant = make_tenant(db_session, "FOREIGN")
    other_user = make_user(db_session, other_tenant, email="foreign-records@test.com")
    other_client = make_cliente(db_session, other_tenant, "FOREIGN")
    other_product = make_producto(db_session, other_tenant, "FOREIGN")
    other_doc = _document(db_session, other_tenant, other_user, other_client, issued_at=datetime(2026, 9, 10), amount="500")
    _item(db_session, other_doc, other_product, amount="500", quantity="5")
    own_doc = _document(db_session, tenant, user, client, issued_at=datetime(2026, 9, 10), amount="10")
    _item(db_session, own_doc, paper, amount="10", quantity="1")
    # Even malformed historic links must not authorize cross-company selection.
    _item(db_session, own_doc, other_product, amount="900", quantity="9")
    for params in [
        {"client_id": other_client.id},
        {"product_id": other_product.id},
        {"product_id": other_product.id, "measure": "product"},
        {"product_id": paper.id, "contains_product_id": other_product.id, "measure": "product"},
        {"client_id": 999999},
        {"product_id": 999999},
    ]:
        response = _records(db_session, tenant.id, **params)
        assert response["total"] == 0
        assert response["total_amount"] == Decimal("0.00")
        assert response["items"] == []
    assert _records(db_session, tenant.id)["total_amount"] == Decimal("10.00")


def test_pagination_counts_selection_not_page_and_stable_order(db_session, selection):
    tenant, user, client, _, _ = selection
    ids = []
    for index in range(18):
        doc = _document(db_session, tenant, user, client, issued_at=datetime(2026, 9, 10), amount=str(index + 1))
        ids.append(doc.id)
    tenant_id = tenant.id
    with _SelectCapture(db_session) as capture:
        page = _records(db_session, tenant_id)
    assert len(capture.statements) == 2
    assert page["total"] == 18
    assert page["total_amount"] == Decimal("171.00")
    assert page["limit"] == 15
    assert [row["document_id"] for row in page["items"]] == list(reversed(ids))[0:15]
    last = _records(db_session, tenant_id, skip=15)
    assert [row["document_id"] for row in last["items"]] == list(reversed(ids))[15:]
    empty_page = _records(db_session, tenant_id, skip=999)
    assert empty_page["items"] == []
    assert empty_page["total"] == 18
    assert empty_page["total_amount"] == Decimal("171.00")


def test_http_records_contract_validation_and_authentication(db_session, selection):
    tenant, user, client, paper, _ = selection
    row = _document(db_session, tenant, user, client, issued_at=datetime(2026, 9, 10), amount="118")
    _item(db_session, row, paper, amount="118", quantity="1")
    client_http = _dashboard_http_client(db_session, user)
    path = "/analytics/dashboard/business/records"
    params = {"desde": "2026-09-01", "hasta": "2026-09-28"}
    response = client_http.get(path, params=params)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert Decimal(response.json()["total_amount"]) == Decimal("118.00")
    assert response.json()["items"][0]["reference"] == "F001-000001"
    for extra, status in [
        ({"measure": "product"}, 400),
        ({"desde": "2026-09-29"}, 400),
        ({"limit": 101}, 422),
        ({"skip": -1}, 422),
        ({"product_id": 0}, 422),
        ({"contains_product_id": 0}, 422),
        ({"currency": "USD"}, 422),
        ({"measure": "unknown"}, 422),
        ({"product_unit": "X" * 21}, 422),
    ]:
        assert client_http.get(path, params={**params, **extra}).status_code == status
    app = FastAPI()
    app.include_router(dashboard_router.router)
    assert TestClient(app).get(path, params=params).status_code == 401
