from __future__ import annotations

from sqlalchemy.orm import Session

import models
from crud._base import (
    _get_tenant_resource,
    _next_correlativo_for_series,
    _retry_on_correlativo_conflict,
    get_latest_fiscal_document_for_quote,
)
from crud._cotizaciones_quotes import get_cotizacion
from crud._cotizaciones_shared import (
    _build_fiscal_document,
    _ensure_quote_has_no_active_fiscal_document,
    _ensure_subscription_capacity,
    _extract_provider_links,
    _lock_quote_for_fiscal_creation,
    _resolve_provider_error_message,
    _resolve_fiscal_series,
)
from services.document_flow_service import (
    DOCUMENT_KIND_CREDIT_NOTE,
    DOCUMENT_KIND_FISCAL_DOCUMENT,
    DOCUMENT_STATUS_ISSUED,
    DOCUMENT_STATUS_PENDING,
    DOCUMENT_STATUS_VOIDED,
    is_quote_document,
)
from services.fiscal_balance_service import ensure_credit_note_within_available_amount


def create_fiscal_document_from_quote(
    db: Session,
    quote: models.Cotizacion,
    usuario_id: int,
    tipo_comprobante: str,
    serie_override: str | None = None,
):
    return _retry_on_correlativo_conflict(
        _create_fiscal_document_from_quote_inner,
        db,
        quote,
        usuario_id,
        tipo_comprobante,
        serie_override,
    )


def _create_fiscal_document_from_quote_inner(
    db: Session,
    quote: models.Cotizacion,
    usuario_id: int,
    tipo_comprobante: str,
    serie_override: str | None = None,
):
    if not is_quote_document(quote):
        raise ValueError("Solo se puede facturar una cotizacion comercial.")

    quote = _lock_quote_for_fiscal_creation(db, quote)
    _ensure_quote_has_no_active_fiscal_document(db, quote)
    _ensure_subscription_capacity(db, quote.tenant_id)

    serie = _resolve_fiscal_series(tipo_comprobante, serie_override)
    nuevo_correlativo = _next_correlativo_for_series(db, quote.tenant_id, serie)
    fiscal_document = _build_fiscal_document(
        quote,
        usuario_id,
        tipo_comprobante,
        serie,
        nuevo_correlativo,
    )

    try:
        db.add(fiscal_document)
        db.flush()
        db.commit()
        db.refresh(fiscal_document)
        return get_cotizacion(db, fiscal_document.id)
    except Exception as exc:
        db.rollback()
        raise exc


def guardar_respuesta_sunat(
    db: Session,
    cotizacion_id: int,
    data_sunat: dict,
    tenant_id: int | None = None,
):
    query = db.query(models.Cotizacion).filter(models.Cotizacion.id == cotizacion_id)
    if tenant_id is not None:
        query = query.filter(models.Cotizacion.tenant_id == tenant_id)
    db_cot = query.first()
    if db_cot:
        was_issued = db_cot.estado == DOCUMENT_STATUS_ISSUED
        links = _extract_provider_links(data_sunat)
        if links:
            db_cot.sunat_xml_url = links.get("xml")
            db_cot.sunat_cdr_url = links.get("cdr")

        if data_sunat.get("xml"):
            db_cot.sunat_xml_content = data_sunat.get("xml")
        if data_sunat.get("hash"):
            db_cot.sunat_hash = data_sunat.get("hash")
        if data_sunat.get("qr_payload"):
            db_cot.sunat_qr_payload = data_sunat.get("qr_payload")
        if data_sunat.get("qr_svg"):
            db_cot.sunat_qr_svg = data_sunat.get("qr_svg")

        if (
            data_sunat.get("success")
            and (
                db_cot.document_kind == DOCUMENT_KIND_CREDIT_NOTE
                or db_cot.tipo_comprobante == "07"
            )
        ):
            try:
                ensure_credit_note_within_available_amount(
                    db,
                    db_cot.tenant_id,
                    db_cot.id,
                )
            except ValueError as exc:
                db_cot.sunat_error = str(exc)
                db.commit()
                db.refresh(db_cot)
                return db_cot

        if data_sunat.get("success"):
            db_cot.estado = DOCUMENT_STATUS_ISSUED
            db_cot.sunat_error = None
        else:
            db_cot.sunat_error = _resolve_provider_error_message(data_sunat)

        if data_sunat.get("serie"):
            db_cot.serie = data_sunat.get("serie")
        if data_sunat.get("correlativo"):
            try:
                db_cot.correlativo = int(data_sunat.get("correlativo"))
            except Exception:
                pass

        if data_sunat.get("success") and db_cot.source_quote_id:
            source_quote = _get_tenant_resource(
                db,
                models.Cotizacion,
                db_cot.source_quote_id,
                db_cot.tenant_id,
            )
            if source_quote:
                source_quote.estado = DOCUMENT_STATUS_ISSUED

        if (
            data_sunat.get("success")
            and db_cot.document_kind == DOCUMENT_KIND_FISCAL_DOCUMENT
        ):
            from crud.pagos import apply_prefiscal_advances_to_fiscal_document

            apply_prefiscal_advances_to_fiscal_document(
                db,
                db_cot.tenant_id,
                db_cot.id,
                commit=False,
            )

        if (
            data_sunat.get("success")
            and not was_issued
            and db_cot.document_kind == DOCUMENT_KIND_FISCAL_DOCUMENT
        ):
            from sqlalchemy import update as _update

            db.execute(
                _update(models.Subscription)
                .where(models.Subscription.tenant_id == db_cot.tenant_id)
                .values(documents_used=models.Subscription.documents_used + 1)
            )

        db.commit()
        db.refresh(db_cot)
    return db_cot


def guardar_error_sunat(
    db: Session,
    cotizacion_id: int,
    error: str,
    tenant_id: int | None = None,
):
    query = db.query(models.Cotizacion).filter(models.Cotizacion.id == cotizacion_id)
    if tenant_id is not None:
        query = query.filter(models.Cotizacion.tenant_id == tenant_id)
    db_cot = query.first()
    if db_cot:
        db_cot.sunat_error = str(error)
        db.commit()
        db.refresh(db_cot)
    return db_cot


def anular_cotizacion(
    db: Session,
    cotizacion_id: int,
    tenant_id: int | None = None,
):
    query = db.query(models.Cotizacion).filter(models.Cotizacion.id == cotizacion_id)
    if tenant_id is not None:
        query = query.filter(models.Cotizacion.tenant_id == tenant_id)
    db_cot = query.with_for_update().first()
    if not db_cot:
        return None

    if db_cot.estado == DOCUMENT_STATUS_VOIDED:
        return db_cot

    try:
        db_cot.estado = DOCUMENT_STATUS_VOIDED
        if db_cot.source_quote_id:
            source_quote = (
                db.query(models.Cotizacion)
                .filter(
                    models.Cotizacion.id == db_cot.source_quote_id,
                    models.Cotizacion.tenant_id == db_cot.tenant_id,
                )
                .with_for_update()
                .first()
            )
            if source_quote:
                fiscal_document_restante = get_latest_fiscal_document_for_quote(
                    db,
                    source_quote.id,
                    source_quote.tenant_id,
                )
                if (
                    not fiscal_document_restante
                    or fiscal_document_restante.id == db_cot.id
                    or fiscal_document_restante.estado == DOCUMENT_STATUS_VOIDED
                ):
                    source_quote.estado = DOCUMENT_STATUS_PENDING
        db.commit()
        db.refresh(db_cot)
        return db_cot
    except Exception as exc:
        db.rollback()
        raise exc
