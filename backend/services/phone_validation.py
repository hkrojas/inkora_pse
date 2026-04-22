"""Validacion de celulares peruanos."""

from __future__ import annotations

from typing import Any, Optional


def digits_only(value: Any) -> str:
    return "".join(char for char in str(value or "") if char.isdigit())


def normalize_peru_mobile(value: Any) -> str:
    digits = digits_only(value)
    if not digits:
        return ""
    if digits.startswith("51"):
        return digits[2:11]
    return digits[:9]


def validate_optional_peru_mobile(value: Any, label: str) -> Optional[str]:
    normalized = normalize_peru_mobile(value)
    if not normalized:
        return None
    if len(normalized) != 9:
        return f"{label} debe tener 9 digitos."
    if not normalized.startswith("9"):
        return f"{label} debe iniciar en 9."
    return None


def normalize_and_validate_optional_peru_mobile(value: Any, label: str) -> Optional[str]:
    normalized = normalize_peru_mobile(value)
    error = validate_optional_peru_mobile(normalized, label)
    if error:
        raise ValueError(error)
    return normalized or None
