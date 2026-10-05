"""Offline API reconciliation and persistence preserve the frozen signed sale."""
import base64
from lxml import etree
import pytest
import requests

import crud
import models
from services import facturacion_service as fiscal, fiscal_evidence_service as evidence
from services import emission_queue_service as queue, smartpse_client, smartpse_panel_client
from test_fiscal_contingency_recovery import sale, sign_xml
from test_smartpse_panel_reconciliation import panel_sale, _cdr, _queue_consult
from test_smartpse_response_normalization import _zip_b64


def _different_xml(document, prepared, sign_xml, variant):
    if variant == "bytes":
        return document.sunat_xml_content + "\n"
    root = etree.fromstring(prepared["unsigned_xml"].encode())
    ns = evidence.smartpse_response.NS
    if variant == "foreign":
        root.find("cbc:ID", namespaces=ns).text = "F999-99"
    elif variant == "customer":
        root.find("cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID", namespaces=ns).text = "20999999999"
    else:
        root.find("cac:LegalMonetaryTotal/cbc:PayableAmount", namespaces=ns).text = "999.00"
    changed = sign_xml(etree.tostring(root).decode())
    if variant == "tampered":
        return changed.replace("999.00", "998.00")
    return changed


@pytest.mark.parametrize("variant", ["bytes", "foreign", "customer", "amount", "tampered"])
def test_api_conflicting_xml_preserves_frozen_document_and_reconciliation(db_session, panel_sale, sign_xml, variant):
    tenant, user, document, job, api, panel = panel_sale
    prepared = job.payload_snapshot["prepared_sale"]
    signed = document.sunat_xml_content
    remote = _different_xml(document, prepared, sign_xml, variant)
    api.consult_ticket.side_effect = None
    api.consult_ticket.return_value = {"estado": 200, "cdr": _cdr(tenant, document), "xml_firmado": remote}
    with pytest.raises(fiscal.FacturacionException, match="otro XML") as err:
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=prepared)
    assert err.value.provider_response["xml_firmado"] == remote
    _queue_consult(db_session, job)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert document.sunat_xml_content == signed
    assert document.estado == "pendiente"
    assert not document.sunat_cdr_content
    assert document.sunat_accepted is not True
    assert tenant.subscription.documents_used == 0
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    assert job.status == "retry"
    api.send_signed_xml.assert_not_called()
    panel.recover_invoice.assert_not_called()


@pytest.mark.parametrize("variant", ["foreign", "customer", "amount", "tampered"])
def test_api_recovered_xml_without_local_requires_full_signature_and_payload(panel_sale, sign_xml, variant):
    tenant, user, document, job, api, panel = panel_sale
    prepared = job.payload_snapshot["prepared_sale"]
    remote = _different_xml(document, prepared, sign_xml, variant)
    document.sunat_xml_content = None
    document.provider_response = None
    api.consult_ticket.side_effect = None
    api.consult_ticket.return_value = {"estado": 200, "cdr": _cdr(tenant, document), "xml_firmado": remote}
    with pytest.raises(fiscal.FacturacionException, match="Evidencia XML invalida"):
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=prepared)
    assert document.sunat_xml_content is None
    assert tenant.subscription.documents_used == 0
    panel.recover_invoice.assert_not_called()


@pytest.mark.parametrize("encoding", ["raw", "base64", "zip"])
@pytest.mark.parametrize("local", [True, False])
def test_api_exact_signed_xml_is_verified_without_changing_bytes(panel_sale, encoding, local):
    tenant, user, document, job, api, panel = panel_sale
    signed = document.sunat_xml_content
    encoded = {"raw": signed, "base64": base64.b64encode(signed.encode()).decode(),
               "zip": _zip_b64("signed.xml", signed)}[encoding]
    if not local:
        document.sunat_xml_content = None
        document.provider_response = None
    api.consult_ticket.side_effect = None
    api.consult_ticket.return_value = {"estado": 200, "cdr": _cdr(tenant, document), "xml_firmado": encoded}
    result = fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    assert result["xml"] == signed
    assert result["provider_verification_status"] == "verified"
    assert not result["pending"]
    panel.recover_invoice.assert_not_called()


@pytest.mark.parametrize("variant", ["bytes", "foreign", "tampered"])
def test_crud_rejects_replacement_before_cdr_or_economic_side_effects(db_session, panel_sale, sign_xml, variant):
    tenant, _, document, job, _, _ = panel_sale
    signed = document.sunat_xml_content
    response = document.provider_response
    original_hash = document.sunat_hash
    remote = _different_xml(document, job.payload_snapshot["prepared_sale"], sign_xml, variant)
    result = {"success": True, "xml": remote, "cdr_xml": _cdr(tenant, document), "hash": "foreign-hash",
              "provider_response": {"xml_firmado": remote}, "provider_verification_status": "verified"}
    with pytest.raises(smartpse_client.SmartPSEException, match="otro XML"):
        crud.guardar_respuesta_sunat(db_session, document.id, result, tenant_id=tenant.id)
    assert document.sunat_xml_content == signed
    assert document.sunat_hash == original_hash
    assert document.provider_response == response
    assert not document.sunat_cdr_content
    assert document.estado == "pendiente"
    assert tenant.subscription.documents_used == 0
    assert document.source_quote.estado != "facturada"


def test_crud_exact_xml_allows_idempotent_acceptance(db_session, panel_sale):
    tenant, user, document, job, _, _ = panel_sale
    signed = document.sunat_xml_content
    result = fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    for _ in range(2):
        crud.guardar_respuesta_sunat(db_session, document.id, result, tenant_id=tenant.id)
    assert document.sunat_xml_content == signed
    assert document.estado == "facturada"
    assert tenant.subscription.documents_used == 1


def test_helper_rejects_conflicting_xml_aliases(panel_sale):
    _, _, document, job, _, _ = panel_sale
    signed = document.sunat_xml_content
    response = {"xml_firmado": signed, "xml": signed + "\n"}
    with pytest.raises(smartpse_client.SmartPSEException, match="otro XML") as err:
        fiscal.validate_sale_response_xml(job.payload_snapshot["prepared_sale"]["payload"], response, frozen_xml=signed)
    assert err.value.response_data == response


def test_primary_pending_conflict_is_not_hidden_by_panel_fallback(panel_sale):
    _, user, document, job, api, panel = panel_sale
    api.consult_ticket.side_effect = None
    api.consult_ticket.return_value = {"estado": 202, "xml_firmado": document.sunat_xml_content + "\n"}
    with pytest.raises(fiscal.FacturacionException, match="otro XML"):
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    panel.recover_invoice.assert_not_called()


def _consult_outage(kind):
    if kind == "503":
        return smartpse_client.SmartPSEException("API outage", {"estado": 503}, status_code=503)
    exc = smartpse_client.SmartPSEException("Transport outage")
    exc.__cause__ = requests.exceptions.Timeout() if kind == "timeout" else requests.exceptions.ConnectionError()
    return exc


@pytest.mark.parametrize("kind", ["503", "timeout", "connection"])
def test_api_outage_reads_existing_panel_evidence_without_sending(panel_sale, kind):
    _, user, document, job, api, panel = panel_sale
    api.consult_ticket.side_effect = _consult_outage(kind)
    result = fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    assert result["recovery_source"] == "smartpse_panel"
    assert result["api_transport_failure"] is True
    assert result["provider_verification_status"] == "verified"
    panel.recover_invoice.assert_called_once()
    api.send_signed_xml.assert_not_called()


@pytest.mark.parametrize("kind", ["503", "timeout", "connection"])
def test_panel_failure_after_api_outage_preserves_primary_error(panel_sale, kind):
    _, user, document, job, api, panel = panel_sale
    original = _consult_outage(kind)
    api.consult_ticket.side_effect = original
    panel.recover_invoice.side_effect = smartpse_panel_client.SmartPSEPanelException("Panel outage", status_code=503)
    with pytest.raises(fiscal.FacturacionException) as err:
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    assert err.value.__cause__ is original
    assert err.value.status_code == original.status_code
    assert err.value.provider_response == original.response_data
    assert "recovery_source" not in err.value.provider_response


@pytest.mark.parametrize("status", [401, 403, 422, 429])
def test_typed_non_outage_status_never_uses_panel(panel_sale, status):
    _, user, document, job, api, panel = panel_sale
    api.consult_ticket.side_effect = smartpse_client.SmartPSEException("Timeout supplied as text", status_code=status)
    with pytest.raises(fiscal.FacturacionException):
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    panel.recover_invoice.assert_not_called()


def test_untyped_error_text_cannot_enable_transport_fallback(panel_sale):
    _, user, document, job, api, panel = panel_sale
    api.consult_ticket.side_effect = smartpse_client.SmartPSEException("Timeout supplied as text")
    with pytest.raises(fiscal.FacturacionException):
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    panel.recover_invoice.assert_not_called()


def test_api_outage_panel_xml_only_remains_pending_with_no_quota(db_session, panel_sale):
    tenant, user, document, job, api, panel = panel_sale
    signed = document.sunat_xml_content
    document.sunat_xml_content = None
    document.provider_response = None
    api.consult_ticket.side_effect = _consult_outage("503")
    panel.recover_invoice.return_value = {"estado": 202, "cdr": None, "xml_firmado": signed}
    with pytest.raises(fiscal.FacturacionException) as err:
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    assert err.value.partial_result["api_transport_failure"] is True
    assert err.value.partial_result["recovery_source"] == "smartpse_panel"
    _queue_consult(db_session, job)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    assert document.sunat_xml_content == signed
    assert evidence.has_deliverable_xml(document)
    assert document.estado == "pendiente"
    assert tenant.subscription.documents_used == 0
    assert job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    api.send_signed_xml.assert_not_called()


def test_panel_recovery_after_404_does_not_claim_api_transport_failure(panel_sale):
    _, user, document, job, _, _ = panel_sale
    result = fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    assert result["recovery_source"] == "smartpse_panel"
    assert "api_transport_failure" not in result


def test_api_outage_panel_rejection_preserves_internal_failure_marker(panel_sale):
    tenant, user, document, job, api, panel = panel_sale
    api.consult_ticket.side_effect = _consult_outage("503")
    panel.recover_invoice.return_value["cdr"] = _cdr(tenant, document, response_code="2335")
    with pytest.raises(fiscal.FacturacionRejectedException) as err:
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    assert err.value.partial_result["api_transport_failure"] is True
    assert err.value.partial_result["recovery_source"] == "smartpse_panel"


def test_api_cannot_forge_internal_recovery_metadata(panel_sale):
    tenant, user, document, job, api, panel = panel_sale
    api.consult_ticket.side_effect = None
    api.consult_ticket.return_value = {"estado": 200, "cdr": _cdr(tenant, document),
        "xml_firmado": document.sunat_xml_content, "recovery_source": "smartpse_panel",
        "api_transport_failure": True}
    result = fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    assert "recovery_source" not in result
    assert "api_transport_failure" not in result
    assert "recovery_source" not in result["provider_response"]
    assert "api_transport_failure" not in result["provider_response"]
    panel.recover_invoice.assert_not_called()


def test_api_forged_panel_source_cannot_skip_xml_validation(panel_sale):
    tenant, user, document, job, api, panel = panel_sale
    api.consult_ticket.side_effect = None
    api.consult_ticket.return_value = {"estado": 200, "cdr": _cdr(tenant, document),
        "xml_firmado": document.sunat_xml_content + "\n", "recovery_source": "smartpse_panel",
        "api_transport_failure": False}
    with pytest.raises(fiscal.FacturacionException, match="otro XML") as err:
        fiscal.consultar_documento_fiscal(document, user, prepared_sale=job.payload_snapshot["prepared_sale"])
    assert "recovery_source" not in err.value.partial_result
    assert "api_transport_failure" not in err.value.partial_result
    assert "recovery_source" not in err.value.provider_response
    assert "api_transport_failure" not in err.value.provider_response
    panel.recover_invoice.assert_not_called()
