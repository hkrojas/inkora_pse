import base64
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

import crud
import models
from api_dependencies import get_current_user, get_db, get_db_tenant
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from routers import superadmin as superadmin_router
from services import emission_queue_service, facturacion_service


def _client_for_superadmin(db_session, user):
    app = FastAPI()
    app.include_router(superadmin_router.router)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_db_tenant] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _make_gre_user_and_guia(db_session, suffix: str):
    tenant = make_tenant(db_session, suffix)
    tenant.smartpse_company_id = "77"
    tenant.smartpse_environment = "demo"
    tenant.smartpse_usuario_secundaria = "AB3KPQR9"
    tenant.smartpse_token_acceso = "MX7TNVQG"
    tenant.smartpse_gre_sol_username = "SOLUSER"
    tenant.smartpse_gre_sol_password_enc = "sol-password-demo"
    tenant.smartpse_gre_client_id = "client-id"
    tenant.smartpse_gre_client_secret_enc = "client-secret"
    subscription = models.Subscription(
        tenant_id=tenant.id,
        status=models.SUBSCRIPTION_STATUS_ACTIVE,
        beta_feature_flags={"guides": True},
    )
    db_session.add(subscription)
    db_session.commit()
    user = make_user(db_session, tenant, email=f"gre-{suffix.lower()}@test.com")
    cliente = make_cliente(db_session, tenant, suffix, numero_documento="20191308868")
    quote = make_quote_via_crud(db_session, tenant, user, cliente)
    fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
    guia = crud.create_guia_remision(
        db_session,
        {
            "cotizacion_id": fiscal.id,
            "fecha_traslado": datetime.now(timezone.utc),
            "motivo_traslado": "01",
            "descripcion_motivo": "VENTA",
            "peso_bruto_total": Decimal("5.00"),
            "unidad_medida_peso": "KGM",
            "numero_bultos": 1,
            "modalidad_traslado": "02",
            "conductor_tipo_doc": "1",
            "conductor_nro_doc": "72758912",
            "conductor_nombres": "KENNEDY",
            "conductor_apellidos": "ROJAS",
            "conductor_licencia": "Q12345678",
            "vehiculo_placa": "ABC123",
            "partida_ubigeo": "150101",
            "partida_direccion": "Av. Origen 100",
            "llegada_ubigeo": "150101",
            "llegada_direccion": "Av. Destino 200",
            "items": [
                {
                    "descripcion": "Paquete de prueba",
                    "cantidad": Decimal("2"),
                    "unidad_medida": "NIU",
                    "codigo_producto": "PK-001",
                }
            ],
        },
        user.id,
        tenant.id,
    )
    return tenant, user, guia


def test_secret_box_encrypts_without_persisting_plaintext():
    from services import secret_box

    encrypted = secret_box.encrypt_secret("client-secret")

    assert encrypted.startswith("enc:v1:")
    assert "client-secret" not in encrypted
    assert secret_box.decrypt_secret(encrypted) == "client-secret"
    assert secret_box.decrypt_secret("legacy-plaintext") == "legacy-plaintext"


def test_superadmin_stores_smartpse_gre_credentials_encrypted_and_redacted(db_session):
    tenant = make_tenant(db_session, "GRC01")
    superadmin = make_user(
        db_session,
        tenant,
        email="gre-superadmin@test.com",
        rol="superadmin",
        is_superadmin=True,
    )
    client = _client_for_superadmin(db_session, superadmin)

    response = client.put(
        f"/superadmin/tenants/{tenant.id}/smartpse/gre-credentials",
        json={
            "sol_username": " SOLUSER ",
            "sol_password": "sol-password-demo",
            "client_id": "client-id",
            "client_secret": "client-secret",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["has_smartpse_gre_credentials"] is True
    assert body["smartpse_gre_status"] == "unchecked"
    assert "sol-password-demo" not in str(body)
    assert "client-secret" not in str(body)
    db_session.refresh(tenant)
    assert tenant.smartpse_gre_sol_username == "SOLUSER"
    assert tenant.smartpse_gre_sol_password_enc.startswith("enc:v1:")
    assert tenant.smartpse_gre_client_secret_enc.startswith("enc:v1:")


def test_superadmin_check_smartpse_gre_credentials_updates_status_without_exposing_secrets(db_session):
    tenant, _, _ = _make_gre_user_and_guia(db_session, "GRC02")
    superadmin = make_user(
        db_session,
        tenant,
        email="gre-check@test.com",
        rol="superadmin",
        is_superadmin=True,
    )
    client = _client_for_superadmin(db_session, superadmin)

    with patch(
        "routers.superadmin.smartpse_gre_credentials.validate_tenant_gre_credentials",
        return_value={
            "valid": True,
            "message": "Credenciales GRE aceptadas.",
            "provider_status_code": 200,
            "provider_detail": "ok",
        },
    ) as validate:
        response = client.post(f"/superadmin/tenants/{tenant.id}/smartpse/gre-credentials/check")

    assert response.status_code == 200
    assert response.json()["valid"] is True
    validate.assert_called_once()
    db_session.refresh(tenant)
    assert tenant.smartpse_gre_status == "ok"
    assert tenant.smartpse_gre_checked_at is not None


def test_emitir_guia_con_ticket_sin_cdr_permanece_pendiente(db_session):
    tenant, user, guia = _make_gre_user_and_guia(db_session, "GRC03")
    fake_client = MagicMock()
    fake_client.process_xml.return_value = {
        "estado": 200,
        "mensaje": "Pendiente",
        "ticket": "GRE-TICKET-1",
        "xml_firmado": "<DespatchAdvice/>",
        "codigo_hash": "hash-gre",
        "rechazado": False,
    }
    with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=fake_client):
        result = facturacion_service.emitir_guia_remision(guia, user)

    assert result["success"] is True
    assert result["pending"] is True
    assert result["ticket"] == "GRE-TICKET-1"
    fake_client.process_xml.assert_called_once()
    extra_payload = fake_client.process_xml.call_args.kwargs["extra_payload"]
    assert extra_payload == {
        "client_id_sunat": "client-id",
        "client_secret_sunat": "client-secret",
        "sol_user": "20123403SOLUSER",
        "sol_password": "sol-password-demo",
        "environment": "demo",
    }


def test_emitir_guia_smartpse_acepta_cdr_y_persiste_evidencia(db_session):
    tenant, user, guia = _make_gre_user_and_guia(db_session, "GRC03CDR")
    cdr_xml = """<ApplicationResponse xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"><cac:DocumentResponse><cac:Response><cbc:ResponseCode>0</cbc:ResponseCode><cbc:Description>Aceptada</cbc:Description></cac:Response><cac:DocumentReference><cbc:ID>T001-1</cbc:ID></cac:DocumentReference></cac:DocumentResponse></ApplicationResponse>"""
    fake_client = MagicMock()
    fake_client.process_xml.return_value = {
        "estado": 200,
        "mensaje": "Aceptado por SUNAT",
        "xml_firmado": "<DespatchAdvice/>",
        "codigo_hash": "hash-gre",
        "cdr": base64.b64encode(cdr_xml.encode("utf-8")).decode("ascii"),
        "rechazado": False,
    }

    with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=fake_client):
        result = facturacion_service.emitir_guia_remision(guia, user)

    assert result["success"] is True
    assert result["cdr_xml"] == cdr_xml
    updated = crud.guardar_respuesta_sunat_gre(db_session, guia.id, result, tenant_id=tenant.id)
    assert updated.estado == "emitida"
    assert updated.cdr_disponible is True


def test_guardar_respuesta_sunat_gre_persists_pending_signed_artifacts(db_session):
    _, _, guia = _make_gre_user_and_guia(db_session, "GRC04")

    updated = crud.guardar_respuesta_sunat_gre(
        db_session,
        guia.id,
        {
            "success": True,
            "pending": True,
            "xml": "<DespatchAdvice/>",
            "hash": "hash-gre",
            "ticket": "GRE-TICKET-1",
            "provider_endpoint": "/api/cpe/procesar-demo",
            "provider_status_code": 200,
            "provider_response": {"estado": 200, "ticket": "GRE-TICKET-1"},
        },
        tenant_id=guia.tenant_id,
    )

    assert updated.estado == "pendiente_smartpse"
    assert updated.sunat_xml_content == "<DespatchAdvice/>"
    assert updated.sunat_hash == "hash-gre"
    assert updated.sunat_ticket == "GRE-TICKET-1"
    assert updated.provider_response == {"estado": 200, "ticket": "GRE-TICKET-1"}
    assert updated.sunat_error is None


def test_worker_keeps_ticket_without_cdr_pending_and_does_not_cover_dispatch(db_session):
    tenant, user, guia = _make_gre_user_and_guia(db_session, "GRC04WORKER")
    guia.frozen_payload = {"tipoDoc": "09", "serie": guia.serie, "correlativo": "1"}
    guia.frozen_xml = "<DespatchAdvice/>"
    guia.emission_environment = "demo"
    db_session.commit()
    job, created = emission_queue_service.enqueue_guide_job(db_session, guia, user)
    assert created is True

    pending_result = {
        "success": True,
        "pending": True,
        "ticket": "GRE-WORKER-TICKET",
        "xml": "<DespatchAdvice Signed='true'/>",
        "hash": "worker-hash",
        "provider_endpoint": "/api/cpe/procesar-demo",
        "provider_status_code": 200,
        "provider_response": {"estado": 200, "ticket": "GRE-WORKER-TICKET"},
    }
    with patch(
        "services.emission_queue_service.sale_dispatch_service.validate_guide_for_emission",
        return_value={"valid": True, "errors": [], "warnings": []},
    ), patch(
        "services.emission_queue_service.facturacion_service.emitir_guia_remision",
        return_value=pending_result,
    ), patch(
        "services.emission_queue_service.sale_dispatch_service.apply_guide_result",
    ) as apply_result:
        assert emission_queue_service.process_emission_job(job.id, db_session=db_session) is True

    db_session.expire_all()
    updated_job = crud.get_emission_job(db_session, job.id)
    updated_guide = db_session.get(models.GuiaRemision, guia.id)
    assert updated_job.status == models.EMISSION_JOB_STATUS_PENDING_CONFIRMATION
    assert updated_job.provider_ticket == "GRE-WORKER-TICKET"
    assert updated_guide.estado == "pendiente_smartpse"
    assert updated_guide.sunat_ticket == "GRE-WORKER-TICKET"
    assert updated_guide.cdr_disponible is False
    apply_result.assert_not_called()


def test_emitir_guia_demo_allows_missing_dedicated_gre_credentials(db_session):
    _, user, guia = _make_gre_user_and_guia(db_session, "GRC05")
    user.tenant.smartpse_gre_client_secret_enc = None
    db_session.commit()
    fake_client = MagicMock()
    fake_client.process_xml.return_value = {
        "estado": 200,
        "mensaje": "Pendiente",
        "ticket": "GRE-DEMO-TICKET",
        "xml_firmado": "<DespatchAdvice/>",
        "codigo_hash": "hash-gre-demo",
        "rechazado": False,
    }

    with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=fake_client):
        result = facturacion_service.emitir_guia_remision(guia, user)

    assert result["pending"] is True
    assert "extra_payload" not in fake_client.process_xml.call_args.kwargs


def test_emitir_guia_production_blocks_missing_dedicated_gre_credentials(
    db_session,
    monkeypatch,
):
    _, user, guia = _make_gre_user_and_guia(db_session, "GRC05PROD")
    user.tenant.smartpse_environment = "produccion"
    user.tenant.smartpse_gre_client_secret_enc = None
    db_session.commit()
    monkeypatch.setattr(facturacion_service.settings, "FISCAL_ENV", "production")
    fake_client = MagicMock()

    with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=fake_client):
        with pytest.raises(facturacion_service.FacturacionException) as exc_info:
            facturacion_service.emitir_guia_remision(guia, user)

    assert "credenciales SUNAT GRE" in str(exc_info.value)
    assert "produccion" in str(exc_info.value)
    fake_client.process_xml.assert_not_called()


def test_consultar_guia_reenvia_credenciales_gre_sin_exponerlas_en_nombre(db_session):
    _, user, guia = _make_gre_user_and_guia(db_session, "GRC06")
    guia.frozen_payload = {
        "company": {"ruc": user.tenant.business_ruc},
        "tipoDoc": "09",
        "serie": guia.serie,
        "correlativo": str(guia.correlativo).zfill(6),
    }
    guia.sunat_ticket = "GRE-TICKET-6"
    db_session.commit()
    fake_client = MagicMock()
    fake_client.consult_ticket.side_effect = facturacion_service.smartpse_client.SmartPSEException(
        "Pendiente"
    )

    with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=fake_client):
        with pytest.raises(facturacion_service.FacturacionException):
            facturacion_service.consultar_guia_remision(guia, user)

    called_tenant, filename = fake_client.consult_ticket.call_args.args
    assert called_tenant.id == user.tenant.id
    expected_ruc = "".join(ch for ch in user.tenant.business_ruc if ch.isdigit())
    assert filename.startswith(f"{expected_ruc}-09-")
    assert "client-secret" not in filename
    assert fake_client.consult_ticket.call_args.kwargs["extra_payload"] == {
        "client_id_sunat": "client-id",
        "client_secret_sunat": "client-secret",
        "sol_user": f"{expected_ruc}SOLUSER",
        "sol_password": "sol-password-demo",
        "environment": "demo",
    }
