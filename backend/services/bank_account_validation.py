"""Validacion y normalizacion de cuentas bancarias del tenant."""

from __future__ import annotations

import re
import unicodedata
from hashlib import sha1
from typing import Any

from services.phone_validation import normalize_and_validate_optional_peru_mobile


def _text(value: Any) -> str:
    return str(value or "").strip()


def _digits(value: Any) -> str:
    return "".join(char for char in str(value or "") if char.isdigit())


def _key(value: Any) -> str:
    return unicodedata.normalize("NFD", _text(value)).encode("ascii", "ignore").decode("ascii").lower()


def _slug_token(value: Any) -> str:
    normalized = _key(value)
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def build_payment_method_id(raw_method: dict[str, Any], index: int, kind: str) -> str:
    explicit = _text(raw_method.get("id"))
    if explicit:
        return explicit

    if kind == "wallet":
        parts = [
            _slug_token(raw_method.get("proveedor")),
            _slug_token(raw_method.get("titular")),
            _digits(raw_method.get("numero") or raw_method.get("cuenta")),
            _slug_token(raw_method.get("nota")),
        ]
    else:
        parts = [
            _slug_token(raw_method.get("banco")),
            _slug_token(raw_method.get("tipo_cuenta")),
            _slug_token(raw_method.get("moneda")),
            _digits(raw_method.get("cuenta")),
            _digits(raw_method.get("cci")),
        ]

    visible_part = "-".join(part for part in parts if part)[:48].strip("-")
    if visible_part:
        return f"pm-{kind}-{index + 1}-{visible_part}"

    digest_source = "|".join(str(part or "") for part in parts)
    return f"pm-{kind}-{index + 1}-{sha1(digest_source.encode('utf-8')).hexdigest()[:12]}"


def _matches_bank(bank_key: str, *aliases: str) -> bool:
    return any(bank_key == alias or alias in bank_key for alias in aliases)


def _get_bank_rule(bank_name: Any, account_type: Any) -> dict[str, Any]:
    bank_key = _key(bank_name)
    account_type_key = _key(account_type)

    if _matches_bank(bank_key, "bcp", "credito del peru", "banco de credito del peru"):
        if "corriente" in account_type_key:
            return {"allowed_lengths": {13}, "description": "13 digitos para cuenta corriente BCP"}
        return {"allowed_lengths": {13, 14}, "description": "13 o 14 digitos segun el tipo de cuenta BCP"}

    if _matches_bank(bank_key, "bbva", "continental"):
        return {"allowed_lengths": {18, 20}, "description": "18 o 20 digitos para cuentas BBVA"}

    if _matches_bank(bank_key, "interbank"):
        return {"allowed_lengths": {13}, "description": "13 digitos para cuentas Interbank"}

    if _matches_bank(bank_key, "scotiabank", "scotia"):
        return {"allowed_lengths": {10, 14}, "description": "10 o 14 digitos para cuentas Scotiabank"}

    if _matches_bank(bank_key, "banco de la nacion", "nacion"):
        return {"allowed_lengths": {10, 13}, "description": "10 o 13 digitos para cuentas del Banco de la Nacion"}

    if _matches_bank(bank_key, "banbif"):
        return {"allowed_lengths": {10, 12}, "description": "10 o 12 digitos para cuentas BanBif"}

    if _matches_bank(bank_key, "pichincha"):
        return {"allowed_lengths": {12}, "description": "12 digitos para cuentas Banco Pichincha"}

    if _matches_bank(bank_key, "caja huancayo"):
        return {"allowed_lengths": {18}, "description": "18 digitos para cuentas Caja Huancayo"}

    return {"min_length": 6, "max_length": 20, "description": "entre 6 y 20 digitos"}


def validate_and_normalize_bank_accounts(methods: Any) -> Any:
    if methods is None:
        return None

    if not isinstance(methods, list):
        raise ValueError("bank_accounts debe ser una lista.")

    normalized_methods: list[dict[str, Any]] = []

    for index, raw_method in enumerate(methods):
        if not isinstance(raw_method, dict):
            raise ValueError(f"Cuenta bancaria {index + 1}: formato invalido.")

        raw_type = _key(raw_method.get("tipo"))
        is_wallet = raw_type == "wallet" or bool(_text(raw_method.get("proveedor")))

        if is_wallet:
            normalized_methods.append(
                {
                    "id": build_payment_method_id(raw_method, index, "wallet"),
                    "tipo": "wallet",
                    "proveedor": _text(raw_method.get("proveedor")),
                    "titular": _text(raw_method.get("titular")),
                    "numero": normalize_and_validate_optional_peru_mobile(
                        raw_method.get("numero") or raw_method.get("cuenta"),
                        f"Billetera digital {index + 1}: numero asociado",
                    ) or "",
                    "nota": _text(raw_method.get("nota")),
                }
            )
            continue

        bank_name = _text(raw_method.get("banco"))
        account_type = _text(raw_method.get("tipo_cuenta")) or "Cta Ahorro"
        currency = _text(raw_method.get("moneda")) or "Soles"
        account_raw = _text(raw_method.get("cuenta"))
        cci_raw = _text(raw_method.get("cci"))
        account_digits = _digits(account_raw)
        cci_digits = _digits(cci_raw)
        rule = _get_bank_rule(bank_name, account_type)

        if account_raw:
            allowed_lengths = rule.get("allowed_lengths")
            if allowed_lengths:
                if len(account_digits) not in allowed_lengths:
                    raise ValueError(
                        f"Cuenta bancaria {index + 1}: numero de cuenta invalido para "
                        f"{bank_name or 'el banco seleccionado'}; se esperan {rule['description']}."
                    )
            else:
                min_length = int(rule["min_length"])
                max_length = int(rule["max_length"])
                if len(account_digits) < min_length or len(account_digits) > max_length:
                    raise ValueError(
                        f"Cuenta bancaria {index + 1}: numero de cuenta invalido; "
                        f"debe tener {rule['description']}."
                    )

        if cci_raw and len(cci_digits) != 20:
            raise ValueError(
                f"Cuenta bancaria {index + 1}: el CCI debe tener exactamente 20 digitos."
            )

        normalized_methods.append(
            {
                "id": build_payment_method_id(raw_method, index, "bank"),
                "tipo": "bank",
                "banco": bank_name,
                "tipo_cuenta": account_type,
                "moneda": currency,
                "cuenta": account_digits,
                "cci": cci_digits,
            }
        )

    return normalized_methods
