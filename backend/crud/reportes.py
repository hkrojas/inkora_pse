"""crud/reportes.py — Dashboard, cobranza y reportes contables."""
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func, or_


import models
from services.document_flow_service import (
    DOCUMENT_KIND_FISCAL_DOCUMENT,
    DOCUMENT_STATUS_ISSUED,
)
from services.fiscal_balance_service import get_fiscal_document_balance


_ZERO = Decimal("0.00")
_MONEY_QUANT = Decimal("0.01")


def _money(value) -> Decimal:
    return Decimal(str(value if value is not None else _ZERO)).quantize(_MONEY_QUANT)


def _is_before_now(value, now: datetime) -> bool:
    if value is None:
        return False
    compare_now = now
    if value.tzinfo is not None and value.utcoffset() is not None:
        compare_now = datetime.now(value.tzinfo)
    return value < compare_now


def _accepted_fiscal_documents_query(db: Session, tenant_id: int):
    return (
        db.query(models.Cotizacion)
        .options(joinedload(models.Cotizacion.cliente))
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.document_kind == DOCUMENT_KIND_FISCAL_DOCUMENT,
            models.Cotizacion.estado == DOCUMENT_STATUS_ISSUED,
            models.Cotizacion.tipo_comprobante.in_(("01", "03")),
        )
    )


def _collection_query(db: Session, tenant_id: int, q: str | None = None):
    query = _accepted_fiscal_documents_query(db, tenant_id).filter(
        models.Cotizacion.fecha_vencimiento.isnot(None)
    )

    term = (q or "").strip()
    if term:
        like_term = f"%{term}%"
        query = query.outerjoin(
            models.Cliente,
            models.Cotizacion.cliente_id == models.Cliente.id,
        ).filter(
            or_(
                models.Cliente.razon_social.ilike(like_term),
                models.Cliente.nombre_comercial.ilike(like_term),
                models.Cliente.numero_documento.ilike(like_term),
                models.Cotizacion.internal_order_number.ilike(like_term),
                models.Cotizacion.serie.ilike(like_term),
            )
        )

    return query.order_by(models.Cotizacion.fecha_vencimiento.asc())


def _payment_filter_for_fiscal_document(fiscal_document):
    primary = models.Pago.fiscal_document_id == fiscal_document.id
    if fiscal_document.source_quote_id is None:
        return primary
    return or_(
        primary,
        and_(
            models.Pago.fiscal_document_id.is_(None),
            models.Pago.source_quote_id == fiscal_document.source_quote_id,
            models.Pago.tipo == "pago",
        ),
    )


def _payments_since_for_fiscal_document(
    db: Session,
    tenant_id: int,
    fiscal_document,
    since: datetime,
) -> Decimal:
    value = (
        db.query(func.sum(models.Pago.monto_pagado))
        .filter(
            models.Pago.tenant_id == tenant_id,
            models.Pago.fecha_pago >= since,
            _payment_filter_for_fiscal_document(fiscal_document),
        )
        .scalar()
    )
    return _money(value)


def _collection_row_for_fiscal_document(fiscal_document, balance):
    cliente = fiscal_document.cliente
    return SimpleNamespace(
        id=fiscal_document.id,
        serie=fiscal_document.serie,
        correlativo=fiscal_document.correlativo,
        fecha_emision=fiscal_document.fecha_emision,
        fecha_vencimiento=fiscal_document.fecha_vencimiento,
        moneda=fiscal_document.moneda,
        estado=fiscal_document.estado,
        document_kind=fiscal_document.document_kind,
        tipo_comprobante=fiscal_document.tipo_comprobante,
        internal_order_number=fiscal_document.internal_order_number,
        total_venta=balance.net_total,
        monto_pagado=balance.payments_total,
        saldo_pendiente=balance.saldo_pendiente,
        cliente_nombre=cliente.razon_social if cliente else None,
        cliente_nombre_alt=cliente.nombre_comercial if cliente else None,
        cliente_documento=cliente.numero_documento if cliente else None,
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

    rows = []
    for fiscal_document in _collection_query(db, tenant_id, q).all():
        if scope == "overdue" and not _is_before_now(
            fiscal_document.fecha_vencimiento,
            ahora,
        ):
            continue

        balance = get_fiscal_document_balance(db, tenant_id, fiscal_document.id)
        if balance.saldo_pendiente <= _ZERO:
            continue

        rows.append(_collection_row_for_fiscal_document(fiscal_document, balance))

    return rows[skip : skip + limit]


def get_cobranza_resumen(db: Session, tenant_id: int) -> dict:
    ahora = datetime.now()
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_por_cobrar = _ZERO
    total_vencido = _ZERO
    total_pagado_mes = _ZERO
    documentos_pendientes = 0
    documentos_vencidos = 0
    documentos_pagados_mes = 0
    clientes_con_deuda = set()

    for fiscal_document in _accepted_fiscal_documents_query(db, tenant_id).all():
        balance = get_fiscal_document_balance(db, tenant_id, fiscal_document.id)
        paid_this_month = _payments_since_for_fiscal_document(
            db,
            tenant_id,
            fiscal_document,
            inicio_mes,
        )
        total_pagado_mes += paid_this_month

        if balance.saldo_pendiente <= _ZERO:
            if paid_this_month > _ZERO:
                documentos_pagados_mes += 1
            continue

        total_por_cobrar += balance.saldo_pendiente
        if fiscal_document.cliente_id is not None:
            clientes_con_deuda.add(fiscal_document.cliente_id)

        if _is_before_now(fiscal_document.fecha_vencimiento, ahora):
            total_vencido += balance.saldo_pendiente
            documentos_vencidos += 1
        else:
            documentos_pendientes += 1

    return {
        "total_por_cobrar": _money(total_por_cobrar),
        "total_vencido": _money(total_vencido),
        "total_pagado_mes": _money(total_pagado_mes),
        "documentos_pendientes": documentos_pendientes,
        "documentos_vencidos": documentos_vencidos,
        "documentos_pagados_mes": documentos_pagados_mes,
        "clientes_con_deuda": len(clientes_con_deuda),
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
