"""Offline panel recovery reconciles a cached CDR without resubmitting a sale."""
import base64
import hashlib
from copy import deepcopy
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest
import requests

import crud
import models
from config import settings
from services import facturacion_service as fiscal, smartpse_client, smartpse_panel_client
from services import emission_queue_service as queue, fiscal_recovery_service as recovery
from services import fiscal_evidence_service as evidence
from test_fiscal_contingency_recovery import sale, sign_xml
from test_emission_queue import _make_fiscal_document
from test_smartpse_response_normalization import _sale_cdr
from test_smartpse_panel_client import Response, cdr as panel_cdr, client_for, listing, login, row


def _cdr(tenant, document, **overrides):
    return _sale_cdr(document_id=f"{document.serie}-{document.correlativo}",
                     ruc=tenant.business_ruc, **overrides)


def _missing():
    return smartpse_client.SmartPSEException(
        "Documento o ticket no encontrado", {"estado": 404}, status_code=404,
    )


@pytest.fixture
def panel_sale(db_session, sale, sign_xml, monkeypatch):
    tenant, user, document, job = sale
    prepared = job.payload_snapshot["prepared_sale"]
    signed = sign_xml(prepared["unsigned_xml"]) + "\n"
    assert evidence.retain_sale_evidence(db_session, document, {"xml_firmado": signed},
                                        payload=prepared["payload"])
    api, panel = Mock(), Mock()
    api.consult_ticket.side_effect = _missing()
    panel.recover_invoice.return_value = {
        "estado": 200, "cdr": _cdr(tenant, document), "recovery_source": "smartpse_panel",
    }
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: api)
    monkeypatch.setattr(smartpse_panel_client, "get_default_client", lambda: panel)
    enabled_tenant_id = tenant.id
    monkeypatch.setattr(smartpse_panel_client, "enabled_for_tenant", lambda tenant_id: tenant_id == enabled_tenant_id)
    return tenant, user, document, job, api, panel


def _queue_consult(db_session, job):
    job.action = models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    job.status = "queued"
    job.available_at = datetime.now() - timedelta(seconds=1)
    db_session.commit()
    assert crud.claim_next_emission_job(db_session).id == job.id


def test_timeout_then_panel_cdr_is_idempotent_without_opening_sunat_circuit(
    db_session, panel_sale, monkeypatch,
):
    tenant, user, document, job, api, panel = panel_sale
    signed, doc_number = document.sunat_xml_content, document.correlativo
    api.send_signed_xml.side_effect = smartpse_client.SmartPSEException("Timeout enviando documento")
    assert crud.claim_next_emission_job(db_session).id == job.id
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    circuit = db_session.get(models.FiscalProviderCircuit, recovery.scope_for(tenant))
    assert circuit.failures == 1
    circuit.next_probe_at = datetime.now() - timedelta(seconds=1)
    db_session.commit()
    recovered = Mock(wraps=recovery.service_recovered)
    monkeypatch.setattr(recovery, "service_recovered", recovered)

    def consult(*args, **kwargs):
        assert not db_session.in_transaction()
        raise _missing()

    response = dict(panel.recover_invoice.return_value)
    def recover(*args, **kwargs):
        assert not db_session.in_transaction()
        return response

    api.consult_ticket.side_effect = consult
    panel.recover_invoice.side_effect = recover
    _queue_consult(db_session, job)
    assert queue.process_emission_job(job.id, db_session=db_session)
    db_session.expire_all()
    assert document.estado == "facturada"
    assert document.sunat_cdr_content == response["cdr"]
    assert document.sunat_xml_content == signed
    assert document.correlativo == doc_number
    assert tenant.subscription.documents_used == 1
    assert document.source_quote.estado == "facturada"
    assert job.result_snapshot["recovery_source"] == "smartpse_panel"
    assert circuit.failures == 1
    recovered.assert_not_called()
    api.sign_xml.assert_not_called()
    assert api.send_signed_xml.call_count == 1

    # Persisting a second verified lookup does not duplicate economic effects.
    api.consult_ticket.side_effect = _missing()
    panel.recover_invoice.side_effect = None
    again = fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    crud.guardar_respuesta_sunat(db_session, document.id, again, tenant_id=tenant.id)
    assert tenant.subscription.documents_used == 1
    assert api.send_signed_xml.call_count == 1


@pytest.mark.parametrize("primary", [{"estado": 202}, {"estado": 200, "mensaje": "Aceptado"}])
def test_primary_response_without_cdr_uses_panel(panel_sale, primary):
    tenant, user, document, job, api, panel = panel_sale
    api.consult_ticket.side_effect = None
    api.consult_ticket.return_value = primary
    result = fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    assert result["recovery_source"] == "smartpse_panel"
    assert result["cdr_xml"] == _cdr(tenant, document)
    panel.recover_invoice.assert_called_once()
    api.send_signed_xml.assert_not_called()


@pytest.mark.parametrize("panel_result", [
    {"estado": 202}, {"estado": 200, "mensaje": "Aceptado", "provider_document_id": 123},
])
def test_panel_absence_or_ui_acceptance_without_cdr_remains_pending(
    db_session, panel_sale, panel_result, monkeypatch,
):
    tenant, _, document, job, api, panel = panel_sale
    panel.recover_invoice.return_value = dict(panel_result, recovery_source="smartpse_panel")
    recovered = Mock()
    monkeypatch.setattr(recovery, "service_recovered", recovered)
    _queue_consult(db_session, job)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert job.status == "retry"
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    assert document.estado == "pendiente"
    assert not document.sunat_cdr_content
    assert tenant.subscription.documents_used == 0
    assert evidence.has_deliverable_xml(document)
    api.send_signed_xml.assert_not_called()
    recovered.assert_not_called()


@pytest.mark.parametrize("status", [401, 429, 503])
def test_panel_errors_remain_pending_without_changing_sunat_circuit(
    db_session, panel_sale, monkeypatch, status,
):
    tenant, _, document, job, api, panel = panel_sale
    panel.recover_invoice.side_effect = smartpse_client.SmartPSEException(
        "Panel unavailable", {"recovery_source": "smartpse_panel"}, status_code=status,
    )
    failed, recovered = Mock(), Mock()
    monkeypatch.setattr(recovery, "service_failed", failed)
    monkeypatch.setattr(recovery, "service_recovered", recovered)
    _queue_consult(db_session, job)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert document.estado == "pendiente"
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    assert job.status == "retry"
    assert tenant.subscription.documents_used == 0
    assert evidence.has_deliverable_xml(document)
    failed.assert_not_called()
    recovered.assert_not_called()
    api.send_signed_xml.assert_not_called()


def test_panel_rejection_does_not_recover_shared_service(db_session, panel_sale, monkeypatch):
    tenant, _, document, job, api, panel = panel_sale
    panel.recover_invoice.return_value["cdr"] = _cdr(tenant, document, response_code="2335")
    recovered = Mock()
    monkeypatch.setattr(recovery, "service_recovered", recovered)
    _queue_consult(db_session, job)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert job.status == "failed"
    assert document.provider_verification_status == "rejected"
    assert document.sunat_cdr_content
    assert tenant.subscription.documents_used == 0
    recovered.assert_not_called()
    api.send_signed_xml.assert_not_called()


@pytest.mark.parametrize("field,value", [
    ("provider_environment", None), ("provider_environment", "produccion"),
    ("ruc", "20999999999"), ("serie", "F999"), ("correlativo", "99"),
    ("nombre_archivo", "foreign-invoice"),
])
def test_panel_requires_frozen_environment_and_document_identity(panel_sale, field, value):
    _, user, document, job, api, panel = panel_sale
    prepared = deepcopy(job.payload_snapshot["prepared_sale"])
    if field in {"provider_environment", "nombre_archivo"}:
        prepared[field] = value
    elif field == "ruc":
        prepared["payload"]["company"]["ruc"] = value
    else:
        prepared["payload"][field] = value
    with pytest.raises(fiscal.FacturacionException):
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=prepared)
    panel.recover_invoice.assert_not_called()
    api.send_signed_xml.assert_not_called()


def test_panel_never_crosses_tenant_ownership(panel_sale):
    _, user, document, job, api, panel = panel_sale
    document.tenant_id += 1
    with pytest.raises(fiscal.FacturacionException, match="tenant"):
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    api.consult_ticket.assert_not_called()
    panel.recover_invoice.assert_not_called()


def test_disabled_panel_preserves_404_and_never_sends(panel_sale, monkeypatch):
    _, user, document, job, api, panel = panel_sale
    monkeypatch.setattr(smartpse_panel_client, "enabled_for_tenant", lambda tenant_id: False)
    with pytest.raises(fiscal.FacturacionException) as err:
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    assert err.value.status_code == 404
    panel.recover_invoice.assert_not_called()
    api.send_signed_xml.assert_not_called()


def test_legacy_lookup_with_cdr_keeps_existing_contract(panel_sale):
    tenant, user, document, _, api, panel = panel_sale
    api.consult_ticket.side_effect = None
    api.consult_ticket.return_value = {"estado": 200, "cdr": _cdr(tenant, document)}
    result = fiscal.consultar_documento_fiscal(document, user)
    assert result["provider_verification_status"] == "verified"
    assert "recovery_source" not in result
    panel.recover_invoice.assert_not_called()


def test_legacy_missing_cdr_never_infers_panel_environment(panel_sale):
    _, user, document, _, _, panel = panel_sale
    with pytest.raises(fiscal.FacturacionException, match="ambiente fiscal original"):
        fiscal.consultar_documento_fiscal(document, user)
    panel.recover_invoice.assert_not_called()


def test_receipt_never_uses_invoice_panel_fallback(panel_sale):
    _, user, document, job, _, panel = panel_sale
    prepared = deepcopy(job.payload_snapshot["prepared_sale"])
    prepared["payload"]["tipoDoc"] = "03"
    document.tipo_comprobante = "03"
    with pytest.raises(fiscal.FacturacionException) as err:
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=prepared)
    assert err.value.status_code == 404
    panel.recover_invoice.assert_not_called()


def test_panel_foreign_cdr_never_accepts_document(db_session, panel_sale):
    tenant, _, document, job, api, panel = panel_sale
    panel.recover_invoice.return_value["cdr"] = _sale_cdr(document_id="F999-99", ruc=tenant.business_ruc)
    _queue_consult(db_session, job)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert document.estado == "pendiente"
    assert not document.sunat_cdr_content
    assert tenant.subscription.documents_used == 0
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    api.send_signed_xml.assert_not_called()


def test_not_submitted_auth_retry_preserves_xml_and_emit_action_past_max_attempts(
    db_session, panel_sale, monkeypatch,
):
    _, _, document, job, api, panel = panel_sale
    signed, number = document.sunat_xml_content, document.correlativo
    api.send_signed_xml.side_effect = smartpse_client.SmartPSENotSubmitted("CPE auth unavailable")
    job.attempts = job.max_attempts
    db_session.commit()
    assert crud.claim_next_emission_job(db_session).id == job.id
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert job.status == "retry"
    assert job.action == models.EMISSION_JOB_ACTION_EMIT_FISCAL
    assert job.payload_snapshot["send_started"] is False
    assert not job.payload_snapshot.get("sign_only")
    assert document.sunat_xml_content == signed
    assert document.correlativo == number
    api.consult_ticket.assert_not_called()
    api.sign_xml.assert_not_called()
    panel.recover_invoice.assert_not_called()


def test_process_timeout_recovers_xml_and_cdr_with_contingency_disabled(
    db_session, sign_xml, monkeypatch,
):
    monkeypatch.setattr(settings, "FISCAL_CONTINGENCY_TENANT_IDS", "")
    tenant, user, document = _make_fiscal_document(db_session, "09312")
    job, _ = queue.enqueue_fiscal_document_job(db_session, document, user, tipo_comprobante="01")
    signed = sign_xml(job.payload_snapshot["prepared_sale"]["unsigned_xml"]) + "\n"
    assert job.payload_snapshot["recovery_flow"] is False
    assert not recovery.enabled_for_job(job)
    api, panel = Mock(), Mock()
    api.consult_ticket.side_effect = _missing()
    api.process_xml.side_effect = smartpse_client.SmartPSEException("Timeout procesando documento")
    panel.recover_invoice.return_value = {"estado": 200, "cdr": _cdr(tenant, document),
        "xml_firmado": base64.b64encode(signed.encode()).decode(), "recovery_source": "smartpse_panel"}
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: api)
    monkeypatch.setattr(smartpse_panel_client, "get_default_client", lambda: panel)
    monkeypatch.setattr(smartpse_panel_client, "enabled_for_tenant", lambda tenant_id: True)
    async def noop(*args, **kwargs):
        pass
    monkeypatch.setattr(queue.pdf_storage_service, "process_pdf_background", noop)
    monkeypatch.setattr(queue.fiscal_artifact_service, "persist_cdr_artifact", noop)
    db_session.commit()
    assert crud.claim_next_emission_job(db_session).id == job.id
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    assert document.sunat_xml_content is None
    assert not document.sunat_cdr_content

    _queue_consult(db_session, job)
    assert queue.process_emission_job(job.id, db_session=db_session)
    db_session.expire_all()
    assert document.estado == "facturada"
    assert document.sunat_xml_content == signed
    assert document.sunat_cdr_content == _cdr(tenant, document)
    assert document.provider_response["inkora_evidence"]["signed_xml_sha256"] == hashlib.sha256(signed.encode()).hexdigest()
    assert evidence.has_deliverable_xml(document)
    assert tenant.subscription.documents_used == 1
    assert panel.recover_invoice.call_args.kwargs["include_xml"] is True
    assert api.process_xml.call_count == 1
    api.sign_xml.assert_not_called()
    api.send_signed_xml.assert_not_called()


@pytest.mark.parametrize("pending_cdr", [False, True])
@pytest.mark.parametrize("variant", ["tampered", "foreign", "foreign_issuer", "different_amount", "customer_number", "customer_type"])
def test_invalid_recovered_xml_never_accepts_or_stores_cdr(
    db_session, panel_sale, sign_xml, variant, pending_cdr, monkeypatch,
):
    from lxml import etree
    tenant, user, document, job, api, panel = panel_sale
    prepared = job.payload_snapshot["prepared_sale"]
    if variant == "tampered":
        root = etree.fromstring(document.sunat_xml_content.encode())
        root.find("cbc:ID", namespaces=evidence.smartpse_response.NS).text = "F999-99"
        recovered_xml = etree.tostring(root).decode()
    else:
        root = etree.fromstring(prepared["unsigned_xml"].encode())
        if variant == "foreign":
            root.find("cbc:ID", namespaces=evidence.smartpse_response.NS).text = "F999-99"
        elif variant == "foreign_issuer":
            root.find("cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID",
                      namespaces=evidence.smartpse_response.NS).text = "20999999999"
        elif variant == "different_amount":
            root.find("cac:LegalMonetaryTotal/cbc:PayableAmount", namespaces=evidence.smartpse_response.NS).text = "999.00"
        else:
            receiver = root.find("cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID",
                                 namespaces=evidence.smartpse_response.NS)
            if variant == "customer_number":
                receiver.text = "20999999999"
            else:
                receiver.set("schemeID", "1")
        recovered_xml = sign_xml(etree.tostring(root).decode())
    document.sunat_xml_content = None
    document.provider_response = None
    pdf = AsyncMock()
    monkeypatch.setattr(queue.pdf_storage_service, "process_pdf_background", pdf)
    panel.recover_invoice.return_value["xml_firmado"] = base64.b64encode(recovered_xml.encode()).decode()
    if pending_cdr:
        panel.recover_invoice.return_value.update(estado=202, cdr=None)
    with pytest.raises(fiscal.FacturacionException, match="Evidencia XML invalida") as err:
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=prepared)
    assert err.value.provider_response["xml_firmado"] == panel.recover_invoice.return_value["xml_firmado"]
    _queue_consult(db_session, job)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert document.estado == "pendiente"
    assert document.sunat_xml_content is None
    assert not evidence.has_deliverable_xml(document)
    assert not document.sunat_cdr_content
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    assert tenant.subscription.documents_used == 0
    assert panel.recover_invoice.call_args.kwargs["include_xml"] is True
    api.process_xml.assert_not_called()
    api.send_signed_xml.assert_not_called()
    pdf.assert_not_called()


@pytest.mark.parametrize("panel_status", [202, 200, "firmado"])
def test_pending_recovered_xml_is_retained_and_deliverable_without_acceptance(
    db_session, panel_sale, monkeypatch, panel_status,
):
    tenant, user, document, job, api, panel = panel_sale
    signed = document.sunat_xml_content
    document.sunat_xml_content = None
    document.provider_response = None
    panel.recover_invoice.return_value = {
        "estado": panel_status, "cdr": None, "xml_firmado": base64.b64encode(signed.encode()).decode(),
        "recovery_source": "smartpse_panel", "provider_document_id": "444364", "environment": "demo",
    }
    with pytest.raises(fiscal.FacturacionException) as err:
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    assert err.value.partial_result["pending"] is True
    assert err.value.partial_result["xml"] == signed
    assert err.value.provider_response["xml_firmado"] == signed
    assert err.value.provider_response["provider_document_id"] == "444364"
    assert err.value.provider_response["environment"] == "demo"
    pdf = AsyncMock()
    monkeypatch.setattr(queue.pdf_storage_service, "process_pdf_background", pdf)
    _queue_consult(db_session, job)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    db_session.expire_all()
    assert document.estado == "pendiente"
    assert document.sunat_accepted is not True
    assert document.sunat_xml_content == signed
    assert not document.sunat_cdr_content
    assert document.sunat_qr_payload
    assert document.provider_verification_status == "pending_confirmation"
    assert evidence.has_deliverable_xml(document)
    assert tenant.subscription.documents_used == 0
    assert document.source_quote.estado != "facturada"
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    assert job.status == "retry"
    pdf.assert_awaited_once_with(document.id, tenant.id)
    api.process_xml.assert_not_called()
    api.sign_xml.assert_not_called()
    api.send_signed_xml.assert_not_called()


def test_panel_without_cdr_or_xml_retains_pending_state_without_pdf(db_session, panel_sale, monkeypatch):
    tenant, _, document, job, api, panel = panel_sale
    document.sunat_xml_content = None
    document.provider_response = None
    panel.recover_invoice.return_value = {"estado": 202, "cdr": None, "recovery_source": "smartpse_panel"}
    pdf = AsyncMock()
    monkeypatch.setattr(queue.pdf_storage_service, "process_pdf_background", pdf)
    _queue_consult(db_session, job)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert document.estado == "pendiente"
    assert document.sunat_xml_content is None
    assert not document.sunat_cdr_content
    assert not evidence.has_deliverable_xml(document)
    assert tenant.subscription.documents_used == 0
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    assert job.status == "retry"
    pdf.assert_not_called()
    api.send_signed_xml.assert_not_called()


def test_cdr_without_requested_xml_stays_pending(db_session, panel_sale):
    tenant, _, document, job, api, panel = panel_sale
    document.sunat_xml_content = None
    document.provider_response = None
    _queue_consult(db_session, job)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert document.estado == "pendiente"
    assert not document.sunat_cdr_content
    assert tenant.subscription.documents_used == 0
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    api.process_xml.assert_not_called()


def test_valid_local_xml_is_preserved_without_requesting_replacement(panel_sale):
    _, user, document, job, _, panel = panel_sale
    signed = document.sunat_xml_content
    result = fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    assert result["xml"] == signed
    assert panel.recover_invoice.call_args.kwargs["include_xml"] is False


def test_panel_unsolicited_different_xml_cannot_replace_frozen_evidence(panel_sale):
    _, user, document, job, _, panel = panel_sale
    signed = document.sunat_xml_content
    panel.recover_invoice.return_value["xml_firmado"] = signed + "\n"
    with pytest.raises(fiscal.FacturacionException, match="otro XML"):
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    assert document.sunat_xml_content == signed
    assert panel.recover_invoice.call_args.kwargs["include_xml"] is False


@pytest.mark.parametrize("panel_response", [
    {"estado": 202, "cdr": None},
    {"estado": 200, "mensaje": "Firmado", "cdr": None},
])
def test_valid_api_xml_survives_panel_without_xml_and_is_retained(
    db_session, panel_sale, monkeypatch, panel_response,
):
    tenant, user, document, job, api, panel = panel_sale
    signed = document.sunat_xml_content
    document.sunat_xml_content = None
    document.provider_response = None
    api.consult_ticket.side_effect = None
    api.consult_ticket.return_value = {"estado": 202, "xml_firmado": base64.b64encode(signed.encode()).decode()}
    panel.recover_invoice.return_value = dict(panel_response, provider_document_id="444364", environment="demo")
    with pytest.raises(fiscal.FacturacionException) as err:
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    assert err.value.partial_result["xml"] == signed
    assert err.value.partial_result["pending"] is True
    assert err.value.partial_result["recovery_source"] == "smartpse_panel"
    assert err.value.provider_response["provider_document_id"] == "444364"
    assert panel.recover_invoice.call_args.kwargs["include_xml"] is True
    pdf = AsyncMock()
    monkeypatch.setattr(queue.pdf_storage_service, "process_pdf_background", pdf)
    _queue_consult(db_session, job)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    db_session.expire_all()
    assert document.sunat_xml_content == signed
    assert evidence.has_deliverable_xml(document)
    assert document.sunat_qr_payload
    assert document.estado == "pendiente" and not document.sunat_accepted
    assert not document.sunat_cdr_content
    assert tenant.subscription.documents_used == 0
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL and job.status == "retry"
    pdf.assert_awaited_once_with(document.id, tenant.id)
    api.sign_xml.assert_not_called()
    api.send_signed_xml.assert_not_called()


@pytest.mark.parametrize("panel_xml", [False, True])
def test_valid_api_xml_and_panel_cdr_reconcile_once(db_session, panel_sale, panel_xml):
    tenant, _, document, job, api, panel = panel_sale
    signed = document.sunat_xml_content
    document.sunat_xml_content = None
    document.provider_response = None
    api.consult_ticket.side_effect = None
    api.consult_ticket.return_value = {"estado": 202, "xml_firmado": signed}
    if panel_xml:
        panel.recover_invoice.return_value["xml_firmado"] = base64.b64encode(signed.encode()).decode()
    _queue_consult(db_session, job)
    assert queue.process_emission_job(job.id, db_session=db_session)
    db_session.expire_all()
    assert document.sunat_xml_content == signed
    assert document.sunat_cdr_content == _cdr(tenant, document)
    assert document.estado == "facturada" and document.sunat_accepted
    assert tenant.subscription.documents_used == 1
    assert job.result_snapshot["recovery_source"] == "smartpse_panel"
    api.sign_xml.assert_not_called()
    api.send_signed_xml.assert_not_called()


@pytest.mark.parametrize("has_cdr", [False, True])
def test_panel_xml_discordance_preserves_first_api_xml_without_acceptance(
    db_session, panel_sale, has_cdr,
):
    tenant, user, document, job, api, panel = panel_sale
    signed = document.sunat_xml_content
    document.sunat_xml_content = None
    document.provider_response = None
    api.consult_ticket.side_effect = None
    api.consult_ticket.return_value = {"estado": 202, "xml_firmado": signed}
    different_xml = signed + "\n"
    panel.recover_invoice.return_value["xml_firmado"] = different_xml
    if not has_cdr:
        panel.recover_invoice.return_value.update(estado=202, cdr=None)
    with pytest.raises(fiscal.FacturacionException, match="otro XML") as err:
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    assert err.value.partial_result["xml"] == signed
    assert err.value.provider_response["xml_firmado"] == different_xml
    _queue_consult(db_session, job)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    db_session.expire_all()
    assert document.sunat_xml_content == signed
    assert document.provider_response["process"]["xml_firmado"] == different_xml
    assert document.estado == "pendiente" and not document.sunat_accepted
    assert not document.sunat_cdr_content
    assert tenant.subscription.documents_used == 0
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL and job.status == "retry"
    api.sign_xml.assert_not_called()
    api.send_signed_xml.assert_not_called()


@pytest.fixture
def real_panel_sale(db_session, panel_sale, sign_xml):
    tenant, user, document, job, api, panel = panel_sale
    # The shared mock fixture uses an alphanumeric RUC; real panel scope requires
    # an eleven-digit identity, with payload and signature prepared consistently.
    tenant.business_ruc = "20606751509"
    prepared = fiscal.prepare_sale_document(document, db_session, user, "01")
    job.payload_snapshot = dict(job.payload_snapshot, prepared_sale=prepared)
    signed = sign_xml(prepared["unsigned_xml"]) + "\n"
    document.sunat_xml_content = None
    document.provider_response = None
    api.consult_ticket.side_effect = None
    api.consult_ticket.return_value = {"estado": 202, "xml_firmado": signed}
    db_session.commit()
    return tenant, user, document, job, api, panel, signed


def test_api_xml_and_real_panel_cdr_survive_missing_panel_xml(db_session, real_panel_sale, monkeypatch):
    tenant, _, document, job, api, _, signed = real_panel_sale
    prepared = job.payload_snapshot["prepared_sale"]
    panel_row = row(company_id=tenant.smartpse_company_id, environment=tenant.smartpse_environment,
                    xml_filename=prepared["nombre_archivo"], has_signed_xml=True)
    raw_cdr = panel_cdr(issuer=tenant.business_ruc, reference=f"{document.serie}-{document.correlativo}")
    client, sessions = client_for(login() + [listing([panel_row]),
        Response(body=raw_cdr, content_type="application/xml"), Response(404)])
    monkeypatch.setattr(smartpse_panel_client, "get_default_client", lambda: client)
    _queue_consult(db_session, job)
    assert queue.process_emission_job(job.id, db_session=db_session), job.last_error
    db_session.expire_all()
    assert document.sunat_xml_content == signed
    assert document.sunat_cdr_content == raw_cdr.decode()
    assert document.estado == "facturada" and document.sunat_accepted
    assert document.provider_response["estado"] == 202
    assert tenant.subscription.documents_used == 1
    assert job.result_snapshot["recovery_source"] == "smartpse_panel"
    calls = sessions[0].calls
    assert calls[-2][1].endswith("/cdr") and calls[-1][1].endswith("/xml")
    assert [call[1] for call in calls if call[0] == "POST"] == [smartpse_panel_client.ORIGIN + "/login"]
    api.sign_xml.assert_not_called()
    api.send_signed_xml.assert_not_called()


def test_api_xml_survives_real_panel_timeout(db_session, real_panel_sale, monkeypatch):
    tenant, user, document, job, api, _, signed = real_panel_sale
    client, sessions = client_for(login() + [requests.Timeout("offline panel timeout"),
                                            requests.Timeout("offline panel timeout")])
    monkeypatch.setattr(smartpse_panel_client, "get_default_client", lambda: client)
    with pytest.raises(fiscal.FacturacionException) as err:
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    assert err.value.partial_result["xml"] == signed
    assert isinstance(err.value.__cause__, smartpse_panel_client.SmartPSEPanelException)
    _queue_consult(db_session, job)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    db_session.expire_all()
    assert document.sunat_xml_content == signed and evidence.has_deliverable_xml(document)
    assert document.estado == "pendiente" and not document.sunat_accepted
    assert not document.sunat_cdr_content
    assert tenant.subscription.documents_used == 0
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL and job.status == "retry"
    assert [call[1] for call in sessions[0].calls if call[0] == "POST"] == [smartpse_panel_client.ORIGIN + "/login"]
    api.sign_xml.assert_not_called()
    api.send_signed_xml.assert_not_called()


@pytest.mark.parametrize("status", [404, 500, 503])
def test_valid_xml_in_api_error_is_retained_after_pending_panel(db_session, panel_sale, status):
    tenant, user, document, job, api, panel = panel_sale
    signed = document.sunat_xml_content
    document.sunat_xml_content = None
    document.provider_response = None
    api.consult_ticket.side_effect = smartpse_client.SmartPSEException(
        "API unavailable", {"estado": status, "xml_firmado": base64.b64encode(signed.encode()).decode()},
        status_code=status)
    panel.recover_invoice.return_value = {"estado": 202, "cdr": None}
    with pytest.raises(fiscal.FacturacionException) as err:
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    assert err.value.partial_result["xml"] == signed
    assert err.value.partial_result["pending"] is True
    assert err.value.partial_result["recovery_source"] == "smartpse_panel"
    assert err.value.partial_result.get("api_transport_failure") is (True if status >= 500 else None)
    _queue_consult(db_session, job)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    db_session.expire_all()
    assert document.sunat_xml_content == signed and evidence.has_deliverable_xml(document)
    assert document.estado == "pendiente" and not document.sunat_accepted
    assert not document.sunat_cdr_content and tenant.subscription.documents_used == 0
    api.sign_xml.assert_not_called()
    api.send_signed_xml.assert_not_called()


def test_api_error_xml_and_discordant_panel_xml_never_accept(db_session, panel_sale):
    tenant, user, document, job, api, panel = panel_sale
    signed = document.sunat_xml_content
    document.sunat_xml_content = None
    document.provider_response = None
    api.consult_ticket.side_effect = smartpse_client.SmartPSEException(
        "API unavailable", {"xml_firmado": signed}, status_code=503)
    panel.recover_invoice.return_value["xml_firmado"] = signed + "\n"
    with pytest.raises(fiscal.FacturacionException) as err:
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    assert err.value.partial_result["xml"] == signed
    assert err.value.partial_result["api_transport_failure"] is True
    _queue_consult(db_session, job)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    db_session.expire_all()
    assert document.sunat_xml_content == signed
    assert document.estado == "pendiente" and not document.sunat_accepted
    assert not document.sunat_cdr_content and tenant.subscription.documents_used == 0
    api.sign_xml.assert_not_called()
    api.send_signed_xml.assert_not_called()


def test_invalid_xml_in_api_error_cannot_authorize_panel_recovery(panel_sale):
    _, user, document, job, api, panel = panel_sale
    document.sunat_xml_content = None
    api.consult_ticket.side_effect = smartpse_client.SmartPSEException(
        "API unavailable", {"xml_firmado": job.payload_snapshot["prepared_sale"]["unsigned_xml"]}, status_code=503)
    with pytest.raises(fiscal.FacturacionException, match="firma digital") as err:
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    assert err.value.partial_result["api_transport_failure"] is True
    assert not err.value.partial_result.get("xml")
    panel.recover_invoice.assert_not_called()
