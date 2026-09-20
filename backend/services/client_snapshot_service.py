"""Helpers for immutable document-level client data."""
from __future__ import annotations

from typing import Any, Mapping


CLIENT_SNAPSHOT_STRING_FIELDS = (
    "tipo_documento",
    "numero_documento",
    "razon_social",
    "nombre_comercial",
    "direccion",
    "ubigeo",
    "email",
    "telefono",
    "whatsapp",
    "contacto",
)


def _read_value(source: Any, key: str):
    if not source:
        return None
    if isinstance(source, Mapping):
        return source.get(key)
    return getattr(source, key, None)


def _clean_string(value: Any) -> str:
    return "" if value is None else str(value).strip()


def build_cliente_snapshot(cliente: Any, override: Mapping[str, Any] | None = None) -> dict:
    source = override or {}
    snapshot: dict[str, Any] = {}
    client_id = source.get("id") if isinstance(source, Mapping) and "id" in source else _read_value(cliente, "id")
    if client_id not in (None, ""):
        try:
            snapshot["id"] = int(client_id)
        except (TypeError, ValueError):
            pass
    for field in CLIENT_SNAPSHOT_STRING_FIELDS:
        value = source.get(field) if isinstance(source, Mapping) and field in source else _read_value(cliente, field)
        snapshot[field] = _clean_string(value)
    if not snapshot.get("razon_social") and snapshot.get("nombre_comercial"):
        snapshot["razon_social"] = snapshot["nombre_comercial"]
    if not snapshot.get("whatsapp") and snapshot.get("telefono"):
        snapshot["whatsapp"] = snapshot["telefono"]
    return snapshot


def resolve_document_cliente_snapshot(document: Any) -> dict:
    return build_cliente_snapshot(
        getattr(document, "cliente", None),
        getattr(document, "cliente_snapshot", None) or None,
    )
