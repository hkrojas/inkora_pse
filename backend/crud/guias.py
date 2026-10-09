"""crud/guias.py — Guías de Remisión."""
from datetime import datetime
from sqlalchemy.orm import Session, joinedload, aliased
from sqlalchemy import and_, case, desc, func, not_, or_
from schemas.guias import GuiaRemisionListResponse

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
    tipo_documento: str | None = None,
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
        tipo_documento=tipo_documento,
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
    tipo_documento: str | None = None,
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
    if tipo_documento:
        query = query.filter(models.GuiaRemision.tipo_documento == tipo_documento)
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
        query = query.outerjoin(models.Cliente, and_(
            models.Cliente.id == models.GuiaRemision.cliente_id,
            models.Cliente.tenant_id == models.GuiaRemision.tenant_id,
        )).filter(
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


def _guide_tab_conditions():
    status = func.lower(func.coalesce(models.GuiaRemision.estado, ""))
    is_smartpse = models.GuiaRemision.estado == "pendiente_smartpse"
    is_cancelled = status.like("%anulad%")
    is_transit = or_(status.like("%transit%"), status.like("%transito%"))
    is_emitted = status.like("%emitid%")

    return {"smartpse": is_smartpse,
            "pending": not_(or_(is_cancelled, is_transit, is_emitted)),
            "transit": is_transit, "emitted": is_emitted,
            "cancelled": is_cancelled, "voided": is_cancelled}


def _tab_filter(query, tab: str | None):
    condition = _guide_tab_conditions().get((tab or "all").strip().lower())
    return query if condition is None else query.filter(condition)


def _guide_counts(base_query) -> dict:
    conditions = _guide_tab_conditions()
    row = base_query.order_by(None).with_entities(
        func.count(models.GuiaRemision.id).label("all"),
        *(func.count(case((condition, 1))).label(name)
          for name, condition in conditions.items()),
    ).one()
    return dict(row._mapping)


def _guide_list_projection(query):
    guide = models.GuiaRemision
    client = aliased(models.Cliente)
    quote = aliased(models.Cotizacion)
    quote_client = aliased(models.Cliente)
    columns = [getattr(guide, name) for name in GuiaRemisionListResponse.model_fields
               if name not in {"cliente_nombre", "cliente_documento"}]
    def name(client):
        return func.nullif(client.razon_social, "")
    return query.with_entities(
        *columns,
        case((client.id.isnot(None), name(client)), else_=name(quote_client)).label("cliente_nombre"),
        case((client.id.isnot(None), func.nullif(client.numero_documento, "")),
             else_=func.nullif(quote_client.numero_documento, "")).label("cliente_documento"),
    ).outerjoin(client, and_(client.id == guide.cliente_id, client.tenant_id == guide.tenant_id)
    ).outerjoin(quote, and_(quote.id == guide.cotizacion_id, quote.tenant_id == guide.tenant_id)
    ).outerjoin(quote_client, and_(quote_client.id == quote.cliente_id, quote_client.tenant_id == guide.tenant_id))


def get_guias_remision_page(
    db: Session,
    usuario: models.User = None,
    skip: int = 0,
    limit: int = 15,
    *,
    estado: str | None = None,
    tipo_documento: str | None = None,
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
        tipo_documento=tipo_documento,
        motivo=motivo,
        modalidad=modalidad,
        desde=desde,
        hasta=hasta,
        q=q,
    )
    filtered_query = _tab_filter(base_query, tab)
    counts = _guide_counts(base_query)
    total = counts.get((tab or "all").strip().lower(), counts["all"])
    items = (
        _guide_list_projection(filtered_query)
        .order_by(desc(models.GuiaRemision.id))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {
        "items": [dict(row._mapping) for row in items],
        "total": total,
        "skip": skip,
        "limit": limit,
        "counts": counts,
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

    from services.guide_series_service import guide_series, next_guide_correlativo

    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).with_for_update().first()
    if not tenant or not tenant.is_active:
        raise ValueError("La empresa no está activa para crear guías.")
    document_type = str(data.get("tipo_documento") or "09")
    environment, serie = guide_series(tenant, document_type)
    nuevo_correlativo = next_guide_correlativo(db, tenant_id, document_type, serie)
    data.pop("serie", None)

    items_db = [models.GuiaRemisionItem(**item) for item in items_data]

    db_guia = models.GuiaRemision(
        **data,
        serie=serie,
        emission_environment=environment,
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
    commit: bool = True,
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
            db_guia.estado = "rechazada"
            db_guia.rejected_at = datetime.now()
        if commit:
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
