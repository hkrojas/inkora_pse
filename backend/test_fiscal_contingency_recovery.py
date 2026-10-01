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


def test_confirmed_not_found_resubmits_identical_xml_without_signing_again(db_session, sale, sign_xml, monkeypatch):
    tenant, _, document, job = sale
    prepared = job.payload_snapshot["prepared_sale"]
    signed = sign_xml(prepared["unsigned_xml"])
    evidence.retain_sale_evidence(db_session, document, {"xml_firmado": signed}, payload=prepared["payload"])
    job.action = models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    job.payload_snapshot = dict(job.payload_snapshot, send_started=True)
    db_session.commit()
    client = Mock()
    client.consult_ticket.side_effect = smartpse_client.SmartPSEException(
        "Documento o ticket no encontrado", {"message": "Documento o ticket no encontrado"}, status_code=404)
    client.send_signed_xml.return_value = {"estado": 200,
        "cdr": _sale_cdr(document_id=f"{document.serie}-{document.correlativo}", ruc=tenant.business_ruc)}
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    crud.claim_next_emission_job(db_session)
    assert queue.process_emission_job(job.id, db_session=db_session)
    assert document.estado == "facturada"
    assert document.sunat_xml_content == signed
    client.sign_xml.assert_not_called()
    client.send_signed_xml.assert_called_once()
    assert client.send_signed_xml.call_args.args[2] == signed
    assert document.correlativo == int(prepared["payload"]["correlativo"])


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
