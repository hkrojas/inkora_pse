"""Regression: an old quotation must not backdate a new fiscal document."""
import json
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import BackgroundTasks, HTTPException
from starlette.requests import Request

import crud
import fiscal_time
import models
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from config import settings
from routers import facturacion
from schemas import FacturarPayload
from schemas.notes import FiscalNoteDraftCreate
from services import emission_queue_service, facturacion_service, note_adjustment_service


OLD_DATE = datetime(2026, 9, 22, 9, 15)
ISSUE_DATE = datetime(2026, 10, 6, 23, 45)


@pytest.fixture(autouse=True)
def isolated_clock_and_network(monkeypatch):
    monkeypatch.setattr(facturacion.limiter, "enabled", False)
    monkeypatch.setattr(fiscal_time, "now_lima", lambda: ISSUE_DATE.replace(tzinfo=fiscal_time.LIMA_TZ))
    monkeypatch.setattr(settings, "EMISSION_MODE_DEFAULT", "async")
    monkeypatch.setattr(settings, "FISCAL_CONTINGENCY_TENANT_IDS", "")
    def forbidden(*args, **kwargs):
        raise AssertionError("These tests must not contact any fiscal provider")
    monkeypatch.setattr("requests.sessions.Session.request", forbidden)


def _setup(db, tipo):
    tenant = make_tenant(db, "DATE01")
    tenant.business_ruc = "20123456789"
    tenant.smartpse_company_id = "77"
    tenant.smartpse_environment = "demo"
    tenant.smartpse_usuario_secundaria = "local-demo-user"
    tenant.smartpse_token_acceso = "local-demo-token"
    user = make_user(db, tenant, email="date@test.invalid")
    db.add(models.Subscription(tenant_id=tenant.id, status="active"))
    client = make_cliente(db, tenant, "DATE01", tipo_documento="6" if tipo == "01" else "1",
                          numero_documento="20191308868" if tipo == "01" else "12345678")
    quote = make_quote_via_crud(db, tenant, user, client)
    quote.fecha_emision = OLD_DATE
    quote.condicion_pago = "contado"
    quote.fecha_vencimiento = None
    db.commit()
    return tenant, user, quote


def _emit(db, user, quote, tipo, selected_date=None):
    request = Request({"type": "http", "method": "POST", "path": "/cotizaciones/facturar",
                       "headers": [], "client": ("127.0.0.1", 1234)})
    return facturacion.emitir_comprobante(request, quote.id, FacturarPayload(tipo_comprobante=tipo, fecha_emision=selected_date),
        BackgroundTasks(), db=db, current_user=user, _emission_check=user, mode="async")


@pytest.mark.parametrize("tipo,age", [("01", 0), ("01", 1), ("01", 3), ("03", 0), ("03", 3), ("03", 5)])
def test_explicit_issue_date_reaches_frozen_payload_and_xml(db_session, tipo, age, monkeypatch):
    _, user, quote = _setup(db_session, tipo)
    chosen = (ISSUE_DATE - timedelta(days=age)).date()
    response = _emit(db_session, user, quote, tipo, chosen)
    result = json.loads(response.body)
    document = db_session.get(models.Cotizacion, result["resource_id"])
    job = db_session.get(models.DocumentEmissionJob, result["job_id"])
    prepared = job.payload_snapshot["prepared_sale"]
    assert document.fecha_emision.date() == chosen
    assert prepared["payload"]["fechaEmision"][:10] == chosen.isoformat()
    assert f"<cbc:IssueDate>{chosen}</cbc:IssueDate>" in prepared["unsigned_xml"]
    assert quote.fecha_emision == OLD_DATE
    monkeypatch.setattr(fiscal_time, "now_lima", lambda: (ISSUE_DATE + timedelta(days=1)).replace(tzinfo=fiscal_time.LIMA_TZ))
    same_job, created = emission_queue_service.enqueue_fiscal_document_job(db_session, document, user, tipo_comprobante=tipo)
    assert not created and same_job.id == job.id
    assert same_job.payload_snapshot["prepared_sale"] == prepared
    assert document.fecha_emision.date() == chosen


@pytest.mark.parametrize("tipo,age", [("01", -1), ("01", 4), ("03", -1), ("03", 6)])
def test_expired_or_future_explicit_date_fails_before_document_job_or_correlativo(db_session, tipo, age):
    _, user, quote = _setup(db_session, tipo)
    chosen = (ISSUE_DATE - timedelta(days=age)).date()
    with patch("crud._cotizaciones_fiscal._next_correlativo_for_series", side_effect=AssertionError("Reserved fiscal number")):
        with pytest.raises(HTTPException) as exc:
            _emit(db_session, user, quote, tipo, chosen)
    assert exc.value.status_code == 400
    assert db_session.query(models.Cotizacion).filter_by(source_quote_id=quote.id).count() == 0
    assert db_session.query(models.DocumentEmissionJob).count() == 0
    with pytest.raises(ValueError):
        crud.create_fiscal_document_from_quote(db_session, quote, user.id, tipo, fecha_emision=chosen)
    assert db_session.query(models.Cotizacion).filter_by(source_quote_id=quote.id).count() == 0


@pytest.mark.parametrize("tipo", ["01", "03"])
def test_explicit_past_issue_date_validates_credit_against_that_date_without_shifting(db_session, tipo):
    _, user, quote = _setup(db_session, tipo)
    chosen = (ISSUE_DATE - timedelta(days=3)).date()
    quote.condicion_pago = "credito_7"
    quote.fecha_vencimiento = ISSUE_DATE - timedelta(days=1)
    quote.cuotas_pago = [{"fecha_pago": quote.fecha_vencimiento.isoformat(), "monto": "118.00"}]
    db_session.commit()
    response = _emit(db_session, user, quote, tipo, chosen)
    job = db_session.get(models.DocumentEmissionJob, json.loads(response.body)["job_id"])
    assert job.payload_snapshot["prepared_sale"]["payload"]["cuotas"][0]["fechaPago"][:10] == "2026-10-05"
    assert quote.cuotas_pago[0]["fecha_pago"] == "2026-10-05T23:45:00"


@pytest.mark.parametrize("tipo", ["01", "03"])
def test_old_quote_emits_today_in_lima_and_freezes_exact_date(db_session, tipo, monkeypatch):
    _, user, quote = _setup(db_session, tipo)
    response = _emit(db_session, user, quote, tipo)
    assert response.status_code == 202
    result = json.loads(response.body)
    document = db_session.get(models.Cotizacion, result["resource_id"])
    job = db_session.get(models.DocumentEmissionJob, result["job_id"])
    prepared = job.payload_snapshot["prepared_sale"]
    assert document.fecha_emision == ISSUE_DATE
    assert prepared["payload"]["fechaEmision"] == "2026-10-06T23:45:00-05:00"
    assert "<cbc:IssueDate>2026-10-06</cbc:IssueDate>" in prepared["unsigned_xml"]
    assert prepared["payload"]["tipoDoc"] == tipo
    assert document.source_quote_id == quote.id
    assert document.total_venta == quote.total_venta == Decimal("118.00")
    db_session.refresh(quote)
    assert quote.fecha_emision == OLD_DATE
    assert quote.estado == "pendiente"
    # A later attempt must reuse the prepared document, never move its date.
    monkeypatch.setattr(fiscal_time, "now_lima", lambda: (ISSUE_DATE + timedelta(days=1)).replace(tzinfo=fiscal_time.LIMA_TZ))
    with patch.object(facturacion_service, "prepare_sale_document", side_effect=AssertionError("Rebuilt fiscal identity")):
        same_job, created = emission_queue_service.enqueue_fiscal_document_job(db_session, document, user, tipo_comprobante=tipo)
    assert not created and same_job.id == job.id
    assert same_job.payload_snapshot["prepared_sale"] == prepared
    assert document.fecha_emision == ISSUE_DATE


@pytest.mark.parametrize("tipo", ["01", "03"])
@pytest.mark.parametrize("explicit_installments", [False, True])
@pytest.mark.parametrize("due_offset", [-1, 0])
def test_stale_credit_is_rejected_before_creating_document_or_job(db_session, tipo, explicit_installments, due_offset):
    _, user, quote = _setup(db_session, tipo)
    quote.condicion_pago = "credito_15"
    quote.fecha_vencimiento = ISSUE_DATE + timedelta(days=due_offset)
    quote.cuotas_pago = [{"fecha_pago": quote.fecha_vencimiento.isoformat(), "monto": "118.00"}] if explicit_installments else None
    db_session.commit()
    with pytest.raises(HTTPException, match="Actualice los vencimientos") as exc:
        _emit(db_session, user, quote, tipo)
    assert exc.value.status_code == 400
    assert db_session.query(models.Cotizacion).filter_by(source_quote_id=quote.id).count() == 0
    assert db_session.query(models.DocumentEmissionJob).count() == 0
    # The low-level creator repeats the guard while holding the quotation lock.
    with pytest.raises(ValueError, match="Actualice los vencimientos"):
        crud.create_fiscal_document_from_quote(db_session, quote, user.id, tipo)
    assert db_session.query(models.Cotizacion).filter_by(source_quote_id=quote.id).count() == 0


@pytest.mark.parametrize("tipo", ["01", "03"])
def test_future_installments_keep_the_agreed_dates_and_amounts(db_session, tipo):
    _, user, quote = _setup(db_session, tipo)
    schedule = [{"fecha_pago": "2026-10-07T00:00:00+00:00", "monto": "59.00"},
                {"fecha_pago": "2026-10-21T00:00:00+00:00", "monto": "59.00"}]
    quote.condicion_pago = "credito_15"
    quote.fecha_vencimiento = datetime(2026, 10, 21)
    quote.cuotas_pago = schedule
    db_session.commit()
    response = _emit(db_session, user, quote, tipo)
    job = db_session.get(models.DocumentEmissionJob, json.loads(response.body)["job_id"])
    payload = job.payload_snapshot["prepared_sale"]["payload"]
    assert [row["fechaPago"][:10] for row in payload["cuotas"]] == ["2026-10-07", "2026-10-21"]
    assert [Decimal(str(row["monto"])) for row in payload["cuotas"]] == [Decimal("59.00")] * 2
    assert quote.cuotas_pago == schedule


@pytest.mark.parametrize("note_type,motive,mode", [("credito", "01", "full"), ("debito", "01", "charge")])
def test_old_note_draft_gets_its_own_date_only_on_first_emission(db_session, monkeypatch, note_type, motive, mode):
    tenant, user, quote = _setup(db_session, "01")
    source = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
    source.fecha_emision = OLD_DATE
    source.estado = "facturada"
    db_session.commit()
    payload = FiscalNoteDraftCreate(comprobante_afectado_id=source.id, tipo_nota=note_type,
        cod_motivo=motive, descripcion_motivo="Ajuste de prueba local", adjustment_mode=mode,
        input_value=Decimal("10") if note_type == "debito" else None)
    note, _ = note_adjustment_service.create_draft(db_session, tenant.id, user.id, payload, "local-date-note")
    note.fecha_emision = OLD_DATE
    db_session.commit()
    note, assigned = note_adjustment_service.assign_number_for_emission(db_session, tenant.id, note.id)
    assert assigned and note.fecha_emision == ISSUE_DATE
    assert source.fecha_emision == OLD_DATE
    monkeypatch.setattr(fiscal_time, "now_lima", lambda: (ISSUE_DATE + timedelta(days=1)).replace(tzinfo=fiscal_time.LIMA_TZ))
    same_note, assigned = note_adjustment_service.assign_number_for_emission(db_session, tenant.id, note.id)
    assert not assigned and same_note.fecha_emision == ISSUE_DATE
