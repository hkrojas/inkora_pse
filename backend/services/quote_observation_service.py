"""Helpers para observaciones enriquecidas de cotizaciones."""

from __future__ import annotations

import json
from typing import Any


DEFAULT_NOTE_1_TEXT = "TODO TRABAJO SE REALIZA CON EL 50% DE ADELANTO"
DEFAULT_NOTE_2_TEXT = "LOS PRECIOS NO INCLUYEN ENVIOS"
DEFAULT_NOTE_1_COLOR = "#FF0000"
DEFAULT_NOTE_2_COLOR = "#111111"
DEFAULT_NOTE_1_BOLD = True
DEFAULT_NOTE_2_BOLD = False


def _normalize_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "si", "sí", "yes"}:
            return True
        if normalized in {"0", "false", "no"}:
            return False
    return default


def _normalize_color(value: Any, default: str) -> str:
    if not value:
        return default
    color = str(value).strip()
    if not color.startswith("#"):
        color = f"#{color}"
    if len(color) == 4:
        color = "#" + "".join(ch * 2 for ch in color[1:])
    if len(color) != 7:
        return default
    return color.upper()


def _normalize_line(line: Any, *, default_color: str, default_bold: bool) -> dict | None:
    if isinstance(line, str):
        text = line.strip()
        if not text:
            return None
        return {"text": text, "color": default_color, "bold": default_bold}

    if not isinstance(line, dict):
        return None

    text = str(line.get("text") or "").strip()
    if not text:
        return None

    return {
        "text": text,
        "color": _normalize_color(line.get("color"), default_color),
        "bold": _normalize_bool(line.get("bold"), default_bold),
    }


def _parse_tenant_default_config(value: Any) -> tuple[dict, str | None]:
    if isinstance(value, dict):
        return value, None

    if not isinstance(value, str):
        return {}, None

    raw = value.strip()
    if not raw:
        return {}, None

    if raw.startswith("{"):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed, None
        except Exception:
            pass

    return {}, value


def build_default_observation_lines(
    note_1_text: str | None = None,
    note_1_color: str | None = None,
    note_2_text: str | None = None,
) -> list[dict]:
    config, legacy_note_2_text = _parse_tenant_default_config(note_2_text)
    line_1_config = config.get("line_1") if isinstance(config.get("line_1"), dict) else {}
    line_2_config = config.get("line_2") if isinstance(config.get("line_2"), dict) else {}
    lines = []

    line_1 = _normalize_line(
        {
            "text": line_1_config.get("text") or note_1_text or DEFAULT_NOTE_1_TEXT,
            "color": line_1_config.get("color") or note_1_color or DEFAULT_NOTE_1_COLOR,
            "bold": line_1_config.get("bold") if "bold" in line_1_config else DEFAULT_NOTE_1_BOLD,
        },
        default_color=DEFAULT_NOTE_1_COLOR,
        default_bold=DEFAULT_NOTE_1_BOLD,
    )
    if line_1:
        lines.append(line_1)

    line_2 = _normalize_line(
        {
            "text": line_2_config.get("text") or legacy_note_2_text or DEFAULT_NOTE_2_TEXT,
            "color": line_2_config.get("color") or DEFAULT_NOTE_2_COLOR,
            "bold": line_2_config.get("bold") if "bold" in line_2_config else DEFAULT_NOTE_2_BOLD,
        },
        default_color=DEFAULT_NOTE_2_COLOR,
        default_bold=DEFAULT_NOTE_2_BOLD,
    )
    if line_2:
        lines.append(line_2)

    return lines


def parse_quote_observations(value: Any) -> list[dict]:
    if not value:
        return []

    if isinstance(value, list):
        return [
            normalized
            for item in value
            if (normalized := _normalize_line(item, default_color=DEFAULT_NOTE_2_COLOR, default_bold=False))
        ]

    if isinstance(value, dict):
        lines = value.get("lines") or []
        return parse_quote_observations(lines)

    if not isinstance(value, str):
        return []

    raw = value.strip()
    if not raw:
        return []

    if raw.startswith("{") or raw.startswith("["):
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = None
        if parsed is not None:
            return parse_quote_observations(parsed)

    return [
        normalized
        for line in raw.splitlines()
        if (normalized := _normalize_line(line, default_color=DEFAULT_NOTE_2_COLOR, default_bold=False))
    ]


def serialize_quote_observations(lines: list[dict]) -> str:
    normalized_lines = parse_quote_observations(lines)
    return json.dumps({"version": 1, "lines": normalized_lines}, ensure_ascii=False)


def observation_lines_to_plain_text(value: Any) -> str:
    return "\n".join(line["text"] for line in parse_quote_observations(value))
