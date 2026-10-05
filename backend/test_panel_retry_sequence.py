"""Offline worker retries require a confirmed outcome and a completed cooldown."""
from datetime import datetime, timedelta

import pytest

import models
from services import emission_leases as leases
from services import emission_queue_service as queue
from services import fiscal_recovery_service as recovery
from services import smartpse_panel_client as panel_service
from test_emission_queue import _make_fiscal_document
from test_panel_retry_worker import pending_sale, run, sale, sign_xml  # noqa: F401
from test_smartpse_response_normalization import _sale_cdr


def confirmed_failure(response=None):
    return dict(response or {}, panel_retry_attempted=True,
        panel_retry_status="confirmed_transient_failure", provider_status_code=200,
        panel_retry_outcome={"source": "retry_response", "response_sha256": "a" * 64,
                             "message": "HTTP 503 Service Unavailable"})


def install_confirmed_failures(panel):
    acknowledged = panel.retry_invoice.side_effect

    def fail(*args, **kwargs):
        response = acknowledged(*args, **kwargs)
        if response.get("panel_retry_attempted") is not True:
            return response
        return confirmed_failure(response)

    panel.retry_invoice.side_effect = fail
    return acknowledged


def test_confirmed_failures_wait_then_lost_third_response_blocks_repetition(
        db_session, pending_sale, monkeypatch):
    tenant, _, document, job, xml, client, panel, _, attempts = pending_sale
    clock = [datetime.now()]
    monkeypatch.setattr(leases, "db_now", lambda db: clock[0])
    acknowledged = install_confirmed_failures(panel)
    other_tenant, other_user, other_document = _make_fiscal_document(db_session, "SEQUENCE_OTHER")
    other_job, _ = queue.enqueue_fiscal_document_job(
        db_session, other_document, other_user, tipo_comprobante="01")
    other_job.payload_snapshot = dict(other_job.payload_snapshot, signed_ready=True)
    other_available_at = clock[0] + timedelta(days=1)
    other_job.available_at = other_available_at
    db_session.commit()

    assert not run(db_session, job)
    first = dict(job.payload_snapshot["panel_retry_attempt"])
    assert len(attempts) == 1 and first["state"] == "confirmed_transient_failure"
    assert first["sequence"] == 1 and first["previous_attempt_id"] is None
    first_due = datetime.fromisoformat(first["next_retry_at"])
    assert first_due - datetime.fromisoformat(first["completed_at"]) == timedelta(seconds=900)

    # Force a worker consultation before the delay: it must not make a POST.
    clock[0] = first_due - timedelta(seconds=1)
    assert not run(db_session, job)
    assert len(attempts) == 1 and panel.retry_invoice.call_count == 1
    assert job.payload_snapshot["panel_retry_attempt"] == first
    clock[0] = first_due
    assert not run(db_session, job)
    second = dict(job.payload_snapshot["panel_retry_attempt"])
    assert len(attempts) == 2 and second["state"] == "confirmed_transient_failure"
    assert second["sequence"] == 2 and second["previous_attempt_id"] == first["id"]
    second_due = datetime.fromisoformat(second["next_retry_at"])
    assert second_due - datetime.fromisoformat(second["completed_at"]) == timedelta(seconds=1800)
    clock[0] = second_due - timedelta(seconds=1)
    assert not run(db_session, job)
    assert len(attempts) == 2 and panel.retry_invoice.call_count == 2

    def lose(*args, **kwargs):
        response = acknowledged(*args, **kwargs)
        response["panel_retry_status"] = "ambiguous"
        raise panel_service.SmartPSEPanelRetryException("Respuesta perdida", response)

    panel.retry_invoice.side_effect = lose
    clock[0] = second_due
    assert not run(db_session, job)
    third = dict(job.payload_snapshot["panel_retry_attempt"])
    assert len(attempts) == 3 and third["state"] == "possible_submission"
    assert third["sequence"] == 3 and third["previous_attempt_id"] == second["id"]
    assert "completed_at" not in third
    clock[0] += timedelta(hours=1)
    assert not run(db_session, job)
    assert len(attempts) == 3 and panel.retry_invoice.call_count == 3
    assert job.payload_snapshot["panel_retry_attempt"] == third
    assert document.provider_response["inkora_evidence"]["panel_retry_attempt"] == third
    assert db_session.query(models.AuditLog).filter_by(
        action="fiscal_panel_retry_started", entity_id=document.id).count() == 3
    assert db_session.query(models.AuditLog).filter_by(
        action="fiscal_panel_retry_completed", entity_id=document.id).count() == 2
    circuit = db_session.get(models.FiscalProviderCircuit, recovery.scope_for(tenant))
    assert circuit.failures == 0
    # The shared run helper deliberately sets a past probe date before each
    # forced consultation. A panel error must not move it into the future.
    assert circuit.next_probe_at is None or circuit.next_probe_at < datetime.now()
    db_session.refresh(other_job)
    assert other_tenant.id != tenant.id and other_job.available_at == other_available_at
    assert document.estado == "pendiente" and document.sunat_xml_content == xml
    assert tenant.subscription.documents_used == 0
    client.sign_xml.assert_not_called()
    client.send_signed_xml.assert_not_called()


@pytest.mark.parametrize("cdr_source", ["api", "panel"])
def test_matching_cdr_prevents_due_repeated_post(db_session, pending_sale, monkeypatch, cdr_source):
    tenant, _, document, job, xml, client, panel, _, attempts = pending_sale
    clock = [datetime.now()]
    monkeypatch.setattr(leases, "db_now", lambda db: clock[0])
    install_confirmed_failures(panel)
    assert not run(db_session, job)
    first = dict(job.payload_snapshot["panel_retry_attempt"])
    clock[0] = datetime.fromisoformat(first["next_retry_at"]) + timedelta(seconds=1)
    cdr = _sale_cdr(document_id=f"{document.serie}-{document.correlativo}", ruc=tenant.business_ruc)
    response = {"estado": 200, "cdr": cdr, "xml_firmado": xml}
    if cdr_source == "api":
        client.consult_ticket.return_value = response
    else:
        panel.recover_invoice.return_value = dict(response, recovery_source="smartpse_panel")
    assert run(db_session, job)
    assert len(attempts) == 1 and panel.retry_invoice.call_count == 1
    assert job.status == "succeeded" and document.sunat_accepted
    assert document.estado == "facturada" and document.sunat_xml_content == xml
    assert tenant.subscription.documents_used == 1
    assert document.provider_response["inkora_evidence"]["panel_retry_attempt"] == first
    assert db_session.query(models.AuditLog).filter_by(
        action="fiscal_panel_retry_started", entity_id=document.id).count() == 1
    client.sign_xml.assert_not_called()
    client.send_signed_xml.assert_not_called()
