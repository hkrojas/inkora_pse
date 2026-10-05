"""Offline fiscal recovery: signed evidence, ambiguous sends and shared probes."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from lxml import etree
import pytest
from signxml import XMLSigner

import crud
import models
from config import settings
from services import emission_queue_service as queue, fiscal_evidence_service as evidence
from services import fiscal_recovery_service as recovery, pdf_storage_service, smartpse_client
from services import fiscal_submission_state as submission
from services.fiscal_presentation_service import presentation_status, presentation_status_expression
from test_emission_queue import _make_fiscal_document
from test_smartpse_response_normalization import _sale_cdr


@pytest.fixture(scope="module")
def sign_xml():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Inkora offline test")])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=1)).sign(key, hashes.SHA256()))
    def sign(xml):
        root = etree.fromstring(xml.encode())
        signed = XMLSigner().sign(root, key=key, cert=cert.public_bytes(serialization.Encoding.PEM))
        return etree.tostring(signed).decode()
    return sign


@pytest.fixture
def sale(db_session, monkeypatch):
    monkeypatch.setattr(settings, "FISCAL_CONTINGENCY_TENANT_IDS", "*")
    tenant, user, document = _make_fiscal_document(db_session, "RECOVERY")
    job, _ = queue.enqueue_fiscal_document_job(db_session, document, user, tipo_comprobante="01")
    async def noop(*args, **kwargs):
        pass
    monkeypatch.setattr(queue.pdf_storage_service, "process_pdf_background", noop)
    monkeypatch.setattr(queue.fiscal_artifact_service, "persist_cdr_artifact", noop)
    return tenant, user, document, job


def test_signed_evidence_is_deliverable_without_acceptance(db_session, sale, sign_xml):
    tenant, _, document, job = sale
    prepared = job.payload_snapshot["prepared_sale"]
    signed = sign_xml(prepared["unsigned_xml"])
    response = {"xml_firmado": signed, "token_acceso": "synthetic-secret", "estado": 202}
    assert evidence.retain_sale_evidence(db_session, document, response, payload=prepared["payload"], status_code=500)
    assert evidence.has_deliverable_xml(document)
    assert document.sunat_xml_content == signed
    assert document.provider_response["process"]["token_acceso"] == "***"
    assert document.sunat_qr_payload
    used_before = tenant.subscription.documents_used
    crud.guardar_respuesta_sunat(db_session, document.id,
        {"success": True, "pending": True, "xml": signed, "provider_response": response}, tenant_id=tenant.id)
    assert document.estado == "pendiente"
    assert tenant.subscription.documents_used == used_before
    assert document.source_quote.estado != "facturada"
    assert evidence.has_deliverable_xml(document)


def test_invalid_or_foreign_xml_is_retained_but_not_deliverable(db_session, sale, sign_xml):
    _, _, document, job = sale
    prepared = job.payload_snapshot["prepared_sale"]
    signed = sign_xml(prepared["unsigned_xml"])
    wrong = dict(prepared["payload"], company={"ruc": "20999999999"})
    assert not evidence.retain_sale_evidence(db_session, document, {"xml_firmado": signed}, payload=wrong)
    assert "otra empresa" in document.provider_response["inkora_evidence"]["xml_validation_error"]
    assert not evidence.has_deliverable_xml(document)
    assert evidence.retain_sale_evidence(db_session, document, {"xml_firmado": signed}, payload=prepared["payload"])
    assert evidence.has_deliverable_xml(document)
    tampered = etree.fromstring(signed.encode())
    tampered.find("cbc:InvoiceTypeCode", namespaces=evidence.smartpse_response.NS).text = "03"
    with pytest.raises(smartpse_client.SmartPSEException):
        evidence.validate_signed_sale_xml(etree.tostring(tampered).decode(), prepared["payload"])


def test_timeout_consults_and_reconciles_without_resending(db_session, sale, sign_xml, monkeypatch):
    tenant, _, document, job = sale
    prepared = job.payload_snapshot["prepared_sale"]
    signed = sign_xml(prepared["unsigned_xml"])
    client = Mock()
    client.sign_xml.return_value = {"xml_firmado": signed}
    client.send_signed_xml.side_effect = smartpse_client.SmartPSEException("Timeout enviando documento")
    client.consult_ticket.return_value = {"xml_firmado": signed, "estado": 200,
        "cdr": _sale_cdr(document_id=f"{document.serie}-{document.correlativo}", ruc=tenant.business_ruc)}
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    crud.claim_next_emission_job(db_session)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    db_session.expire_all()
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    assert job.status == "retry"
    assert document.estado == "pendiente"
    assert evidence.has_deliverable_xml(document)
    circuit = db_session.get(models.FiscalProviderCircuit, recovery.scope_for(tenant))
    assert circuit.failures == 1
    monkeypatch.setattr(settings, "FISCAL_CONTINGENCY_TENANT_IDS", "")
    assert recovery.enabled_for_job(job)
    circuit.next_probe_at = datetime.now() - timedelta(seconds=1)
    job.available_at = datetime.now() - timedelta(seconds=1)
    db_session.commit()
    crud.claim_next_emission_job(db_session)
    assert queue.process_emission_job(job.id, db_session=db_session)
    assert document.estado == "facturada"
    assert presentation_status(document) == "emitted"
    assert job.status == "succeeded"
    assert circuit.failures == 0
    assert client.sign_xml.call_count == 1
    assert client.send_signed_xml.call_count == 1
    assert client.consult_ticket.call_count == 1


def test_open_service_signs_other_invoice_and_defers_send(db_session, sale, sign_xml, monkeypatch):
    tenant, _, document, job = sale
    recovery.service_failed(db_session, tenant)
    client = Mock()
    client.sign_xml.return_value = {"xml_firmado": sign_xml(job.payload_snapshot["prepared_sale"]["unsigned_xml"])}
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    crud.claim_next_emission_job(db_session)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert evidence.has_deliverable_xml(document)
    assert job.status == "retry"
    client.sign_xml.assert_called_once()
    client.send_signed_xml.assert_not_called()
    monkeypatch.setattr(settings, "FISCAL_CONTINGENCY_TENANT_IDS", "")
    assert recovery.enabled_for_job(job)
    circuit = db_session.get(models.FiscalProviderCircuit, recovery.scope_for(tenant))
    circuit.next_probe_at = datetime.now() - timedelta(seconds=1)
    job.available_at = datetime.now() - timedelta(seconds=1)
    db_session.commit()
    client.send_signed_xml.return_value = {"estado": 200,
        "cdr": _sale_cdr(document_id=f"{document.serie}-{document.correlativo}", ruc=tenant.business_ruc)}
    signed = document.sunat_xml_content
    crud.claim_next_emission_job(db_session)
    assert queue.process_emission_job(job.id, db_session=db_session)
    assert document.estado == "facturada"
    client.sign_xml.assert_called_once()
    client.send_signed_xml.assert_called_once()
    assert client.send_signed_xml.call_args.args[2] == signed
    assert job.payload_snapshot["send_count"] == 1
    client.consult_ticket.assert_not_called()


def test_timeout_then_not_found_keeps_reconciliation_without_resending(db_session, sale, sign_xml, monkeypatch):
    tenant, _, document, job = sale
    prepared = job.payload_snapshot["prepared_sale"]
    signed = sign_xml(prepared["unsigned_xml"])
    remote_acceptances = []
    client = Mock()
    client.sign_xml.return_value = {"xml_firmado": signed}
    def accept_without_returning_cdr(*args, **kwargs):
        remote_acceptances.append(_sale_cdr(
            document_id=f"{document.serie}-{document.correlativo}", ruc=tenant.business_ruc))
        raise smartpse_client.SmartPSEException("Timeout enviando documento")
    client.send_signed_xml.side_effect = accept_without_returning_cdr
    client.consult_ticket.side_effect = smartpse_client.SmartPSEException(
        "Documento o ticket no encontrado", {"message": "Documento o ticket no encontrado"}, status_code=404)
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    crud.claim_next_emission_job(db_session)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert len(remote_acceptances) == 1
    circuit = db_session.get(models.FiscalProviderCircuit, recovery.scope_for(tenant))
    circuit.next_probe_at = datetime.now() - timedelta(seconds=1)
    job.available_at = datetime.now() - timedelta(seconds=1)
    db_session.commit()
    # Existing jobs must stay safe even after enrollment has been disabled.
    monkeypatch.setattr(settings, "FISCAL_CONTINGENCY_TENANT_IDS", "")
    crud.claim_next_emission_job(db_session)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    db_session.expire_all()
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    assert job.status == "retry"
    assert "Documento o ticket no encontrado" in job.last_error
    assert job.payload_snapshot["send_count"] == 1
    assert document.estado == "pendiente"
    assert not document.sunat_cdr_content
    assert document.provider_verification_status == "pending_confirmation"
    assert document.sunat_xml_content == signed
    assert evidence.has_deliverable_xml(document)
    assert presentation_status(document) == "pending_confirmation"
    client.sign_xml.assert_called_once()
    client.send_signed_xml.assert_called_once()
    client.consult_ticket.assert_called_once()
    assert client.send_signed_xml.call_args.args[2] == signed
    assert document.correlativo == int(prepared["payload"]["correlativo"])


@pytest.mark.parametrize("submission_history", [
    {"send_started": True, "send_count": 1, "retry_signed_after_not_found": True},
    {"retry_signed_after_not_found": True},
])
def test_legacy_not_found_retry_snapshot_only_consults(db_session, sale, sign_xml, monkeypatch, submission_history):
    _, _, document, job = sale
    prepared = job.payload_snapshot["prepared_sale"]
    signed = sign_xml(prepared["unsigned_xml"])
    evidence.retain_sale_evidence(db_session, document, {"xml_firmado": signed}, payload=prepared["payload"])
    job.payload_snapshot = dict(job.payload_snapshot, **submission_history)
    db_session.commit()
    client = Mock()
    client.consult_ticket.side_effect = smartpse_client.SmartPSEException(
        "Documento o ticket no encontrado", {"message": "Documento o ticket no encontrado"}, status_code=404)
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    crud.claim_next_emission_job(db_session)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    db_session.expire_all()
    assert job.status == "retry"
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    assert job.payload_snapshot["send_started"] is True
    assert "retry_signed_after_not_found" not in job.payload_snapshot
    assert job.payload_snapshot.get("send_count") == submission_history.get("send_count")
    assert document.estado == "pendiente"
    assert document.sunat_xml_content == signed
    assert evidence.has_deliverable_xml(document)
    client.consult_ticket.assert_called_once()
    client.sign_xml.assert_not_called()
    client.send_signed_xml.assert_not_called()


def test_matching_rejection_cdr_stops_retries(db_session, sale, sign_xml, monkeypatch):
    tenant, _, document, job = sale
    signed = sign_xml(job.payload_snapshot["prepared_sale"]["unsigned_xml"])
    client = Mock()
    client.sign_xml.return_value = {"xml_firmado": signed}
    client.send_signed_xml.return_value = {"estado": 200, "rechazado": True,
        "cdr": _sale_cdr(document_id=f"{document.serie}-{document.correlativo}", response_code="2335", ruc=tenant.business_ruc)}
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    crud.claim_next_emission_job(db_session)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert job.status == "failed"
    assert document.provider_verification_status == "rejected"
    assert presentation_status(document) == "rejected"
    assert document.sunat_cdr_content
    assert not evidence.has_deliverable_xml(document)
    from routers.facturacion import _fiscal_doc_list_columns
    projection = next(column for column in _fiscal_doc_list_columns() if column.name == "has_deliverable_fiscal_xml")
    assert db_session.query(projection).filter(models.Cotizacion.id == document.id).scalar() is False


def test_verified_flag_without_cdr_does_not_show_accepted(db_session, sale):
    _, _, document, _ = sale
    document.estado = "facturada"
    document.provider_verification_status = "verified"
    document.sunat_cdr_content = None
    document.sunat_cdr_url = None
    db_session.commit()
    assert presentation_status(document) == "pending"
    assert db_session.query(presentation_status_expression(models.Cotizacion)).filter(
        models.Cotizacion.id == document.id).scalar() == "pending"


def test_legacy_0111_recovers_to_consult_without_signing(db_session, sale):
    _, _, _, job = sale
    job.status = "pending_confirmation"
    job.last_error = "[0111] Rejected by policy"
    job.payload_snapshot = {key: value for key, value in job.payload_snapshot.items()
                            if key not in {"submission_state_version", "submission_phase"}}
    db_session.commit()
    assert crud.recover_pending_fiscal_reconciliations(db_session) == 1
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    assert job.status == "retry"


def test_pending_state_and_sql_filter_agree_on_transport_errors(db_session, sale):
    _, _, document, _ = sale
    document.sunat_error = "Timeout enviando documento"
    db_session.commit()
    assert presentation_status(document) == "pending_confirmation"
    status = db_session.query(presentation_status_expression(models.Cotizacion)).filter(models.Cotizacion.id == document.id).scalar()
    assert status == "pending_confirmation"


def test_fiscal_pdf_needs_valid_signed_xml_and_cache_tracks_qr(db_session, sale, sign_xml):
    _, _, document, job = sale
    with pytest.raises(pdf_storage_service.FiscalPdfNotReady):
        pdf_storage_service.ensure_fiscal_pdf_ready(document)
    prepared = job.payload_snapshot["prepared_sale"]
    first = pdf_storage_service._pdf_source_fingerprint(document)
    evidence.retain_sale_evidence(db_session, document, {"xml_firmado": sign_xml(prepared["unsigned_xml"])}, payload=prepared["payload"])
    pdf_storage_service.ensure_fiscal_pdf_ready(document)
    assert pdf_storage_service._pdf_source_fingerprint(document) != first


def test_deadline_is_calendar_based_and_never_sends_expired_invoice(db_session, sale, monkeypatch):
    _, _, document, job = sale
    document.fecha_emision = datetime(2026, 1, 1, 23, 59)
    assert recovery.invoice_deadline(document) == datetime(2026, 1, 5, 5)
    db_session.commit()
    client = Mock()
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    crud.claim_next_emission_job(db_session)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert job.status == "failed"
    client.sign_xml.assert_not_called()
    client.send_signed_xml.assert_not_called()
    assert db_session.query(models.AuditLog).filter(models.AuditLog.action == "fiscal_recovery_deadline").count() == 1


@pytest.mark.parametrize("failure", [
    smartpse_client.SmartPSEException("Timeout firmando documento"),
    smartpse_client.SmartPSEException("No se pudo conectar con Smart PSE"),
    smartpse_client.SmartPSEException("Respuesta HTTP 503", status_code=503),
])
def test_signing_outage_retries_past_max_attempts_then_recovers(
    db_session, sale, sign_xml, monkeypatch, failure,
):
    tenant, _, document, job = sale
    signed = sign_xml(job.payload_snapshot["prepared_sale"]["unsigned_xml"])
    client = Mock()
    client.sign_xml.side_effect = [failure] * 7 + [{"xml_firmado": signed}]
    client.send_signed_xml.return_value = {"estado": 200,
        "cdr": _sale_cdr(document_id=f"{document.serie}-{document.correlativo}", ruc=tenant.business_ruc)}
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    for attempt in range(1, 8):
        job.available_at = datetime.now() - timedelta(seconds=1)
        circuit = db_session.get(models.FiscalProviderCircuit, recovery.scope_for(tenant, service="cpe:sign"))
        if circuit:
            circuit.next_probe_at = datetime.now() - timedelta(seconds=1)
        db_session.commit()
        assert crud.claim_next_emission_job(db_session).id == job.id
        assert not queue.process_emission_job(job.id, db_session=db_session)
        assert job.status == "retry" and job.action == models.EMISSION_JOB_ACTION_EMIT_FISCAL
        assert job.attempts == attempt
        assert submission.can_submit(job.payload_snapshot)
        assert job.payload_snapshot["submission_phase"] == submission.NOT_STARTED
        assert not document.sunat_xml_content and not document.sunat_cdr_content
        assert (job.available_at - datetime.now()).total_seconds() > settings.FISCAL_RECOVERY_FIRST_SECONDS - 5
        client.send_signed_xml.assert_not_called()
        client.consult_ticket.assert_not_called()
    circuit = db_session.get(models.FiscalProviderCircuit, recovery.scope_for(tenant, service="cpe:sign"))
    assert circuit.failures == 7
    assert db_session.get(models.FiscalProviderCircuit, recovery.scope_for(tenant)) is None
    circuit.next_probe_at = job.available_at = datetime.now() - timedelta(seconds=1)
    db_session.commit()
    crud.claim_next_emission_job(db_session)
    assert queue.process_emission_job(job.id, db_session=db_session)
    assert job.status == "succeeded" and document.sunat_accepted
    assert document.sunat_xml_content == signed
    assert circuit.failures == 0
    assert client.sign_xml.call_count == 8
    client.send_signed_xml.assert_called_once()
    client.consult_ticket.assert_not_called()


def test_signing_outage_stops_at_deadline_with_single_alert(db_session, sale, monkeypatch):
    tenant, _, document, job = sale
    client = Mock()
    client.sign_xml.side_effect = smartpse_client.SmartPSEException("Timeout firmando documento")
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    crud.claim_next_emission_job(db_session)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    document.fecha_emision = datetime(2026, 1, 1)
    for _ in range(2):
        job.status = "retry"
        job.available_at = datetime.now() - timedelta(seconds=1)
        db_session.commit()
        crud.claim_next_emission_job(db_session)
        assert not queue.process_emission_job(job.id, db_session=db_session)
        assert job.status == "failed" and submission.can_submit(job.payload_snapshot)
    assert client.sign_xml.call_count == 1
    client.send_signed_xml.assert_not_called()
    client.consult_ticket.assert_not_called()
    assert db_session.query(models.AuditLog).filter_by(action="fiscal_recovery_deadline").count() == 1
    assert db_session.get(models.FiscalProviderCircuit, recovery.scope_for(tenant, service="cpe:sign")).failures == 1


@pytest.mark.parametrize("failure", [
    smartpse_client.SmartPSEException("Respuesta HTTP 422: XML invalido", status_code=422),
    smartpse_client.SmartPSEException("Respuesta HTTP 422: valor timeout invalido", status_code=422),
    None,
])
def test_signing_validation_is_terminal_without_transport_retries(db_session, sale, monkeypatch, failure):
    tenant, _, _, job = sale
    client = Mock()
    if failure:
        client.sign_xml.side_effect = failure
    else:
        client.sign_xml.return_value = {"xml_firmado": "invalid-signature"}
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    crud.claim_next_emission_job(db_session)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert job.status == "failed" and job.action == models.EMISSION_JOB_ACTION_EMIT_FISCAL
    assert submission.can_submit(job.payload_snapshot)
    assert crud.recover_pending_fiscal_reconciliations(db_session) == 0
    client.sign_xml.assert_called_once()
    client.send_signed_xml.assert_not_called()
    client.consult_ticket.assert_not_called()
    assert db_session.get(models.FiscalProviderCircuit, recovery.scope_for(tenant, service="cpe:sign")).failures == 0


def test_signing_circuit_pauses_other_tenants_without_pausing_submission(db_session, sale, sign_xml, monkeypatch):
    tenant, _, _, job = sale
    other_tenant, other_user, other_document = _make_fiscal_document(db_session, "OTHER-SIGN")
    other_job, _ = queue.enqueue_fiscal_document_job(db_session, other_document, other_user, tipo_comprobante="01")
    signed_tenant, signed_user, signed_document = _make_fiscal_document(db_session, "ALREADY-SIGNED")
    signed_job, _ = queue.enqueue_fiscal_document_job(db_session, signed_document, signed_user, tipo_comprobante="01")
    signed = sign_xml(signed_job.payload_snapshot["prepared_sale"]["unsigned_xml"])
    evidence.retain_sale_evidence(db_session, signed_document, {"xml_firmado": signed},
                                payload=signed_job.payload_snapshot["prepared_sale"]["payload"])
    signed_job.payload_snapshot = dict(signed_job.payload_snapshot, signed_ready=True)
    consult_job = models.DocumentEmissionJob(tenant_id=other_tenant.id, created_by_user_id=other_user.id,
        action=models.EMISSION_JOB_ACTION_CONSULT_FISCAL, provider="smartpse", resource_type="cotizacion",
        resource_id=other_document.id, idempotency_key="sign-circuit-consult", status="queued",
        available_at=datetime.now(), payload_snapshot={"recovery_flow": True})
    db_session.add(consult_job)
    db_session.commit()
    consult_available = consult_job.available_at
    signed_available = signed_job.available_at
    client = Mock()
    client.sign_xml.side_effect = smartpse_client.SmartPSEException("Respuesta HTTP 503", status_code=503)
    client.send_signed_xml.return_value = {"estado": 200,
        "cdr": _sale_cdr(document_id=f"{signed_document.serie}-{signed_document.correlativo}", ruc=signed_tenant.business_ruc)}
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    crud.claim_next_emission_job(db_session)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    db_session.expire_all()
    assert other_job.available_at > datetime.now() + timedelta(seconds=800)
    assert signed_job.available_at == signed_available and consult_job.available_at == consult_available
    # A forced early claim is still guarded by the persistent signing circuit.
    other_job.available_at = datetime.now() - timedelta(seconds=1)
    db_session.commit()
    assert not queue.process_emission_job(other_job.id, db_session=db_session)
    assert client.sign_xml.call_count == 1
    assert queue.process_emission_job(signed_job.id, db_session=db_session)
    assert signed_document.sunat_accepted
    assert db_session.get(models.FiscalProviderCircuit, recovery.scope_for(tenant, service="cpe:sign")).failures == 1


@pytest.mark.parametrize("recovering_service", ["cpe", "cpe:sign"])
def test_recovering_one_circuit_does_not_release_the_other_queue(db_session, sale, recovering_service):
    tenant, _, _, unsigned_job = sale
    user = db_session.query(models.User).filter_by(tenant_id=tenant.id).first()
    signed_job = models.DocumentEmissionJob(tenant_id=tenant.id, created_by_user_id=user.id,
        action=models.EMISSION_JOB_ACTION_EMIT_FISCAL, provider="smartpse", resource_type="cotizacion",
        resource_id=unsigned_job.resource_id, idempotency_key="already-signed-separate-circuit", status="queued",
        available_at=datetime.now(), payload_snapshot={"recovery_flow": True, "signed_ready": True})
    consult_job = models.DocumentEmissionJob(tenant_id=tenant.id, created_by_user_id=user.id,
        action=models.EMISSION_JOB_ACTION_CONSULT_FISCAL, provider="smartpse", resource_type="cotizacion",
        resource_id=unsigned_job.resource_id, idempotency_key="consult-separate-circuit", status="queued",
        available_at=datetime.now(), payload_snapshot={"recovery_flow": True})
    db_session.add_all([signed_job, consult_job])
    db_session.commit()
    recovery.service_failed(db_session, tenant, service="cpe")
    recovery.service_failed(db_session, tenant, service="cpe:sign")
    db_session.expire_all()
    unsigned_at, signed_at, consult_at = unsigned_job.available_at, signed_job.available_at, consult_job.available_at
    recovery.service_recovered(db_session, tenant, service=recovering_service)
    db_session.expire_all()
    if recovering_service == "cpe":
        assert unsigned_job.available_at == unsigned_at
        assert signed_job.available_at < signed_at and consult_job.available_at < consult_at
    else:
        assert unsigned_job.available_at < unsigned_at
        assert signed_job.available_at == signed_at and consult_job.available_at == consult_at


def test_consult_is_allowed_when_creator_or_subscription_is_inactive(db_session, sale):
    tenant, user, _, job = sale
    job.action = models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    tenant.is_active = False
    user.is_active = False
    tenant.subscription.status = "expired"
    db_session.commit()
    queue._validate_job_execution_context(db_session, job, user)
    foreign = SimpleNamespace(tenant_id=999)
    with pytest.raises(queue.NonRetryableEmissionValidationError):
        queue._validate_job_execution_context(db_session, job, foreign)


def test_frozen_provider_environment_cannot_change_before_send(db_session, sale, monkeypatch):
    tenant, _, _, job = sale
    tenant.smartpse_environment = "produccion"
    db_session.commit()
    client = Mock()
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    crud.claim_next_emission_job(db_session)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert job.status == "failed"
    assert "ambiente fiscal cambio" in job.last_error
    client.sign_xml.assert_not_called()
    client.send_signed_xml.assert_not_called()


def test_http_error_keeps_structured_signed_evidence(db_session, sale, sign_xml):
    from test_smartpse_client import _json_response
    _, _, document, job = sale
    prepared = job.payload_snapshot["prepared_sale"]
    signed = sign_xml(prepared["unsigned_xml"])
    response = _json_response(503, {"message": "SUNAT no disponible", "xml_firmado": signed})
    client = smartpse_client.SmartPSEClient(base_url="https://provider.invalid")
    with pytest.raises(smartpse_client.SmartPSEException) as failure:
        client._raise_for_response(response, action="procesar")
    exc = failure.value
    assert exc.status_code == 503
    assert evidence.retain_sale_evidence(db_session, document, exc.response_data, payload=prepared["payload"])
    assert document.sunat_xml_content == signed


def test_accepted_historical_pdf_is_not_regenerated(db_session, sale, monkeypatch):
    import asyncio
    from services import storage_service
    _, _, document, _ = sale
    document.estado = "facturada"
    document.sunat_cdr_content = "<ApplicationResponse>historical fixture</ApplicationResponse>"
    document.sunat_pdf_url = storage_service.build_private_storage_reference("cotizaciones/tenant_1/historical.pdf")
    db_session.commit()
    renderer = Mock(side_effect=AssertionError("Historical representation must be preserved"))
    monkeypatch.setattr(pdf_storage_service.pdf_generator, "create_comprobante_pdf", renderer)
    assert asyncio.run(pdf_storage_service.generate_and_upload_pdf(db_session, document)) == document.sunat_pdf_url
    renderer.assert_not_called()


@pytest.mark.parametrize("enrollment", ["", "*"])
def test_new_invoice_submission_state_is_initialized_once(db_session, sale, monkeypatch, enrollment):
    tenant, user, _, _ = sale
    monkeypatch.setattr(settings, "FISCAL_CONTINGENCY_TENANT_IDS", enrollment)
    _, _, document = _make_fiscal_document(db_session, "INITIAL_PHASE")
    user = document.usuario
    job, created = queue.enqueue_fiscal_document_job(db_session, document, user, tipo_comprobante="01")
    assert created
    assert job.payload_snapshot["submission_phase"] == submission.NOT_STARTED
    assert submission.can_submit(job.payload_snapshot)
    assert job.payload_snapshot["recovery_flow"] is bool(enrollment)
    # Requeue cannot promote a historical unknown into a safe first submission.
    job.payload_snapshot = {key: value for key, value in job.payload_snapshot.items()
                            if key not in {"submission_state_version", "submission_phase"}}
    job.status = "failed"
    db_session.commit()
    same_job, created = queue.enqueue_fiscal_document_job(db_session, document, user, tipo_comprobante="01")
    assert not created and same_job.id == job.id
    assert not submission.can_submit(same_job.payload_snapshot)
    assert "submission_phase" not in same_job.payload_snapshot


@pytest.mark.parametrize("enrollment", ["", "*"])
@pytest.mark.parametrize("legacy_fields", [{}, {"send_started": False, "sign_only": True}])
def test_unknown_invoice_history_never_signs_or_sends(db_session, sale, monkeypatch, enrollment, legacy_fields):
    _, _, document, job = sale
    snapshot = {key: value for key, value in job.payload_snapshot.items()
                if key not in {"submission_state_version", "submission_phase"}}
    job.payload_snapshot = dict(snapshot, recovery_flow=bool(enrollment), **legacy_fields)
    monkeypatch.setattr(settings, "FISCAL_CONTINGENCY_TENANT_IDS", enrollment)
    monkeypatch.setattr(settings, "SMARTPSE_PANEL_RECOVERY_TENANT_IDS", "")
    db_session.commit()
    client = Mock()
    client.consult_ticket.side_effect = smartpse_client.SmartPSEException("Documento no encontrado", status_code=404)
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    crud.claim_next_emission_job(db_session)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    assert job.status == "retry"
    assert "submission_phase" not in job.payload_snapshot
    assert not document.sunat_xml_content
    client.consult_ticket.assert_called_once()
    client.sign_xml.assert_not_called()
    client.send_signed_xml.assert_not_called()
    client.process_xml.assert_not_called()


def test_sign_and_send_are_outside_sql_transactions(db_session, sale, sign_xml, monkeypatch):
    tenant, _, document, job = sale
    prepared = job.payload_snapshot["prepared_sale"]
    signed = sign_xml(prepared["unsigned_xml"])
    expected_credentials = (tenant.id, tenant.smartpse_usuario_secundaria, tenant.smartpse_token_acceso)
    client = Mock()
    def sign(network_tenant, name, xml, **kwargs):
        assert not db_session.in_transaction()
        assert (network_tenant.id, network_tenant.smartpse_usuario_secundaria,
                network_tenant.smartpse_token_acceso) == expected_credentials
        assert name == prepared["nombre_archivo"] and xml == prepared["unsigned_xml"]
        return {"xml_firmado": signed}
    def send(network_tenant, name, xml, **kwargs):
        assert not db_session.in_transaction()
        assert (network_tenant.id, network_tenant.smartpse_usuario_secundaria,
                network_tenant.smartpse_token_acceso) == expected_credentials
        assert name == prepared["nombre_archivo"] and xml == signed
        return {"estado": 200, "cdr": _sale_cdr(
            document_id=f"{prepared['payload']['serie']}-{prepared['payload']['correlativo']}",
            ruc=prepared["payload"]["company"]["ruc"])}
    client.sign_xml.side_effect = sign
    client.send_signed_xml.side_effect = send
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    crud.claim_next_emission_job(db_session)
    assert queue.process_emission_job(job.id, db_session=db_session)
    assert job.payload_snapshot["submission_phase"] == submission.POSSIBLE_SUBMISSION
    assert document.sunat_xml_content == signed
    client.sign_xml.assert_called_once()
    client.send_signed_xml.assert_called_once()


def test_normal_process_marks_possible_before_http_and_cannot_send_after_flag_flip(
    db_session, sale, monkeypatch,
):
    _, _, _, _ = sale
    monkeypatch.setattr(settings, "FISCAL_CONTINGENCY_TENANT_IDS", "")
    _, user, document = _make_fiscal_document(db_session, "PROCESS_PHASE")
    job, _ = queue.enqueue_fiscal_document_job(db_session, document, user, tipo_comprobante="01")
    assert submission.can_submit(job.payload_snapshot)
    job_id = job.id
    client = Mock()
    def process(*args, **kwargs):
        assert not db_session.in_transaction()
        # Inspect committed state using a separate Session, not an ORM refresh
        # on the session whose HTTP boundary is under test.
        from sqlalchemy.orm import Session
        with Session(db_session.bind) as reader:
            persisted = reader.get(models.DocumentEmissionJob, job_id)
            assert persisted.payload_snapshot["submission_phase"] == submission.POSSIBLE_SUBMISSION
            assert persisted.payload_snapshot["send_started"] is True
        assert not db_session.in_transaction()
        raise smartpse_client.SmartPSEException("Timeout enviando documento")
    client.process_xml.side_effect = process
    client.consult_ticket.side_effect = smartpse_client.SmartPSEException("Documento no encontrado", status_code=404)
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    crud.claim_next_emission_job(db_session)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    assert job.payload_snapshot["submission_phase"] == submission.POSSIBLE_SUBMISSION
    # Even an emit action restored during rollout must consult the prior send.
    monkeypatch.setattr(settings, "FISCAL_CONTINGENCY_TENANT_IDS", "*")
    monkeypatch.setattr(settings, "SMARTPSE_PANEL_RECOVERY_TENANT_IDS", "")
    job.action = models.EMISSION_JOB_ACTION_EMIT_FISCAL
    job.available_at = datetime.now() - timedelta(seconds=1)
    db_session.commit()
    crud.claim_next_emission_job(db_session)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    client.process_xml.assert_called_once()
    client.consult_ticket.assert_called_once()
    client.sign_xml.assert_not_called()
    client.send_signed_xml.assert_not_called()


def test_proven_preauth_failure_retries_same_xml_once(db_session, sale, sign_xml, monkeypatch):
    tenant, _, document, job = sale
    prepared = job.payload_snapshot["prepared_sale"]
    signed = sign_xml(prepared["unsigned_xml"]) + "\n"
    number = document.correlativo
    client = Mock()
    client.sign_xml.return_value = {"xml_firmado": signed}
    client.send_signed_xml.side_effect = [
        smartpse_client.SmartPSENotSubmitted("CPE preauthentication failed"),
        {"estado": 200, "cdr": _sale_cdr(
            document_id=f"{document.serie}-{document.correlativo}", ruc=tenant.business_ruc)},
    ]
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    crud.claim_next_emission_job(db_session)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert job.action == models.EMISSION_JOB_ACTION_EMIT_FISCAL
    assert job.payload_snapshot["submission_phase"] == submission.NOT_SUBMITTED
    assert submission.can_submit(job.payload_snapshot)
    assert document.sunat_xml_content == signed
    job.available_at = datetime.now() - timedelta(seconds=1)
    db_session.commit()
    crud.claim_next_emission_job(db_session)
    assert queue.process_emission_job(job.id, db_session=db_session)
    assert job.payload_snapshot["submission_phase"] == submission.POSSIBLE_SUBMISSION
    assert document.sunat_xml_content == signed and document.correlativo == number
    client.sign_xml.assert_called_once()
    assert client.send_signed_xml.call_count == 2
    assert all(call.args[2] == signed for call in client.send_signed_xml.call_args_list)
    client.consult_ticket.assert_not_called()
    client.process_xml.assert_not_called()


def test_unknown_history_consults_when_creator_and_tenant_are_inactive(db_session, sale, monkeypatch):
    tenant, user, _, job = sale
    job.payload_snapshot = {key: value for key, value in job.payload_snapshot.items()
                            if key not in {"submission_state_version", "submission_phase"}}
    user.is_active = False
    tenant.is_active = False
    tenant.subscription.status = "expired"
    db_session.commit()
    client = Mock()
    client.consult_ticket.side_effect = smartpse_client.SmartPSEException("Documento no encontrado", status_code=404)
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    crud.claim_next_emission_job(db_session)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    assert job.status == "retry"
    client.consult_ticket.assert_called_once()
    client.process_xml.assert_not_called()
    client.sign_xml.assert_not_called()
    client.send_signed_xml.assert_not_called()


@pytest.mark.parametrize("foreign_scope", ["user", "document"])
def test_unknown_history_cannot_cross_tenant_scope(db_session, sale, monkeypatch, foreign_scope):
    _, _, _, job = sale
    _, foreign_user, foreign_document = _make_fiscal_document(db_session, "FOREIGN_PHASE")
    job.payload_snapshot = {key: value for key, value in job.payload_snapshot.items()
                            if key not in {"submission_state_version", "submission_phase"}}
    if foreign_scope == "user":
        monkeypatch.setattr(queue, "_load_job_user", lambda *args: foreign_user)
    else:
        job.resource_id = foreign_document.id
    db_session.commit()
    client = Mock()
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    crud.claim_next_emission_job(db_session)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert job.status == "failed"
    client.consult_ticket.assert_not_called()
    client.process_xml.assert_not_called()
    client.sign_xml.assert_not_called()
    client.send_signed_xml.assert_not_called()


@pytest.mark.parametrize("malformed", [[], "legacy snapshot", 7, False])
def test_malformed_snapshot_fails_validation_without_discarding_evidence(db_session, sale, monkeypatch, malformed):
    _, _, _, job = sale
    job.payload_snapshot = malformed
    db_session.commit()
    client = Mock()
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    crud.claim_next_emission_job(db_session)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert job.status == "failed"
    assert job.last_error == "Snapshot fiscal no reconocido; requiere revisión."
    assert job.payload_snapshot == malformed
    client.consult_ticket.assert_not_called()
    client.process_xml.assert_not_called()
    client.sign_xml.assert_not_called()
    client.send_signed_xml.assert_not_called()


@pytest.mark.parametrize("primary_error", ["503", "timeout", "connection", "404"])
@pytest.mark.parametrize("panel_outcome", ["accepted", "pending", "rejected"])
def test_panel_recovery_preserves_primary_transport_failure_and_shared_backoff(
    db_session, sale, sign_xml, monkeypatch, primary_error, panel_outcome,
):
    import requests
    from services import smartpse_panel_client

    tenant, _, document, job = sale
    signed = sign_xml(job.payload_snapshot["prepared_sale"]["unsigned_xml"])
    evidence.retain_sale_evidence(db_session, document, {"xml_firmado": signed},
                                payload=job.payload_snapshot["prepared_sale"]["payload"])
    other_tenant, other_user, other_document = _make_fiscal_document(db_session, "OTHER-PANEL-OUTAGE")
    other_job, _ = queue.enqueue_fiscal_document_job(db_session, other_document, other_user, tipo_comprobante="01")
    other_job.action = models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    job.action = models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    db_session.commit()
    other_available = other_job.available_at
    client, panel = Mock(), Mock()
    if primary_error in {"503", "404"}:
        original = smartpse_client.SmartPSEException("API lookup error", status_code=int(primary_error))
    else:
        original = smartpse_client.SmartPSEException("API transport error")
        original.__cause__ = (requests.exceptions.Timeout() if primary_error == "timeout"
                              else requests.exceptions.ConnectionError())
    client.consult_ticket.side_effect = original
    response = {"estado": 202 if panel_outcome == "pending" else 200,
                "cdr": None if panel_outcome == "pending" else _sale_cdr(
                    document_id=f"{document.serie}-{document.correlativo}", ruc=tenant.business_ruc,
                    response_code="2335" if panel_outcome == "rejected" else "0"),
                "recovery_source": "smartpse_panel"}
    panel.recover_invoice.return_value = response
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    monkeypatch.setattr(smartpse_panel_client, "get_default_client", lambda: panel)
    monkeypatch.setattr(smartpse_panel_client, "enabled_for_tenant", lambda tenant_id: tenant_id == tenant.id)
    assert crud.claim_next_emission_job(db_session).id == job.id
    result = queue.process_emission_job(job.id, db_session=db_session)
    db_session.expire_all()
    circuit = db_session.get(models.FiscalProviderCircuit, recovery.scope_for(tenant))
    if primary_error == "404":
        assert circuit.failures == 0 and circuit.next_probe_at is None
        assert other_job.available_at == other_available
    else:
        assert circuit.failures == 1
        assert (circuit.next_probe_at - datetime.now()).total_seconds() > 895
        assert other_job.available_at == circuit.next_probe_at
    assert document.sunat_xml_content == signed
    if panel_outcome == "accepted":
        assert result and job.status == "succeeded"
        assert document.sunat_accepted and document.estado == "facturada"
        assert document.sunat_cdr_content
        assert tenant.subscription.documents_used == 1
    elif panel_outcome == "pending":
        assert not result and job.status == "retry"
        assert document.estado == "pendiente" and not document.sunat_accepted
        assert not document.sunat_cdr_content
        assert evidence.has_deliverable_xml(document)
        assert tenant.subscription.documents_used == 0
    else:
        assert not result and job.status == "failed"
        assert document.provider_verification_status == "rejected"
        assert document.sunat_cdr_content
        assert not document.sunat_accepted
        assert tenant.subscription.documents_used == 0
    client.consult_ticket.assert_called_once()
    panel.recover_invoice.assert_called_once()
    client.process_xml.assert_not_called()
    client.sign_xml.assert_not_called()
    client.send_signed_xml.assert_not_called()
