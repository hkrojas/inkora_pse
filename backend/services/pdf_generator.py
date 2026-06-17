import io
import os
import traceback
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP, getcontext
from functools import lru_cache
from types import SimpleNamespace

import models
import qrcode
import requests
from dateutil.relativedelta import relativedelta
from num2words import num2words
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, Image, KeepInFrame, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from services import fiscal_qr_service, fiscal_xml_service
from services.calculations import TOTAL_PRECISION, calculate_cotizacion_totals_v3, to_decimal
from services.client_snapshot_service import resolve_document_cliente_snapshot
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
        "A": "CED. DIPLOMATICA",
    }
    return mapeo.get(str(codigo), "DOC")


def _resolve_document_client_data(document_data) -> dict:
    snapshot = resolve_document_cliente_snapshot(document_data)
    return {
        "name": snapshot.get("razon_social") or snapshot.get("nombre_comercial") or "Cliente General",
        "doc_type": snapshot.get("tipo_documento") or "0",
        "doc_type_label": obtener_etiqueta_tipo_doc(snapshot.get("tipo_documento") or "0"),
        "doc_number": str(snapshot.get("numero_documento") or ""),
        "address": str(snapshot.get("direccion") or "-"),
        "email": str(snapshot.get("email") or ""),
        "phone": str(snapshot.get("telefono") or ""),
    }


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
        "mostrar_en_cotizaciones": entry.get("mostrar_en_cotizaciones") is not False,
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


def _get_payment_qr_image_url(payment_methods) -> str:
    if not isinstance(payment_methods, list):
        return ""

    for entry in payment_methods:
        if not isinstance(entry, dict):
            continue
        entry_type = str(entry.get("tipo") or "").strip().lower()
        if entry_type != "payment_qr_image":
            continue
        qr_url = str(entry.get("url") or entry.get("payment_qr_filename") or "").strip()
        if qr_url:
            return qr_url

    return ""


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


def _resolve_quote_bank_accounts(payment_methods, quote_payment_methods) -> list[dict]:
    if quote_payment_methods is not None:
        return [
            method
            for method in _normalize_payment_methods(quote_payment_methods)
            if method.get("tipo") == "bank"
        ]

    return [
        method
        for method in _normalize_payment_methods(payment_methods)
        if method.get("tipo") == "bank" and method.get("mostrar_en_cotizaciones", True)
    ]


def _build_qr_content(document_data, fallback_content: str) -> str:
    qr_payload = getattr(document_data, "sunat_qr_payload", None)
    if isinstance(qr_payload, dict):
        qr_content = qr_payload.get("qr_content")
        if isinstance(qr_content, str) and qr_content.strip():
            return qr_content.strip()
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
    xml_content = getattr(document_data, "sunat_xml_content", None)
    provider_hash = getattr(document_data, "sunat_hash", None)
    generated_payload = fiscal_qr_service.build_sunat_qr_payload(xml_content, provider_hash=provider_hash)
    if generated_payload and generated_payload.get("qr_content"):
        return generated_payload["qr_content"]
    return fallback_content


def _resolve_qr_visible_summary(document_data) -> str | None:
    qr_payload = getattr(document_data, "sunat_qr_payload", None)
    if isinstance(qr_payload, dict) and qr_payload.get("digest_in_qr") is False:
        summary = qr_payload.get("qr_visible_summary") or qr_payload.get("valorResumen")
        return str(summary).strip() if summary else None

    generated_payload = fiscal_qr_service.build_sunat_qr_payload(
        getattr(document_data, "sunat_xml_content", None),
        provider_hash=getattr(document_data, "sunat_hash", None),
    )
    if generated_payload and generated_payload.get("digest_in_qr") is False:
        summary = generated_payload.get("qr_visible_summary") or generated_payload.get("valorResumen")
        return str(summary).strip() if summary else None
    return None


def _build_qr_flowable(document_data, qr_content: str, ancho_total: float):
    official_qr_svg = getattr(document_data, "sunat_qr_svg", None)
    qr_payload = getattr(document_data, "sunat_qr_payload", None)
    should_use_legacy_svg = official_qr_svg and not (
        isinstance(qr_payload, dict) and qr_payload.get("qr_content")
    )
    if should_use_legacy_svg:
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

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_Q,
        border=4,
        box_size=8,
    )
    qr.add_data(qr_content or "QR")
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
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


@lru_cache(maxsize=128)
def _load_remote_logo_bytes(url: str) -> bytes | None:
    response = requests.get(url, timeout=2)
    if response.status_code != 200:
        return None
    return response.content


def _load_logo(tenant):
    if not getattr(tenant, "logo_filename", None):
        return ""

    try:
        if tenant.logo_filename.startswith("http"):
            content = _load_remote_logo_bytes(tenant.logo_filename)
            if content:
                return Image(io.BytesIO(content), width=151, height=76)
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


class _RoundedDocumentBox(Flowable):
    def __init__(
        self,
        width,
        height,
        stroke_color,
        title_paragraph,
        number_paragraph,
        footer_paragraph,
        radius=8,
        stroke_width=1.5,
        band_fill=None,
    ):
        super().__init__()
        self.width = width
        self.height = height
        self.stroke_color = stroke_color
        self.title_paragraph = title_paragraph
        self.number_paragraph = number_paragraph
        self.footer_paragraph = footer_paragraph
        self.radius = radius
        self.stroke_width = stroke_width
        self.band_fill = band_fill or stroke_color

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        canvas.setStrokeColor(self.stroke_color)
        canvas.setLineWidth(self.stroke_width)
        canvas.roundRect(0, 0, self.width, self.height, self.radius, stroke=1, fill=0)

        band_h = self.height * 0.28
        title_h = (self.height - band_h) / 2
        footer_h = title_h

        band_y = footer_h
        title_y = footer_h + band_h

        canvas.setFillColor(self.band_fill)
        band_inset_x = 0.15 * cm
        band_width = max(self.width - (band_inset_x * 2), 0)
        band_radius = max(min(self.radius - 1, (band_h / 2) - 1), 2)
        canvas.roundRect(band_inset_x, band_y, band_width, band_h, band_radius, stroke=0, fill=1)

        title_w = self.width - 12
        number_w = band_width - 10
        footer_w = self.width - 12

        _, title_ph = self.title_paragraph.wrap(title_w, title_h)
        _, number_ph = self.number_paragraph.wrap(number_w, band_h)
        _, footer_ph = self.footer_paragraph.wrap(footer_w, footer_h)

        self.title_paragraph.drawOn(
            canvas,
            (self.width - title_w) / 2,
            title_y + ((title_h - title_ph) / 2),
        )
        self.number_paragraph.drawOn(
            canvas,
            band_inset_x + ((band_width - number_w) / 2),
            band_y + ((band_h - number_ph) / 2),
        )
        self.footer_paragraph.drawOn(
            canvas,
            (self.width - footer_w) / 2,
            ((footer_h - footer_ph) / 2),
        )
        canvas.restoreState()


class _RoundedContainerBox(Flowable):
    def __init__(
        self,
        child,
        width,
        height,
        stroke_color,
        radius=8,
        stroke_width=1,
        padding=0,
    ):
        super().__init__()
        self.child = child
        self.width = width
        self.height = height
        self.stroke_color = stroke_color
        self.radius = radius
        self.stroke_width = stroke_width
        self.padding = padding
        self._child_width = 0
        self._child_height = 0
        self.hAlign = "LEFT"

    def wrap(self, availWidth, availHeight):
        inner_width = max(self.width - (self.padding * 2), 0)
        inner_height = max(self.height - (self.padding * 2), 0)
        self._child_width, self._child_height = self.child.wrap(inner_width, inner_height)
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        canvas.setStrokeColor(self.stroke_color)
        canvas.setLineWidth(self.stroke_width)
        canvas.roundRect(0, 0, self.width, self.height, self.radius, stroke=1, fill=0)
        child_x = self.padding + max((self.width - (self.padding * 2) - self._child_width) / 2, 0)
        child_y = self.padding + max((self.height - (self.padding * 2) - self._child_height) / 2, 0)
        self.child.drawOn(canvas, child_x, child_y)
        canvas.restoreState()


class _AutoRoundedContainerBox(Flowable):
    def __init__(
        self,
        child,
        width,
        stroke_color,
        radius=8,
        stroke_width=1,
        padding=0,
    ):
        super().__init__()
        self.child = child
        self.width = width
        self.stroke_color = stroke_color
        self.radius = radius
        self.stroke_width = stroke_width
        self.padding = padding
        self.height = 0
        self._child_width = 0
        self._child_height = 0
        self.hAlign = "LEFT"

    def wrap(self, availWidth, availHeight):
        inner_width = max(self.width - (self.padding * 2), 0)
        self._child_width, self._child_height = self.child.wrap(inner_width, availHeight)
        self.height = self._child_height + (self.padding * 2)
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        clip_path = canvas.beginPath()
        clip_path.roundRect(0, 0, self.width, self.height, self.radius)
        canvas.clipPath(clip_path, stroke=0, fill=0)
        child_x = self.padding
        child_y = self.padding + max((self.height - (self.padding * 2) - self._child_height) / 2, 0)
        self.child.drawOn(canvas, child_x, child_y)
        canvas.restoreState()
        canvas.saveState()
        canvas.setStrokeColor(self.stroke_color)
        canvas.setLineWidth(self.stroke_width)
        canvas.roundRect(0, 0, self.width, self.height, self.radius, stroke=1, fill=0)
        canvas.restoreState()


class _HeaderDividerBox(Flowable):
    def __init__(self, child, width, height, divider_positions, divider_color, divider_height=4 * cm, stroke_width=1):
        super().__init__()
        self.child = child
        self.width = width
        self.height = height
        self.divider_positions = divider_positions
        self.divider_color = divider_color
        self.divider_height = divider_height
        self.stroke_width = stroke_width
        self._child_width = 0
        self._child_height = 0
        self.hAlign = "LEFT"

    def wrap(self, availWidth, availHeight):
        self._child_width, self._child_height = self.child.wrap(self.width, self.height)
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        self.child.drawOn(canvas, 0, 0)
        canvas.saveState()
        canvas.setStrokeColor(self.divider_color)
        canvas.setLineWidth(self.stroke_width)
        y1 = max((self.height - self.divider_height) / 2, 0)
        y2 = min(y1 + self.divider_height, self.height)
        for x in self.divider_positions:
            canvas.line(x, y1, x, y2)
        canvas.restoreState()


class _InsetHorizontalRule(Flowable):
    def __init__(self, width, color, inset=0.3 * cm, stroke_width=1):
        super().__init__()
        self.width = width
        self.color = color
        self.inset = inset
        self.stroke_width = stroke_width
        self.height = stroke_width
        self.hAlign = "LEFT"

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        canvas.setStrokeColor(self.color)
        canvas.setLineWidth(self.stroke_width)
        canvas.line(self.inset, self.height / 2, self.width - self.inset, self.height / 2)
        canvas.restoreState()


class _AutoVerticalDividerBox(Flowable):
    def __init__(self, child, width, divider_positions, divider_color, inset_y=0.3 * cm, stroke_width=1):
        super().__init__()
        self.child = child
        self.width = width
        self.divider_positions = divider_positions
        self.divider_color = divider_color
        self.inset_y = inset_y
        self.stroke_width = stroke_width
        self.height = 0
        self._child_width = 0
        self._child_height = 0
        self.hAlign = "LEFT"

    def wrap(self, availWidth, availHeight):
        self._child_width, self._child_height = self.child.wrap(self.width, availHeight)
        self.height = self._child_height
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        self.child.drawOn(canvas, 0, 0)
        canvas.saveState()
        canvas.setStrokeColor(self.divider_color)
        canvas.setLineWidth(self.stroke_width)
        y1 = self.inset_y
        y2 = max(y1, self.height - self.inset_y)
        for x in self.divider_positions:
            canvas.line(x, y1, x, y2)
        canvas.restoreState()


def _build_local_line_context(document_data):
    productos_fuente_dict = []
    items = getattr(document_data, "items", [])
    for item in items:
        if isinstance(item, dict):
            descripcion = item.get("descripcion", "")
            cantidad = item.get("unidades", 0) or item.get("cantidad", 0)
            precio_unitario = item.get("precio_unitario", 0)
            codigo = item.get("codigo") or item.get("code") or item.get("sku") or item.get("item_code")
            codigo = codigo or item.get("codigo_producto") or item.get("codProducto")
            unidad = item.get("unidad") or item.get("unidad_medida") or item.get("unit_code") or "UND"
        else:
            descripcion = getattr(item, "descripcion", "")
            cantidad = getattr(item, "cantidad", 0)
            precio_unitario = getattr(item, "precio_unitario", 0)
            codigo = (
                getattr(item, "codigo", None)
                or getattr(item, "code", None)
                or getattr(item, "sku", None)
                or getattr(item, "item_code", None)
                or getattr(item, "codigo_producto", None)
            )
            unidad = (
                getattr(item, "unidad", None)
                or getattr(item, "unidad_medida", None)
                or getattr(item, "unit_code", None)
                or "UND"
            )

        productos_fuente_dict.append(
            {
                "unidades": cantidad,
                "precio_unitario": precio_unitario,
                "descripcion": descripcion,
                "codigo": codigo,
                "unidad": unidad,
            }
        )

    totals_v3 = calculate_cotizacion_totals_v3(productos_fuente_dict)
    productos_para_tabla_data = []
    for idx, item_dict in enumerate(productos_fuente_dict):
        line_totals = totals_v3["line_totals"][idx]
        productos_para_tabla_data.append(
            {
                "indice": idx + 1,
                "codigo": item_dict.get("codigo") or f"ITEM-{str(idx + 1).zfill(3)}",
                "descripcion": str(item_dict["descripcion"]).replace("\n", "<br/>"),
                "cantidad": to_decimal(item_dict["unidades"]),
                "unidad": str(item_dict.get("unidad") or "UND"),
                "valor_unitario": line_totals["mto_valor_unitario"],
                "p_unit_con_igv": line_totals["mto_precio_unitario_con_igv"],
                "igv_item": line_totals["igv_linea"],
                "subtotal_item": line_totals["precio_total_linea"] - line_totals["igv_linea"],
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

    for idx, line in enumerate(parsed_xml.get("lines") or [], start=1):
        cantidad = to_decimal(line.get("quantity") or 0)
        line_extension_amount = to_decimal(line.get("line_extension_amount") or 0)
        precio_total_item = to_decimal(line.get("line_extension_amount") or 0) + to_decimal(line.get("tax_amount") or 0)
        valor_unitario = Decimal("0.00")
        if cantidad > 0:
            valor_unitario = (line_extension_amount / cantidad).quantize(TOTAL_PRECISION, rounding=ROUND_HALF_UP)
        productos_para_tabla_data.append(
            {
                "indice": idx,
                "codigo": str(line.get("code") or f"ITEM-{str(idx).zfill(3)}"),
                "descripcion": str(line.get("description") or "").replace("\n", "<br/>"),
                "cantidad": cantidad,
                "unidad": str(line.get("unit_code") or "UND"),
                "valor_unitario": valor_unitario,
                "p_unit_con_igv": to_decimal(line.get("price_amount") or 0),
                "igv_item": to_decimal(line.get("tax_amount") or 0),
                "subtotal_item": line_extension_amount,
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
    serie = _value_from_obj(document_data, "serie", "COT") or "COT"
    correlativo = _value_from_obj(document_data, "correlativo", None)
    if correlativo in (None, "", 0):
        correlativo = _value_from_obj(document_data, "id", 0)
    return f"{serie}-{str(correlativo or 0).zfill(6)}"


def _resolve_quote_company_data(document_data, tenant: models.Tenant) -> dict:
    user = getattr(document_data, "usuario", None)

    company_name = getattr(tenant, "business_name", None) or "Nombre del Negocio"
    company_ruc = getattr(tenant, "business_ruc", None) or ""
    company_address = getattr(tenant, "business_address", None) or "Direccion no especificada"
    company_phone = getattr(tenant, "business_phone", None) or ""
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
        "quote_bank_accounts": _resolve_quote_bank_accounts(
            bank_accounts,
            getattr(document_data, "quote_payment_methods", None),
        ),
        "logo_source": logo_source,
    }


def _format_money(symbol: str, amount: Decimal | int | float | str) -> str:
    return f"{symbol} {to_decimal(amount):,.2f}"


def _format_detail_money(symbol: str, amount: Decimal | int | float | str) -> str:
    max_amount = Decimal("999999.00")
    value = to_decimal(amount)
    if value > max_amount:
        value = max_amount
    elif value < -max_amount:
        value = -max_amount
    return f"{symbol} {value:,.2f}"


def _format_money_inline(symbol: str, amount: Decimal | int | float | str) -> str:
    return _format_money(symbol, amount).replace(" ", "&nbsp;", 1)


def _measure_flowable_height(flowable, width: float) -> float:
    _, height = flowable.wrap(width, 10_000)
    return float(height)


def _display_unit_code(unit_code: str | None) -> str:
    normalized = str(unit_code or "UND").strip().upper()
    if normalized == "NIU":
        return "UND"
    return normalized or "UND"


def _html_escape(value: object) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _text_width(value: object, style: ParagraphStyle) -> float:
    return stringWidth(str(value or ""), style.fontName, style.fontSize)


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))


def _build_quote_detail_col_widths(
    lines: list[dict],
    total_width: float,
    *,
    header_style: ParagraphStyle,
    text_style: ParagraphStyle,
    money_style: ParagraphStyle,
    symbol: str,
) -> list[float]:
    """Distribuye columnas del detalle sin cambiar el ancho total de la tabla."""
    headers = ["N°", "CANTIDAD", "CÓDIGO", "DESCRIPCIÓN", "V/U", "P/U", "SUBTOTAL", "TOTAL"]
    padding_allowance = 11

    index_width = max(
        _text_width(headers[0], header_style),
        *[_text_width(line.get("indice") or "", text_style) for line in lines],
    ) + padding_allowance
    quantity_width = max(
        _text_width(headers[1], header_style),
        *[
            _text_width(
                f"{_format_quantity(line.get('cantidad') or 0)} {_display_unit_code(line.get('unidad'))}",
                text_style,
            )
            for line in lines
        ],
    ) + padding_allowance
    code_width = max(
        _text_width(headers[2], header_style),
        *[_text_width(line.get("codigo") or "-", text_style) for line in lines],
    ) + padding_allowance
    money_width = max(
        _text_width(headers[4], header_style),
        _text_width(headers[5], header_style),
        _text_width(headers[6], header_style),
        _text_width(headers[7], header_style),
        *[
            _text_width(_format_detail_money(symbol, line.get(key) or 0), money_style)
            for line in lines
            for key in ("valor_unitario", "p_unit_con_igv", "subtotal_item", "precio_total_item")
        ],
    ) + padding_allowance

    widths = [
        _clamp(index_width, total_width * 0.04, total_width * 0.055),
        _clamp(quantity_width, total_width * 0.105, total_width * 0.13),
        _clamp(code_width, total_width * 0.09, total_width * 0.145),
        0,
        _clamp(money_width, total_width * 0.092, total_width * 0.125),
        _clamp(money_width, total_width * 0.092, total_width * 0.125),
        _clamp(money_width, total_width * 0.118, total_width * 0.145),
        _clamp(money_width, total_width * 0.118, total_width * 0.145),
    ]
    widths[3] = total_width - sum(widths[:3]) - sum(widths[4:])
    description_min = total_width * 0.22
    if widths[3] < description_min:
        deficit = description_min - widths[3]
        minimums = {
            1: total_width * 0.105,
            2: total_width * 0.09,
            4: total_width * 0.092,
            5: total_width * 0.092,
            6: total_width * 0.118,
            7: total_width * 0.118,
        }
        for idx in (2, 6, 7, 1, 4, 5):
            available = max(0, widths[idx] - minimums[idx])
            reduction = min(available, deficit)
            widths[idx] -= reduction
            deficit -= reduction
            if deficit <= 0:
                break
        widths[3] = total_width - sum(widths[:3]) - sum(widths[4:])

    widths[3] += total_width - sum(widths)
    return widths


def _resolve_company_data(document_data, tenant: models.Tenant, parsed_xml: dict | None) -> dict:
    user = getattr(document_data, "usuario", None)
    supplier = (parsed_xml or {}).get("supplier") or {}

    company_name = supplier.get("name") or getattr(tenant, "business_name", None) or "Nombre del Negocio"
    company_ruc = supplier.get("doc_number") or getattr(tenant, "business_ruc", None) or ""
    company_address = supplier.get("address") or getattr(tenant, "business_address", None) or "Direccion no especificada"
    company_phone = getattr(tenant, "business_phone", None) or getattr(user, "business_phone", None) or ""
    company_email = (
        getattr(tenant, "business_email", None)
        or getattr(user, "business_email", None)
        or getattr(user, "email", None)
        or ""
    )

    bank_accounts = getattr(tenant, "bank_accounts", None) or []
    logo_source = tenant if getattr(tenant, "logo_filename", None) else user

    return {
        "name": str(company_name or "").strip(),
        "ruc": str(company_ruc or "").strip(),
        "address": str(company_address or "").strip(),
        "phone": str(company_phone or "").strip(),
        "email": str(company_email or "").strip(),
        "bank_accounts": bank_accounts,
        "logo_source": logo_source or tenant,
    }


def _pick_wallet_payment_method(payment_methods) -> dict | None:
    for method in _normalize_payment_methods(payment_methods):
        if method.get("tipo") == "wallet":
            return method
    return None


def _build_quote_wallet_qr_content(payment_methods, beneficiary_name: str) -> tuple[str, dict | None]:
    wallet = _pick_wallet_payment_method(payment_methods)
    if wallet:
        qr_parts = [
            wallet.get("proveedor") or "Billetera digital",
            wallet.get("titular") or beneficiary_name,
            wallet.get("numero") or "",
            wallet.get("nota") or "",
        ]
        return "|".join(str(part).strip() for part in qr_parts if str(part or "").strip()), wallet

    normalized = _normalize_payment_methods(payment_methods)
    if normalized:
        first = normalized[0]
        if first.get("tipo") == "bank":
            qr_parts = [
                beneficiary_name,
                first.get("banco") or "",
                first.get("cuenta") or "",
                first.get("cci") or "",
            ]
            return "|".join(str(part).strip() for part in qr_parts if str(part or "").strip()), None

    return beneficiary_name or "PAGO DIGITAL", None


_QUOTE_CREDIT_TERM_DAYS = {
    "credito_7": 7,
    "credito_15": 15,
    "credito_30": 30,
    "credito_60": 60,
}


def _resolve_quote_due_date_display(document_data) -> tuple[str, str]:
    raw_issue = (
        _value_from_obj(document_data, "fecha_emision", None)
        or _value_from_obj(document_data, "created_at", datetime.now())
    )
    issue_dt = _parse_datetime_like(raw_issue) or datetime.now()
    issue_label = issue_dt.strftime("%d/%m/%Y")

    raw_due = _value_from_obj(document_data, "fecha_vencimiento", None)
    if raw_due:
        parsed_due = _parse_datetime_like(raw_due)
        if parsed_due:
            return issue_label, parsed_due.strftime("%d/%m/%Y")
        return issue_label, issue_label

    condicion_pago = str(_value_from_obj(document_data, "condicion_pago", "") or "").strip().lower()
    if condicion_pago == "contado":
        return issue_label, issue_label

    due_days = _QUOTE_CREDIT_TERM_DAYS.get(condicion_pago, 15)
    return issue_label, (issue_dt + relativedelta(days=due_days)).strftime("%d/%m/%Y")


def _build_generated_qr_flowable(qr_content: str, target_size: float, col_width: float):
    qr_img = qrcode.make(qr_content or "QR")
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    qr_image_obj = Image(qr_buffer, width=target_size, height=target_size)
    qr_table = Table([[qr_image_obj]], colWidths=[col_width])
    qr_table.setStyle(
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
    return qr_table


def _build_uploaded_payment_qr_flowable(payment_methods, target_size: float, col_width: float):
    qr_url = _get_payment_qr_image_url(payment_methods)
    if not qr_url:
        return None

    try:
        content = None
        if qr_url.startswith("http"):
            content = _load_remote_logo_bytes(qr_url)
        elif os.path.exists(qr_url):
            with open(qr_url, "rb") as image_file:
                content = image_file.read()

        if not content:
            return None

        qr_image_obj = Image(io.BytesIO(content), width=target_size, height=target_size)
        qr_table = Table([[qr_image_obj]], colWidths=[col_width])
        qr_table.setStyle(
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
        return qr_table
    except Exception as err:
        print(f"Error cargando QR de cobro en PDF: {err}")
        return None


def _build_logo_block(company_data: dict, color_principal, width: float, name_style: ParagraphStyle):
    logo = _load_logo(company_data["logo_source"])
    if logo:
        return logo

    fallback_name = company_data["name"].upper() or "INKORA"
    return Paragraph(fallback_name.replace(" Y ", "<br/>"), name_style)


def _build_observation_paragraphs(document_data, tenant, base_style: ParagraphStyle) -> list:
    footer_notes = []
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
            name=f"ModernObservation{index}",
            parent=base_style,
            textColor=note_color,
            fontName="Helvetica-Bold" if note_line.get("bold") else "Helvetica",
        )
        footer_notes.append(Paragraph(note_line["text"].replace("\n", "<br/>"), note_style))
    return footer_notes


def _build_footer_contact_text(company_data: dict) -> str:
    parts = []
    if company_data.get("phone"):
        parts.append(company_data["phone"])
    if company_data.get("email"):
        parts.append(company_data["email"])
    return "  |  ".join(parts)


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

    fecha_emision, fecha_vencimiento = _resolve_quote_due_date_display(document_data)

    client_data = _resolve_document_client_data(document_data)
    nombre_cliente = client_data["name"]
    tipo_doc_cliente = client_data["doc_type_label"]
    nro_doc_cliente = client_data["doc_number"]
    direccion_cliente = client_data["address"].replace("\n", "<br/>")

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
        company_data["quote_bank_accounts"],
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
        client_data = _resolve_document_client_data(document_data)
        nombre_cliente = client_data["name"]
        tipo_doc_cliente_str = client_data["doc_type_label"]
        nro_doc_cliente = client_data["doc_number"] or "00000000"
        direccion_cliente = client_data["address"].replace("\n", "<br/>")
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


def _build_modern_pdf_buffer(document_data, tenant: models.Tenant, is_comprobante: bool):
    buffer = io.BytesIO()
    parsed_xml = None
    if is_comprobante:
        parsed_xml = fiscal_xml_service.parse_sale_document_xml(
            getattr(document_data, "sunat_xml_content", None)
        )

    margin_lr = 0.7 * cm
    margin_tb = 0.5 * cm
    header_height = 5.3 * cm
    ancho_total = A4[0] - (margin_lr * 2)
    color_principal = colors.HexColor(getattr(tenant, "primary_color", None) or "#2563EB")
    color_borde = colors.HexColor("#C9D4E5")
    color_texto = colors.HexColor("#1F2937")
    color_suave = colors.HexColor("#F8FAFF")

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=margin_lr,
        rightMargin=margin_lr,
        topMargin=margin_tb,
        bottomMargin=margin_tb,
    )

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        name="ModernBodyFinal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.4,
        leading=13,
        textColor=color_texto,
    )
    body_small = ParagraphStyle(name="ModernBodySmallFinal", parent=body, fontSize=9.4, leading=12)
    body_center = ParagraphStyle(name="ModernBodyCenterFinal", parent=body, alignment=TA_CENTER)
    body_right = ParagraphStyle(name="ModernBodyRightFinal", parent=body, alignment=TA_RIGHT)
    body_bold = ParagraphStyle(name="ModernBodyBoldFinal", parent=body, fontName="Helvetica-Bold")
    body_bold_blue = ParagraphStyle(name="ModernBodyBoldBlueFinal", parent=body_bold, textColor=color_principal)
    body_bold_center = ParagraphStyle(name="ModernBodyBoldCenterFinal", parent=body_bold, alignment=TA_CENTER)
    body_bold_blue_nobreak = ParagraphStyle(
        name="ModernBodyBoldBlueNoBreakFinal",
        parent=body_bold_blue,
        splitLongWords=0,
        wordWrap="LTR",
    )
    section_title = ParagraphStyle(name="ModernSectionTitleFinal", parent=body_bold, textColor=color_principal, fontSize=13, leading=16)
    company_name_style = ParagraphStyle(name="ModernCompanyNameFinal", parent=body_bold, fontSize=11.6, leading=13.2)
    company_logo_fallback_style = ParagraphStyle(
        name="ModernLogoFallbackFinal",
        parent=body_bold_blue,
        fontSize=15,
        leading=17.2,
        alignment=TA_CENTER,
    )
    document_title_style = ParagraphStyle(
        name="ModernDocumentTitleFinal",
        parent=body_bold_center,
        fontSize=11.8,
        leading=14.2,
        textColor=color_principal,
    )
    document_number_style = ParagraphStyle(
        name="ModernDocumentNumberFinal",
        parent=body_bold_center,
        fontSize=15.5,
        leading=18,
        textColor=colors.white,
    )
    strip_label_style = ParagraphStyle(name="ModernStripLabelFinal", parent=body_bold_blue, fontSize=9.8, leading=12)
    strip_value_style = ParagraphStyle(name="ModernStripValueFinal", parent=body, fontSize=10.8, leading=12)
    table_header_style = ParagraphStyle(
        name="ModernTableHeaderFinal",
        parent=body_bold_center,
        textColor=colors.white,
        fontSize=7.45,
        leading=8.91,
    )
    detail_money_style = ParagraphStyle(
        name="ModernDetailMoneyFinal",
        parent=body_center,
        fontSize=8.1,
        leading=9.8,
    )
    amount_big_style = ParagraphStyle(
        name="ModernAmountBigFinal",
        parent=body_bold_blue,
        alignment=TA_RIGHT,
        fontSize=16.2,
        leading=15.84,
        splitLongWords=0,
        wordWrap="LTR",
    )
    totals_value_style = ParagraphStyle(
        name="ModernTotalsValueFinal",
        parent=body_right,
        fontSize=8.1,
        leading=8.28,
        splitLongWords=0,
        wordWrap="LTR",
    )
    totals_label_style = ParagraphStyle(
        name="ModernTotalsLabelFinal",
        parent=body,
        fontSize=8.1,
        leading=8.28,
    )
    totals_label_highlight_style = ParagraphStyle(
        name="ModernTotalsLabelHighlightFinal",
        parent=body_bold_blue_nobreak,
        fontSize=8.1,
        leading=8.28,
    )
    total_bar_text_style = ParagraphStyle(
        name="ModernTotalBarTextFinal",
        parent=body_bold_center,
        fontSize=8.1,
        leading=10.8,
    )
    footer_title_style = ParagraphStyle(name="ModernFooterTitleFinal", parent=body_bold_blue, fontSize=10.5, leading=14)

    moneda_codigo = (parsed_xml or {}).get("currency") or _value_from_obj(document_data, "moneda", "PEN")
    simbolo = "S/" if moneda_codigo == "PEN" else "$"
    moneda_texto = "SOLES" if moneda_codigo == "PEN" else "DOLARES"

    tipo_doc_sunat = (parsed_xml or {}).get("tipo_comprobante") or _value_from_obj(document_data, "tipo_comprobante", "03")
    doc_title_str = _resolver_titulo_documento(tipo_doc_sunat, is_comprobante)
    serie = _value_from_obj(document_data, "serie", "COT")
    correlativo = _value_from_obj(document_data, "correlativo", 0)
    doc_number_str = f"{serie}-{str(correlativo).zfill(6)}" if is_comprobante else _build_quote_document_number(document_data)
    if parsed_xml and parsed_xml.get("document_id"):
        doc_number_str = parsed_xml["document_id"]

    raw_fecha = (
        (parsed_xml or {}).get("issue_date")
        or _value_from_obj(document_data, "fecha_emision", None)
        or _value_from_obj(document_data, "created_at", datetime.now())
    )
    fecha_emision = _format_date_ddmmyyyy(raw_fecha, default=datetime.now().strftime("%d/%m/%Y"))
    fecha_vencimiento = ""
    if not is_comprobante:
        fecha_emision, fecha_vencimiento = _resolve_quote_due_date_display(document_data)

    customer = (parsed_xml or {}).get("customer") or {}
    if parsed_xml:
        nombre_cliente = customer.get("name") or "Cliente General"
        tipo_doc_cliente = obtener_etiqueta_tipo_doc(customer.get("doc_type") or "0")
        nro_doc_cliente = str(customer.get("doc_number") or "")
        direccion_cliente = str(customer.get("address") or "-").replace("\n", "<br/>")
        line_context = _build_xml_line_context(parsed_xml)
        monto_en_letras_str = parsed_xml.get("amount_in_words") or ""
    else:
        client_data = _resolve_document_client_data(document_data)
        nombre_cliente = client_data["name"]
        tipo_doc_cliente = client_data["doc_type_label"]
        nro_doc_cliente = client_data["doc_number"]
        direccion_cliente = client_data["address"].replace("\n", "<br/>")
        line_context = _build_local_line_context(document_data)
        monto_en_letras_str = ""

    company_data = _resolve_company_data(document_data, tenant, parsed_xml)
    total_gravado_d = to_decimal(line_context["total_gravado"])
    total_igv_d = to_decimal(line_context["total_igv"])
    monto_total_d = to_decimal(line_context["monto_total"])
    if not monto_en_letras_str:
        monto_en_letras_str = monto_a_letras(monto_total_d, simbolo)

    header_col_1 = 8.0 * cm
    header_col_2 = 6.0 * cm
    header_col_3 = ancho_total - header_col_1 - header_col_2

    logo_block = _build_logo_block(company_data, color_principal, header_col_1, company_logo_fallback_style)
    company_name_style.fontSize = 11.8
    company_name_style.leading = 14
    body.fontSize = 9.0
    body.leading = 10.8
    body_small.fontSize = 8.0
    body_small.leading = 9.4
    body_center.fontSize = body.fontSize
    body_center.leading = body.leading

    contact_lines = []
    if company_data["phone"]:
        contact_lines.append(f"Teléfono: {company_data['phone']}")
    if company_data["email"]:
        contact_lines.append(f"Email: {company_data['email']}")

    company_rows = [
        [Paragraph(company_data["name"].upper() or "NOMBRE DEL NEGOCIO", company_name_style)],
        [""],
        [Paragraph(f"RUC {company_data['ruc']}", body)],
        [""],
        [Paragraph(company_data["address"].replace("\n", "<br/>"), body_small)],
    ]
    company_row_heights = [None, 0.4 * cm, None, 0.4 * cm, None]
    if contact_lines:
        company_rows.extend([[""], [Paragraph("<br/>".join(contact_lines), body_small)]])
        company_row_heights.extend([0.4 * cm, None])

    company_table = Table(
        company_rows,
        colWidths=[header_col_2 - 0.4 * cm],
        rowHeights=company_row_heights,
    )
    company_table.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    company_box = KeepInFrame(
        header_col_2 - 0.4 * cm,
        header_height - 18,
        [company_table],
        mode="shrink",
        hAlign="CENTER",
        vAlign="TOP",
    )

    doc_box_width = 4.9 * cm
    doc_box_height = 4.0 * cm
    doc_box = _RoundedDocumentBox(
        width=doc_box_width,
        height=doc_box_height,
        stroke_color=color_principal,
        title_paragraph=Paragraph(
            doc_title_str.replace(" ELECTRONICA", "<br/>ELECTRONICA"),
            document_title_style,
        ),
        number_paragraph=Paragraph(doc_number_str, document_number_style),
        footer_paragraph=Paragraph(f"RUC: {company_data['ruc']}", body_bold_center),
        radius=4.5,
        stroke_width=1.5,
        band_fill=color_principal,
    )

    logo_box = KeepInFrame(
        header_col_1 - 0.4 * cm,
        header_height - 18,
        [logo_block],
        mode="shrink",
        hAlign="CENTER",
        vAlign="MIDDLE",
    )

    header_inner = Table(
        [[logo_box, company_box, doc_box]],
        colWidths=[header_col_1, header_col_2, header_col_3],
        rowHeights=[header_height],
    )
    header_inner.setStyle(
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
    header_inner = _HeaderDividerBox(
        child=header_inner,
        width=ancho_total,
        height=header_height,
        divider_positions=[header_col_1, header_col_1 + header_col_2],
        divider_color=color_borde,
        divider_height=4 * cm,
        stroke_width=1,
    )
    header_container = _RoundedContainerBox(
        child=header_inner,
        width=ancho_total,
        height=header_height,
        stroke_color=color_borde,
        radius=4.5,
        stroke_width=1,
        padding=0,
    )
    header_container.hAlign = "LEFT"

    color_strip = color_principal
    strip_label_style.textColor = color_strip
    strip = Table(
        [[
            Paragraph("Fecha de emisión:", strip_label_style),
            Paragraph(fecha_emision, strip_value_style),
            "",
            Paragraph("Moneda:", strip_label_style),
            Paragraph(moneda_texto, strip_value_style),
        ]],
        colWidths=[
            ancho_total * 0.19,
            ancho_total * 0.18,
            ancho_total * 0.36,
            ancho_total * 0.12,
            ancho_total * 0.15,
        ],
    )
    strip.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, -1), 1.6, color_strip),
                ("LINEBELOW", (0, 0), (-1, -1), 1.6, color_strip),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0.22 * cm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0.22 * cm),
                ("ALIGN", (0, 0), (1, 0), "LEFT"),
                ("ALIGN", (3, 0), (4, 0), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    client_title = "DATOS DEL RECEPTOR" if is_comprobante else "DATOS DEL CLIENTE"
    client_card = Table(
        [
            [Paragraph(client_title, section_title), ""],
            [Paragraph("<b>Señores:</b>", body_bold), Paragraph(nombre_cliente, body)],
            [Paragraph(f"<b>{tipo_doc_cliente}:</b>", body_bold), Paragraph(nro_doc_cliente or "-", body)],
            [Paragraph("<b>Dirección:</b>", body_bold), Paragraph(direccion_cliente, body)],
        ],
        colWidths=[ancho_total * 0.12, ancho_total * 0.88],
    )
    client_card.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (1, 0)),
                ("BOX", (0, 0), (-1, -1), 1, color_borde),
                ("BACKGROUND", (0, 0), (-1, 0), color_suave),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 1, color_borde),
                ("TOPPADDING", (0, 1), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 10),
            ]
        )
    )

    client_label_style = ParagraphStyle(
        "PdfClientLabel",
        parent=body_bold,
        fontSize=8.64,
        leading=7.38,
        textColor=colors.HexColor("#1F2633"),
    )
    client_value_style = ParagraphStyle(
        "PdfClientValue",
        parent=body,
        fontSize=8.73,
        leading=7.65,
        textColor=colors.HexColor("#202A39"),
    )
    detail_text_style = ParagraphStyle(
        "PdfDetailText",
        parent=body,
        fontSize=7.86,
        leading=9.56,
        textColor=colors.HexColor("#202A39"),
    )
    detail_center_style = ParagraphStyle(
        "PdfDetailCenter",
        parent=detail_text_style,
        alignment=TA_CENTER,
    )
    detail_money_style = ParagraphStyle(
        "PdfDetailMoney",
        parent=detail_text_style,
        alignment=TA_CENTER,
    )
    client_rows = [
        [
            Paragraph("<b>Se&#241;ores:</b>", client_label_style),
            Paragraph(nombre_cliente, client_value_style),
            Paragraph("<b>Emisi&#243;n:</b>", client_label_style),
            Paragraph(fecha_emision, client_value_style),
        ],
    ]
    if is_comprobante:
        client_rows.extend(
            [
                [
                    Paragraph(f"<b>{tipo_doc_cliente}:</b>", client_label_style),
                    Paragraph(nro_doc_cliente or "-", client_value_style),
                    Paragraph("<b>Moneda:</b>", client_label_style),
                    Paragraph(moneda_texto, client_value_style),
                ],
                [
                    Paragraph("<b>Direcci&#243;n:</b>", client_label_style),
                    Paragraph(direccion_cliente, client_value_style),
                    "",
                    "",
                ],
            ]
        )
    else:
        client_rows.extend(
            [
                [
                    Paragraph(f"<b>{tipo_doc_cliente}:</b>", client_label_style),
                    Paragraph(nro_doc_cliente or "-", client_value_style),
                    Paragraph("<b>Vencimiento:</b>", client_label_style),
                    Paragraph(fecha_vencimiento, client_value_style),
                ],
                [
                    Paragraph("<b>Direcci&#243;n:</b>", client_label_style),
                    Paragraph(direccion_cliente, client_value_style),
                    Paragraph("<b>Moneda:</b>", client_label_style),
                    Paragraph(moneda_texto, client_value_style),
                ],
            ]
        )
    client_body = Table(
        client_rows,
        colWidths=[2.4 * cm, 8.1 * cm, 2.5 * cm, ancho_total - (2.4 * cm) - (8.1 * cm) - (2.5 * cm)],
    )
    client_body.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (0, -1), 6),
                ("RIGHTPADDING", (0, 0), (0, -1), 8),
                ("LEFTPADDING", (1, 0), (1, -1), 6),
                ("RIGHTPADDING", (1, 0), (1, -1), 8),
                ("LEFTPADDING", (2, 0), (2, 1), 12),
                ("RIGHTPADDING", (2, 0), (2, 1), 6),
                ("LEFTPADDING", (3, 0), (3, 1), 6),
                ("RIGHTPADDING", (3, 0), (3, 1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (2, 0), (2, 1), "LEFT"),
                ("LINEABOVE", (0, 0), (-1, 0), 1.6, color_strip),
                ("LINEBELOW", (0, 2), (-1, 2), 1.6, color_strip),
            ]
        )
    )
    client_card = Table([[client_body]], colWidths=[ancho_total])
    client_card.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    client_card.hAlign = "LEFT"

    detail_rows = [[
        Paragraph("N°", table_header_style),
        Paragraph("DESCRIPCIÓN", table_header_style),
        Paragraph("UNIDAD", table_header_style),
        Paragraph("CANTIDAD", table_header_style),
        Paragraph("V. UNITARIO<br/>(S/ sin IGV)", table_header_style),
        Paragraph("IGV<br/>(18%)", table_header_style),
        Paragraph("IMPORTE<br/>(S/ con IGV)", table_header_style),
    ]]
    for item_data in line_context["lines"]:
        detail_rows.append(
            [
                Paragraph(str(item_data.get("indice") or ""), body_center),
                Paragraph(item_data["descripcion"], body),
                Paragraph(_display_unit_code(item_data.get("unidad")), body_center),
                Paragraph(_format_quantity(item_data["cantidad"]), body_center),
                Paragraph(_format_money(simbolo, item_data.get("valor_unitario") or 0), body_center),
                Paragraph(_format_money(simbolo, item_data["igv_item"]), body_center),
                Paragraph(_format_money(simbolo, item_data["precio_total_item"]), body_center),
            ]
        )

    detail_table = Table(
        detail_rows,
        colWidths=[
            ancho_total * 0.065,
            ancho_total * 0.32,
            ancho_total * 0.10,
            ancho_total * 0.115,
            ancho_total * 0.135,
            ancho_total * 0.115,
            ancho_total * 0.15,
        ],
        repeatRows=1,
    )
    detail_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), color_principal),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.8, color_borde),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (2, 1), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    detail_rows = [[
        Paragraph("N°", table_header_style),
        Paragraph("CANTIDAD", table_header_style),
        Paragraph("CÓDIGO", table_header_style),
        Paragraph("DESCRIPCIÓN", table_header_style),
        Paragraph("V/U", table_header_style),
        Paragraph("P/U", table_header_style),
        Paragraph("SUBTOTAL", table_header_style),
        Paragraph("TOTAL", table_header_style),
    ]]
    for item_data in line_context["lines"]:
        detail_rows.append(
            [
                Paragraph(str(item_data.get("indice") or ""), detail_center_style),
                Paragraph(f"{_format_quantity(item_data['cantidad'])} {_display_unit_code(item_data.get('unidad'))}", detail_center_style),
                Paragraph(f"<nobr>{_html_escape(item_data.get('codigo') or '-')}</nobr>", detail_center_style),
                Paragraph(item_data["descripcion"], detail_text_style),
                Paragraph(_format_detail_money(simbolo, item_data.get("valor_unitario") or 0), detail_money_style),
                Paragraph(_format_detail_money(simbolo, item_data.get("p_unit_con_igv") or 0), detail_money_style),
                Paragraph(_format_detail_money(simbolo, item_data.get("subtotal_item") or 0), detail_money_style),
                Paragraph(_format_detail_money(simbolo, item_data["precio_total_item"]), detail_money_style),
            ]
        )

    detail_col_widths = _build_quote_detail_col_widths(
        line_context["lines"],
        ancho_total,
        header_style=table_header_style,
        text_style=detail_text_style,
        money_style=detail_money_style,
        symbol=simbolo,
    )

    detail_table = Table(
        detail_rows,
        colWidths=detail_col_widths,
        repeatRows=1,
    )
    detail_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), color_principal),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("INNERGRID", (0, 0), (-1, -1), 0.8, color_borde),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, color_borde),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (2, -1), "CENTER"),
                ("ALIGN", (4, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    detail_table = _AutoRoundedContainerBox(
        child=detail_table,
        width=ancho_total,
        stroke_color=color_borde,
        radius=4.5,
        stroke_width=1,
        padding=0,
    )
    detail_table.hAlign = "LEFT"

    totals_label_1 = "<nobr>OP. GRAVADAS:</nobr>"
    totals_label_2 = "<nobr>IGV (18%):</nobr>"
    totals_label_3 = "IMPORTE&nbsp;TOTAL:"
    totals_value_1 = _format_money_inline(simbolo, total_gravado_d)
    totals_value_2 = _format_money_inline(simbolo, total_igv_d)
    totals_value_3 = _format_money_inline(simbolo, monto_total_d)

    label_width_px = max(
        stringWidth("OP. GRAVADAS:", body.fontName, body.fontSize),
        stringWidth("IGV (18%):", body.fontName, body.fontSize),
        stringWidth("IMPORTE TOTAL:", body_bold_blue.fontName, body_bold_blue.fontSize),
    )
    value_width_px = max(
        stringWidth(totals_value_1.replace("&nbsp;", " "), totals_value_style.fontName, totals_value_style.fontSize),
        stringWidth(totals_value_2.replace("&nbsp;", " "), totals_value_style.fontName, totals_value_style.fontSize),
        stringWidth(totals_value_3.replace("&nbsp;", " "), amount_big_style.fontName, amount_big_style.fontSize),
    )
    # Account for cell padding so the label/value widths remain truly usable.
    totals_label_width = label_width_px + 28
    totals_value_width = value_width_px + 28
    totals_box_width = min(totals_label_width + totals_value_width + 24, ancho_total * 0.74)
    totals_value_col_width = totals_box_width - totals_label_width

    totals_divider = _InsetHorizontalRule(totals_box_width, color_borde, inset=0.3 * cm, stroke_width=1)
    totals_box = Table(
        [
            [Paragraph(totals_label_1, totals_label_style), Paragraph(totals_value_1, totals_value_style)],
            [Paragraph(totals_label_2, totals_label_style), Paragraph(totals_value_2, totals_value_style)],
            [totals_divider, ""],
            [Paragraph(totals_label_3, totals_label_highlight_style), Paragraph(totals_value_3, amount_big_style)],
        ],
        colWidths=[totals_label_width, totals_value_col_width],
    )
    totals_box.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("SPAN", (0, 2), (1, 2)),
                ("LEFTPADDING", (0, 0), (0, -1), 12),
                ("RIGHTPADDING", (0, 0), (0, -1), 8),
                ("LEFTPADDING", (1, 0), (1, -1), 8),
                ("RIGHTPADDING", (1, 0), (1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 2), (1, 2), 0),
                ("RIGHTPADDING", (0, 2), (1, 2), 0),
                ("TOPPADDING", (0, 2), (1, 2), 4),
                ("BOTTOMPADDING", (0, 2), (1, 2), 4),
                ("TOPPADDING", (0, 3), (1, 3), 3),
                ("BOTTOMPADDING", (0, 3), (1, 3), 11),
            ]
        )
    )
    totals_box = _AutoRoundedContainerBox(
        child=totals_box,
        width=totals_box_width,
        stroke_color=color_borde,
        radius=4.5,
        stroke_width=1,
        padding=0,
    )
    totals_row = Table([["", totals_box]], colWidths=[ancho_total - totals_box_width, totals_box_width])
    totals_row.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (1, 0), (1, 0), "TOP"),
            ]
        )
    )

    total_bar = Table(
        [
            [Paragraph(monto_en_letras_str, total_bar_text_style)],
        ],
        colWidths=[ancho_total],
    )
    total_bar.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color_suave),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    total_bar = _AutoRoundedContainerBox(
        child=total_bar,
        width=ancho_total,
        stroke_color=color_borde,
        radius=4.5,
        stroke_width=1,
        padding=0,
    )

    quote_notes_elements = []
    payment_methods_text = _build_payment_methods_text(
        company_data["bank_accounts"],
        beneficiary_name=company_data["name"],
    )
    if not is_comprobante:
        quote_notes_elements.extend(_build_observation_paragraphs(document_data, tenant, body))
        if payment_methods_text:
            quote_notes_elements.append(Paragraph(payment_methods_text, body))

    qr_col_width = ancho_total * 0.22
    if is_comprobante:
        qr_content = _build_qr_content(
            document_data,
            f"{company_data['ruc']}|{tipo_doc_sunat}|{serie}|{correlativo}|{total_igv_d}|{monto_total_d}|{fecha_emision}|{tipo_doc_cliente}|{nro_doc_cliente}",
        )
        qr_flowable = _build_qr_flowable(document_data, qr_content, qr_col_width)
        qr_title = Paragraph(
            f"Representación impresa de la {doc_title_str}.",
            footer_title_style,
        )
        qr_body = Paragraph(
            "El usuario puede consultar su validez en SUNAT Virtual:",
            body,
        )
        qr_link = Paragraph("www.sunat.gob.pe", body_bold_blue)
        qr_summary_text = _resolve_qr_visible_summary(document_data)
        bottom_left_text = "Puedes descargar el XML, CDR y representación impresa desde nuestro portal."
    else:
        wallet = _pick_wallet_payment_method(company_data["bank_accounts"])
        qr_flowable = _build_uploaded_payment_qr_flowable(
            company_data["bank_accounts"],
            1.75 * inch,
            qr_col_width,
        )
        if not qr_flowable:
            qr_content, wallet = _build_quote_wallet_qr_content(company_data["bank_accounts"], company_data["name"])
            qr_flowable = _build_generated_qr_flowable(qr_content, 1.75 * inch, qr_col_width)
        provider = (wallet or {}).get("proveedor") or "billetera digital"
        qr_title = Paragraph(
            f"Escanea para pagar con {provider}.",
            footer_title_style,
        )
        qr_lines = []
        if wallet and wallet.get("titular"):
            qr_lines.append(f"Titular: {wallet['titular']}")
        if wallet and wallet.get("numero"):
            qr_lines.append(f"Número: {wallet['numero']}")
        if wallet and wallet.get("nota"):
            qr_lines.append(wallet["nota"])
        qr_body = Paragraph("<br/>".join(qr_lines) if qr_lines else "Usa la billetera digital configurada por el emisor.", body)
        qr_link = Paragraph("", body)
        qr_summary_text = None
        bottom_left_text = "Condiciones sujetas a confirmación comercial."

    qr_right_rows = [[qr_title], [qr_body]]
    if is_comprobante:
        qr_right_rows.append([qr_link])
        if qr_summary_text:
            qr_right_rows.append([Paragraph(f"Valor resumen: {qr_summary_text}", body_small)])
    else:
        if qr_link.getPlainText().strip():
            qr_right_rows.append([qr_link])
        for paragraph in quote_notes_elements:
            qr_right_rows.append([paragraph])

    qr_right = Table(
        qr_right_rows,
        colWidths=[ancho_total * 0.58],
    )
    qr_right.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    qr_block = Table(
        [[qr_flowable, "", qr_right]],
        colWidths=[qr_col_width, ancho_total * 0.03, ancho_total * 0.75],
    )
    qr_block.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, -1), 1.5, color_principal),
                ("LINEBELOW", (0, 0), (-1, -1), 1.5, color_principal),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    qr_block = _AutoVerticalDividerBox(
        child=qr_block,
        width=ancho_total,
        divider_positions=[qr_col_width],
        divider_color=color_borde,
        inset_y=0.3 * cm,
        stroke_width=1,
    )

    footer_contact = _build_footer_contact_text(company_data)
    footer_table = Table(
        [[Paragraph(bottom_left_text, body_small), Paragraph(footer_contact, body_small)]],
        colWidths=[ancho_total * 0.62, ancho_total * 0.38],
    )
    footer_table.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]
        )
    )

    footer_block = Table(
        [[qr_block], [footer_table]],
        colWidths=[ancho_total],
        splitByRow=0,
    )
    footer_block.setStyle(
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

    elementos = [
        header_container,
        Spacer(1, 14),
        client_card,
        Spacer(1, 14),
        detail_table,
        Spacer(1, 14),
        totals_row,
        Spacer(1, 14),
        total_bar,
    ]

    usable_height = A4[1] - doc.topMargin - doc.bottomMargin
    consumed_height = sum(_measure_flowable_height(flowable, ancho_total) for flowable in elementos)
    footer_height = _measure_flowable_height(footer_block, ancho_total)
    remaining_height = max(0, usable_height - consumed_height - footer_height - 28)

    elementos += [Spacer(1, remaining_height), footer_block]

    try:
        doc.build(elementos)
    except Exception as build_err:
        print(f"ERROR: Fallo la construccion del PDF moderno: {build_err}")
        traceback.print_exc()
        raise

    buffer.seek(0)
    return buffer


def create_pdf_buffer(document_data, tenant: models.Tenant, document_type: str):
    return _build_modern_pdf_buffer(document_data, tenant, is_comprobante=(document_type == "comprobante"))


def generar_pdf_cotizacion(cotizacion: models.Cotizacion, tenant: models.Tenant):
    return create_pdf_buffer(cotizacion, tenant, "cotizacion")


def create_comprobante_pdf(comprobante, tenant: models.Tenant):
    return create_pdf_buffer(comprobante, tenant, "comprobante")
