"""crud/reportes.py — Dashboard, cobranza y reportes contables."""
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, case, func, or_


import models
from services.document_flow_service import (
    DOCUMENT_KIND_CREDIT_NOTE,
    DOCUMENT_KIND_DEBIT_NOTE,
    DOCUMENT_KIND_FISCAL_DOCUMENT,
    DOCUMENT_STATUS_ISSUED,
)


_ZERO = Decimal("0.00")
_MONEY_QUANT = Decimal("0.01")


def _money(value) -> Decimal:
    return Decimal(str(value if value is not None else _ZERO)).quantize(_MONEY_QUANT)


def _notes_total_subquery(db: Session, tenant_id: int, document_kind: str, name: str):
    return (
        db.query(
            models.Cotizacion.nota_referencia_id.label("fiscal_document_id"),
            func.sum(models.Cotizacion.total_venta).label("total"),
        )
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.nota_referencia_id.isnot(None),
            models.Cotizacion.document_kind == document_kind,
            models.Cotizacion.estado == DOCUMENT_STATUS_ISSUED,
        )
        .group_by(models.Cotizacion.nota_referencia_id)
        .subquery(name)
    )


def _primary_payments_total_subquery(
    db: Session,
    tenant_id: int,
    name: str,
    *,
    since: datetime | None = None,
):
    query = db.query(
        models.Pago.fiscal_document_id.label("fiscal_document_id"),
        func.sum(models.Pago.monto_pagado).label("total"),
    ).filter(
        models.Pago.tenant_id == tenant_id,
        models.Pago.fiscal_document_id.isnot(None),
    )
    if since is not None:
        query = query.filter(models.Pago.fecha_pago >= since)
    return query.group_by(models.Pago.fiscal_document_id).subquery(name)


def _legacy_payments_total_subquery(
    db: Session,
    tenant_id: int,
    name: str,
    *,
    since: datetime | None = None,
):
    query = db.query(
        models.Pago.source_quote_id.label("source_quote_id"),
        func.sum(models.Pago.monto_pagado).label("total"),
    ).filter(
        models.Pago.tenant_id == tenant_id,
        models.Pago.fiscal_document_id.is_(None),
        models.Pago.source_quote_id.isnot(None),
        models.Pago.tipo == "pago",
    )
    if since is not None:
        query = query.filter(models.Pago.fecha_pago >= since)
    return query.group_by(models.Pago.source_quote_id).subquery(name)


def _coalesce_money(value):
    return func.coalesce(value, _ZERO)


def _collection_totals(db: Session, tenant_id: int, *, include_monthly: bool = False):
    credit_notes = _notes_total_subquery(
        db,
        tenant_id,
        DOCUMENT_KIND_CREDIT_NOTE,
        "collection_credit_notes",
    )
    debit_notes = _notes_total_subquery(
        db,
        tenant_id,
        DOCUMENT_KIND_DEBIT_NOTE,
        "collection_debit_notes",
    )
    primary_payments = _primary_payments_total_subquery(
        db,
        tenant_id,
        "collection_primary_payments",
    )
    legacy_payments = _legacy_payments_total_subquery(
        db,
        tenant_id,
        "collection_legacy_payments",
    )

    monthly_primary_payments = None
    monthly_legacy_payments = None
    if include_monthly:
        ahora = datetime.now()
        inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_primary_payments = _primary_payments_total_subquery(
            db,
            tenant_id,
            "collection_monthly_primary_payments",
            since=inicio_mes,
        )
        monthly_legacy_payments = _legacy_payments_total_subquery(
            db,
            tenant_id,
            "collection_monthly_legacy_payments",
            since=inicio_mes,
        )

    document_total = _coalesce_money(models.Cotizacion.total_venta)
    credit_total = _coalesce_money(credit_notes.c.total)
    debit_total = _coalesce_money(debit_notes.c.total)
    primary_total = _coalesce_money(primary_payments.c.total)
    legacy_total = _coalesce_money(legacy_payments.c.total)

    net_total = document_total - credit_total + debit_total
    payments_total = primary_total + legacy_total
    saldo_pendiente = net_total - payments_total

    return SimpleNamespace(
        credit_notes=credit_notes,
        debit_notes=debit_notes,
        primary_payments=primary_payments,
        legacy_payments=legacy_payments,
        monthly_primary_payments=monthly_primary_payments,
        monthly_legacy_payments=monthly_legacy_payments,
        net_total=net_total,
        payments_total=payments_total,
        saldo_pendiente=saldo_pendiente,
    )


def _join_collection_totals(query, totals):
    query = (
        query.outerjoin(
            totals.credit_notes,
            totals.credit_notes.c.fiscal_document_id == models.Cotizacion.id,
        )
        .outerjoin(
            totals.debit_notes,
            totals.debit_notes.c.fiscal_document_id == models.Cotizacion.id,
        )
        .outerjoin(
            totals.primary_payments,
            totals.primary_payments.c.fiscal_document_id == models.Cotizacion.id,
        )
        .outerjoin(
            totals.legacy_payments,
            totals.legacy_payments.c.source_quote_id == models.Cotizacion.source_quote_id,
        )
    )
    if totals.monthly_primary_payments is not None:
        query = query.outerjoin(
            totals.monthly_primary_payments,
            totals.monthly_primary_payments.c.fiscal_document_id
            == models.Cotizacion.id,
        )
    if totals.monthly_legacy_payments is not None:
        query = query.outerjoin(
            totals.monthly_legacy_payments,
            totals.monthly_legacy_payments.c.source_quote_id
            == models.Cotizacion.source_quote_id,
        )
    return query


def _accepted_fiscal_filters(tenant_id: int):
    return (
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == DOCUMENT_KIND_FISCAL_DOCUMENT,
        models.Cotizacion.estado == DOCUMENT_STATUS_ISSUED,
        models.Cotizacion.tipo_comprobante.in_(("01", "03")),
    )


def get_dashboard_stats(db: Session, tenant_id: int):
    from datetime import datetime as _dt
    from decimal import Decimal as _D

    ingresos = db.query(func.sum(models.Pago.monto_pagado)).filter(
        models.Pago.tenant_id == tenant_id
    ).scalar() or _D("0")

    cobranza = get_cobranza_resumen(db, tenant_id)

    costos = db.query(func.sum(models.OrdenProduccion.costo_tercerizado)).filter(
        models.OrdenProduccion.tenant_id == tenant_id
    ).scalar() or _D("0")

    ahora = _dt.now()
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    emitidos_mes = db.query(func.count(models.Cotizacion.id)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "fiscal_document",
        models.Cotizacion.estado == "facturada",
        models.Cotizacion.fecha_emision >= inicio_mes,
    ).scalar() or 0

    top_productos_query = db.query(
        models.Producto.nombre
    ).join(
        models.CotizacionItem, models.Producto.id == models.CotizacionItem.producto_id
    ).join(
        models.Cotizacion, models.CotizacionItem.cotizacion_id == models.Cotizacion.id
    ).filter(
        models.Cotizacion.tenant_id == tenant_id
    ).group_by(
        models.Producto.id
    ).order_by(
        func.sum(models.CotizacionItem.cantidad).desc()
    ).limit(5).all()

    top_productos = [p.nombre for p in top_productos_query]

    return {
        "ingresos_totales": ingresos,
        "saldos_por_cobrar": cobranza["total_por_cobrar"],
        "saldo_vencido": cobranza["total_vencido"],
        "costos_tercerizacion": costos,
        "documentos_emitidos_mes": emitidos_mes,
        "documentos_vencidos": cobranza["documentos_vencidos"],
        "top_productos": top_productos,
    }


def get_cobranza_vencida(
    db: Session,
    tenant_id: int,
    skip: int = 0,
    limit: int = 100,
    q: str | None = None,
    scope: str = "overdue",
) -> list:
    ahora = datetime.now()

    if scope not in {"overdue", "active"}:
        raise ValueError("scope debe ser 'overdue' o 'active'")

    totals = _collection_totals(db, tenant_id)
    query = db.query(
        models.Cotizacion.id.label("id"),
        models.Cotizacion.serie.label("serie"),
        models.Cotizacion.correlativo.label("correlativo"),
        models.Cotizacion.fecha_emision.label("fecha_emision"),
        models.Cotizacion.fecha_vencimiento.label("fecha_vencimiento"),
        models.Cotizacion.moneda.label("moneda"),
        models.Cotizacion.estado.label("estado"),
        models.Cotizacion.document_kind.label("document_kind"),
        models.Cotizacion.tipo_comprobante.label("tipo_comprobante"),
        models.Cotizacion.internal_order_number.label("internal_order_number"),
        totals.net_total.label("total_venta"),
        totals.payments_total.label("monto_pagado"),
        totals.saldo_pendiente.label("saldo_pendiente"),
        models.Cliente.razon_social.label("cliente_nombre"),
        models.Cliente.nombre_comercial.label("cliente_nombre_alt"),
        models.Cliente.numero_documento.label("cliente_documento"),
    ).select_from(models.Cotizacion)
    query = _join_collection_totals(query, totals)
    query = query.outerjoin(
        models.Cliente,
        and_(
            models.Cotizacion.cliente_id == models.Cliente.id,
            models.Cliente.tenant_id == tenant_id,
        ),
    ).filter(
        *_accepted_fiscal_filters(tenant_id),
        models.Cotizacion.fecha_vencimiento.isnot(None),
        totals.saldo_pendiente > _ZERO,
    )

    if scope == "overdue":
        query = query.filter(models.Cotizacion.fecha_vencimiento < ahora)

    term = (q or "").strip()
    if term:
        like_term = f"%{term}%"
        query = query.filter(
            or_(
                models.Cliente.razon_social.ilike(like_term),
                models.Cliente.nombre_comercial.ilike(like_term),
                models.Cliente.numero_documento.ilike(like_term),
                models.Cotizacion.internal_order_number.ilike(like_term),
                models.Cotizacion.serie.ilike(like_term),
            )
        )

    rows = (
        query.order_by(
            models.Cotizacion.fecha_vencimiento.asc(),
            models.Cotizacion.id.asc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        SimpleNamespace(
            id=row.id,
            serie=row.serie,
            correlativo=row.correlativo,
            fecha_emision=row.fecha_emision,
            fecha_vencimiento=row.fecha_vencimiento,
            moneda=row.moneda,
            estado=row.estado,
            document_kind=row.document_kind,
            tipo_comprobante=row.tipo_comprobante,
            internal_order_number=row.internal_order_number,
            total_venta=_money(row.total_venta),
            monto_pagado=_money(row.monto_pagado),
            saldo_pendiente=_money(row.saldo_pendiente),
            cliente_nombre=row.cliente_nombre,
            cliente_nombre_alt=row.cliente_nombre_alt,
            cliente_documento=row.cliente_documento,
        )
        for row in rows
    ]


def get_cobranza_resumen(db: Session, tenant_id: int) -> dict:
    ahora = datetime.now()
    totals = _collection_totals(db, tenant_id, include_monthly=True)
    monthly_paid = _coalesce_money(totals.monthly_primary_payments.c.total) + _coalesce_money(
        totals.monthly_legacy_payments.c.total
    )
    has_debt = totals.saldo_pendiente > _ZERO
    is_overdue = and_(
        models.Cotizacion.fecha_vencimiento.isnot(None),
        models.Cotizacion.fecha_vencimiento < ahora,
    )
    is_pending = or_(
        models.Cotizacion.fecha_vencimiento.is_(None),
        models.Cotizacion.fecha_vencimiento >= ahora,
    )

    query = db.query(
        func.sum(
            case((has_debt, totals.saldo_pendiente), else_=_ZERO)
        ).label("total_por_cobrar"),
        func.sum(
            case((and_(has_debt, is_overdue), totals.saldo_pendiente), else_=_ZERO)
        ).label("total_vencido"),
        func.sum(monthly_paid).label("total_pagado_mes"),
        func.sum(case((and_(has_debt, is_pending), 1), else_=0)).label(
            "documentos_pendientes"
        ),
        func.sum(case((and_(has_debt, is_overdue), 1), else_=0)).label(
            "documentos_vencidos"
        ),
        func.sum(
            case((and_(totals.saldo_pendiente <= _ZERO, monthly_paid > _ZERO), 1), else_=0)
        ).label("documentos_pagados_mes"),
        func.count(
            func.distinct(
                case(
                    (
                        and_(has_debt, models.Cotizacion.cliente_id.isnot(None)),
                        models.Cotizacion.cliente_id,
                    )
                )
            )
        ).label("clientes_con_deuda"),
    ).select_from(models.Cotizacion)
    query = _join_collection_totals(query, totals).filter(
        *_accepted_fiscal_filters(tenant_id),
    )
    row = query.one()

    return {
        "total_por_cobrar": _money(row.total_por_cobrar),
        "total_vencido": _money(row.total_vencido),
        "total_pagado_mes": _money(row.total_pagado_mes),
        "documentos_pendientes": int(row.documentos_pendientes or 0),
        "documentos_vencidos": int(row.documentos_vencidos or 0),
        "documentos_pagados_mes": int(row.documentos_pagados_mes or 0),
        "clientes_con_deuda": int(row.clientes_con_deuda or 0),
    }


def get_reporte_mensual(db: Session, tenant_id: int, anio: int, mes: int) -> list:
    from datetime import date
    inicio = date(anio, mes, 1)
    fin = date(anio + 1, 1, 1) if mes == 12 else date(anio, mes + 1, 1)

    return (
        db.query(models.Cotizacion)
        .options(
            joinedload(models.Cotizacion.cliente),
            joinedload(models.Cotizacion.items),
        )
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.document_kind.in_(
                ["fiscal_document", "credit_note", "debit_note"]
            ),
            models.Cotizacion.estado == "facturada",
            models.Cotizacion.fecha_emision >= inicio,
            models.Cotizacion.fecha_emision < fin,
        )
        .order_by(models.Cotizacion.fecha_emision.asc())
        .all()
    )
