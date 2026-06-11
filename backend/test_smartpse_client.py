from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
import requests

from services.smartpse_client import SmartPSEClient, SmartPSEException


class TenantStub:
    id = 10
    business_ruc = "20123456789"
    business_name = "INKORA TEST SAC"
    smartpse_usuario_secundaria = "AB3KPQR9"
    smartpse_token_acceso = "MX7TNVQG"


def _json_response(status_code: int, payload: dict):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = str(payload)
    response.headers = {"Content-Type": "application/json"}
    return response


def test_get_cpe_token_caches_short_lived_jwt(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return _json_response(200, {"token_acceso": "jwt-one", "expira_en": 600})

    client = SmartPSEClient(
        base_url="https://panel.smartpse.pe",
        api_token="global-token",
        timeout_seconds=7,
        post=fake_post,
    )

    first = client.get_cpe_token(TenantStub())
    second = client.get_cpe_token(TenantStub())

    assert first == "jwt-one"
    assert second == "jwt-one"
    assert len(calls) == 1
    assert calls[0][0] == "https://panel.smartpse.pe/api/auth/cpe/token"
    assert calls[0][1]["json"] == {"usuario": "AB3KPQR9", "password": "MX7TNVQG"}
    assert calls[0][1]["timeout"] == 7


def test_process_xml_refreshes_token_once_after_unauthorized(monkeypatch):
    calls = {"token": 0, "process": 0}

    def fake_post(url, **kwargs):
        if url.endswith("/api/auth/cpe/token"):
            calls["token"] += 1
            token = "jwt-one" if calls["token"] == 1 else "jwt-two"
            return _json_response(200, {"token_acceso": token, "expira_en": 600})
        calls["process"] += 1
        if calls["process"] == 1:
            assert kwargs["headers"]["Authorization"] == "Bearer jwt-one"
            return _json_response(401, {"message": "Token vencido"})
        assert kwargs["headers"]["Authorization"] == "Bearer jwt-two"
        return _json_response(200, {"estado": 200, "mensaje": "Aceptado", "rechazado": False})

    client = SmartPSEClient(
        base_url="https://panel.smartpse.pe",
        api_token="global-token",
        post=fake_post,
    )

    data = client.process_xml(TenantStub(), "20123456789-01-F001-00000001", b"<Invoice/>", demo=True)

    assert data["estado"] == 200
    assert calls == {"token": 2, "process": 2}


def test_process_xml_merges_gre_extra_payload_without_logging_secrets():
    process_payloads = []

    def fake_post(url, **kwargs):
        if url.endswith("/api/auth/cpe/token"):
            return _json_response(200, {"token_acceso": "jwt-one", "expira_en": 600})
        process_payloads.append(kwargs["json"])
        return _json_response(200, {"estado": 200, "mensaje": "Pendiente", "ticket": "T1"})

    client = SmartPSEClient(
        base_url="https://panel.smartpse.pe",
        api_token="global-token",
        post=fake_post,
    )

    client.process_xml(
        TenantStub(),
        "20123456789-09-T001-00000001",
        b"<DespatchAdvice/>",
        demo=True,
        extra_payload={
            "client_id_sunat": "client-id",
            "client_secret_sunat": "client-secret",
            "sol_user": "20123456789SOLUSER",
            "sol_password": "sol-password",
        },
    )

    assert process_payloads[0]["client_id_sunat"] == "client-id"
    assert process_payloads[0]["client_secret_sunat"] == "client-secret"
    assert process_payloads[0]["sol_user"] == "20123456789SOLUSER"
    assert process_payloads[0]["sol_password"] == "sol-password"


def test_provision_company_uses_global_management_token():
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return _json_response(
            201,
            {
                "success": True,
                "data": {
                    "id": 7,
                    "ruc": "20123456789",
                    "environment": "demo",
                    "credenciales_cpe": {
                        "usuario_secundaria": "AB3KPQR9",
                        "token_acceso": "MX7TNVQG",
                    },
                },
            },
        )

    client = SmartPSEClient(
        base_url="https://panel.smartpse.pe",
        api_token="global-token",
        post=fake_post,
    )

    company = client.provision_company(
        ruc="20123456789",
        razon_social="INKORA TEST SAC",
        environment="demo",
    )

    assert company["id"] == 7
    assert calls[0][0] == "https://panel.smartpse.pe/api/v1/companies"
    assert calls[0][1]["headers"]["Authorization"] == "Bearer global-token"
    assert calls[0][1]["json"]["ruc"] == "20123456789"


def test_company_management_methods_use_global_management_token():
    calls = []

    def fake_get(url, **kwargs):
        calls.append(("GET", url, kwargs))
        if url.endswith("/api/v1/companies/7"):
            return _json_response(
                200,
                {
                    "success": True,
                    "data": {
                        "id": 7,
                        "ruc": "20123456789",
                        "environment": "demo",
                        "active": True,
                        "estado": "ACTIVO",
                    },
                },
            )
        return _json_response(
            200,
            {
                "success": True,
                "data": {
                    "data": [{"id": 7, "ruc": "20123456789"}],
                    "total": 1,
                    "current_page": 1,
                    "last_page": 1,
                },
            },
        )

    def fake_post(url, **kwargs):
        calls.append(("POST", url, kwargs))
        return _json_response(
            200,
            {
                "success": True,
                "data": {"id": 7, "active": False, "estado": "INACTIVO"},
            },
        )

    client = SmartPSEClient(
        base_url="https://panel.smartpse.pe",
        api_token="global-token",
        get=fake_get,
        post=fake_post,
    )

    page = client.list_companies(search="20123456789", page=1, per_page=5)
    detail = client.get_company("7")
    activation = client.toggle_company_activation("7")

    assert page["data"][0]["ruc"] == "20123456789"
    assert detail["id"] == 7
    assert activation["active"] is False
    assert calls[0][0] == "GET"
    assert calls[0][1] == "https://panel.smartpse.pe/api/v1/companies"
    assert calls[0][2]["params"] == {"search": "20123456789", "page": 1, "per_page": 5}
    assert calls[0][2]["headers"]["Authorization"] == "Bearer global-token"
    assert calls[1][1] == "https://panel.smartpse.pe/api/v1/companies/7"
    assert calls[2][1] == "https://panel.smartpse.pe/api/v1/companies/7/activation"


def test_update_company_redacts_provider_secrets_on_error():
    calls = []

    def fake_put(url, **kwargs):
        calls.append((url, kwargs))
        return _json_response(
            422,
            {
                "message": "Empresa invalida",
                "credenciales_cpe": {
                    "usuario_secundaria": "AB3KPQR9",
                    "token_acceso": "MX7TNVQG",
                },
                "token_acceso": "secret-token",
            },
        )

    client = SmartPSEClient(
        base_url="https://panel.smartpse.pe",
        api_token="global-token",
        put=fake_put,
    )

    with pytest.raises(SmartPSEException) as exc_info:
        client.update_company("7", {"environment": "produccion"})

    message = str(exc_info.value)
    assert "Empresa invalida" in message
    assert "AB3KPQR9" not in message
    assert "MX7TNVQG" not in message
    assert "secret-token" not in message
    assert calls[0][0] == "https://panel.smartpse.pe/api/v1/companies/7"
    assert calls[0][1]["json"] == {"environment": "produccion"}


def test_provider_errors_are_reported_without_leaking_credentials():
    def fake_post(url, **kwargs):
        return _json_response(
            422,
            {
                "message": "RUC invalido",
                "token_acceso": "secret",
                "client_secret_sunat": "client-secret",
                "sol_password": "sol-password",
            },
        )

    client = SmartPSEClient(
        base_url="https://panel.smartpse.pe",
        api_token="global-token",
        post=fake_post,
    )

    with pytest.raises(SmartPSEException) as exc_info:
        client.provision_company(ruc="20", razon_social="Bad", environment="demo")

    message = str(exc_info.value)
    assert "RUC invalido" in message
    assert "secret" not in message
    assert "client-secret" not in message
    assert "sol-password" not in message
