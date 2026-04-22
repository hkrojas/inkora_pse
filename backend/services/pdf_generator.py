import io
import os
import traceback
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP, getcontext

import models
import qrcode
import requests
from dateutil.relativedelta import relativedelta
from num2words import num2words
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Flowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from services import fiscal_xml_service
from services.calculations import TOTAL_PRECISION, calculate_cotizacion_totals_v3, to_decimal
from services.quote_observation_service import build_default_observation_lines, parse_quote_observations
from tenant_access import get_company_bank_accounts

getcontext().prec = 50


def monto_a_letras(amount, currency_symbol):
    """Convierte un monto numerico a su representacion en palabras."""
    currency_name = "SOLES" if currency_symbol == "S/" else "DOLARES AMERICANOS"
    try:
        amount_decimal = to_decimal(amount).quantize(TOTAL_PRECISION, rounding=ROUND_HALF_UP)
        integer_part_decimal = amount_decimal.to_integral_value(rounding="ROUND_DOWN")
        if integer_part_decimal < 0:
            integer_part_decimal = Decimal("0")
        integer_part = int(integer_part_decimal)

        decimal_part_num = abs(amount_decimal) % 1
        decimal_part_str = f"{decimal_part_num:.2f}"
        if "." in decimal_part_str:
            decimal_part = decimal_part_str.split(".")[-1].ljust(2, "0")[:2]
        else:
            decimal_part = "00"
    except (ValueError, TypeError, Exception) as err:
        print(f"Error en monto_a_letras: {err}, amount: {amount}")
        return "MONTO INVALIDO"

    text_integer = num2words(integer_part, lang="es").upper()
    return f"SON: {text_integer} CON {decimal_part}/100 {currency_name}"


def obtener_etiqueta_tipo_doc(codigo):
    """Mapea el codigo de SUNAT al nombre legible."""
    mapeo = {
        "6": "RUC",
        "1": "DNI",
        "4": "C.E.",
        "7": "PASAPORTE",
        "0": "DOC.TRIB.NO.DOM.",
    }
    return mapeo.get(str(codigo), "DOC")


def _resolver_titulo_documento(tipo_doc_sunat: str | None, is_comprobante: bool) -> str:
    if not is_comprobante:
        return "COTIZACION"

    tipo_doc_sunat = str(tipo_doc_sunat or "03")
    if tipo_doc_sunat == "01":
        return "FACTURA ELECTRONICA"
    if tipo_doc_sunat == "07":
        return "NOTA DE CREDITO"
    if tipo_doc_sunat == "08":
        return "NOTA DE DEBITO"
    return "BOLETA DE VENTA ELECTRONICA"


def _value_from_obj(source, key, default=None):
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def _parse_datetime_like(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except Exception:
            return None
    return None


def _format_date_ddmmyyyy(value, default: str = "") -> str:
    parsed = _parse_datetime_like(value)
    if parsed:
        return parsed.strftime("%d/%m/%Y")
    return default


def _format_quantity(value: Decimal) -> str:
    value = to_decimal(value)
    if value % 1 == 0:
        return str(int(value))
    return f"{value:f}".rstrip("0").rstrip(".")


def _normalize_payment_method_entry(entry):
    if not isinstance(entry, dict):
        return None

    entry_type = str(entry.get("tipo") or "").strip().lower()
    is_wallet = entry_type == "wallet" or bool(entry.get("proveedor"))

    if is_wallet:
        provider = str(entry.get("proveedor") or "").strip()
        holder = str(entry.get("titular") or "").strip()
        number = str(entry.get("numero") or entry.get("cuenta") or "").strip()
        note = str(entry.get("nota") or "").strip()
        if not any([provider, holder, number, note]):
            return None
        return {
            "tipo": "wallet",
            "proveedor": provider,
            "titular": holder,
            "numero": number,
            "nota": note,
        }

    bank_name = str(entry.get("banco") or "").strip()
    account_type = str(entry.get("tipo_cuenta") or "Cta Ahorro").strip() or "Cta Ahorro"
    currency = str(entry.get("moneda") or "Soles").strip() or "Soles"
    account_number = str(entry.get("cuenta") or "").strip()
    cci = str(entry.get("cci") or "").strip()
    if not any([bank_name, account_number, cci]):
        return None
    return {
        "tipo": "bank",
        "banco": bank_name,
        "tipo_cuenta": account_type,
        "moneda": currency,
        "cuenta": account_number,
        "cci": cci,
    }


def _normalize_payment_methods(payment_methods) -> list[dict]:
    if not isinstance(payment_methods, list):
        return []

    normalized = []
    for entry in payment_methods:
        payment_method = _normalize_payment_method_entry(entry)
        if payment_method:
            normalized.append(payment_method)
    return normalized


def _build_payment_methods_text(payment_methods, beneficiary_name: str = "") -> str:
    normalized_methods = _normalize_payment_methods(payment_methods)
    if not normalized_methods:
        return ""

    payment_text = "<b>Datos para la Transferencia</b><br/>"
    if beneficiary_name:
        payment_text += f"Beneficiario: {str(beneficiary_name).upper()}<br/><br/>"

    for method in normalized_methods:
        if method["tipo"] == "wallet":
            provider = method["proveedor"] or "Billetera digital"
            payment_text += f"<b>{provider}</b><br/>"
            if method["titular"]:
                payment_text += f"Titular: {method['titular']}<br/>"
            if method["numero"]:
                payment_text += f"Numero: {method['numero']}<br/>"
            if method["nota"]:
                payment_text += f"{method['nota']}<br/>"
            payment_text += "<br/>"
            continue

        bank_name = method["banco"] or "Cuenta bancaria"
        payment_text += f"<b>{bank_name}</b><br/>"
        account_label = (
            f"Cuenta Detraccion en {method['moneda']}"
            if "nacion" in bank_name.lower()
            else f"{method['tipo_cuenta']} en {method['moneda']}"
        )
        if method["cuenta"] and method["cci"]:
            payment_text += f"{account_label}: {method['cuenta']} CCI: {method['cci']}<br/>"
        elif method["cuenta"]:
            payment_text += f"{account_label}: {method['cuenta']}<br/>"
        elif method["cci"]:
            payment_text += f"CCI: {method['cci']}<br/>"
        else:
            payment_text += f"{account_label}<br/>"
        payment_text += "<br/>"

    return payment_text


def _build_qr_content(document_data, fallback_content: str) -> str:
    qr_payload = getattr(document_data, "sunat_qr_payload", None)
    if isinstance(qr_payload, dict):
        return "|".join(
            [
                str(qr_payload.get("ruc") or ""),
                str(qr_payload.get("tipo") or ""),
                str(qr_payload.get("serie") or ""),
                str(qr_payload.get("numero") or ""),
                str(qr_payload.get("igv") or ""),
                str(qr_payload.get("total") or ""),
                str(qr_payload.get("emision") or ""),
                str(qr_payload.get("clienteTipo") or ""),
                str(qr_payload.get("clienteNumero") or ""),
            ]
        )
    return fallback_content


def _build_qr_flowable(document_data, qr_content: str, ancho_total: float):
    official_qr_svg = getattr(document_data, "sunat_qr_svg", None)
    if official_qr_svg:
        try:
            from io import BytesIO as _BytesIO

            from svglib.svglib import svg2rlg

            drawing = svg2rlg(_BytesIO(official_qr_svg.encode("utf-8")))
            if drawing is not None and getattr(drawing, "width", 0) and getattr(drawing, "height", 0):
                target_size = 1.6 * inch
                scale_x = target_size / drawing.width
                scale_y = target_size / drawing.height
                drawing.scale(scale_x, scale_y)
                drawing.width = target_size
                drawing.height = target_size

                qr_table = Table([[drawing]], colWidths=[ancho_total])
                qr_table.setStyle(
                    TableStyle(
                        [
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ]
                    )
                )
                return qr_table
        except Exception as qr_err:
            print(f"Error cargando QR oficial SVG en PDF: {qr_err}")

    qr_img = qrcode.make(qr_content)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    qr_image_obj = Image(qr_buffer, width=1.6 * inch, height=1.6 * inch)

    qr_table = Table([[qr_image_obj]], colWidths=[ancho_total])
    qr_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return qr_table


def _load_logo(tenant):
    if not getattr(tenant, "logo_filename", None):
        return ""

    try:
        if tenant.logo_filename.startswith("http"):
            response = requests.get(tenant.logo_filename, timeout=5)
            if response.status_code == 200:
                return Image(io.BytesIO(response.content), width=151, height=76)
        elif os.path.exists(f"logos/{tenant.logo_filename}"):
            return Image(f"logos/{tenant.logo_filename}", width=151, height=76)
    except Exception as err:
        print(f"Error cargando logo en PDF: {err}")

    return ""


class _RoundedHeaderBox(Flowable):
    def __init__(
        self,
        paragraphs,
        width,
        stroke_color,
        padding_x=10,
        padding_y=8,
        gap=5,
        radius=7,
        stroke_width=1.5,
    ):
        super().__init__()
        self.paragraphs = paragraphs
        self.width = width
        self.stroke_color = stroke_color
        self.padding_x = padding_x
        self.padding_y = padding_y
        self.gap = gap
        self.radius = radius
        self.stroke_width = stroke_width
        self._line_heights = []
        self._inner_width = max(width - (padding_x * 2), 20)
        self.height = 0

    def wrap(self, availWidth, availHeight):
        total_height = self.padding_y * 2
        self._line_heights = []
        for idx, paragraph in enumerate(self.paragraphs):
            _, line_height = paragraph.wrap(self._inner_width, availHeight)
            self._line_heights.append(line_height)
            total_height += line_height
            if idx < len(self.paragraphs) - 1:
                total_height += self.gap
        self.height = total_height
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        canvas.setStrokeColor(self.stroke_color)
        canvas.setLineWidth(self.stroke_width)
        canvas.roundRect(0, 0, self.width, self.height, self.radius, stroke=1, fill=0)

        cursor_y = self.height - self.padding_y
        for idx, paragraph in enumerate(self.paragraphs):
            line_height = self._line_heights[idx]
            cursor_y -= line_height
            paragraph.drawOn(canvas, self.padding_x, cursor_y)
            if idx < len(self.paragraphs) - 1:
                cursor_y -= self.gap
        canvas.restoreState()


def _build_local_line_context(document_data):
    productos_fuente_dict = []
    items = getattr(document_data, "items", [])
    for item in items:
        if isinstance(item, dict):
            descripcion = item.get("descripcion", "")
            cantidad = item.get("unidades", 0) or item.get("cantidad", 0)
            precio_unitario = item.get("precio_unitario", 0)
        else:
            descripcion = getattr(item, "descripcion", "")
            cantidad = getattr(item, "cantidad", 0)
            precio_unitario = getattr(item, "precio_unitario", 0)

        productos_fuente_dict.append(
            {
                "unidades": cantidad,
                "precio_unitario": precio_unitario,
                "descripcion": descripcion,
            }
        )

    totals_v3 = calculate_cotizacion_totals_v3(productos_fuente_dict)
    productos_para_tabla_data = []
    for idx, item_dict in enumerate(productos_fuente_dict):
        line_totals = totals_v3["line_totals"][idx]
        productos_para_tabla_data.append(
            {
                "descripcion": str(item_dict["descripcion"]).replace("\n", "<br/>"),
                "cantidad": to_decimal(item_dict["unidades"]),
                "p_unit_con_igv": line_totals["mto_precio_unitario_con_igv"],
                "igv_item": line_totals["igv_linea"],
                "precio_total_item": line_totals["precio_total_linea"],
            }
        )

    return {
        "lines": productos_para_tabla_data,
        "total_gravado": totals_v3["total_gravado_v3"],
        "total_igv": totals_v3["total_igv_v3"],
        "monto_total": totals_v3["monto_total_v3"],
    }


def _build_xml_line_context(parsed_xml: dict):
    totals_xml = parsed_xml.get("totals") or {}
    productos_para_tabla_data = []

    for line in parsed_xml.get("lines") or []:
        precio_total_item = to_decimal(line.get("line_extension_amount") or 0) + to_decimal(line.get("tax_amount") or 0)
        productos_para_tabla_data.append(
            {
                "descripcion": str(line.get("description") or "").replace("\n", "<br/>"),
                "cantidad": to_decimal(line.get("quantity") or 0),
                "p_unit_con_igv": to_decimal(line.get("price_amount") or 0),
                "igv_item": to_decimal(line.get("tax_amount") or 0),
                "precio_total_item": precio_total_item,
            }
        )

    return {
        "lines": productos_para_tabla_data,
        "total_gravado": to_decimal(totals_xml.get("line_extension_amount") or 0),
        "total_igv": to_decimal(totals_xml.get("tax_amount") or 0),
        "monto_total": to_decimal(
            totals_xml.get("payable_amount")
            or totals_xml.get("tax_inclusive_amount")
            or 0
        ),
    }


def _build_quote_document_number(document_data) -> str:
    correlativo = _value_from_obj(document_data, "correlativo", None)
    if correlativo in (None, "", 0):
        correlativo = _value_from_obj(document_data, "id", 0)
    return f"N° {str(correlativo or 0).zfill(4)}"


def _resolve_quote_company_data(document_data, tenant: models.Tenant) -> dict:
    user = getattr(document_data, "usuario", None)

    company_name = (
        getattr(tenant, "business_name", None)
        or getattr(user, "business_name", None)
        or "Nombre del Negocio"
    )
    company_ruc = (
        getattr(tenant, "business_ruc", None)
        or getattr(user, "business_ruc", None)
        or ""
    )
    company_address = (
        getattr(tenant, "business_address", None)
        or getattr(user, "business_address", None)
        or "Direccion no especificada"
    )
    company_phone = (
        getattr(tenant, "business_phone", None)
        or getattr(user, "business_phone", None)
        or ""
    )
    company_email = (
        getattr(tenant, "business_email", None)
        or getattr(user, "business_email", None)
        or getattr(user, "email", None)
        or ""
    )

    bank_accounts = []
    if user is not None:
        bank_accounts = get_company_bank_accounts(user)
    if not bank_accounts:
        bank_accounts = getattr(tenant, "bank_accounts", None) or []

    logo_source = tenant if getattr(tenant, "logo_filename", None) else user

    return {
        "name": str(company_name or "").strip(),
        "ruc": str(company_ruc or "").strip(),
        "address": str(company_address or "").strip(),
        "phone": str(company_phone or "").strip(),
        "email": str(company_email or "").strip(),
        "bank_accounts": bank_accounts,
        "logo_source": logo_source,
    }


def _build_quote_pdf_buffer(document_data, tenant: models.Tenant):
    buffer = io.BytesIO()

    margen_izq = 24
    margen_der = 24
    ancho_total = letter[0] - margen_izq - margen_der

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=margen_izq,
        rightMargin=margen_der,
        topMargin=24,
        bottomMargin=24,
    )

    styles = getSampleStyleSheet()
    body = styles["Normal"]
    body.fontName = "Helvetica"
    body.fontSize = 10.5
    body.leading = 12

    body_center = ParagraphStyle(name="QuoteBodyCenter", parent=body, alignment=TA_CENTER)
    body_right = ParagraphStyle(name="QuoteBodyRight", parent=body, alignment=TA_RIGHT)
    body_bold = ParagraphStyle(name="QuoteBodyBold", parent=body, fontName="Helvetica-Bold")
    body_bold_center = ParagraphStyle(name="QuoteBodyBoldCenter", parent=body_bold, alignment=TA_CENTER)
    body_bold_right = ParagraphStyle(name="QuoteBodyBoldRight", parent=body_bold, alignment=TA_RIGHT)
    header_name_style = ParagraphStyle(
        name="QuoteHeaderName",
        parent=body_bold_center,
        fontSize=14,
        leading=16,
    )
    header_meta_style = ParagraphStyle(
        name="QuoteHeaderMeta",
        parent=body_center,
        fontSize=10.5,
        leading=12,
    )
    header_box_ruc_style = ParagraphStyle(
        name="QuoteHeaderBoxRuc",
        parent=body_center,
        fontSize=10.5,
        leading=12,
    )
    header_box_title_style = ParagraphStyle(
        name="QuoteHeaderBoxTitle",
        parent=body_bold_center,
        fontSize=13,
        leading=15,
    )
    header_box_number_style = ParagraphStyle(
        name="QuoteHeaderBoxNumber",
        parent=body_bold_center,
        fontSize=12,
        leading=14,
    )
    centered_header = ParagraphStyle(
        name="QuoteCenteredHeader",
        parent=body_bold_center,
        textColor=colors.white,
    )

    moneda_codigo = _value_from_obj(document_data, "moneda", "PEN")
    simbolo = "S/" if moneda_codigo == "PEN" else "$"
    moneda_texto = "SOLES" if moneda_codigo == "PEN" else "DOLARES"

    raw_fecha = (
        _value_from_obj(document_data, "fecha_emision", None)
        or _value_from_obj(document_data, "created_at", datetime.now())
    )
    fecha_emision = _format_date_ddmmyyyy(raw_fecha, default=datetime.now().strftime("%d/%m/%Y"))

    raw_venc = _value_from_obj(document_data, "fecha_vencimiento", None)
    if raw_venc:
        parsed_venc = _parse_datetime_like(raw_venc)
        fecha_vencimiento = parsed_venc.strftime("%d/%m/%Y") if parsed_venc else fecha_emision
    else:
        base_fecha = _parse_datetime_like(raw_fecha) or datetime.now()
        fecha_vencimiento = (base_fecha + relativedelta(months=1)).strftime("%d/%m/%Y")

    cliente = getattr(document_data, "cliente", None)
    if cliente:
        nombre_cliente = getattr(cliente, "razon_social", "") or "Cliente General"
        tipo_doc_cliente = obtener_etiqueta_tipo_doc(getattr(cliente, "tipo_documento", "1"))
        nro_doc_cliente = str(getattr(cliente, "numero_documento", "") or "")
        direccion_cliente = str(getattr(cliente, "direccion", "") or "-").replace("\n", "<br/>")
    else:
        nombre_cliente = "Cliente General"
        tipo_doc_cliente = "DOC"
        nro_doc_cliente = ""
        direccion_cliente = "-"

    line_context = _build_local_line_context(document_data)
    total_gravado_d = to_decimal(line_context["total_gravado"])
    total_igv_d = to_decimal(line_context["total_igv"])
    monto_total_d = to_decimal(line_context["monto_total"])
    monto_en_letras_str = monto_a_letras(monto_total_d, simbolo)

    company_data = _resolve_quote_company_data(document_data, tenant)
    color_principal = colors.HexColor(getattr(tenant, "primary_color", None) or "#004aad")
    logo = _load_logo(company_data["logo_source"])

    company_rows = [
        [Paragraph(company_data["name"].upper() or "NOMBRE DEL NEGOCIO", header_name_style)],
        [Paragraph(company_data["address"].replace("\n", "<br/>"), header_meta_style)],
    ]
    if company_data["email"]:
        company_rows.append([Paragraph(company_data["email"], header_meta_style)])
    if company_data["phone"]:
        company_rows.append([Paragraph(company_data["phone"], header_meta_style)])

    company_col_width = ancho_total - 160 - 145
    company_table = Table(company_rows, colWidths=[company_col_width])
    company_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )

    document_header_box = _RoundedHeaderBox(
        [
            Paragraph(f"RUC {company_data['ruc']}", header_box_ruc_style),
            Paragraph("COTIZACIÓN", header_box_title_style),
            Paragraph(_build_quote_document_number(document_data), header_box_number_style),
        ],
        width=145,
        stroke_color=color_principal,
        padding_x=10,
        padding_y=8,
        gap=7,
        radius=7,
        stroke_width=1.5,
    )

    tabla_principal = Table(
        [[logo, company_table, document_header_box]],
        colWidths=[160, company_col_width, 145],
    )
    tabla_principal.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    tabla_cliente = Table(
        [
            ["Señores:", Paragraph(nombre_cliente, body), "Emisión:", fecha_emision],
            [f"{tipo_doc_cliente}:", nro_doc_cliente, "Vencimiento:", fecha_vencimiento],
            ["Dirección:", Paragraph(direccion_cliente, body), "Moneda:", moneda_texto],
        ],
        colWidths=[ancho_total * 0.1, ancho_total * 0.6, ancho_total * 0.15, ancho_total * 0.15],
    )
    tabla_cliente.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 0), (-1, -1), 10.5),
                ("LINEABOVE", (0, 0), (-1, 0), 1.5, color_principal),
                ("LINEBELOW", (0, -1), (-1, -1), 1.5, color_principal),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    productos_para_pdf = []
    for item_data in line_context["lines"]:
        productos_para_pdf.append(
            [
                Paragraph(item_data["descripcion"], body),
                Paragraph(_format_quantity(item_data["cantidad"]), body_center),
                Paragraph(f"{simbolo} {to_decimal(item_data['p_unit_con_igv']):.2f}", body_center),
                Paragraph(f"{simbolo} {to_decimal(item_data['igv_item']):.2f}", body_center),
                Paragraph(f"{simbolo} {to_decimal(item_data['precio_total_item']):.2f}", body_center),
            ]
        )

    tabla_productos = Table(
        [
            [
                Paragraph("Descripción", centered_header),
                Paragraph("Cantidad", centered_header),
                Paragraph("P.Unit", centered_header),
                Paragraph("IGV", centered_header),
                Paragraph("Precio", centered_header),
            ]
        ] + productos_para_pdf,
        colWidths=[
            ancho_total * 0.4,
            ancho_total * 0.15,
            ancho_total * 0.15,
            ancho_total * 0.15,
            ancho_total * 0.15,
        ],
        repeatRows=1,
    )
    tabla_productos.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (-1, 0), color_principal),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("LINEBELOW", (0, -1), (-1, -1), 1.5, color_principal),
            ]
        )
    )

    tabla_total = Table(
        [
            [Paragraph("Total Gravado", body_right), Paragraph(f"{simbolo} {total_gravado_d:.2f}", body_right)],
            [Paragraph("Total IGV", body_right), Paragraph(f"{simbolo} {total_igv_d:.2f}", body_right)],
            [Paragraph("Importe Total", body_bold_right), Paragraph(f"{simbolo} {monto_total_d:.2f}", body_bold_right)],
        ],
        colWidths=[ancho_total * 0.84, ancho_total * 0.16],
    )
    tabla_total.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    tabla_monto = Table(
        [
            [Paragraph(f"IMPORTE TOTAL A PAGAR {simbolo} {monto_total_d:.2f}", body_bold_center)],
            [Paragraph(monto_en_letras_str, body_bold_center)],
        ],
        colWidths=[ancho_total],
    )
    tabla_monto.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEABOVE", (0, 0), (-1, 0), 1.5, color_principal),
                ("LINEBELOW", (0, -1), (-1, -1), 1.5, color_principal),
                ("TOPPADDING", (0, 0), (0, 0), 6),
                ("BOTTOMPADDING", (0, 0), (0, 0), 2),
                ("TOPPADDING", (0, 1), (0, 1), 2),
                ("BOTTOMPADDING", (0, 1), (0, 1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    footer_elements = []
    observation_lines = parse_quote_observations(getattr(document_data, "observaciones", None))
    if not observation_lines:
        observation_lines = build_default_observation_lines(
            note_1_text=getattr(tenant, "pdf_note_1", None),
            note_1_color=getattr(tenant, "pdf_note_1_color", None),
            note_2_text=getattr(tenant, "pdf_note_2", None),
        )

    for index, note_line in enumerate(observation_lines):
        try:
            note_color = colors.HexColor(note_line["color"])
        except Exception:
            note_color = colors.HexColor("#111111")
        note_style = ParagraphStyle(
            name=f"QuoteObservation{index}",
            parent=body,
            textColor=note_color,
            fontName="Helvetica-Bold" if note_line.get("bold") else "Helvetica",
        )
        footer_elements.append(Paragraph(note_line["text"].replace("\n", "<br/>"), note_style))
        footer_elements.append(Spacer(1, 5))

    if footer_elements:
        footer_elements.append(Spacer(1, 5))

    payment_methods_text = _build_payment_methods_text(
        company_data["bank_accounts"],
        beneficiary_name=company_data["name"],
    )
    if payment_methods_text:
        footer_elements.append(Paragraph(payment_methods_text, body))

    elementos = [
        tabla_principal,
        Spacer(1, 18),
        tabla_cliente,
        Spacer(1, 18),
        tabla_productos,
        tabla_total,
        tabla_monto,
    ]

    if footer_elements:
        elementos += [Spacer(1, 16)] + footer_elements

    try:
        doc.build(elementos)
    except Exception as build_err:
        print(f"ERROR: Fallo la construccion del PDF de cotizacion: {build_err}")
        traceback.print_exc()
        raise

    buffer.seek(0)
    return buffer


def create_pdf_buffer(document_data, tenant: models.Tenant, document_type: str):
    if document_type == "cotizacion":
        return _build_quote_pdf_buffer(document_data, tenant)

    buffer = io.BytesIO()
    is_comprobante = document_type == "comprobante"
    parsed_xml = None
    if is_comprobante:
        parsed_xml = fiscal_xml_service.parse_sale_document_xml(
            getattr(document_data, "sunat_xml_content", None)
        )

    margen_izq = 20
    margen_der = 20
    ancho_total = letter[0] - margen_izq - margen_der

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=margen_izq,
        rightMargin=margen_der,
        topMargin=20,
        bottomMargin=20,
    )

    styles = getSampleStyleSheet()
    header_text_style = ParagraphStyle(
        name="HeaderText",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=11,
    )
    header_bold_style = ParagraphStyle(
        name="HeaderBold",
        parent=header_text_style,
        fontName="Helvetica-Bold",
    )
    body = styles["Normal"]
    body_center = ParagraphStyle(name="BodyCenter", parent=body, alignment=TA_CENTER)
    body_bold = ParagraphStyle(name="BodyBold", parent=body, fontName="Helvetica-Bold")
    body_total_label_right = ParagraphStyle(name="BodyTotalLabelRight", parent=body, alignment=TA_RIGHT)
    body_total_value_center = ParagraphStyle(name="BodyTotalValueCenter", parent=body, alignment=TA_CENTER)
    body_bold_total_label_right = ParagraphStyle(name="BodyBoldTotalLabelRight", parent=body_bold, alignment=TA_RIGHT)
    body_bold_total_value_center = ParagraphStyle(name="BodyBoldTotalValueCenter", parent=body_bold, alignment=TA_CENTER)
    legal_text_style = ParagraphStyle(name="LegalText", parent=body, alignment=TA_CENTER, fontSize=7)

    moneda_codigo = (parsed_xml or {}).get("currency") or _value_from_obj(document_data, "moneda", "PEN")
    simbolo = "S/" if moneda_codigo == "PEN" else "$"
    moneda_texto = "SOLES" if moneda_codigo == "PEN" else "DOLARES"

    tipo_doc_sunat = (parsed_xml or {}).get("tipo_comprobante") or _value_from_obj(document_data, "tipo_comprobante", "03")
    doc_title_str = _resolver_titulo_documento(tipo_doc_sunat, is_comprobante)

    serie = _value_from_obj(document_data, "serie", "COT")
    correlativo = _value_from_obj(document_data, "correlativo", 0)
    doc_number_str = f"N° {serie}-{str(correlativo).zfill(6)}"
    if parsed_xml and parsed_xml.get("document_id"):
        doc_number_str = f"N° {parsed_xml['document_id']}"

    raw_fecha = (
        (parsed_xml or {}).get("issue_date")
        or _value_from_obj(document_data, "fecha_emision", None)
        or _value_from_obj(document_data, "created_at", datetime.now())
    )
    fecha_emision = _format_date_ddmmyyyy(raw_fecha, default=datetime.now().strftime("%d/%m/%Y"))

    raw_venc = _value_from_obj(document_data, "fecha_vencimiento", None)
    if raw_venc:
        parsed_venc = _parse_datetime_like(raw_venc)
        fecha_vencimiento = parsed_venc.strftime("%d/%m/%Y") if parsed_venc else fecha_emision
    else:
        base_fecha = _parse_datetime_like(raw_fecha) or datetime.now()
        fecha_vencimiento = (base_fecha + relativedelta(months=1)).strftime("%d/%m/%Y")

    supplier = (parsed_xml or {}).get("supplier") or {}
    customer = (parsed_xml or {}).get("customer") or {}
    business_name_render = supplier.get("name") or tenant.business_name or "Nombre del Negocio"
    business_address_render = supplier.get("address") or tenant.business_address or "Direccion no especificada"
    ruc_para_cuadro = supplier.get("doc_number") or tenant.business_ruc or ""

    if parsed_xml:
        nombre_cliente = customer.get("name") or "Cliente General"
        tipo_doc_cliente_str = obtener_etiqueta_tipo_doc(customer.get("doc_type") or "0")
        nro_doc_cliente = str(customer.get("doc_number") or "00000000")
        direccion_cliente = str(customer.get("address") or "-").replace("\n", "<br/>")
        line_context = _build_xml_line_context(parsed_xml)
        monto_en_letras_str = parsed_xml.get("amount_in_words") or ""
    else:
        cliente = getattr(document_data, "cliente", None)
        if cliente:
            nombre_cliente = getattr(cliente, "razon_social", "")
            tipo_doc_cliente_str = obtener_etiqueta_tipo_doc(getattr(cliente, "tipo_documento", "1"))
            nro_doc_cliente = str(getattr(cliente, "numero_documento", ""))
            direccion_cliente = str(getattr(cliente, "direccion", "") or "").replace("\n", "<br/>")
        else:
            nombre_cliente = "Cliente General"
            tipo_doc_cliente_str = "DOC"
            nro_doc_cliente = "00000000"
            direccion_cliente = "-"
        line_context = _build_local_line_context(document_data)
        monto_en_letras_str = ""

    total_gravado_d = to_decimal(line_context["total_gravado"])
    total_igv_d = to_decimal(line_context["total_igv"])
    monto_total_d = to_decimal(line_context["monto_total"])
    if not monto_en_letras_str:
        monto_en_letras_str = monto_a_letras(monto_total_d, simbolo)

    color_principal = colors.HexColor(tenant.primary_color or "#004aad")
    logo = _load_logo(tenant)

    business_name_p = Paragraph(business_name_render, header_bold_style)
    business_address_p = Paragraph(str(business_address_render).replace("\n", "<br/>"), header_text_style)
    contact_info_p = Paragraph(f"{(tenant.business_phone or '').strip()}", header_text_style)
    header_box_ruc_style = ParagraphStyle(
        name="HeaderBoxRuc",
        parent=header_text_style,
        alignment=TA_CENTER,
        fontSize=10.5,
        leading=12,
    )
    header_box_title_style = ParagraphStyle(
        name="HeaderBoxTitle",
        parent=header_bold_style,
        alignment=TA_CENTER,
        fontSize=12.5,
        leading=14,
    )
    header_box_number_style = ParagraphStyle(
        name="HeaderBoxNumber",
        parent=header_bold_style,
        alignment=TA_CENTER,
        fontSize=11.5,
        leading=13,
    )

    ruc_p = Paragraph(f"RUC {ruc_para_cuadro}", header_box_ruc_style)
    titulo_p = Paragraph(doc_title_str.replace("ELECTRONICA", "<br/>ELECTRONICA"), header_box_title_style)
    numero_p = Paragraph(doc_number_str, header_box_number_style)
    document_box_width = ancho_total * 0.24
    document_header_box = _RoundedHeaderBox(
        [ruc_p, titulo_p, numero_p],
        width=document_box_width,
        stroke_color=color_principal,
        padding_x=10,
        padding_y=8,
        gap=5,
        radius=7,
        stroke_width=1.5,
    )

    data_principal = [
        [logo, business_name_p, document_header_box],
        ["", business_address_p, ""],
        ["", contact_info_p, ""],
    ]
    tabla_principal = Table(data_principal, colWidths=[ancho_total * 0.3, ancho_total * 0.46, document_box_width])
    tabla_principal.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("SPAN", (0, 0), (0, -1)),
                ("SPAN", (2, 0), (2, -1)),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (2, 0), (2, -1), "TOP"),
            ]
        )
    )

    nombre_cliente_p = Paragraph(nombre_cliente, body)
    direccion_cliente_p = Paragraph(direccion_cliente, body)
    lbl_venc = " Vencimiento:" if not is_comprobante else ""
    val_venc = fecha_vencimiento if not is_comprobante else ""

    data_cliente = [
        ["Señores:", nombre_cliente_p, " Emision:", fecha_emision],
        [f"{tipo_doc_cliente_str}:", nro_doc_cliente, lbl_venc, val_venc],
        ["Direccion:", direccion_cliente_p, " Moneda:", moneda_texto],
    ]
    tabla_cliente = Table(
        data_cliente,
        colWidths=[ancho_total * 0.1, ancho_total * 0.6, ancho_total * 0.15, ancho_total * 0.15],
    )
    tabla_cliente.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("LINEABOVE", (0, 0), (-1, 0), 1.5, color_principal),
                ("LINEBELOW", (0, -1), (-1, -1), 1.5, color_principal),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    productos_para_pdf = []
    for item_data in line_context["lines"]:
        productos_para_pdf.append(
            [
                Paragraph(item_data["descripcion"], body),
                Paragraph(_format_quantity(item_data["cantidad"]), body_center),
                Paragraph(f"{simbolo} {to_decimal(item_data['p_unit_con_igv']):.2f}", body_center),
                Paragraph(f"{simbolo} {to_decimal(item_data['igv_item']):.2f}", body_center),
                Paragraph(f"{simbolo} {to_decimal(item_data['precio_total_item']):.2f}", body_center),
            ]
        )

    centered_header = ParagraphStyle(
        name="CenteredHeader",
        parent=body_bold,
        alignment=TA_CENTER,
        textColor=colors.white,
    )
    header_productos = [
        Paragraph("Descripcion", centered_header),
        Paragraph("Cantidad", centered_header),
        Paragraph("P.Unit", centered_header),
        Paragraph("IGV", centered_header),
        Paragraph("Precio", centered_header),
    ]
    data_productos = [header_productos] + productos_para_pdf
    tabla_productos = Table(
        data_productos,
        colWidths=[
            ancho_total * 0.4,
            ancho_total * 0.15,
            ancho_total * 0.15,
            ancho_total * 0.15,
            ancho_total * 0.15,
        ],
        repeatRows=1,
    )
    tabla_productos.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (-1, 0), color_principal),
                ("LINEBELOW", (0, -1), (-1, -1), 1.5, color_principal),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ]
        )
    )

    data_total = [
        [Paragraph("Total Gravado", body_total_label_right), Paragraph(f"{simbolo} {total_gravado_d:.2f}", body_total_value_center)],
        [Paragraph("Total IGV", body_total_label_right), Paragraph(f"{simbolo} {total_igv_d:.2f}", body_total_value_center)],
        [Paragraph("Importe Total", body_bold_total_label_right), Paragraph(f"{simbolo} {monto_total_d:.2f}", body_bold_total_value_center)],
    ]
    tabla_total = Table(data_total, colWidths=[ancho_total * 0.85, ancho_total * 0.15])
    tabla_total.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTNAME", (0, 2), (1, 2), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    centered_bold_style = ParagraphStyle(name="CenteredBold", parent=body_bold, alignment=TA_CENTER)
    monto_letras_p = Paragraph(monto_en_letras_str, centered_bold_style)
    monto_numeros_p = Paragraph(f"IMPORTE TOTAL A PAGAR {simbolo} {monto_total_d:.2f}", centered_bold_style)
    tabla_monto = Table([[monto_numeros_p], [monto_letras_p]], colWidths=[ancho_total])
    tabla_monto.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEABOVE", (0, 0), (-1, 0), 1.5, color_principal),
                ("LINEBELOW", (0, -1), (-1, -1), 1.5, color_principal),
                ("TOPPADDING", (0, 0), (0, 0), 6),
                ("BOTTOMPADDING", (0, 0), (0, 0), 2),
                ("TOPPADDING", (0, 1), (0, 1), 2),
                ("BOTTOMPADDING", (0, 1), (0, 1), 6),
            ]
        )
    )

    qr_content = _build_qr_content(
        document_data,
        f"{ruc_para_cuadro}|{tipo_doc_sunat}|{serie}|{correlativo}|{total_igv_d}|{monto_total_d}|{fecha_emision}|{tipo_doc_cliente_str}|{nro_doc_cliente}",
    )
    t_qr_centered = _build_qr_flowable(document_data, qr_content, ancho_total)

    payment_methods_text = _build_payment_methods_text(
        getattr(tenant, "bank_accounts", None),
        beneficiary_name=getattr(tenant, "business_name", None) or "",
    )
    payment_methods_p = Paragraph(payment_methods_text, body) if payment_methods_text else None

    footer_notes = []
    if not is_comprobante:
        default_observation_lines = build_default_observation_lines(
            note_1_text=getattr(tenant, "pdf_note_1", None),
            note_1_color=getattr(tenant, "pdf_note_1_color", None),
            note_2_text=getattr(tenant, "pdf_note_2", None),
        )
        for index, note_line in enumerate(default_observation_lines):
            try:
                note_color = colors.HexColor(note_line["color"])
            except Exception:
                note_color = colors.HexColor("#111111")
            note_style = ParagraphStyle(
                name=f"DefaultObservation{index}",
                parent=body,
                textColor=note_color,
                fontName="Helvetica-Bold" if note_line.get("bold") else "Helvetica",
            )
            footer_notes.append(Paragraph(note_line["text"].replace("\n", "<br/>"), note_style))
            footer_notes.append(Spacer(1, 5))

        if footer_notes:
            footer_notes.append(Spacer(1, 5))

    final_legal = []
    if is_comprobante:
        legal_text = (
            f"Representacion impresa de la <b>{doc_title_str}</b>. "
            "El usuario puede consultar su validez en SUNAT Virtual: www.sunat.gob.pe"
        )
        legal_paragraph = Paragraph(legal_text, legal_text_style)
        tabla_legal = Table([[legal_paragraph]], colWidths=[ancho_total])
        tabla_legal.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 1, colors.black),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        final_legal = [Spacer(1, 10), tabla_legal]

    elementos = [
        tabla_principal,
        Spacer(1, 20),
        tabla_cliente,
        Spacer(1, 20),
        tabla_productos,
        tabla_total,
        tabla_monto,
        Spacer(1, 15),
    ] + footer_notes

    if payment_methods_p:
        elementos += [payment_methods_p, Spacer(1, 15)]

    elementos += [t_qr_centered] + final_legal

    try:
        doc.build(elementos)
    except Exception as build_err:
        print(f"ERROR: Fallo la construccion del PDF: {build_err}")
        traceback.print_exc()
        raise

    buffer.seek(0)
    return buffer


def generar_pdf_cotizacion(cotizacion: models.Cotizacion, tenant: models.Tenant):
    return create_pdf_buffer(cotizacion, tenant, "cotizacion")


def create_comprobante_pdf(comprobante, tenant: models.Tenant):
    return create_pdf_buffer(comprobante, tenant, "comprobante")
