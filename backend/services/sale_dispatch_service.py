"""Invoice-linked dispatch allocation and GRE draft rules.

This module never changes inventory balances. Inventory remains owned by the
accepted sales invoice; dispatch lines only allocate quantities already sold.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import re

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

import models
import fiscal_time
from access_control import DOCUMENT_EMITTER_ROLES, TENANT_ADMIN_ROLES, get_effective_role
from services.document_flow_service import (
    DOCUMENT_KIND_CREDIT_NOTE,
    DOCUMENT_KIND_FISCAL_DOCUMENT,
    DOCUMENT_STATUS_ISSUED,
    DOCUMENT_STATUS_PENDING,
    DOCUMENT_STATUS_VOIDED,
)
from services import internal_transfer_service


ZERO = Decimal("0.0000")
QTY = Decimal("0.0001")
OPEN_RESERVATIONS = {
    models.DISPATCH_RESERVATION_ACTIVE,
    models.DISPATCH_RESERVATION_COVERED,
}
EDITABLE_DISPATCH_STATUSES = {
    models.DISPATCH_STATUS_PROVISIONAL,
    models.DISPATCH_STATUS_DRAFT,
}

SUPPORTED_SALES_DOCUMENT_TYPES = {"01", "03"}


class DispatchError(ValueError):
    def __init__(self, message: str, *, status_code: int = 409, code: str = "DISPATCH_CONFLICT", context=None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.context = context or {}

    def detail(self):
        return {"code": self.code, "message": str(self), **self.context}


def _qty(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(QTY, rounding=ROUND_HALF_UP)


def _json_value(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Unsupported fingerprint value: {type(value).__name__}")


def _fingerprint(value) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json_value)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _invoice_fingerprint(invoice) -> str:
    return _fingerprint({
        "id": invoice.id,
        "document_type": invoice.tipo_comprobante,
        "status": invoice.estado,
        "error": invoice.sunat_error,
        "verification": invoice.provider_verification_status,
        "items": [
            {
                "id": item.id,
                "product": item.producto_id,
                "quantity": item.cantidad,
                "unit": item.unidad_medida,
                "description": item.descripcion,
            }
            for item in sorted(invoice.items, key=lambda row: row.id)
        ],
    })


def _get_sales_document(
    db: Session,
    tenant_id: int,
    document_id: int,
    *,
    lock=False,
    allowed_types=SUPPORTED_SALES_DOCUMENT_TYPES,
):
    filters = (
        models.Cotizacion.id == document_id,
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == DOCUMENT_KIND_FISCAL_DOCUMENT,
        models.Cotizacion.tipo_comprobante.in_(tuple(allowed_types)),
    )
    if lock:
        # Lock only the invoice row. Applying FOR UPDATE to the eager-loaded
        # LEFT JOINs is rejected by PostgreSQL because their nullable side
        # cannot be locked.
        locked_id = db.query(models.Cotizacion.id).filter(*filters).with_for_update().scalar()
        if locked_id is None:
            raise DispatchError(
                "Comprobante de venta no encontrado para la empresa autenticada.",
                status_code=404,
                code="INVOICE_NOT_FOUND",
            )
    query = db.query(models.Cotizacion).options(
        joinedload(models.Cotizacion.items),
        joinedload(models.Cotizacion.cliente),
    ).filter(*filters)
    invoice = query.first()
    if not invoice:
        raise DispatchError(
            "Comprobante de venta no encontrado para la empresa autenticada.",
            status_code=404,
            code="INVOICE_NOT_FOUND",
        )
    return invoice


def _get_invoice(db: Session, tenant_id: int, invoice_id: int, *, lock=False):
    return _get_sales_document(
        db, tenant_id, invoice_id, lock=lock, allowed_types={"01"}
    )


def _accepted_summary_for_receipt(db: Session, receipt):
    expected = str(receipt.document_number or "").upper()
    if not expected:
        return None
    summaries = db.query(models.ResumenDiario).filter(
        models.ResumenDiario.tenant_id == receipt.tenant_id,
        models.ResumenDiario.status == models.RESUMEN_DIARIO_STATUS_SENT,
        models.ResumenDiario.success.is_(True),
        models.ResumenDiario.sunat_error.is_(None),
    ).order_by(models.ResumenDiario.id.desc()).all()
    for summary in summaries:
        details = (summary.payload_snapshot or {}).get("details") or []
        if any(
            str(row.get("tipoDoc") or "").zfill(2) == "03"
            and str(row.get("serieNro") or "").upper() == expected
            and str(row.get("estado") or "1") == "1"
            for row in details
        ):
            return summary
    return None


def _source_acceptance(db: Session, document) -> tuple[dict | None, object | None]:
    if document.estado == DOCUMENT_STATUS_ISSUED and document.sunat_accepted:
        return ({
            "method": "individual_cdr",
            "document_type": document.tipo_comprobante,
            "document_number": document.document_number,
            "provider_verification_status": document.provider_verification_status,
        }, None)
    if document.tipo_comprobante == "03" and document.estado == DOCUMENT_STATUS_ISSUED:
        summary = _accepted_summary_for_receipt(db, document)
        if summary:
            return ({
                "method": "daily_summary",
                "document_type": "03",
                "document_number": document.document_number,
                "summary_id": summary.id,
                "summary_correlativo": summary.correlativo,
                "summary_status": summary.status,
            }, summary)
    return None, None


def _void_job_pending(db: Session, invoice) -> bool:
    return db.query(models.DocumentEmissionJob.id).filter(
        models.DocumentEmissionJob.tenant_id == invoice.tenant_id,
        models.DocumentEmissionJob.resource_type == models.EMISSION_JOB_RESOURCE_COTIZACION,
        models.DocumentEmissionJob.resource_id == invoice.id,
        models.DocumentEmissionJob.action == models.EMISSION_JOB_ACTION_VOID_FISCAL,
        models.DocumentEmissionJob.status.in_([
            models.EMISSION_JOB_STATUS_QUEUED,
            models.EMISSION_JOB_STATUS_PROCESSING,
            models.EMISSION_JOB_STATUS_RETRY,
            models.EMISSION_JOB_STATUS_PENDING_CONFIRMATION,
            models.EMISSION_JOB_STATUS_CONTINGENCY_PENDING,
        ]),
    ).first() is not None


def document_eligibility(db: Session, invoice) -> dict:
    label = "boleta" if invoice.tipo_comprobante == "03" else "factura"
    if getattr(invoice, "dispatch_reconciliation_status", "not_required") == "required":
        return {"can_prepare": False, "can_reserve": False, "can_emit": False, "code": "HISTORICAL_RECONCILIATION_REQUIRED", "reason": f"La {label} histórica requiere confirmar que no tuvo despachos previos fuera de este flujo."}
    if invoice.estado == DOCUMENT_STATUS_VOIDED:
        return {"can_prepare": False, "can_reserve": False, "can_emit": False, "code": "SALES_DOCUMENT_VOIDED", "reason": f"La {label} está anulada."}
    if _void_job_pending(db, invoice):
        return {"can_prepare": False, "can_reserve": False, "can_emit": False, "code": "VOID_PENDING", "reason": "La factura tiene una baja o anulación en proceso."}
    evidence, summary = _source_acceptance(db, invoice)
    if evidence:
        return {"can_prepare": True, "can_reserve": True, "can_emit": True, "code": "ACCEPTED", "reason": None, "acceptance_evidence": evidence, "source_summary_id": getattr(summary, "id", None)}
    if invoice.estado == DOCUMENT_STATUS_PENDING and not invoice.sunat_error:
        return {"can_prepare": True, "can_reserve": False, "can_emit": False, "code": "SALES_DOCUMENT_PENDING", "reason": f"La {label} aún no tiene aceptación fiscal definitiva."}
    if invoice.provider_verification_status and invoice.provider_verification_status != "verified":
        return {"can_prepare": True, "can_reserve": False, "can_emit": False, "code": "SALES_DOCUMENT_AMBIGUOUS", "reason": f"El resultado fiscal de la {label} requiere conciliación."}
    return {"can_prepare": False, "can_reserve": False, "can_emit": False, "code": "SALES_DOCUMENT_REJECTED", "reason": invoice.sunat_error or f"La {label} no tiene aceptación fiscal válida."}


def invoice_eligibility(db: Session, invoice) -> dict:
    return document_eligibility(db, invoice)


def active_dispatch_allocation_exists(db: Session, tenant_id: int, invoice_id: int) -> bool:
    return db.query(models.SaleDispatchLine.id).join(
        models.SaleDispatch, models.SaleDispatch.id == models.SaleDispatchLine.dispatch_id
    ).filter(
        models.SaleDispatch.tenant_id == tenant_id,
        models.SaleDispatch.fiscal_document_id == invoice_id,
        models.SaleDispatchLine.reservation_status.in_([
            models.DISPATCH_RESERVATION_ACTIVE,
            models.DISPATCH_RESERVATION_COVERED,
        ]),
        models.SaleDispatch.status != models.DISPATCH_STATUS_CANCELLED,
    ).first() is not None


def reconcile_historical_document(db: Session, tenant_id: int, user_id: int, invoice_id: int, payload, *, allowed_types=SUPPORTED_SALES_DOCUMENT_TYPES):
    _lock_tenant(db, tenant_id)
    invoice = _get_sales_document(
        db, tenant_id, invoice_id, lock=True, allowed_types=allowed_types
    )
    if invoice.dispatch_reconciliation_status != "required":
        return invoice
    if not payload.confirmed_no_prior_dispatch:
        raise DispatchError(
            "Un comprobante con despachos previos no puede habilitarse sin reconstruir cantidades y evidencia por línea.",
            status_code=422,
            code="HISTORICAL_DISPATCH_REMAINS_BLOCKED",
        )
    invoice.dispatch_reconciliation_status = "cleared"
    invoice.dispatch_reconciliation_evidence = {
        "confirmed_no_prior_dispatch": True,
        "note": payload.note,
        "user_id": user_id,
        "confirmed_at": datetime.now().isoformat(),
    }
    db.commit()
    return invoice


def reconcile_historical_invoice(db: Session, tenant_id: int, user_id: int, invoice_id: int, payload):
    return reconcile_historical_document(
        db, tenant_id, user_id, invoice_id, payload, allowed_types={"01"}
    )


def _cancelled_quantity(db: Session, tenant_id: int, line_id: int) -> Decimal:
    value = db.query(func.sum(models.CotizacionItem.cantidad)).join(
        models.Cotizacion,
        models.Cotizacion.id == models.CotizacionItem.cotizacion_id,
    ).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == DOCUMENT_KIND_CREDIT_NOTE,
        models.Cotizacion.estado == DOCUMENT_STATUS_ISSUED,
        models.Cotizacion.inventory_impact == "undelivered",
        models.CotizacionItem.inventory_source_item_id == line_id,
    ).scalar()
    return _qty(value)


def _pending_adjustment(db: Session, tenant_id: int, line_id: int) -> bool:
    return db.query(models.CotizacionItem.id).join(
        models.Cotizacion,
        models.Cotizacion.id == models.CotizacionItem.cotizacion_id,
    ).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == DOCUMENT_KIND_CREDIT_NOTE,
        models.Cotizacion.estado == DOCUMENT_STATUS_PENDING,
        models.CotizacionItem.inventory_source_item_id == line_id,
    ).first() is not None


def _allocated_quantities(db: Session, tenant_id: int, line_id: int, *, exclude_dispatch_id=None):
    query = db.query(
        models.SaleDispatchLine.reservation_status,
        func.sum(models.SaleDispatchLine.quantity),
    ).join(
        models.SaleDispatch,
        models.SaleDispatch.id == models.SaleDispatchLine.dispatch_id,
    ).filter(
        models.SaleDispatchLine.tenant_id == tenant_id,
        models.SaleDispatchLine.fiscal_document_item_id == line_id,
        models.SaleDispatchLine.reservation_status.in_(list(OPEN_RESERVATIONS)),
        models.SaleDispatch.status != models.DISPATCH_STATUS_CANCELLED,
    )
    if exclude_dispatch_id is not None:
        query = query.filter(models.SaleDispatchLine.dispatch_id != exclude_dispatch_id)
    rows = query.group_by(models.SaleDispatchLine.reservation_status).all()
    reserved = ZERO
    covered = ZERO
    for status, value in rows:
        if status == models.DISPATCH_RESERVATION_COVERED:
            covered += _qty(value)
        else:
            reserved += _qty(value)
    return reserved, covered


def _sale_inventory_movement(db: Session, invoice, item):
    if not item.producto_id:
        return None
    product = db.query(models.Producto).filter(
        models.Producto.id == item.producto_id,
        models.Producto.tenant_id == invoice.tenant_id,
    ).first()
    if not product:
        raise DispatchError("Una línea de factura referencia un producto ajeno o inexistente.", code="PRODUCT_SCOPE_ERROR")
    tenant = invoice.tenant
    if not tenant.inventory_enabled or not tenant.inventory_started_at or not product.inventory_enabled:
        return None
    movement = db.query(models.InventoryMovement).filter(
        models.InventoryMovement.tenant_id == invoice.tenant_id,
        models.InventoryMovement.source_type == "fiscal_document",
        models.InventoryMovement.source_id == invoice.id,
        models.InventoryMovement.source_line_id == item.id,
        models.InventoryMovement.movement_type == "sale_out",
    ).first()
    return movement


def _line_context(db: Session, invoice, item, *, exclude_dispatch_id=None) -> dict:
    cancelled = _cancelled_quantity(db, invoice.tenant_id, item.id)
    reserved, covered = _allocated_quantities(
        db, invoice.tenant_id, item.id, exclude_dispatch_id=exclude_dispatch_id
    )
    invoiced = _qty(item.cantidad)
    available = max(ZERO, invoiced - cancelled - reserved - covered)
    product = None
    if item.producto_id:
        product = db.query(models.Producto).filter(
            models.Producto.id == item.producto_id,
            models.Producto.tenant_id == invoice.tenant_id,
        ).first()
    movement = _sale_inventory_movement(db, invoice, item)
    inventory_missing = bool(
        product
        and product.inventory_enabled
        and invoice.tenant.inventory_enabled
        and invoice.tenant.inventory_started_at
        and movement is None
    )
    item_type = getattr(product, "item_type", None) or "manual"
    return {
        "id": item.id,
        "product_id": item.producto_id,
        "product_code": item.codigo_producto,
        "description": item.descripcion,
        "unit": item.unidad_medida,
        "item_type": item_type,
        "requires_goods_confirmation": item_type in {"manual", "unclassified"},
        "dispatchable": item_type != "service",
        "invoiced": invoiced,
        "cancelled_undelivered": cancelled,
        "reserved": reserved,
        "covered": covered,
        "available": available,
        "pending_adjustment": _pending_adjustment(db, invoice.tenant_id, item.id),
        "inventory_movement_id": movement.id if movement else None,
        "inventory_evidence_missing": inventory_missing,
    }


def transport_requirements_catalog() -> dict:
    return {
        "private": {
            "required": ["fecha_traslado", "vehiculo_placa", "conductor_tipo_doc", "conductor_nro_doc", "conductor_nombres", "conductor_apellidos", "conductor_licencia"],
            "gre_31_required": False,
        },
        "public_carrier_guide": {
            "required": ["fecha_entrega_transportista", "transportista_ruc", "transportista_razon_social", "transportista_nro_mtc"],
            "gre_31_required": True,
        },
        "public_registered": {
            "required": ["fecha_entrega_transportista", "transportista_ruc", "transportista_razon_social", "transportista_nro_mtc", "vehiculo_placa", "vehiculo_nro_circulacion", "conductor_tipo_doc", "conductor_nro_doc", "conductor_nombres", "conductor_apellidos", "conductor_licencia", "transportista_acuerdo_confirmado"],
            "gre_31_required": False,
        },
        "m1_l_public": {
            "required": ["fecha_entrega_transportista", "vehiculo_placa"],
            "gre_31_required": False,
        },
        "m1_l_private": {
            "required": ["fecha_traslado", "vehiculo_placa"],
            "gre_31_required": False,
        },
    }


def _source_location_context(db: Session, tenant_id: int, warehouse_id: int | None) -> dict:
    establishment_rules_enabled = db.query(models.TenantEstablishment.id).filter(
        models.TenantEstablishment.tenant_id == tenant_id,
        models.TenantEstablishment.is_active.is_(True),
        models.TenantEstablishment.verified_at.isnot(None),
    ).first() is not None
    if not warehouse_id:
        return {
            "ready": False,
            "enforced": establishment_rules_enabled,
            "reason": "El comprobante no tiene un almacén de origen asociado.",
            "warehouse": None,
            "establishment": None,
        }
    warehouse = db.query(models.Warehouse).options(
        joinedload(models.Warehouse.establishment)
    ).filter(
        models.Warehouse.id == warehouse_id,
        models.Warehouse.tenant_id == tenant_id,
        models.Warehouse.is_active.is_(True),
    ).first()
    if not warehouse:
        return {
            "ready": False,
            "enforced": establishment_rules_enabled,
            "reason": "El almacén de origen ya no está disponible.",
            "warehouse": None,
            "establishment": None,
        }
    establishment = warehouse.establishment
    complete = bool(
        establishment
        and establishment.is_active
        and establishment.verified_at
        and re.fullmatch(r"\d{4}", str(establishment.sunat_code or ""))
        and re.fullmatch(r"\d{6}", str(establishment.ubigeo or ""))
        and str(establishment.address or "").strip()
    )
    return {
        "ready": complete,
        "enforced": establishment_rules_enabled,
        "reason": None if complete else "Vincula y sincroniza el almacén con un establecimiento SUNAT antes de emitir.",
        "warehouse": {
            "id": warehouse.id,
            "code": warehouse.code,
            "name": warehouse.name,
            "location": warehouse.location,
        },
        "establishment": None if not establishment else {
            "id": establishment.id,
            "sunat_code": establishment.sunat_code,
            "name": establishment.name,
            "ubigeo": establishment.ubigeo,
            "address": establishment.address,
            "verified_at": establishment.verified_at,
        },
    }


def _apply_persisted_source_location(db: Session, tenant_id: int, warehouse_id: int | None, guide) -> None:
    source = _source_location_context(db, tenant_id, warehouse_id)
    if not source["ready"]:
        return
    establishment = source["establishment"]
    guide.partida_codigo_local = establishment["sunat_code"]
    guide.partida_ubigeo = establishment["ubigeo"]
    guide.partida_direccion = establishment["address"]


def get_sales_document_dispatch_context(db: Session, tenant_id: int, invoice_id: int, *, lock=False, exclude_dispatch_id=None, allowed_types=SUPPORTED_SALES_DOCUMENT_TYPES) -> dict:
    invoice = _get_sales_document(db, tenant_id, invoice_id, lock=lock, allowed_types=allowed_types)
    eligibility = document_eligibility(db, invoice)
    client = invoice.cliente
    lines = [
        _line_context(db, invoice, item, exclude_dispatch_id=exclude_dispatch_id)
        for item in sorted(invoice.items, key=lambda row: row.id)
    ]
    return {
        "invoice": {
            "id": invoice.id,
            "number": invoice.document_number,
            "status": invoice.estado,
            "issue_date": invoice.fecha_emision,
            "warehouse_id": invoice.warehouse_id,
            "fingerprint": _invoice_fingerprint(invoice),
            "document_type": invoice.tipo_comprobante,
        },
        "customer": {
            "id": invoice.cliente_id,
            "document_type": getattr(client, "tipo_documento", None),
            "document_number": getattr(client, "numero_documento", None),
            "name": getattr(client, "razon_social", None),
            "address": getattr(client, "direccion_entrega", None) or getattr(client, "direccion", None),
            "ubigeo": getattr(client, "ubigeo", None),
        },
        "eligibility": eligibility,
        "transport_requirements": transport_requirements_catalog(),
        "source_location": _source_location_context(db, tenant_id, invoice.warehouse_id),
        "source_document": {
            "id": invoice.id,
            "type": invoice.tipo_comprobante,
            "label": "Boleta de venta" if invoice.tipo_comprobante == "03" else "Factura",
            "number": invoice.document_number,
        },
        "lines": lines,
    }


def get_invoice_dispatch_context(db: Session, tenant_id: int, invoice_id: int, **kwargs) -> dict:
    return get_sales_document_dispatch_context(
        db, tenant_id, invoice_id, allowed_types={"01"}, **kwargs
    )


def _lock_tenant(db: Session, tenant_id: int):
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).with_for_update().first()
    if not tenant or not tenant.is_active:
        raise DispatchError("La empresa no está activa para crear despachos.", status_code=403, code="TENANT_INACTIVE")
    return tenant


def _next_guide_number(db: Session, tenant_id: int, document_type: str, series: str) -> int:
    from services.guide_series_service import GuideSeriesConfigurationError, next_guide_correlativo
    try:
        return next_guide_correlativo(db, tenant_id, document_type, series)
    except GuideSeriesConfigurationError as exc:
        raise DispatchError(str(exc), status_code=422, code=exc.code) from exc


def _guide_environment(tenant) -> str:
    from services.guide_series_service import GuideSeriesConfigurationError, guide_environment
    try:
        return guide_environment(tenant)
    except GuideSeriesConfigurationError as exc:
        raise DispatchError(str(exc), status_code=422, code=exc.code) from exc


def _guide_series(tenant, document_type: str) -> tuple[str, str]:
    from services.guide_series_service import GuideSeriesConfigurationError, guide_series
    try:
        return guide_series(tenant, document_type)
    except GuideSeriesConfigurationError as exc:
        raise DispatchError(str(exc), status_code=422, code=exc.code) from exc


def _guide_fields(data) -> dict:
    names = (
        "fecha_traslado", "peso_bruto_total", "unidad_medida_peso", "numero_bultos",
        "modalidad_traslado", "fecha_entrega_transportista", "indicador_m1_l",
        "registrar_vehiculo_transportista", "transportista_ruc", "transportista_razon_social",
        "transportista_nro_mtc", "conductor_tipo_doc", "conductor_nro_doc",
        "conductor_nombres", "conductor_apellidos", "conductor_licencia", "vehiculo_placa",
        "vehiculo_nro_circulacion", "vehiculo_cod_emisor", "vehiculo_nro_autorizacion",
        "partida_ubigeo", "partida_direccion", "llegada_ubigeo", "llegada_direccion",
        "observaciones",
    )
    return {name: getattr(data, name) for name in names}


def _apply_carrier_agreement(guide, data, user_id: int) -> None:
    confirmed = bool(getattr(data, "transportista_acuerdo_confirmado", False))
    if confirmed:
        guide.transportista_acuerdo_confirmado_at = datetime.now()
        guide.transportista_acuerdo_confirmado_by_user_id = user_id
    else:
        guide.transportista_acuerdo_confirmado_at = None
        guide.transportista_acuerdo_confirmado_by_user_id = None


def _selected_line_map(payload) -> dict[int, object]:
    return {line.fiscal_document_item_id: line for line in payload.lines}


def _validate_selection(context: dict, selections: dict[int, object], *, can_reserve: bool):
    by_id = {line["id"]: line for line in context["lines"]}
    resolved = []
    for line_id, selected in selections.items():
        line = by_id.get(line_id)
        if not line:
            raise DispatchError("Una línea seleccionada no pertenece al comprobante.", code="LINE_SCOPE_ERROR")
        if not line["dispatchable"]:
            raise DispatchError(f"'{line['description']}' está clasificado como servicio y no puede despacharse.", code="SERVICE_LINE")
        if line["requires_goods_confirmation"] and not selected.confirmed_as_goods:
            raise DispatchError(f"Confirma que '{line['description']}' corresponde a un bien.", status_code=422, code="GOODS_CONFIRMATION_REQUIRED")
        if line["pending_adjustment"] and can_reserve:
            raise DispatchError(f"'{line['description']}' tiene un ajuste fiscal pendiente.", code="PENDING_LINE_ADJUSTMENT")
        if line["inventory_evidence_missing"] and can_reserve:
            raise DispatchError(f"Falta conciliar la salida de inventario de '{line['description']}'.", code="INVENTORY_EVIDENCE_MISSING")
        requested = _qty(selected.quantity)
        if can_reserve and requested > line["available"]:
            raise DispatchError(
                f"La cantidad de '{line['description']}' excede el saldo disponible.",
                code="DISPATCH_QUANTITY_EXCEEDED",
                context={"line_id": line_id, "requested": str(requested), "available": str(line["available"])},
            )
        resolved.append((line, selected, requested))
    return resolved


def _new_guide_from_dispatch(db: Session, tenant, invoice, dispatch, data, resolved_lines, user_id: int):
    client = invoice.cliente
    environment, series = _guide_series(tenant, "09")
    guide = models.GuiaRemision(
        tipo_documento="09",
        serie=series,
        correlativo=_next_guide_number(db, tenant.id, "09", series),
        emission_environment=environment,
        fecha_emision=fiscal_time.now_lima_naive(),
        estado="pendiente",
        tenant_id=tenant.id,
        usuario_id=user_id,
        cotizacion_id=invoice.id,
        fiscal_document_id=invoice.id,
        source_quote_id=invoice.source_quote_id,
        internal_order_number=invoice.internal_order_number,
        cliente_id=invoice.cliente_id,
        dispatch=dispatch,
        motivo_traslado="01",
        descripcion_motivo="VENTA",
        destinatario_tipo_doc=getattr(client, "tipo_documento", None),
        destinatario_nro_doc=getattr(client, "numero_documento", None),
        destinatario_razon_social=getattr(client, "razon_social", None),
        **_guide_fields(data),
    )
    db.add(guide)
    _apply_persisted_source_location(db, tenant.id, invoice.warehouse_id, guide)
    _apply_carrier_agreement(guide, data, user_id)
    db.flush()
    for line_context, selected, quantity in resolved_lines:
        dispatch_line = next(row for row in dispatch.lines if row.fiscal_document_item_id == line_context["id"])
        guide.items.append(models.GuiaRemisionItem(
            dispatch_line_id=dispatch_line.id,
            fiscal_document_item_id=line_context["id"],
            producto_id=line_context["product_id"],
            descripcion=line_context["description"],
            cantidad=quantity,
            unidad_medida=line_context["unit"],
            codigo_producto=line_context["product_code"],
        ))
    return guide


def create_from_document(db: Session, tenant_id: int, user_id: int, payload, *, allowed_types=SUPPORTED_SALES_DOCUMENT_TYPES):
    tenant = _lock_tenant(db, tenant_id)
    request_data = payload.model_dump(mode="json")
    request_fingerprint = _fingerprint(request_data)
    existing = db.query(models.SaleDispatch).filter(
        models.SaleDispatch.tenant_id == tenant_id,
        models.SaleDispatch.idempotency_key == payload.idempotency_key,
    ).first()
    if existing:
        if existing.request_fingerprint != request_fingerprint:
            raise DispatchError("La clave de idempotencia ya fue usada con otro contenido.", code="IDEMPOTENCY_CONFLICT")
        return get_dispatch(db, tenant_id, existing.id), False

    context = get_sales_document_dispatch_context(
        db, tenant_id, payload.fiscal_document_id, lock=True, allowed_types=allowed_types
    )
    eligibility = context["eligibility"]
    if not eligibility["can_prepare"]:
        raise DispatchError(eligibility["reason"], code=eligibility["code"])
    selections = _selected_line_map(payload)
    resolved = _validate_selection(context, selections, can_reserve=eligibility["can_reserve"])
    reservation_status = models.DISPATCH_RESERVATION_ACTIVE if eligibility["can_reserve"] else models.DISPATCH_RESERVATION_PROVISIONAL
    dispatch = models.SaleDispatch(
        tenant_id=tenant_id,
        fiscal_document_id=payload.fiscal_document_id,
        source_document_type=context["source_document"]["type"],
        source_summary_id=eligibility.get("source_summary_id"),
        source_acceptance_evidence=eligibility.get("acceptance_evidence"),
        warehouse_id=context["invoice"]["warehouse_id"],
        created_by_user_id=user_id,
        status=models.DISPATCH_STATUS_DRAFT if eligibility["can_reserve"] else models.DISPATCH_STATUS_PROVISIONAL,
        idempotency_key=payload.idempotency_key,
        request_fingerprint=request_fingerprint,
        provisional_invoice_fingerprint=None if eligibility["can_reserve"] else context["invoice"]["fingerprint"],
    )
    db.add(dispatch)
    db.flush()
    now = datetime.now()
    for line, selected, quantity in resolved:
        dispatch.lines.append(models.SaleDispatchLine(
            tenant_id=tenant_id,
            fiscal_document_item_id=line["id"],
            product_id=line["product_id"],
            inventory_movement_id=line["inventory_movement_id"],
            quantity=quantity,
            unit_code=line["unit"],
            product_code=line["product_code"],
            description=line["description"],
            confirmed_as_goods=selected.confirmed_as_goods,
            reservation_status=reservation_status,
            reserved_at=now if eligibility["can_reserve"] else None,
        ))
    db.flush()
    invoice = _get_sales_document(
        db, tenant_id, payload.fiscal_document_id, allowed_types=allowed_types
    )
    _new_guide_from_dispatch(db, tenant, invoice, dispatch, payload, resolved, user_id)
    db.commit()
    return get_dispatch(db, tenant_id, dispatch.id), True


def create_from_invoice(db: Session, tenant_id: int, user_id: int, payload):
    return create_from_document(
        db, tenant_id, user_id, payload, allowed_types={"01"}
    )


def get_dispatch(db: Session, tenant_id: int, dispatch_id: int, *, lock=False):
    filters = (
        models.SaleDispatch.id == dispatch_id,
        models.SaleDispatch.tenant_id == tenant_id,
    )
    if lock:
        # As with invoices, lock the base row separately from collection and
        # nullable relationship eager loads.
        locked_id = db.query(models.SaleDispatch.id).filter(*filters).with_for_update().scalar()
        if locked_id is None:
            return None
    query = db.query(models.SaleDispatch).options(
        joinedload(models.SaleDispatch.lines),
        joinedload(models.SaleDispatch.guides).joinedload(models.GuiaRemision.cliente),
    ).filter(*filters)
    return query.first()


def update_dispatch(db: Session, tenant_id: int, dispatch_id: int, payload, *, user_id: int | None = None):
    _lock_tenant(db, tenant_id)
    dispatch = get_dispatch(db, tenant_id, dispatch_id, lock=True)
    if not dispatch:
        raise DispatchError("Despacho no encontrado.", status_code=404, code="DISPATCH_NOT_FOUND")
    if dispatch.status not in EDITABLE_DISPATCH_STATUSES:
        raise DispatchError("El despacho ya no es editable.", code="DISPATCH_IMMUTABLE")
    if dispatch.version != payload.version:
        context = get_sales_document_dispatch_context(db, tenant_id, dispatch.fiscal_document_id, exclude_dispatch_id=dispatch.id)
        raise DispatchError("El borrador cambió en otra sesión.", code="VERSION_CONFLICT", context={"current_version": dispatch.version, "context": context})
    context = get_sales_document_dispatch_context(db, tenant_id, dispatch.fiscal_document_id, lock=True, exclude_dispatch_id=dispatch.id)
    eligibility = context["eligibility"]
    if not eligibility["can_prepare"]:
        raise DispatchError(eligibility["reason"], code=eligibility["code"])
    resolved = _validate_selection(context, _selected_line_map(payload), can_reserve=eligibility["can_reserve"])
    guide = next((row for row in dispatch.guides if row.tipo_documento == "09"), None)
    if not guide or guide.estado != "pendiente":
        raise DispatchError("La guía asociada ya no es editable.", code="GUIDE_IMMUTABLE")
    # Delete dependent guide items before replacing their dispatch lines.
    guide.items.clear()
    db.flush()
    dispatch.lines.clear()
    db.flush()
    reservation_status = models.DISPATCH_RESERVATION_ACTIVE if eligibility["can_reserve"] else models.DISPATCH_RESERVATION_PROVISIONAL
    now = datetime.now()
    for line, selected, quantity in resolved:
        dispatch.lines.append(models.SaleDispatchLine(
            tenant_id=tenant_id, fiscal_document_item_id=line["id"], product_id=line["product_id"],
            inventory_movement_id=line["inventory_movement_id"], quantity=quantity,
            unit_code=line["unit"], product_code=line["product_code"], description=line["description"],
            confirmed_as_goods=selected.confirmed_as_goods, reservation_status=reservation_status,
            reserved_at=now if eligibility["can_reserve"] else None,
        ))
    for key, value in _guide_fields(payload).items():
        setattr(guide, key, value)
    _apply_persisted_source_location(db, tenant_id, dispatch.warehouse_id, guide)
    _apply_carrier_agreement(guide, payload, user_id or guide.usuario_id)
    db.flush()
    for line_context, selected, quantity in resolved:
        dispatch_line = next(row for row in dispatch.lines if row.fiscal_document_item_id == line_context["id"])
        guide.items.append(models.GuiaRemisionItem(
            dispatch_line_id=dispatch_line.id, fiscal_document_item_id=line_context["id"],
            producto_id=line_context["product_id"], descripcion=line_context["description"],
            cantidad=quantity, unidad_medida=line_context["unit"], codigo_producto=line_context["product_code"],
        ))
    dispatch.status = models.DISPATCH_STATUS_DRAFT if eligibility["can_reserve"] else models.DISPATCH_STATUS_PROVISIONAL
    dispatch.provisional_invoice_fingerprint = None if eligibility["can_reserve"] else context["invoice"]["fingerprint"]
    dispatch.source_document_type = context["source_document"]["type"]
    dispatch.source_summary_id = eligibility.get("source_summary_id")
    dispatch.source_acceptance_evidence = eligibility.get("acceptance_evidence")
    dispatch.version += 1
    dispatch.request_fingerprint = _fingerprint(payload.model_dump(mode="json"))
    db.commit()
    return get_dispatch(db, tenant_id, dispatch.id)


def cancel_dispatch(db: Session, tenant_id: int, dispatch_id: int):
    _lock_tenant(db, tenant_id)
    dispatch = get_dispatch(db, tenant_id, dispatch_id, lock=True)
    if not dispatch:
        raise DispatchError("Despacho no encontrado.", status_code=404, code="DISPATCH_NOT_FOUND")
    if dispatch.status == models.DISPATCH_STATUS_CANCELLED:
        return dispatch
    if dispatch.status not in EDITABLE_DISPATCH_STATUSES:
        raise DispatchError("Solo se puede cancelar localmente un borrador no enviado.", code="DISPATCH_IMMUTABLE")
    now = datetime.now()
    for line in dispatch.lines:
        line.reservation_status = models.DISPATCH_RESERVATION_RELEASED
        line.released_at = now
    for guide in dispatch.guides:
        if guide.estado == "pendiente":
            guide.estado = "cancelled"
    dispatch.status = models.DISPATCH_STATUS_CANCELLED
    dispatch.cancelled_at = now
    dispatch.version += 1
    db.commit()
    return get_dispatch(db, tenant_id, dispatch.id)


def transport_scenario(guide) -> str:
    """Return the one authoritative transport scenario used by every action."""
    if bool(getattr(guide, "indicador_m1_l", False)):
        return "m1_l_public" if guide.modalidad_traslado == "01" else "m1_l_private"
    if guide.modalidad_traslado == "01":
        return "public_registered" if bool(
            getattr(guide, "registrar_vehiculo_transportista", False)
        ) else "public_carrier_guide"
    return "private"


def carrier_guide_required(guide) -> bool:
    return transport_scenario(guide) == "public_carrier_guide"


def _transport_validation_errors(guide) -> list[dict]:
    errors = []

    def required(fields, code, message):
        for field in fields:
            if not getattr(guide, field, None):
                errors.append({"field": field, "code": code, "message": message})

    scenario = transport_scenario(guide)
    if guide.indicador_m1_l and guide.registrar_vehiculo_transportista:
        errors.append({
            "field": "registrar_vehiculo_transportista",
            "code": "CONTRADICTORY_TRANSPORT_FLAGS",
            "message": "M1/L no puede combinarse con el registro completo de vehículo y conductor del transportista.",
        })
    if scenario.startswith("m1_l"):
        required(("vehiculo_placa",), "M1L_PLATE_REQUIRED", "M1/L requiere la placa del vehículo.")
        if scenario == "m1_l_public":
            required(("fecha_entrega_transportista",), "M1L_DELIVERY_DATE_REQUIRED", "M1/L público requiere la fecha de entrega al transportista.")
    elif scenario == "public_carrier_guide":
        required(
            ("transportista_ruc", "transportista_razon_social", "transportista_nro_mtc", "fecha_entrega_transportista"),
            "PUBLIC_TRANSPORT_REQUIRED",
            "Campo obligatorio para transporte público.",
        )
    elif scenario == "public_registered":
        required(
            ("transportista_ruc", "transportista_razon_social", "transportista_nro_mtc", "fecha_entrega_transportista"),
            "PUBLIC_TRANSPORT_REQUIRED",
            "Campo obligatorio para transporte público.",
        )
        required(
            ("vehiculo_placa", "vehiculo_nro_circulacion", "conductor_tipo_doc", "conductor_nro_doc", "conductor_nombres", "conductor_apellidos", "conductor_licencia"),
            "CARRIER_FLEET_REQUIRED",
            "Campo obligatorio al registrar vehículo y conductor del transportista.",
        )
        if not getattr(guide, "transportista_acuerdo_confirmado_at", None):
            errors.append({
                "field": "transportista_acuerdo_confirmado",
                "code": "CARRIER_AGREEMENT_REQUIRED",
                "message": "Confirma y audita el acuerdo con el transportista para omitir la GRE 31.",
            })
    else:
        required(
            ("vehiculo_placa", "conductor_tipo_doc", "conductor_nro_doc", "conductor_nombres", "conductor_apellidos", "conductor_licencia"),
            "PRIVATE_TRANSPORT_REQUIRED",
            "Campo obligatorio para transporte privado.",
        )
    return errors


def validate_guide_for_emission(db: Session, guide) -> dict:
    errors = []
    warnings = []
    dispatch = guide.dispatch or guide.internal_transfer_dispatch
    tenant = db.query(models.Tenant).filter(models.Tenant.id == guide.tenant_id).first()
    try:
        current_environment, expected_series = _guide_series(tenant, guide.tipo_documento)
        if guide.emission_environment != current_environment or guide.serie != expected_series:
            errors.append({
                "field": "emission_environment",
                "code": "GUIDE_ENVIRONMENT_CHANGED",
                "message": (
                    "El ambiente o la serie cambió después de crear el borrador. "
                    "Cancela este borrador y crea uno nuevo en el ambiente actual."
                ),
            })
    except DispatchError as exc:
        errors.append({"field": "emission_environment", "code": exc.code, "message": str(exc)})
    if guide.tipo_documento == "09":
        if guide.motivo_traslado == "04":
            errors.extend(internal_transfer_service.validate_guide_for_emission(db, guide))
        elif not dispatch or not guide.fiscal_document_id:
            errors.append({"field": "fiscal_document_id", "code": "SALES_DOCUMENT_REQUIRED", "message": "La GRE 09 inicial debe provenir de una factura o boleta de venta."})
        else:
            context = get_sales_document_dispatch_context(db, guide.tenant_id, guide.fiscal_document_id, lock=True, exclude_dispatch_id=dispatch.id)
            eligibility = context["eligibility"]
            if dispatch.source_document_type != context["source_document"]["type"]:
                errors.append({
                    "field": "fiscal_document_id",
                    "code": "SOURCE_DOCUMENT_TYPE_MISMATCH",
                    "message": "El tipo del comprobante origen no coincide con el registrado en el despacho.",
                })
            if not eligibility["can_emit"]:
                errors.append({"field": "fiscal_document_id", "code": eligibility["code"], "message": eligibility["reason"]})
            if dispatch.status == models.DISPATCH_STATUS_PROVISIONAL:
                errors.append({"field": "dispatch", "code": "PROVISIONAL_DISPATCH", "message": "Confirma nuevamente el borrador después de la aceptación del comprobante."})
            if any(line.reservation_status != models.DISPATCH_RESERVATION_ACTIVE for line in dispatch.lines):
                errors.append({"field": "lines", "code": "RESERVATION_REQUIRED", "message": "Todas las cantidades deben tener una reserva activa."})
            source_location = context["source_location"]
            if not source_location["ready"]:
                issue = {
                    "field": "partida_codigo_local",
                    "code": "SOURCE_ESTABLISHMENT_REQUIRED",
                    "message": (
                        source_location["reason"]
                        if source_location["enforced"]
                        else f"{source_location['reason']} El borrador conserva la ruta manual por compatibilidad."
                    ),
                }
                if source_location["enforced"]:
                    errors.append(issue)
                else:
                    warnings.append(issue)
            else:
                establishment = source_location["establishment"]
                current_identity = (
                    guide.partida_codigo_local,
                    guide.partida_ubigeo,
                    str(guide.partida_direccion or "").strip(),
                )
                expected_identity = (
                    establishment["sunat_code"],
                    establishment["ubigeo"],
                    str(establishment["address"] or "").strip(),
                )
                if current_identity != expected_identity:
                    errors.append({
                        "field": "partida_codigo_local",
                        "code": "SOURCE_ESTABLISHMENT_CHANGED",
                        "message": "Los datos SUNAT del origen cambiaron. Actualiza el borrador antes de emitir.",
                    })
            source = dispatch.fiscal_document
            if source and source.tipo_comprobante == "03":
                document_number = str(guide.destinatario_nro_doc or "").strip()
                document_type = str(guide.destinatario_tipo_doc or "").strip()
                if document_type in {"", "0"} or document_number in {"", "00000000"}:
                    errors.append({
                        "field": "destinatario_nro_doc",
                        "code": "RECIPIENT_IDENTITY_REQUIRED",
                        "message": "La boleta tiene destinatario genérico; identifica y contrasta al destinatario del despacho antes de emitir.",
                    })
    elif guide.tipo_documento == "31":
        if not guide.external_gre_reference or guide.external_gre_reference.document_type != "09":
            errors.append({"field": "gre_remitente", "code": "GRE_09_REQUIRED", "message": "La GRE 31 requiere la referencia de una GRE remitente 09."})
        elif guide.external_gre_reference.verification_status != "verified":
            errors.append({"field": "gre_remitente", "code": "GRE_09_NOT_VERIFIED", "message": "La GRE remitente externa debe tener XML y CDR de aceptación verificados por un administrador."})
        if not guide.goods_invoice_reference or guide.goods_invoice_reference.document_type not in SUPPORTED_SALES_DOCUMENT_TYPES:
            errors.append({"field": "goods_invoice", "code": "GOODS_DOCUMENT_REQUIRED", "message": "La factura o boleta de bienes debe conservarse como referencia separada."})
        if not tenant or guide.transportista_ruc != tenant.business_ruc:
            errors.append({"field": "transportista_ruc", "code": "CARRIER_ISSUER_MISMATCH", "message": "La GRE 31 solo puede emitirla el tenant transportista autenticado."})
    if guide.motivo_traslado not in {"01", "04"}:
        errors.append({"field": "motivo_traslado", "code": "OUT_OF_SCOPE", "message": "Esta versión emite guías por venta (01) o traslado interno (04)."})
    if guide.fecha_traslado and guide.fecha_emision and guide.fecha_traslado.date() < guide.fecha_emision.date():
        errors.append({"field": "fecha_traslado", "code": "INVALID_TRANSFER_DATE", "message": "La fecha de traslado no puede ser anterior a la fecha de emisión."})
    if guide.tipo_documento == "31" and guide.modalidad_traslado != "01":
        errors.append({"field": "modalidad_traslado", "code": "TRANSPORT_GUIDE_PUBLIC_ONLY", "message": "La GRE transportista usa modalidad pública 01."})
    if not guide.items:
        errors.append({"field": "items", "code": "ITEMS_REQUIRED", "message": "Selecciona al menos un bien."})
    if not guide.peso_bruto_total or Decimal(str(guide.peso_bruto_total)) <= 0:
        errors.append({"field": "peso_bruto_total", "code": "WEIGHT_REQUIRED", "message": "Registra un peso bruto positivo."})
    for field in ("partida_ubigeo", "llegada_ubigeo"):
        if not re.fullmatch(r"\d{6}", str(getattr(guide, field, "") or "")):
            errors.append({"field": field, "code": "INVALID_UBIGEO", "message": "El ubigeo debe tener seis dígitos."})
    if guide.tipo_documento == "09":
        errors.extend(_transport_validation_errors(guide))
    else:
        for field in (
            "transportista_ruc", "transportista_razon_social", "transportista_nro_mtc",
            "vehiculo_placa", "conductor_tipo_doc", "conductor_nro_doc",
            "conductor_nombres", "conductor_apellidos", "conductor_licencia",
        ):
            if not getattr(guide, field, None):
                errors.append({
                    "field": field,
                    "code": "TRANSPORT_GUIDE_FIELD_REQUIRED",
                    "message": "Campo obligatorio para la GRE del transportista.",
                })
    if guide.vehiculo_placa and not re.fullmatch(r"[A-Z0-9]{6,8}", guide.vehiculo_placa.upper()):
        errors.append({"field": "vehiculo_placa", "code": "INVALID_PLATE", "message": "La placa debe tener entre 6 y 8 caracteres alfanuméricos."})
    if guide.conductor_licencia and not re.fullmatch(r"[A-Z0-9]{9,10}", guide.conductor_licencia.upper()):
        errors.append({"field": "conductor_licencia", "code": "INVALID_LICENSE", "message": "La licencia debe tener entre 9 y 10 caracteres alfanuméricos."})
    return {"valid": not errors, "errors": errors, "warnings": warnings}


def mark_guide_pending(db: Session, guide):
    if guide.internal_transfer_dispatch_id:
        internal_transfer_service.mark_guide_pending(db, guide)
    if guide.dispatch:
        guide.dispatch.status = models.DISPATCH_STATUS_GUIDE_PENDING
        guide.dispatch.version += 1
    guide.estado = "pendiente_smartpse"
    db.flush()


def apply_guide_result(db: Session, guide, *, accepted: bool, rejected: bool = False):
    if guide.internal_transfer_dispatch_id:
        internal_transfer_service.apply_guide_result(db, guide, accepted=accepted, rejected=rejected)
        return
    dispatch = guide.dispatch or guide.internal_transfer_dispatch
    if not dispatch:
        return
    now = datetime.now()
    if accepted:
        for line in dispatch.lines:
            if line.reservation_status == models.DISPATCH_RESERVATION_ACTIVE:
                line.reservation_status = models.DISPATCH_RESERVATION_COVERED
                line.covered_at = now
        dispatch.status = models.DISPATCH_STATUS_GUIDE_ACCEPTED
    elif rejected:
        for line in dispatch.lines:
            if line.reservation_status == models.DISPATCH_RESERVATION_ACTIVE:
                line.reservation_status = models.DISPATCH_RESERVATION_RELEASED
                line.released_at = now
        dispatch.status = models.DISPATCH_STATUS_GUIDE_REJECTED
        guide.rejected_at = now
    dispatch.version += 1


def lock_guide_result_scope(db: Session, guide):
    """Short lock scope used only while persisting a definitive fiscal result."""
    _lock_tenant(db, guide.tenant_id)
    if guide.dispatch_id:
        dispatch = get_dispatch(db, guide.tenant_id, guide.dispatch_id, lock=True)
        if dispatch:
            _get_sales_document(db, guide.tenant_id, dispatch.fiscal_document_id, lock=True)
    elif guide.internal_transfer_dispatch_id:
        internal_transfer_service.lock_guide_result_scope(db, guide)


def confirm_departure(db: Session, tenant_id: int, dispatch_id: int, user_id: int, idempotency_key: str):
    _lock_tenant(db, tenant_id)
    dispatch = get_dispatch(db, tenant_id, dispatch_id, lock=True)
    if not dispatch:
        raise DispatchError("Despacho no encontrado.", status_code=404, code="DISPATCH_NOT_FOUND")
    if dispatch.departure_confirmed_at:
        return dispatch
    remitente = next((guide for guide in dispatch.guides if guide.tipo_documento == "09"), None)
    if not remitente or remitente.estado != "emitida":
        raise DispatchError("La GRE remitente debe estar aceptada antes de confirmar la salida.", code="GRE_09_NOT_ACCEPTED")
    if carrier_guide_required(remitente):
        internal = db.query(models.GuiaRemision.id).filter(
            models.GuiaRemision.tenant_id == tenant_id,
            models.GuiaRemision.related_guide_id == remitente.id,
            models.GuiaRemision.tipo_documento == "31",
            models.GuiaRemision.estado == "emitida",
        ).first()
        external = remitente.external_gre_reference and remitente.external_gre_reference.verification_status == "verified"
        if not internal and not external:
            raise DispatchError("Falta una GRE transportista aceptada o verificada para este traslado público.", code="GRE_31_REQUIRED")
    dispatch.departure_confirmed_at = datetime.now()
    dispatch.departure_confirmed_by_user_id = user_id
    dispatch.status = models.DISPATCH_STATUS_DEPARTED
    dispatch.version += 1
    dispatch.logistical_block_detail = f"departure-key:{hashlib.sha256(idempotency_key.encode()).hexdigest()[:16]}"
    db.commit()
    return get_dispatch(db, tenant_id, dispatch.id)


def _external_reference(db: Session, tenant_id: int, user_id: int, data, *, source: str):
    existing = db.query(models.GuideExternalReference).filter(
        models.GuideExternalReference.tenant_id == tenant_id,
        models.GuideExternalReference.document_type == data.document_type,
        models.GuideExternalReference.issuer_ruc == data.issuer_ruc,
        models.GuideExternalReference.series == data.series.upper(),
        models.GuideExternalReference.number == data.number,
    ).first()
    if existing:
        return existing
    reference = models.GuideExternalReference(
        tenant_id=tenant_id,
        document_type=data.document_type,
        issuer_ruc=data.issuer_ruc,
        series=data.series.upper(),
        number=data.number,
        source=source,
        verification_status="unverified",
        evidence=data.evidence,
        created_by_user_id=user_id,
    )
    db.add(reference)
    db.flush()
    return reference


def verify_external_guide_reference(db: Session, tenant_id: int, user_id: int, guide_id: int, payload):
    """Verify an external GRE 09 or 31 using matching signed XML and accepted CDR."""
    from services import smartpse_response
    from services.smartpse_client import SmartPSEException

    guide = db.query(models.GuiaRemision).filter(
        models.GuiaRemision.id == guide_id,
        models.GuiaRemision.tenant_id == tenant_id,
    ).with_for_update().first()
    if not guide or not guide.external_gre_reference:
        raise DispatchError("Guía o referencia GRE externa no encontrada.", status_code=404, code="EXTERNAL_GRE_NOT_FOUND")
    reference = guide.external_gre_reference
    expected_type = "09" if guide.tipo_documento == "31" else "31" if guide.tipo_documento == "09" else None
    if not expected_type or reference.document_type != expected_type:
        raise DispatchError("La referencia GRE externa no corresponde al tipo de guía.", status_code=422, code="INVALID_REFERENCE")

    signed_xml = smartpse_response.extract_xml_from_signed_zip(payload.signed_xml)
    identity = smartpse_response.extract_gre_document_identity(signed_xml)
    expected_number = str(int(reference.number)) if str(reference.number).isdigit() else str(reference.number)
    actual_number = str(int(identity.get("number"))) if str(identity.get("number") or "").isdigit() else str(identity.get("number") or "")
    matches = (
        identity.get("document_type") == reference.document_type
        and str(identity.get("series") or "").upper() == reference.series.upper()
        and actual_number == expected_number
        and identity.get("issuer_ruc") == reference.issuer_ruc
    )
    if not matches:
        raise DispatchError(
            "El XML firmado no coincide con el tipo, emisor o número de la GRE remitente registrada.",
            status_code=422,
            code="EXTERNAL_GRE_IDENTITY_MISMATCH",
        )
    cdr_xml = smartpse_response.extract_cdr_xml({"cdr": payload.cdr})
    if not cdr_xml:
        raise DispatchError("El CDR no es legible.", status_code=422, code="EXTERNAL_GRE_CDR_INVALID")
    try:
        smartpse_response.validate_gre_cdr(cdr_xml, {
            "tipoDoc": reference.document_type, "serie": reference.series, "correlativo": reference.number,
        })
    except SmartPSEException as exc:
        raise DispatchError(str(exc), status_code=422, code="EXTERNAL_GRE_CDR_INVALID") from exc

    verified_at = datetime.now()
    reference.verification_status = "verified"
    reference.source = "admin_evidence_review"
    reference.evidence = {
        "environment": payload.environment,
        "provider_document_name": payload.provider_document_name,
        "signed_xml": signed_xml,
        "cdr": cdr_xml,
        "signed_xml_sha256": hashlib.sha256(signed_xml.encode("utf-8")).hexdigest(),
        "cdr_sha256": hashlib.sha256(cdr_xml.encode("utf-8")).hexdigest(),
        "verified_at": verified_at.isoformat(),
        "verified_by_user_id": user_id,
        "note": payload.note,
    }
    db.add(models.AuditLog(
        user_id=user_id,
        action="guide.external_reference.verified",
        entity_type="guide_external_reference",
        entity_id=reference.id,
        details=json.dumps({
            "tenant_id": tenant_id,
            "guide_id": guide.id,
            "document": f"{reference.series}-{reference.number}",
            "issuer_ruc": reference.issuer_ruc,
            "environment": payload.environment,
            "signed_xml_sha256": reference.evidence["signed_xml_sha256"],
            "cdr_sha256": reference.evidence["cdr_sha256"],
        }, sort_keys=True),
    ))
    guide.version += 1
    db.commit()
    db.refresh(reference)
    return reference


def guide_action_availability(db: Session, guide, current_user) -> dict:
    """Authoritative action hints for the guide detail UI."""
    role = get_effective_role(current_user)
    can_emit_role = role in DOCUMENT_EMITTER_ROLES
    can_admin = role in TENANT_ADMIN_ROLES
    can_manage = can_emit_role and (
        role in {"superadmin", "admin", "operador"} or guide.usuario_id == current_user.id
    )
    tenant_active = bool(getattr(current_user.tenant, "is_active", False)) or current_user.is_superadmin
    subscription = db.query(models.Subscription).filter(
        models.Subscription.tenant_id == guide.tenant_id
    ).first()
    subscription_active = current_user.is_superadmin or (
        subscription is not None and str(subscription.status or "").lower() in {"active", "trial", "grace"}
    )
    dispatch = guide.dispatch or guide.internal_transfer_dispatch

    def state(enabled, code=None, reason=None):
        return {"enabled": bool(enabled), "code": code, "reason": reason}

    draft = guide.estado == "pendiente"
    mutable = draft and can_manage and tenant_active
    validation = validate_guide_for_emission(db, guide) if draft and can_manage else {"valid": False, "errors": []}
    validation_reason = validation["errors"][0]["message"] if validation.get("errors") else None
    emission_ready = mutable and subscription_active and validation["valid"]

    departure_enabled = False
    departure_code = "GRE_09_NOT_ACCEPTED"
    departure_reason = "La GRE remitente debe estar aceptada antes de confirmar la salida."
    if guide.tipo_documento != "09" or not dispatch:
        departure_code, departure_reason = "DISPATCH_NOT_AVAILABLE", "Esta guía no controla una salida física."
    elif dispatch.departure_confirmed_at:
        departure_code, departure_reason = "DEPARTURE_ALREADY_CONFIRMED", "La salida física ya fue confirmada."
    elif guide.estado == "emitida":
        if carrier_guide_required(guide):
            internal = db.query(models.GuiaRemision.id).filter(
                models.GuiaRemision.tenant_id == guide.tenant_id,
                models.GuiaRemision.related_guide_id == guide.id,
                models.GuiaRemision.tipo_documento == "31",
                models.GuiaRemision.estado == "emitida",
            ).first()
            external = guide.external_gre_reference and guide.external_gre_reference.verification_status == "verified"
            if internal or external:
                departure_enabled, departure_code, departure_reason = True, None, None
            else:
                departure_code, departure_reason = "GRE_31_REQUIRED", "Falta una GRE transportista aceptada o verificada."
        else:
            departure_enabled, departure_code, departure_reason = True, None, None

    return {
        "edit": state(mutable and bool(guide.dispatch), "GUIDE_NOT_EDITABLE" if not mutable else None, None if mutable else "El borrador ya no es editable."),
        "cancel": state(mutable and bool(guide.dispatch), "GUIDE_NOT_CANCELLABLE" if not mutable else None, None if mutable else "Cancela el traslado desde su operación de origen."),
        "validate": state(draft and can_manage, "GUIDE_NOT_VALIDATABLE" if not draft else None, None if draft else "La guía ya fue enviada."),
        "emit": state(emission_ready, None if emission_ready else "GUIDE_NOT_READY", None if emission_ready else (validation_reason or "La guía, la suscripción o el tenant no permiten emitir.")),
        "consult": state(guide.estado == "pendiente_smartpse" and can_manage, "GUIDE_NOT_PENDING" if guide.estado != "pendiente_smartpse" else None, None if guide.estado == "pendiente_smartpse" else "La guía no tiene resultado pendiente."),
        "confirm_departure": state(departure_enabled and can_manage and tenant_active and subscription_active, departure_code, departure_reason),
        "register_external_carrier": state(
            guide.tipo_documento == "09" and carrier_guide_required(guide) and guide.estado == "emitida" and not guide.external_gre_reference and can_manage,
            "EXTERNAL_GRE_ALREADY_REGISTERED" if guide.external_gre_reference else None,
            None,
        ),
        "verify_external_reference": state(
            guide.tipo_documento in {"09", "31"} and bool(guide.external_gre_reference) and guide.external_gre_reference.verification_status != "verified" and can_admin,
            "EXTERNAL_GRE_ALREADY_VERIFIED" if guide.external_gre_reference and guide.external_gre_reference.verification_status == "verified" else None,
            None,
        ),
    }


def create_transport_guide(db: Session, tenant_id: int, user_id: int, payload):
    """Create GRE 31 in the carrier tenant from expressly supplied external evidence."""
    tenant = _lock_tenant(db, tenant_id)
    existing = db.query(models.GuiaRemision).filter(
        models.GuiaRemision.tenant_id == tenant_id,
        models.GuiaRemision.creation_idempotency_key == payload.idempotency_key,
    ).first()
    fingerprint = _fingerprint(payload.model_dump(mode="json"))
    if existing:
        stored = (existing.provider_response or {}).get("creation_fingerprint")
        if stored and stored != fingerprint:
            raise DispatchError("La clave de idempotencia ya fue usada con otro contenido.", code="IDEMPOTENCY_CONFLICT")
        return existing, False
    if payload.gre_remitente.document_type != "09" or payload.goods_invoice.document_type not in SUPPORTED_SALES_DOCUMENT_TYPES:
        raise DispatchError("La GRE 31 requiere una GRE remitente 09 y un comprobante de bienes 01 o 03.", status_code=422, code="INVALID_REFERENCES")
    if payload.gre_remitente.issuer_ruc != payload.remitente_nro_doc:
        raise DispatchError("El emisor de la GRE 09 debe coincidir con el remitente declarado.", status_code=422, code="SENDER_MISMATCH")
    gre_reference = _external_reference(db, tenant_id, user_id, payload.gre_remitente, source="carrier_input")
    invoice_reference = _external_reference(db, tenant_id, user_id, payload.goods_invoice, source="carrier_input")
    environment, series = _guide_series(tenant, "31")
    guide = models.GuiaRemision(
        tipo_documento="31",
        serie=series,
        correlativo=_next_guide_number(db, tenant_id, "31", series),
        emission_environment=environment,
        fecha_emision=fiscal_time.now_lima_naive(),
        estado="pendiente",
        tenant_id=tenant_id,
        usuario_id=user_id,
        motivo_traslado="01",
        descripcion_motivo="VENTA",
        external_gre_reference=gre_reference,
        goods_invoice_reference=invoice_reference,
        creation_idempotency_key=payload.idempotency_key,
        remitente_tipo_doc=payload.remitente_tipo_doc,
        remitente_nro_doc=payload.remitente_nro_doc,
        remitente_razon_social=payload.remitente_razon_social,
        destinatario_tipo_doc=payload.destinatario_tipo_doc,
        destinatario_nro_doc=payload.destinatario_nro_doc,
        destinatario_razon_social=payload.destinatario_razon_social,
        pagador_flete_tipo=payload.pagador_flete_tipo,
        pagador_tipo_doc=payload.pagador_tipo_doc,
        pagador_nro_doc=payload.pagador_nro_doc,
        pagador_razon_social=payload.pagador_razon_social,
        provider_response={"creation_fingerprint": fingerprint},
        **_guide_fields(payload),
    )
    # _guide_fields intentionally lets the operator provide MTC/fleet data but
    # the authenticated tenant remains the carrier and fiscal issuer.
    guide.transportista_ruc = tenant.business_ruc
    guide.transportista_razon_social = tenant.business_name
    guide.items = [models.GuiaRemisionItem(
        producto_id=item.producto_id,
        descripcion=item.descripcion,
        cantidad=_qty(item.cantidad),
        unidad_medida=item.unidad_medida,
        codigo_producto=item.codigo_producto,
        peso_item=item.peso_item,
    ) for item in payload.lines]
    db.add(guide)
    db.commit()
    db.refresh(guide)
    return guide, True


def register_external_carrier_guide(db: Session, tenant_id: int, user_id: int, guide_id: int, payload):
    guide = db.query(models.GuiaRemision).filter(
        models.GuiaRemision.id == guide_id,
        models.GuiaRemision.tenant_id == tenant_id,
        models.GuiaRemision.tipo_documento == "09",
    ).with_for_update().first()
    if not guide:
        raise DispatchError("GRE remitente no encontrada.", status_code=404, code="GUIDE_NOT_FOUND")
    if payload.guide.document_type != "31":
        raise DispatchError("La referencia externa del transportista debe ser una GRE 31.", status_code=422, code="INVALID_REFERENCE")
    reference = _external_reference(db, tenant_id, user_id, payload.guide, source="seller_attachment")
    guide.external_gre_reference = reference
    guide.version += 1
    db.commit()
    return guide
