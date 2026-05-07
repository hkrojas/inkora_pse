from __future__ import annotations

from xml.etree import ElementTree as ET


MAX_QR_CONTENT_LENGTH = 180

NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}


def _text(node: ET.Element | None) -> str | None:
    if node is None or node.text is None:
        return None
    value = node.text.strip()
    return value or None


def _find_text(root: ET.Element, path: str) -> str | None:
    return _text(root.find(path, NS))


def _root_name(root: ET.Element) -> str:
    return root.tag.rsplit("}", 1)[-1]


def _document_type(root: ET.Element) -> str | None:
    name = _root_name(root)
    if name == "Invoice":
        return _find_text(root, "./cbc:InvoiceTypeCode")
    if name == "CreditNote":
        return "07"
    if name == "DebitNote":
        return "08"
    return None


def _document_id_parts(root: ET.Element) -> tuple[str | None, str | None]:
    document_id = _find_text(root, "./cbc:ID")
    if not document_id or "-" not in document_id:
        return document_id, None
    serie, correlativo = document_id.split("-", 1)
    return serie, correlativo


def _party_id(root: ET.Element, path: str) -> tuple[str | None, str | None]:
    party = root.find(path, NS)
    if party is None:
        return None, None
    identification = party.find("./cac:Party/cac:PartyIdentification/cbc:ID", NS)
    if identification is None:
        identification = party.find("./cac:PartyIdentification/cbc:ID", NS)
    if identification is None:
        return None, None
    return _text(identification), identification.attrib.get("schemeID")


def _payable_amount(root: ET.Element) -> str | None:
    for path in (
        "./cac:LegalMonetaryTotal/cbc:PayableAmount",
        "./cac:RequestedMonetaryTotal/cbc:PayableAmount",
        "./cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount",
        "./cac:RequestedMonetaryTotal/cbc:TaxInclusiveAmount",
    ):
        value = _find_text(root, path)
        if value:
            return value
    return None


def _digest_value(root: ET.Element) -> str | None:
    digest = _find_text(root, ".//ds:DigestValue")
    if digest:
        return digest
    return _find_text(root, ".//DigestValue")


def _empty_if_none(value: str | None) -> str:
    return value or ""


def _build_content(fields: list[str], summary: str | None, *, include_summary: bool) -> str:
    values = list(fields)
    if include_summary and summary:
        values.append(summary)
    return "|".join(_empty_if_none(value) for value in values)


def build_sunat_qr_payload(xml_content: str | None, *, provider_hash: str | None = None) -> dict | None:
    if not xml_content:
        return None

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return None

    root_name = _root_name(root)
    if root_name not in {"Invoice", "CreditNote", "DebitNote"}:
        return None

    serie, numero = _document_id_parts(root)
    supplier_number, _ = _party_id(root, "./cac:AccountingSupplierParty")
    customer_number, customer_type = _party_id(root, "./cac:AccountingCustomerParty")
    digest = _digest_value(root)
    digest_source = "xml_digest" if digest else None
    if not digest and provider_hash:
        digest = str(provider_hash).strip() or None
        digest_source = "provider_hash" if digest else None

    base_fields = [
        _empty_if_none(supplier_number),
        _empty_if_none(_document_type(root)),
        _empty_if_none(serie),
        _empty_if_none(numero),
        _empty_if_none(_find_text(root, "./cac:TaxTotal/cbc:TaxAmount")),
        _empty_if_none(_payable_amount(root)),
        _empty_if_none(_find_text(root, "./cbc:IssueDate")),
        _empty_if_none(customer_type),
        _empty_if_none(customer_number),
    ]

    content_with_summary = _build_content(base_fields, digest, include_summary=True)
    digest_in_qr = bool(digest) and len(content_with_summary) <= MAX_QR_CONTENT_LENGTH
    qr_content = content_with_summary if digest_in_qr else _build_content(base_fields, digest, include_summary=False)

    return {
        "ruc": base_fields[0],
        "tipo": base_fields[1],
        "serie": base_fields[2],
        "numero": base_fields[3],
        "igv": base_fields[4],
        "total": base_fields[5],
        "emision": base_fields[6],
        "clienteTipo": base_fields[7],
        "clienteNumero": base_fields[8],
        "valorResumen": digest,
        "digest_source": digest_source or "missing",
        "digest_in_qr": digest_in_qr,
        "qr_content": qr_content,
        "qr_visible_summary": None if digest_in_qr else digest,
    }
