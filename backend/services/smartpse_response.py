from __future__ import annotations

import base64
import zipfile
from io import BytesIO
from typing import Any
from xml.etree import ElementTree as ET

from services.smartpse_client import SmartPSEException


NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
}


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _join_messages(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        for item in _as_list(value):
            if item is None:
                continue
            text = str(item).strip()
            if text:
                parts.append(text)
    return ". ".join(parts)


def _decode_base64_text(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if text.startswith("<"):
        return text
    try:
        raw = base64.b64decode(text, validate=True)
    except Exception:
        return text
    try:
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            names = [name for name in archive.namelist() if name.lower().endswith(".xml")]
            if not names:
                names = archive.namelist()
            if not names:
                return None
            return archive.read(names[0]).decode("utf-8")
    except zipfile.BadZipFile:
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return None


def extract_cdr_xml(provider_response: dict | None) -> str | None:
    """Obtiene el CDR XML persistido en la respuesta de Smart PSE."""
    if not isinstance(provider_response, dict):
        return None
    cdr = provider_response.get("cdr")
    if cdr:
        return _decode_base64_text(cdr)
    for key in ("process", "verification", "data", "sunat_response"):
        resolved = extract_cdr_xml(provider_response.get(key))
        if resolved:
            return resolved
    return None


def extract_xml_from_signed_zip(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if text.startswith("<"):
        return text
    try:
        raw = base64.b64decode(text, validate=True)
    except Exception:
        return text

    try:
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            names = [name for name in archive.namelist() if name.lower().endswith(".xml")]
            if not names:
                names = archive.namelist()
            if not names:
                return None
            return archive.read(names[0]).decode("utf-8")
    except zipfile.BadZipFile:
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return None


def extract_sale_document_identity(xml_text: str | None) -> dict:
    if not xml_text:
        return {}
    try:
        root = ET.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)
    except Exception:
        return {}

    root_name = root.tag.rsplit("}", 1)[-1]
    if root_name == "CreditNote":
        tipo_doc = "07"
    elif root_name == "DebitNote":
        tipo_doc = "08"
    else:
        tipo_doc = root.findtext("cbc:InvoiceTypeCode", namespaces=NS)

    supplier_ruc = root.findtext(
        "cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID",
        namespaces=NS,
    )
    if supplier_ruc is None:
        supplier_ruc = root.findtext(
            "cac:AccountingSupplierParty/cbc:CustomerAssignedAccountID",
            namespaces=NS,
        )

    document_id = root.findtext("cbc:ID", namespaces=NS)
    serie = None
    correlativo = None
    if document_id and "-" in document_id:
        serie, correlativo = document_id.split("-", 1)

    return {
        "document_id": document_id,
        "serie": serie,
        "correlativo": correlativo,
        "tipo_doc": str(tipo_doc or "").strip().zfill(2) if tipo_doc else None,
        "issue_date": root.findtext("cbc:IssueDate", namespaces=NS),
        "ruc": str(supplier_ruc or "").strip() or None,
    }


def extract_gre_document_identity(xml_text: str | None) -> dict:
    """Read the immutable identity of a signed UBL DespatchAdvice."""
    if not xml_text:
        return {}
    try:
        root = ET.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)
    except Exception:
        return {}
    if root.tag.rsplit("}", 1)[-1] != "DespatchAdvice":
        return {}
    document_id = root.findtext("cbc:ID", namespaces=NS)
    series = number = None
    if document_id and "-" in document_id:
        series, number = document_id.split("-", 1)
    issuer_ruc = root.findtext(
        "cac:DespatchSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID",
        namespaces=NS,
    )
    document_type = root.findtext("cbc:DespatchAdviceTypeCode", namespaces=NS)
    return {
        "document_id": document_id,
        "series": series,
        "number": number,
        "issuer_ruc": str(issuer_ruc or "").strip() or None,
        "document_type": str(document_type or "").strip() or None,
    }


def _normalize_document_id(value: str | None) -> tuple[str, str]:
    series, separator, number = str(value or "").strip().partition("-")
    if not separator:
        return series.upper(), ""
    normalized_number = str(int(number)) if number.isdigit() else number
    return series.upper(), normalized_number


def validate_sale_cdr(cdr_xml: str, payload: dict) -> None:
    """Require a readable, matching, accepted CDR for invoices and notes."""
    try:
        root = ET.fromstring(cdr_xml)
    except Exception as exc:
        raise SmartPSEException(
            "El CDR del comprobante no es XML legible; requiere conciliación."
        ) from exc

    response_code = root.findtext(".//cbc:ResponseCode", namespaces=NS)
    reference_id = root.findtext(".//cbc:ReferenceID", namespaces=NS)
    if not reference_id:
        reference_id = root.findtext(".//cac:DocumentReference/cbc:ID", namespaces=NS)
    expected = f"{payload.get('serie')}-{payload.get('correlativo')}"
    if response_code is None:
        raise SmartPSEException(
            "El CDR del comprobante no contiene resultado SUNAT; requiere conciliación."
        )
    if not reference_id:
        raise SmartPSEException(
            "El CDR del comprobante no identifica el documento; requiere conciliación."
        )
    if _normalize_document_id(reference_id) != _normalize_document_id(expected):
        raise SmartPSEException(
            f"El CDR corresponde a {reference_id} y no a {expected}; requiere conciliación."
        )

    expected_ruc = str((payload.get("company") or {}).get("ruc") or "").strip()
    receiver_ruc = root.findtext(
        ".//cac:ReceiverParty/cac:PartyIdentification/cbc:ID",
        namespaces=NS,
    )
    if expected_ruc and receiver_ruc and str(receiver_ruc).strip() != expected_ruc:
        raise SmartPSEException(
            "El CDR corresponde a otro RUC emisor; requiere conciliación."
        )

    if str(response_code).strip() != "0":
        from services.smartpse_client import SmartPSEDefinitiveRejection

        description = root.findtext(".//cbc:Description", namespaces=NS)
        raise SmartPSEDefinitiveRejection(
            f"SUNAT rechazó el comprobante con código {response_code}: "
            f"{description or 'sin descripción'}",
            {"cdr": cdr_xml, "estado": response_code, "mensaje": description},
        )


def validate_gre_cdr(cdr_xml: str, payload: dict) -> None:
    """Require a readable, matching, accepted CDR before a GRE becomes accepted."""
    try:
        root = ET.fromstring(cdr_xml)
    except Exception as exc:
        raise SmartPSEException("El CDR GRE no es XML legible; requiere conciliación.") from exc

    response_code = root.findtext(".//cbc:ResponseCode", namespaces=NS)
    reference_id = root.findtext(".//cac:DocumentReference/cbc:ID", namespaces=NS)
    expected = f"{payload.get('serie')}-{payload.get('correlativo')}"
    if not reference_id:
        raise SmartPSEException("El CDR GRE no identifica el documento; requiere conciliación.")
    if _normalize_document_id(reference_id) != _normalize_document_id(expected):
        raise SmartPSEException(
            f"El CDR corresponde a {reference_id} y no a {expected}; requiere conciliación."
        )
    if str(response_code or "").strip() != "0":
        from services.smartpse_client import SmartPSEDefinitiveRejection
        description = root.findtext(".//cbc:Description", namespaces=NS)
        raise SmartPSEDefinitiveRejection(
            f"SUNAT rechazó la GRE con código {response_code}: {description or 'sin descripción'}",
            {"cdr": cdr_xml, "estado": response_code, "mensaje": description},
        )


def _is_pending(data: dict) -> bool:
    estado = str(data.get("estado") or "").strip()
    return bool(data.get("ticket")) and not data.get("cdr") and estado != "202"


def _provider_rejected(data: dict) -> bool:
    return data.get("rechazado") is True or bool(data.get("errores"))


def build_smartpse_result(
    payload: dict,
    data: dict,
    *,
    endpoint: str,
    status_code: int,
    ticket: str | None = None,
    require_cdr: bool = False,
) -> dict:
    payload = payload or {}
    data = data or {}
    if status_code >= 400 or _provider_rejected(data):
        detail = _join_messages(
            data.get("mensaje"),
            data.get("message"),
            data.get("errores"),
            data.get("observaciones"),
            data.get("error"),
        )
        if _provider_rejected(data) and status_code < 400:
            from services.smartpse_client import SmartPSEDefinitiveRejection
            raise SmartPSEDefinitiveRejection(
                detail or "Smart PSE rechazo definitivamente el documento.", data
            )
        raise SmartPSEException(detail or "Smart PSE rechazo el documento.")

    resolved_ticket = ticket or data.get("ticket")
    signed_xml = extract_xml_from_signed_zip(data.get("xml_firmado") or data.get("xml"))
    cdr_xml = _decode_base64_text(data.get("cdr"))
    document_type = str(payload.get("tipoDoc") or "").zfill(2)
    if cdr_xml and document_type in {"09", "31"}:
        validate_gre_cdr(cdr_xml, payload)
    elif cdr_xml and document_type in {"01", "03", "07", "08"}:
        validate_sale_cdr(cdr_xml, payload)
    pending = str(data.get("estado") or "").strip() == "202" or _is_pending(data)
    explicitly_pending = str(data.get("estado") or "").strip() == "202"
    if require_cdr and not cdr_xml and not pending:
        raise SmartPSEException(
            "Smart PSE no devolvio CDR de aceptacion; el documento no puede marcarse como aceptado."
        )

    result = {
        "success": True,
        "serie": payload.get("serie"),
        "correlativo": payload.get("correlativo"),
        "hash": data.get("codigo_hash") or data.get("hash"),
        "xml": signed_xml,
        "cdr_xml": cdr_xml,
        "ticket": resolved_ticket,
        "pending": pending,
        "provider_status_code": status_code,
        "provider_endpoint": endpoint,
        "provider_response": data,
        "sunat_response": {
            "success": True,
            "error": None,
            "ticket": resolved_ticket,
            "cdrResponse": {
                "code": str(data.get("estado") or "0"),
                "description": data.get("mensaje") or data.get("message") or "",
                "notes": data.get("observaciones") or [],
            },
        },
    }
    return result
