from __future__ import annotations

import base64
import zipfile
from io import BytesIO
from typing import Any

from services.smartpse_client import SmartPSEException


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
        return base64.b64decode(text, validate=True).decode("utf-8")
    except Exception:
        return text


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
