from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import re
from xml.etree import ElementTree as ET


NS = {
    "invoice": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "credit": "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2",
    "debit": "urn:oasis:names:specification:ubl:schema:xsd:DebitNote-2",
    "despatch": "urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2",
    "summary": "urn:sunat:names:specification:ubl:peru:schema:xsd:SummaryDocuments-1",
    "voided": "urn:sunat:names:specification:ubl:peru:schema:xsd:VoidedDocuments-1",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "sac": "urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1",
}

for prefix, uri in NS.items():
    if prefix in {"invoice", "credit", "debit", "despatch", "summary", "voided"}:
        continue
    ET.register_namespace(prefix, uri)


def _q(prefix: str, tag: str) -> str:
    return f"{{{NS[prefix]}}}{tag}"


def _add(parent: ET.Element, prefix: str, tag: str, text=None, **attrs) -> ET.Element:
    node = ET.SubElement(parent, _q(prefix, tag), {key: str(value) for key, value in attrs.items() if value is not None})
    if text is not None:
        node.text = str(text)
    return node


def _money(value) -> str:
    try:
        return f"{Decimal(str(value or 0)):.2f}"
    except Exception:
        return "0.00"


def _unit_price(value) -> str:
    try:
        normalized = Decimal(str(value or 0)).quantize(Decimal("0.0000000001"), rounding=ROUND_HALF_UP)
        return f"{normalized:f}"
    except Exception:
        return "0.0000000000"


def _quantity(value) -> str:
    try:
        normalized = Decimal(str(value or 0))
        return f"{normalized.normalize():f}"
    except Exception:
        return "0"


def _date_time(value: str | None) -> tuple[str, str]:
    text = str(value or "").strip()
    if "T" in text:
        date_part, time_part = text.split("T", 1)
        time_part = time_part.split("-", 1)[0].split("+", 1)[0]
        return date_part, time_part or "00:00:00"
    if len(text) >= 10:
        return text[:10], "00:00:00"
    now = datetime.now()
    return now.date().isoformat(), now.time().replace(microsecond=0).isoformat()


_BATCH_DOC_TYPES = {"RC", "RA", "RR"}
_COMPACT_DATE_RE = re.compile(r"^\d{8}$")
_DATE_PREFIXED_CORRELATIVO_RE = re.compile(r"^\d{8}-\d+(?:-\d+)?$")
_SMARTPSE_DOCUMENT_CORRELATIVO_WIDTH = 8


def _compact_date(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y%m%d")

    text = str(value or "").strip()
    if _COMPACT_DATE_RE.match(text):
        return text
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10].replace("-", "")

    return datetime.now().strftime("%Y%m%d")


def _strip_batch_prefix(value) -> str:
    normalized = str(value or "").strip().upper()
    for prefix in _BATCH_DOC_TYPES:
        marker = f"{prefix}-"
        if normalized.startswith(marker):
            return normalized[len(marker) :]
    return normalized


def _batch_reference_date(payload: dict, tipo_doc: str):
    if tipo_doc == "RC":
        return payload.get("fecResumen") or payload.get("fecGeneracion")
    return payload.get("fecComunicacion") or payload.get("fecResumen") or payload.get("fecGeneracion")


def normalize_batch_correlativo(payload: dict, tipo_doc: str) -> str:
    """Return the Smart PSE batch suffix as YYYYMMDD-NNNNN."""
    tipo_doc = str(tipo_doc or payload.get("tipoDoc") or "").strip().upper()
    raw = _strip_batch_prefix(payload.get("correlativo"))
    if _DATE_PREFIXED_CORRELATIVO_RE.match(raw):
        return raw

    suffix = raw or "1"
    if suffix.isdigit():
        suffix = suffix.zfill(5)
    return f"{_compact_date(_batch_reference_date(payload, tipo_doc))}-{suffix}"


def normalize_smartpse_document_correlativo(value) -> str:
    """Format regular CPE correlatives for Smart PSE XML and ZIP names.

    Smart PSE requires the document identifier to use an eight-digit numeric
    correlative (for example, E001-00007245). The database keeps the numeric
    value itself, so this formatting is intentionally limited to provider
    payload generation.
    """
    normalized = str(value or "").strip()
    if normalized.isdigit():
        return normalized.zfill(_SMARTPSE_DOCUMENT_CORRELATIVO_WIDTH)
    return normalized


def _date_only(value: str | None) -> str:
    return _date_time(value)[0]


def _document_id(payload: dict) -> str:
    return f"{payload.get('serie')}-{normalize_smartpse_document_correlativo(payload.get('correlativo'))}"


def _company(payload: dict) -> dict:
    return payload.get("company") or {}


def _address(data: dict) -> dict:
    return data.get("address") or {}


def _add_ubl_extensions(root: ET.Element) -> None:
    extensions = _add(root, "ext", "UBLExtensions")
    extension = _add(extensions, "ext", "UBLExtension")
    _add(extension, "ext", "ExtensionContent")


def _add_signature(root: ET.Element, company: dict) -> None:
    ruc = company.get("ruc") or ""
    name = company.get("razonSocial") or company.get("nombreComercial") or ""
    signature_id = f"SIGN-{ruc}"
    signature = _add(root, "cac", "Signature")
    _add(signature, "cbc", "ID", signature_id)
    party = _add(signature, "cac", "SignatoryParty")
    party_id = _add(party, "cac", "PartyIdentification")
    _add(party_id, "cbc", "ID", ruc)
    party_name = _add(party, "cac", "PartyName")
    _add(party_name, "cbc", "Name", name)
    attachment = _add(signature, "cac", "DigitalSignatureAttachment")
    reference = _add(attachment, "cac", "ExternalReference")
    _add(reference, "cbc", "URI", f"#{signature_id}")


def _add_supplier(root: ET.Element, company: dict) -> None:
    supplier = _add(root, "cac", "AccountingSupplierParty")
    party = _add(supplier, "cac", "Party")
    identification = _add(party, "cac", "PartyIdentification")
    _add(identification, "cbc", "ID", company.get("ruc"), schemeID="6")
    party_name = _add(party, "cac", "PartyName")
    _add(party_name, "cbc", "Name", company.get("razonSocial") or company.get("nombreComercial") or "")
    legal = _add(party, "cac", "PartyLegalEntity")
    _add(legal, "cbc", "RegistrationName", company.get("razonSocial") or company.get("nombreComercial") or "")
    registration = _add(legal, "cac", "RegistrationAddress")
    address = _address(company)
    _add(registration, "cbc", "ID", address.get("ubigueo") or address.get("ubigeo") or "150101")
    _add(registration, "cbc", "AddressTypeCode", address.get("codLocal") or address.get("codEstablecimiento") or "0000")
    line = _add(registration, "cac", "AddressLine")
    _add(line, "cbc", "Line", address.get("direccion") or "-")


def _add_legacy_supplier(root: ET.Element, company: dict) -> None:
    supplier = _add(root, "cac", "AccountingSupplierParty")
    _add(supplier, "cbc", "CustomerAssignedAccountID", company.get("ruc"))
    _add(supplier, "cbc", "AdditionalAccountID", "6")
    party = _add(supplier, "cac", "Party")
    party_name = _add(party, "cac", "PartyName")
    _add(party_name, "cbc", "Name", company.get("nombreComercial") or company.get("razonSocial") or "")
    legal = _add(party, "cac", "PartyLegalEntity")
    _add(legal, "cbc", "RegistrationName", company.get("razonSocial") or company.get("nombreComercial") or "")


def _add_customer(root: ET.Element, client: dict) -> None:
    customer = _add(root, "cac", "AccountingCustomerParty")
    party = _add(customer, "cac", "Party")
    identification = _add(party, "cac", "PartyIdentification")
    _add(identification, "cbc", "ID", client.get("numDoc"), schemeID=client.get("tipoDoc") or "0")
    legal = _add(party, "cac", "PartyLegalEntity")
    _add(legal, "cbc", "RegistrationName", client.get("rznSocial") or "-")


def _add_legacy_customer(parent: ET.Element, item: dict) -> None:
    customer = _add(parent, "cac", "AccountingCustomerParty")
    _add(customer, "cbc", "CustomerAssignedAccountID", item.get("clienteNro") or "-")
    _add(customer, "cbc", "AdditionalAccountID", item.get("clienteTipo") or "0")


def _add_tax_total(parent: ET.Element, taxable, tax_amount) -> None:
    tax_total = _add(parent, "cac", "TaxTotal")
    _add(tax_total, "cbc", "TaxAmount", _money(tax_amount), currencyID="PEN")
    subtotal = _add(tax_total, "cac", "TaxSubtotal")
    _add(subtotal, "cbc", "TaxableAmount", _money(taxable), currencyID="PEN")
    _add(subtotal, "cbc", "TaxAmount", _money(tax_amount), currencyID="PEN")
    category = _add(subtotal, "cac", "TaxCategory")
    _add(category, "cbc", "Percent", "18.00" if Decimal(_money(tax_amount)) > 0 else "0.00")
    _add(category, "cbc", "TaxExemptionReasonCode", "10" if Decimal(_money(tax_amount)) > 0 else "20")
    scheme = _add(category, "cac", "TaxScheme")
    _add(scheme, "cbc", "ID", "1000")
    _add(scheme, "cbc", "Name", "IGV")
    _add(scheme, "cbc", "TaxTypeCode", "VAT")


def _add_payment_terms(root: ET.Element, payload: dict) -> None:
    forma_pago = payload.get("formaPago") if isinstance(payload.get("formaPago"), dict) else {}
    tipo_pago = str(forma_pago.get("tipo") or "Contado").strip().lower()
    currency = payload.get("tipoMoneda") or "PEN"
    payment = _add(root, "cac", "PaymentTerms")
    _add(payment, "cbc", "ID", "FormaPago")
    _add(payment, "cbc", "PaymentMeansID", "Credito" if tipo_pago == "credito" else "Contado")
    if tipo_pago == "credito":
        _add(payment, "cbc", "Amount", _money(forma_pago.get("monto") or payload.get("mtoImporteTotal")), currencyID=currency)
        for index, cuota in enumerate(payload.get("cuotas") or [], start=1):
            cuota_node = _add(root, "cac", "PaymentTerms")
            _add(cuota_node, "cbc", "ID", "FormaPago")
            _add(cuota_node, "cbc", "PaymentMeansID", f"Cuota{index:03d}")
            _add(cuota_node, "cbc", "Amount", _money(cuota.get("monto")), currencyID=currency)
            due_date, _ = _date_time(cuota.get("fechaPago"))
            _add(cuota_node, "cbc", "PaymentDueDate", due_date)


def _add_monetary_total(root: ET.Element, payload: dict, *, tag: str = "LegalMonetaryTotal") -> None:
    total = _add(root, "cac", tag)
    _add(total, "cbc", "LineExtensionAmount", _money(payload.get("valorVenta")), currencyID=payload.get("tipoMoneda") or "PEN")
    _add(total, "cbc", "TaxInclusiveAmount", _money(payload.get("mtoImpVenta")), currencyID=payload.get("tipoMoneda") or "PEN")
    _add(total, "cbc", "PayableAmount", _money(payload.get("mtoImpVenta")), currencyID=payload.get("tipoMoneda") or "PEN")


def _add_sale_lines(root: ET.Element, payload: dict, *, tipo_doc: str) -> None:
    if tipo_doc == "07":
        line_tag, qty_tag = "CreditNoteLine", "CreditedQuantity"
    elif tipo_doc == "08":
        line_tag, qty_tag = "DebitNoteLine", "DebitedQuantity"
    else:
        line_tag, qty_tag = "InvoiceLine", "InvoicedQuantity"

    for index, item in enumerate(payload.get("details") or [], start=1):
        line = _add(root, "cac", line_tag)
        _add(line, "cbc", "ID", index)
        _add(line, "cbc", qty_tag, _quantity(item.get("cantidad")), unitCode=item.get("unidad") or "NIU")
        _add(line, "cbc", "LineExtensionAmount", _money(item.get("mtoValorVenta")), currencyID=payload.get("tipoMoneda") or "PEN")
        pricing = _add(line, "cac", "PricingReference")
        price_condition = _add(pricing, "cac", "AlternativeConditionPrice")
        _add(price_condition, "cbc", "PriceAmount", _unit_price(item.get("mtoPrecioUnitario")), currencyID=payload.get("tipoMoneda") or "PEN")
        _add(price_condition, "cbc", "PriceTypeCode", "01")
        _add_tax_total(line, item.get("mtoBaseIgv"), item.get("igv"))
        product = _add(line, "cac", "Item")
        _add(product, "cbc", "Description", item.get("descripcion") or "-")
        sellers = _add(product, "cac", "SellersItemIdentification")
        _add(sellers, "cbc", "ID", item.get("codProducto") or f"ITEM-{index:03d}")
        price = _add(line, "cac", "Price")
        _add(price, "cbc", "PriceAmount", _unit_price(item.get("mtoValorUnitario")), currencyID=payload.get("tipoMoneda") or "PEN")


def build_sale_document_xml(payload: dict) -> str:
    tipo_doc = str(payload.get("tipoDoc") or "").zfill(2)
    root_prefix = "credit" if tipo_doc == "07" else "debit" if tipo_doc == "08" else "invoice"
    root_name = "CreditNote" if tipo_doc == "07" else "DebitNote" if tipo_doc == "08" else "Invoice"
    root = ET.Element(_q(root_prefix, root_name), {"xmlns": NS[root_prefix]})
    _add_ubl_extensions(root)
    _add(root, "cbc", "UBLVersionID", payload.get("ublVersion") or "2.1")
    _add(root, "cbc", "CustomizationID", "2.0")
    _add(
        root,
        "cbc",
        "ProfileID",
        payload.get("tipoOperacion") or "0101",
        schemeName="SUNAT:Identificador de Tipo de Operacion",
        schemeAgencyName="PE:SUNAT",
        schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo17",
    )
    _add(root, "cbc", "ID", _document_id(payload))
    issue_date, issue_time = _date_time(payload.get("fechaEmision"))
    _add(root, "cbc", "IssueDate", issue_date)
    _add(root, "cbc", "IssueTime", issue_time)

    if tipo_doc == "07":
        _add(root, "cbc", "CreditNoteTypeCode", payload.get("codMotivo") or "01")
        for legend in payload.get("legends") or []:
            _add(root, "cbc", "Note", legend.get("value"), languageLocaleID=legend.get("code") or "1000")
        _add(root, "cbc", "DocumentCurrencyCode", payload.get("tipoMoneda") or "PEN")
        _add_note_reference(root, payload)
    elif tipo_doc == "08":
        for legend in payload.get("legends") or []:
            _add(root, "cbc", "Note", legend.get("value"), languageLocaleID=legend.get("code") or "1000")
        _add(root, "cbc", "DocumentCurrencyCode", payload.get("tipoMoneda") or "PEN")
        _add_note_reference(root, payload)
    else:
        _add(
            root,
            "cbc",
            "InvoiceTypeCode",
            tipo_doc,
            listID=payload.get("tipoOperacion") or "0101",
            listAgencyName="PE:SUNAT",
            name="Tipo de Operacion",
            listSchemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo51",
        )
        for legend in payload.get("legends") or []:
            _add(root, "cbc", "Note", legend.get("value"), languageLocaleID=legend.get("code") or "1000")
        _add(root, "cbc", "DocumentCurrencyCode", payload.get("tipoMoneda") or "PEN")
    company = _company(payload)
    _add_signature(root, company)
    _add_supplier(root, company)
    _add_customer(root, payload.get("client") or {})
    if tipo_doc not in {"07", "08"}:
        _add_payment_terms(root, payload)
    _add_tax_total(root, payload.get("valorVenta"), payload.get("mtoIGV") or payload.get("totalImpuestos"))
    total_tag = "RequestedMonetaryTotal" if tipo_doc == "08" else "LegalMonetaryTotal"
    _add_monetary_total(root, payload, tag=total_tag)
    _add_sale_lines(root, payload, tipo_doc=tipo_doc)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def _add_note_reference(root: ET.Element, payload: dict) -> None:
    discrepancy = _add(root, "cac", "DiscrepancyResponse")
    _add(discrepancy, "cbc", "ReferenceID", payload.get("numDocfectado") or payload.get("numDocAfectado") or "")
    _add(discrepancy, "cbc", "ResponseCode", payload.get("codMotivo") or "01")
    _add(discrepancy, "cbc", "Description", payload.get("desMotivo") or "")
    billing = _add(root, "cac", "BillingReference")
    invoice = _add(billing, "cac", "InvoiceDocumentReference")
    _add(invoice, "cbc", "ID", payload.get("numDocfectado") or payload.get("numDocAfectado") or "")
    _add(invoice, "cbc", "DocumentTypeCode", payload.get("tipDocAfectado") or "")


def build_despatch_document_xml(payload: dict) -> str:
    root = ET.Element(_q("despatch", "DespatchAdvice"), {"xmlns": NS["despatch"]})
    _add_ubl_extensions(root)
    _add(root, "cbc", "UBLVersionID", "2.1")
    _add(root, "cbc", "CustomizationID", "2.0")
    _add(root, "cbc", "ID", _document_id(payload))
    issue_date, issue_time = _date_time(payload.get("fechaEmision"))
    _add(root, "cbc", "IssueDate", issue_date)
    _add(root, "cbc", "IssueTime", issue_time)
    _add(root, "cbc", "DespatchAdviceTypeCode", "09")
    company = _company(payload)
    _add_signature(root, company)
    _add_supplier(root, company)
    _add_despatch_customer(root, payload.get("destinatario") or payload.get("client") or {})
    envio = payload.get("envio") or {}
    shipment = _add(root, "cac", "Shipment")
    _add(shipment, "cbc", "ID", "1")
    _add(shipment, "cbc", "HandlingCode", envio.get("codTraslado") or "01")
    if envio.get("desTraslado"):
        _add(shipment, "cbc", "Information", envio.get("desTraslado"))
    if envio.get("indTransbordo") is not None:
        _add(shipment, "cbc", "SplitConsignmentIndicator", str(bool(envio.get("indTransbordo"))).lower())
    if envio.get("numBultos") is not None:
        _add(shipment, "cbc", "TotalTransportHandlingUnitQuantity", envio.get("numBultos"))
    handling = _add(shipment, "cac", "ShipmentStage")
    _add(handling, "cbc", "TransportModeCode", envio.get("modTraslado") or "02")
    transit = _add(handling, "cac", "TransitPeriod")
    _add(transit, "cbc", "StartDate", _date_only(envio.get("fecTraslado")))
    transportista = envio.get("transportista") or {}
    if transportista:
        carrier = _add(handling, "cac", "CarrierParty")
        party_id = _add(carrier, "cac", "PartyIdentification")
        _add(party_id, "cbc", "ID", transportista.get("numDoc"), schemeID=transportista.get("tipoDoc") or "6")
        legal = _add(carrier, "cac", "PartyLegalEntity")
        _add(legal, "cbc", "RegistrationName", transportista.get("rznSocial") or "-")
    vehiculo = envio.get("vehiculo") or {}
    placa = vehiculo.get("placa") or transportista.get("placa")
    if placa:
        means = _add(handling, "cac", "TransportMeans")
        road = _add(means, "cac", "RoadTransport")
        _add(road, "cbc", "LicensePlateID", placa)
    for chofer in envio.get("choferes") or []:
        driver = _add(handling, "cac", "DriverPerson")
        _add(driver, "cbc", "ID", chofer.get("nroDoc"), schemeID=chofer.get("tipoDoc") or "1")
        if chofer.get("nombres"):
            _add(driver, "cbc", "FirstName", chofer.get("nombres"))
        if chofer.get("apellidos"):
            _add(driver, "cbc", "FamilyName", chofer.get("apellidos"))
        if chofer.get("licencia"):
            _add(driver, "cbc", "LicenseID", chofer.get("licencia"))
    delivery = _add(shipment, "cac", "Delivery")
    for tag_name, source in (("DeliveryAddress", envio.get("llegada") or {}), ("DespatchAddress", envio.get("partida") or {})):
        address = _add(delivery, "cac", tag_name)
        _add(address, "cbc", "ID", source.get("ubigueo") or source.get("ubigeo") or "150101")
        line = _add(address, "cac", "AddressLine")
        _add(line, "cbc", "Line", source.get("direccion") or "-")
    _add(shipment, "cbc", "GrossWeightMeasure", _quantity(envio.get("pesoTotal")), unitCode=envio.get("undPesoTotal") or "KGM")
    for index, item in enumerate(payload.get("details") or [], start=1):
        line = _add(root, "cac", "DespatchLine")
        _add(line, "cbc", "ID", index)
        _add(line, "cbc", "DeliveredQuantity", _quantity(item.get("cantidad")), unitCode=item.get("unidad") or item.get("unidad_medida") or "NIU")
        product = _add(line, "cac", "Item")
        _add(product, "cbc", "Description", item.get("descripcion") or "-")
        sellers = _add(product, "cac", "SellersItemIdentification")
        _add(sellers, "cbc", "ID", item.get("codigo") or item.get("codigo_producto") or f"ITEM-{index:03d}")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def _add_despatch_customer(root: ET.Element, party_data: dict) -> None:
    customer = _add(root, "cac", "DeliveryCustomerParty")
    party = _add(customer, "cac", "Party")
    identification = _add(party, "cac", "PartyIdentification")
    _add(identification, "cbc", "ID", party_data.get("numDoc"), schemeID=party_data.get("tipoDoc") or "6")
    legal = _add(party, "cac", "PartyLegalEntity")
    _add(legal, "cbc", "RegistrationName", party_data.get("rznSocial") or "-")


def build_summary_document_xml(payload: dict) -> str:
    root = ET.Element(_q("summary", "SummaryDocuments"), {"xmlns": NS["summary"]})
    _add_ubl_extensions(root)
    _add(root, "cbc", "UBLVersionID", "2.0")
    _add(root, "cbc", "CustomizationID", "1.1")
    batch_correlativo = normalize_batch_correlativo(payload, "RC")
    _add(root, "cbc", "ID", f"RC-{batch_correlativo}")
    gen_date, _ = _date_time(payload.get("fecGeneracion"))
    ref_date, _ = _date_time(payload.get("fecResumen"))
    _add(root, "cbc", "ReferenceDate", ref_date)
    _add(root, "cbc", "IssueDate", gen_date)
    company = _company(payload)
    _add_signature(root, company)
    _add_legacy_supplier(root, company)
    for index, item in enumerate(payload.get("details") or [], start=1):
        line = _add(root, "sac", "SummaryDocumentsLine")
        _add(line, "cbc", "LineID", index)
        _add(line, "cbc", "DocumentTypeCode", item.get("tipoDoc") or "03")
        _add(line, "cbc", "ID", item.get("serieNro") or "")
        _add_legacy_customer(line, item)
        status = _add(line, "cac", "Status")
        _add(status, "cbc", "ConditionCode", item.get("estado") or "1")
        _add(line, "sac", "TotalAmount", _money(item.get("total")), currencyID=payload.get("moneda") or "PEN")
        gravada = item.get("mtoOperGravadas")
        if gravada is not None:
            payment = _add(line, "sac", "BillingPayment")
            _add(payment, "cbc", "PaidAmount", _money(gravada), currencyID=payload.get("moneda") or "PEN")
            _add(payment, "cbc", "InstructionID", "01")
        _add_tax_total(line, item.get("mtoOperGravadas") or item.get("total"), item.get("mtoIGV") or 0)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def build_voided_document_xml(payload: dict) -> str:
    root = ET.Element(_q("voided", "VoidedDocuments"), {"xmlns": NS["voided"]})
    _add_ubl_extensions(root)
    _add(root, "cbc", "UBLVersionID", "2.0")
    _add(root, "cbc", "CustomizationID", "1.0")
    tipo_doc = str(payload.get("tipoDoc") or "RA").upper()
    batch_correlativo = normalize_batch_correlativo(payload, tipo_doc)
    _add(root, "cbc", "ID", f"{tipo_doc}-{batch_correlativo}")
    gen_date, _ = _date_time(payload.get("fecGeneracion"))
    ref_date, _ = _date_time(payload.get("fecComunicacion") or payload.get("fecResumen"))
    _add(root, "cbc", "ReferenceDate", ref_date)
    _add(root, "cbc", "IssueDate", gen_date)
    company = _company(payload)
    _add_signature(root, company)
    _add_legacy_supplier(root, company)
    for index, item in enumerate(payload.get("details") or [], start=1):
        line = _add(root, "sac", "VoidedDocumentsLine")
        _add(line, "cbc", "LineID", index)
        _add(line, "cbc", "DocumentTypeCode", item.get("tipoDoc") or "01")
        _add(line, "sac", "DocumentSerialID", item.get("serie") or "")
        _add(line, "sac", "DocumentNumberID", item.get("correlativo") or "")
        _add(line, "sac", "VoidReasonDescription", item.get("desMotivoBaja") or item.get("motivo") or "ERROR")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def build_smartpse_filename(payload: dict) -> str:
    company = _company(payload)
    ruc = "".join(ch for ch in str(company.get("ruc") or "") if ch.isdigit())
    tipo_doc = str(payload.get("tipoDoc") or "").strip().upper()
    if tipo_doc in _BATCH_DOC_TYPES:
        batch_correlativo = normalize_batch_correlativo(payload, tipo_doc)
        return f"{ruc}-{tipo_doc}-{batch_correlativo}"
    correlativo = normalize_smartpse_document_correlativo(payload.get("correlativo"))
    return f"{ruc}-{tipo_doc}-{payload.get('serie')}-{correlativo}"
