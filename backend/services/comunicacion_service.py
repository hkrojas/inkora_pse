import urllib.parse

from services.phone_validation import normalize_peru_mobile, validate_optional_peru_mobile


DEFAULT_WHATSAPP_TEMPLATE = (
    "Hola {cliente}, le compartimos la cotizacion {numero} por {moneda} {total}.\n\n"
    "Puede descargar el documento aqui: {url}\n\n"
    "PIN de seguridad: {pin}"
)

DEFAULT_EMAIL_SUBJECT_TEMPLATE = "Cotizacion {numero} - {empresa}"
DEFAULT_EMAIL_BODY_TEMPLATE = (
    "Estimado cliente,\n\n"
    "Le enviamos el enlace para descargar la cotizacion {numero}.\n\n"
    "Enlace de descarga:\n{url}\n\n"
    "PIN de seguridad: {pin}\n\n"
    "Quedamos atentos a sus comentarios.\n\n"
    "Saludos cordiales,\n{empresa}"
)


def _get_communication_templates(tenant) -> dict:
    for method in getattr(tenant, "bank_accounts", None) or []:
        if isinstance(method, dict) and method.get("tipo") == "communication_templates":
            return method
    return {}


def _document_number(cotizacion) -> str:
    serie = getattr(cotizacion, "serie", None)
    correlativo = getattr(cotizacion, "correlativo", None)
    if serie and correlativo is not None:
        return f"{serie}-{str(correlativo).zfill(6)}"
    return f"#{getattr(cotizacion, 'id', '')}".strip()


def _template_context(cotizacion, url_publica: str, tenant=None) -> dict:
    cliente = getattr(cotizacion, "cliente", None)
    simbolo = "S/" if getattr(cotizacion, "moneda", None) == "PEN" else "$"
    pin = getattr(cliente, "numero_documento", None) or "N/A"
    return {
        "numero": _document_number(cotizacion),
        "total": f"{float(getattr(cotizacion, 'total_venta', 0) or 0):.2f}",
        "moneda": simbolo,
        "url": url_publica,
        "pin": pin,
        "cliente": getattr(cliente, "razon_social", None) or "cliente",
        "empresa": getattr(tenant, "business_name", None) or "Inkora",
    }


def _render_template(template: str, context: dict) -> str:
    rendered = str(template or "")
    for key, value in context.items():
        rendered = rendered.replace(f"{{{key}}}", str(value))
    return rendered


def generar_link_whatsapp(cotizacion, telefono: str, url_publica: str, tenant=None) -> str:
    """Genera un link de wa.me pre-llenado con mensaje formal y PIN (Fase 3)."""
    if not telefono:
        return ""

    telefono_normalizado = normalize_peru_mobile(telefono)
    if validate_optional_peru_mobile(telefono_normalizado, "Telefono / WhatsApp"):
        return ""

    telefono_limpio = f"51{telefono_normalizado}"
    templates = _get_communication_templates(tenant)
    template = templates.get("whatsapp_message") or DEFAULT_WHATSAPP_TEMPLATE
    mensaje = _render_template(template, _template_context(cotizacion, url_publica, tenant))

    mensaje_encoded = urllib.parse.quote(mensaje)
    return f"https://wa.me/{telefono_limpio}?text={mensaje_encoded}"


def generar_link_mailto(cotizacion, email_cliente: str, url_publica: str, tenant) -> str:
    """Genera un enlace mailto pre-llenado con asunto, cuerpo formal y PIN (Fase 3)."""
    if not email_cliente:
        return ""

    templates = _get_communication_templates(tenant)
    context = _template_context(cotizacion, url_publica, tenant)
    asunto = _render_template(
        templates.get("email_subject") or DEFAULT_EMAIL_SUBJECT_TEMPLATE,
        context,
    )
    cuerpo = _render_template(
        templates.get("email_body") or DEFAULT_EMAIL_BODY_TEMPLATE,
        context,
    )

    asunto_encoded = urllib.parse.quote(asunto)
    cuerpo_encoded = urllib.parse.quote(cuerpo)

    return f"mailto:{email_cliente}?subject={asunto_encoded}&body={cuerpo_encoded}"
