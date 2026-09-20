"""Inkora printable representation for GRE 09 and GRE 31 documents."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from html import escape
from io import BytesIO
from xml.etree import ElementTree as ET

import qrcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch
from reportlab.platypus import (
    Image,
    KeepInFrame,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from services import pdf_generator, smartpse_response


_STATUS_META = {
    "pendiente": ("BORRADOR", "BORRADOR - SIN VALIDEZ FISCAL"),
    "pendiente_smartpse": ("PENDIENTE DE ACEPTACIÓN", "PENDIENTE DE ACEPTACIÓN"),
    "emitida": ("ACEPTADA POR SUNAT", None),
    "rechazada": ("RECHAZADA", "RECHAZADA"),
    "cancelada": ("CANCELADA", "CANCELADA"),
    "cancelado": ("CANCELADA", "CANCELADA"),
    "cancelled": ("CANCELADA", "CANCELADA"),
}

_PROVIDER_QR_KEYS = (
    "qr_content",
    "qrContent",
    "codigo_qr",
    "codigoQr",
    "contenido_qr",
    "contenidoQr",
)


def _text(value, fallback="-") -> str:
    rendered = str(value or "").strip()
    return escape(rendered) if rendered else fallback


def _format_date(value) -> str:
    if isinstance(value, (datetime, date)):
        return value.strftime("%d/%m/%Y")
    if value:
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%d/%m/%Y")
        except ValueError:
            return str(value)
    return "-"


def _format_time(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%H:%M")
    if value:
        text = str(value).strip()
        if "T" in text:
            text = text.split("T", 1)[1]
        return text[:5] or "-"
    return "-"


def _format_quantity(value) -> str:
    try:
        number = Decimal(str(value or 0))
    except Exception:
        return str(value or "0")
    if number == number.to_integral_value():
        return str(int(number))
    return f"{number:f}".rstrip("0").rstrip(".")


def _guide_number(guide) -> str:
    identity = smartpse_response.extract_gre_document_identity(
        getattr(guide, "sunat_xml_content", None)
    )
    if identity.get("document_id"):
        return str(identity["document_id"])
    return f"{guide.serie}-{str(guide.correlativo).zfill(6)}"


def _fiscal_identity(guide) -> dict:
    """Prefer the immutable signed GRE XML for identity and issue timestamps."""
    xml_content = getattr(guide, "sunat_xml_content", None)
    identity = smartpse_response.extract_gre_document_identity(xml_content)
    identity.update({"issue_date": None, "issue_time": None, "issuer_name": None})
    if not xml_content:
        return identity
    try:
        root = ET.fromstring(xml_content)
    except (ET.ParseError, TypeError):
        return identity
    ns = smartpse_response.NS
    identity["issue_date"] = root.findtext("cbc:IssueDate", namespaces=ns)
    identity["issue_time"] = root.findtext("cbc:IssueTime", namespaces=ns)
    identity["issuer_name"] = root.findtext(
        "cac:DespatchSupplierParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName",
        namespaces=ns,
    )
    return identity


def _reference_number(reference) -> str | None:
    if not reference:
        return None
    explicit = getattr(reference, "document_number", None)
    if explicit:
        return str(explicit)
    series = getattr(reference, "serie", None) or getattr(reference, "series", None)
    number = getattr(reference, "correlativo", None) or getattr(reference, "number", None)
    if series and number is not None:
        rendered = str(number)
        return f"{series}-{rendered.zfill(6) if rendered.isdigit() else rendered}"
    return None


def _invoice_reference(guide) -> str:
    return (
        _reference_number(getattr(guide, "cotizacion", None))
        or _reference_number(getattr(guide, "goods_invoice_reference", None))
        or "Referencia de bienes no consignada"
    )


def _source_document_label(guide) -> str:
    source = getattr(guide, "cotizacion", None)
    reference = getattr(guide, "goods_invoice_reference", None)
    document_type = getattr(source, "tipo_comprobante", None) or getattr(reference, "document_type", None)
    return "Boleta de venta" if document_type == "03" else "Factura de bienes"


def _transport_scenario(guide) -> str:
    if getattr(guide, "indicador_m1_l", False):
        return "Vehículo M1/L - no requiere conductor"
    if guide.tipo_documento == "31":
        return "GRE del transportista"
    if guide.modalidad_traslado == "01" and getattr(guide, "registrar_vehiculo_transportista", False):
        return "Público - vehículo y conductor registrados por acuerdo"
    if guide.modalidad_traslado == "01":
        return "Público - requiere GRE transportista 31"
    return "Privado - vehículo y conductor"


def _gre_reference(guide) -> str | None:
    return _reference_number(getattr(guide, "related_guide", None)) or _reference_number(
        getattr(guide, "external_gre_reference", None)
    )


def _recipient(guide) -> tuple[str, str, str]:
    client = getattr(guide, "cliente", None)
    if client is None:
        client = getattr(getattr(guide, "cotizacion", None), "cliente", None)
    name = (
        getattr(guide, "destinatario_razon_social", None)
        or getattr(guide, "cliente_nombre", None)
        or getattr(client, "razon_social", None)
        or getattr(client, "nombre", None)
        or "Destinatario no consignado"
    )
    document = (
        getattr(guide, "destinatario_nro_doc", None)
        or getattr(guide, "cliente_documento", None)
        or getattr(client, "numero_documento", None)
        or "-"
    )
    # The destination of a GRE is a fiscal/logistics fact. A later customer master-data
    # update must not replace it in the printable representation.
    address = getattr(guide, "llegada_direccion", None) or getattr(client, "direccion", None) or "-"
    return str(name), str(document), str(address)


def _extract_provider_qr(value) -> str | None:
    """Return only a QR payload explicitly supplied by the provider/SUNAT response."""
    if not isinstance(value, dict):
        return None
    for key in _PROVIDER_QR_KEYS:
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    qr_payload = value.get("qr_payload")
    if isinstance(qr_payload, str) and qr_payload.strip():
        return qr_payload.strip()
    if isinstance(qr_payload, dict):
        candidate = _extract_provider_qr(qr_payload)
        if candidate:
            return candidate
    for key in ("process", "verification", "data", "sunat_response", "resultado", "response"):
        candidate = _extract_provider_qr(value.get(key))
        if candidate:
            return candidate
    return None


def _cdr_details(guide) -> dict:
    details = {"accepted": False, "code": None, "description": None, "notes": []}
    cdr_xml = smartpse_response.extract_cdr_xml(getattr(guide, "provider_response", None))
    if not cdr_xml:
        return details
    try:
        root = ET.fromstring(cdr_xml)
    except ET.ParseError:
        return details
    for node in root.iter():
        local_name = node.tag.rsplit("}", 1)[-1]
        text = (node.text or "").strip()
        if local_name == "ResponseCode" and text and details["code"] is None:
            details["code"] = text
        elif local_name == "Description" and text and details["description"] is None:
            details["description"] = text
        elif local_name == "Note" and text:
            details["notes"].append(text)
    details["accepted"] = details["code"] == "0"
    return details


def _cdr_qr_content(guide, tenant) -> str | None:
    del tenant  # The QR content must come from the accepted response, not local fields.
    if guide.estado != "emitida" or not _cdr_details(guide)["accepted"]:
        return None
    return _extract_provider_qr(getattr(guide, "provider_response", None))


def _qr_image(content: str) -> Image:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q, border=4, box_size=8)
    qr.add_data(content)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    # 36.8 mm: aligned with Inkora's fiscal footer and comfortably scannable.
    return Image(buffer, width=1.45 * inch, height=1.45 * inch)


def _card(title: str, rows: list[list], width: float, styles: dict, palette: dict) -> Table:
    data = [[Paragraph(escape(title), styles["section"]), ""]] + rows
    table = Table(data, colWidths=[width * 0.24, width * 0.76], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (1, 0)),
                ("BACKGROUND", (0, 0), (-1, 0), palette["soft"]),
                ("LINEBELOW", (0, 0), (-1, 0), 1, palette["border"]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, 0), 4.5),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 4.5),
                ("TOPPADDING", (0, 1), (-1, -1), 1.5),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 1.5),
            ]
        )
    )
    rounded = pdf_generator._AutoRoundedContainerBox(
        child=table,
        width=width,
        stroke_color=palette["border"],
        radius=4.5,
        stroke_width=1,
        padding=0,
    )
    rounded.hAlign = "LEFT"
    return rounded


def _label_value(label: str, value, styles: dict) -> list:
    return [Paragraph(f"<b>{escape(label)}:</b>", styles["label"]), Paragraph(_text(value), styles["body"])]


def _build_header(guide, tenant, width: float, styles: dict, palette: dict, fiscal_identity: dict):
    company_data = pdf_generator._resolve_company_data(guide, tenant, None)
    if fiscal_identity.get("issuer_name"):
        company_data["name"] = fiscal_identity["issuer_name"]
    if fiscal_identity.get("issuer_ruc"):
        company_data["ruc"] = fiscal_identity["issuer_ruc"]

    header_height = 4.35 * cm
    header_col_1 = 8.0 * cm
    header_col_2 = 6.0 * cm
    header_col_3 = width - header_col_1 - header_col_2
    logo = pdf_generator._build_logo_block(
        company_data,
        palette["primary"],
        header_col_1,
        styles["logo"],
    )
    logo_box = KeepInFrame(
        header_col_1 - 0.4 * cm,
        header_height - 18,
        [logo],
        mode="shrink",
        hAlign="CENTER",
        vAlign="MIDDLE",
    )

    contact = []
    if company_data.get("phone"):
        contact.append(f"Teléfono: {_text(company_data['phone'])}")
    if company_data.get("email"):
        contact.append(f"Email: {_text(company_data['email'])}")
    company_rows = [
        [Paragraph(_text(company_data.get("name"), "INKORA").upper(), styles["company"])],
        [""],
        [Paragraph(f"RUC {_text(company_data.get('ruc'))}", styles["body"])],
        [""],
        [Paragraph(_text(company_data.get("address"), "Dirección no consignada"), styles["small"])],
    ]
    company_row_heights = [None, 0.4 * cm, None, 0.4 * cm, None]
    if contact:
        company_rows.extend([[""], [Paragraph("<br/>".join(contact), styles["small"])]] )
        company_row_heights.extend([0.4 * cm, None])
    company = Table(company_rows, colWidths=[header_col_2 - 0.4 * cm], rowHeights=company_row_heights)
    company.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    company_box = KeepInFrame(
        header_col_2 - 0.4 * cm,
        header_height - 18,
        [company],
        mode="shrink",
        hAlign="CENTER",
        vAlign="TOP",
    )

    title = (
        "GUÍA DE REMISIÓN<br/>REMITENTE ELECTRÓNICA"
        if guide.tipo_documento == "09"
        else "GUÍA DE REMISIÓN<br/>TRANSPORTISTA ELECTRÓNICA"
    )
    document_box = pdf_generator._RoundedDocumentBox(
        width=4.9 * cm,
        height=3.45 * cm,
        stroke_color=palette["primary"],
        title_paragraph=Paragraph(title, styles["document_title"]),
        number_paragraph=Paragraph(_guide_number(guide), styles["document_number"]),
        footer_paragraph=Paragraph(f"RUC: {_text(company_data.get('ruc'))}", styles["document_footer"]),
        radius=4.5,
        stroke_width=1.5,
        band_fill=palette["primary"],
    )

    header = Table(
        [[logo_box, company_box, document_box]],
        colWidths=[header_col_1, header_col_2, header_col_3],
        rowHeights=[header_height],
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    header = pdf_generator._HeaderDividerBox(
        child=header,
        width=width,
        height=header_height,
        divider_positions=[header_col_1, header_col_1 + header_col_2],
        divider_color=palette["border"],
        divider_height=3.35 * cm,
        stroke_width=1,
    )
    container = pdf_generator._RoundedContainerBox(
        child=header,
        width=width,
        height=header_height,
        stroke_color=palette["border"],
        radius=4.5,
        stroke_width=1,
        padding=0,
    )
    container.hAlign = "LEFT"
    return container


def _build_items(items, start_index: int, width: float, styles: dict, palette: dict):
    rows = [[
        Paragraph("N°", styles["table_header"]),
        Paragraph("CANTIDAD", styles["table_header"]),
        Paragraph("UNIDAD", styles["table_header"]),
        Paragraph("CÓDIGO", styles["table_header"]),
        Paragraph("DESCRIPCIÓN", styles["table_header"]),
    ]]
    for index, item in enumerate(items, start=start_index):
        rows.append(
            [
                Paragraph(str(index), styles["center"]),
                Paragraph(_format_quantity(item.cantidad), styles["center"]),
                Paragraph(_text(item.unidad_medida, "UND"), styles["center"]),
                Paragraph(_text(getattr(item, "codigo_producto", None)), styles["center"]),
                Paragraph(_text(item.descripcion), styles["body"]),
            ]
        )
    table = Table(rows, colWidths=[width * 0.055, width * 0.12, width * 0.11, width * 0.15, width * 0.565], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), palette["primary"]),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("INNERGRID", (0, 0), (-1, -1), 0.8, palette["border"]),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, palette["border"]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
            ]
        )
    )
    rounded = pdf_generator._AutoRoundedContainerBox(
        child=table,
        width=width,
        stroke_color=palette["border"],
        radius=4.5,
        stroke_width=1,
        padding=0,
    )
    rounded.hAlign = "LEFT"
    return rounded


def _build_continuation_header(
    guide,
    tenant,
    width: float,
    styles: dict,
    palette: dict,
    fiscal_identity: dict,
):
    """Identify every continuation page without repeating the full first-page header."""
    company_data = pdf_generator._resolve_company_data(guide, tenant, None)
    if fiscal_identity.get("issuer_name"):
        company_data["name"] = fiscal_identity["issuer_name"]
    if fiscal_identity.get("issuer_ruc"):
        company_data["ruc"] = fiscal_identity["issuer_ruc"]
    document_type = "GRE REMITENTE" if guide.tipo_documento == "09" else "GRE TRANSPORTISTA"
    table = Table(
        [[
            Paragraph(
                f"<b>{_text(company_data.get('name'), 'INKORA').upper()}</b><br/>"
                f"RUC {_text(company_data.get('ruc'))}",
                styles["body"],
            ),
            Paragraph(
                f"<b>{document_type} ELECTRÓNICA</b><br/>"
                f"<font size='13'><b>{_text(_guide_number(guide))}</b></font>",
                styles["continuation_number"],
            ),
        ]],
        colWidths=[width * 0.58, width * 0.42],
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LINEBEFORE", (1, 0), (1, 0), 1, palette["border"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    container = pdf_generator._AutoRoundedContainerBox(
        child=table,
        width=width,
        stroke_color=palette["border"],
        radius=4.5,
        stroke_width=1,
        padding=0,
    )
    container.hAlign = "LEFT"
    return container


def _paginate_item_rows(
    items,
    *,
    single_page_capacity: int,
    first_page_capacity: int = 8,
    continuation_capacity: int = 10,
) -> list[list]:
    """Fill page one, then balance continuation rows without exceeding the cap."""
    rows = list(items or [])
    total = len(rows)
    if total <= single_page_capacity:
        return [rows]

    first_size = min(first_page_capacity, total)
    pages = [rows[:first_size]]
    cursor = first_size
    remaining = total - first_size
    continuation_pages = (
        remaining + continuation_capacity - 1
    ) // continuation_capacity
    for pages_left in range(continuation_pages, 0, -1):
        page_size = (remaining + pages_left - 1) // pages_left
        pages.append(rows[cursor : cursor + page_size])
        cursor += page_size
        remaining -= page_size
    return pages


def _build_footer(guide, tenant, width: float, styles: dict, palette: dict):
    status_label, _ = _STATUS_META.get(
        str(guide.estado or "").lower(), (str(guide.estado or "SIN ESTADO").upper(), None)
    )
    cdr_details = _cdr_details(guide)
    qr_content = _cdr_qr_content(guide, tenant)
    if qr_content:
        right = [
            Paragraph(f"Representación impresa de la GRE {escape(guide.tipo_documento or '09')}.", styles["footer_title"]),
            Paragraph("Documento electrónico aceptado por SUNAT.", styles["body"]),
            Paragraph(
                f"Verificación: RUC {_text(getattr(tenant, 'business_ruc', None))} · "
                f"GRE {_text(_guide_number(guide))}",
                styles["body"],
            ),
            Paragraph("Consulta disponible en SUNAT Virtual", styles["link"]),
            Paragraph(f"Hash: {_text(getattr(guide, 'sunat_hash', None))}", styles["small"]),
        ]
        if cdr_details["notes"]:
            right.append(Paragraph(f"Observación CDR: {_text(' · '.join(cdr_details['notes']))}", styles["small"]))
        right_box = KeepInFrame(width * 0.70, 1.45 * inch, right, mode="shrink", vAlign="MIDDLE")
        footer = Table([[_qr_image(qr_content), right_box]], colWidths=[width * 0.25, width * 0.75])
        divider_positions = [width * 0.25]
    else:
        if str(guide.estado or "").lower() == "emitida" and cdr_details["accepted"]:
            message = (
                "Documento electrónico aceptado por SUNAT. El proveedor no entregó un contenido QR "
                f"verificable; sustento alternativo: RUC {_text(getattr(tenant, 'business_ruc', None))}, "
                f"serie y número {_text(_guide_number(guide))}."
            )
        else:
            message = {
                "pendiente": "Borrador operativo. No acredita emisión ni aceptación fiscal.",
                "pendiente_smartpse": "Documento enviado o conciliándose. No acredita aceptación hasta disponer del CDR.",
                "rechazada": "Documento rechazado. No utilizar como constancia fiscal del traslado.",
                "cancelada": "Borrador cancelado. Las cantidades reservadas fueron liberadas.",
                "cancelado": "Borrador cancelado. Las cantidades reservadas fueron liberadas.",
                "cancelled": "Borrador cancelado. Las cantidades reservadas fueron liberadas.",
            }.get(str(guide.estado or "").lower(), "Representación sin evidencia CDR disponible.")
        footer = Table(
            [[Paragraph(status_label, styles["status"]), Paragraph(message, styles["body"])]],
            colWidths=[width * 0.30, width * 0.70],
        )
        divider_positions = [width * 0.30]
    footer.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, -1), 1.5, palette["primary"]),
                ("LINEBELOW", (0, 0), (-1, -1), 1.5, palette["primary"]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    footer = pdf_generator._AutoVerticalDividerBox(
        child=footer,
        width=width,
        divider_positions=divider_positions,
        divider_color=palette["border"],
        inset_y=0.3 * cm,
        stroke_width=1,
    )

    contact = pdf_generator._build_footer_contact_text(
        pdf_generator._resolve_company_data(guide, tenant, None)
    )
    contact_row = Table(
        [[
            Paragraph("XML, CDR y representación impresa disponibles en Inkora.", styles["small"]),
            Paragraph(_text(contact, ""), styles["small_right"]),
        ]],
        colWidths=[width * 0.62, width * 0.38],
    )
    contact_row.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]
        )
    )
    block = Table([[footer], [contact_row]], colWidths=[width], splitByRow=0)
    block.setStyle(
        TableStyle(
            [
                ("NOSPLIT", (0, 0), (-1, -1)),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return block


def build_guide_pdf(guide, tenant) -> bytes:
    output = BytesIO()
    margin_lr = 0.7 * cm
    margin_tb = 0.42 * cm
    width = A4[0] - (margin_lr * 2)
    try:
        primary = colors.HexColor(getattr(tenant, "primary_color", None) or "#2563EB")
    except Exception:
        primary = colors.HexColor("#2563EB")
    palette = {
        "primary": primary,
        "border": colors.HexColor("#C9D4E5"),
        "text": colors.HexColor("#1F2937"),
        "soft": colors.HexColor("#F8FAFF"),
    }

    base = getSampleStyleSheet()["Normal"]
    styles = {
        "body": ParagraphStyle("GuideBody", parent=base, fontName="Helvetica", fontSize=8.7, leading=10.2, textColor=palette["text"]),
        "small": ParagraphStyle("GuideSmall", parent=base, fontName="Helvetica", fontSize=8.0, leading=9.4, textColor=palette["text"]),
        "small_right": ParagraphStyle("GuideSmallRight", parent=base, fontName="Helvetica", fontSize=8.0, leading=9.4, alignment=TA_RIGHT, textColor=palette["text"]),
        "label": ParagraphStyle("GuideLabel", parent=base, fontName="Helvetica-Bold", fontSize=8.4, leading=10.0, textColor=palette["text"]),
        "center": ParagraphStyle("GuideCenter", parent=base, fontName="Helvetica", fontSize=8.2, leading=10, alignment=TA_CENTER, textColor=palette["text"]),
        "section": ParagraphStyle("GuideSection", parent=base, fontName="Helvetica-Bold", fontSize=10.7, leading=12.8, textColor=primary),
        "company": ParagraphStyle("GuideCompany", parent=base, fontName="Helvetica-Bold", fontSize=11.4, leading=13.2, textColor=palette["text"]),
        "logo": ParagraphStyle("GuideLogo", parent=base, fontName="Helvetica-Bold", fontSize=15, leading=18, alignment=TA_CENTER, textColor=primary),
        "document_title": ParagraphStyle("GuideDocumentTitle", parent=base, fontName="Helvetica-Bold", fontSize=11.2, leading=13.2, alignment=TA_CENTER, textColor=primary),
        "document_number": ParagraphStyle("GuideDocumentNumber", parent=base, fontName="Helvetica-Bold", fontSize=15.5, leading=18, alignment=TA_CENTER, textColor=colors.white),
        "document_footer": ParagraphStyle("GuideDocumentFooter", parent=base, fontName="Helvetica-Bold", fontSize=9.0, leading=10.8, alignment=TA_CENTER, textColor=palette["text"]),
        "table_header": ParagraphStyle("GuideTableHeader", parent=base, fontName="Helvetica-Bold", fontSize=7.45, leading=8.91, alignment=TA_CENTER, textColor=colors.white),
        "footer_title": ParagraphStyle("GuideFooterTitle", parent=base, fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=primary),
        "link": ParagraphStyle("GuideLink", parent=base, fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=primary),
        "status": ParagraphStyle("GuideStatus", parent=base, fontName="Helvetica-Bold", fontSize=9.0, leading=11, alignment=TA_CENTER, textColor=primary),
        "continuation_number": ParagraphStyle("GuideContinuationNumber", parent=base, fontName="Helvetica", fontSize=8.5, leading=14, alignment=TA_RIGHT, textColor=primary),
    }

    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=margin_lr,
        rightMargin=margin_lr,
        topMargin=margin_tb,
        bottomMargin=0.58 * cm,
        title=f"GRE {_guide_number(guide)}",
    )
    status_label, watermark = _STATUS_META.get(
        str(guide.estado or "").lower(), (str(guide.estado or "SIN ESTADO").upper(), None)
    )

    def draw_page(canvas, doc):
        canvas.saveState()
        if watermark:
            canvas.setFillColor(colors.Color(0.45, 0.45, 0.45, alpha=0.12))
            canvas.setFont("Helvetica-Bold", 34)
            canvas.translate(A4[0] / 2, A4[1] / 2)
            canvas.rotate(32)
            canvas.drawCentredString(0, 0, watermark)
            canvas.rotate(-32)
            canvas.translate(-A4[0] / 2, -A4[1] / 2)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(A4[0] - margin_lr, 0.42 * cm, f"Página {doc.page}")
        canvas.restoreState()

    fiscal_identity = _fiscal_identity(guide)
    recipient_name, recipient_document, recipient_address = _recipient(guide)
    gre_reference = _gre_reference(guide)
    modality = "Transporte público" if guide.modalidad_traslado == "01" else "Transporte privado"
    motive = "Venta" if guide.motivo_traslado == "01" else (guide.descripcion_motivo or guide.motivo_traslado or "-")
    issue_date = fiscal_identity.get("issue_date") or guide.fecha_emision
    issue_time = fiscal_identity.get("issue_time") or guide.fecha_emision

    summary = Table(
        [[
            Paragraph("<b>Fecha de emisión:</b>", styles["label"]),
            Paragraph(f"<nobr>{_format_date(issue_date)}</nobr>", styles["body"]),
            Paragraph("<b>Hora:</b>", styles["label"]),
            Paragraph(f"<nobr>{_format_time(issue_time)}</nobr>", styles["body"]),
            Paragraph("<b>Fecha de traslado:</b>", styles["label"]),
            Paragraph(f"<nobr>{_format_date(guide.fecha_traslado)}</nobr>", styles["body"]),
            Paragraph("<b>Estado:</b>", styles["label"]),
            Paragraph(escape(status_label), styles["status"]),
        ]],
        colWidths=[
            width * 0.13,
            width * 0.105,
            width * 0.065,
            width * 0.075,
            width * 0.14,
            width * 0.105,
            width * 0.075,
            width * 0.305,
        ],
    )
    summary.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, -1), 1.6, colors.HexColor("#1747C8")),
                ("LINEBELOW", (0, 0), (-1, -1), 1.6, colors.HexColor("#1747C8")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    recipient_rows = [
        _label_value("Razón social", recipient_name, styles),
        _label_value("Documento", recipient_document, styles),
        _label_value("Dirección", recipient_address, styles),
        _label_value(_source_document_label(guide), _invoice_reference(guide), styles),
    ]
    if gre_reference:
        recipient_rows.append(_label_value("GRE remitente relacionada", gre_reference, styles))

    transfer_rows = [
        _label_value("Motivo", motive, styles),
        _label_value("Modalidad", modality, styles),
        _label_value("Peso bruto", f"{_format_quantity(guide.peso_bruto_total)} {_text(guide.unidad_medida_peso, 'KGM')}", styles),
        _label_value("Número de bultos", getattr(guide, "numero_bultos", None), styles),
        _label_value("Escenario", _transport_scenario(guide), styles),
    ]
    if guide.modalidad_traslado == "01" and getattr(guide, "fecha_entrega_transportista", None):
        transfer_rows.append(_label_value("Entrega al transportista", _format_date(guide.fecha_entrega_transportista), styles))
    if getattr(guide, "observaciones", None):
        transfer_rows.append(_label_value("Observaciones", guide.observaciones, styles))
    route_rows = [
        _label_value("Punto de partida", f"{guide.partida_ubigeo or ''} {guide.partida_direccion or ''}".strip(), styles),
        _label_value("Punto de llegada", f"{guide.llegada_ubigeo or ''} {guide.llegada_direccion or ''}".strip(), styles),
    ]
    if getattr(guide, "num_contenedor", None):
        route_rows.append(_label_value("Contenedor", guide.num_contenedor, styles))
    if getattr(guide, "cod_puerto", None):
        route_rows.append(_label_value("Puerto", guide.cod_puerto, styles))

    transport_rows = []
    if (guide.modalidad_traslado == "01" and not getattr(guide, "indicador_m1_l", False)) or guide.tipo_documento == "31":
        transport_rows.extend(
            [
                _label_value("Transportista", getattr(guide, "transportista_razon_social", None) or getattr(tenant, "business_name", None), styles),
                _label_value("RUC transportista", getattr(guide, "transportista_ruc", None) or (getattr(tenant, "business_ruc", None) if guide.tipo_documento == "31" else None), styles),
                _label_value("Registro MTC", getattr(guide, "transportista_nro_mtc", None), styles),
            ]
        )
    if getattr(guide, "vehiculo_placa", None):
        transport_rows.append(_label_value("Vehículo", guide.vehiculo_placa, styles))
    if getattr(guide, "vehiculo_nro_circulacion", None):
        transport_rows.append(_label_value("Nro. circulación", guide.vehiculo_nro_circulacion, styles))
    if getattr(guide, "conductor_nro_doc", None):
        transport_rows.extend(
            [
                _label_value("Conductor", " ".join(filter(None, [getattr(guide, "conductor_nombres", None), getattr(guide, "conductor_apellidos", None)])), styles),
                _label_value("Documento conductor", f"Tipo {getattr(guide, 'conductor_tipo_doc', None) or '1'} - {guide.conductor_nro_doc}", styles),
                _label_value("Licencia", getattr(guide, "conductor_licencia", None), styles),
            ]
        )
    if getattr(guide, "transportista_acuerdo_confirmado_at", None):
        transport_rows.append(_label_value("Acuerdo con transportista", "Confirmado y auditado", styles))

    elements = [
        _build_header(guide, tenant, width, styles, palette, fiscal_identity),
        Spacer(1, 7),
        summary,
        Spacer(1, 4),
        _card("DATOS DEL DESTINATARIO Y DOCUMENTOS RELACIONADOS", recipient_rows, width, styles, palette),
        Spacer(1, 3),
        _card("DATOS DEL TRASLADO", transfer_rows, width, styles, palette),
        Spacer(1, 3),
        _card("RUTA DEL TRASLADO", route_rows, width, styles, palette),
    ]
    if transport_rows:
        transport_title = (
            "VEHÍCULO DEL TRASLADO"
            if getattr(guide, "indicador_m1_l", False)
            else "TRANSPORTE, VEHÍCULO Y CONDUCTOR"
        )
        elements.extend([Spacer(1, 3), _card(transport_title, transport_rows, width, styles, palette)])
    all_items = list(getattr(guide, "items", None) or [])
    # Measurements against the rendered A4 layout establish these capacities:
    # five rows fit with the accepted-document QR on the complete first page;
    # without a QR, the complete first-page metadata fits with eight.
    # Continuation pages carry at most ten rows and are balanced only after the
    # first page has consumed its full reserved capacity.
    qr_content = _cdr_qr_content(guide, tenant)
    first_page_capacity = 5 if qr_content else 8
    item_pages = _paginate_item_rows(
        all_items,
        single_page_capacity=first_page_capacity,
        first_page_capacity=first_page_capacity,
    )
    first_page_items = item_pages[0]
    elements.extend(
        [
            Spacer(1, 4),
            Paragraph("BIENES A TRASLADAR", styles["section"]),
            Spacer(1, 3),
            _build_items(first_page_items, 1, width, styles, palette),
        ]
    )
    if len(item_pages) > 1:
        elements.extend(
            [Spacer(1, 3), Paragraph("Continúa en la página siguiente.", styles["small_right"])]
        )
    # The fiscal QR belongs to the first-page representation, even when the
    # goods table continues. Never defer this evidence to the last page.
    elements.extend([Spacer(1, 4), _build_footer(guide, tenant, width, styles, palette)])

    next_index = len(first_page_items) + 1
    continuation_items = item_pages[1:]
    for page_number, page_items in enumerate(continuation_items, start=1):
        elements.extend(
            [
                PageBreak(),
                _build_continuation_header(
                    guide,
                    tenant,
                    width,
                    styles,
                    palette,
                    fiscal_identity,
                ),
                Spacer(1, 10),
                Paragraph("BIENES A TRASLADAR — CONTINUACIÓN", styles["section"]),
                Spacer(1, 4),
            ]
        )
        elements.append(_build_items(page_items, next_index, width, styles, palette))
        next_index += len(page_items)
        if page_number < len(continuation_items):
            elements.extend(
                [Spacer(1, 3), Paragraph("Continúa en la página siguiente.", styles["small_right"])]
            )

    document.build(elements, onFirstPage=draw_page, onLaterPages=draw_page)
    return output.getvalue()
