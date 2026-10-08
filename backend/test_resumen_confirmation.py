"""RC confirmation uses the shared fiscal client and never resubmits a batch."""
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

import crud
import models
from api_dependencies import get_current_user, get_db_tenant
from conftest import make_tenant, make_user
from database import get_db
from routers import facturacion
from services import facturacion_service, smartpse_response
from services.smartpse_client import SmartPSEDefinitiveRejection, SmartPSEException


def _payload():
    return {
        "correlativo": "20261005-1", "fecGeneracion": "2026-10-05T00:00:00-05:00",
        "fecResumen": "2026-10-05T00:00:00-05:00", "moneda": "PEN",
        "company": {"ruc": "20123456789"},
        "details": [{"tipoDoc": "03", "serieNro": "B001-1", "estado": "1",
                     "clienteTipo": "1", "clienteNro": "12345678", "total": "118",
                     "mtoOperGravadas": "100", "mtoIGV": "18"}],
    }


def _cdr(*, reference="RC-20261005-1", code="0", ruc="20123456789"):
    return f"""<ApplicationResponse
      xmlns:cbc='urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
      xmlns:cac='urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'>
      <cac:ReceiverParty><cac:PartyIdentification><cbc:ID>{ruc}</cbc:ID></cac:PartyIdentification></cac:ReceiverParty>
      <cac:DocumentResponse><cac:Response><cbc:ReferenceID>{reference}</cbc:ReferenceID>
      <cbc:ResponseCode>{code}</cbc:ResponseCode><cbc:Description>Resultado sintético</cbc:Description>
      </cac:Response></cac:DocumentResponse></ApplicationResponse>"""


def _result(data):
    return smartpse_response.build_smartpse_result(
        dict(_payload(), tipoDoc="RC"), data, endpoint="/api/cpe/procesar", status_code=200,
    )


@pytest.fixture
def context(db_session, monkeypatch):
    monkeypatch.setattr(facturacion.limiter, "enabled", False)
    tenant = make_tenant(db_session, "501")
    tenant.business_ruc = "20123456789"
    user = make_user(db_session, tenant, email="summary-confirmation@test.pe")
    db_session.add(models.Subscription(tenant_id=tenant.id, status="active",
                                      beta_feature_flags={"daily_summary": True}))
    db_session.commit()
    row = crud.create_resumen_diario(db_session, tenant_id=tenant.id, usuario_id=user.id, payload=_payload())
    app = FastAPI()
    app.include_router(facturacion.router)
    app.dependency_overrides[get_db_tenant] = lambda: db_session
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user
    return tenant, user, row, TestClient(app)


@pytest.mark.parametrize("data", [{"estado": 200}, {"estado": 202, "ticket": "pending-rc"}])
def test_receipt_or_ticket_without_cdr_is_not_acceptance(context, db_session, data):
    tenant, _, row, _ = context
    result = _result(data)
    assert result["pending"] is True
    saved = crud.mark_resumen_diario_sent(db_session, row.id, result=result, tenant_id=tenant.id)
    assert saved.status == "pending"
    assert saved.success is False


@pytest.mark.parametrize("cdr", [_cdr(reference="RC-20261004-1"), _cdr(ruc="20987654321"),
                                  "<ApplicationResponse/>", "not xml"])
def test_unverified_cdr_cannot_confirm_a_batch(cdr):
    with pytest.raises(SmartPSEException):
        _result({"estado": 200, "cdr": cdr})


def test_matching_rejected_cdr_is_a_definitive_rejection():
    with pytest.raises(SmartPSEDefinitiveRejection):
        _result({"estado": 200, "cdr": _cdr(code="2335")})


def test_persistence_also_rejects_unverified_cdr(context, db_session):
    tenant, _, row, _ = context
    with pytest.raises(SmartPSEException):
        crud.mark_resumen_diario_sent(db_session, row.id,
            result={"success": True, "cdr_xml": _cdr(reference="RC-20261004-1")}, tenant_id=tenant.id)
    db_session.rollback()
    assert row.status == "pending"
    assert row.success is False


def test_consultation_confirms_frozen_batch_without_resubmission(context, db_session):
    _, _, row, client = context
    row.ticket = "ticket-original"
    db_session.commit()
    provider = Mock()
    provider.consult_ticket.return_value = {"estado": 200, "cdr": _cdr()}
    with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=provider):
        response = client.post(f"/resumen-diario/{row.id}/consultar")
        second = client.post(f"/resumen-diario/{row.id}/consultar")
    assert response.status_code == second.status_code == 200
    assert response.json()["status"] == "sent"
    assert response.json()["success"] is True
    assert response.json()["ticket"] == "ticket-original"
    assert provider.consult_ticket.call_args.args[1] == "20123456789-RC-20261005-1"
    provider.consult_ticket.assert_called_once()
    provider.process_xml.assert_not_called()


@pytest.mark.parametrize("data", [{"estado": 202, "ticket": "still-pending"},
                                  {"estado": 200, "mensaje": "Recibido"}])
def test_consultation_preserves_pending_without_cdr(context, data):
    _, _, row, client = context
    provider = Mock()
    provider.consult_ticket.return_value = data
    with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=provider):
        response = client.post(f"/resumen-diario/{row.id}/consultar")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["success"] is False
    provider.process_xml.assert_not_called()


def test_consultation_records_rejection_and_is_idempotent(context):
    _, _, row, client = context
    provider = Mock()
    provider.consult_ticket.return_value = {"estado": 200, "cdr": _cdr(code="2335")}
    with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=provider):
        response = client.post(f"/resumen-diario/{row.id}/consultar")
        repeat = client.post(f"/resumen-diario/{row.id}/consultar")
    assert response.status_code == repeat.status_code == 200
    assert response.json()["status"] == "rejected"
    assert "2335" in response.json()["sunat_error"]
    provider.consult_ticket.assert_called_once()


@pytest.mark.parametrize("provider_error", [SmartPSEException("Timeout"),
                                           {"estado": 200, "cdr": _cdr(reference="RC-20261003-1")}])
def test_uncertain_consultation_does_not_mark_rejection(context, db_session, provider_error):
    _, _, row, client = context
    row.ticket = "keep-ticket"
    db_session.commit()
    provider = Mock()
    if isinstance(provider_error, Exception):
        provider.consult_ticket.side_effect = provider_error
    else:
        provider.consult_ticket.return_value = provider_error
    with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=provider):
        response = client.post(f"/resumen-diario/{row.id}/consultar")
    assert response.status_code == 502
    db_session.refresh(row)
    assert row.status == "pending"
    assert row.ticket == "keep-ticket"
    provider.process_xml.assert_not_called()


def test_cross_tenant_consultation_is_404_without_provider_access(context, db_session):
    _, _, row, client = context
    other = make_tenant(db_session, "502")
    row.tenant_id = other.id
    db_session.commit()
    with patch("services.facturacion_service.smartpse_client.get_default_client") as provider:
        response = client.post(f"/resumen-diario/{row.id}/consultar")
    assert response.status_code == 404
    provider.assert_not_called()


@pytest.mark.parametrize("block", ["flag", "role", "suspended"])
def test_consultation_requires_tenant_permissions_and_flag(context, db_session, block):
    tenant, user, row, client = context
    if block == "flag":
        tenant.subscription.beta_feature_flags = {}
    elif block == "role":
        user.rol = "vendedor"
    else:
        tenant.is_active = False
    db_session.commit()
    with patch("services.facturacion_service.smartpse_client.get_default_client") as provider:
        response = client.post(f"/resumen-diario/{row.id}/consultar")
    assert response.status_code == 403
    provider.assert_not_called()


@pytest.mark.parametrize("code, expected", [("0", "sent"), ("2335", "rejected")])
def test_late_responses_cannot_erase_a_confirmed_cdr(context, db_session, code, expected):
    tenant, _, row, _ = context
    row.provider_response = {"cdr": _cdr(code=code)}
    row.status = expected
    row.success = code == "0"
    db_session.commit()
    crud.mark_resumen_diario_sent(db_session, row.id, result=_result({"estado": 202}), tenant_id=tenant.id)
    crud.mark_resumen_diario_rejected(db_session, row.id, error="Timeout", tenant_id=tenant.id, pending=True)
    assert row.status == expected
    assert row.success is (code == "0")


def test_legacy_sent_without_cdr_is_reconciled_instead_of_trusted(context, db_session):
    _, _, row, client = context
    row.status = "sent"
    row.success = True
    row.provider_response = {"success": True}
    db_session.commit()
    provider = Mock()
    provider.consult_ticket.return_value = {"estado": 202}
    with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=provider):
        response = client.post(f"/resumen-diario/{row.id}/consultar")
    assert response.json()["status"] == "pending"
    assert response.json()["success"] is False


def test_ambiguous_send_remains_pending_for_consultation(context, db_session):
    _, _, _, client = context
    provider = Mock()
    provider.process_xml.side_effect = SmartPSEException("Timeout después del envío")
    payload = _payload()
    payload["correlativo"] = "20261005-2"
    payload.pop("company")
    with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=provider):
        response = client.post("/resumen-diario/enviar", json=payload)
    assert response.status_code == 502
    newest = db_session.query(models.ResumenDiario).order_by(models.ResumenDiario.id.desc()).first()
    assert newest.status == "pending"
    assert newest.success is False


@pytest.mark.parametrize("tipo", ["01", "03"])
def test_high_amount_sales_use_the_same_existing_emission_path(db_session, tipo):
    from decimal import Decimal
    from test_apisperu_documentos_matrix import _FakeSmartPSEClient, _make_fiscal_document, _patch_smartpse
    _, user, _, fiscal = _make_fiscal_document(db_session, "503", tipo)
    fiscal.items[0].cantidad = Decimal("1")
    fiscal.items[0].valor_unitario = Decimal("1000")
    fiscal.items[0].precio_unitario = Decimal("1180")
    fiscal.total_venta = Decimal("1180")
    provider = _FakeSmartPSEClient()
    with _patch_smartpse(provider):
        result = facturacion_service.emitir_factura(fiscal, db_session, user, tipo_doc_override=tipo)
    xml = provider.process_calls[0][2].decode()
    assert result["success"] is True
    assert result["provider_verification_status"] == "verified"
    assert f">{tipo}</cbc:InvoiceTypeCode>" in xml
    assert '>1180.00</cbc:PayableAmount>' in xml
    assert "PaymentMeansCode" not in xml  # normal 0101, no automatic detraction
