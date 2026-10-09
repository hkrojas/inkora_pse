"""Synthetic cancellation lifecycle; never contacts Smart PSE or SUNAT."""
from datetime import datetime, timedelta, timezone
import json
from unittest.mock import Mock
from xml.etree import ElementTree as ET

import pytest

import crud
import fiscal_time
import models
import schemas
from services import emission_queue_service as queue, facturacion_service, void_recovery_service as recovery
from services import emission_leases, inventory_service
from test_emission_queue import _make_fiscal_document
from test_smartpse_response_normalization import _sale_cdr


def accepted_document(db, suffix="V001", kind="03"):
    tenant, user, document = _make_fiscal_document(db, suffix)
    subscription = crud.get_subscription_by_tenant(db, tenant.id)
    subscription.beta_feature_flags = {"voiding": True}
    document.tipo_comprobante = kind
    document.serie = "B001" if kind != "01" else "F001"
    document.estado = "facturada"
    document.sunat_xml_content = "<signed-document/>"
    document.sunat_cdr_content = _sale_cdr(document_id=f"{document.serie}-{document.correlativo}", ruc=tenant.business_ruc)
    document.provider_verification_status = "verified"
    document.provider_verified_at = datetime.now(timezone.utc).replace(tzinfo=None)
    document.fecha_emision = fiscal_time.now_lima_naive() - timedelta(days=2)
    db.commit()
    return tenant, user, document


def enqueue(db, user, document):
    return queue.enqueue_void_document_job(db, document, user, motivo="Documento no otorgado")[0]


def run_job(db, job):
    job.available_at = datetime.now() - timedelta(seconds=1)
    db.commit()
    assert crud.claim_next_emission_job(db).id == job.id
    return queue.process_emission_job(job.id, db_session=db)


def batch_cdr(job, ruc, code="0"):
    payload = job.payload_snapshot["void_payload"]
    return _sale_cdr(document_id=f"{payload['tipoDoc']}-{payload['correlativo']}", ruc=ruc, response_code=code)


def test_pending_batch_never_voids_or_reverses_inventory_then_accepts_once(db_session, monkeypatch):
    tenant, user, document = accepted_document(db_session)
    job = enqueue(db_session, user, document)
    client = Mock()
    client.process_xml.return_value = {"estado": 202, "ticket": "synthetic-ticket"}
    client.consult_ticket.return_value = {"cdr": batch_cdr(job, tenant.business_ruc), "estado": 200}
    monkeypatch.setattr(facturacion_service.smartpse_client, "get_default_client", lambda: client)
    original = crud.anular_cotizacion
    void = Mock(side_effect=original)
    monkeypatch.setattr(crud, "anular_cotizacion", void)
    assert run_job(db_session, job)
    db_session.refresh(document)
    db_session.refresh(job)
    assert document.estado == "facturada"
    assert job.status == "retry"
    void.assert_not_called()
    assert job.provider_ticket == "synthetic-ticket"
    frozen = job.payload_snapshot["void_filename"]
    assert run_job(db_session, job)
    db_session.refresh(document)
    db_session.refresh(job)
    assert document.estado == "anulada"
    assert job.status == "succeeded"
    assert job.payload_snapshot["void_result"]["cdr_xml"]
    assert client.process_xml.call_count == 1
    client.consult_ticket.assert_called_once_with(user.tenant, frozen, extra_payload={"environment": "demo"})
    assert void.call_count == 1
    assert enqueue(db_session, user, document).id == job.id


@pytest.mark.parametrize("first_error", [
    facturacion_service.FacturacionException("Timeout después de enviar"), RuntimeError("Unexpected parser failure")])
def test_uncertain_first_submission_only_queries_frozen_batch(db_session, monkeypatch, first_error):
    tenant, user, document = accepted_document(db_session)
    job = enqueue(db_session, user, document)
    send = Mock(side_effect=first_error)
    monkeypatch.setattr(facturacion_service, "_enviar_a_api", send)
    client = Mock()
    client.consult_ticket.return_value = {"cdr": batch_cdr(job, tenant.business_ruc)}
    monkeypatch.setattr(facturacion_service.smartpse_client, "get_default_client", lambda: client)
    assert run_job(db_session, job)
    assert document.estado == "facturada"
    assert job.payload_snapshot["void_send_started"] is True
    assert run_job(db_session, job)
    assert document.estado == "anulada"
    assert send.call_count == 1
    assert client.consult_ticket.call_count == 1


@pytest.mark.parametrize("kind", ["01", "03"])
@pytest.mark.parametrize("environment", ["demo", "produccion"])
def test_batch_consultation_selects_demo_explicitly_without_changing_production(db_session, monkeypatch, kind, environment):
    tenant, user, document = accepted_document(db_session, kind=kind)
    tenant.smartpse_environment = environment
    monkeypatch.setattr(facturacion_service.settings, "FISCAL_ENV", "beta" if environment == "demo" else "production")
    db_session.commit()
    job = enqueue(db_session, user, document)
    client = Mock()
    client.process_xml.return_value = {"estado": 202, "ticket": "synthetic-ticket"}
    client.consult_ticket.return_value = {"cdr": batch_cdr(job, tenant.business_ruc), "estado": 200}
    monkeypatch.setattr(facturacion_service.smartpse_client, "get_default_client", lambda: client)
    assert run_job(db_session, job)
    assert document.estado == "facturada" and job.status == "retry"
    assert run_job(db_session, job)
    expected_kwargs = {"extra_payload": {"environment": "demo"}} if environment == "demo" else {}
    client.consult_ticket.assert_called_once_with(user.tenant, job.payload_snapshot["void_filename"], **expected_kwargs)
    assert document.estado == "anulada" and job.status == "succeeded"
    assert client.process_xml.call_count == 1


@pytest.mark.parametrize("cdr", [None, "not-xml", "<Invoice/>", _sale_cdr(),
    _sale_cdr(document_id="RC-19000101-00001")])
def test_missing_or_wrong_cdr_keeps_sale_and_inventory_intact(db_session, monkeypatch, cdr):
    _, user, document = accepted_document(db_session)
    job = enqueue(db_session, user, document)
    monkeypatch.setattr(facturacion_service, "_enviar_a_api", Mock(return_value={"success": True, "cdr_xml": cdr}))
    assert run_job(db_session, job)
    db_session.refresh(job)
    assert job.status == "retry"
    assert document.estado == "facturada"
    assert db_session.query(models.InventoryMovement).filter_by(movement_type="void_reversal").count() == 0


def test_wrong_issuer_cdr_is_not_acceptance(db_session, monkeypatch):
    _, user, document = accepted_document(db_session)
    job = enqueue(db_session, user, document)
    monkeypatch.setattr(facturacion_service, "_enviar_a_api", Mock(return_value={"cdr_xml": batch_cdr(job, "20999999999")}))
    assert run_job(db_session, job)
    assert job.status == "retry"
    assert document.estado == "facturada"


def test_matching_rejection_is_terminal_without_stock_reversal(db_session, monkeypatch):
    tenant, user, document = accepted_document(db_session)
    job = enqueue(db_session, user, document)
    send = Mock(return_value={"cdr_xml": batch_cdr(job, tenant.business_ruc, "2335")})
    monkeypatch.setattr(facturacion_service, "_enviar_a_api", send)
    assert run_job(db_session, job) is False
    assert job.status == "failed"
    assert document.estado == "facturada"
    assert job.payload_snapshot["void_result"]["cdr_xml"]
    assert enqueue(db_session, user, document).id == job.id
    assert send.call_count == 1


def test_batch_dates_use_original_issue_day_and_current_generation_day(db_session):
    _, user, document = accepted_document(db_session)
    job = enqueue(db_session, user, document)
    root = ET.fromstring(job.payload_snapshot["void_xml"])
    ns = {"cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"}
    assert root.findtext("cbc:ReferenceDate", namespaces=ns) == document.fecha_emision.date().isoformat()
    assert root.findtext("cbc:IssueDate", namespaces=ns) == fiscal_time.today_lima().isoformat()
    assert fiscal_time.today_lima().strftime("%Y%m%d") in job.payload_snapshot["void_filename"]


@pytest.mark.parametrize("kind", ["07", "08"])
def test_boleta_notes_include_original_boleta_reference(db_session, kind):
    tenant, user, original = accepted_document(db_session)
    _, _, note = accepted_document(db_session, suffix="V002", kind=kind)
    note.tenant_id = tenant.id
    note.serie = "BC01" if kind == "07" else "BD01"
    note.document_kind = "credit_note" if kind == "07" else "debit_note"
    note.nota_referencia_id = original.id
    note.sunat_cdr_content = _sale_cdr(document_id=f"{note.serie}-{note.correlativo}", ruc=tenant.business_ruc)
    db_session.commit()
    job = enqueue(db_session, user, note)
    root = ET.fromstring(job.payload_snapshot["void_xml"])
    ns = {"cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
          "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"}
    assert root.findtext(".//cac:InvoiceDocumentReference/cbc:ID", namespaces=ns) == f"{original.serie}-{str(original.correlativo).zfill(6)}"
    assert root.findtext(".//cac:InvoiceDocumentReference/cbc:DocumentTypeCode", namespaces=ns) == "03"


@pytest.mark.parametrize("invalid", ["expired", "future", "missing_reception", "not_accepted", "other_tenant"])
def test_invalid_cancellation_never_creates_job(db_session, invalid):
    _, user, document = accepted_document(db_session)
    if invalid == "expired": document.provider_verified_at -= timedelta(days=8)
    if invalid == "future": document.fecha_emision += timedelta(days=5)
    if invalid == "missing_reception": document.provider_verified_at = None
    if invalid == "not_accepted": document.provider_verification_status = "pending_confirmation"
    if invalid == "other_tenant":
        _, user, _ = accepted_document(db_session, suffix="V003")
    db_session.commit()
    with pytest.raises(ValueError):
        enqueue(db_session, user, document)
    db_session.rollback()
    assert db_session.query(models.DocumentEmissionJob).count() == 0


def test_duplicate_requests_keep_identity_reason_and_evidence(db_session):
    _, user, document = accepted_document(db_session)
    first = enqueue(db_session, user, document)
    second, created = queue.enqueue_void_document_job(db_session, document, user, motivo="Otro motivo")
    assert first.id == second.id and not created
    assert second.payload_snapshot["motivo"] == "Documento no otorgado"
    assert db_session.query(models.DocumentEmissionJob).count() == 1


def test_api_requires_explicit_not_delivered_confirmation_even_in_sync_mode(db_session):
    from fastapi import HTTPException
    from starlette.requests import Request
    from routers.facturacion import anular_documento
    _, user, document = accepted_document(db_session)
    action = getattr(anular_documento, "__wrapped__", anular_documento)
    with pytest.raises(HTTPException) as error:
        action(Request({"type": "http"}), schemas.AnulacionCreate(comprobante_id=document.id, motivo="Error"), db_session, user, user, "sync")
    assert error.value.status_code == 400
    result = action(Request({"type": "http"}), schemas.AnulacionCreate(comprobante_id=document.id, motivo="Error", confirmed_not_delivered=True), db_session, user, user, "sync")
    response = json.loads(result.body)
    assert result.status_code == 202 and response["queued"] is True and response["job_id"]
    assert document.estado == "facturada"


def test_recovery_of_expired_execution_queries_instead_of_resending(db_session, monkeypatch):
    tenant, user, document = accepted_document(db_session)
    job = enqueue(db_session, user, document)
    snapshot = dict(job.payload_snapshot, void_send_started=True)
    job.payload_snapshot = snapshot
    job.status = "processing"
    job.execution_started_at = datetime.now() - timedelta(minutes=10)
    job.lease_token = "expired"
    job.lease_expires_at = datetime.now() - timedelta(seconds=1)
    job.attempts = job.max_attempts
    db_session.commit()
    assert emission_leases.recover(db_session) == 1
    assert job.status == "retry"
    client = Mock()
    client.consult_ticket.return_value = {"cdr": batch_cdr(job, tenant.business_ruc)}
    monkeypatch.setattr(facturacion_service.smartpse_client, "get_default_client", lambda: client)
    # Legacy test claim does not issue a lease; relinquish the expired token.
    job.lease_token = None
    db_session.commit()
    assert run_job(db_session, job)
    client.process_xml.assert_not_called()
    assert document.estado == "anulada"


def test_accepted_cancellation_reverses_actual_sale_stock_only_once(db_session, monkeypatch):
    from test_inventory import _activate, _inventory_product
    from conftest import make_producto
    tenant, user, document = accepted_document(db_session)
    warehouse = _activate(db_session, tenant)
    product = make_producto(db_session, tenant, "VOIDS")
    _inventory_product(db_session, tenant, product, warehouse, user, stock="10")
    balance = inventory_service._balance(db_session, tenant.id, warehouse.id, product.id)
    inventory_service._record_movement(db_session, balance, -2, "sale_out", "fiscal_document", document.id, 1, user.id, "Synthetic sale", "synthetic-sale")
    db_session.commit()
    job = enqueue(db_session, user, document)
    monkeypatch.setattr(facturacion_service, "_enviar_a_api", Mock(return_value={"cdr_xml": batch_cdr(job, tenant.business_ruc)}))
    assert run_job(db_session, job)
    assert balance.on_hand == 10
    assert db_session.query(models.InventoryMovement).filter_by(movement_type="void_reversal").count() == 1
    crud.anular_cotizacion(db_session, document.id, tenant_id=tenant.id)
    assert balance.on_hand == 10
    assert db_session.query(models.InventoryMovement).filter_by(movement_type="void_reversal").count() == 1


def test_manual_summary_cannot_reuse_automatic_void_identity(db_session):
    _, user, document = accepted_document(db_session)
    job = enqueue(db_session, user, document)
    with pytest.raises(ValueError, match="registrado o reservado"):
        recovery.ensure_manual_batch_available(db_session, user.tenant_id, job.payload_snapshot["void_payload"])


@pytest.mark.parametrize("previous", ["automatic", "manual"])
def test_manual_summary_cannot_bypass_reserved_counter_by_removing_zeroes(db_session, previous):
    _, user, document = accepted_document(db_session)
    job = enqueue(db_session, user, document)
    payload = dict(job.payload_snapshot["void_payload"])
    if previous == "manual":
        crud.create_resumen_diario(db_session, tenant_id=user.tenant_id, usuario_id=user.id,
            payload=dict(payload, fecResumen=payload["fecResumen"], fecGeneracion=payload["fecGeneracion"]))
        db_session.delete(job)
        db_session.commit()
    day, number = payload["correlativo"].split("-")
    payload["correlativo"] = f"{day}-{int(number)}"
    with pytest.raises(ValueError, match="registrado o reservado"):
        recovery.ensure_manual_batch_available(db_session, user.tenant_id, payload)


def test_boleta_note_with_inventory_impact_requires_manual_reconciliation(db_session):
    _, user, document = accepted_document(db_session, kind="07")
    document.inventory_impact = "physical_return"
    db_session.commit()
    with pytest.raises(ValueError, match="inventario"):
        enqueue(db_session, user, document)


def test_notes_cannot_be_created_or_numbered_while_source_void_is_pending(db_session):
    from services import note_adjustment_service as notes
    from test_notes_v2 import _payload
    _, user, document = accepted_document(db_session, kind="01")
    payload = _payload(document)
    draft, _ = notes.create_draft(db_session, user.tenant_id, user.id, payload, "before-void")
    enqueue(db_session, user, document)
    with pytest.raises(ValueError, match="baja pendiente"):
        notes.assign_number_for_emission(db_session, user.tenant_id, draft.id)
    db_session.rollback()
    with pytest.raises(ValueError, match="baja pendiente"):
        notes.create_draft(db_session, user.tenant_id, user.id, payload, "after-void")
    db_session.rollback()
    with pytest.raises(ValueError, match="baja pendiente"):
        crud.crear_nota_credito_debito(db_session, document, user.id, "debito", "02", "Aumento")
    assert draft.correlativo is None


def test_source_void_is_blocked_until_linked_notes_are_resolved(db_session):
    _, user, document = accepted_document(db_session)
    note = crud.crear_nota_credito_debito(db_session, document, user.id, "debito", "02", "Aumento")
    with pytest.raises(ValueError, match="notas pendientes"):
        enqueue(db_session, user, document)
    db_session.rollback()
    note.estado = "anulada"
    db_session.commit()
    assert enqueue(db_session, user, document).id


@pytest.mark.parametrize("definitive", [False, True])
def test_failed_void_with_possible_submission_blocks_notes_unless_matching_rejection(db_session, definitive):
    from services.sale_dispatch_service import _void_job_pending
    tenant, user, document = accepted_document(db_session)
    job = enqueue(db_session, user, document)
    job.status = "failed"
    result = {"cdr_xml": batch_cdr(job, tenant.business_ruc, "2335")} if definitive else {}
    job.payload_snapshot = dict(job.payload_snapshot, void_send_started=True, void_result=result)
    db_session.commit()
    if definitive:
        recovery.ensure_note_source_available(db_session, document)
        assert not _void_job_pending(db_session, document)
    else:
        with pytest.raises(ValueError, match="baja pendiente"):
            recovery.ensure_note_source_available(db_session, document)
        assert _void_job_pending(db_session, document)


def test_missing_original_issue_date_requires_reconciliation(db_session):
    _, user, document = accepted_document(db_session)
    document.fecha_emision = None
    db_session.commit()
    with pytest.raises(ValueError, match="fecha de emisión original"):
        enqueue(db_session, user, document)


def test_failed_historical_void_without_submission_fence_requires_reconciliation_before_notes(db_session):
    from services.sale_dispatch_service import _void_job_pending
    _, user, document = accepted_document(db_session)
    job = enqueue(db_session, user, document)
    job.status = "failed"
    job.payload_snapshot = {"motivo": "Baja histórica con resultado desconocido"}
    db_session.commit()
    with pytest.raises(ValueError, match="baja pendiente"):
        recovery.ensure_note_source_available(db_session, document)
    assert _void_job_pending(db_session, document)
