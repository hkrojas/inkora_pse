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
        raise SmartPSEException(detail or "Smart PSE rechazo el documento.")

    resolved_ticket = ticket or data.get("ticket")
    signed_xml = extract_xml_from_signed_zip(data.get("xml_firmado") or data.get("xml"))
    cdr_xml = _decode_base64_text(data.get("cdr"))
    pending = str(data.get("estado") or "").strip() == "202" or _is_pending(data)
    if require_cdr and not cdr_xml:
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
