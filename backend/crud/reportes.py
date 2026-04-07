"""crud/reportes.py — Dashboard, cobranza y reportes contables."""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func


import models


def get_dashboard_stats(db: Session, tenant_id: int):
    from datetime import datetime as _dt
    from decimal import Decimal as _D

    ingresos = db.query(func.sum(models.Pago.monto_pagado)).filter(
        models.Pago.tenant_id == tenant_id
    ).scalar() or _D("0")

    saldos = db.query(func.sum(models.Cotizacion.saldo_pendiente)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "quotation",
        models.Cotizacion.estado != "anulada",
    ).scalar() or _D("0")

    costos = db.query(func.sum(models.OrdenProduccion.costo_tercerizado)).filter(
        models.OrdenProduccion.tenant_id == tenant_id
    ).scalar() or _D("0")

    ahora = _dt.now()
    vencidos_count = db.query(func.count(models.Cotizacion.id)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "quotation",
        models.Cotizacion.estado != "anulada",
        models.Cotizacion.fecha_vencimiento < ahora,
        models.Cotizacion.saldo_pendiente > 0,
    ).scalar() or 0

    saldo_vencido = db.query(func.sum(models.Cotizacion.saldo_pendiente)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "quotation",
        models.Cotizacion.estado != "anulada",
        models.Cotizacion.fecha_vencimiento < ahora,
        models.Cotizacion.saldo_pendiente > 0,
    ).scalar() or _D("0")

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
        "saldos_por_cobrar": saldos,
        "saldo_vencido": saldo_vencido,
        "costos_tercerizacion": costos,
        "documentos_emitidos_mes": emitidos_mes,
        "documentos_vencidos": vencidos_count,
        "top_productos": top_productos,
    }


def get_cobranza_vencida(
    db: Session,
    tenant_id: int,
    skip: int = 0,
    limit: int = 100,
) -> list:
    from datetime import datetime as _dt
    ahora = _dt.now()
    return (
        db.query(models.Cotizacion)
        .options(joinedload(models.Cotizacion.cliente))
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.document_kind == "quotation",
            models.Cotizacion.estado != "anulada",
            models.Cotizacion.fecha_vencimiento < ahora,
            models.Cotizacion.saldo_pendiente > 0,
        )
        .order_by(models.Cotizacion.fecha_vencimiento.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_cobranza_resumen(db: Session, tenant_id: int) -> dict:
    from datetime import datetime as _dt
    from decimal import Decimal as _D
    ahora = _dt.now()
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_por_cobrar = db.query(func.sum(models.Cotizacion.saldo_pendiente)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "quotation",
        models.Cotizacion.estado != "anulada",
        models.Cotizacion.saldo_pendiente > 0,
    ).scalar() or _D("0")

    total_vencido = db.query(func.sum(models.Cotizacion.saldo_pendiente)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "quotation",
        models.Cotizacion.estado != "anulada",
        models.Cotizacion.fecha_vencimiento < ahora,
        models.Cotizacion.saldo_pendiente > 0,
    ).scalar() or _D("0")

    total_pagado_mes = db.query(func.sum(models.Pago.monto_pagado)).filter(
        models.Pago.tenant_id == tenant_id,
        models.Pago.fecha_pago >= inicio_mes,
    ).scalar() or _D("0")

    docs_pendientes = db.query(func.count(models.Cotizacion.id)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "quotation",
        models.Cotizacion.estado != "anulada",
        models.Cotizacion.saldo_pendiente > 0,
        models.Cotizacion.fecha_vencimiento >= ahora,
    ).scalar() or 0

    docs_vencidos = db.query(func.count(models.Cotizacion.id)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "quotation",
        models.Cotizacion.estado != "anulada",
        models.Cotizacion.fecha_vencimiento < ahora,
        models.Cotizacion.saldo_pendiente > 0,
    ).scalar() or 0

    docs_pagados_mes = db.query(func.count(models.Cotizacion.id)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "quotation",
        models.Cotizacion.monto_pagado >= models.Cotizacion.total_venta,
        models.Cotizacion.total_venta > 0,
    ).scalar() or 0

    return {
        "total_por_cobrar": total_por_cobrar,
        "total_vencido": total_vencido,
        "total_pagado_mes": total_pagado_mes,
        "documentos_pendientes": docs_pendientes,
        "documentos_vencidos": docs_vencidos,
        "documentos_pagados_mes": docs_pagados_mes,
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
            models.Cotizacion.document_kind == "fiscal_document",
            models.Cotizacion.estado != "anulada",
            models.Cotizacion.fecha_emision >= inicio,
            models.Cotizacion.fecha_emision < fin,
        )
        .order_by(models.Cotizacion.fecha_emision.asc())
        .all()
    )
