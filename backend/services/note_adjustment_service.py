from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

import models
from crud._cotizaciones_shared import _next_note_correlativo, _resolve_note_series
from schemas.notes import FiscalNoteDraftCreate
from services import calculations
from services.document_flow_service import (
    DOCUMENT_KIND_CREDIT_NOTE,
    DOCUMENT_KIND_DEBIT_NOTE,
    DOCUMENT_KIND_FISCAL_DOCUMENT,
    DOCUMENT_STATUS_ISSUED,
    DOCUMENT_STATUS_PENDING,
    get_document_kind_for_note,
    resolve_source_quote_id,
)
from services.fiscal_balance_service import get_fiscal_document_balance

MONEY = Decimal("0.01")
ZERO = Decimal("0.00")

CREDIT_MOTIVES = {
    "01": "Anulacion de la operacion",
    "02": "Anulacion por error en el RUC",
    "03": "Correccion por error en la descripcion",
    "04": "Descuento global",
    "05": "Descuento por item",
    "06": "Devolucion total",
    "07": "Devolucion por item",
    "08": "Bonificacion",
    "09": "Disminucion en el valor",
    "10": "Otros conceptos",
    "11": "Ajustes de operaciones de exportacion",
    "12": "Ajustes afectos al IVAP",
    "13": "Correccion del monto neto pendiente y/o cuotas",
}
DEBIT_MOTIVES = {
    "01": "Intereses por mora",
    "02": "Aumento en el valor",
    "03": "Otros conceptos",
    "13": "Penalidades (inafectas)",
}


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(MONEY, rounding=ROUND_HALF_UP)


def _source_document(db: Session, tenant_id: int, document_id: int, *, lock=False):
    query = db.query(models.Cotizacion)
    if not lock:
        query = query.options(
            joinedload(models.Cotizacion.items),
            joinedload(models.Cotizacion.cliente),
        )
    query = query.filter(
            models.Cotizacion.id == document_id,
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.document_kind == DOCUMENT_KIND_FISCAL_DOCUMENT,
            models.Cotizacion.estado == DOCUMENT_STATUS_ISSUED,
            models.Cotizacion.tipo_comprobante.in_(("01", "03")),
        )
    if lock:
        query = query.with_for_update()
    document = query.first()
    if not document:
        raise ValueError("Comprobante aceptado no encontrado para la empresa.")
    return document


def allowed_motives(document) -> dict[str, dict[str, str]]:
    credit = dict(CREDIT_MOTIVES)
    if document.tipo_comprobante == "03":
        for code in ("04", "05", "08"):
            credit.pop(code, None)
    # Inkora aun no persiste la operacion de exportacion/IVAP en este contrato.
    credit.pop("11", None)
    credit.pop("12", None)
    return {"credito": credit, "debito": dict(DEBIT_MOTIVES)}


def _reserved_credit(db: Session, tenant_id: int, document_id: int, exclude_id=None) -> Decimal:
    filters = [
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.nota_referencia_id == document_id,
        models.Cotizacion.document_kind == DOCUMENT_KIND_CREDIT_NOTE,
        models.Cotizacion.estado == DOCUMENT_STATUS_PENDING,
        models.Cotizacion.nota_ajuste_metadata.isnot(None),
        models.Cotizacion.correlativo.isnot(None),
        models.Cotizacion.sunat_error.is_(None),
    ]
    if exclude_id is not None:
        filters.append(models.Cotizacion.id != exclude_id)
    value = db.query(func.sum(models.Cotizacion.total_venta)).filter(*filters).scalar()
    return _money(value)


def _returned_quantity(db: Session, tenant_id: int, source_item_id: int, exclude_id=None):
    filters = [
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == DOCUMENT_KIND_CREDIT_NOTE,
        models.Cotizacion.estado == DOCUMENT_STATUS_ISSUED,
        models.CotizacionItem.inventory_source_item_id == source_item_id,
        models.Cotizacion.inventory_impact.in_(("undelivered", "physical_return")),
    ]
    if exclude_id:
        filters.append(models.Cotizacion.id != exclude_id)
    value = (
        db.query(func.sum(models.CotizacionItem.cantidad))
        .join(models.Cotizacion, models.Cotizacion.id == models.CotizacionItem.cotizacion_id)
        .filter(*filters)
        .scalar()
    )
    return Decimal(str(value or 0))


def get_note_context(db: Session, tenant_id: int, document_id: int):
    document = _source_document(db, tenant_id, document_id)
    balance = get_fiscal_document_balance(db, tenant_id, document_id)
    reserved = _reserved_credit(db, tenant_id, document_id)
    available = max(balance.credit_note_available_amount - reserved, ZERO)
    return {
        "document": {
            "id": document.id,
            "number": document.document_number,
            "tipo_comprobante": document.tipo_comprobante,
            "moneda": document.moneda,
            "fecha_emision": document.fecha_emision,
            "cliente": {
                "id": document.cliente_id,
                "nombre": getattr(document.cliente, "razon_social", None)
                or getattr(document.cliente, "nombre", None),
                "documento": getattr(document.cliente, "numero_documento", None),
            },
            "total": _money(document.total_venta),
        },
        "lines": [
            {
                "id": item.id,
                "producto_id": item.producto_id,
                "codigo": item.codigo_producto,
                "descripcion": item.descripcion,
                "cantidad": item.cantidad,
                "precio_unitario": item.precio_unitario,
                "tipo_afectacion_igv": item.tipo_afectacion_igv,
                "total": item.total_item,
                "cantidad_devolvible": max(
                    Decimal(str(item.cantidad or 0))
                    - _returned_quantity(db, tenant_id, item.id),
                    Decimal("0"),
                ),
            }
            for item in document.items
        ],
        "balance": {
            "original": balance.document_total,
            "creditos_aceptados": balance.credit_notes_total,
            "debitos_aceptados": balance.debit_notes_total,
            "ajustes_reservados": reserved,
            "maximo_disponible": available,
            "saldo_fiscal": balance.net_total,
            "pagos": balance.payments_total,
            "saldo_por_cobrar": balance.saldo_pendiente,
        },
        "allowed_motives": allowed_motives(document),
        "warehouses": [
            {"id": warehouse.id, "name": warehouse.name, "is_default": warehouse.is_default}
            for warehouse in db.query(models.Warehouse).filter(
                models.Warehouse.tenant_id == tenant_id,
                models.Warehouse.is_active.is_(True),
            ).order_by(models.Warehouse.is_default.desc(), models.Warehouse.name.asc()).all()
        ],
    }


def _db_line(source, *, quantity, unit_price, description=None, tax_affectation=None):
    tax = tax_affectation or source.tipo_afectacion_igv or "10"
    calc = calculations.calcular_item(quantity, unit_price, tax)
    line = models.CotizacionItem(
        producto_id=source.producto_id,
        inventory_source_item_id=source.id,
        codigo_producto=source.codigo_producto,
        descripcion=description or source.descripcion,
        cantidad=calc["cantidad"],
        precio_unitario=calc["precio_unitario"],
        valor_unitario=calc["valor_unitario"],
        total_base_igv=calc["total_base_igv"],
        total_igv=calc["total_igv"],
        total_item=calc["total_item"],
        unidad_medida=source.unidad_medida or "NIU",
        tipo_afectacion_igv=tax,
    )
    return line, calc


def _allocate(document, target: Decimal):
    total = _money(document.total_venta)
    if target <= ZERO or target > total:
        raise ValueError("El ajuste debe ser mayor que cero y no exceder el total original.")
    remaining = target
    allocations = []
    source_lines = list(document.items)
    for index, source in enumerate(source_lines):
        if index == len(source_lines) - 1:
            line_total = remaining
        else:
            line_total = _money(target * _money(source.total_item) / total)
            remaining -= line_total
        qty = Decimal(str(source.cantidad or 0))
        allocations.append((source, qty, line_total / qty))
    return allocations


def calculate_adjustment(db: Session, tenant_id: int, payload: FiscalNoteDraftCreate, *, exclude_note_id=None):
    document = _source_document(db, tenant_id, payload.comprobante_afectado_id)
    motives = allowed_motives(document)[payload.tipo_nota]
    if payload.cod_motivo not in motives:
        raise ValueError("El motivo SUNAT no aplica al comprobante seleccionado.")

    selected = {line.source_item_id: line for line in payload.lines if line.source_item_id}
    sources = {item.id: item for item in document.items}
    built = []
    calculations_list = []

    def append(source, qty, price, description=None, tax=None):
        line, calc = _db_line(
            source, quantity=qty, unit_price=price,
            description=description, tax_affectation=tax,
        )
        built.append(line)
        calculations_list.append(calc)

    if payload.tipo_nota == "credito" and payload.cod_motivo in {"01", "02", "06"}:
        for source in document.items:
            append(source, source.cantidad, source.precio_unitario)
    elif payload.tipo_nota == "credito" and payload.cod_motivo == "03":
        if not selected:
            raise ValueError("Indique al menos una descripcion corregida.")
        changed = False
        for source in document.items:
            description = selected.get(source.id).description if source.id in selected else source.descripcion
            changed = changed or description != source.descripcion
            append(source, source.cantidad, source.precio_unitario, description=description)
        if not changed:
            raise ValueError("La descripcion corregida debe ser distinta a la original.")
    elif payload.tipo_nota == "credito" and payload.cod_motivo in {"04", "09", "10", "13"}:
        if payload.cod_motivo == "13":
            if not payload.payment_terms or payload.payment_terms.get("pending_amount") is None:
                raise ValueError("Registre el nuevo monto pendiente y las cuotas corregidas.")
            current_pending = get_fiscal_document_balance(db, tenant_id, document.id).net_total
            new_pending = _money(payload.payment_terms.get("pending_amount"))
            target = _money(current_pending - new_pending)
        elif payload.input_type == "percentage":
            target = _money(document.total_venta * Decimal(str(payload.input_value or 0)) / 100)
        else:
            target = _money(payload.input_value)
        for source, qty, price in _allocate(document, target):
            append(source, qty, price)
    elif payload.tipo_nota == "credito" and payload.cod_motivo in {"05", "07", "08"}:
        if not selected:
            raise ValueError("Seleccione al menos una linea del comprobante.")
        for source_id, request_line in selected.items():
            source = sources.get(source_id)
            if not source:
                raise ValueError("Una linea seleccionada no pertenece al comprobante.")
            if payload.cod_motivo == "07":
                qty = Decimal(str(request_line.quantity or 0))
                max_qty = Decimal(str(source.cantidad or 0))
                if payload.inventory_impact != "none":
                    max_qty -= _returned_quantity(db, tenant_id, source.id, exclude_note_id)
                if qty <= 0 or qty > max_qty:
                    raise ValueError(f"La cantidad de {source.descripcion} excede el maximo devolvible.")
                append(source, qty, source.precio_unitario)
            elif payload.cod_motivo == "08":
                append(source, source.cantidad, source.precio_unitario)
            else:
                if request_line.percentage is not None:
                    price = Decimal(str(source.precio_unitario)) * request_line.percentage / 100
                elif request_line.amount is not None:
                    price = Decimal(str(request_line.amount)) / Decimal(str(source.cantidad))
                else:
                    raise ValueError("Ingrese monto o porcentaje para cada linea seleccionada.")
                append(source, source.cantidad, price)
    else:
        # Debitos: concepto explicito. El codigo 13 es siempre inafecto.
        target = _money(payload.input_value)
        if target <= ZERO:
            raise ValueError("Ingrese el importe del debito.")
        source = list(document.items)[0]
        tax = "30" if payload.cod_motivo == "13" else (payload.lines[0].tax_affectation if payload.lines else source.tipo_afectacion_igv)
        append(source, Decimal("1"), target, description=payload.descripcion_motivo, tax=tax)

    totals = calculations.sumarizar_cotizacion(calculations_list)
    if totals["total_venta"] <= ZERO:
        raise ValueError("El ajuste calculado debe ser mayor que cero.")
    if payload.tipo_nota == "credito":
        balance = get_fiscal_document_balance(db, tenant_id, document.id)
        available = max(
            balance.credit_note_available_amount
            - _reserved_credit(db, tenant_id, document.id, exclude_note_id), ZERO,
        )
        if totals["total_venta"] > available:
            raise ValueError(f"La nota excede el maximo fiscal disponible ({available}).")
    return document, built, totals


def _apply_draft(note, document, payload, items, totals, user_id, idempotency_key=None):
    note.serie = None
    note.correlativo = None
    note.fecha_emision = datetime.now()
    note.cliente_id = document.cliente_id
    note.usuario_id = user_id
    note.tenant_id = document.tenant_id
    note.moneda = document.moneda
    note.tipo_comprobante = "07" if payload.tipo_nota == "credito" else "08"
    note.estado = "borrador"
    note.document_kind = get_document_kind_for_note(payload.tipo_nota)
    note.source_quote_id = resolve_source_quote_id(document)
    note.nota_referencia_id = document.id
    note.nota_motivo_codigo = payload.cod_motivo
    note.nota_motivo_descripcion = payload.descripcion_motivo
    note.nota_ajuste_metadata = jsonable_encoder({
        "version": 2,
        "adjustment_mode": payload.adjustment_mode,
        "input_type": payload.input_type,
        "input_value": payload.input_value,
        "lines": [line.model_dump() for line in payload.lines],
        "payment_terms": payload.payment_terms,
    })
    if idempotency_key:
        note.nota_idempotency_key = idempotency_key
    note.inventory_impact = payload.inventory_impact
    note.inventory_return_warehouse_id = payload.inventory_return_warehouse_id
    note.warehouse_id = document.warehouse_id
    note.total_gravada = totals["total_gravada"]
    note.total_exonerada = totals["total_exonerada"]
    note.total_inafecta = totals["total_inafecta"]
    note.total_igv = totals["total_igv"]
    note.total_venta = totals["total_venta"]
    note.items = items
    return note


def create_draft(db, tenant_id, user_id, payload, idempotency_key):
    if not idempotency_key or len(idempotency_key) > 120:
        raise ValueError("Idempotency-Key es obligatorio y debe tener hasta 120 caracteres.")
    existing = db.query(models.Cotizacion).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.nota_idempotency_key == idempotency_key,
    ).first()
    if existing:
        return existing, False
    document, items, totals = calculate_adjustment(db, tenant_id, payload)
    note = _apply_draft(models.Cotizacion(), document, payload, items, totals, user_id, idempotency_key)
    db.add(note)
    # El default historico "COT" se aplica al INSERT incluso con None. Los
    # borradores fiscales no deben aparentar haber consumido serie/correlativo.
    db.flush()
    note.serie = None
    note.correlativo = None
    db.commit()
    db.refresh(note)
    return note, True


def update_draft(db, tenant_id, user_id, note_id, payload):
    note = db.query(models.Cotizacion).filter(
        models.Cotizacion.id == note_id,
        models.Cotizacion.tenant_id == tenant_id,
    ).with_for_update().first()
    if not note or note.estado != "borrador" or note.nota_ajuste_metadata is None:
        raise ValueError("Solo se pueden editar borradores de la empresa.")
    document, items, totals = calculate_adjustment(db, tenant_id, payload, exclude_note_id=note.id)
    _apply_draft(note, document, payload, items, totals, user_id)
    db.commit()
    db.refresh(note)
    return note


def delete_draft(db, tenant_id, note_id):
    note = db.query(models.Cotizacion).filter(
        models.Cotizacion.id == note_id,
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.estado == "borrador",
        models.Cotizacion.nota_ajuste_metadata.isnot(None),
    ).first()
    if not note:
        raise ValueError("Borrador no encontrado para la empresa.")
    db.delete(note)
    db.commit()


def assign_number_for_emission(db, tenant_id, note_id):
    note_probe = db.query(models.Cotizacion).filter(
        models.Cotizacion.id == note_id,
        models.Cotizacion.tenant_id == tenant_id,
    ).first()
    if not note_probe or note_probe.nota_ajuste_metadata is None:
        raise ValueError("Nota v2 no encontrada para la empresa.")
    # Mismo orden de locks que el worker: comprobante origen y luego nota.
    source = _source_document(db, tenant_id, note_probe.nota_referencia_id, lock=True)
    note = db.query(models.Cotizacion).filter(
        models.Cotizacion.id == note_id,
        models.Cotizacion.tenant_id == tenant_id,
    ).with_for_update().first()
    if note.estado != "borrador":
        return note, False
    if note.document_kind == DOCUMENT_KIND_CREDIT_NOTE:
        available = max(
            get_fiscal_document_balance(db, tenant_id, source.id).credit_note_available_amount
            - _reserved_credit(db, tenant_id, source.id, note.id), ZERO,
        )
        if _money(note.total_venta) > available:
            raise ValueError(f"La nota excede el maximo fiscal disponible ({available}).")
    note.serie = _resolve_note_series(source.serie)
    note.correlativo = _next_note_correlativo(db, tenant_id, note.serie)
    note.fecha_emision = datetime.now()
    note.estado = DOCUMENT_STATUS_PENDING
    note.sunat_error = None
    db.commit()
    db.refresh(note)
    return note, True


def serialize_note(db, note):
    active_job = db.query(models.DocumentEmissionJob).filter(
        models.DocumentEmissionJob.tenant_id == note.tenant_id,
        models.DocumentEmissionJob.resource_type == models.EMISSION_JOB_RESOURCE_COTIZACION,
        models.DocumentEmissionJob.resource_id == note.id,
        models.DocumentEmissionJob.action == models.EMISSION_JOB_ACTION_EMIT_NOTE,
    ).order_by(models.DocumentEmissionJob.id.desc()).first()
    return {
        "id": note.id,
        "number": note.document_number,
        "estado": note.estado,
        "tipo_nota": "credito" if note.tipo_comprobante == "07" else "debito",
        "cod_motivo": note.nota_motivo_codigo,
        "descripcion_motivo": note.nota_motivo_descripcion,
        "comprobante_afectado_id": note.nota_referencia_id,
        "total_gravada": note.total_gravada,
        "total_exonerada": note.total_exonerada,
        "total_inafecta": note.total_inafecta,
        "total_igv": note.total_igv,
        "total_venta": note.total_venta,
        "adjustment": note.nota_ajuste_metadata or {"version": 1, "mode": "legacy_full_clone"},
        "inventory_impact": note.inventory_impact or "none",
        "inventory_return_warehouse_id": note.inventory_return_warehouse_id,
        "cdr_disponible": note.has_sunat_cdr,
        "xml_disponible": note.has_sunat_xml,
        "replacement_id": note.nota_reemplazo_id,
        "job": ({"id": active_job.id, "status": active_job.status, "error": active_job.last_error} if active_job else None),
    }
