"""Read-only business analytics for the authenticated tenant dashboard."""

from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import and_, case, func, or_, true
from sqlalchemy.orm import Session, aliased

import fiscal_time
import models
from services.document_flow_service import (
    DOCUMENT_KIND_CREDIT_NOTE,
    DOCUMENT_KIND_DEBIT_NOTE,
    DOCUMENT_KIND_FISCAL_DOCUMENT,
    DOCUMENT_KIND_QUOTATION,
    DOCUMENT_STATUS_ISSUED,
    DOCUMENT_STATUS_PENDING,
)


ZERO = Decimal("0.00")
MONEY = Decimal("0.01")
PERCENT = Decimal("0.1")
MONTH_ABBR_ES = (
    "",
    "ene",
    "feb",
    "mar",
    "abr",
    "may",
    "jun",
    "jul",
    "ago",
    "sep",
    "oct",
    "nov",
    "dic",
)


def _money(value) -> Decimal:
    return Decimal(str(value if value is not None else ZERO)).quantize(MONEY)


def _percent(current: Decimal, previous: Decimal) -> Decimal | None:
    if previous == ZERO:
        return None
    return (((current - previous) / abs(previous)) * Decimal("100")).quantize(
        PERCENT,
        rounding=ROUND_HALF_UP,
    )


def _period_label(start: date, end: date) -> str:
    if start.year == end.year and start.month == end.month:
        return f"{start.day}–{end.day} {MONTH_ABBR_ES[end.month]} {end.year}"
    return f"{start.isoformat()} – {end.isoformat()}"


def _month_before(value: date) -> tuple[int, int]:
    if value.month == 1:
        return value.year - 1, 12
    return value.year, value.month - 1


def _comparison_period(start: date, end: date) -> tuple[date, date]:
    if start.day == 1 and start.year == end.year and start.month == end.month:
        year, month = _month_before(start)
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, 1), date(year, month, min(end.day, last_day))
    duration = end - start
    comparison_end = start - timedelta(days=1)
    return comparison_end - duration, comparison_end


def _day_start(value: date) -> datetime:
    return datetime.combine(value, time.min)


def _day_after(value: date) -> datetime:
    return datetime.combine(value + timedelta(days=1), time.min)


def _base_sale_filter():
    return and_(
        models.Cotizacion.document_kind == DOCUMENT_KIND_FISCAL_DOCUMENT,
        models.Cotizacion.tipo_comprobante.in_(("01", "03")),
        models.Cotizacion.estado.in_(
            (DOCUMENT_STATUS_PENDING, DOCUMENT_STATUS_ISSUED)
        ),
    )


def _recognized_sales_filter():
    return or_(
        _base_sale_filter(),
        and_(
            models.Cotizacion.document_kind.in_(
                (DOCUMENT_KIND_CREDIT_NOTE, DOCUMENT_KIND_DEBIT_NOTE)
            ),
            models.Cotizacion.estado == DOCUMENT_STATUS_ISSUED,
        ),
    )


def _registered_quote_filter():
    # Registered quotes remain pending until their derived invoice is accepted.
    return and_(
        models.Cotizacion.document_kind == DOCUMENT_KIND_QUOTATION,
        models.Cotizacion.estado.in_((DOCUMENT_STATUS_PENDING, DOCUMENT_STATUS_ISSUED)),
    )


def _signed_total():
    total = func.coalesce(models.Cotizacion.total_venta, ZERO)
    return case(
        (models.Cotizacion.document_kind == DOCUMENT_KIND_CREDIT_NOTE, -total),
        else_=total,
    )


def _signed_item_amount():
    total = func.coalesce(models.CotizacionItem.total_item, ZERO)
    return case(
        (models.Cotizacion.document_kind == DOCUMENT_KIND_CREDIT_NOTE, -total),
        else_=total,
    )


def _signed_item_quantity():
    quantity = func.coalesce(models.CotizacionItem.cantidad, ZERO)
    return case(
        (models.Cotizacion.document_kind == DOCUMENT_KIND_CREDIT_NOTE, -quantity),
        else_=quantity,
    )


def _document_filters(
    tenant_id: int,
    currency: str,
    *,
    client_id: int | None,
    product_id: int | None,
):
    filters = [
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.moneda == currency,
    ]
    if client_id is not None:
        filters.append(models.Cotizacion.cliente_id == client_id)
    if product_id is not None:
        filters.append(
            models.Cotizacion.items.any(
                models.CotizacionItem.producto_id == product_id
            )
        )
    return filters


def _client_name(primary, secondary) -> str:
    return primary or secondary or "Cliente sin nombre"


def _previous_history_sales(db: Session, filters: list, start: date, end: date):
    """Aggregate the previous equivalent month span, independent of current rows."""
    first_day = start.day if (start.year, start.month) == (end.year, end.month) else 1
    year, month = _month_before(end)
    last_day = calendar.monthrange(year, month)[1]
    matched_start = date(year, month, min(first_day, last_day))
    matched_end = date(year, month, min(end.day, last_day))
    return (
        db.query(func.sum(_signed_total()))
        .filter(
            *filters,
            _recognized_sales_filter(),
            models.Cotizacion.fecha_emision >= _day_start(matched_start),
            models.Cotizacion.fecha_emision < _day_after(matched_end),
        )
        .correlate(None)
        .scalar_subquery()
    )


def get_business_dashboard(
    db: Session,
    tenant_id: int,
    *,
    start: date | None = None,
    end: date | None = None,
    client_id: int | None = None,
    product_id: int | None = None,
    currency: str = "PEN",
    group_by: str = "month",
    history_scope: str = "all",
    period_scope: str = "selected",
) -> dict:
    """Return one bounded dashboard payload without loading document collections."""

    today = fiscal_time.today_lima()
    if group_by not in ("day", "month"):
        raise ValueError("Agrupa los datos por días o por meses.")
    if history_scope not in ("all", "period"):
        raise ValueError("Elige el historial completo o el período seleccionado.")
    if period_scope not in ("selected", "all"):
        raise ValueError("Elige un período o todo el historial.")
    if period_scope == "all" and group_by != "month":
        raise ValueError("Para ver todo el historial, agrupa por meses.")
    if period_scope == "all":
        history_scope = "period"
    if group_by == "day" and history_scope != "period":
        raise ValueError("Para ver días, selecciona un período de hasta 93 días.")
    history_today_dt = _day_after(today)
    first_activity_query = (
        db.query(func.min(models.Cotizacion.fecha_emision))
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.fecha_emision < history_today_dt,
            or_(_registered_quote_filter(), _recognized_sales_filter()),
        )
    )
    all_activity = first_activity_query.scalar() if period_scope == "all" else None
    period_end = today if period_scope == "all" else min(end or today, today)
    period_start = (all_activity.date() if all_activity else today) if period_scope == "all" else start or period_end.replace(day=1)
    if period_start > period_end:
        raise ValueError("La fecha inicial no puede ser posterior a la fecha final.")
    if period_scope == "selected" and (period_end - period_start).days > 366:
        raise ValueError("El periodo analizado no puede superar 367 dias.")
    if group_by == "day" and (period_end - period_start).days > 92:
        raise ValueError("La vista por días permite hasta 93 días. Elige un período más corto.")
    if currency != "PEN":
        raise ValueError("El dashboard comercial solo consolida operaciones en PEN.")

    comparison_start, comparison_end = _comparison_period(period_start, period_end)
    period_start_dt = _day_start(period_start)
    period_end_dt = _day_after(period_end)
    comparison_start_dt = _day_start(comparison_start)
    comparison_end_dt = _day_after(comparison_end)
    range_start_dt = min(period_start_dt, comparison_start_dt)
    common_filters = _document_filters(
        tenant_id,
        currency,
        client_id=client_id,
        product_id=product_id,
    )

    in_period = and_(
        models.Cotizacion.fecha_emision >= period_start_dt,
        models.Cotizacion.fecha_emision < period_end_dt,
    )
    in_comparison = and_(
        models.Cotizacion.fecha_emision >= comparison_start_dt,
        models.Cotizacion.fecha_emision < comparison_end_dt,
    )
    history_end = period_end if history_scope == "period" else today
    history_end_dt = _day_after(history_end)
    # Conversion remains the current state of the selected quotation cohort.
    conversion_end_dt = history_today_dt
    linked_document = aliased(models.Cotizacion)
    has_linked_sale = (
        db.query(linked_document.id)
        .filter(
            linked_document.tenant_id == tenant_id,
            linked_document.source_quote_id == models.Cotizacion.id,
            linked_document.document_kind == DOCUMENT_KIND_FISCAL_DOCUMENT,
            linked_document.tipo_comprobante.in_(("01", "03")),
            linked_document.estado.in_((DOCUMENT_STATUS_PENDING, DOCUMENT_STATUS_ISSUED)),
            linked_document.fecha_emision < conversion_end_dt,
        )
        .correlate(models.Cotizacion)
        .exists()
    )
    quote_summary = (
        db.query(
            func.count(models.Cotizacion.id).label("quote_count"),
            func.sum(case((has_linked_sale, 1), else_=0)).label("converted_count"),
        )
        .filter(*common_filters, in_period, _registered_quote_filter())
        .subquery("dashboard_quote_summary")
    )
    first_activity_scalar = first_activity_query.scalar_subquery()
    signed_total = _signed_total()
    sales_summary = (
        db.query(
            func.sum(
                case((and_(in_period, _recognized_sales_filter()), signed_total), else_=ZERO)
            ).label("sales_amount"),
            func.sum(
                case((and_(in_comparison, _recognized_sales_filter()), signed_total), else_=ZERO)
            ).label("previous_sales_amount"),
            func.sum(case((and_(in_period, _base_sale_filter()), 1), else_=0)).label(
                "sales_count"
            ),
            func.count(
                func.distinct(
                    case(
                        (
                            and_(
                                in_period,
                                _base_sale_filter(),
                                models.Cotizacion.cliente_id.isnot(None),
                            ),
                            models.Cotizacion.cliente_id,
                        )
                    )
                )
            ).label("customers_count"),
            func.sum(
                case(
                    (
                        and_(
                            in_period,
                            _base_sale_filter(),
                            models.Cotizacion.estado == DOCUMENT_STATUS_PENDING,
                        ),
                        func.coalesce(models.Cotizacion.total_venta, ZERO),
                    ),
                    else_=ZERO,
                )
            ).label("pending_sunat_amount"),
        )
        .filter(
            *common_filters,
            models.Cotizacion.fecha_emision >= range_start_dt,
            models.Cotizacion.fecha_emision < period_end_dt,
            _recognized_sales_filter(),
        )
        .subquery("dashboard_sales_summary")
    )

    current_customer_query = db.query(
        models.Cotizacion.cliente_id.label("client_id")
    ).filter(
        *common_filters,
        in_period,
        _base_sale_filter(),
        models.Cotizacion.cliente_id.isnot(None),
    )
    current_customers = current_customer_query.distinct().subquery(
        "dashboard_current_customers"
    )
    first_sales = (
        db.query(
            models.Cotizacion.cliente_id.label("client_id"),
            func.min(models.Cotizacion.fecha_emision).label("first_sale_at"),
        )
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.moneda == currency,
            _base_sale_filter(),
            models.Cotizacion.cliente_id.isnot(None),
        )
        .group_by(models.Cotizacion.cliente_id)
        .subquery("dashboard_first_sales")
    )
    new_customers_count_query = (
        db.query(func.count(first_sales.c.client_id))
        .join(
            current_customers,
            current_customers.c.client_id == first_sales.c.client_id,
        )
        .filter(first_sales.c.first_sale_at >= period_start_dt)
        .scalar_subquery()
    )

    from crud.reportes import (
        _accepted_fiscal_filters,
        _collection_totals,
        _join_collection_totals,
    )

    collection_totals = _collection_totals(db, tenant_id)
    overdue_query = db.query(
        func.sum(
            case(
                (
                    collection_totals.saldo_pendiente > ZERO,
                    collection_totals.saldo_pendiente,
                ),
                else_=ZERO,
            )
        ).label("amount"),
        func.count(
            func.distinct(
                case(
                    (
                        and_(
                            collection_totals.saldo_pendiente > ZERO,
                            models.Cotizacion.cliente_id.isnot(None),
                        ),
                        models.Cotizacion.cliente_id,
                    )
                )
            )
        ).label("customers"),
    ).select_from(models.Cotizacion)
    overdue_query = _join_collection_totals(overdue_query, collection_totals).filter(
        *_accepted_fiscal_filters(tenant_id),
        *common_filters,
        in_period,
        models.Cotizacion.fecha_vencimiento.isnot(None),
        models.Cotizacion.fecha_vencimiento < fiscal_time.now_lima_naive(),
    )
    overdue_metrics = overdue_query.subquery("dashboard_overdue_metrics")

    low_stock_count_query = (
        db.query(func.count(func.distinct(models.InventoryBalance.product_id)))
        .filter(
            models.InventoryBalance.tenant_id == tenant_id,
            models.InventoryBalance.minimum_stock > ZERO,
            (
                models.InventoryBalance.on_hand - models.InventoryBalance.committed
                <= models.InventoryBalance.minimum_stock
            ),
        )
        .scalar_subquery()
    )
    fiscal_error_count_query = (
        db.query(func.count(models.Cotizacion.id))
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.document_kind == DOCUMENT_KIND_FISCAL_DOCUMENT,
            models.Cotizacion.tipo_comprobante.in_(("01", "03")),
            models.Cotizacion.estado == DOCUMENT_STATUS_PENDING,
            models.Cotizacion.sunat_error.isnot(None),
            func.length(func.trim(models.Cotizacion.sunat_error)) > 0,
        )
        .scalar_subquery()
    )
    summary_row = (
        db.query(
            sales_summary.c.sales_amount,
            sales_summary.c.previous_sales_amount,
            sales_summary.c.sales_count,
            sales_summary.c.customers_count,
            sales_summary.c.pending_sunat_amount,
            func.coalesce(new_customers_count_query, 0).label("new_customers_count"),
            func.coalesce(overdue_metrics.c.amount, ZERO).label("overdue_amount"),
            func.coalesce(overdue_metrics.c.customers, 0).label("overdue_customers"),
            func.coalesce(low_stock_count_query, 0).label("low_stock_count"),
            func.coalesce(fiscal_error_count_query, 0).label("fiscal_error_count"),
            quote_summary.c.quote_count,
            func.coalesce(quote_summary.c.converted_count, 0).label("converted_count"),
            first_activity_scalar.label("first_activity"),
            *(
                [_previous_history_sales(db, common_filters, period_start, history_end)
                 .label("previous_history_amount")]
                if history_scope == "period" else []
            ),
        )
        .select_from(sales_summary)
        .join(overdue_metrics, true())
        .join(quote_summary, true())
        .one()
    )

    sales_amount = _money(summary_row.sales_amount)
    previous_sales_amount = _money(summary_row.previous_sales_amount)
    sales_count = int(summary_row.sales_count or 0)
    customers_count = int(summary_row.customers_count or 0)
    new_customers_count = int(summary_row.new_customers_count or 0)

    activity_start = summary_row.first_activity.date() if summary_row.first_activity else None
    history_start = period_start if history_scope == "period" else activity_start or today
    history_start_dt = _day_start(history_start)
    # Period comparisons are part of the summary so empty months retain them.
    previous_history_amount = (
        _previous_history_sales(db, common_filters, history_start, history_end)
        if history_scope == "all" else None
    )
    year_expr = func.extract("year", models.Cotizacion.fecha_emision)
    month_expr = func.extract("month", models.Cotizacion.fecha_emision)
    day_expr = func.extract("day", models.Cotizacion.fecha_emision)
    grouping = [year_expr, month_expr] + ([day_expr] if group_by == "day" else [])
    history_columns = [
        year_expr.label("year"), month_expr.label("month"),
        func.sum(case((_recognized_sales_filter(), signed_total), else_=ZERO)).label("amount"),
        func.sum(case((_registered_quote_filter(), models.Cotizacion.total_venta), else_=ZERO)).label("quoted_amount"),
    ]
    if history_scope == "all":
        history_columns.append(previous_history_amount.label("previous_matched_amount"))
    if group_by == "day":
        history_columns.append(day_expr.label("day"))
    sales_history_rows = (
        db.query(*history_columns)
        .filter(
            *common_filters,
            models.Cotizacion.fecha_emision >= history_start_dt,
            models.Cotizacion.fecha_emision < history_end_dt,
            or_(_recognized_sales_filter(), _registered_quote_filter()),
        )
        .group_by(*grouping)
        .all()
    )
    def history_key(row):
        key = (int(row.year), int(row.month))
        return key + (int(row.day),) if group_by == "day" else key
    sales_history = {history_key(row): _money(row.amount) for row in sales_history_rows}
    quoted_history = {history_key(row): _money(row.quoted_amount) for row in sales_history_rows}
    previous_matched_sales = (
        _money(summary_row.previous_history_amount)
        if history_scope == "period"
        else _money(sales_history_rows[0].previous_matched_amount) if sales_history_rows else None
    )
    history = []
    cursor = history_start if group_by == "day" else history_start.replace(day=1)
    while (activity_start or (history_scope == "period" and period_scope == "selected")) and cursor <= history_end:
        key = (cursor.year, cursor.month)
        last_day = calendar.monthrange(cursor.year, cursor.month)[1]
        bucket_start = max(cursor, history_start)
        bucket_end = min(date(cursor.year, cursor.month, last_day), history_end)
        partial = bucket_start.day != 1 or bucket_end.day != last_day
        if group_by == "day":
            key += (cursor.day,)
            bucket_start = bucket_end = cursor
            partial = False
        history.append({
            "year": cursor.year,
            "month": cursor.month,
            "date": cursor if group_by == "day" else None,
            "period_start": bucket_start,
            "period_end": bucket_end,
            "sales_amount": sales_history.get(key, ZERO),
            "quoted_amount": quoted_history.get(key, ZERO),
            "is_partial": partial,
            "cutoff_day": bucket_end.day if partial else None,
            "previous_matched_sales": previous_matched_sales if partial and bucket_end == history_end else None,
        })
        if group_by == "day":
            cursor += timedelta(days=1)
        elif cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)

    product = aliased(models.Producto)
    product_name = func.coalesce(product.nombre, models.CotizacionItem.descripcion)
    # Historical missing units use the same default as newly created lines.
    product_unit = func.coalesce(models.CotizacionItem.unidad_medida, "NIU")
    current_item_amount = func.sum(
        case(
            (
                and_(in_period, _recognized_sales_filter()),
                _signed_item_amount(),
            ),
            else_=ZERO,
        )
    )
    previous_item_amount = func.sum(
        case(
            (
                and_(in_comparison, _recognized_sales_filter()),
                _signed_item_amount(),
            ),
            else_=ZERO,
        )
    )
    product_totals = (
        db.query(
            models.CotizacionItem.producto_id.label("id"),
            product_name.label("name"),
            product_unit.label("unit"),
            func.sum(
                case(
                    (
                        and_(in_period, _recognized_sales_filter()),
                        _signed_item_quantity(),
                    ),
                    else_=ZERO,
                )
            ).label("quantity"),
            current_item_amount.label("amount"),
            previous_item_amount.label("previous_amount"),
        )
        .select_from(models.CotizacionItem)
        .join(models.Cotizacion, models.Cotizacion.id == models.CotizacionItem.cotizacion_id)
        .outerjoin(
            product,
            and_(
                product.id == models.CotizacionItem.producto_id,
                product.tenant_id == tenant_id,
            ),
        )
        .filter(
            *common_filters,
            models.CotizacionItem.producto_id.isnot(None),
            models.Cotizacion.fecha_emision >= range_start_dt,
            models.Cotizacion.fecha_emision < period_end_dt,
            _recognized_sales_filter(),
        )
        .group_by(
            models.CotizacionItem.producto_id,
            product_name,
            product_unit,
        )
        .subquery("dashboard_product_totals")
    )
    product_decline_order = case(
        (
            and_(
                product_totals.c.previous_amount > ZERO,
                product_totals.c.amount < product_totals.c.previous_amount,
            ),
            (product_totals.c.amount - product_totals.c.previous_amount)
            / product_totals.c.previous_amount,
        ),
        else_=Decimal("1000000"),
    )
    product_ranked = (
        db.query(
            product_totals,
            func.row_number()
            .over(order_by=(product_totals.c.amount.desc(), product_totals.c.id.asc()))
            .label("sales_rank"),
            func.row_number()
            .over(order_by=(product_decline_order.asc(), product_totals.c.id.asc()))
            .label("decline_rank"),
        )
        .subquery("dashboard_product_ranked")
    )
    product_rows = (
        db.query(product_ranked)
        .filter(
            or_(
                product_ranked.c.sales_rank <= 10,
                product_ranked.c.decline_rank <= 10,
            )
        )
        .order_by(product_ranked.c.sales_rank.asc())
        .all()
    )
    products = []
    for row in product_rows:
        amount = _money(row.amount)
        previous = _money(row.previous_amount)
        products.append(
            {
                "id": row.id,
                "name": row.name or "Producto sin nombre",
                "unit": row.unit or "NIU",
                "quantity": Decimal(str(row.quantity or 0)),
                "amount": amount,
                "previous_amount": previous,
                "change_percent": _percent(amount, previous),
            }
        )

    client = aliased(models.Cliente)
    client_name = func.coalesce(client.razon_social, client.nombre_comercial)
    current_client_amount = func.sum(
        case((and_(in_period, _recognized_sales_filter()), signed_total), else_=ZERO)
    )
    previous_client_amount = func.sum(
        case((and_(in_comparison, _recognized_sales_filter()), signed_total), else_=ZERO)
    )
    client_totals = (
        db.query(
            models.Cotizacion.cliente_id.label("id"),
            client_name.label("name"),
            current_client_amount.label("amount"),
            previous_client_amount.label("previous_amount"),
            func.sum(case((and_(in_period, _base_sale_filter()), 1), else_=0)).label(
                "purchases"
            ),
            func.max(
                case((and_(in_period, _base_sale_filter()), models.Cotizacion.fecha_emision))
            ).label("last_purchase"),
        )
        .select_from(models.Cotizacion)
        .join(
            client,
            and_(
                client.id == models.Cotizacion.cliente_id,
                client.tenant_id == tenant_id,
            ),
        )
        .filter(
            *common_filters,
            models.Cotizacion.fecha_emision >= range_start_dt,
            models.Cotizacion.fecha_emision < period_end_dt,
            _recognized_sales_filter(),
            models.Cotizacion.cliente_id.isnot(None),
        )
        .group_by(models.Cotizacion.cliente_id, client_name)
        .subquery("dashboard_client_totals")
    )
    client_decline_order = case(
        (
            and_(
                client_totals.c.previous_amount > ZERO,
                client_totals.c.amount < client_totals.c.previous_amount,
            ),
            (client_totals.c.amount - client_totals.c.previous_amount)
            / client_totals.c.previous_amount,
        ),
        else_=Decimal("1000000"),
    )
    client_ranked = (
        db.query(
            client_totals,
            func.row_number()
            .over(order_by=(client_totals.c.amount.desc(), client_totals.c.id.asc()))
            .label("sales_rank"),
            func.row_number()
            .over(order_by=(client_decline_order.asc(), client_totals.c.id.asc()))
            .label("decline_rank"),
        )
        .subquery("dashboard_client_ranked")
    )
    client_rows = (
        db.query(client_ranked)
        .filter(
            or_(
                client_ranked.c.sales_rank <= 10,
                client_ranked.c.decline_rank <= 10,
            )
        )
        .order_by(client_ranked.c.sales_rank.asc())
        .all()
    )
    clients = []
    for row in client_rows:
        amount = _money(row.amount)
        previous = _money(row.previous_amount)
        clients.append(
            {
                "id": row.id,
                "name": row.name or "Cliente sin nombre",
                "amount": amount,
                "purchases": int(row.purchases or 0),
                "last_purchase": row.last_purchase.date() if row.last_purchase else None,
                "share_percent": (
                    (amount / sales_amount * Decimal("100")).quantize(PERCENT)
                    if sales_amount > ZERO
                    else ZERO
                ),
                "previous_amount": previous,
                "change_percent": _percent(amount, previous),
            }
        )

    now = fiscal_time.now_lima()

    quote_follow_rows = (
        db.query(
            models.Cotizacion.id,
            models.Cotizacion.cliente_id,
            models.Cotizacion.serie,
            models.Cotizacion.correlativo,
            models.Cotizacion.total_venta,
            models.Cotizacion.fecha_emision,
            models.Cliente.razon_social.label("client_name"),
            models.Cliente.nombre_comercial.label("client_alt"),
            func.count().over().label("total_count"),
        )
        .outerjoin(models.Cliente, and_(
            models.Cliente.id == models.Cotizacion.cliente_id,
            models.Cliente.tenant_id == tenant_id,
        ))
        .filter(
            *common_filters,
            in_period,
            _registered_quote_filter(),
            ~has_linked_sale,
        )
        .order_by(models.Cotizacion.fecha_emision.asc(), models.Cotizacion.id.asc())
        .limit(3)
        .all()
    )
    quote_count = int(summary_row.quote_count or 0)
    converted_count = int(summary_row.converted_count or 0)

    declining_clients = sorted(
        [
            row
            for row in clients
            if row["previous_amount"] > ZERO and row["amount"] < row["previous_amount"]
        ],
        key=lambda row: row["change_percent"] if row["change_percent"] is not None else ZERO,
    )
    declining_follow_rows = [
        {
            "client_id": row["id"],
            "client": row["name"],
            "reference": "Ventas del periodo",
            "amount": row["amount"],
            "age_days": max((period_end - row["last_purchase"]).days, 0)
            if row["last_purchase"]
            else 0,
        }
        for row in declining_clients[:3]
    ]

    inactive_cutoff = _day_start(period_end - timedelta(days=60))
    inactive_ranked = (
        db.query(
            models.Cotizacion.cliente_id.label("client_id"),
            models.Cotizacion.fecha_emision.label("last_purchase"),
            models.Cotizacion.total_venta.label("amount"),
            func.row_number()
            .over(
                partition_by=models.Cotizacion.cliente_id,
                order_by=(
                    models.Cotizacion.fecha_emision.desc(),
                    models.Cotizacion.id.desc(),
                ),
            )
            .label("purchase_rank"),
        )
        .filter(
            *common_filters,
            _base_sale_filter(),
            models.Cotizacion.fecha_emision < period_end_dt,
            models.Cotizacion.cliente_id.isnot(None),
        )
        .subquery("dashboard_inactive_ranked")
    )
    inactive_latest = (
        db.query(inactive_ranked)
        .filter(
            inactive_ranked.c.purchase_rank == 1,
            inactive_ranked.c.last_purchase < inactive_cutoff,
        )
        .subquery("dashboard_inactive_latest")
    )
    inactive_query = (
        db.query(
            inactive_latest.c.client_id,
            inactive_latest.c.last_purchase,
            inactive_latest.c.amount,
            models.Cliente.razon_social.label("client_name"),
            models.Cliente.nombre_comercial.label("client_alt"),
            func.count().over().label("total_count"),
        )
        .join(
            models.Cliente,
            and_(
                models.Cliente.id == inactive_latest.c.client_id,
                models.Cliente.tenant_id == tenant_id,
            ),
        )
    )
    inactive_rows = inactive_query.order_by(inactive_latest.c.last_purchase.asc()).limit(3).all()
    inactive_count = int(inactive_rows[0].total_count) if inactive_rows else 0
    inactive_follow_rows = [
        {
            "client_id": row.client_id,
            "client": _client_name(row.client_name, row.client_alt),
            "reference": "Ultima compra",
            "amount": _money(row.amount),
            "age_days": max((period_end - row.last_purchase.date()).days, 0),
        }
        for row in inactive_rows
    ]

    return {
        "meta": {
            "generated_at": now,
            "activity_start": activity_start,
            "group_by": group_by,
            "history_scope": history_scope,
            "period_scope": period_scope,
            "overdue_as_of": today,
            "currency": currency,
            "period": {
                "start": period_start,
                "end": period_end,
                "label": _period_label(period_start, period_end),
            },
            "comparison": {
                "start": comparison_start,
                "end": comparison_end,
                "label": _period_label(comparison_start, comparison_end),
            },
            "history": {
                "start": history_start,
                "end": history_end,
                "label": _period_label(history_start, history_end),
            },
            "client_id": client_id,
            "product_id": product_id,
        },
        "summary": {
            "sales_amount": sales_amount,
            "sales_count": sales_count,
            "pending_sunat_amount": _money(summary_row.pending_sunat_amount),
            "sales_change_percent": _percent(sales_amount, previous_sales_amount),
            "customers_count": customers_count,
            "new_customers_count": new_customers_count,
            "returning_customers_count": max(customers_count - new_customers_count, 0),
            "average_sale": _money(sales_amount / sales_count) if sales_count else ZERO,
            "overdue_amount": _money(summary_row.overdue_amount),
            "overdue_customers_count": int(summary_row.overdue_customers or 0),
        },
        "history": history,
        "conversion": {
            "available": True,
            "reason": None,
            "quote_count": quote_count,
            "linked_sales_count": converted_count,
            "rate_percent": (Decimal(converted_count) / quote_count * 100).quantize(PERCENT, rounding=ROUND_HALF_UP) if quote_count else None,
        },
        "products": products,
        "clients": clients,
        "follow_up": {
            "quotes": {
                "available": True,
                "reason": None,
                "count": int(quote_follow_rows[0].total_count) if quote_follow_rows else 0,
                "rows": [
                    {
                        "quote_id": row.id,
                        "client_id": row.cliente_id,
                        "client": _client_name(row.client_name, row.client_alt),
                        "reference": f"{row.serie or 'COT'}-{row.correlativo:06d}" if row.correlativo is not None else f"COT-{row.id}",
                        "amount": _money(row.total_venta),
                        "age_days": max((today - row.fecha_emision.date()).days, 0),
                    }
                    for row in quote_follow_rows
                ],
            },
            "declining": {"count": len(declining_clients), "rows": declining_follow_rows},
            "inactive": {"count": inactive_count, "rows": inactive_follow_rows},
        },
        "pending": {
            "low_stock_products": int(summary_row.low_stock_count or 0),
            "fiscal_documents_with_errors": int(summary_row.fiscal_error_count or 0),
        },
    }
