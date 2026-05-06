"""Catalogos SUNAT usados por los flujos de lanzamiento."""

from __future__ import annotations

import re


PRODUCT_INTERNAL_CODE_MAX_LENGTH = 30
PRODUCT_NAME_MAX_LENGTH = 160
PRODUCT_DESCRIPTION_MAX_LENGTH = 1000

_PRODUCT_CODE_RE = re.compile(r"^[A-Z0-9._/-]+$")

# Subconjunto operativo del catalogo 03 suficiente para imprentas.
# Los codigos siguen UN/ECE Rec 20 y deben enviarse con longitud an..3.
SUNAT_UNIT_CODES = {
    "NIU",  # Unidad (bienes)
    "ZZ",   # Unidad (servicios)
    "BG",   # Bolsa
    "BX",   # Caja
    "C62",  # Pieza
    "CEN",  # Ciento de unidades
    "GRM",  # Gramo
    "KGM",  # Kilogramo
    "KT",   # Kit
    "LEF",  # Hoja
    "LTR",  # Litro
    "MLL",  # Millares
    "MTR",  # Metro
    "MTK",  # Metro cuadrado
    "MTQ",  # Metro cubico
    "PK",   # Paquete
    "RM",   # Resma
    "SET",  # Juego
    "ST",   # Pliego
    "TNE",  # Tonelada
}

SUNAT_UNIT_ALIASES = {
    "MIL": "MLL",
}

# Alcance de lanzamiento: ventas internas gravadas, exoneradas o inafectas.
SUNAT_TAX_AFFECTATION_CODES = {
    "10",  # Gravado - operacion onerosa
    "20",  # Exonerado - operacion onerosa
    "30",  # Inafecto - operacion onerosa
}

GRAVADO_IGV_CODES = {"10"}
EXONERADO_IGV_CODES = {"20"}
INAFECTO_IGV_CODES = {"30"}


def normalize_sunat_unit_code(value: str | None) -> str:
    normalized = (value or "NIU").strip().upper()
    normalized = SUNAT_UNIT_ALIASES.get(normalized, normalized)
    if normalized not in SUNAT_UNIT_CODES:
        raise ValueError("La unidad de medida debe pertenecer al Catalogo SUNAT 03")
    return normalized


def normalize_tax_affectation_code(value: str | None) -> str:
    normalized = (value or "10").strip()
    if normalized not in SUNAT_TAX_AFFECTATION_CODES:
        raise ValueError(
            "Tipo de afectacion IGV no soportado. Usa 10, 20 o 30."
        )
    return normalized


def normalize_internal_product_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().upper()
    if not normalized:
        return None
    if len(normalized) > PRODUCT_INTERNAL_CODE_MAX_LENGTH:
        raise ValueError("El codigo interno debe tener 30 caracteres como maximo")
    if not _PRODUCT_CODE_RE.match(normalized):
        raise ValueError(
            "El codigo interno solo puede usar letras, numeros, punto, guion, slash o guion bajo"
        )
    return normalized


def tax_affectation_bucket(code: str | None) -> str:
    normalized = normalize_tax_affectation_code(code)
    if normalized in EXONERADO_IGV_CODES:
        return "exonerada"
    if normalized in INAFECTO_IGV_CODES:
        return "inafecta"
    return "gravada"

