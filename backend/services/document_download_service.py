"""Naming helpers for tenant-owned document downloads."""
from __future__ import annotations

import re
from typing import Any

from services.client_snapshot_service import resolve_document_cliente_snapshot


def _document_number(document: Any) -> str:
    serie = str(getattr(document, "serie", "") or "DOCUMENTO").strip().upper()
    correlativo = getattr(document, "correlativo", None)
    try:
        number = str(int(correlativo)).zfill(6)
    except (TypeError, ValueError):
        number = str(correlativo or "0").strip().zfill(6)
    return f"{serie}-{number}"


def _receiver_document(document: Any) -> str:
    snapshot = resolve_document_cliente_snapshot(document)
    raw = str(snapshot.get("numero_documento") or "")
    digits = "".join(character for character in raw if character.isdigit())
    return digits or "SIN-DOCUMENTO"


def _safe_filename_component(value: str) -> str:
    normalized = re.sub(r"[^A-Z0-9_-]+", "-", str(value or "").upper())
    return normalized.strip("-_") or "DOCUMENTO"


def build_document_download_filename(document: Any, extension: str = "pdf") -> str:
    """Build ``SERIE-CORRELATIVO_RECEPTOR.ext`` without customer names or secrets."""
    safe_extension = _safe_filename_component(extension).lower()
    return (
        f"{_safe_filename_component(_document_number(document))}_"
        f"{_safe_filename_component(_receiver_document(document))}.{safe_extension}"
    )
