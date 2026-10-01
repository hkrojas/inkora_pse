import base64
from io import BytesIO
import zipfile

import pytest

from services import gre_qr_service, smartpse_response


QR_URL = (
    "https://e-factura.sunat.gob.pe/v1/contribuyente/gre/comprobantes/descargaqr"
    "?hashqr=/tcJ/QNiVAdtOt8ZmMNJEgnYeGN+DATOS+SINTETICOS="
)
CDR = f"""<ApplicationResponse xmlns="urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2"
 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
 <cac:ReceiverParty><cac:PartyIdentification><cbc:ID>20606751509</cbc:ID></cac:PartyIdentification></cac:ReceiverParty>
 <cac:DocumentResponse>
  <cac:Response>
   <cbc:ReferenceID>TI01-000004</cbc:ReferenceID><cbc:ResponseCode>0</cbc:ResponseCode>
   <cbc:Description>El Comprobante numero TI01-000004, ha sido aceptado</cbc:Description>
  </cac:Response>
  <cac:DocumentReference>
   <cbc:ID>TI01-000004</cbc:ID><cbc:DocumentDescription>{QR_URL}</cbc:DocumentDescription>
  </cac:DocumentReference>
 </cac:DocumentResponse>
</ApplicationResponse>"""


def _extract(cdr=CDR, **kwargs):
    return gre_qr_service.extract_qr_content(
        cdr,
        issuer_ruc=kwargs.get("issuer_ruc", "20606751509"),
        document_type=kwargs.get("document_type", "09"),
        document_id=kwargs.get("document_id", "TI01-4"),
    )


def test_accepted_cdr_supplies_exact_qr_url_without_reencoding_hash():
    assert _extract() == QR_URL


def test_gre_31_uses_its_own_cdr_and_document_identity():
    assert _extract(CDR.replace("TI01", "VI01"), document_type="31", document_id="VI01-4") == QR_URL


def test_qr_is_extracted_from_smartpse_consultation_cdr_zip_without_signed_xml():
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("R-20606751509-09-TI01-000004.xml", CDR)
    response = {"verification": {"estado": "0", "cdr": base64.b64encode(buffer.getvalue()).decode()}}
    assert _extract(smartpse_response.extract_cdr_xml(response)) == QR_URL


@pytest.mark.parametrize("cdr", [
    None,
    "no-es-xml",
    CDR.replace("ApplicationResponse", "DespatchAdvice"),
    CDR.replace("<cbc:ResponseCode>0</cbc:ResponseCode>", "<cbc:ResponseCode>4000</cbc:ResponseCode>"),
    CDR.replace("TI01-000004", "TI01-000005"),
    CDR.replace("<cbc:ReferenceID>TI01-000004</cbc:ReferenceID>", "<cbc:ReferenceID>VI01-000004</cbc:ReferenceID>"),
    CDR.replace("20606751509", "20600000001"),
    CDR.replace("<cbc:ID>TI01-000004</cbc:ID>", ""),
    CDR.replace("<cbc:ID>TI01-000004</cbc:ID>", "<cbc:ID>TI01-000004</cbc:ID><cbc:DocumentTypeCode>31</cbc:DocumentTypeCode>"),
    CDR.replace(f"<cbc:DocumentDescription>{QR_URL}</cbc:DocumentDescription>", ""),
])
def test_missing_rejected_or_unrelated_evidence_cannot_supply_qr(cdr):
    assert _extract(cdr) is None


@pytest.mark.parametrize("kwargs", [
    {"issuer_ruc": None},
    {"issuer_ruc": "20600000001"},
    {"document_type": "01"},
    {"document_type": "31"},
    {"document_id": "TI01-5"},
    {"document_id": "TI01-"},
])
def test_qr_requires_the_requested_guide_and_issuer(kwargs):
    assert _extract(**kwargs) is None


@pytest.mark.parametrize("series", ["EG07", "F001", "T01", "TI001", "T!01"])
def test_qr_requires_a_remitente_series_from_the_contributor_emission_system(series):
    assert _extract(CDR.replace("TI01", series), document_id=f"{series}-4") is None


@pytest.mark.parametrize("url", [
    QR_URL.replace("https://", "http://"),
    QR_URL.replace("e-factura.sunat.gob.pe", "e-factura.sunat.gob.pe.ejemplo.test"),
    QR_URL.replace("e-factura.sunat.gob.pe", "usuario@e-factura.sunat.gob.pe"),
    QR_URL.replace("e-factura.sunat.gob.pe", "e-factura.sunat.gob.pe:8443"),
    QR_URL.replace("descargaqr", "otro-recurso"),
    QR_URL.split("?", 1)[0],
    QR_URL.split("?", 1)[0] + "?hashqr=",
    QR_URL + "&amp;hashqr=otro",
    QR_URL + "#fragmento",
    QR_URL + "\ncontenido",
])
def test_qr_rejects_urls_outside_the_sunat_cdr_contract(url):
    assert _extract(CDR.replace(QR_URL, url)) is None


def test_ambiguous_cdr_with_two_document_responses_does_not_supply_qr():
    response = CDR.split("<cac:DocumentResponse>", 1)[1].split("</cac:DocumentResponse>", 1)[0]
    assert _extract(CDR.replace("</ApplicationResponse>", f"<cac:DocumentResponse>{response}</cac:DocumentResponse></ApplicationResponse>")) is None
