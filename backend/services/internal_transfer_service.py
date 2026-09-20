"""National transfers between establishments with optional GRE 09 support."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import hashlib
import json

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

import models
from services import beta_feature_flags, inventory_service
from services.guide_series_service import guide_series, next_guide_correlativo


ZERO = Decimal("0.0000")
ACTIVE_ALLOCATION_STATES = {"active", "covered", "departed", "received"}
OPEN_DISPATCH_STATES = {"reserved", "guide_draft", "guide_pending", "guide_accepted"}


class InternalTransferError(ValueError):
    def __init__(self, message: str, *, code: str = "INTERNAL_TRANSFER_ERROR", status_code: int = 409, context=None):
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.context = context


def _decimal(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.0001"))


def _fingerprint(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _lock_tenant(db: Session, tenant_id: int):
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).with_for_update().first()
    if not tenant or not tenant.is_active:
        raise InternalTransferError("La empresa no está activa.", code="TENANT_INACTIVE", status_code=403)
    return tenant


def _get_establishment(db: Session, tenant_id: int, establishment_id: int, *, active=True, lock=False):
    query = db.query(models.TenantEstablishment).filter(
        models.TenantEstablishment.id == establishment_id,
        models.TenantEstablishment.tenant_id == tenant_id,
    )
    if active:
        query = query.filter(models.TenantEstablishment.is_active.is_(True))
    if lock:
        query = query.with_for_update()
    row = query.first()
    if not row:
        raise InternalTransferError(
            "Establecimiento no encontrado para la empresa autenticada.",
            code="ESTABLISHMENT_NOT_FOUND",
            status_code=404,
        )
    return row


def list_establishments(db: Session, tenant_id: int, *, include_inactive=False):
    query = db.query(models.TenantEstablishment).filter(models.TenantEstablishment.tenant_id == tenant_id)
    if not include_inactive:
        query = query.filter(models.TenantEstablishment.is_active.is_(True))
    return query.order_by(models.TenantEstablishment.is_main.desc(), models.TenantEstablishment.name).all()


def create_establishment(db: Session, tenant_id: int, user_id: int, data):
    _lock_tenant(db, tenant_id)
    if data.is_main:
        db.query(models.TenantEstablishment).filter(
            models.TenantEstablishment.tenant_id == tenant_id
        ).update({models.TenantEstablishment.is_main: False}, synchronize_session=False)
    row = models.TenantEstablishment(
        tenant_id=tenant_id,
        sunat_code=data.sunat_code,
        name=data.name,
        ubigeo=data.ubigeo,
        address=data.address,
        is_main=data.is_main,
    )
    db.add(row)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise InternalTransferError(
            "Ya existe un establecimiento con ese código SUNAT.",
            code="ESTABLISHMENT_CODE_CONFLICT",
        ) from exc
    db.refresh(row)
    return row


def update_establishment(db: Session, tenant_id: int, establishment_id: int, data):
    _lock_tenant(db, tenant_id)
    row = _get_establishment(db, tenant_id, establishment_id, active=False, lock=True)
    identity_changed = any(
        getattr(row, field) != getattr(data, field)
        for field in ("sunat_code", "ubigeo", "address")
    )
    if data.is_main:
        db.query(models.TenantEstablishment).filter(
            models.TenantEstablishment.tenant_id == tenant_id,
            models.TenantEstablishment.id != row.id,
        ).update({models.TenantEstablishment.is_main: False}, synchronize_session=False)
    for field in ("sunat_code", "name", "ubigeo", "address", "is_main", "is_active"):
        setattr(row, field, getattr(data, field))
    if identity_changed:
        row.verified_at = None
        row.verified_by_user_id = None
        row.verification_note = None
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise InternalTransferError(
            "El código SUNAT ya está registrado en otro establecimiento.",
            code="ESTABLISHMENT_CODE_CONFLICT",
        ) from exc
    db.refresh(row)
    return row


def verify_establishment(db: Session, tenant_id: int, establishment_id: int, user_id: int, data):
    _lock_tenant(db, tenant_id)
    row = _get_establishment(db, tenant_id, establishment_id, lock=True)
    row.verified_at = datetime.now()
    row.verified_by_user_id = user_id
    row.verification_note = data.note.strip()
    db.commit()
    db.refresh(row)
    return row


def _warehouse_for_establishment(db, tenant_id, warehouse_id, establishment_id):
    if warehouse_id is None:
        return None
    warehouse = inventory_service.get_warehouse(db, tenant_id, warehouse_id)
    if warehouse.establishment_id != establishment_id:
        raise InternalTransferError(
            "El almacén no está vinculado al establecimiento seleccionado.",
            code="WAREHOUSE_ESTABLISHMENT_MISMATCH",
            status_code=422,
        )
    return warehouse


def _resolve_lines(db: Session, tenant_id: int, lines):
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    inventory_enabled = bool(tenant and tenant.inventory_enabled)
    resolved = []
    seen_products = set()
    for item in lines:
        product = None
        if item.product_id is not None:
            if item.product_id in seen_products:
                raise InternalTransferError(
                    "Un producto del catálogo no puede repetirse en la misma transferencia.",
                    code="DUPLICATE_PRODUCT_LINE",
                    status_code=422,
                )
            seen_products.add(item.product_id)
            product = inventory_service._get_product(db, tenant_id, item.product_id, inventory_required=False)
            if getattr(product, "item_type", None) == "service":
                raise InternalTransferError(
                    f"'{product.nombre}' está configurado como servicio y no puede trasladarse.",
                    code="SERVICE_NOT_ALLOWED",
                    status_code=422,
                )
        controlled = bool(
            inventory_enabled
            and product
            and product.inventory_enabled
            and product.item_type == "inventory"
        )
        resolved.append({
            "product": product,
            "product_id": getattr(product, "id", None),
            "description": getattr(product, "nombre", None) or item.description.strip(),
            "product_code": getattr(product, "codigo_interno", None) or item.product_code,
            "unit_code": getattr(product, "unidad_medida", None) or item.unit_code,
            "quantity": _decimal(item.quantity),
            "inventory_controlled": controlled,
        })
    return resolved


def _validate_route(db, tenant_id, data, resolved_lines):
    source = _get_establishment(db, tenant_id, data.source_establishment_id)
    destination = _get_establishment(db, tenant_id, data.destination_establishment_id)
    source_warehouse = _warehouse_for_establishment(
        db, tenant_id, data.source_warehouse_id, source.id
    )
    destination_warehouse = _warehouse_for_establishment(
        db, tenant_id, data.destination_warehouse_id, destination.id
    )
    if source.id == destination.id:
        if not source_warehouse or not destination_warehouse or source_warehouse.id == destination_warehouse.id:
            raise InternalTransferError(
                "Dentro del mismo establecimiento selecciona dos almacenes distintos.",
                code="SAME_LOCATION",
                status_code=422,
            )
    if any(line["inventory_controlled"] for line in resolved_lines):
        if not source_warehouse or not destination_warehouse:
            raise InternalTransferError(
                "Los bienes con control de stock requieren almacenes de origen y destino.",
                code="WAREHOUSES_REQUIRED",
                status_code=422,
            )
    return source, destination, source_warehouse, destination_warehouse


def create_transfer(db: Session, tenant_id: int, user_id: int, data):
    _lock_tenant(db, tenant_id)
    request_data = data.model_dump(mode="json")
    fingerprint = _fingerprint(request_data)
    existing = db.query(models.InternalTransferOrder).filter(
        models.InternalTransferOrder.tenant_id == tenant_id,
        models.InternalTransferOrder.idempotency_key == data.idempotency_key,
    ).first()
    if existing:
        if existing.request_fingerprint != fingerprint:
            raise InternalTransferError(
                "La clave de idempotencia ya fue usada con otro contenido.",
                code="IDEMPOTENCY_CONFLICT",
            )
        return get_transfer(db, tenant_id, existing.id), False
    resolved = _resolve_lines(db, tenant_id, data.lines)
    source, destination, source_warehouse, destination_warehouse = _validate_route(
        db, tenant_id, data, resolved
    )
    transfer = models.InternalTransferOrder(
        tenant_id=tenant_id,
        source_establishment_id=source.id,
        destination_establishment_id=destination.id,
        source_warehouse_id=getattr(source_warehouse, "id", None),
        destination_warehouse_id=getattr(destination_warehouse, "id", None),
        reason=data.reason.strip(),
        status="draft",
        idempotency_key=data.idempotency_key,
        request_fingerprint=fingerprint,
        created_by_user_id=user_id,
    )
    db.add(transfer)
    db.flush()
    for line in resolved:
        transfer.lines.append(models.InternalTransferOrderLine(
            tenant_id=tenant_id,
            product_id=line["product_id"],
            description=line["description"],
            product_code=line["product_code"],
            unit_code=line["unit_code"],
            quantity=line["quantity"],
            inventory_controlled=line["inventory_controlled"],
        ))
    db.commit()
    return get_transfer(db, tenant_id, transfer.id), True


def get_transfer(db: Session, tenant_id: int, transfer_id: int, *, lock=False):
    filters = (
        models.InternalTransferOrder.id == transfer_id,
        models.InternalTransferOrder.tenant_id == tenant_id,
    )
    if lock:
        locked = db.query(models.InternalTransferOrder.id).filter(*filters).with_for_update().scalar()
        if locked is None:
            return None
    return db.query(models.InternalTransferOrder).options(
        joinedload(models.InternalTransferOrder.source_establishment),
        joinedload(models.InternalTransferOrder.destination_establishment),
        joinedload(models.InternalTransferOrder.source_warehouse),
        joinedload(models.InternalTransferOrder.destination_warehouse),
        joinedload(models.InternalTransferOrder.lines).joinedload(models.InternalTransferOrderLine.product),
        joinedload(models.InternalTransferOrder.dispatches)
            .joinedload(models.InternalTransferDispatch.lines)
            .joinedload(models.InternalTransferDispatchLine.transfer_line),
        joinedload(models.InternalTransferOrder.dispatches)
            .joinedload(models.InternalTransferDispatch.guides),
        joinedload(models.InternalTransferOrder.dispatches)
            .joinedload(models.InternalTransferDispatch.receipts),
    ).filter(*filters).first()


def list_transfers(db: Session, tenant_id: int, *, skip=0, limit=15):
    query = db.query(models.InternalTransferOrder).filter(models.InternalTransferOrder.tenant_id == tenant_id)
    total = query.with_entities(func.count(models.InternalTransferOrder.id)).scalar() or 0
    rows = query.order_by(models.InternalTransferOrder.created_at.desc(), models.InternalTransferOrder.id.desc()).offset(skip).limit(limit).all()
    return {"items": [transfer_context(db, tenant_id, row.id) for row in rows], "total": total, "skip": skip, "limit": limit}


def update_transfer(db: Session, tenant_id: int, transfer_id: int, data):
    _lock_tenant(db, tenant_id)
    transfer = get_transfer(db, tenant_id, transfer_id, lock=True)
    if not transfer:
        raise InternalTransferError("Traslado no encontrado.", code="TRANSFER_NOT_FOUND", status_code=404)
    if transfer.version != data.version:
        raise InternalTransferError(
            "El traslado cambió en otra sesión.",
            code="VERSION_CONFLICT",
            context=transfer_context(db, tenant_id, transfer.id),
        )
    if transfer.dispatches:
        raise InternalTransferError(
            "Las cantidades y la ruta ya no pueden editarse porque existe un despacho en el historial.",
            code="TRANSFER_IMMUTABLE",
        )
    resolved = _resolve_lines(db, tenant_id, data.lines)
    source, destination, source_warehouse, destination_warehouse = _validate_route(db, tenant_id, data, resolved)
    transfer.lines.clear()
    db.flush()
    transfer.source_establishment_id = source.id
    transfer.destination_establishment_id = destination.id
    transfer.source_warehouse_id = getattr(source_warehouse, "id", None)
    transfer.destination_warehouse_id = getattr(destination_warehouse, "id", None)
    transfer.reason = data.reason.strip()
    transfer.version += 1
    transfer.request_fingerprint = _fingerprint(data.model_dump(mode="json"))
    for line in resolved:
        transfer.lines.append(models.InternalTransferOrderLine(
            tenant_id=tenant_id,
            product_id=line["product_id"],
            description=line["description"],
            product_code=line["product_code"],
            unit_code=line["unit_code"],
            quantity=line["quantity"],
            inventory_controlled=line["inventory_controlled"],
        ))
    db.commit()
    return get_transfer(db, tenant_id, transfer.id)


def _allocated_quantity(line) -> Decimal:
    return sum(
        (_decimal(dispatch_line.quantity) for dispatch_line in line.dispatch_lines
         if dispatch_line.reservation_status in ACTIVE_ALLOCATION_STATES),
        ZERO,
    )


def create_dispatch(db: Session, tenant_id: int, transfer_id: int, user_id: int, data):
    _lock_tenant(db, tenant_id)
    fingerprint = _fingerprint(data.model_dump(mode="json"))
    existing = db.query(models.InternalTransferDispatch).filter(
        models.InternalTransferDispatch.tenant_id == tenant_id,
        models.InternalTransferDispatch.idempotency_key == data.idempotency_key,
    ).first()
    if existing:
        if existing.request_fingerprint != fingerprint:
            raise InternalTransferError("La clave de idempotencia ya fue usada con otro contenido.", code="IDEMPOTENCY_CONFLICT")
        return existing, False
    transfer = get_transfer(db, tenant_id, transfer_id, lock=True)
    if not transfer:
        raise InternalTransferError("Traslado no encontrado.", code="TRANSFER_NOT_FOUND", status_code=404)
    if transfer.status in {"cancelled", "completed"}:
        raise InternalTransferError("El traslado ya no admite nuevos despachos.", code="TRANSFER_CLOSED")
    line_ids = sorted(item.transfer_line_id for item in data.lines)
    locked_lines = db.query(models.InternalTransferOrderLine).filter(
        models.InternalTransferOrderLine.tenant_id == tenant_id,
        models.InternalTransferOrderLine.transfer_id == transfer.id,
        models.InternalTransferOrderLine.id.in_(line_ids),
    ).order_by(models.InternalTransferOrderLine.id).with_for_update().all()
    by_id = {line.id: line for line in locked_lines}
    if set(by_id) != set(line_ids):
        raise InternalTransferError("Una línea no pertenece al traslado.", code="TRANSFER_LINE_NOT_FOUND", status_code=404)
    dispatch = models.InternalTransferDispatch(
        tenant_id=tenant_id,
        transfer_id=transfer.id,
        status="reserved",
        idempotency_key=data.idempotency_key,
        request_fingerprint=fingerprint,
        created_by_user_id=user_id,
    )
    db.add(dispatch)
    db.flush()
    now = datetime.now()
    requested = {item.transfer_line_id: _decimal(item.quantity) for item in data.lines}
    for line_id in line_ids:
        line = by_id[line_id]
        remaining = (
            _decimal(line.quantity)
            - _decimal(line.cancelled_quantity)
            - _allocated_quantity(line)
        )
        quantity = requested[line_id]
        if quantity > remaining:
            raise InternalTransferError(
                f"La cantidad de '{line.description}' excede el saldo pendiente.",
                code="TRANSFER_QUANTITY_EXCEEDED",
                context={"line_id": line.id, "requested": str(quantity), "available": str(remaining)},
            )
        if line.inventory_controlled:
            balance = inventory_service._balance(db, tenant_id, transfer.source_warehouse_id, line.product_id)
            available = _decimal(balance.on_hand) - _decimal(balance.committed)
            if quantity > available:
                raise InternalTransferError(
                    f"Stock insuficiente para '{line.description}'.",
                    code="INSUFFICIENT_STOCK",
                    context={"line_id": line.id, "requested": str(quantity), "available": str(available)},
                )
            balance.committed = _decimal(balance.committed) + quantity
        dispatch.lines.append(models.InternalTransferDispatchLine(
            tenant_id=tenant_id,
            transfer_line_id=line.id,
            quantity=quantity,
            reservation_status="active",
            reserved_at=now,
        ))
    transfer.status = "pending"
    transfer.version += 1
    db.commit()
    db.refresh(dispatch)
    return dispatch, True


def _guide_fields(data):
    return {
        "fecha_traslado": data.fecha_traslado,
        "peso_bruto_total": data.peso_bruto_total,
        "unidad_medida_peso": data.unidad_medida_peso,
        "numero_bultos": data.numero_bultos,
        "modalidad_traslado": data.modalidad_traslado,
        "fecha_entrega_transportista": data.fecha_entrega_transportista,
        "indicador_m1_l": data.indicador_m1_l,
        "registrar_vehiculo_transportista": data.registrar_vehiculo_transportista,
        "observaciones": data.observaciones,
        "transportista_ruc": data.transportista_ruc,
        "transportista_razon_social": data.transportista_razon_social,
        "transportista_nro_mtc": data.transportista_nro_mtc,
        "conductor_tipo_doc": data.conductor_tipo_doc,
        "conductor_nro_doc": data.conductor_nro_doc,
        "conductor_nombres": data.conductor_nombres,
        "conductor_apellidos": data.conductor_apellidos,
        "conductor_licencia": data.conductor_licencia,
        "vehiculo_placa": data.vehiculo_placa,
        "vehiculo_nro_circulacion": data.vehiculo_nro_circulacion,
        "vehiculo_cod_emisor": data.vehiculo_cod_emisor,
        "vehiculo_nro_autorizacion": data.vehiculo_nro_autorizacion,
    }


def create_guide(db: Session, tenant_id: int, user_id: int, data):
    tenant = _lock_tenant(db, tenant_id)
    fingerprint = _fingerprint(data.model_dump(mode="json"))
    existing = db.query(models.GuiaRemision).filter(
        models.GuiaRemision.tenant_id == tenant_id,
        models.GuiaRemision.creation_idempotency_key == data.idempotency_key,
    ).first()
    if existing:
        stored = (existing.provider_response or {}).get("creation_fingerprint")
        if stored and stored != fingerprint:
            raise InternalTransferError(
                "La clave de idempotencia ya fue usada con otro contenido.",
                code="IDEMPOTENCY_CONFLICT",
            )
        if existing.internal_transfer_dispatch_id != data.dispatch_id:
            raise InternalTransferError("La clave de idempotencia ya fue usada para otra guía.", code="IDEMPOTENCY_CONFLICT")
        return existing, False
    dispatch = db.query(models.InternalTransferDispatch).filter(
        models.InternalTransferDispatch.id == data.dispatch_id,
        models.InternalTransferDispatch.tenant_id == tenant_id,
    ).with_for_update().first()
    if not dispatch:
        raise InternalTransferError("Despacho interno no encontrado.", code="DISPATCH_NOT_FOUND", status_code=404)
    transfer = get_transfer(db, tenant_id, dispatch.transfer_id, lock=True)
    if transfer.source_establishment_id == transfer.destination_establishment_id:
        raise InternalTransferError(
            "Este movimiento ocurre dentro del mismo establecimiento y no requiere GRE.",
            code="GRE_NOT_REQUIRED",
            status_code=422,
        )
    if dispatch.status != "reserved" or any(line.reservation_status != "active" for line in dispatch.lines):
        raise InternalTransferError("El despacho no tiene reservas activas para crear la GRE.", code="RESERVATION_REQUIRED")
    if any(guide.estado not in {"rechazada", "cancelled"} for guide in dispatch.guides):
        raise InternalTransferError("El despacho ya tiene una GRE vigente.", code="GUIDE_ALREADY_EXISTS")
    source = transfer.source_establishment
    destination = transfer.destination_establishment
    if not source.verified_at or not destination.verified_at:
        raise InternalTransferError(
            "Verifica los establecimientos de partida y llegada antes de crear la GRE.",
            code="ESTABLISHMENT_VERIFICATION_REQUIRED",
            status_code=422,
        )
    environment, series = guide_series(tenant, "09")
    guide = models.GuiaRemision(
        tipo_documento="09",
        serie=series,
        correlativo=next_guide_correlativo(db, tenant_id, "09", series),
        emission_environment=environment,
        fecha_emision=datetime.now(),
        estado="pendiente",
        tenant_id=tenant_id,
        usuario_id=user_id,
        internal_transfer_dispatch=dispatch,
        internal_order_number=f"TI-{transfer.id}",
        creation_idempotency_key=data.idempotency_key,
        provider_response={"creation_fingerprint": fingerprint},
        motivo_traslado="04",
        descripcion_motivo="TRASLADO ENTRE ESTABLECIMIENTOS DE LA MISMA EMPRESA",
        destinatario_tipo_doc="6",
        destinatario_nro_doc=tenant.business_ruc,
        destinatario_razon_social=tenant.business_name,
        partida_ubigeo=source.ubigeo,
        partida_direccion=source.address,
        partida_codigo_local=source.sunat_code,
        llegada_ubigeo=destination.ubigeo,
        llegada_direccion=destination.address,
        llegada_codigo_local=destination.sunat_code,
        **_guide_fields(data),
    )
    if data.transportista_acuerdo_confirmado:
        guide.transportista_acuerdo_confirmado_at = datetime.now()
        guide.transportista_acuerdo_confirmado_by_user_id = user_id
    db.add(guide)
    db.flush()
    for dispatch_line in dispatch.lines:
        line = dispatch_line.transfer_line
        guide.items.append(models.GuiaRemisionItem(
            producto_id=line.product_id,
            internal_transfer_dispatch_line_id=dispatch_line.id,
            descripcion=line.description,
            cantidad=dispatch_line.quantity,
            unidad_medida=line.unit_code,
            codigo_producto=line.product_code,
        ))
    dispatch.status = "guide_draft"
    dispatch.version += 1
    db.commit()
    db.refresh(guide)
    return guide, True


def validate_guide_for_emission(db: Session, guide) -> list[dict]:
    errors = []
    dispatch = guide.internal_transfer_dispatch
    if not dispatch:
        return [{"field": "internal_transfer_dispatch_id", "code": "DISPATCH_REQUIRED", "message": "La GRE interna requiere un despacho."}]
    transfer = dispatch.transfer
    tenant = db.query(models.Tenant).filter(models.Tenant.id == guide.tenant_id).first()
    if not beta_feature_flags.is_feature_enabled_for_tenant(tenant, beta_feature_flags.FISCAL_FEATURE_INTERNAL_TRANSFERS):
        errors.append({"field": "feature", "code": "INTERNAL_TRANSFERS_DISABLED", "message": "Los traslados internos no están habilitados para esta empresa."})
    if guide.fiscal_document_id or guide.dispatch_id:
        errors.append({"field": "origin", "code": "INVALID_INTERNAL_ORIGIN", "message": "El traslado interno no puede depender de una factura o despacho de venta."})
    if transfer.status == "cancelled" or dispatch.status in {"cancelled", "guide_rejected"}:
        errors.append({"field": "dispatch", "code": "DISPATCH_CLOSED", "message": "El despacho interno está cerrado."})
    if transfer.source_establishment_id == transfer.destination_establishment_id:
        errors.append({"field": "route", "code": "GRE_NOT_REQUIRED", "message": "El movimiento dentro del mismo establecimiento no requiere GRE."})
    for side, establishment, code, ubigeo, address in (
        ("partida", transfer.source_establishment, guide.partida_codigo_local, guide.partida_ubigeo, guide.partida_direccion),
        ("llegada", transfer.destination_establishment, guide.llegada_codigo_local, guide.llegada_ubigeo, guide.llegada_direccion),
    ):
        if not establishment.is_active or not establishment.verified_at:
            errors.append({"field": side, "code": "ESTABLISHMENT_NOT_VERIFIED", "message": f"El establecimiento de {side} debe estar activo y verificado."})
        if (code, ubigeo, address) != (establishment.sunat_code, establishment.ubigeo, establishment.address):
            errors.append({"field": side, "code": "ESTABLISHMENT_CHANGED", "message": f"Los datos de {side} cambiaron; crea un nuevo borrador."})
    if any(line.reservation_status not in {"active", "covered"} for line in dispatch.lines):
        errors.append({"field": "lines", "code": "RESERVATION_REQUIRED", "message": "Todas las cantidades deben conservar una reserva válida."})
    item_quantities = {item.internal_transfer_dispatch_line_id: _decimal(item.cantidad) for item in guide.items}
    expected = {line.id: _decimal(line.quantity) for line in dispatch.lines}
    if item_quantities != expected:
        errors.append({"field": "items", "code": "GUIDE_LINES_MISMATCH", "message": "Los bienes de la GRE no coinciden con el despacho reservado."})
    return errors


def mark_guide_pending(db: Session, guide):
    dispatch = guide.internal_transfer_dispatch
    if dispatch:
        dispatch.status = "guide_pending"
        dispatch.version += 1


def lock_guide_result_scope(db: Session, guide):
    _lock_tenant(db, guide.tenant_id)
    if guide.internal_transfer_dispatch_id:
        db.query(models.InternalTransferDispatch.id).filter(
            models.InternalTransferDispatch.id == guide.internal_transfer_dispatch_id,
            models.InternalTransferDispatch.tenant_id == guide.tenant_id,
        ).with_for_update().scalar()


def apply_guide_result(db: Session, guide, *, accepted: bool, rejected: bool = False):
    dispatch = guide.internal_transfer_dispatch
    if not dispatch:
        return
    now = datetime.now()
    if accepted:
        for line in dispatch.lines:
            if line.reservation_status == "active":
                line.reservation_status = "covered"
                line.covered_at = now
        dispatch.status = "guide_accepted"
    elif rejected:
        transfer = dispatch.transfer
        for line in sorted(dispatch.lines, key=lambda row: row.transfer_line.product_id or 0):
            if line.reservation_status != "active":
                continue
            if line.transfer_line.inventory_controlled:
                balance = inventory_service._balance(
                    db, guide.tenant_id, transfer.source_warehouse_id, line.transfer_line.product_id
                )
                balance.committed = max(ZERO, _decimal(balance.committed) - _decimal(line.quantity))
            line.reservation_status = "released"
            line.released_at = now
        dispatch.status = "guide_rejected"
        guide.rejected_at = now
    dispatch.version += 1
    _refresh_transfer_status(dispatch.transfer)


def _refresh_transfer_status(transfer):
    lines = [line for dispatch in transfer.dispatches for line in dispatch.lines]
    total_requested = sum(
        (_decimal(line.quantity) - _decimal(line.cancelled_quantity) for line in transfer.lines),
        ZERO,
    )
    total_departed = sum((_decimal(line.departed_quantity) for line in lines), ZERO)
    total_received = sum((_decimal(line.received_quantity) for line in lines), ZERO)
    active_allocated = sum((_decimal(line.quantity) for line in lines if line.reservation_status in ACTIVE_ALLOCATION_STATES), ZERO)
    if total_requested and total_received >= total_requested:
        transfer.status = "completed"
    elif total_received:
        transfer.status = "partially_received"
    elif total_departed:
        transfer.status = "in_transit"
    elif active_allocated:
        transfer.status = "pending"
    elif total_requested:
        transfer.status = "draft"
    else:
        transfer.status = "cancelled"
    transfer.version += 1


def confirm_departure(db: Session, tenant_id: int, dispatch_id: int, user_id: int, idempotency_key: str):
    _lock_tenant(db, tenant_id)
    key_owner = db.query(models.InternalTransferDispatch.id).filter(
        models.InternalTransferDispatch.tenant_id == tenant_id,
        models.InternalTransferDispatch.departure_idempotency_key == idempotency_key,
    ).scalar()
    if key_owner is not None and key_owner != dispatch_id:
        raise InternalTransferError(
            "La clave de idempotencia ya fue usada para confirmar otra salida.",
            code="IDEMPOTENCY_CONFLICT",
        )
    dispatch = db.query(models.InternalTransferDispatch).filter(
        models.InternalTransferDispatch.id == dispatch_id,
        models.InternalTransferDispatch.tenant_id == tenant_id,
    ).with_for_update().first()
    if not dispatch:
        raise InternalTransferError("Despacho no encontrado.", code="DISPATCH_NOT_FOUND", status_code=404)
    if dispatch.departure_confirmed_at:
        if dispatch.departure_idempotency_key and dispatch.departure_idempotency_key != idempotency_key:
            raise InternalTransferError(
                "La salida ya fue confirmada con otra clave de idempotencia.",
                code="IDEMPOTENCY_CONFLICT",
            )
        return dispatch
    transfer = get_transfer(db, tenant_id, dispatch.transfer_id, lock=True)
    requires_gre = transfer.source_establishment_id != transfer.destination_establishment_id
    guide = next((row for row in dispatch.guides if row.tipo_documento == "09" and row.estado == "emitida"), None)
    if requires_gre and not guide:
        raise InternalTransferError("La GRE remitente debe estar aceptada antes de confirmar la salida.", code="GRE_09_NOT_ACCEPTED")
    if guide:
        from services import sale_dispatch_service
        if sale_dispatch_service.carrier_guide_required(guide):
            internal = db.query(models.GuiaRemision.id).filter(
                models.GuiaRemision.tenant_id == tenant_id,
                models.GuiaRemision.related_guide_id == guide.id,
                models.GuiaRemision.tipo_documento == "31",
                models.GuiaRemision.estado == "emitida",
            ).first()
            external = guide.external_gre_reference and guide.external_gre_reference.verification_status == "verified"
            if not internal and not external:
                raise InternalTransferError("Falta una GRE transportista aceptada o verificada.", code="GRE_31_REQUIRED")
    for line in sorted(dispatch.lines, key=lambda row: row.transfer_line.product_id or 0):
        quantity = _decimal(line.quantity)
        if line.transfer_line.inventory_controlled:
            balance = inventory_service._balance(db, tenant_id, transfer.source_warehouse_id, line.transfer_line.product_id)
            balance.committed = max(ZERO, _decimal(balance.committed) - quantity)
            movement = inventory_service._record_movement(
                db, balance, -quantity, "transfer_out", "internal_transfer_dispatch",
                dispatch.id, line.id, user_id, transfer.reason,
                f"internal-transfer:{dispatch.id}:{line.id}:out",
            )
            line.source_movement_id = movement.id
        line.departed_quantity = quantity
        line.reservation_status = "departed"
    dispatch.departure_idempotency_key = idempotency_key
    dispatch.departure_confirmed_at = datetime.now()
    dispatch.departure_confirmed_by_user_id = user_id
    dispatch.status = "departed"
    dispatch.version += 1
    _refresh_transfer_status(transfer)
    db.commit()
    return dispatch


def receive_dispatch(db: Session, tenant_id: int, dispatch_id: int, user_id: int, data):
    _lock_tenant(db, tenant_id)
    fingerprint = _fingerprint(data.model_dump(mode="json"))
    existing = db.query(models.InternalTransferReceipt).filter(
        models.InternalTransferReceipt.tenant_id == tenant_id,
        models.InternalTransferReceipt.idempotency_key == data.idempotency_key,
    ).first()
    if existing:
        if existing.request_fingerprint != fingerprint:
            raise InternalTransferError("La clave de idempotencia ya fue usada con otro contenido.", code="IDEMPOTENCY_CONFLICT")
        return existing, False
    dispatch = db.query(models.InternalTransferDispatch).filter(
        models.InternalTransferDispatch.id == dispatch_id,
        models.InternalTransferDispatch.tenant_id == tenant_id,
    ).with_for_update().first()
    if not dispatch:
        raise InternalTransferError("Despacho no encontrado.", code="DISPATCH_NOT_FOUND", status_code=404)
    if not dispatch.departure_confirmed_at:
        raise InternalTransferError("Confirma la salida antes de registrar la recepción.", code="DEPARTURE_REQUIRED")
    transfer = get_transfer(db, tenant_id, dispatch.transfer_id, lock=True)
    requested_ids = sorted(line.dispatch_line_id for line in data.lines)
    locked_lines = db.query(models.InternalTransferDispatchLine).filter(
        models.InternalTransferDispatchLine.tenant_id == tenant_id,
        models.InternalTransferDispatchLine.dispatch_id == dispatch.id,
        models.InternalTransferDispatchLine.id.in_(requested_ids),
    ).order_by(models.InternalTransferDispatchLine.id).with_for_update().all()
    by_id = {line.id: line for line in locked_lines}
    if set(by_id) != set(requested_ids):
        raise InternalTransferError("Una línea no pertenece al despacho.", code="DISPATCH_LINE_NOT_FOUND", status_code=404)
    receipt = models.InternalTransferReceipt(
        tenant_id=tenant_id,
        dispatch_id=dispatch.id,
        idempotency_key=data.idempotency_key,
        request_fingerprint=fingerprint,
        note=data.note,
        received_by_user_id=user_id,
    )
    db.add(receipt)
    db.flush()
    quantities = {line.dispatch_line_id: _decimal(line.quantity) for line in data.lines}
    for line_id in requested_ids:
        dispatch_line = by_id[line_id]
        quantity = quantities[line_id]
        pending = _decimal(dispatch_line.departed_quantity) - _decimal(dispatch_line.received_quantity)
        if quantity > pending:
            raise InternalTransferError(
                "La recepción supera la cantidad enviada pendiente.",
                code="RECEIPT_QUANTITY_EXCEEDED",
                context={"line_id": line_id, "requested": str(quantity), "available": str(pending)},
            )
        movement = None
        if dispatch_line.transfer_line.inventory_controlled:
            balance = inventory_service._balance(
                db, tenant_id, transfer.destination_warehouse_id, dispatch_line.transfer_line.product_id
            )
            movement = inventory_service._record_movement(
                db, balance, quantity, "transfer_in", "internal_transfer_receipt",
                receipt.id, dispatch_line.id, user_id, data.note or transfer.reason,
                f"internal-transfer:{dispatch.id}:{receipt.id}:{dispatch_line.id}:in",
            )
        receipt.lines.append(models.InternalTransferReceiptLine(
            dispatch_line_id=dispatch_line.id,
            quantity=quantity,
            destination_movement_id=getattr(movement, "id", None),
        ))
        dispatch_line.received_quantity = _decimal(dispatch_line.received_quantity) + quantity
        if dispatch_line.received_quantity >= dispatch_line.departed_quantity:
            dispatch_line.reservation_status = "received"
    if all(_decimal(line.received_quantity) >= _decimal(line.departed_quantity) for line in dispatch.lines):
        dispatch.status = "received"
    else:
        dispatch.status = "partially_received"
    dispatch.version += 1
    _refresh_transfer_status(transfer)
    db.commit()
    db.refresh(receipt)
    return receipt, True


def cancel_transfer(db: Session, tenant_id: int, transfer_id: int):
    _lock_tenant(db, tenant_id)
    transfer = get_transfer(db, tenant_id, transfer_id, lock=True)
    if not transfer:
        raise InternalTransferError("Traslado no encontrado.", code="TRANSFER_NOT_FOUND", status_code=404)
    if transfer.status == "cancelled":
        return transfer
    blocking_states = {"guide_pending", "guide_accepted", "departed", "partially_received", "received"}
    now = datetime.now()
    for dispatch in transfer.dispatches:
        if dispatch.status in blocking_states:
            continue
        for line in dispatch.lines:
            if line.reservation_status == "active":
                if line.transfer_line.inventory_controlled:
                    balance = inventory_service._balance(db, tenant_id, transfer.source_warehouse_id, line.transfer_line.product_id)
                    balance.committed = max(ZERO, _decimal(balance.committed) - _decimal(line.quantity))
                line.reservation_status = "released"
                line.released_at = now
        for guide in dispatch.guides:
            if guide.estado == "pendiente":
                guide.estado = "cancelled"
        dispatch.status = "cancelled"
        dispatch.cancelled_at = now
    for line in transfer.lines:
        line.cancelled_quantity = max(
            ZERO,
            _decimal(line.quantity) - _allocated_quantity(line),
        )
    transfer.cancelled_at = now
    _refresh_transfer_status(transfer)
    db.commit()
    return get_transfer(db, tenant_id, transfer.id)


def transfer_context(db: Session, tenant_id: int, transfer_id: int):
    transfer = get_transfer(db, tenant_id, transfer_id)
    if not transfer:
        raise InternalTransferError("Traslado no encontrado.", code="TRANSFER_NOT_FOUND", status_code=404)
    line_rows = []
    for line in transfer.lines:
        assigned = _allocated_quantity(line)
        departed = sum((_decimal(row.departed_quantity) for row in line.dispatch_lines), ZERO)
        received = sum((_decimal(row.received_quantity) for row in line.dispatch_lines), ZERO)
        available_stock = None
        if line.inventory_controlled and transfer.source_warehouse_id:
            balance = inventory_service._balance(db, tenant_id, transfer.source_warehouse_id, line.product_id, lock=False)
            available_stock = _decimal(balance.on_hand) - _decimal(balance.committed)
        line_rows.append({
            "id": line.id,
            "product_id": line.product_id,
            "description": line.description,
            "product_code": line.product_code,
            "unit_code": line.unit_code,
            "quantity": line.quantity,
            "cancelled": _decimal(line.cancelled_quantity),
            "inventory_controlled": line.inventory_controlled,
            "assigned": assigned,
            "departed": departed,
            "received": received,
            "pending_assignment": max(
                ZERO,
                _decimal(line.quantity) - _decimal(line.cancelled_quantity) - assigned,
            ),
            "in_transit": max(ZERO, departed - received),
            "available_stock": available_stock,
        })
    return {
        "id": transfer.id,
        "status": transfer.status,
        "version": transfer.version,
        "reason": transfer.reason,
        "requires_gre": transfer.source_establishment_id != transfer.destination_establishment_id,
        "source_establishment": _establishment_payload(transfer.source_establishment),
        "destination_establishment": _establishment_payload(transfer.destination_establishment),
        "source_warehouse": _warehouse_payload(transfer.source_warehouse),
        "destination_warehouse": _warehouse_payload(transfer.destination_warehouse),
        "lines": line_rows,
        "dispatches": [_dispatch_payload(dispatch) for dispatch in sorted(transfer.dispatches, key=lambda row: row.id)],
        "created_at": transfer.created_at,
    }


def _establishment_payload(row):
    return {
        "id": row.id,
        "sunat_code": row.sunat_code,
        "name": row.name,
        "ubigeo": row.ubigeo,
        "address": row.address,
        "is_main": row.is_main,
        "is_active": row.is_active,
        "verified_at": row.verified_at,
    }


def _warehouse_payload(row):
    if not row:
        return None
    return {"id": row.id, "code": row.code, "name": row.name, "establishment_id": row.establishment_id}


def _dispatch_payload(dispatch):
    guide = next((row for row in sorted(dispatch.guides, key=lambda item: item.id, reverse=True) if row.tipo_documento == "09"), None)
    return {
        "id": dispatch.id,
        "status": dispatch.status,
        "version": dispatch.version,
        "departure_confirmed_at": dispatch.departure_confirmed_at,
        "guide": ({
            "id": guide.id,
            "number": f"{guide.serie}-{str(guide.correlativo).zfill(6)}",
            "status": guide.estado,
        } if guide else None),
        "lines": [{
            "id": line.id,
            "transfer_line_id": line.transfer_line_id,
            "quantity": line.quantity,
            "reservation_status": line.reservation_status,
            "departed_quantity": line.departed_quantity,
            "received_quantity": line.received_quantity,
        } for line in dispatch.lines],
    }
