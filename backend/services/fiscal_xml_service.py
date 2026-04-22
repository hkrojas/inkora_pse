from __future__ import annotations

from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET


NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "sac": "urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1",
}


def _text(node: ET.Element | None) -> str | None:
    if node is None or node.text is None:
        return None
    value = node.text.strip()
    return value or None


def _decimal(value: str | None) -> Decimal:
    if not value:
        return Decimal("0.00")
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def _find_text(root: ET.Element, path: str) -> str | None:
    return _text(root.find(path, NS))


def _extract_party(root: ET.Element, base_path: str) -> dict:
    node = root.find(base_path, NS)
    if node is None:
        return {}

    identification_node = node.find("./cac:Party/cac:PartyIdentification/cbc:ID", NS)
    if identification_node is None:
        identification_node = node.find("./cac:PartyIdentification/cbc:ID", NS)

    name_node = node.find("./cac:Party/cac:PartyLegalEntity/cbc:RegistrationName", NS)
    if name_node is None:
        name_node = node.find("./cac:PartyLegalEntity/cbc:RegistrationName", NS)
    if name_node is None:
        name_node = node.find("./cac:Party/cac:PartyName/cbc:Name", NS)
    if name_node is None:
        name_node = node.find("./cac:PartyName/cbc:Name", NS)

    address_node = node.find("./cac:Party/cac:PartyLegalEntity/cac:RegistrationAddress/cac:AddressLine/cbc:Line", NS)
    if address_node is None:
        address_node = node.find("./cac:Party/cac:PostalAddress/cbc:StreetName", NS)
    if address_node is None:
        address_node = node.find("./cac:PartyLegalEntity/cac:RegistrationAddress/cac:AddressLine/cbc:Line", NS)
    if address_node is None:
        address_node = node.find("./cac:PostalAddress/cbc:StreetName", NS)

    ubigeo_node = node.find("./cac:Party/cac:PartyLegalEntity/cac:RegistrationAddress/cbc:ID", NS)
    if ubigeo_node is None:
        ubigeo_node = node.find("./cac:Party/cac:PostalAddress/cbc:ID", NS)
    if ubigeo_node is None:
        ubigeo_node = node.find("./cac:PartyLegalEntity/cac:RegistrationAddress/cbc:ID", NS)
    if ubigeo_node is None:
        ubigeo_node = node.find("./cac:PostalAddress/cbc:ID", NS)

    return {
        "doc_number": _text(identification_node),
        "doc_type": identification_node.attrib.get("schemeID") if identification_node is not None else None,
        "name": _text(name_node),
        "address": _text(address_node),
        "ubigeo": _text(ubigeo_node),
    }


def _extract_document_lines(root: ET.Element) -> list[dict]:
    line_specs = [
        ("./cac:InvoiceLine", "./cbc:InvoicedQuantity"),
        ("./cac:CreditNoteLine", "./cbc:CreditedQuantity"),
        ("./cac:DebitNoteLine", "./cbc:DebitedQuantity"),
    ]

    for line_path, qty_path in line_specs:
        lines = root.findall(line_path, NS)
        if not lines:
            continue

        parsed = []
        for line in lines:
            qty_node = line.find(qty_path, NS)
            price_amount = _text(line.find("./cac:PricingReference/cac:AlternativeConditionPrice/cbc:PriceAmount", NS))
            if not price_amount:
                price_amount = _text(line.find("./cac:Price/cbc:PriceAmount", NS))

            parsed.append(
                {
                    "id": _text(line.find("./cbc:ID", NS)),
                    "quantity": _decimal(_text(qty_node)),
                    "unit_code": qty_node.attrib.get("unitCode") if qty_node is not None else None,
                    "description": _text(line.find("./cac:Item/cbc:Description", NS)),
                    "code": _text(line.find("./cac:Item/cac:SellersItemIdentification/cbc:ID", NS)),
                    "line_extension_amount": _decimal(_text(line.find("./cbc:LineExtensionAmount", NS))),
                    "tax_amount": _decimal(_text(line.find("./cac:TaxTotal/cbc:TaxAmount", NS))),
                    "price_amount": _decimal(price_amount),
                }
            )
        return parsed

    return []


def parse_sale_document_xml(xml_content: str | None) -> dict | None:
    if not xml_content:
        return None

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return None

    root_name = root.tag.rsplit("}", 1)[-1]
    if root_name not in {"Invoice", "CreditNote", "DebitNote"}:
        return None

    document_id = _find_text(root, "./cbc:ID")
    serie = None
    correlativo = None
    if document_id and "-" in document_id:
        serie, correlativo = document_id.split("-", 1)

    doc_type_code = (
        _find_text(root, "./cbc:InvoiceTypeCode")
        or _find_text(root, "./cbc:CreditNoteTypeCode")
        or _find_text(root, "./cbc:DebitNoteTypeCode")
    )

    note_amount_words = None
    for note in root.findall("./cbc:Note", NS):
        if note.attrib.get("languageLocaleID") == "1000":
            note_amount_words = _text(note)
            break

    supplier = _extract_party(root, "./cac:AccountingSupplierParty")
    customer = _extract_party(root, "./cac:AccountingCustomerParty")
    monetary = root.find("./cac:LegalMonetaryTotal", NS)

    return {
        "root_name": root_name,
        "document_id": document_id,
        "serie": serie,
        "correlativo": correlativo,
        "tipo_comprobante": doc_type_code,
        "issue_date": _find_text(root, "./cbc:IssueDate"),
        "issue_time": _find_text(root, "./cbc:IssueTime"),
        "currency": _find_text(root, "./cbc:DocumentCurrencyCode") or "PEN",
        "amount_in_words": note_amount_words,
        "supplier": supplier,
        "customer": customer,
        "totals": {
            "tax_amount": _decimal(_find_text(root, "./cac:TaxTotal/cbc:TaxAmount")),
            "line_extension_amount": _decimal(
                _text(monetary.find("./cbc:LineExtensionAmount", NS)) if monetary is not None else None
            ),
            "tax_inclusive_amount": _decimal(
                _text(monetary.find("./cbc:TaxInclusiveAmount", NS)) if monetary is not None else None
            ),
            "payable_amount": _decimal(
                _text(monetary.find("./cbc:PayableAmount", NS)) if monetary is not None else None
            ),
        },
        "lines": _extract_document_lines(root),
    }


def build_sale_qr_payload_from_xml(xml_content: str | None) -> dict | None:
    parsed = parse_sale_document_xml(xml_content)
    if not parsed:
        return None

    supplier = parsed.get("supplier") or {}
    customer = parsed.get("customer") or {}
    totals = parsed.get("totals") or {}

    issue_date = parsed.get("issue_date")
    issue_time = parsed.get("issue_time") or "00:00:00"
    issue_datetime = f"{issue_date}T{issue_time}-05:00" if issue_date else None

    return {
        "ruc": supplier.get("doc_number"),
        "tipo": parsed.get("tipo_comprobante"),
        "serie": parsed.get("serie"),
        "numero": parsed.get("correlativo"),
        "emision": issue_datetime,
        "igv": float(totals.get("tax_amount") or 0),
        "total": float(totals.get("payable_amount") or 0),
        "clienteTipo": customer.get("doc_type"),
        "clienteNumero": customer.get("doc_number"),
    }
