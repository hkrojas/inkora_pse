from __future__ import annotations

from sqlalchemy.orm import Session

import models
from crud._base import _retry_on_correlativo_conflict
from crud._cotizaciones_shared import (
    _build_quote_item,
    _build_note_document,
    _next_note_correlativo,
    _resolve_note_series,
)
from services import calculations
from services.document_flow_service import (
    DOCUMENT_KIND_FISCAL_DOCUMENT,
    DOCUMENT_STATUS_ISSUED,
)
from services.fiscal_balance_service import get_credit_note_available_amount


def crear_nota_credito_debito(
    db: Session,
    doc_afectado: models.Cotizacion,
    usuario_id: int,
    tipo_nota: str,
    cod_motivo: str,
    descripcion_motivo: str,
    items=None,
    inventory_impact="none",
    inventory_return_warehouse_id=None,
):
    return _retry_on_correlativo_conflict(
        _crear_nota_credito_debito_inner,
        db,
        doc_afectado,
        usuario_id,
        tipo_nota,
        cod_motivo,
        descripcion_motivo,
        items,
        inventory_impact,
        inventory_return_warehouse_id,
    )


def _crear_nota_credito_debito_inner(
    db: Session,
    doc_afectado: models.Cotizacion,
    usuario_id: int,
    tipo_nota: str,
    cod_motivo: str,
    descripcion_motivo: str,
    items=None,
    inventory_impact="none",
    inventory_return_warehouse_id=None,
):
    doc_afectado = (
        db.query(models.Cotizacion)
        .filter(
            models.Cotizacion.id == doc_afectado.id,
            models.Cotizacion.tenant_id == doc_afectado.tenant_id,
        )
        .with_for_update()
        .first()
    )

    if not doc_afectado:
        raise ValueError("Comprobante afectado no encontrado para el tenant.")
    if doc_afectado.document_kind != DOCUMENT_KIND_FISCAL_DOCUMENT:
        raise ValueError("Solo se pueden emitir notas contra comprobantes fiscales.")
    if doc_afectado.estado != DOCUMENT_STATUS_ISSUED:
        raise ValueError(
            "El documento debe estar en estado 'facturada' para emitir una nota. "
            f"Estado actual: '{doc_afectado.estado}'."
        )

    note_items = None
    note_totals = None
    if items:
        note_items = []
        items_procesados = []
        for item in items:
            db_item, calculo = _build_quote_item(db, item, doc_afectado.tenant_id)
            note_items.append(db_item)
            items_procesados.append(calculo)
        note_totals = calculations.sumarizar_cotizacion(items_procesados)

    note_total = (
        note_totals["total_venta"] if note_totals is not None
        else doc_afectado.total_venta
    )
    if tipo_nota == "credito":
        disponible = get_credit_note_available_amount(
            db,
            doc_afectado.tenant_id,
            doc_afectado.id,
        )
        if note_total > disponible:
            raise ValueError(
                f"La nota de credito excede el monto fiscal disponible ({disponible})."
            )

    serie_nota = _resolve_note_series(doc_afectado.serie)
    nuevo_correlativo = _next_note_correlativo(
        db,
        doc_afectado.tenant_id,
        serie_nota,
    )
    db_nota = _build_note_document(
        doc_afectado,
        usuario_id,
        tipo_nota,
        cod_motivo,
        descripcion_motivo,
        serie_nota,
        nuevo_correlativo,
        items=note_items,
        totales=note_totals,
        inventory_impact=inventory_impact,
        inventory_return_warehouse_id=inventory_return_warehouse_id,
    )

    try:
        db.add(db_nota)
        db.commit()
        db.refresh(db_nota)
        return db_nota
    except Exception as exc:
        db.rollback()
        raise exc
