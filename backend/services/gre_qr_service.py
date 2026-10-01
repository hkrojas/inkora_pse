"""Read SUNAT's GRE QR content from a matching, accepted CDR.

The CDR supplies the URL to encode. Inkora renders the QR locally; neither a
provider-generated image nor an HTTP request to that URL is needed.
"""
from __future__ import annotations

from urllib.parse import parse_qs, urlsplit
from xml.etree import ElementTree as ET


NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
}
APPLICATION_RESPONSE_TAG = (
    "{urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2}ApplicationResponse"
)
SUNAT_QR_HOST = "e-factura.sunat.gob.pe"
SUNAT_QR_PATH = "/v1/contribuyente/gre/comprobantes/descargaqr"


def document_id_matches(actual: str | None, expected: str | None) -> bool:
    def parts(value):
        series, separator, number = str(value or "").strip().partition("-")
        if not separator or not series or not number.isascii() or not number.isdigit():
            return None
        return series.upper(), number.lstrip("0") or "0"

    actual_parts = parts(actual)
    return actual_parts is not None and actual_parts == parts(expected)


def _sunat_qr_url(value: str | None) -> str | None:
    content = str(value or "").strip()
    if not content or len(content) > 2048 or any(char.isspace() for char in content):
        return None
    try:
        parsed = urlsplit(content)
        query = parse_qs(parsed.query, keep_blank_values=True)
    except ValueError:
        return None
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != SUNAT_QR_HOST
        or parsed.path != SUNAT_QR_PATH
        or parsed.fragment
        or set(query) != {"hashqr"}
        or len(query["hashqr"]) != 1
        or not query["hashqr"][0].strip()
    ):
        return None
    # Keep the exact CDR content: decoding/re-encoding '+' or '/' changes hashqr.
    return content


def extract_qr_content(
    cdr_xml: str | None,
    *,
    issuer_ruc: str | None,
    document_type: str | None,
    document_id: str,
) -> str | None:
    if not cdr_xml or not issuer_ruc or document_type not in {"09", "31"}:
        return None
    series = str(document_id).partition("-")[0].upper()
    if len(series) != 4 or not series.isascii() or not series.isalnum():
        return None
    if not series.startswith("T" if document_type == "09" else "V"):
        return None
    try:
        root = ET.fromstring(cdr_xml)
    except (ET.ParseError, TypeError, ValueError):
        return None
    if root.tag != APPLICATION_RESPONSE_TAG:
        return None
    receiver_ruc = root.findtext("./cac:ReceiverParty/cac:PartyIdentification/cbc:ID", namespaces=NS)
    if str(receiver_ruc or "").strip() != str(issuer_ruc).strip():
        return None
    responses = root.findall("./cac:DocumentResponse", NS)
    if len(responses) != 1:
        return None
    response = responses[0]
    code = response.findtext("./cac:Response/cbc:ResponseCode", namespaces=NS)
    if str(code or "").strip() != "0":
        return None
    reference_id = response.findtext("./cac:Response/cbc:ReferenceID", namespaces=NS)
    if reference_id and not document_id_matches(reference_id, document_id):
        return None
    reference = response.find("./cac:DocumentReference", NS)
    if reference is None or not document_id_matches(reference.findtext("cbc:ID", namespaces=NS), document_id):
        return None
    cdr_type = reference.findtext("cbc:DocumentTypeCode", namespaces=NS)
    if cdr_type and cdr_type.strip() != document_type:
        return None
    candidates = {
        url
        for node in reference.findall("cbc:DocumentDescription", NS)
        if (url := _sunat_qr_url(node.text))
    }
    return next(iter(candidates)) if len(candidates) == 1 else None
