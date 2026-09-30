"""Paginated records explaining read-only dashboard sales totals."""

from datetime import date
from decimal import Decimal

from sqlalchemy import and_, case, func, literal
from sqlalchemy.orm import Session

import fiscal_time
import models
from crud.dashboard_business import (
    _day_after,
    _day_start,
    _document_filters,
    _money,
    _period_label,
    _recognized_sales_filter,
    _signed_item_amount,
    _signed_item_quantity,
    _signed_total,
)


def get_business_dashboard_records(
    db: Session,
    tenant_id: int,
    *,
    start: date,
    end: date,
    client_id: int | None = None,
    product_id: int | None = None,
    contains_product_id: int | None = None,
    product_unit: str | None = None,
    currency: str = "PEN",
    measure: str = "document",
    skip: int = 0,
    limit: int = 15,
) -> dict:
    """Aggregate and page in SQL, without loading document/item collections."""
    end = min(end, fiscal_time.today_lima())
    if start > end:
        raise ValueError("La fecha inicial no puede ser posterior a la fecha final.")
    if currency != "PEN":
        raise ValueError("El dashboard comercial solo consolida operaciones en PEN.")
    if measure not in ("document", "product"):
        raise ValueError("Elige los importes por comprobante o por producto.")
    if measure == "product" and product_id is None:
        raise ValueError("Selecciona un producto para consultar sus ventas.")
    if skip < 0 or not 1 <= limit <= 100:
        raise ValueError("La página solicitada no es válida.")

    filters = _document_filters(
        tenant_id, currency, client_id=client_id, product_id=product_id
    )
    # Ownership is checked inside the selection, so foreign/nonexistent IDs
    # produce no rows and require no extra lookup or disclosure.
    if client_id is not None:
        filters.append(
            db.query(models.Cliente.id)
            .filter(models.Cliente.id == client_id, models.Cliente.tenant_id == tenant_id)
            .exists()
        )
    if contains_product_id is not None:
        filters.append(models.Cotizacion.items.any(models.CotizacionItem.producto_id == contains_product_id))
    for owned_product_id in {product_id, contains_product_id} - {None}:
        filters.append(
            db.query(models.Producto.id)
            .filter(models.Producto.id == owned_product_id, models.Producto.tenant_id == tenant_id)
            .exists()
        )
    filters.extend(
        (
            _recognized_sales_filter(),
            models.Cotizacion.fecha_emision >= _day_start(start),
            models.Cotizacion.fecha_emision < _day_after(end),
        )
    )
    document = models.Cotizacion
    columns = [
        document.id.label("document_id"),
        document.serie.label("series"),
        document.correlativo.label("correlative"),
        document.tipo_comprobante.label("tipo_comprobante"),
        document.document_kind.label("document_kind"),
        document.fecha_emision.label("issued_at"),
        document.cliente_id.label("client_id"),
        document.estado.label("state"),
    ]
    if measure == "product":
        item = models.CotizacionItem
        normalized_unit = func.coalesce(item.unidad_medida, "NIU")
        unit = func.min(normalized_unit)
        # Quantities only have one unit when every matching line agrees.
        same_unit = func.min(normalized_unit) == func.max(normalized_unit)
        item_filters = [item.producto_id == product_id]
        if product_unit is not None:
            item_filters.append(normalized_unit == product_unit)
        selection = (
            db.query(
                *columns,
                func.sum(_signed_item_amount()).label("amount"),
                case((same_unit, func.sum(_signed_item_quantity())), else_=None).label("quantity"),
                case((same_unit, unit), else_=None).label("unit"),
            )
            .select_from(document)
            .join(item, item.cotizacion_id == document.id)
            .filter(*filters, *item_filters)
            .group_by(*columns)
        )
    else:
        selection = db.query(
            *columns,
            _signed_total().label("amount"),
            literal(None).label("quantity"),
            literal(None).label("unit"),
        ).filter(*filters)
    selected = selection.subquery("dashboard_records")
    totals = db.query(
        func.count(selected.c.document_id).label("total"),
        func.sum(selected.c.amount).label("total_amount"),
    ).one()
    rows = (
        db.query(
            selected,
            models.Cliente.razon_social.label("client_name"),
            models.Cliente.nombre_comercial.label("client_alt"),
        )
        .outerjoin(
            models.Cliente,
            and_(
                models.Cliente.id == selected.c.client_id,
                models.Cliente.tenant_id == tenant_id,
            ),
        )
        .order_by(selected.c.issued_at.desc(), selected.c.document_id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {
        "meta": {
            "period": {"start": start, "end": end, "label": _period_label(start, end)},
            "currency": currency,
            "client_id": client_id,
            "product_id": product_id,
            "contains_product_id": contains_product_id,
            "product_unit": product_unit,
            "measure": measure,
        },
        "total": totals.total,
        "total_amount": _money(totals.total_amount),
        "skip": skip,
        "limit": limit,
        "items": [
            {
                "document_id": row.document_id,
                "reference": (
                    f"{row.series}-{row.correlative:06d}"
                    if row.series and row.correlative is not None
                    else f"Comprobante {row.document_id}"
                ),
                "tipo_comprobante": row.tipo_comprobante,
                "document_kind": row.document_kind,
                "issued_at": row.issued_at,
                "client_name": row.client_name or row.client_alt or "Cliente sin nombre",
                "amount": _money(row.amount),
                "quantity": Decimal(str(row.quantity)) if row.quantity is not None else None,
                "unit": row.unit,
                "state": row.state,
            }
            for row in rows
        ],
    }
