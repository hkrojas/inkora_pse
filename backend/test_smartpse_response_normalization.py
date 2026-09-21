import base64
import zipfile
from io import BytesIO

import pytest

from services.smartpse_client import SmartPSEDefinitiveRejection, SmartPSEException
from services.smartpse_response import build_smartpse_result


def _zip_b64(filename: str, content: str) -> str:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(filename, content)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _sale_cdr(*, document_id="F001-00000001", response_code="0", ruc="20123456789"):
    return f"""<ApplicationResponse
    xmlns='urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2'
    xmlns:cac='urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'
    xmlns:cbc='urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'>
  <cac:ReceiverParty><cac:PartyIdentification><cbc:ID>{ruc}</cbc:ID></cac:PartyIdentification></cac:ReceiverParty>
  <cac:DocumentResponse><cac:Response><cbc:ReferenceID>{document_id}</cbc:ReferenceID><cbc:ResponseCode>{response_code}</cbc:ResponseCode><cbc:Description>Resultado SUNAT</cbc:Description></cac:Response></cac:DocumentResponse>
</ApplicationResponse>"""


def test_accepted_response_extracts_signed_xml_and_matches_internal_shape():
    payload = {
        "serie": "F001",
        "correlativo": "00000001",
        "tipoDoc": "01",
        "company": {"ruc": "20123456789"},
    }
    signed_xml = "<?xml version='1.0'?><Invoice><cbc>ID</cbc:ID></Invoice>"
    data = {
        "estado": 200,
        "mensaje": "Aceptado por SUNAT",
        "xml_firmado": _zip_b64("20123456789-01-F001-00000001.xml", signed_xml),
        "codigo_hash": "hash-abc",
        "cdr": _sale_cdr(),
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
    assert result["cdr_xml"] == _sale_cdr()
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
    payload = {
        "serie": "F001",
        "correlativo": "00000001",
        "tipoDoc": "01",
        "company": {"ruc": "20123456789"},
    }
    cdr_xml = _sale_cdr()
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


@pytest.mark.parametrize(
    ("cdr_xml", "expected_message"),
    [
        (_sale_cdr(document_id="F001-00000999"), "corresponde a F001-00000999"),
        (_sale_cdr(ruc="20999999999"), "otro RUC emisor"),
        ("<ApplicationResponse/>", "no contiene resultado SUNAT"),
    ],
)
def test_sale_cdr_requires_matching_document_and_issuer(cdr_xml, expected_message):
    payload = {
        "serie": "F001",
        "correlativo": "00000001",
        "tipoDoc": "01",
        "company": {"ruc": "20123456789"},
    }

    with pytest.raises(SmartPSEException) as exc_info:
        build_smartpse_result(
            payload,
            {"estado": 200, "xml_firmado": "<Invoice/>", "cdr": cdr_xml},
            endpoint="/api/cpe/procesar",
            status_code=200,
        )

    assert expected_message in str(exc_info.value)


def test_sale_cdr_with_nonzero_response_is_definitive_rejection():
    payload = {
        "serie": "F001",
        "correlativo": "00000001",
        "tipoDoc": "01",
        "company": {"ruc": "20123456789"},
    }

    with pytest.raises(SmartPSEDefinitiveRejection) as exc_info:
        build_smartpse_result(
            payload,
            {
                "estado": 200,
                "xml_firmado": "<Invoice/>",
                "cdr": _sale_cdr(response_code="2335"),
            },
            endpoint="/api/cpe/procesar",
            status_code=200,
        )

    assert "2335" in str(exc_info.value)


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


def test_sale_ticket_response_without_cdr_stays_pending_when_cdr_required():
    payload = {"serie": "F001", "correlativo": "00000001", "tipoDoc": "01"}
    data = {
        "estado": 200,
        "mensaje": "Documento enviado, consulte ticket",
        "ticket": "TICKET-1",
        "xml_firmado": "<Invoice/>",
        "rechazado": False,
    }

    result = build_smartpse_result(
        payload,
        data,
        endpoint="/api/cpe/procesar",
        status_code=200,
        require_cdr=True,
    )

    assert result["success"] is True
    assert result["pending"] is True
    assert result["ticket"] == "TICKET-1"
    assert result["cdr_xml"] is None
