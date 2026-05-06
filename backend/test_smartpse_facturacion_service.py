import base64
import zipfile
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

import crud
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from services import facturacion_service


def _zip_b64(filename: str, content: str) -> str:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(filename, content)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _make_smartpse_fiscal_document(db_session):
    tenant = make_tenant(db_session, "9001")
    tenant.smartpse_company_id = "77"
    tenant.smartpse_environment = "demo"
    tenant.smartpse_usuario_secundaria = "AB3KPQR9"
    tenant.smartpse_token_acceso = "MX7TNVQG"
    user = make_user(db_session, tenant, email="smartpse-facturacion@test.com")
    cliente = make_cliente(db_session, tenant, "9001", tipo_documento="6", numero_documento="20191308868")
    quote = make_quote_via_crud(db_session, tenant, user, cliente)
    fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
    db_session.commit()
    return tenant, user, fiscal


def test_emitir_factura_uses_smartpse_xml_flow_without_apisperu_http(db_session):
    tenant, user, fiscal = _make_smartpse_fiscal_document(db_session)
    signed_xml = f"""<?xml version='1.0'?>
<Invoice xmlns='urn:oasis:names:specification:ubl:schema:xsd:Invoice-2'
    xmlns:cac='urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'
    xmlns:cbc='urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'>
  <cbc:ID>F001-000001</cbc:ID>
  <cbc:IssueDate>2026-05-05</cbc:IssueDate>
  <cbc:IssueTime>10:30:00</cbc:IssueTime>
  <cbc:InvoiceTypeCode>01</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>PEN</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty><cac:Party><cac:PartyIdentification><cbc:ID schemeID='6'>{tenant.business_ruc}</cbc:ID></cac:PartyIdentification><cac:PartyLegalEntity><cbc:RegistrationName>INKORA TEST SAC</cbc:RegistrationName></cac:PartyLegalEntity></cac:Party></cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty><cac:Party><cac:PartyIdentification><cbc:ID schemeID='6'>20191308868</cbc:ID></cac:PartyIdentification><cac:PartyLegalEntity><cbc:RegistrationName>CLIENTE SAC</cbc:RegistrationName></cac:PartyLegalEntity></cac:Party></cac:AccountingCustomerParty>
  <cac:TaxTotal><cbc:TaxAmount currencyID='PEN'>18.00</cbc:TaxAmount></cac:TaxTotal>
  <cac:LegalMonetaryTotal><cbc:PayableAmount currencyID='PEN'>118.00</cbc:PayableAmount></cac:LegalMonetaryTotal>
</Invoice>"""
    fake_client = MagicMock()
    fake_client.process_xml.return_value = {
        "estado": 200,
        "mensaje": "Aceptado por SUNAT",
        "xml_firmado": _zip_b64("signed.xml", signed_xml),
        "codigo_hash": "hash-smart",
        "cdr": "<ApplicationResponse/>",
        "rechazado": False,
    }

    with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=fake_client), patch(
        "services.facturacion_service.requests.post",
        side_effect=AssertionError("APISPeru HTTP should not be called"),
    ):
        result = facturacion_service.emitir_factura(fiscal, db_session, user)

    assert result["success"] is True
    assert result["hash"] == "hash-smart"
    assert result["xml"] == signed_xml
    assert result["qr_payload"]["ruc"] == tenant.business_ruc
    fake_client.process_xml.assert_called_once()
    called_tenant, filename, xml_content = fake_client.process_xml.call_args.args
    assert called_tenant.id == tenant.id
    assert filename.startswith(f"{tenant.business_ruc}-01-")
    assert b"<ns0:Invoice" in xml_content or b"<Invoice" in xml_content
    assert fake_client.process_xml.call_args.kwargs["demo"] is True


def test_retenciones_and_percepciones_are_blocked_for_smartpse_v1(db_session):
    _, user, _ = _make_smartpse_fiscal_document(db_session)

    with pytest.raises(facturacion_service.FacturacionException) as retencion_error:
        facturacion_service.emitir_retencion({"serie": "R001", "correlativo": "1"}, user, prepared=True)
    with pytest.raises(facturacion_service.FacturacionException) as percepcion_error:
        facturacion_service.emitir_percepcion({"serie": "P001", "correlativo": "1"}, user, prepared=True)

    assert "Smart PSE v1" in str(retencion_error.value)
    assert "Smart PSE v1" in str(percepcion_error.value)


def test_descargar_xml_uses_persisted_smartpse_xml_without_apisperu(db_session):
    _, user, fiscal = _make_smartpse_fiscal_document(db_session)
    fiscal.sunat_xml_content = "<Invoice><cbc:ID>F001-1</cbc:ID></Invoice>"
    db_session.commit()

    with patch(
        "services.facturacion_service.requests.post",
        side_effect=AssertionError("APISPeru HTTP should not be called"),
    ):
        content = facturacion_service.descargar_archivo("xml", fiscal, user)

    assert content == fiscal.sunat_xml_content.encode("utf-8")
