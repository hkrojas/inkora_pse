"""Facade estable para cotizaciones, documentos fiscales y notas."""

from crud._cotizaciones_fiscal import (
    anular_cotizacion,
    create_fiscal_document_from_quote,
    guardar_error_sunat,
    guardar_respuesta_sunat,
)
from crud._cotizaciones_notes import crear_nota_credito_debito
from crud._cotizaciones_quotes import (
    create_cotizacion,
    delete_cotizacion,
    duplicate_cotizacion,
    get_cotizacion,
    get_cotizacion_by_uuid,
    get_cotizaciones,
)


__all__ = [
    "anular_cotizacion",
    "create_cotizacion",
    "create_fiscal_document_from_quote",
    "crear_nota_credito_debito",
    "delete_cotizacion",
    "duplicate_cotizacion",
    "get_cotizacion",
    "get_cotizacion_by_uuid",
    "get_cotizaciones",
    "guardar_error_sunat",
    "guardar_respuesta_sunat",
]
