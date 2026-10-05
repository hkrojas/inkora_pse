"""Offline worker panel retry: one durable attempt, then CDR reconciliation only."""
import hashlib
from copy import deepcopy
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

import crud
import models
from config import settings
from services import emission_leases as leases
from services import emission_queue_service as queue
from services import facturacion_service, fiscal_evidence_service as evidence
from services import fiscal_recovery_service as recovery, fiscal_submission_state as submission
from services import smartpse_client, smartpse_panel_client as panel_service
from services import smartpse_response
from test_fiscal_contingency_recovery import sale, sign_xml
from test_emission_queue import _make_fiscal_document
from test_smartpse_response_normalization import _sale_cdr


@pytest.fixture
def pending_sale(db_session, sale, sign_xml, monkeypatch):
    tenant, user, document, job = sale
    prepared = job.payload_snapshot["prepared_sale"]
    xml = sign_xml(prepared["unsigned_xml"])
    assert evidence.retain_sale_evidence(db_session, document, {"xml_firmado": xml}, payload=prepared["payload"])
    job.payload_snapshot = dict(submission.mark_possible(job.payload_snapshot), recovery_flow=True, signed_ready=True)
    job.action = models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    db_session.commit()
    monkeypatch.setattr(settings, "SMARTPSE_PANEL_RETRY_TENANT_IDS", str(tenant.id))
    monkeypatch.setattr(settings, "SMARTPSE_PANEL_RECOVERY_TENANT_IDS", str(tenant.id))
    client, panel = Mock(), Mock()
    client.consult_ticket.return_value = {"estado": 202, "pending": True}
    panel.recover_invoice.return_value = {"estado": 202, "pending": True, "recovery_source": "smartpse_panel"}
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    monkeypatch.setattr(panel_service, "get_default_client", lambda: panel)
    metadata = {"provider_document_id": "444951", "provider_company_id": "77", "environment": "demo",
        "xml_sha256": hashlib.sha256(xml.encode()).hexdigest(), "state": "error",
        "provider_error_message": "HTTP 503 Service Unavailable", "provider_xml_hash": None}
    attempts = []
    def retry(*args, **kwargs):
        assert not db_session.in_transaction(), "panel listing/XML must not hold a transaction"
        assert kwargs["expected_xml"] == xml
        authorized = kwargs["before_submit"](metadata)
        assert not db_session.in_transaction(), "panel POST must follow the durable commit"
        if authorized is not True:
            return {"panel_retry_attempted": False, "panel_retry_status": "blocked"}
        attempts.append(dict(metadata))
        # This acknowledgment deliberately contains ok=True and no acceptance CDR.
        return {"estado": 202, "pending": True, "cdr": None, "ok": True,
            "recovery_source": "smartpse_panel", "panel_retry_attempted": True,
            "panel_retry_status": "response_received"}
    panel.retry_invoice.side_effect = retry
    return tenant, user, document, job, xml, client, panel, metadata, attempts


def run(db, job):
    job_id = job.id
    job.available_at = datetime.now() - timedelta(seconds=1)
    circuit = db.get(models.FiscalProviderCircuit, recovery.scope_for(db.get(models.Tenant, job.tenant_id)))
    if circuit:
        circuit.next_probe_at = datetime.now() - timedelta(seconds=1)
        circuit.probe_token = circuit.probe_expires_at = None
    db.commit()
    reservation = leases.claim(db, owner="offline-panel", lease_seconds=300, global_limit=10, tenant_limit=10)
    assert reservation and reservation[0] == job_id
    return queue.process_emission_job(job_id, db_session=db, lease_token=reservation[1])


def reserve(db, job, user, xml, metadata):
    job_id, user_id = job.id, user.id
    db.commit()
    claimed = leases.claim(db, owner="offline-panel", lease_seconds=300, global_limit=10, tenant_limit=10)
    assert claimed and claimed[0] == job_id
    leases.attach(db, *claimed)
    try:
        return queue._reserve_panel_retry_attempt(db, job_id, user_id, xml, metadata)
    finally:
        leases.detach(db)


def test_panel_ack_stays_pending_until_matching_cdr(db_session, pending_sale):
    tenant, _, document, job, xml, client, panel, _, attempts = pending_sale
    assert not run(db_session, job)
    assert len(attempts) == 1
    assert job.status == "retry" and job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    assert document.estado == "pendiente" and not document.sunat_accepted
    assert document.sunat_xml_content == xml
    assert tenant.subscription.documents_used == 0
    marker = job.payload_snapshot["panel_retry_attempt"]
    assert marker == document.provider_response["inkora_evidence"]["panel_retry_attempt"]
    assert db_session.query(models.AuditLog).filter_by(action="fiscal_panel_retry_started", entity_id=document.id).count() == 1
    client.consult_ticket.return_value = {"estado": 200,
        "cdr": _sale_cdr(document_id=f"{document.serie}-{document.correlativo}", ruc=tenant.business_ruc)}
    assert run(db_session, job)
    assert document.estado == "facturada" and document.sunat_accepted
    assert document.sunat_xml_content == xml
    assert tenant.subscription.documents_used == 1
    assert document.provider_response["inkora_evidence"]["panel_retry_attempt"] == marker
    panel.retry_invoice.assert_called_once()
    client.sign_xml.assert_not_called()
    client.send_signed_xml.assert_not_called()


def test_demo_observed_2074_body_estado_500_is_not_http_outage(db_session, pending_sale):
    """FERR-1 observed HTTP 200, estado 500, rejected without CDR (2074).

    The provider's exact message was discarded; this test reconstructs that
    observed shape. Missing CDR remains consultation-only, not acceptance.
    """
    tenant, _, document, job, xml, client, panel, metadata, attempts = pending_sale
    client.consult_ticket.return_value = {
        "estado": 500, "rechazado": True, "cdr": None, "ticket": None,
        "errores": ["[2074] UBLVersionID no valido"], "observaciones": None,
        "mensaje": "Rechazo de validacion [2074]",
    }
    metadata.update(state="rechazado", provider_error_message="[2074] UBLVersionID no valido")
    assert not run(db_session, job)
    assert not attempts
    assert "panel_retry_attempt" not in job.payload_snapshot
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    assert document.estado == "pendiente" and not document.sunat_accepted
    assert document.sunat_xml_content == xml and tenant.subscription.documents_used == 0
    circuit = db_session.get(models.FiscalProviderCircuit, recovery.scope_for(tenant))
    assert circuit.failures == 0 and circuit.next_probe_at is None
    client.sign_xml.assert_not_called()
    client.send_signed_xml.assert_not_called()


def test_lost_panel_response_never_allows_second_attempt(db_session, pending_sale):
    tenant, _, document, job, xml, client, panel, _, attempts = pending_sale
    acknowledged = panel.retry_invoice.side_effect
    def lose(*args, **kwargs):
        result = acknowledged(*args, **kwargs)
        result["panel_retry_status"] = "ambiguous"
        raise panel_service.SmartPSEPanelRetryException("Respuesta perdida", result)
    panel.retry_invoice.side_effect = lose
    assert not run(db_session, job)
    assert len(attempts) == 1
    marker = job.payload_snapshot["panel_retry_attempt"]
    assert db_session.get(models.FiscalProviderCircuit, recovery.scope_for(tenant)).failures == 0
    assert not run(db_session, job)
    assert len(attempts) == 1 and panel.retry_invoice.call_count == 1
    assert client.consult_ticket.call_count == 2
    assert job.payload_snapshot["panel_retry_attempt"] == marker
    assert document.sunat_xml_content == xml and document.estado == "pendiente"
    assert tenant.subscription.documents_used == 0
    client.sign_xml.assert_not_called()
    client.send_signed_xml.assert_not_called()


@pytest.mark.parametrize("panel_status", [None, 401, 403, 419, 422, 429, 500, 503])
@pytest.mark.parametrize("api_failed", [False, True])
def test_panel_failure_only_preserves_independent_api_outage(db_session, pending_sale, panel_status, api_failed):
    tenant, _, document, job, xml, client, panel, _, attempts = pending_sale
    other_tenant, other_user, other_document = _make_fiscal_document(db_session, "PANEL_OTHER")
    other_job, _ = queue.enqueue_fiscal_document_job(db_session, other_document, other_user, tipo_comprobante="01")
    other_job.payload_snapshot = dict(other_job.payload_snapshot, signed_ready=True)
    other_available_at = datetime.now() + timedelta(minutes=5)
    other_job.available_at = other_available_at
    db_session.commit()
    if api_failed:
        client.consult_ticket.side_effect = smartpse_client.SmartPSEException(
            "API service unavailable", {}, status_code=503)
    acknowledged = panel.retry_invoice.side_effect

    def fail_panel(*args, **kwargs):
        result = acknowledged(*args, **kwargs)
        result.update(panel_retry_status="ambiguous", provider_status_code=panel_status)
        # HTTP 429 is raised before the panel client populates the response status.
        if panel_status == 429:
            result["provider_status_code"] = None
        raise panel_service.SmartPSEPanelRetryException("Panel requiere conciliacion", result, status_code=panel_status)

    panel.retry_invoice.side_effect = fail_panel
    assert not run(db_session, job)
    assert len(attempts) == 1
    assert "panel_retry_attempt" in job.payload_snapshot
    assert job.status == "retry" and job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    assert document.estado == "pendiente" and document.sunat_xml_content == xml
    assert tenant.subscription.documents_used == 0
    circuit = db_session.get(models.FiscalProviderCircuit, recovery.scope_for(tenant))
    assert circuit.failures == int(api_failed)
    db_session.refresh(other_job)
    assert other_tenant.id != tenant.id
    if api_failed:
        assert circuit.next_probe_at is not None and other_job.available_at > other_available_at
    else:
        assert circuit.next_probe_at is None and other_job.available_at == other_available_at
    client.sign_xml.assert_not_called()
    client.send_signed_xml.assert_not_called()


def test_cdr_discovered_by_panel_accepts_without_retry_marker(db_session, pending_sale):
    tenant, _, document, job, xml, _, panel, _, attempts = pending_sale
    panel.retry_invoice.side_effect = None
    panel.retry_invoice.return_value = {"estado": 200, "recovery_source": "smartpse_panel",
        "panel_retry_attempted": False, "panel_retry_status": "cdr_available",
        "cdr": _sale_cdr(document_id=f"{document.serie}-{document.correlativo}", ruc=tenant.business_ruc)}
    assert run(db_session, job)
    assert document.estado == "facturada" and tenant.subscription.documents_used == 1
    assert document.sunat_xml_content == xml and not attempts
    assert "panel_retry_attempt" not in job.payload_snapshot
    assert db_session.query(models.AuditLog).filter_by(action="fiscal_panel_retry_started").count() == 0


@pytest.mark.parametrize("setting", ["SMARTPSE_PANEL_RETRY_TENANT_IDS", "SMARTPSE_PANEL_RECOVERY_TENANT_IDS", "FISCAL_CONTINGENCY_TENANT_IDS"])
def test_every_current_rollout_required(db_session, pending_sale, monkeypatch, setting):
    _, _, document, job, _, client, panel, _, attempts = pending_sale
    monkeypatch.setattr(settings, setting, "")
    assert not run(db_session, job)
    panel.retry_invoice.assert_not_called()
    client.consult_ticket.assert_called_once()
    assert not attempts and document.estado == "pendiente"


@pytest.mark.parametrize("blocked", ["user", "tenant", "role", "subscription", "manual_pause"])
def test_post_permissions_do_not_block_cdr_consultation(db_session, pending_sale, blocked):
    tenant, user, document, job, _, client, panel, _, attempts = pending_sale
    if blocked == "user":
        user.is_active = False
    elif blocked == "tenant":
        tenant.is_active = False
    elif blocked == "role":
        user.rol = "vendedor"
    elif blocked == "subscription":
        tenant.subscription.status = "suspended"
    else:
        tenant.fiscal_contingency_mode = True
    db_session.commit()
    assert not run(db_session, job)
    client.consult_ticket.assert_called_once()
    assert not attempts and "panel_retry_attempt" not in job.payload_snapshot
    assert document.estado == "pendiente"


@pytest.mark.parametrize("alteration", ["version", "phase", "environment", "xml", "company_list", "nonfiscal", "boleta", "resource"])
def test_only_frozen_invoice_contract_allows_retry(db_session, pending_sale, alteration):
    tenant, _, document, job, xml, _, _, metadata, attempts = pending_sale
    snapshot = dict(job.payload_snapshot)
    if alteration == "version":
        snapshot["submission_state_version"] = True
        snapshot["malformed_contract"] = True  # JSON bool and int compare equal in Python.
    elif alteration == "phase":
        snapshot["submission_phase"] = "unknown"
    elif alteration == "environment":
        tenant.smartpse_environment = "produccion"
    elif alteration == "xml":
        document.sunat_xml_content = xml.replace(">01</cbc:InvoiceTypeCode>", ">03</cbc:InvoiceTypeCode>")
        assert document.sunat_xml_content != xml
    elif alteration == "company_list":
        prepared = dict(snapshot["prepared_sale"])
        prepared["payload"] = dict(prepared["payload"], company=["not a company"])
        snapshot["prepared_sale"] = prepared
    elif alteration == "nonfiscal":
        document.document_kind = "quote"
    elif alteration == "boleta":
        document.tipo_comprobante = "03"
    else:
        job.resource_type = models.EMISSION_JOB_RESOURCE_GUIA
    job.payload_snapshot = snapshot
    db_session.commit()
    assert reserve(db_session, job, pending_sale[1], xml, metadata) is False
    assert not attempts and "panel_retry_attempt" not in job.payload_snapshot


@pytest.mark.parametrize("accepted_evidence", ["accepted", "cdr", "rejected"])
def test_prior_fiscal_result_never_authorizes_retry(db_session, pending_sale, accepted_evidence):
    tenant, user, document, job, xml, _, _, metadata, _ = pending_sale
    if accepted_evidence == "accepted":
        document.estado = "facturada"
    elif accepted_evidence == "cdr":
        document.sunat_cdr_content = _sale_cdr(document_id=f"{document.serie}-{document.correlativo}", ruc=tenant.business_ruc)
    else:
        document.provider_verification_status = "rejected"
    db_session.commit()
    assert reserve(db_session, job, user, xml, metadata) is False
    assert "panel_retry_attempt" not in job.payload_snapshot


def test_expired_invoice_alerts_once_and_continues_only_consultation(db_session, pending_sale):
    _, _, document, job, _, client, panel, _, attempts = pending_sale
    document.fecha_emision = datetime.now() - timedelta(days=8)
    db_session.commit()
    assert not run(db_session, job)
    assert not run(db_session, job)
    assert client.consult_ticket.call_count == 2
    panel.retry_invoice.assert_not_called()
    assert not attempts
    assert db_session.query(models.AuditLog).filter_by(action="fiscal_recovery_deadline", entity_id=document.id).count() == 1


@pytest.mark.parametrize("where", ["other_job", "audit", "document"])
def test_marker_survives_job_and_provider_response_replacement(db_session, pending_sale, where):
    tenant, user, document, job, _, client, panel, _, attempts = pending_sale
    if where == "other_job":
        old_job = models.DocumentEmissionJob(tenant_id=tenant.id, created_by_user_id=user.id,
            resource_type="cotizacion", resource_id=document.id, action="consult_fiscal_document",
            provider="smartpse", status="failed", idempotency_key=f"previous:{job.id}",
            payload_snapshot={"panel_retry_attempt": {"id": "prior"}})
        db_session.add(old_job)
    elif where == "audit":
        db_session.add(models.AuditLog(user_id=user.id, action="fiscal_panel_retry_started", entity_type="cotizacion", entity_id=document.id))
    else:
        document.provider_response = dict(document.provider_response,
            inkora_evidence=dict(document.provider_response["inkora_evidence"], panel_retry_attempt={"id": "prior"}))
    db_session.commit()
    assert not run(db_session, job)
    panel.retry_invoice.assert_not_called()
    client.consult_ticket.assert_called_once()
    assert not attempts and document.estado == "pendiente"


def test_legacy_unfenced_consultation_cannot_retry(db_session, pending_sale):
    _, _, _, job, _, client, panel, _, attempts = pending_sale
    crud.claim_next_emission_job(db_session)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    client.consult_ticket.assert_called_once()
    panel.retry_invoice.assert_not_called()
    assert not attempts


def test_expired_fence_vetoes_before_marker(db_session, pending_sale):
    _, user, document, job, xml, _, _, metadata, _ = pending_sale
    job_id, user_id = job.id, user.id
    claimed = leases.claim(db_session, owner="offline-panel", lease_seconds=300, global_limit=10, tenant_limit=10)
    assert claimed[0] == job_id
    job.lease_expires_at = datetime.now() - timedelta(seconds=1)
    db_session.commit()
    leases.attach(db_session, *claimed)
    try:
        with pytest.raises(leases.LeaseLost):
            queue._reserve_panel_retry_attempt(db_session, job_id, user_id, xml, metadata)
    finally:
        db_session.rollback()
        leases.detach(db_session)
    assert "panel_retry_attempt" not in job.payload_snapshot
    assert db_session.query(models.AuditLog).filter_by(action="fiscal_panel_retry_started", entity_id=document.id).count() == 0


def test_shared_cpe_pause_vetoes_panel_post(db_session, pending_sale):
    tenant, user, document, job, xml, _, _, metadata, _ = pending_sale
    recovery.service_failed(db_session, tenant)
    job.available_at = datetime.now() - timedelta(seconds=1)
    db_session.commit()
    assert reserve(db_session, job, user, xml, metadata) is False
    assert not db_session.in_transaction()
    assert "panel_retry_attempt" not in job.payload_snapshot


def test_permissions_are_reloaded_after_circuit_reservation(db_session, pending_sale, monkeypatch):
    _, user, _, job, xml, _, _, metadata, _ = pending_sale
    original = recovery.reserve_probe
    def deactivate(db, tenant, **kwargs):
        result = original(db, tenant, **kwargs)
        # SQL bypasses the populated ORM user; the locked re-read must see it.
        db.execute(models.User.__table__.update().where(models.User.id == user.id).values(is_active=False))
        db.commit()
        return result
    monkeypatch.setattr(recovery, "reserve_probe", deactivate)
    assert reserve(db_session, job, user, xml, metadata) is False
    assert "panel_retry_attempt" not in job.payload_snapshot


def test_company_changed_during_panel_prefetch_vetoes_post(db_session, pending_sale):
    tenant, _, document, job, _, client, panel, metadata, attempts = pending_sale
    original = panel.retry_invoice.side_effect
    def change_company(*args, **kwargs):
        assert not db_session.in_transaction()
        # The panel request still refers to company 77, but the current tenant does not.
        db_session.execute(models.Tenant.__table__.update().where(models.Tenant.id == tenant.id)
            .values(smartpse_company_id="99"))
        db_session.commit()
        return original(*args, **kwargs)
    panel.retry_invoice.side_effect = change_company
    assert not run(db_session, job)
    client.consult_ticket.assert_called_once()
    assert metadata["provider_company_id"] == "77"
    assert not attempts and "panel_retry_attempt" not in job.payload_snapshot
    assert db_session.query(models.AuditLog).filter_by(action="fiscal_panel_retry_started", entity_id=document.id).count() == 0


def test_production_panel_post_is_blocked_in_beta_runtime(db_session, pending_sale, monkeypatch):
    tenant, user, document, job, xml, _, _, metadata, _ = pending_sale
    tenant.smartpse_environment = "produccion"
    prepared = dict(job.payload_snapshot["prepared_sale"], provider_environment="produccion")
    job.payload_snapshot = dict(job.payload_snapshot, prepared_sale=prepared)
    metadata["environment"] = "produccion"
    monkeypatch.setattr(settings, "FISCAL_ENV", "beta")
    db_session.commit()
    assert reserve(db_session, job, user, xml, metadata) is False
    assert "panel_retry_attempt" not in job.payload_snapshot
    assert db_session.query(models.AuditLog).filter_by(action="fiscal_panel_retry_started", entity_id=document.id).count() == 0


@pytest.mark.parametrize("cdr_status", ["foreign", "rejected"])
def test_panel_cdr_needs_matching_acceptance_before_marking_emitted(db_session, pending_sale, cdr_status):
    tenant, _, document, job, xml, _, panel, _, attempts = pending_sale
    panel.retry_invoice.side_effect = None
    panel.retry_invoice.return_value = {"estado": 200, "recovery_source": "smartpse_panel",
        "panel_retry_attempted": False, "panel_retry_status": "cdr_available",
        "cdr": _sale_cdr(document_id="FA99-999" if cdr_status == "foreign" else f"{document.serie}-{document.correlativo}",
                         ruc=tenant.business_ruc, response_code="0" if cdr_status == "foreign" else "2335")}
    assert not run(db_session, job)
    assert not document.sunat_accepted and tenant.subscription.documents_used == 0
    assert document.sunat_xml_content == xml and not attempts
    if cdr_status == "foreign":
        assert job.status == "retry" and document.provider_verification_status == "pending_confirmation"
    else:
        assert job.status == "failed" and document.provider_verification_status == "rejected"
        assert document.sunat_cdr_content


@pytest.mark.parametrize("late_response", ["pending", "different_artifacts", "accepted"])
def test_late_consultation_cannot_revive_verified_rejection(db_session, pending_sale, late_response):
    tenant, _, document, job, xml, client, panel, _, attempts = pending_sale
    assert not run(db_session, job)  # A real panel attempt has already been reserved and acknowledged.
    rejection = _sale_cdr(document_id=f"{document.serie}-{document.correlativo}", ruc=tenant.business_ruc, response_code="2335")
    document.sunat_cdr_content = rejection
    document.provider_verification_status = "rejected"
    document.sunat_error = "SUNAT rechazo acreditado 2335"
    db_session.commit()
    original_response = deepcopy(document.provider_response)
    if late_response == "different_artifacts":
        client.consult_ticket.return_value = {"estado": 202, "xml_firmado": "<Invoice>otro XML</Invoice>",
            "cdr": _sale_cdr(document_id="FA99-999", ruc=tenant.business_ruc)}
    elif late_response == "accepted":
        client.consult_ticket.return_value = {"estado": 200,
            "cdr": _sale_cdr(document_id=f"{document.serie}-{document.correlativo}", ruc=tenant.business_ruc)}
    assert not run(db_session, job)
    assert job.status == "failed" and document.provider_verification_status == "rejected"
    assert document.sunat_cdr_content == rejection and document.sunat_xml_content == xml
    assert document.provider_response == original_response
    assert not evidence.has_deliverable_xml(document) and not document.sunat_accepted
    assert tenant.subscription.documents_used == 0 and len(attempts) == 1
    panel.retry_invoice.assert_called_once()
    if late_response == "accepted":
        assert "CDR contradictorios" in job.last_error
        conflict = job.result_snapshot["cdr_conflict"]
        assert conflict["stored_cdr_sha256"] == hashlib.sha256(rejection.encode()).hexdigest()
        assert conflict["received_cdr_sha256"] == hashlib.sha256(client.consult_ticket.return_value["cdr"].encode()).hexdigest()
        assert db_session.query(models.AuditLog).filter_by(action="fiscal_cdr_conflict", entity_id=document.id).count() == 1
        # Requeued evidence cannot duplicate the same conflict audit.
        crud.requeue_emission_job(db_session, job.id)
        assert not run(db_session, job)
        assert db_session.query(models.AuditLog).filter_by(action="fiscal_cdr_conflict", entity_id=document.id).count() == 1


@pytest.mark.parametrize("false_rejection", ["text", "foreign_identity", "foreign_ruc", "unreadable", "missing_ruc", "snapshot_identity"])
def test_rejection_marker_without_matching_cdr_is_not_terminal(db_session, pending_sale, false_rejection):
    tenant, _, document, job, _, _, _, _, _ = pending_sale
    document.provider_verification_status = "rejected"
    document.sunat_error = "rechazado"
    if false_rejection == "text":
        document.sunat_cdr_content = None
    elif false_rejection == "unreadable":
        document.sunat_cdr_content = "not XML"
    else:
        identity = "FA99-999" if false_rejection in {"foreign_identity", "snapshot_identity"} else f"{document.serie}-{document.correlativo}"
        ruc = "20999999999" if false_rejection == "foreign_ruc" else tenant.business_ruc
        cdr = _sale_cdr(document_id=identity, ruc=ruc, response_code="2335")
        if false_rejection == "missing_ruc":
            cdr = cdr.replace(f"<cbc:ID>{ruc}</cbc:ID>", "")
        if false_rejection == "snapshot_identity":
            prepared = deepcopy(job.payload_snapshot["prepared_sale"])
            prepared["payload"].update(serie="FA99", correlativo="999")
            job.payload_snapshot = dict(job.payload_snapshot, prepared_sale=prepared)
        document.sunat_cdr_content = cdr
    db_session.commit()
    assert not run(db_session, job)
    assert job.status == "retry" and document.provider_verification_status == "pending_confirmation"


def test_late_pending_preserves_existing_acceptance(db_session, pending_sale):
    tenant, _, document, job, xml, _, _, _, _ = pending_sale
    payload = job.payload_snapshot["prepared_sale"]["payload"]
    cdr = _sale_cdr(document_id=f"{document.serie}-{document.correlativo}", ruc=tenant.business_ruc)
    result = smartpse_response.build_smartpse_result(payload, {"cdr": cdr, "xml_firmado": xml},
        endpoint="offline", status_code=200, require_cdr=True)
    result["provider_verification_status"] = "verified"
    crud.guardar_respuesta_sunat(db_session, document.id, result, tenant_id=tenant.id)
    original_response = deepcopy(document.provider_response)
    assert run(db_session, job)
    assert job.status == "succeeded" and document.sunat_accepted
    assert document.provider_verification_status == "verified" and document.estado == "facturada"
    assert document.sunat_cdr_content == cdr and document.sunat_xml_content == xml
    assert document.provider_response == original_response and tenant.subscription.documents_used == 1


def test_acceptance_arriving_after_evidence_commit_survives_late_rejection(db_session, pending_sale, monkeypatch):
    tenant, _, document, job, xml, client, _, _, _ = pending_sale
    identity = f"{document.serie}-{document.correlativo}"
    accepted_cdr = _sale_cdr(document_id=identity, ruc=tenant.business_ruc)
    client.consult_ticket.return_value = {"estado": 200,
        "cdr": _sale_cdr(document_id=identity, ruc=tenant.business_ruc, response_code="2335")}
    accepted_response = {"success": True, "cdr_xml": accepted_cdr, "xml": xml,
        "provider_verification_status": "verified", "provider_response": {"cdr": accepted_cdr}}
    pdf_calls = []
    async def accept_during_pdf(*args, **kwargs):
        pdf_calls.append(True)
        crud.guardar_respuesta_sunat(db_session, document.id, accepted_response, tenant_id=tenant.id)
    monkeypatch.setattr(queue.pdf_storage_service, "process_pdf_background", accept_during_pdf)
    assert run(db_session, job)
    assert pdf_calls and job.status == "succeeded"
    assert document.estado == "facturada" and document.sunat_accepted
    assert document.sunat_cdr_content == accepted_cdr and document.sunat_xml_content == xml
    assert document.provider_verification_status == "verified" and tenant.subscription.documents_used == 1


def test_incoming_rejection_without_issuer_cdr_keeps_reconciliation(db_session, pending_sale):
    tenant, _, document, job, _, client, _, _, _ = pending_sale
    cdr = _sale_cdr(document_id=f"{document.serie}-{document.correlativo}", ruc=tenant.business_ruc, response_code="2335")
    cdr = cdr.replace(f"<cbc:ID>{tenant.business_ruc}</cbc:ID>", "")
    client.consult_ticket.return_value = {"estado": 200, "cdr": cdr}
    assert not run(db_session, job)
    assert job.status == "retry" and document.provider_verification_status == "pending_confirmation"
    assert not document.sunat_cdr_content and not document.sunat_accepted
    assert tenant.subscription.documents_used == 0


def test_api_outage_is_recorded_once_when_existing_rejection_is_preserved(db_session, pending_sale, monkeypatch):
    tenant, _, document, job, xml, _, _, _, _ = pending_sale
    rejected_cdr = _sale_cdr(document_id=f"{document.serie}-{document.correlativo}", ruc=tenant.business_ruc, response_code="2335")
    document.sunat_cdr_content = rejected_cdr
    document.provider_verification_status = "rejected"
    document.sunat_error = "SUNAT rechazo acreditado 2335"
    db_session.commit()
    response = deepcopy(document.provider_response)
    monkeypatch.setattr(facturacion_service, "consultar_documento_fiscal", Mock(side_effect=
        facturacion_service.FacturacionException("Consulta API503 pendiente", {"estado": 503},
            partial_result={"pending": True, "api_transport_failure": True})))
    assert not run(db_session, job)
    assert job.status == "failed" and document.provider_verification_status == "rejected"
    assert document.sunat_cdr_content == rejected_cdr and document.sunat_xml_content == xml
    assert document.provider_response == response and tenant.subscription.documents_used == 0
    assert db_session.get(models.FiscalProviderCircuit, recovery.scope_for(tenant)).failures == 1


def test_api503_panel_acceptance_conflict_records_only_one_outage(db_session, pending_sale):
    tenant, _, document, job, xml, client, panel, _, _ = pending_sale
    identity = f"{document.serie}-{document.correlativo}"
    rejected_cdr = _sale_cdr(document_id=identity, ruc=tenant.business_ruc, response_code="2335")
    document.sunat_cdr_content = rejected_cdr
    document.provider_verification_status = "rejected"
    document.sunat_error = "SUNAT rechazo acreditado 2335"
    db_session.commit()
    original_response = deepcopy(document.provider_response)
    client.consult_ticket.side_effect = smartpse_client.SmartPSEException("API503",
        {"estado": 503}, status_code=503)
    panel.recover_invoice.return_value = {"estado": 200, "recovery_source": "smartpse_panel",
        "cdr": _sale_cdr(document_id=identity, ruc=tenant.business_ruc), "xml_firmado": xml}
    assert not run(db_session, job)
    assert document.provider_verification_status == "rejected" and document.sunat_cdr_content == rejected_cdr
    assert document.sunat_xml_content == xml and document.provider_response == original_response
    assert job.status == "failed" and "CDR contradictorios" in job.last_error
    assert tenant.subscription.documents_used == 0
    assert db_session.get(models.FiscalProviderCircuit, recovery.scope_for(tenant)).failures == 1
    assert db_session.query(models.AuditLog).filter_by(action="fiscal_cdr_conflict", entity_id=document.id).count() == 1
