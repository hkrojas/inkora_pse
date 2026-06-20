import base64
import zipfile
from io import BytesIO

import pytest

from services.smartpse_client import SmartPSEException
from services.smartpse_response import build_smartpse_result


def _zip_b64(filename: str, content: str) -> str:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(filename, content)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def test_accepted_response_extracts_signed_xml_and_matches_internal_shape():
    payload = {"serie": "F001", "correlativo": "00000001", "tipoDoc": "01"}
    signed_xml = "<?xml version='1.0'?><Invoice><cbc>ID</cbc:ID></Invoice>"
    data = {
        "estado": 200,
        "mensaje": "Aceptado por SUNAT",
        "xml_firmado": _zip_b64("20123456789-01-F001-00000001.xml", signed_xml),
        "codigo_hash": "hash-abc",
        "cdr": "<ApplicationResponse/>",
        "rechazado": False,
        "observaciones": None,
        "errores": None,
    }

    result = build_smartpse_result(
        payload,
        data,
        endpoint="/api/cpe/procesar-demo",
        status_code=200,
    )

    assert result["success"] is True
    assert result["serie"] == "F001"
    assert result["correlativo"] == "00000001"
    assert result["hash"] == "hash-abc"
    assert result["xml"] == signed_xml
    assert result["cdr_xml"] == "<ApplicationResponse/>"
    assert result["provider_endpoint"] == "/api/cpe/procesar-demo"
    assert result["sunat_response"]["success"] is True
    assert result["sunat_response"]["cdrResponse"]["description"] == "Aceptado por SUNAT"


def test_rejected_response_raises_non_successful_provider_error():
    payload = {"serie": "F001", "correlativo": "00000001", "tipoDoc": "01"}
    data = {
        "estado": 200,
        "mensaje": "Rechazado por SUNAT",
        "rechazado": True,
        "errores": ["ERROR 2335"],
        "observaciones": ["Revise el XML"],
    }

    with pytest.raises(SmartPSEException) as exc_info:
        build_smartpse_result(payload, data, endpoint="/api/cpe/procesar", status_code=200)

    message = str(exc_info.value)
    assert "Rechazado por SUNAT" in message
    assert "ERROR 2335" in message


def test_ticket_response_is_pending_and_keeps_ticket_for_polling():
    payload = {"serie": "RC", "correlativo": "20260505-001", "tipoDoc": "RC"}
    data = {
        "estado": 200,
        "mensaje": "Resumen enviado, consulte el ticket",
        "ticket": "20123456789-RC-20260505-001",
        "rechazado": False,
    }

    result = build_smartpse_result(payload, data, endpoint="/api/cpe/procesar-demo", status_code=200)

    assert result["success"] is True
    assert result["pending"] is True
    assert result["ticket"] == "20123456789-RC-20260505-001"
    assert result["sunat_response"]["ticket"] == "20123456789-RC-20260505-001"


def test_consult_response_with_cdr_completes_ticket_flow():
    payload = {"serie": "RC", "correlativo": "20260505-001", "tipoDoc": "RC"}
    data = {
        "estado": 200,
        "mensaje": "Procesado",
        "cdr": "<ApplicationResponse/>",
        "rechazado": False,
    }

    result = build_smartpse_result(
        payload,
        data,
        endpoint="/api/cpe/consultar/20123456789-RC-20260505-001",
        status_code=200,
        ticket="20123456789-RC-20260505-001",
    )

    assert result["success"] is True
    assert result["ticket"] == "20123456789-RC-20260505-001"
    assert result["cdr_xml"] == "<ApplicationResponse/>"


def test_cdr_zip_base64_is_normalized_to_xml_content():
    payload = {"serie": "F001", "correlativo": "00000001", "tipoDoc": "01"}
    cdr_xml = "<ApplicationResponse><Response>0</Response></ApplicationResponse>"
    data = {
        "estado": 200,
        "mensaje": "Procesado",
        "xml_firmado": "<Invoice/>",
        "cdr": _zip_b64("R-20123456789-01-F001-00000001.xml", cdr_xml),
        "rechazado": False,
    }

    result = build_smartpse_result(
        payload,
        data,
        endpoint="/api/cpe/procesar-demo",
        status_code=200,
    )

    assert result["cdr_xml"] == cdr_xml


def test_sale_response_without_cdr_is_not_accepted_when_cdr_required():
    payload = {"serie": "F001", "correlativo": "00000001", "tipoDoc": "01"}
    data = {
        "estado": 200,
        "mensaje": "Procesado sin CDR",
        "xml_firmado": "<Invoice/>",
        "rechazado": False,
    }

    with pytest.raises(SmartPSEException) as exc_info:
        build_smartpse_result(
            payload,
            data,
            endpoint="/api/cpe/procesar",
            status_code=200,
            require_cdr=True,
        )

    assert "CDR" in str(exc_info.value)


def test_sale_ticket_response_without_cdr_is_not_accepted_when_cdr_required():
    payload = {"serie": "F001", "correlativo": "00000001", "tipoDoc": "01"}
    data = {
        "estado": 200,
        "mensaje": "Documento enviado, consulte ticket",
        "ticket": "TICKET-1",
        "xml_firmado": "<Invoice/>",
        "rechazado": False,
    }

    with pytest.raises(SmartPSEException) as exc_info:
        build_smartpse_result(
            payload,
            data,
            endpoint="/api/cpe/procesar",
            status_code=200,
            require_cdr=True,
        )

    assert "CDR" in str(exc_info.value)
