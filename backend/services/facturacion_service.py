import base64
import decimal
import json
import time
from datetime import datetime, timedelta

import requests
from sqlalchemy.orm import Session

import models
from config import settings
from services import calculations
from services import fiscal_xml_service
from services.quote_observation_service import observation_lines_to_plain_text
from tenant_access import (
    get_apisperu_token as _get_apisperu_token,
    get_company_address as _get_company_address,
    get_company_bank_accounts as _get_company_bank_accounts,
    get_company_name as _get_company_name,
    get_company_ruc as _get_company_ruc,
)


class FacturacionException(Exception):
    """Excepcion para errores de negocio en facturacion."""


class SUNATDecimalEncoder(json.JSONEncoder):
    """Codificador JSON para serializar Decimal sin perder precision fiscal."""

    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super().default(obj)


UNIDADES = {
    0: "",
    1: "UN",
    2: "DOS",
    3: "TRES",
    4: "CUATRO",
    5: "CINCO",
    6: "SEIS",
    7: "SIETE",
    8: "OCHO",
    9: "NUEVE",
}
DECENAS = {
    10: "DIEZ",
    11: "ONCE",
    12: "DOCE",
    13: "TRECE",
    14: "CATORCE",
    15: "QUINCE",
    20: "VEINTE",
    30: "TREINTA",
    40: "CUARENTA",
    50: "CINCUENTA",
    60: "SESENTA",
    70: "SETENTA",
    80: "OCHENTA",
    90: "NOVENTA",
}
CENTENAS = {
    100: "CIEN",
    200: "DOSCIENTOS",
    300: "TRESCIENTOS",
    400: "CUATROCIENTOS",
    500: "QUINIENTOS",
    600: "SEISCIENTOS",
    700: "SETECIENTOS",
    800: "OCHOCIENTOS",
    900: "NOVECIENTOS",
}

DEFAULT_UBIGEO = "150101"
DEFAULT_PROVINCIA = "LIMA"
DEFAULT_DEPARTAMENTO = "LIMA"
DEFAULT_DISTRITO = "LIMA"
DEFAULT_TIMEOUT_SECONDS = 30
ASYNC_STATUS_MAX_ATTEMPTS = 5
ASYNC_STATUS_RETRY_SECONDS = 2


def numero_a_letras(numero):
    parte_entera = int(numero)
    parte_decimal = int(round((numero - parte_entera) * 100))
    letras = convert_number(parte_entera)
    return f"SON: {letras} CON {parte_decimal:02d}/100 SOLES"


def convert_number(n):
    if n == 0:
        return "CERO"
    if n < 10:
        return UNIDADES[n]
    if n < 20:
        return DECENAS.get(n, "DIECI" + UNIDADES[n - 10])
    if n < 30:
        return "VEINTI" + UNIDADES[n - 20] if n > 20 else "VEINTE"
    if n < 100:
        decena, unidad = divmod(n, 10)
        return DECENAS[decena * 10] + (" Y " + UNIDADES[unidad] if unidad > 0 else "")
    if n < 1000:
        if n == 100:
            return "CIEN"
        centena, resto = divmod(n, 100)
        prefijo = CENTENAS[centena * 100] if centena > 1 else "CIENTO"
        return prefijo + (" " + convert_number(resto) if resto > 0 else "")
    if n < 1000000:
        miles, resto = divmod(n, 1000)
        prefijo = convert_number(miles) + " MIL" if miles > 1 else "MIL"
        return prefijo + (" " + convert_number(resto) if resto > 0 else "")
    return "NUMERO DEMASIADO GRANDE"


def obtener_tipo_documento_codigo(tipo: str) -> str:
    if not tipo:
        return "1"

    tipo_normalizado = str(tipo).strip().upper()
    if tipo_normalizado.isdigit():
        return tipo_normalizado

    mapping = {
        "DNI": "1",
        "DOC. TRIB. NO DOM. SIN RUC": "0",
        "RUC": "6",
        "CE": "4",
        "CARNET DE EXTRANJERIA": "4",
        "PASAPORTE": "7",
        "PAS": "7",
        "CEDULA DIPLOMATICA": "A",
    }
    return mapping.get(tipo_normalizado, "1")


def _decode_jwt_payload_without_verification(token: str) -> dict:
    parts = (token or "").split(".")
    if len(parts) < 2 or not parts[1]:
        return {}

    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(f"{payload}{padding}".encode("utf-8"))
        data = json.loads(decoded.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except (ValueError, TypeError, json.JSONDecodeError):
        return {}


def _extract_token_company_ruc(token: str) -> str | None:
    payload = _decode_jwt_payload_without_verification(token)
    company_ruc = payload.get("company")
    if company_ruc is None:
        return None
    company_ruc = "".join(ch for ch in str(company_ruc) if ch.isdigit())
    return company_ruc or None


def _get_api_base_url(user) -> str:
    tenant = getattr(user, "tenant", None)
    base_url = (
        getattr(tenant, "apisperu_url", None)
        or getattr(user, "apisperu_url", None)
        or settings.API_URL
    )
    base_url = (base_url or "").strip().rstrip("/")
    if not base_url:
        raise FacturacionException("No hay URL de ApisPeru configurada.")
    return base_url


def _safe_json(response) -> dict:
    try:
        data = response.json()
        return data if isinstance(data, dict) else {"data": data}
    except ValueError:
        return {"raw": response.text[:4000]}


def _stringify_error_candidate(candidate) -> str:
    if candidate is None:
        return ""
    if isinstance(candidate, str):
        return candidate.strip()
    if isinstance(candidate, list):
        parts = []
        for entry in candidate:
            if isinstance(entry, dict):
                field = entry.get("field")
                message = entry.get("message") or entry.get("description")
                if field and message:
                    parts.append(f"{field}: {message}")
                elif message:
                    parts.append(str(message))
                else:
                    parts.append(json.dumps(entry, ensure_ascii=False))
            else:
                parts.append(str(entry))
        return "; ".join(part for part in parts if part)
    if isinstance(candidate, dict):
        code = candidate.get("code")
        message = candidate.get("message") or candidate.get("description") or candidate.get("error")
        if code and message:
            return f"[{code}] {message}"
        if message:
            return str(message)
        return json.dumps(candidate, ensure_ascii=False)
    return str(candidate)


def _extract_provider_error_message(data: dict) -> str:
    sunat_response = data.get("sunatResponse") or data.get("sunat_response") or {}
    candidates = [
        sunat_response.get("error"),
        data.get("error"),
        data.get("errors"),
        sunat_response.get("message"),
        data.get("message"),
        data.get("raw"),
    ]
    for candidate in candidates:
        text = _stringify_error_candidate(candidate)
        if text:
            return text
    return "Respuesta no interpretable del proveedor fiscal."


def _normalize_links(data: dict) -> dict:
    candidate_links = data.get("links") or {}
    if not candidate_links and isinstance(data.get("sunat_response"), dict):
        candidate_links = data["sunat_response"].get("links") or {}
    if not candidate_links and isinstance(data.get("sunatResponse"), dict):
        candidate_links = data["sunatResponse"].get("links") or {}

    normalized = {}
    for key in ("xml", "pdf", "cdr"):
        value = candidate_links.get(key)
        if isinstance(value, str) and value.strip().lower().startswith(("http://", "https://")):
            normalized[key] = value.strip()
    return normalized


def _fetch_sale_qr_svg(user, xml_content: str | None) -> tuple[dict | None, str | None]:
    qr_payload = fiscal_xml_service.build_sale_qr_payload_from_xml(xml_content)
    if not qr_payload or not all(
        qr_payload.get(key)
        for key in ("ruc", "tipo", "serie", "numero", "emision", "clienteTipo", "clienteNumero")
    ):
        return qr_payload, None

    token = _get_apisperu_token(user)
    if not token:
        return qr_payload, None

    url = f"{_get_api_base_url(user)}/sale/qr"
    try:
        response = requests.post(
            url,
            data=json.dumps(qr_payload, cls=SUNATDecimalEncoder),
            headers=_provider_request_headers(token),
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        return qr_payload, None

    content_type = (response.headers.get("Content-Type") or "").lower()
    if response.status_code >= 400 or "svg" not in content_type:
        return qr_payload, None

    return qr_payload, response.text


def _attach_sale_artifacts(result: dict, user) -> dict:
    if not result.get("success"):
        return result

    xml_content = result.get("xml")
    qr_payload, qr_svg = _fetch_sale_qr_svg(user, xml_content)
    if qr_payload:
        result["qr_payload"] = qr_payload
    if qr_svg:
        result["qr_svg"] = qr_svg
    return result


def _build_address_payload(
    direccion: str | None,
    ubigeo: str | None = None,
    provincia: str | None = None,
    departamento: str | None = None,
    distrito: str | None = None,
) -> dict:
    return {
        "direccion": (direccion or "Direccion no declarada").strip(),
        "provincia": (provincia or DEFAULT_PROVINCIA).strip(),
        "departamento": (departamento or DEFAULT_DEPARTAMENTO).strip(),
        "distrito": (distrito or DEFAULT_DISTRITO).strip(),
        "ubigueo": (ubigeo or DEFAULT_UBIGEO).strip(),
    }


def _build_company_payload(user) -> dict:
    company_ruc = _get_company_ruc(user)
    company_name = _get_company_name(user)
    company_address = _get_company_address(user)

    if not company_ruc:
        raise FacturacionException("Emisor sin RUC configurado.")
    if not company_name:
        raise FacturacionException("Emisor sin razon social configurada.")

    return {
        "ruc": company_ruc,
        "razonSocial": company_name,
        "nombreComercial": company_name,
        "address": _build_address_payload(company_address),
    }


def _build_client_payload(cliente) -> dict:
    if not cliente:
        raise FacturacionException("Documento sin cliente asociado.")

    numero_documento = str(getattr(cliente, "numero_documento", "") or "").strip()
    if not numero_documento:
        raise FacturacionException("El cliente no tiene numero de documento configurado.")

    razon_social = getattr(cliente, "razon_social", None) or getattr(cliente, "nombre_comercial", None) or "-"
    return {
        "tipoDoc": obtener_tipo_documento_codigo(getattr(cliente, "tipo_documento", None)),
        "numDoc": numero_documento,
        "rznSocial": razon_social,
        "address": _build_address_payload(
            getattr(cliente, "direccion", None),
            getattr(cliente, "ubigeo", None),
        ),
    }


def _current_issue_datetime(value: datetime | None = None, *, plus_minutes: int = 0) -> str:
    issued_at = value or datetime.now().astimezone()
    if issued_at.tzinfo is None:
        issued_at = issued_at.astimezone()
    if plus_minutes:
        issued_at = issued_at + timedelta(minutes=plus_minutes)
    return issued_at.replace(microsecond=0).isoformat()


def _build_batch_correlativo() -> str:
    now = datetime.now()
    seconds_of_day = now.hour * 3600 + now.minute * 60 + now.second
    return str(seconds_of_day).zfill(5)


def _document_number(documento) -> str:
    serie = getattr(documento, "serie", None)
    correlativo = getattr(documento, "correlativo", None)
    if not serie or correlativo is None:
        return "-"
    return f"{serie}-{str(correlativo).zfill(6)}"


def _sync_invoice_totals(payload: dict) -> dict:
    total_gravada = calculations.redondear(payload.get("mtoOperGravadas", 0))
    total_igv = calculations.redondear(payload.get("mtoIGV", payload.get("totalImpuestos", 0)))
    total_venta = calculations.redondear(
        payload.get("mtoImpVenta", payload.get("mtoImporteTotal", payload.get("subTotal", 0)))
    )

    payload["mtoOperGravadas"] = total_gravada
    payload["mtoIGV"] = total_igv
    payload["valorVenta"] = total_gravada
    payload["totalImpuestos"] = total_igv
    payload["subTotal"] = total_venta
    payload["mtoImpVenta"] = total_venta
    payload["mtoImporteTotal"] = total_venta
    return payload


def _construir_items_payload(items):
    items_payload = []
    totales = {
        "gravada": calculations.Decimal("0.00"),
        "igv": calculations.Decimal("0.00"),
        "venta": calculations.Decimal("0.00"),
    }

    for index, item in enumerate(items, start=1):
        calc = calculations.calcular_item(item.cantidad, item.precio_unitario)
        unidad = getattr(item, "unidad_medida", None) or calc["unidad_medida"]
        afectacion = getattr(item, "tipo_afectacion_igv", None) or calc["tipo_afectacion_igv"]
        codigo_producto = getattr(item, "codigo_producto", None) or getattr(item, "producto_id", None)
        if codigo_producto:
            codigo_producto = f"PROD-{codigo_producto}"
        else:
            codigo_producto = f"ITEM-{index:03d}"

        totales["gravada"] += calc["total_base_igv"]
        totales["igv"] += calc["total_igv"]
        totales["venta"] += calc["total_item"]

        items_payload.append(
            {
                "codProducto": codigo_producto,
                "unidad": unidad,
                "descripcion": item.descripcion,
                "cantidad": calc["cantidad"],
                "mtoValorUnitario": calc["valor_unitario"],
                "mtoValorVenta": calc["total_base_igv"],
                "mtoBaseIgv": calc["total_base_igv"],
                "porcentajeIgv": 18,
                "igv": calc["total_igv"],
                "tipAfeIgv": afectacion,
                "totalImpuestos": calc["total_igv"],
                "mtoPrecioUnitario": calc["precio_unitario"],
            }
        )

    return items_payload, {key: calculations.redondear(value) for key, value in totales.items()}


def _resolve_tipo_operacion(tipo_doc_comprobante: str, tipo_operacion_override: str | None = None) -> str:
    if tipo_operacion_override:
        return str(tipo_operacion_override).strip()
    return "0101"


def _build_payment_terms(cotizacion, moneda: str, monto_total):
    condicion_pago = str(getattr(cotizacion, "condicion_pago", "") or "").strip().lower()
    if not condicion_pago or condicion_pago == "contado":
        return {
            "formaPago": {
                "moneda": moneda,
                "tipo": "Contado",
            },
            "cuotas": None,
        }

    fecha_vencimiento = getattr(cotizacion, "fecha_vencimiento", None)
    forma_pago = {
        "moneda": moneda,
        "tipo": "Credito",
        "monto": calculations.redondear(monto_total),
    }

    cuotas = None
    if fecha_vencimiento:
        cuotas = [
            {
                "moneda": moneda,
                "monto": calculations.redondear(monto_total),
                "fechaPago": _current_issue_datetime(fecha_vencimiento),
            }
        ]

    return {"formaPago": forma_pago, "cuotas": cuotas}


def _base_payload(cotizacion, user, tipo_doc_comprobante, *, tipo_operacion_override: str | None = None):
    cliente = cotizacion.cliente
    if not cliente:
        raise FacturacionException("Cotizacion sin cliente.")
    if not cotizacion.items:
        raise FacturacionException("El documento no tiene items para emitir.")

    items_payload, totales = _construir_items_payload(cotizacion.items)
    fecha_emision = _current_issue_datetime(getattr(cotizacion, "fecha_emision", None))
    leyenda_monto = numero_a_letras(totales["venta"])

    payload = {
        "ublVersion": "2.1",
        "tipoDoc": tipo_doc_comprobante,
        "fechaEmision": fecha_emision,
        "tipoMoneda": getattr(cotizacion, "moneda", None) or "PEN",
        "company": _build_company_payload(user),
        "client": _build_client_payload(cliente),
        "mtoOperGravadas": totales["gravada"],
        "mtoIGV": totales["igv"],
        "valorVenta": totales["gravada"],
        "totalImpuestos": totales["igv"],
        "subTotal": totales["venta"],
        "mtoImpVenta": totales["venta"],
        "mtoImporteTotal": totales["venta"],
        "details": items_payload,
        "legends": [{"code": "1000", "value": leyenda_monto}],
    }

    if tipo_doc_comprobante in {"01", "03"}:
        payload["tipoOperacion"] = _resolve_tipo_operacion(
            tipo_doc_comprobante,
            tipo_operacion_override=tipo_operacion_override,
        )
        payment_terms = _build_payment_terms(cotizacion, payload["tipoMoneda"], totales["venta"])
        payload["formaPago"] = payment_terms["formaPago"]
        if payment_terms["cuotas"]:
            payload["cuotas"] = payment_terms["cuotas"]
        if getattr(cotizacion, "fecha_vencimiento", None):
            payload["fecVencimiento"] = _current_issue_datetime(cotizacion.fecha_vencimiento)
        if getattr(cotizacion, "observaciones", None):
            payload["observacion"] = observation_lines_to_plain_text(cotizacion.observaciones)

    return payload, totales


UMBRAL_DETRACCION = calculations.Decimal("700.00")
PORCENTAJE_DETRACCION_IMPRENTA = calculations.Decimal("12.00")
CODIGO_DETRACCION_IMPRENTA = "012"


def _aplicar_detraccion(payload, cotizacion, user, db: Session):
    monto_total = calculations.to_decimal(
        payload.get("mtoImpVenta", payload.get("mtoImporteTotal", 0))
    )
    moneda = (cotizacion.moneda or "PEN").upper()
    tipo_doc = payload.get("tipoDoc", "00")

    if moneda != "PEN" or tipo_doc != "01" or monto_total <= UMBRAL_DETRACCION:
        return payload

    porcentaje = calculations.to_decimal(
        cotizacion.porcentaje_detraccion or PORCENTAJE_DETRACCION_IMPRENTA
    )
    monto_detraccion = calculations.redondear(
        monto_total * porcentaje / calculations.Decimal("100")
    )

    cuenta_bn = cotizacion.cuenta_banco_nacion
    if not cuenta_bn:
        for cuenta in _get_company_bank_accounts(user):
            if isinstance(cuenta, dict) and "nacion" in (cuenta.get("banco", "")).lower():
                cuenta_bn = cuenta.get("cuenta", "")
                break
    cuenta_bn = cuenta_bn or ""

    payload["detraccion"] = {
        "codBienDetraccion": CODIGO_DETRACCION_IMPRENTA,
        "codMedioPago": "001",
        "ctaBanco": cuenta_bn,
        "percent": porcentaje,
        "mount": monto_detraccion,
    }
    payload.setdefault("legends", []).append(
        {
            "code": "2006",
            "value": "Operacion sujeta al Sistema de Pago de Obligaciones Tributarias",
        }
    )

    cotizacion.sujeta_detraccion = True
    cotizacion.porcentaje_detraccion = porcentaje
    cotizacion.monto_detraccion = monto_detraccion
    cotizacion.cuenta_banco_nacion = cuenta_bn

    if db:
        try:
            db.commit()
        except Exception:
            db.rollback()

    return _sync_invoice_totals(payload)


def _aplicar_anticipos(payload, cotizacion, user):
    anticipos_json = cotizacion.anticipos_deducidos
    if not anticipos_json or not isinstance(anticipos_json, list):
        return payload

    anticipos_payload = []
    total_anticipos = calculations.Decimal("0.00")

    for anticipo in anticipos_json:
        monto = calculations.to_decimal(anticipo.get("monto", 0))
        total_anticipos += monto
        serie = anticipo.get("serie", "F001")
        correlativo = str(anticipo.get("correlativo", "1")).zfill(6)
        tipo_doc_anticipo = anticipo.get("tipo_doc", "02")
        anticipos_payload.append(
            {
                "nroDocRel": f"{serie}-{correlativo}",
                "tipoDocRel": tipo_doc_anticipo,
                "total": calculations.redondear(monto),
            }
        )

    total_anticipos = calculations.redondear(total_anticipos)
    anticipo_gravada = calculations.redondear(total_anticipos / calculations.FACTOR_IGV)
    anticipo_igv = calculations.redondear(total_anticipos - anticipo_gravada)

    payload["anticipos"] = anticipos_payload
    payload["totalAnticipos"] = total_anticipos
    payload["mtoOperGravadas"] = calculations.redondear(
        calculations.to_decimal(payload.get("mtoOperGravadas", 0)) - anticipo_gravada
    )
    payload["mtoIGV"] = calculations.redondear(
        calculations.to_decimal(payload.get("mtoIGV", 0)) - anticipo_igv
    )
    payload["mtoImpVenta"] = calculations.redondear(
        calculations.to_decimal(payload.get("mtoImpVenta", payload.get("mtoImporteTotal", 0)))
        - total_anticipos
    )

    cotizacion.total_anticipos = total_anticipos
    return _sync_invoice_totals(payload)


def _provider_request_headers(token: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }


def _build_async_status_params(user, ticket: str, payload: dict) -> dict:
    params = {"ticket": ticket}
    company = payload.get("company") if isinstance(payload, dict) else None
    company_ruc = None
    if isinstance(company, dict):
        company_ruc = company.get("ruc")
    company_ruc = company_ruc or _get_company_ruc(user)
    if company_ruc:
        params["ruc"] = str(company_ruc).strip()
    return params


def _is_pending_async_status_response(status_code: int, data: dict) -> bool:
    if status_code >= 500:
        return True

    error_text = _extract_provider_error_message(data).lower()
    code = str(data.get("code") or "").strip()
    provider_error = data.get("error")
    if isinstance(provider_error, dict):
        code = str(provider_error.get("code") or code).strip()

    pending_codes = {"0127", "98"}
    pending_fragments = (
        "ticket no existe",
        "ticket no encontrado",
        "en proceso",
        "procesando",
        "aun no ha sido procesado",
        "todavia no ha sido procesado",
    )

    return code in pending_codes or any(fragment in error_text for fragment in pending_fragments)


def _raise_for_provider_http_error(
    endpoint: str,
    status_code: int,
    data: dict,
    diagnostic: str | None = None,
) -> None:
    detail = _extract_provider_error_message(data)
    if diagnostic:
        detail = f"{detail}. {diagnostic}"
    raise FacturacionException(f"ApisPeru devolvio {status_code} en {endpoint}: {detail}")


def _diagnose_summary_provider_error(endpoint: str, data: dict) -> str | None:
    if endpoint != "/summary/send":
        return None

    sunat_error = (data.get("sunatResponse") or {}).get("error") or {}
    code = str(sunat_error.get("code") or data.get("code") or "").strip()
    xml = data.get("xml") or ""
    if code == "2992" and "<cbc:ID>1000</cbc:ID>" in xml and "<cbc:Percent>" not in xml:
        return (
            "ApisPeru genero el XML del resumen sin el nodo <cbc:Percent> para el tributo IGV "
            "(codigo 1000); el payload ya contiene montos tributarios y el bloqueo queda en el "
            "renderizado XML del proveedor"
        )
    return None


def _probe_render_diagnostic(user, payload: dict, endpoint: str) -> str | None:
    if endpoint != "/despatch/send":
        return None

    token = _get_apisperu_token(user)
    if not token:
        return None

    base_url = _get_api_base_url(user)
    render_endpoint = endpoint.replace("/send", "/xml")
    url = f"{base_url}{render_endpoint}"
    try:
        response = requests.post(
            url,
            data=json.dumps(payload, cls=SUNATDecimalEncoder),
            headers=_provider_request_headers(token),
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
    except requests.exceptions.RequestException:
        return None

    content_type = (response.headers.get("Content-Type") or "").lower()
    if response.status_code < 400 and ("xml" in content_type or response.text.lstrip().startswith("<?xml")):
        return (
            f"El payload si genero XML correctamente en {render_endpoint}; el fallo parece estar "
            "en la etapa de envio SUNAT o en la configuracion interna del proveedor"
        )
    return None


def _build_immediate_result(payload: dict, endpoint: str, status_code: int, data: dict) -> dict:
    sunat_response = data.get("sunatResponse") or {}
    cdr_response = sunat_response.get("cdrResponse") or {}
    success = (
        sunat_response.get("success") is True
        and not sunat_response.get("error")
        and str(cdr_response.get("code") or "0") == "0"
    )
    if not success:
        diagnostic = _diagnose_summary_provider_error(endpoint, data)
        detail = _extract_provider_error_message(data)
        if diagnostic:
            detail = f"{detail}. {diagnostic}"
        raise FacturacionException(
            f"ApisPeru rechazo {payload.get('tipoDoc')} {payload.get('serie')}-{payload.get('correlativo')}: "
            f"{detail}"
        )

    return {
        "success": True,
        "serie": payload.get("serie"),
        "correlativo": payload.get("correlativo"),
        "hash": data.get("hash"),
        "xml": data.get("xml"),
        "cdr_zip_base64": sunat_response.get("cdrZip"),
        "links": _normalize_links(data),
        "provider_status_code": status_code,
        "provider_endpoint": endpoint,
        "provider_response": data,
        "sunat_response": {
            "success": True,
            "error": None,
            "cdrZip": sunat_response.get("cdrZip"),
            "cdrResponse": cdr_response,
        },
    }


def _build_status_result(
    payload: dict,
    endpoint: str,
    status_code: int,
    data: dict,
    ticket: str,
    *,
    xml: str | None = None,
    hash_value: str | None = None,
) -> dict:
    cdr_response = data.get("cdrResponse") or {}
    success = (
        data.get("success") is True
        and not data.get("error")
        and str(data.get("code") or cdr_response.get("code") or "0") == "0"
    )
    if not success:
        raise FacturacionException(
            f"ApisPeru rechazo el ticket {ticket} en {endpoint}: {_extract_provider_error_message(data)}"
        )

    return {
        "success": True,
        "serie": payload.get("serie"),
        "correlativo": payload.get("correlativo"),
        "hash": hash_value,
        "xml": xml,
        "ticket": ticket,
        "cdr_zip_base64": data.get("cdrZip"),
        "links": _normalize_links(data),
        "provider_status_code": status_code,
        "provider_endpoint": endpoint,
        "provider_response": data,
        "sunat_response": {
            "success": True,
            "error": None,
            "ticket": ticket,
            "cdrZip": data.get("cdrZip"),
            "cdrResponse": cdr_response,
        },
    }


def _poll_async_status(user, payload: dict, ticket: str, status_endpoint: str, *, xml=None, hash_value=None):
    token = _get_apisperu_token(user)
    if not token:
        raise FacturacionException("Falta Token API.")

    base_url = _get_api_base_url(user)
    url = f"{base_url}{status_endpoint}"
    params = _build_async_status_params(user, ticket, payload)
    last_status_code = None
    last_data = {}

    for attempt in range(1, ASYNC_STATUS_MAX_ATTEMPTS + 1):
        try:
            response = requests.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                timeout=DEFAULT_TIMEOUT_SECONDS,
            )
        except requests.exceptions.Timeout as exc:
            raise FacturacionException(
                f"Timeout consultando ticket {ticket} en {status_endpoint}."
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise FacturacionException(
                f"No se pudo consultar el ticket {ticket} en {status_endpoint}."
            ) from exc

        data = _safe_json(response)
        last_status_code = response.status_code
        last_data = data

        if response.status_code < 400 and (data.get("cdrResponse") or data.get("cdrZip")):
            return _build_status_result(
                payload,
                status_endpoint,
                response.status_code,
                data,
                ticket,
                xml=xml,
                hash_value=hash_value,
            )

        if attempt < ASYNC_STATUS_MAX_ATTEMPTS and _is_pending_async_status_response(response.status_code, data):
            time.sleep(ASYNC_STATUS_RETRY_SECONDS)
            continue

        if response.status_code >= 400:
            _raise_for_provider_http_error(status_endpoint, response.status_code, data)

        raise FacturacionException(
            f"ApisPeru devolvio el ticket {ticket} sin confirmacion final en {status_endpoint}: "
            f"{_extract_provider_error_message(data)}"
        )

    if last_status_code is not None and last_status_code >= 400:
        _raise_for_provider_http_error(status_endpoint, last_status_code, last_data)

    raise FacturacionException(
        f"El ticket {ticket} no quedo listo despues de {ASYNC_STATUS_MAX_ATTEMPTS} intentos en {status_endpoint}: "
        f"{_extract_provider_error_message(last_data)}"
    )


def _enviar_a_api(payload, user, endpoint, *, status_endpoint: str | None = None):
    token = _get_apisperu_token(user)
    if not token:
        raise FacturacionException("Falta Token API.")

    base_url = _get_api_base_url(user)
    url = f"{base_url}{endpoint}"
    payload_str = json.dumps(payload, cls=SUNATDecimalEncoder)

    try:
        response = requests.post(
            url,
            data=payload_str,
            headers=_provider_request_headers(token),
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout as exc:
        raise FacturacionException(f"Timeout enviando documento a {endpoint}.") from exc
    except requests.exceptions.ConnectionError as exc:
        raise FacturacionException(
            f"No se pudo conectar con el servicio fiscal en {endpoint}."
        ) from exc

    data = _safe_json(response)
    if response.status_code >= 400:
        diagnostic = _probe_render_diagnostic(user, payload, endpoint)
        _raise_for_provider_http_error(endpoint, response.status_code, data, diagnostic)

    sunat_response = data.get("sunatResponse") or {}
    if sunat_response.get("error"):
        diagnostic = _diagnose_summary_provider_error(endpoint, data)
        detail = _extract_provider_error_message(data)
        if diagnostic:
            detail = f"{detail}. {diagnostic}"
        raise FacturacionException(
            f"ApisPeru rechazo el envio en {endpoint}: {detail}"
        )

    ticket = sunat_response.get("ticket")
    if status_endpoint and ticket:
        return _poll_async_status(
            user,
            payload,
            ticket,
            status_endpoint,
            xml=data.get("xml"),
            hash_value=data.get("hash"),
        )

    return _build_immediate_result(payload, endpoint, response.status_code, data)


def emitir_factura(
    cotizacion: models.Cotizacion,
    db: Session,
    user: models.User,
    tipo_doc_override=None,
    tipo_operacion_override: str | None = None,
    serie_override: str | None = None,
):
    if tipo_doc_override:
        tipo_comprobante = tipo_doc_override
    else:
        tipo_cliente = obtener_tipo_documento_codigo(cotizacion.cliente.tipo_documento)
        tipo_comprobante = "01" if tipo_cliente == "6" else "03"

    serie = serie_override or ("F001" if tipo_comprobante == "01" else "B001")
    payload, _ = _base_payload(
        cotizacion,
        user,
        tipo_comprobante,
        tipo_operacion_override=tipo_operacion_override,
    )
    payload["serie"] = serie_override or cotizacion.serie or serie
    payload["correlativo"] = str(cotizacion.correlativo or cotizacion.id).zfill(6)

    payload = _aplicar_detraccion(payload, cotizacion, user, db)
    payload = _aplicar_anticipos(payload, cotizacion, user)
    payload = _sync_invoice_totals(payload)

    result = _enviar_a_api(payload, user, "/invoice/send")
    return _attach_sale_artifacts(result, user)


def emitir_nota(
    nota: models.Cotizacion,
    doc_afectado: models.Cotizacion,
    user: models.User,
    cod_motivo: str,
    descripcion: str,
    tipo_nota: str,
):
    tipo_comprobante = "07" if tipo_nota == "credito" else "08"
    serie_nota = "FF01" if (doc_afectado.serie or "").startswith("F") else "BB01"

    payload, _ = _base_payload(nota, user, tipo_comprobante)
    payload["serie"] = nota.serie or serie_nota
    payload["correlativo"] = str(nota.correlativo or nota.id).zfill(6)
    payload.update(
        _build_note_reference_payload(
            nota,
            doc_afectado=doc_afectado,
            cod_motivo=cod_motivo,
            descripcion=descripcion,
        )
    )
    payload["mtoImpVenta"] = calculations.redondear(
        payload.get("mtoImpVenta", payload.get("mtoImporteTotal", 0))
    )
    payload["mtoImporteTotal"] = payload["mtoImpVenta"]

    result = _enviar_a_api(payload, user, "/note/send")
    return _attach_sale_artifacts(result, user)


def _build_summary_payload(comprobante, motivo: str, user) -> dict:
    fecha_operacion = _current_issue_datetime()
    cliente = comprobante.cliente
    total = calculations.redondear(getattr(comprobante, "total_venta", 0))
    total_gravada = calculations.redondear(getattr(comprobante, "total_gravada", 0))
    total_inafecta = calculations.redondear(getattr(comprobante, "total_inafecta", 0))
    total_exonerada = calculations.redondear(getattr(comprobante, "total_exonerada", 0))
    total_igv = calculations.redondear(getattr(comprobante, "total_igv", 0))

    return {
        "fecGeneracion": fecha_operacion,
        "fecResumen": fecha_operacion,
        "correlativo": _build_batch_correlativo(),
        "moneda": comprobante.moneda or "PEN",
        "company": _build_company_payload(user),
        "details": [
            {
                "tipoDoc": comprobante.tipo_comprobante,
                "serieNro": f"{comprobante.serie}-{comprobante.correlativo}",
                "estado": "3",
                "clienteTipo": obtener_tipo_documento_codigo(getattr(cliente, "tipo_documento", None)),
                "clienteNro": str(getattr(cliente, "numero_documento", "00000000") or "00000000"),
                "total": total,
                "mtoOperGravadas": total_gravada,
                "mtoOperInafectas": total_inafecta,
                "mtoOperExoneradas": total_exonerada,
                "mtoOperExportacion": calculations.Decimal("0.00"),
                "mtoOperGratuitas": calculations.Decimal("0.00"),
                "mtoOtrosCargos": calculations.Decimal("0.00"),
                "mtoIGV": total_igv,
                "mtoIvap": calculations.Decimal("0.00"),
                "mtoIcbper": calculations.Decimal("0.00"),
                "mtoISC": calculations.Decimal("0.00"),
                "mtoOtrosTributos": calculations.Decimal("0.00"),
                "desMotivoBaja": motivo,
            }
        ],
    }


def anular_comprobante(comprobante: models.Cotizacion, motivo: str, user: models.User):
    payload = {
        "correlativo": _build_batch_correlativo(),
        "fecGeneracion": _current_issue_datetime(),
        "fecComunicacion": _current_issue_datetime(plus_minutes=1),
        "company": _build_company_payload(user),
        "details": [
            {
                "tipoDoc": comprobante.tipo_comprobante,
                "serie": comprobante.serie,
                "correlativo": str(comprobante.correlativo).zfill(6),
                "desMotivoBaja": motivo,
            }
        ],
    }

    if comprobante.tipo_comprobante == "03" or (
        comprobante.tipo_comprobante in {"07", "08"} and (comprobante.serie or "").startswith("B")
    ):
        summary_payload = _build_summary_payload(comprobante, motivo, user)
        return _enviar_a_api(
            summary_payload,
            user,
            "/summary/send",
            status_endpoint="/summary/status",
        )

    return _enviar_a_api(
        payload,
        user,
        "/voided/send",
        status_endpoint="/voided/status",
    )


def _resolve_guide_recipient(guia) -> dict:
    cotizacion = getattr(guia, "cotizacion", None)
    cliente = getattr(cotizacion, "cliente", None) if cotizacion else None
    if not cliente:
        raise FacturacionException(
            "La guia requiere una cotizacion con cliente para construir el destinatario."
        )
    return {
        "tipoDoc": obtener_tipo_documento_codigo(cliente.tipo_documento),
        "numDoc": str(cliente.numero_documento).strip(),
        "rznSocial": cliente.razon_social or "-",
    }


def _build_company_payload_gre(user) -> dict:
    """Company payload para GRE: incluye codLocal requerido por SUNAT Nueva GRE."""
    company_ruc = _get_company_ruc(user)
    company_name = _get_company_name(user)
    company_address = _get_company_address(user)

    if not company_ruc:
        raise FacturacionException("Emisor sin RUC configurado.")
    if not company_name:
        raise FacturacionException("Emisor sin razon social configurada.")

    address = _build_address_payload(company_address)
    address["codLocal"] = "0000"

    return {
        "ruc": company_ruc,
        "razonSocial": company_name,
        "nombreComercial": company_name,
        "address": address,
    }


def _base_payload_gre(guia, user):
    cotizacion = getattr(guia, "cotizacion", None)
    cliente = getattr(cotizacion, "cliente", None) if cotizacion else None
    destinatario_ruc = str(cliente.numero_documento).strip() if cliente and cliente.numero_documento else None
    company_ruc = _get_company_ruc(user)
    llegada = {
        "ubigueo": guia.llegada_ubigeo or DEFAULT_UBIGEO,
        "direccion": guia.llegada_direccion,
    }
    if destinatario_ruc:
        llegada["ruc"] = destinatario_ruc
    if guia.motivo_traslado == "04" or (destinatario_ruc and destinatario_ruc == company_ruc):
        llegada["codLocal"] = "0000"

    payload = {
        "version": 2022,
        "tipoDoc": "09",
        "serie": guia.serie or "T001",
        "correlativo": str(guia.correlativo).zfill(6),
        "fechaEmision": _current_issue_datetime(getattr(guia, "fecha_emision", None)),
        "observacion": guia.descripcion_motivo or "GUIA DE REMISION",
        "company": _build_company_payload_gre(user),
        "destinatario": _resolve_guide_recipient(guia),
        "envio": {
            "codTraslado": guia.motivo_traslado,
            "desTraslado": (guia.descripcion_motivo or "VENTA").upper(),
            "modTraslado": guia.modalidad_traslado,
            "fecTraslado": _current_issue_datetime(guia.fecha_traslado),
            "pesoTotal": calculations.redondear(getattr(guia, "peso_bruto_total", 0)),
            "undPesoTotal": guia.unidad_medida_peso or "KGM",
            "llegada": llegada,
            "partida": {
                "ubigueo": guia.partida_ubigeo or DEFAULT_UBIGEO,
                "direccion": guia.partida_direccion,
                "codLocal": "0000",
                "ruc": company_ruc,
            },
        },
        "details": [
            {
                "cantidad": calculations.redondear(item.cantidad),
                "unidad": item.unidad_medida or "NIU",
                "descripcion": item.descripcion,
                "codigo": item.codigo_producto or f"ITEM-{index:03d}",
            }
            for index, item in enumerate(guia.items, start=1)
        ],
    }

    if guia.numero_bultos:
        payload["envio"]["numBultos"] = guia.numero_bultos
    if guia.sustento_peso:
        payload["envio"]["sustentoPeso"] = guia.sustento_peso
    if guia.ind_transbordo is not None:
        payload["envio"]["indTransbordo"] = bool(guia.ind_transbordo)
    if guia.num_contenedor:
        payload["envio"]["numContenedor"] = guia.num_contenedor
    if guia.cod_puerto:
        payload["envio"]["codPuerto"] = guia.cod_puerto

    if guia.modalidad_traslado == "01":
        if not guia.transportista_ruc:
            raise FacturacionException(
                "La guia con traslado publico requiere RUC del transportista."
            )
        transportista = {
            "tipoDoc": "6",
            "numDoc": guia.transportista_ruc,
            "rznSocial": guia.transportista_razon_social or "-",
        }
        if guia.transportista_nro_mtc:
            transportista["nroMtc"] = guia.transportista_nro_mtc
        if guia.vehiculo_placa:
            transportista["placa"] = guia.vehiculo_placa
        if guia.conductor_tipo_doc:
            transportista["choferTipoDoc"] = guia.conductor_tipo_doc
        if guia.conductor_nro_doc:
            transportista["choferDoc"] = guia.conductor_nro_doc
        payload["envio"]["transportista"] = transportista
        payload["tercero"] = {
            "tipoDoc": "6",
            "numDoc": guia.transportista_ruc,
            "rznSocial": guia.transportista_razon_social or "-",
        }
    else:
        if not guia.vehiculo_placa or not guia.conductor_nro_doc:
            raise FacturacionException(
                "La guia con traslado privado requiere placa y documento del conductor."
            )
        payload["envio"]["vehiculo"] = {
            "placa": guia.vehiculo_placa,
        }
        if guia.vehiculo_nro_circulacion:
            payload["envio"]["vehiculo"]["nroCirculacion"] = guia.vehiculo_nro_circulacion
        if guia.vehiculo_cod_emisor:
            payload["envio"]["vehiculo"]["codEmisor"] = guia.vehiculo_cod_emisor
        if guia.vehiculo_nro_autorizacion:
            payload["envio"]["vehiculo"]["nroAutorizacion"] = guia.vehiculo_nro_autorizacion
        chofer = {
            "tipo": "Principal",
            "tipoDoc": guia.conductor_tipo_doc or "1",
            "nroDoc": guia.conductor_nro_doc,
        }
        if guia.conductor_nombres:
            chofer["nombres"] = guia.conductor_nombres
        if guia.conductor_apellidos:
            chofer["apellidos"] = guia.conductor_apellidos
        if guia.conductor_licencia:
            chofer["licencia"] = guia.conductor_licencia
        payload["envio"]["choferes"] = [chofer]

    return payload


def emitir_guia_remision(guia, user):
    payload = _base_payload_gre(guia, user)
    return _enviar_a_api(
        payload,
        user,
        "/despatch/send",
        status_endpoint="/despatch/status",
    )


def emitir_resumen_diario(payload: dict, user):
    return _enviar_a_api(
        payload,
        user,
        "/summary/send",
        status_endpoint="/summary/status",
    )


def emitir_comunicacion_baja(payload: dict, user):
    return _enviar_a_api(
        payload,
        user,
        "/voided/send",
        status_endpoint="/voided/status",
    )


def emitir_retencion(payload: dict, user):
    return _enviar_a_api(payload, user, "/retention/send")


def emitir_percepcion(payload: dict, user):
    return _enviar_a_api(payload, user, "/perception/send")


def emitir_reversion(payload: dict, user):
    return _enviar_a_api(
        payload,
        user,
        "/reversion/send",
        status_endpoint="/reversion/status",
    )


def _build_minimal_lookup_payload(comprobante, user) -> dict:
    return {
        "tipoDoc": comprobante.tipo_comprobante,
        "serie": comprobante.serie,
        "correlativo": str(comprobante.correlativo).zfill(6),
        "company": {"ruc": _get_company_ruc(user)},
    }


def _build_note_reference_payload(
    nota: models.Cotizacion,
    *,
    doc_afectado: models.Cotizacion | None = None,
    cod_motivo: str | None = None,
    descripcion: str | None = None,
) -> dict:
    documento_afectado = doc_afectado or getattr(nota, "nota_referencia", None)
    if not documento_afectado:
        raise FacturacionException(
            "La nota no tiene comprobante afectado referenciado para construir el payload."
        )

    motivo_codigo = (cod_motivo or getattr(nota, "nota_motivo_codigo", None) or "").strip()
    motivo_descripcion = (
        descripcion or getattr(nota, "nota_motivo_descripcion", None) or ""
    ).strip()
    if not motivo_codigo or not motivo_descripcion:
        raise FacturacionException(
            "La nota no tiene motivo persistido; no se puede reconstruir el payload de ApisPeru."
        )

    return {
        "tipDocAfectado": documento_afectado.tipo_comprobante,
        "numDocfectado": _document_number(documento_afectado),
        "codMotivo": motivo_codigo,
        "desMotivo": motivo_descripcion,
    }


def _build_download_payload(comprobante, user) -> dict:
    if comprobante.tipo_comprobante in {"01", "03"}:
        payload, _ = _base_payload(comprobante, user, comprobante.tipo_comprobante)
        payload["serie"] = comprobante.serie
        payload["correlativo"] = str(comprobante.correlativo).zfill(6)
        return _sync_invoice_totals(payload)

    if comprobante.tipo_comprobante in {"07", "08"}:
        payload, _ = _base_payload(comprobante, user, comprobante.tipo_comprobante)
        payload["serie"] = comprobante.serie
        payload["correlativo"] = str(comprobante.correlativo).zfill(6)
        payload.update(_build_note_reference_payload(comprobante))
        return _sync_invoice_totals(payload)

    return _build_minimal_lookup_payload(comprobante, user)


def descargar_archivo(tipo_archivo: str, comprobante: models.Cotizacion, user: models.User):
    if tipo_archivo == "cdr":
        raise FacturacionException(
            "ApisPeru no expone un endpoint generico de descarga CDR para este flujo. "
            "Use el CDR devuelto al momento de la emision."
        )

    token = _get_apisperu_token(user)
    if not token:
        raise FacturacionException("Falta Token API.")

    base_url = _get_api_base_url(user)
    prefix = "/note" if comprobante.tipo_comprobante in {"07", "08"} else "/invoice"
    url = f"{base_url}{prefix}/{tipo_archivo}"
    payload = _build_download_payload(comprobante, user)

    try:
        response = requests.post(
            url,
            data=json.dumps(payload, cls=SUNATDecimalEncoder),
            headers=_provider_request_headers(token),
            timeout=DEFAULT_TIMEOUT_SECONDS,
            stream=True,
        )
    except requests.exceptions.Timeout as exc:
        raise FacturacionException(
            f"Timeout descargando {tipo_archivo.upper()} del proveedor fiscal."
        ) from exc
    except requests.exceptions.ConnectionError as exc:
        raise FacturacionException(
            f"No se pudo conectar con ApisPeru para descargar {tipo_archivo.upper()}."
        ) from exc

    if response.status_code >= 400:
        _raise_for_provider_http_error(f"{prefix}/{tipo_archivo}", response.status_code, _safe_json(response))

    content_type = (response.headers.get("Content-Type") or "").lower()
    if "application/json" in content_type:
        data = _safe_json(response)
        raise FacturacionException(
            f"ApisPeru no entrego {tipo_archivo.upper()} para {_document_number(comprobante)}: "
            f"{_extract_provider_error_message(data)}"
        )

    return response.content


def validate_apisperu_token(
    token: str,
    api_url: str | None = None,
    business_ruc: str | None = None,
) -> dict:
    token = (token or "").strip()
    business_ruc = "".join(ch for ch in str(business_ruc or "") if ch.isdigit()) or None
    token_company_ruc = _extract_token_company_ruc(token)
    matches_business_ruc = (
        token_company_ruc == business_ruc
        if business_ruc and token_company_ruc
        else None
    )
    if not token:
        return {
            "valid": False,
            "message": "Ingrese un token de ApisPeru para validarlo.",
            "provider_status_code": None,
            "provider_detail": None,
            "token_company_ruc": token_company_ruc,
            "matches_business_ruc": matches_business_ruc,
        }

    base_url = (api_url or settings.API_URL).strip().rstrip("/")
    if not base_url:
        return {
            "valid": False,
            "message": "No hay URL de ApisPeru configurada para la validacion.",
            "provider_status_code": None,
            "provider_detail": None,
            "token_company_ruc": token_company_ruc,
            "matches_business_ruc": matches_business_ruc,
        }

    url = f"{base_url}/invoice/send"

    try:
        response = requests.post(
            url,
            data="{}",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            timeout=15,
        )
    except requests.exceptions.Timeout:
        return {
            "valid": False,
            "message": "ApisPeru no respondio a tiempo al validar el token.",
            "provider_status_code": None,
            "provider_detail": "timeout",
            "token_company_ruc": token_company_ruc,
            "matches_business_ruc": matches_business_ruc,
        }
    except requests.exceptions.ConnectionError:
        return {
            "valid": False,
            "message": "No se pudo conectar con ApisPeru para validar el token.",
            "provider_status_code": None,
            "provider_detail": "connection_error",
            "token_company_ruc": token_company_ruc,
            "matches_business_ruc": matches_business_ruc,
        }

    provider_data = _safe_json(response)
    provider_detail_text = _extract_provider_error_message(provider_data)

    if response.status_code in {400, 422}:
        if business_ruc and token_company_ruc and token_company_ruc != business_ruc:
            return {
                "valid": False,
                "message": (
                    f"El token de ApisPeru es valido, pero pertenece al RUC {token_company_ruc} "
                    f"y no al RUC configurado ({business_ruc})."
                ),
                "provider_status_code": response.status_code,
                "provider_detail": provider_detail_text or "payload_validation_error",
                "token_company_ruc": token_company_ruc,
                "matches_business_ruc": False,
            }

        success_message = (
            "Token aceptado por ApisPeru. "
            "La respuesta del proveedor indica que el payload de prueba fue rechazado, "
            "lo cual confirma que el bearer token funciona."
        )
        if business_ruc and token_company_ruc == business_ruc:
            success_message = f"Token aceptado por ApisPeru y asociado al RUC {business_ruc}."
        elif business_ruc and not token_company_ruc:
            success_message = (
                "Token aceptado por ApisPeru. "
                "No se pudo verificar el RUC asociado desde el JWT del proveedor."
            )

        return {
            "valid": True,
            "message": success_message,
            "provider_status_code": response.status_code,
            "provider_detail": provider_detail_text or "payload_validation_error",
            "token_company_ruc": token_company_ruc,
            "matches_business_ruc": matches_business_ruc,
        }

    company_token_without_payload = (
        response.status_code == 404
        and token_company_ruc is not None
        and "empresa no encontrada" in provider_detail_text.lower()
    )
    if company_token_without_payload:
        if business_ruc and token_company_ruc != business_ruc:
            return {
                "valid": False,
                "message": (
                    f"El token de ApisPeru es valido, pero pertenece al RUC {token_company_ruc} "
                    f"y no al RUC configurado ({business_ruc})."
                ),
                "provider_status_code": response.status_code,
                "provider_detail": provider_detail_text or "company_mismatch",
                "token_company_ruc": token_company_ruc,
                "matches_business_ruc": False,
            }

        return {
            "valid": True,
            "message": (
                f"Token aceptado por ApisPeru y asociado al RUC {token_company_ruc}."
                if token_company_ruc
                else "Token aceptado por ApisPeru."
            ),
            "provider_status_code": response.status_code,
            "provider_detail": provider_detail_text or "company_not_found_without_payload",
            "token_company_ruc": token_company_ruc,
            "matches_business_ruc": matches_business_ruc,
        }

    if response.status_code in {401, 403}:
        return {
            "valid": False,
            "message": "ApisPeru rechazo el token ingresado.",
            "provider_status_code": response.status_code,
            "provider_detail": provider_detail_text or "unauthorized",
            "token_company_ruc": token_company_ruc,
            "matches_business_ruc": matches_business_ruc,
        }

    if response.status_code in {404, 405}:
        return {
            "valid": False,
            "message": "La URL de ApisPeru no es valida o no expone el endpoint esperado.",
            "provider_status_code": response.status_code,
            "provider_detail": provider_detail_text or "invalid_api_url",
            "token_company_ruc": token_company_ruc,
            "matches_business_ruc": matches_business_ruc,
        }

    if response.status_code >= 500:
        return {
            "valid": False,
            "message": "ApisPeru devolvio un error interno al validar el token.",
            "provider_status_code": response.status_code,
            "provider_detail": provider_detail_text or "provider_error",
            "token_company_ruc": token_company_ruc,
            "matches_business_ruc": matches_business_ruc,
        }

    return {
        "valid": False,
        "message": "No se pudo determinar con certeza si el token es valido.",
        "provider_status_code": response.status_code,
        "provider_detail": provider_detail_text or "unexpected_response",
        "token_company_ruc": token_company_ruc,
        "matches_business_ruc": matches_business_ruc,
    }
