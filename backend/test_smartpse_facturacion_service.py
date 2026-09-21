import base64
import zipfile
from io import BytesIO
from types import SimpleNamespace
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


def _sale_xml(tenant, *, doc_id="F001-00000001", issue_date="2026-05-05", tipo_doc="01"):
    return f"""<?xml version='1.0'?>
<Invoice xmlns='urn:oasis:names:specification:ubl:schema:xsd:Invoice-2'
    xmlns:cac='urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'
    xmlns:cbc='urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'>
  <cbc:ID>{doc_id}</cbc:ID>
  <cbc:IssueDate>{issue_date}</cbc:IssueDate>
  <cbc:IssueTime>10:30:00</cbc:IssueTime>
  <cbc:InvoiceTypeCode>{tipo_doc}</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>PEN</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty><cac:Party><cac:PartyIdentification><cbc:ID schemeID='6'>{tenant.business_ruc}</cbc:ID></cac:PartyIdentification><cac:PartyLegalEntity><cbc:RegistrationName>INKORA TEST SAC</cbc:RegistrationName></cac:PartyLegalEntity></cac:Party></cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty><cac:Party><cac:PartyIdentification><cbc:ID schemeID='6'>20191308868</cbc:ID></cac:PartyIdentification><cac:PartyLegalEntity><cbc:RegistrationName>CLIENTE SAC</cbc:RegistrationName></cac:PartyLegalEntity></cac:Party></cac:AccountingCustomerParty>
  <cac:TaxTotal><cbc:TaxAmount currencyID='PEN'>18.00</cbc:TaxAmount></cac:TaxTotal>
  <cac:LegalMonetaryTotal><cbc:PayableAmount currencyID='PEN'>118.00</cbc:PayableAmount></cac:LegalMonetaryTotal>
</Invoice>"""


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
    signed_xml = _sale_xml(tenant, issue_date=fiscal.fecha_emision.date().isoformat())
    fake_client = MagicMock()
    fake_client.process_xml.return_value = {
        "estado": 200,
        "mensaje": "Aceptado por SUNAT",
        "xml_firmado": _zip_b64("signed.xml", signed_xml),
        "codigo_hash": "hash-smart",
        "cdr": "<ApplicationResponse/>",
        "rechazado": False,
    }
    fake_client.consult_ticket.return_value = {
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
    assert filename.endswith("-00000001")
    assert b"<ns0:Invoice" in xml_content or b"<Invoice" in xml_content
    assert fake_client.process_xml.call_args.kwargs["demo"] is True
    fake_client.consult_ticket.assert_called_once_with(called_tenant, filename)
    assert result["provider_document_name"] == filename
    assert result["provider_verification_status"] == "verified"
    assert result["provider_verified_at"]


def test_emitir_factura_bloquea_produccion_smartpse_si_runtime_fiscal_no_es_produccion(
    db_session,
    monkeypatch,
):
    tenant, user, fiscal = _make_smartpse_fiscal_document(db_session)
    tenant.smartpse_environment = "produccion"
    db_session.commit()
    monkeypatch.setattr(facturacion_service.settings, "FISCAL_ENV", "beta")
    fake_client = MagicMock()

    with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=fake_client):
        with pytest.raises(facturacion_service.FacturacionException) as exc:
            facturacion_service.emitir_factura(fiscal, db_session, user)

    assert "FISCAL_ENV=production" in str(exc.value)
    fake_client.process_xml.assert_not_called()


@pytest.mark.parametrize("environment", ["produccion", "production", "prod"])
def test_smartpse_production_aliases_never_degrade_to_demo(monkeypatch, environment):
    monkeypatch.setattr(facturacion_service.settings, "FISCAL_ENV", "beta")
    user = SimpleNamespace(tenant=SimpleNamespace(smartpse_environment=environment))

    with pytest.raises(facturacion_service.FacturacionException) as exc_info:
        facturacion_service._smartpse_demo_mode(user)

    assert "Emision bloqueada" in str(exc_info.value)


def test_smartpse_unknown_environment_is_blocked(monkeypatch):
    monkeypatch.setattr(facturacion_service.settings, "FISCAL_ENV", "beta")
    user = SimpleNamespace(tenant=SimpleNamespace(smartpse_environment="sandbox-typo"))

    with pytest.raises(facturacion_service.FacturacionException) as exc_info:
        facturacion_service._smartpse_demo_mode(user)

    assert "no reconocido" in str(exc_info.value)


def test_emitir_factura_usa_endpoint_produccion_si_tenant_y_runtime_son_produccion(
    db_session,
    monkeypatch,
):
    tenant, user, fiscal = _make_smartpse_fiscal_document(db_session)
    tenant.smartpse_environment = "produccion"
    db_session.commit()
    monkeypatch.setattr(facturacion_service.settings, "FISCAL_ENV", "production")
    signed_xml = _sale_xml(tenant, issue_date=fiscal.fecha_emision.date().isoformat())
    fake_client = MagicMock()
    fake_client.process_xml.return_value = {
        "estado": 200,
        "mensaje": "Aceptado por SUNAT",
        "xml_firmado": _zip_b64("signed.xml", signed_xml),
        "codigo_hash": "hash-smart-prod",
        "cdr": "<ApplicationResponse/>",
        "rechazado": False,
    }
    fake_client.consult_ticket.return_value = {
        "estado": 200,
        "mensaje": "Aceptado por SUNAT",
        "xml_firmado": _zip_b64("signed.xml", signed_xml),
        "codigo_hash": "hash-smart-prod",
        "cdr": "<ApplicationResponse/>",
        "rechazado": False,
    }

    with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=fake_client):
        result = facturacion_service.emitir_factura(fiscal, db_session, user)

    assert result["provider_endpoint"] == "/api/cpe/procesar"
    assert fake_client.process_xml.call_args.kwargs["demo"] is False
    assert result["provider_verification_status"] == "verified"


def test_emitir_factura_rechaza_smartpse_sin_verificacion_remota(db_session):
    tenant, user, fiscal = _make_smartpse_fiscal_document(db_session)
    signed_xml = _sale_xml(tenant, issue_date=fiscal.fecha_emision.date().isoformat())
    fake_client = MagicMock()
    fake_client.process_xml.return_value = {
        "estado": 200,
        "mensaje": "Aceptado por SUNAT",
        "xml_firmado": _zip_b64("signed.xml", signed_xml),
        "codigo_hash": "hash-smart",
        "cdr": "<ApplicationResponse/>",
        "rechazado": False,
    }
    fake_client.consult_ticket.side_effect = facturacion_service.smartpse_client.SmartPSEException(
        "Documento no encontrado"
    )

    with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=fake_client), patch(
        "services.facturacion_service.time.sleep"
    ) as sleep_mock:
        with pytest.raises(facturacion_service.FacturacionException) as exc:
            facturacion_service.emitir_factura(fiscal, db_session, user)

    assert "remote verification missing" in str(exc.value)
    assert fake_client.process_xml.call_count == 1
    assert fake_client.consult_ticket.call_count == facturacion_service.ASYNC_STATUS_MAX_ATTEMPTS
    assert sleep_mock.call_count == facturacion_service.ASYNC_STATUS_MAX_ATTEMPTS - 1


def test_emitir_factura_reintenta_solo_consulta_hasta_obtener_cdr(db_session):
    tenant, user, fiscal = _make_smartpse_fiscal_document(db_session)
    signed_xml = _sale_xml(tenant, issue_date=fiscal.fecha_emision.date().isoformat())
    accepted_response = {
        "estado": 200,
        "mensaje": "Aceptado por SUNAT",
        "xml_firmado": _zip_b64("signed.xml", signed_xml),
        "codigo_hash": "hash-smart-delayed",
        "cdr": "<ApplicationResponse/>",
        "rechazado": False,
    }
    fake_client = MagicMock()
    fake_client.process_xml.return_value = {
        "estado": 200,
        "mensaje": "Documento recibido",
        "xml_firmado": _zip_b64("signed.xml", signed_xml),
        "codigo_hash": "hash-smart-delayed",
        "rechazado": False,
    }
    missing = facturacion_service.smartpse_client.SmartPSEException(
        "Documento o ticket no encontrado"
    )
    fake_client.consult_ticket.side_effect = [missing, missing, accepted_response]

    with patch(
        "services.facturacion_service.smartpse_client.get_default_client",
        return_value=fake_client,
    ), patch("services.facturacion_service.time.sleep") as sleep_mock:
        result = facturacion_service.emitir_factura(fiscal, db_session, user)

    assert result["success"] is True
    assert result["cdr_xml"] == "<ApplicationResponse/>"
    assert result["provider_verification_status"] == "verified"
    assert fake_client.process_xml.call_count == 1
    assert fake_client.consult_ticket.call_count == 3
    assert sleep_mock.call_count == 2


def test_emitir_factura_acepta_cdr_desde_verificacion_remota(db_session):
    tenant, user, fiscal = _make_smartpse_fiscal_document(db_session)
    signed_xml = _sale_xml(tenant, issue_date=fiscal.fecha_emision.date().isoformat())
    fake_client = MagicMock()
    fake_client.process_xml.return_value = {
        "estado": 200,
        "mensaje": "Aceptado por SUNAT",
        "xml_firmado": _zip_b64("signed.xml", signed_xml),
        "codigo_hash": "hash-smart",
        "rechazado": False,
    }
    fake_client.consult_ticket.return_value = {
        "estado": 200,
        "mensaje": "Aceptado por SUNAT",
        "xml_firmado": _zip_b64("signed.xml", signed_xml),
        "codigo_hash": "hash-smart",
        "cdr": "<ApplicationResponse/>",
        "rechazado": False,
    }

    with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=fake_client):
        result = facturacion_service.emitir_factura(fiscal, db_session, user)

    assert result["success"] is True
    assert result["cdr_xml"] == "<ApplicationResponse/>"
    assert result["provider_verification_status"] == "verified"
    fake_client.consult_ticket.assert_called_once()


def test_emitir_factura_rechaza_identidad_remota_distinta(db_session):
    tenant, user, fiscal = _make_smartpse_fiscal_document(db_session)
    signed_xml = _sale_xml(tenant, issue_date=fiscal.fecha_emision.date().isoformat())
    stale_xml = _sale_xml(tenant, doc_id="F001-00000999", issue_date="2026-05-04")
    fake_client = MagicMock()
    fake_client.process_xml.return_value = {
        "estado": 200,
        "mensaje": "Aceptado por SUNAT",
        "xml_firmado": _zip_b64("signed.xml", signed_xml),
        "codigo_hash": "hash-smart",
        "cdr": "<ApplicationResponse/>",
        "rechazado": False,
    }
    fake_client.consult_ticket.return_value = {
        "estado": 200,
        "mensaje": "Aceptado por SUNAT",
        "xml_firmado": _zip_b64("signed.xml", stale_xml),
        "codigo_hash": "hash-old",
        "cdr": "<ApplicationResponse/>",
        "rechazado": False,
    }

    with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=fake_client):
        with pytest.raises(facturacion_service.FacturacionException) as exc:
            facturacion_service.emitir_factura(fiscal, db_session, user)

    assert "remote verification mismatch" in str(exc.value)


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
