"""crud/guias.py — Guías de Remisión."""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, not_, or_

import models
from access_control import can_access_all_tenant_resources
from services.document_flow_service import is_fiscal_document
from crud._base import (
    _get_tenant_resource,
    get_source_quote,
    get_latest_fiscal_document_for_quote,
)


def get_guias_remision(
    db: Session,
    usuario: models.User = None,
    skip: int = 0,
    limit: int = 15,
    *,
    estado: str | None = None,
    motivo: str | None = None,
    modalidad: str | None = None,
    desde=None,
    hasta=None,
    q: str | None = None,
):
    query = _build_guias_query(
        db,
        usuario,
        estado=estado,
        motivo=motivo,
        modalidad=modalidad,
        desde=desde,
        hasta=hasta,
        q=q,
    ).options(
        joinedload(models.GuiaRemision.cliente),
        joinedload(models.GuiaRemision.cotizacion).joinedload(models.Cotizacion.cliente),
    )
    query = query.order_by(desc(models.GuiaRemision.id))
    return query.offset(skip).limit(limit).all()


def _build_guias_query(
    db: Session,
    usuario: models.User = None,
    *,
    estado: str | None = None,
    motivo: str | None = None,
    modalidad: str | None = None,
    desde=None,
    hasta=None,
    q: str | None = None,
):
    query = db.query(models.GuiaRemision)
    if usuario and getattr(usuario, "tenant_id", None):
        query = query.filter(models.GuiaRemision.tenant_id == usuario.tenant_id)
    if usuario and not can_access_all_tenant_resources(usuario):
        query = query.filter(models.GuiaRemision.usuario_id == usuario.id)
    if estado:
        query = query.filter(models.GuiaRemision.estado == estado)
    if motivo:
        query = query.filter(models.GuiaRemision.motivo_traslado == motivo)
    if modalidad:
        query = query.filter(models.GuiaRemision.modalidad_traslado == modalidad)
    if desde:
        query = query.filter(models.GuiaRemision.fecha_traslado >= desde)
    if hasta:
        query = query.filter(models.GuiaRemision.fecha_traslado <= hasta)
    if q:
        term = f"%{q.strip()}%"
        query = query.outerjoin(models.GuiaRemision.cliente).filter(
            or_(
                models.GuiaRemision.serie.ilike(term),
                models.GuiaRemision.internal_order_number.ilike(term),
                models.GuiaRemision.partida_direccion.ilike(term),
                models.GuiaRemision.llegada_direccion.ilike(term),
                models.GuiaRemision.transportista_razon_social.ilike(term),
                models.Cliente.razon_social.ilike(term),
                models.Cliente.numero_documento.ilike(term),
            )
        )
    return query


def _tab_filter(query, tab: str | None):
    normalized = (tab or "all").strip().lower()
    status = func.lower(func.coalesce(models.GuiaRemision.estado, ""))
    is_smartpse = models.GuiaRemision.estado == "pendiente_smartpse"
    is_cancelled = status.like("%anulad%")
    is_transit = or_(status.like("%transit%"), status.like("%transito%"))
    is_emitted = status.like("%emitid%")

    if normalized == "smartpse":
        return query.filter(is_smartpse)
    if normalized == "pending":
        return query.filter(not_(or_(is_cancelled, is_transit, is_emitted)))
    if normalized == "transit":
        return query.filter(is_transit)
    if normalized == "emitted":
        return query.filter(is_emitted)
    if normalized in {"cancelled", "voided"}:
        return query.filter(is_cancelled)
    return query


def _count(query) -> int:
    return query.order_by(None).count()


def _guide_counts(base_query) -> dict:
    smartpse = _count(_tab_filter(base_query, "smartpse"))
    cancelled = _count(_tab_filter(base_query, "cancelled"))
    return {
        "all": _count(base_query),
        "pending": _count(_tab_filter(base_query, "pending")),
        "smartpse": smartpse,
        "transit": _count(_tab_filter(base_query, "transit")),
        "emitted": _count(_tab_filter(base_query, "emitted")),
        "cancelled": cancelled,
        "voided": cancelled,
    }


def get_guias_remision_page(
    db: Session,
    usuario: models.User = None,
    skip: int = 0,
    limit: int = 15,
    *,
    estado: str | None = None,
    motivo: str | None = None,
    modalidad: str | None = None,
    desde=None,
    hasta=None,
    q: str | None = None,
    tab: str | None = None,
) -> dict:
    base_query = _build_guias_query(
        db,
        usuario,
        estado=estado,
        motivo=motivo,
        modalidad=modalidad,
        desde=desde,
        hasta=hasta,
        q=q,
    )
    filtered_query = _tab_filter(base_query, tab)
    total = _count(filtered_query)
    items = (
        filtered_query
        .options(
            joinedload(models.GuiaRemision.cliente),
            joinedload(models.GuiaRemision.cotizacion).joinedload(models.Cotizacion.cliente),
        )
        .order_by(desc(models.GuiaRemision.id))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "counts": _guide_counts(base_query),
    }


def get_guia_remision(db: Session, guia_id: int, usuario: models.User = None):
    query = db.query(models.GuiaRemision)\
        .options(
            joinedload(models.GuiaRemision.items),
            joinedload(models.GuiaRemision.cliente),
            joinedload(models.GuiaRemision.cotizacion).joinedload(models.Cotizacion.cliente),
        )\
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
    cliente_id = data.get("cliente_id")
    source_quote_id = None
    fiscal_document_id = None
    internal_order_number = None

    if cliente_id is not None:
        cliente = _get_tenant_resource(db, models.Cliente, cliente_id, tenant_id)
        if not cliente:
            raise ValueError("El cliente destinatario no existe o no pertenece al tenant actual.")

    if cotizacion_id is not None:
        cotizacion = _get_tenant_resource(db, models.Cotizacion, cotizacion_id, tenant_id)
        if not cotizacion:
            raise ValueError("La cotizacion de origen no existe o no pertenece al tenant actual.")
        if cliente_id is None and getattr(cotizacion, "cliente_id", None):
            data["cliente_id"] = cotizacion.cliente_id

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
        db_guia.sunat_xml_content = data_sunat.get("xml") or data_sunat.get("sunat_xml_content")
        db_guia.sunat_hash = data_sunat.get("hash") or data_sunat.get("sunat_hash")
        db_guia.sunat_ticket = data_sunat.get("ticket") or data_sunat.get("sunat_ticket")
        db_guia.provider_response = data_sunat.get("provider_response")
        db_guia.provider_endpoint = data_sunat.get("provider_endpoint")
        db_guia.provider_status_code = data_sunat.get("provider_status_code")
        if data_sunat.get("success"):
            db_guia.estado = "pendiente_smartpse" if data_sunat.get("pending") else "emitida"
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
