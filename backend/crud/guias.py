"""crud/guias.py — Guías de Remisión."""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

import models
from access_control import can_access_all_tenant_resources
from services.document_flow_service import is_fiscal_document
from crud._base import (
    _get_tenant_resource,
    get_source_quote,
    get_latest_fiscal_document_for_quote,
)


def get_guias_remision(db: Session, usuario: models.User = None, skip: int = 0, limit: int = 100):
    query = db.query(models.GuiaRemision)\
        .options(joinedload(models.GuiaRemision.items))\
        .order_by(desc(models.GuiaRemision.id))
    if usuario and getattr(usuario, "tenant_id", None):
        query = query.filter(models.GuiaRemision.tenant_id == usuario.tenant_id)
    if usuario and not can_access_all_tenant_resources(usuario):
        query = query.filter(models.GuiaRemision.usuario_id == usuario.id)
    return query.offset(skip).limit(limit).all()


def get_guia_remision(db: Session, guia_id: int, usuario: models.User = None):
    query = db.query(models.GuiaRemision)\
        .options(joinedload(models.GuiaRemision.items))\
        .filter(models.GuiaRemision.id == guia_id)
    if usuario and getattr(usuario, "tenant_id", None):
        query = query.filter(models.GuiaRemision.tenant_id == usuario.tenant_id)
    if usuario and not can_access_all_tenant_resources(usuario):
        query = query.filter(models.GuiaRemision.usuario_id == usuario.id)
    return query.first()


def create_guia_remision(db: Session, data: dict, usuario_id: int, tenant_id: int):
    """Crea una guia de remision.

    Envuelto con retry transparente para colisiones de correlativo (Fase A).
    """
    from crud._base import _retry_on_correlativo_conflict
    return _retry_on_correlativo_conflict(
        _create_guia_remision_inner,
        db, data, usuario_id, tenant_id,
    )


def _create_guia_remision_inner(db: Session, data: dict, usuario_id: int, tenant_id: int):
    """Implementacion interna — llamada por el wrapper con retry."""
    items_data = data.pop("items", [])
    cotizacion_id = data.get("cotizacion_id")
    source_quote_id = None
    fiscal_document_id = None
    internal_order_number = None

    if cotizacion_id is not None:
        cotizacion = _get_tenant_resource(db, models.Cotizacion, cotizacion_id, tenant_id)
        if not cotizacion:
            raise ValueError("La cotizacion de origen no existe o no pertenece al tenant actual.")

        source_quote = get_source_quote(db, cotizacion)
        if source_quote:
            source_quote_id = source_quote.id
            internal_order_number = source_quote.internal_order_number

        if is_fiscal_document(cotizacion):
            fiscal_document_id = cotizacion.id
        elif source_quote_id:
            fiscal_document = get_latest_fiscal_document_for_quote(db, source_quote_id, tenant_id)
            if fiscal_document:
                fiscal_document_id = fiscal_document.id

    serie = data.get("serie") or "T001"

    last_guia = db.query(models.GuiaRemision).filter(
        models.GuiaRemision.tenant_id == tenant_id,
        models.GuiaRemision.serie == serie
    ).order_by(models.GuiaRemision.correlativo.desc()).with_for_update().first()

    ultimo_correlativo_guia = last_guia.correlativo if last_guia else 0
    nuevo_correlativo = ultimo_correlativo_guia + 1

    items_db = [models.GuiaRemisionItem(**item) for item in items_data]

    db_guia = models.GuiaRemision(
        **data,
        serie=serie,
        source_quote_id=source_quote_id,
        fiscal_document_id=fiscal_document_id,
        internal_order_number=internal_order_number,
        usuario_id=usuario_id,
        tenant_id=tenant_id,
        correlativo=nuevo_correlativo,
        items=items_db
    )

    try:
        db.add(db_guia)
        db.commit()
        db.refresh(db_guia)
        return get_guia_remision(db, db_guia.id)
    except Exception as e:
        db.rollback()
        raise e


def guardar_respuesta_sunat_gre(
    db: Session,
    guia_id: int,
    data_sunat: dict,
    tenant_id: int | None = None,
):
    query = db.query(models.GuiaRemision).filter(models.GuiaRemision.id == guia_id)
    if tenant_id is not None:
        query = query.filter(models.GuiaRemision.tenant_id == tenant_id)
    db_guia = query.first()
    if db_guia:
        links = data_sunat.get("links", {}) or data_sunat.get("sunat_response", {}).get("links", {})
        if links:
            db_guia.sunat_xml_url = links.get("xml")
            db_guia.sunat_pdf_url = links.get("pdf")
            db_guia.sunat_cdr_url = links.get("cdr")
        if data_sunat.get("success"):
            db_guia.estado = "emitida"
            db_guia.sunat_error = None
        else:
            error = (
                data_sunat.get("sunat_error")
                or data_sunat.get("message")
                or data_sunat.get("sunat_response", {}).get("error")
                or data_sunat.get("provider_response", {}).get("error")
            )
            db_guia.sunat_error = str(error) if error else "El proveedor fiscal rechazo la guia."
        db.commit()
        db.refresh(db_guia)
    return db_guia


def guardar_error_sunat_gre(
    db: Session,
    guia_id: int,
    error: str,
    tenant_id: int | None = None,
):
    query = db.query(models.GuiaRemision).filter(models.GuiaRemision.id == guia_id)
    if tenant_id is not None:
        query = query.filter(models.GuiaRemision.tenant_id == tenant_id)
    db_guia = query.first()
    if db_guia:
        db_guia.sunat_error = str(error)
        db.commit()
        db.refresh(db_guia)
    return db_guia
