from __future__ import annotations

from typing import Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

import models
import schemas
from access_control import can_access_all_tenant_resources
from crud._base import (
    _clone_cotizacion_items,
    get_latest_fiscal_document_for_quote,
    get_producto_for_tenant,
)
from crud.tenants import get_subscription_by_tenant
from services import calculations
from services.fiscal_clock import now_in_peru_naive
from services.client_snapshot_service import build_cliente_snapshot
from services.document_flow_service import (
    DOCUMENT_KIND_FISCAL_DOCUMENT,
    DOCUMENT_STATUS_PENDING,
    build_internal_order_number,
    get_document_kind_for_note,
    resolve_source_quote_id,
)


QUOTE_SERIE = "COT"
FACTURA_SERIE = "F001"
BOLETA_SERIE = "B001"
FACTURA_NOTE_SERIE = "FF01"
BOLETA_NOTE_SERIE = "BB01"


def _apply_quote_user_scope(query, usuario: Optional[models.User]):
    if usuario and getattr(usuario, "tenant_id", None):
        query = query.filter(models.Cotizacion.tenant_id == usuario.tenant_id)
    if usuario and not can_access_all_tenant_resources(usuario):
        query = query.filter(models.Cotizacion.usuario_id == usuario.id)
    return query


def _build_quote_listing_query(db: Session):
    return (
        db.query(models.Cotizacion)
        .options(
            joinedload(models.Cotizacion.cliente),
            joinedload(models.Cotizacion.usuario).joinedload(models.User.tenant),
            joinedload(models.Cotizacion.derived_documents),
        )
        .filter(models.Cotizacion.source_quote_id.is_(None))
        .order_by(desc(models.Cotizacion.id))
    )


def _build_quote_detail_query(db: Session):
    return (
        db.query(models.Cotizacion)
        .options(
            joinedload(models.Cotizacion.cliente),
            joinedload(models.Cotizacion.items),
            joinedload(models.Cotizacion.usuario).joinedload(models.User.tenant),
            joinedload(models.Cotizacion.derived_documents),
            joinedload(models.Cotizacion.source_quote),
        )
    )


def _resolve_quote_item_context(
    db: Session,
    item: schemas.CotizacionItemCreate,
    tenant_id: int,
) -> tuple[models.Producto | None, str, str, str | None]:
    db_producto = None
    if item.producto_id is not None:
        db_producto = get_producto_for_tenant(db, item.producto_id, tenant_id)
        if not db_producto:
            raise ValueError(
                "Uno de los productos no existe o no pertenece al tenant actual."
            )

    unidad_medida = (
        item.unidad_medida
        or (db_producto.unidad_medida if db_producto else None)
        or "NIU"
    )
    tipo_afectacion_igv = (
        item.tipo_afectacion_igv
        or (db_producto.tipo_afectacion_igv if db_producto else None)
        or "10"
    )
    codigo_producto = (
        item.codigo_producto
        or (db_producto.codigo_interno if db_producto else None)
        or None
    )
    return db_producto, unidad_medida, tipo_afectacion_igv, codigo_producto


def _build_quote_item(
    db: Session,
    item: schemas.CotizacionItemCreate,
    tenant_id: int,
):
    _db_producto, unidad_medida, tipo_afectacion_igv, codigo_producto = _resolve_quote_item_context(
        db,
        item,
        tenant_id,
    )
    calculo = calculations.calcular_item(
        cantidad=item.cantidad,
        precio_con_igv=item.precio_unitario,
        tipo_afectacion_igv=tipo_afectacion_igv,
    )
    db_item = models.CotizacionItem(
        producto_id=item.producto_id,
        codigo_producto=codigo_producto,
        descripcion=item.descripcion,
        cantidad=calculo["cantidad"],
        precio_unitario=calculo["precio_unitario"],
        valor_unitario=calculo["valor_unitario"],
        total_base_igv=calculo["total_base_igv"],
        total_igv=calculo["total_igv"],
        total_item=calculo["total_item"],
        unidad_medida=unidad_medida,
        tipo_afectacion_igv=tipo_afectacion_igv,
    )
    return db_item, calculo


def _build_quote_items(
    db: Session,
    cotizacion: schemas.CotizacionCreate,
    tenant_id: int,
) -> tuple[list[models.CotizacionItem], list[dict]]:
    items_db = []
    items_procesados = []
    for item in cotizacion.items:
        db_item, calculo = _build_quote_item(db, item, tenant_id)
        items_db.append(db_item)
        items_procesados.append(calculo)
    return items_db, items_procesados


def _next_quote_identity(db: Session, tenant_id: int) -> tuple[int, str]:
    last_doc = (
        db.query(models.Cotizacion)
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.serie == QUOTE_SERIE,
        )
        .order_by(models.Cotizacion.correlativo.desc())
        .with_for_update()
        .first()
    )
    ultimo_correlativo = last_doc.correlativo if last_doc else 0
    nuevo_correlativo = ultimo_correlativo + 1
    internal_order_number = build_internal_order_number(tenant_id, nuevo_correlativo)
    return nuevo_correlativo, internal_order_number


def _ensure_quote_balance_persisted(
    db: Session,
    cotizacion: models.Cotizacion,
    total_venta,
) -> None:
    if not cotizacion.saldo_pendiente or cotizacion.saldo_pendiente == 0:
        from sqlalchemy import text as _text

        db.execute(
            _text("UPDATE cotizaciones SET saldo_pendiente = :saldo WHERE id = :id"),
            {"saldo": float(total_venta), "id": cotizacion.id},
        )
        db.commit()
        db.refresh(cotizacion)


def _lock_quote_for_fiscal_creation(db: Session, quote: models.Cotizacion):
    locked_quote = (
        db.query(models.Cotizacion)
        .filter(
            models.Cotizacion.id == quote.id,
            models.Cotizacion.tenant_id == quote.tenant_id,
        )
        .with_for_update()
        .first()
    )
    if not locked_quote:
        raise ValueError(
            "La cotizacion de origen no existe o no pertenece al tenant actual."
        )
    return locked_quote


def _ensure_quote_has_no_active_fiscal_document(
    db: Session,
    quote: models.Cotizacion,
) -> None:
    fiscal_document_existente = get_latest_fiscal_document_for_quote(
        db,
        quote.id,
        quote.tenant_id,
    )
    if fiscal_document_existente:
        raise ValueError("La cotizacion ya tiene un documento fiscal asociado.")


def _ensure_subscription_capacity(db: Session, tenant_id: int) -> None:
    sub = get_subscription_by_tenant(db, tenant_id)
    if sub and sub.max_documents and (sub.documents_used or 0) >= sub.max_documents:
        raise ValueError(
            "Limite de documentos alcanzado para este periodo. "
            "Contacte al administrador para ampliar su plan."
        )


def _configured_fiscal_series(tenant: models.Tenant, tipo_comprobante: str) -> str:
    attribute = "fiscal_invoice_series" if tipo_comprobante == "01" else "fiscal_boleta_series"
    configured = str(getattr(tenant, attribute, "") or "").strip().upper()
    if configured:
        return configured
    return FACTURA_SERIE if tipo_comprobante == "01" else BOLETA_SERIE


def _resolve_fiscal_series(
    tenant: models.Tenant,
    tipo_comprobante: str,
    serie_override: str | None = None,
) -> str:
    configured = _configured_fiscal_series(tenant, tipo_comprobante)
    series_attribute = "fiscal_invoice_series" if tipo_comprobante == "01" else "fiscal_boleta_series"
    explicitly_configured = str(getattr(tenant, series_attribute, "") or "").strip()
    requested = str(serie_override or "").strip().upper()
    if requested and requested != configured:
        raise ValueError(
            f"La serie {requested} no coincide con la serie fiscal configurada ({configured})."
        )

    is_production = str(getattr(tenant, "smartpse_environment", "") or "").strip().lower() == "produccion"
    floor_attribute = "fiscal_invoice_series_floor" if tipo_comprobante == "01" else "fiscal_boleta_series_floor"
    expected_prefix = "F" if tipo_comprobante == "01" else "B"
    if is_production and not explicitly_configured:
        raise ValueError(
            "La emision en produccion requiere configurar la serie fiscal autorizada ante SUNAT."
        )
    if is_production and not configured.startswith(expected_prefix):
        document_label = "factura" if tipo_comprobante == "01" else "boleta"
        raise ValueError(
            f"La serie de {document_label} en produccion debe iniciar con {expected_prefix}."
        )
    if is_production and getattr(tenant, floor_attribute, None) is None:
        raise ValueError(
            "La emision en produccion requiere configurar la serie y el ultimo correlativo confirmado ante SUNAT."
        )
    return configured


def _build_fiscal_document(
    quote: models.Cotizacion,
    usuario_id: int,
    tipo_comprobante: str,
    serie: str,
    nuevo_correlativo: int,
):
    return models.Cotizacion(
        serie=serie,
        correlativo=nuevo_correlativo,
        cliente_id=quote.cliente_id,
        cliente_snapshot=quote.cliente_snapshot or build_cliente_snapshot(getattr(quote, "cliente", None)),
        usuario_id=usuario_id,
        tenant_id=quote.tenant_id,
        fecha_emision=quote.fecha_emision or now_in_peru_naive(),
        fecha_vencimiento=quote.fecha_vencimiento,
        moneda=quote.moneda,
        tipo_comprobante=tipo_comprobante,
        estado=DOCUMENT_STATUS_PENDING,
        document_kind=DOCUMENT_KIND_FISCAL_DOCUMENT,
        source_quote_id=quote.id,
        warehouse_id=quote.warehouse_id,
        internal_order_number=quote.internal_order_number,
        observaciones=quote.observaciones,
        condicion_pago=quote.condicion_pago,
        cuotas_pago=quote.cuotas_pago,
        total_gravada=quote.total_gravada,
        total_exonerada=quote.total_exonerada,
        total_inafecta=quote.total_inafecta,
        total_igv=quote.total_igv,
        total_venta=quote.total_venta,
        sujeta_detraccion=quote.sujeta_detraccion,
        porcentaje_detraccion=quote.porcentaje_detraccion,
        monto_detraccion=quote.monto_detraccion,
        cuenta_banco_nacion=quote.cuenta_banco_nacion,
        anticipos_deducidos=quote.anticipos_deducidos,
        total_anticipos=quote.total_anticipos,
        items=_clone_cotizacion_items(list(quote.items or [])),
    )


def _extract_provider_links(data_sunat: dict) -> dict:
    if data_sunat.get("links"):
        return data_sunat.get("links", {})
    return data_sunat.get("sunat_response", {}).get("links", {})


def _resolve_provider_error_message(data_sunat: dict) -> str:
    error = (
        data_sunat.get("sunat_error")
        or data_sunat.get("message")
        or data_sunat.get("sunat_response", {}).get("error")
        or data_sunat.get("provider_response", {}).get("error")
    )
    return str(error) if error else "El proveedor fiscal rechazo la emision."


def _resolve_note_series(serie_origen: str | None) -> str:
    if (serie_origen or "").startswith("F"):
        return FACTURA_NOTE_SERIE
    return BOLETA_NOTE_SERIE


def _next_note_correlativo(db: Session, tenant_id: int, serie_nota: str) -> int:
    last_doc = (
        db.query(models.Cotizacion)
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.serie == serie_nota,
        )
        .order_by(models.Cotizacion.correlativo.desc())
        .with_for_update()
        .first()
    )
    ultimo_correlativo = last_doc.correlativo if last_doc else 0
    return ultimo_correlativo + 1


def _build_note_document(
    doc_afectado: models.Cotizacion,
    usuario_id: int,
    tipo_nota: str,
    cod_motivo: str,
    descripcion_motivo: str,
    serie_nota: str,
    nuevo_correlativo: int,
    items: list[models.CotizacionItem] | None = None,
    totales: dict | None = None,
    inventory_impact: str = "none",
    inventory_return_warehouse_id: int | None = None,
):
    tipo_comprobante = "07" if tipo_nota == "credito" else "08"
    note_items = items if items is not None else _clone_cotizacion_items(doc_afectado.items)
    note_totals = totales or {
        "total_gravada": doc_afectado.total_gravada,
        "total_exonerada": doc_afectado.total_exonerada,
        "total_inafecta": doc_afectado.total_inafecta,
        "total_igv": doc_afectado.total_igv,
        "total_venta": doc_afectado.total_venta,
    }
    return models.Cotizacion(
        serie=serie_nota,
        correlativo=nuevo_correlativo,
        cliente_id=doc_afectado.cliente_id,
        cliente_snapshot=doc_afectado.cliente_snapshot
        or build_cliente_snapshot(getattr(doc_afectado, "cliente", None)),
        usuario_id=usuario_id,
        tenant_id=doc_afectado.tenant_id,
        moneda=doc_afectado.moneda,
        tipo_comprobante=tipo_comprobante,
        estado=DOCUMENT_STATUS_PENDING,
        document_kind=get_document_kind_for_note(tipo_nota),
        source_quote_id=resolve_source_quote_id(doc_afectado),
        internal_order_number=doc_afectado.internal_order_number,
        total_gravada=note_totals["total_gravada"],
        total_exonerada=note_totals["total_exonerada"],
        total_inafecta=note_totals["total_inafecta"],
        total_igv=note_totals["total_igv"],
        total_venta=note_totals["total_venta"],
        nota_referencia_id=doc_afectado.id,
        nota_motivo_codigo=cod_motivo,
        nota_motivo_descripcion=descripcion_motivo,
        warehouse_id=doc_afectado.warehouse_id,
        inventory_impact=inventory_impact,
        inventory_return_warehouse_id=inventory_return_warehouse_id,
        items=note_items,
    )
