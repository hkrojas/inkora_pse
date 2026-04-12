import base64
import json
from unittest.mock import MagicMock, patch

import requests

from services import facturacion_service


def _make_jwt(company=None):
    header = base64.urlsafe_b64encode(json.dumps({"typ": "JWT", "alg": "none"}).encode()).decode().rstrip("=")
    payload_data = {}
    if company is not None:
        payload_data["company"] = company
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip("=")
    return f"{header}.{payload}.signature"


def test_validate_apisperu_token_accepts_payload_validation_error():
    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_response.json.return_value = {"message": "The given data was invalid."}

    with patch("services.facturacion_service.requests.post", return_value=mock_response):
        result = facturacion_service.validate_apisperu_token(
            _make_jwt("20606751509"),
            "https://facturacion.apisperu.com/api/v1",
            "20606751509",
        )

    assert result["valid"] is True
    assert result["provider_status_code"] == 422
    assert "RUC 20606751509" in result["message"]
    assert result["token_company_ruc"] == "20606751509"
    assert result["matches_business_ruc"] is True


def test_validate_apisperu_token_rejects_invalid_token():
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {"error": "Token incorrecto"}

    with patch("services.facturacion_service.requests.post", return_value=mock_response):
        result = facturacion_service.validate_apisperu_token(
            _make_jwt("20606751509"),
            "https://facturacion.apisperu.com/api/v1",
        )

    assert result["valid"] is False
    assert result["provider_status_code"] == 401
    assert result["provider_detail"] == "Token incorrecto"


def test_validate_apisperu_token_handles_connection_error():
    with patch(
        "services.facturacion_service.requests.post",
        side_effect=requests.exceptions.ConnectionError(),
    ):
        result = facturacion_service.validate_apisperu_token(
            _make_jwt("20606751509"),
            "https://facturacion.apisperu.com/api/v1",
        )

    assert result["valid"] is False
    assert result["provider_detail"] == "connection_error"


def test_validate_apisperu_token_rejects_company_ruc_mismatch():
    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_response.json.return_value = {"message": "The given data was invalid."}

    with patch("services.facturacion_service.requests.post", return_value=mock_response):
        result = facturacion_service.validate_apisperu_token(
            _make_jwt("20606751509"),
            "https://facturacion.apisperu.com/api/v1",
            "20999999999",
        )

    assert result["valid"] is False
    assert result["token_company_ruc"] == "20606751509"
    assert result["matches_business_ruc"] is False
    assert "no al RUC configurado" in result["message"]


def test_validate_apisperu_token_accepts_company_token_probe_without_payload():
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {"error": "Empresa no encontrada."}

    with patch("services.facturacion_service.requests.post", return_value=mock_response):
        result = facturacion_service.validate_apisperu_token(
            _make_jwt("20606751509"),
            "https://facturacion.apisperu.com/api/v1",
            "20606751509",
        )

    assert result["valid"] is True
    assert result["provider_status_code"] == 404
    assert result["matches_business_ruc"] is True
    assert "asociado al RUC 20606751509" in result["message"]
