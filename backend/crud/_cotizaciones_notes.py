from __future__ import annotations

from sqlalchemy.orm import Session

import models
from crud._base import _retry_on_correlativo_conflict
from crud._cotizaciones_shared import (
    _build_note_document,
    _next_note_correlativo,
    _resolve_note_series,
)
from services.document_flow_service import DOCUMENT_STATUS_ISSUED


def crear_nota_credito_debito(
    db: Session,
    doc_afectado: models.Cotizacion,
    usuario_id: int,
    tipo_nota: str,
    cod_motivo: str,
    descripcion_motivo: str,
):
    return _retry_on_correlativo_conflict(
        _crear_nota_credito_debito_inner,
        db,
        doc_afectado,
        usuario_id,
        tipo_nota,
        cod_motivo,
        descripcion_motivo,
    )


def _crear_nota_credito_debito_inner(
    db: Session,
    doc_afectado: models.Cotizacion,
    usuario_id: int,
    tipo_nota: str,
    cod_motivo: str,
    descripcion_motivo: str,
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

    if doc_afectado.estado != DOCUMENT_STATUS_ISSUED:
        raise ValueError(
            "El documento debe estar en estado 'facturada' para emitir una nota. "
            f"Estado actual: '{doc_afectado.estado}'."
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
    )

    try:
        db.add(db_nota)
        db.commit()
        db.refresh(db_nota)
        return db_nota
    except Exception as exc:
        db.rollback()
        raise exc
