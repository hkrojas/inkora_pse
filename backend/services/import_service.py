"""
import_service.py — Fase 8: Onboarding Acceleration

Importación masiva de clientes y productos desde archivos CSV o Excel (.xlsx).

Diseño:
  - parse_clientes(ext, raw_bytes) -> (filas_validas, errores)
  - parse_productos(ext, raw_bytes) -> (filas_validas, errores)
  - El caller (router) es responsable de deduplicar y persistir.

Columnas CSV/Excel para clientes:
  Requeridas : numero_documento, razon_social
  Opcionales : tipo_documento, nombre_comercial, direccion, email, telefono,
               whatsapp, contacto, condicion_pago, direccion_entrega, observaciones

Columnas CSV/Excel para productos:
  Requeridas : nombre, precio_unitario
  Opcionales : codigo_interno, descripcion, unidad_medida, tipo_afectacion_igv,
               precio_incluye_igv, moneda
"""

import csv
import io
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import List, Optional

from fiscal_catalogs import (
    normalize_internal_product_code,
    normalize_sunat_unit_code,
    normalize_tax_affectation_code,
)

try:
    import openpyxl
    _HAS_OPENPYXL = True
except ImportError:
    _HAS_OPENPYXL = False


# ---------------------------------------------------------------------------
# Tipos de retorno
# ---------------------------------------------------------------------------

@dataclass
class FilaClienteParseada:
    numero_documento: str
    razon_social: str
    tipo_documento: str = "1"
    nombre_comercial: Optional[str] = None
    direccion: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    whatsapp: Optional[str] = None
    contacto: Optional[str] = None
    condicion_pago: Optional[str] = None
    direccion_entrega: Optional[str] = None
    observaciones: Optional[str] = None


@dataclass
class FilaProductoParseada:
    nombre: str
    precio_unitario: Decimal
    codigo_interno: Optional[str] = None
    descripcion: Optional[str] = None
    moneda: str = "PEN"
    unidad_medida: str = "NIU"
    tipo_afectacion_igv: str = "10"
    precio_incluye_igv: bool = True


# ---------------------------------------------------------------------------
# Constantes de validación
# ---------------------------------------------------------------------------

_CONDICION_PAGO_VALIDAS = {"contado", "credito_7", "credito_15", "credito_30", "credito_60"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _str(val) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _rows_from_csv(raw_bytes: bytes) -> list[dict]:
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return [row for row in reader]


def _rows_from_excel(raw_bytes: bytes) -> list[dict]:
    if not _HAS_OPENPYXL:
        raise RuntimeError("openpyxl no está instalado. Instálelo con: pip install openpyxl")
    wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [_str(h).lower() if h is not None else "" for h in rows[0]]
    result = []
    for row in rows[1:]:
        if all(v is None for v in row):
            continue
        result.append({headers[i]: _str(row[i]) if i < len(row) else "" for i in range(len(headers))})
    return result


def _parse_rows(ext: str, raw_bytes: bytes) -> list[dict]:
    if ext == "csv":
        return _rows_from_csv(raw_bytes)
    return _rows_from_excel(raw_bytes)


def _normalize_row(row: dict) -> dict:
    """Normaliza claves: lower + strip."""
    return {k.lower().strip(): _str(v) for k, v in row.items()}


def _get_field(row: dict, *aliases: str) -> str:
    """Busca el valor de un campo por múltiples nombres de columna posibles."""
    for alias in aliases:
        val = row.get(alias, "")
        if val:
            return val
    return ""


def _parse_bool(val, *, default: bool = True) -> bool:
    normalized = _str(val).lower().replace("-", "_").replace(" ", "_")
    if not normalized:
        return default

    truthy = {
        "1", "true", "t", "si", "sí", "yes", "y",
        "con_igv", "incluye_igv", "precio_con_igv", "bruto",
    }
    falsy = {
        "0", "false", "f", "no", "n",
        "sin_igv", "precio_sin_igv", "neto", "base",
    }

    if normalized in truthy:
        return True
    if normalized in falsy:
        return False
    return default


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------

def parse_clientes(
    ext: str, raw_bytes: bytes
) -> tuple[list[FilaClienteParseada], list[dict]]:
    """
    Parsea un archivo CSV/Excel de clientes.

    Retorna:
        (filas_validas, errores)
        - filas_validas: lista de FilaClienteParseada listos para insertar.
        - errores: lista de dicts {fila, campo, mensaje} para filas rechazadas.
    """
    rows = _parse_rows(ext, raw_bytes)
    validas: list[FilaClienteParseada] = []
    errores: list[dict] = []

    for i, raw_row in enumerate(rows, start=2):  # fila 1 = cabecera
        row = _normalize_row(raw_row)

        num_doc = _get_field(row, "numero_documento", "nro_documento", "documento", "ruc", "dni")
        razon = _get_field(row, "razon_social", "razón_social", "nombre", "nombre_o_razon_social")

        if not num_doc:
            errores.append({"fila": i, "campo": "numero_documento", "mensaje": "Campo requerido vacío."})
            continue
        if not razon:
            errores.append({"fila": i, "campo": "razon_social", "mensaje": "Campo requerido vacío."})
            continue

        # Inferir tipo_documento si no se provee
        tipo_doc = _get_field(row, "tipo_documento")
        if not tipo_doc:
            tipo_doc = "6" if len(num_doc) == 11 else "1"

        condicion = _get_field(row, "condicion_pago").lower() or None
        if condicion and condicion not in _CONDICION_PAGO_VALIDAS:
            condicion = None  # valor inválido silenciado; no rechaza la fila

        validas.append(FilaClienteParseada(
            numero_documento=num_doc,
            razon_social=razon,
            tipo_documento=tipo_doc,
            nombre_comercial=_get_field(row, "nombre_comercial") or None,
            direccion=_get_field(row, "direccion", "dirección", "direccion_fiscal") or None,
            email=_get_field(row, "email", "correo", "correo_electronico") or None,
            telefono=_get_field(row, "telefono", "teléfono", "phone") or None,
            whatsapp=_get_field(row, "whatsapp") or None,
            contacto=_get_field(row, "contacto", "nombre_contacto") or None,
            condicion_pago=condicion,
            direccion_entrega=_get_field(row, "direccion_entrega", "dirección_entrega") or None,
            observaciones=_get_field(row, "observaciones", "notas") or None,
        ))

    return validas, errores


# ---------------------------------------------------------------------------
# Productos
# ---------------------------------------------------------------------------

def parse_productos(
    ext: str, raw_bytes: bytes
) -> tuple[list[FilaProductoParseada], list[dict]]:
    """
    Parsea un archivo CSV/Excel de productos.

    Retorna:
        (filas_validas, errores)
        - filas_validas: lista de FilaProductoParseada listos para insertar.
        - errores: lista de dicts {fila, campo, mensaje} para filas rechazadas.
    """
    rows = _parse_rows(ext, raw_bytes)
    validas: list[FilaProductoParseada] = []
    errores: list[dict] = []

    for i, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)

        nombre = _get_field(row, "nombre", "producto", "descripcion_producto")
        precio_raw = _get_field(row, "precio_unitario", "precio", "precio_unit", "price")

        if not nombre:
            errores.append({"fila": i, "campo": "nombre", "mensaje": "Campo requerido vacío."})
            continue
        if not precio_raw:
            errores.append({"fila": i, "campo": "precio_unitario", "mensaje": "Campo requerido vacío."})
            continue

        try:
            precio = Decimal(precio_raw.replace(",", "."))
            if precio <= 0:
                raise ValueError("El precio debe ser mayor a cero.")
        except (InvalidOperation, ValueError) as exc:
            errores.append({
                "fila": i,
                "campo": "precio_unitario",
                "mensaje": f"Valor inválido: '{precio_raw}'. Debe ser un número positivo. ({exc})",
            })
            continue

        codigo_interno = _get_field(row, "codigo_interno", "código_interno", "codigo", "sku") or None
        unidad_medida = _get_field(row, "unidad_medida") or "NIU"
        tipo_afectacion_igv = _get_field(row, "tipo_afectacion_igv") or "10"

        try:
            codigo_interno = normalize_internal_product_code(codigo_interno)
            unidad_medida = normalize_sunat_unit_code(unidad_medida)
            tipo_afectacion_igv = normalize_tax_affectation_code(tipo_afectacion_igv)
        except ValueError as exc:
            errores.append({
                "fila": i,
                "campo": "datos_sunat",
                "mensaje": str(exc),
            })
            continue

        validas.append(FilaProductoParseada(
            nombre=nombre,
            precio_unitario=precio,
            codigo_interno=codigo_interno,
            descripcion=_get_field(row, "descripcion", "descripción", "detalle") or None,
            moneda=(_get_field(row, "moneda") or "PEN").upper(),
            unidad_medida=unidad_medida,
            tipo_afectacion_igv=tipo_afectacion_igv,
            precio_incluye_igv=_parse_bool(
                _get_field(row, "precio_incluye_igv", "precio_con_igv", "incluye_igv"),
                default=True,
            ),
        ))

    return validas, errores
