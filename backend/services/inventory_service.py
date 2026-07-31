"""Tenant-scoped commercial inventory operations.

All mutations are short local transactions. Provider calls must happen before
or after these functions, never while balance rows are locked.
"""
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

import models

ZERO = Decimal("0")


def _decimal(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.0001"))


def get_default_warehouse(db: Session, tenant_id: int):
    return db.query(models.Warehouse).filter(
        models.Warehouse.tenant_id == tenant_id,
        models.Warehouse.is_default.is_(True),
        models.Warehouse.is_active.is_(True),
    ).first()


def get_warehouse(db: Session, tenant_id: int, warehouse_id: int, *, active=True):
    query = db.query(models.Warehouse).filter(
        models.Warehouse.id == warehouse_id,
        models.Warehouse.tenant_id == tenant_id,
    )
    if active:
        query = query.filter(models.Warehouse.is_active.is_(True))
    warehouse = query.first()
    if not warehouse:
        raise HTTPException(404, "Almacen no encontrado para la empresa autenticada.")
    return warehouse


def create_warehouse(db: Session, tenant_id: int, data):
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).with_for_update().first()
    if not tenant:
        raise HTTPException(404, "Empresa no encontrada.")
    has_default = get_default_warehouse(db, tenant_id) is not None
    make_default = bool(data.is_default or not has_default)
    if make_default:
        db.query(models.Warehouse).filter(models.Warehouse.tenant_id == tenant_id).update(
            {models.Warehouse.is_default: False}, synchronize_session=False
        )
    warehouse = models.Warehouse(
        tenant_id=tenant_id, code=data.code, name=data.name,
        location=data.location, is_default=make_default,
    )
    db.add(warehouse)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(409, "Ya existe un almacen con ese codigo.")
    db.refresh(warehouse)
    return warehouse


def update_warehouse(db: Session, tenant_id: int, warehouse_id: int, data):
    warehouse = get_warehouse(db, tenant_id, warehouse_id)
    warehouse.name = data.name.strip()
    warehouse.location = data.location.strip() if data.location and data.location.strip() else None
    if data.is_default and not warehouse.is_default:
        db.query(models.Warehouse).filter(
            models.Warehouse.tenant_id == tenant_id,
            models.Warehouse.id != warehouse.id,
        ).update({models.Warehouse.is_default: False}, synchronize_session=False)
        warehouse.is_default = True
    db.commit()
    db.refresh(warehouse)
    return warehouse


def activate_inventory(db: Session, tenant_id: int, data):
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).with_for_update().first()
    if tenant.inventory_enabled:
        warehouse = get_default_warehouse(db, tenant_id)
        if warehouse:
            return warehouse
    warehouse = get_default_warehouse(db, tenant_id)
    if not warehouse:
        warehouse = models.Warehouse(
            tenant_id=tenant_id,
            code=data.warehouse_code.strip().upper(),
            name=data.warehouse_name.strip(),
            is_default=True,
            is_active=True,
        )
        db.add(warehouse)
        db.flush()
    tenant.inventory_enabled = True
    tenant.inventory_started_at = datetime.now()
    db.commit()
    db.refresh(warehouse)
    return warehouse


def _get_product(db, tenant_id, product_id, *, inventory_required=True):
    product = db.query(models.Producto).filter(
        models.Producto.id == product_id,
        models.Producto.tenant_id == tenant_id,
    ).first()
    if not product:
        raise HTTPException(404, "Producto no encontrado para la empresa autenticada.")
    if inventory_required and (not product.inventory_enabled or product.item_type != "inventory"):
        raise HTTPException(409, f"El producto '{product.nombre}' no controla inventario.")
    return product


def _balance(db, tenant_id, warehouse_id, product_id, *, lock=True):
    query = db.query(models.InventoryBalance).filter(
        models.InventoryBalance.tenant_id == tenant_id,
        models.InventoryBalance.warehouse_id == warehouse_id,
        models.InventoryBalance.product_id == product_id,
    )
    if lock:
        query = query.with_for_update()
    balance = query.first()
    if balance:
        return balance
    balance = models.InventoryBalance(
        tenant_id=tenant_id, warehouse_id=warehouse_id, product_id=product_id,
        on_hand=ZERO, committed=ZERO, minimum_stock=ZERO,
    )
    db.add(balance)
    db.flush()
    return balance


def configure_product(db, tenant_id, product_id, data, user_id):
    product = _get_product(db, tenant_id, product_id, inventory_required=False)
    if data.inventory_enabled and data.item_type != "inventory":
        raise HTTPException(422, "Solo un producto inventariable puede controlar stock.")
    if not data.inventory_enabled or data.item_type == "service":
        active_balance = db.query(models.InventoryBalance).filter(
            models.InventoryBalance.tenant_id == tenant_id,
            models.InventoryBalance.product_id == product_id,
            or_(
                models.InventoryBalance.on_hand != ZERO,
                models.InventoryBalance.committed != ZERO,
            ),
        ).first()
        if active_balance:
            raise HTTPException(
                409,
                "Regulariza el stock y las reservas antes de convertir el producto en servicio.",
            )
    product.item_type = data.item_type
    product.inventory_enabled = bool(data.inventory_enabled)
    if product.inventory_enabled:
        warehouse = get_warehouse(
            db, tenant_id, data.warehouse_id or getattr(get_default_warehouse(db, tenant_id), "id", 0)
        )
        balance = _balance(db, tenant_id, warehouse.id, product.id)
        balance.minimum_stock = _decimal(data.minimum_stock)
        if _decimal(data.opening_stock) != ZERO:
            _record_movement(
                db, balance, _decimal(data.opening_stock), "opening", "opening_balance",
                product.id, None, user_id, "Saldo de apertura",
                f"opening:{tenant_id}:{warehouse.id}:{product.id}", allow_negative=False,
            )
    db.commit()
    db.refresh(product)
    return product


def _record_movement(db, balance, quantity, movement_type, source_type, source_id,
                     source_line_id, user_id, reason, idempotency_key, *, allow_negative=False):
    existing = db.query(models.InventoryMovement).filter(
        models.InventoryMovement.tenant_id == balance.tenant_id,
        models.InventoryMovement.idempotency_key == idempotency_key,
    ).first()
    if existing:
        return existing
    quantity = _decimal(quantity)
    before = _decimal(balance.on_hand)
    after = before + quantity
    if after < ZERO and not allow_negative:
        raise HTTPException(409, "Stock insuficiente para completar la operacion.")
    balance.on_hand = after
    movement = models.InventoryMovement(
        tenant_id=balance.tenant_id, warehouse_id=balance.warehouse_id,
        product_id=balance.product_id, movement_type=movement_type,
        quantity=quantity, balance_before=before, balance_after=after,
        source_type=source_type, source_id=source_id, source_line_id=source_line_id,
        user_id=user_id, reason=reason, idempotency_key=idempotency_key,
    )
    db.add(movement)
    db.flush()
    return movement


def adjust_stock(db, tenant_id, data, user_id, *, can_override_negative=False):
    get_warehouse(db, tenant_id, data.warehouse_id)
    _get_product(db, tenant_id, data.product_id)
    quantity = _decimal(data.quantity)
    if quantity == ZERO:
        raise HTTPException(422, "La cantidad del ajuste no puede ser cero.")
    if data.allow_negative and not can_override_negative:
        raise HTTPException(403, "Solo un administrador puede autorizar stock negativo.")
    balance = _balance(db, tenant_id, data.warehouse_id, data.product_id)
    movement = _record_movement(
        db, balance, quantity, data.movement_type, "manual_adjustment", None, None,
        user_id, data.reason, data.idempotency_key or f"adjustment:{tenant_id}:{uuid4()}",
        allow_negative=data.allow_negative and can_override_negative,
    )
    db.commit()
    db.refresh(movement)
    return movement


def transfer_stock(db, tenant_id, data, user_id, *, can_override_negative=False):
    if data.source_warehouse_id == data.destination_warehouse_id:
        raise HTTPException(422, "Los almacenes de origen y destino deben ser distintos.")
    for wid in sorted([data.source_warehouse_id, data.destination_warehouse_id]):
        get_warehouse(db, tenant_id, wid)
    if data.allow_negative and not can_override_negative:
        raise HTTPException(403, "Solo un administrador puede autorizar stock negativo.")
    transfer = models.InventoryTransfer(
        tenant_id=tenant_id, source_warehouse_id=data.source_warehouse_id,
        destination_warehouse_id=data.destination_warehouse_id, reason=data.reason,
        created_by_user_id=user_id, status="completed",
    )
    db.add(transfer)
    db.flush()
    merged = {}
    for item in data.items:
        merged[item.product_id] = merged.get(item.product_id, ZERO) + _decimal(item.quantity)
    for product_id in sorted(merged):
        _get_product(db, tenant_id, product_id)
        quantity = merged[product_id]
        source = _balance(db, tenant_id, data.source_warehouse_id, product_id)
        destination = _balance(db, tenant_id, data.destination_warehouse_id, product_id)
        db.add(models.InventoryTransferItem(transfer_id=transfer.id, product_id=product_id, quantity=quantity))
        _record_movement(db, source, -quantity, "transfer_out", "transfer", transfer.id, None,
                         user_id, data.reason, f"transfer:{transfer.id}:{product_id}:out",
                         allow_negative=data.allow_negative and can_override_negative)
        _record_movement(db, destination, quantity, "transfer_in", "transfer", transfer.id, None,
                         user_id, data.reason, f"transfer:{transfer.id}:{product_id}:in")
    db.commit()
    db.refresh(transfer)
    return transfer


def list_stock(db, tenant_id, *, warehouse_id=None, q=None):
    query = db.query(models.InventoryBalance, models.Producto, models.Warehouse).select_from(
        models.Producto
    ).join(
        models.Warehouse,
        models.Warehouse.tenant_id == models.Producto.tenant_id,
    ).outerjoin(
        models.InventoryBalance,
        and_(
            models.InventoryBalance.tenant_id == tenant_id,
            models.InventoryBalance.product_id == models.Producto.id,
            models.InventoryBalance.warehouse_id == models.Warehouse.id,
        ),
    ).filter(
        models.Producto.tenant_id == tenant_id,
        models.Producto.inventory_enabled.is_(True),
        models.Producto.item_type == "inventory",
        models.Warehouse.tenant_id == tenant_id,
        models.Warehouse.is_active.is_(True),
    )
    if warehouse_id:
        query = query.filter(models.Warehouse.id == warehouse_id)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(or_(models.Producto.nombre.ilike(term), models.Producto.codigo_interno.ilike(term)))
    result = []
    for balance, product, warehouse in query.order_by(models.Producto.nombre, models.Warehouse.name).all():
        on_hand = _decimal(getattr(balance, "on_hand", ZERO))
        committed = _decimal(getattr(balance, "committed", ZERO))
        minimum_stock = _decimal(getattr(balance, "minimum_stock", ZERO))
        available = on_hand - committed
        status = "negative" if available < ZERO else "out" if available == ZERO else "low" if available <= minimum_stock else "ok"
        result.append({
            "product_id": product.id, "product_name": product.nombre,
            "product_code": product.codigo_interno, "warehouse_id": warehouse.id,
            "warehouse_name": warehouse.name, "unit": product.unidad_medida,
            "on_hand": on_hand, "committed": committed,
            "available": available, "minimum_stock": minimum_stock, "status": status,
        })
    return result


def list_stock_page(db, tenant_id, *, warehouse_id=None, q=None, status=None, skip=0, limit=15):
    rows = list_stock(db, tenant_id, warehouse_id=warehouse_id, q=q)
    if status and status != "all":
        expected = "ok" if status == "available" else status
        rows = [row for row in rows if row["status"] == expected]
    total = len(rows)
    return {"items": rows[skip:skip + min(limit, 100)], "total": total, "skip": skip, "limit": limit}


def _movement_filters(query, *, product_id=None, warehouse_id=None, document_id=None,
                      date_from=None, date_to=None, movement_type=None, direction=None):
    if product_id:
        query = query.filter(models.InventoryMovement.product_id == product_id)
    if warehouse_id:
        query = query.filter(models.InventoryMovement.warehouse_id == warehouse_id)
    if document_id:
        query = query.filter(
            models.InventoryMovement.source_id == document_id,
            models.InventoryMovement.source_type.in_({"fiscal_document", "credit_note", "fiscal_void"}),
        )
    if date_from:
        query = query.filter(models.InventoryMovement.created_at >= date_from)
    if date_to:
        query = query.filter(models.InventoryMovement.created_at <= date_to)
    if movement_type:
        query = query.filter(models.InventoryMovement.movement_type == movement_type)
    if direction == "entry":
        query = query.filter(models.InventoryMovement.quantity > ZERO)
    elif direction == "exit":
        query = query.filter(models.InventoryMovement.quantity < ZERO)
    return query


def list_movements(db, tenant_id, *, product_id=None, warehouse_id=None, document_id=None,
                   date_from=None, date_to=None, movement_type=None, direction=None,
                   skip=0, limit=15):
    query = db.query(models.InventoryMovement, models.Producto, models.Warehouse).join(
        models.Producto, models.Producto.id == models.InventoryMovement.product_id
    ).join(models.Warehouse, models.Warehouse.id == models.InventoryMovement.warehouse_id).filter(
        models.InventoryMovement.tenant_id == tenant_id,
        models.Producto.tenant_id == tenant_id,
        models.Warehouse.tenant_id == tenant_id,
    )
    query = _movement_filters(
        query, product_id=product_id, warehouse_id=warehouse_id, document_id=document_id,
        date_from=date_from, date_to=date_to, movement_type=movement_type, direction=direction,
    )
    rows = query.order_by(models.InventoryMovement.created_at.desc(), models.InventoryMovement.id.desc()).offset(skip).limit(min(limit, 100)).all()
    document_ids = {
        movement.source_id
        for movement, _product, _warehouse in rows
        if movement.source_id and movement.source_type in {"fiscal_document", "credit_note", "fiscal_void"}
    }
    documents = {}
    if document_ids:
        documents = {
            document.id: document
            for document in db.query(models.Cotizacion).filter(
                models.Cotizacion.tenant_id == tenant_id,
                models.Cotizacion.id.in_(document_ids),
            ).all()
        }
    return [{
        "id": m.id, "product_id": m.product_id, "product_name": p.nombre,
        "warehouse_id": m.warehouse_id, "warehouse_name": w.name,
        "movement_type": m.movement_type, "quantity": m.quantity,
        "balance_before": m.balance_before, "balance_after": m.balance_after,
        "source_type": m.source_type, "source_id": m.source_id,
        "source_line_id": m.source_line_id, "reason": m.reason, "created_at": m.created_at,
        "source_document_number": getattr(documents.get(m.source_id), "document_number", None),
        "source_document_type": getattr(documents.get(m.source_id), "tipo_comprobante", None),
    } for m, p, w in rows]


def count_movements(db, tenant_id, *, product_id=None, warehouse_id=None, document_id=None,
                    date_from=None, date_to=None, movement_type=None, direction=None):
    query = db.query(models.InventoryMovement).filter(
        models.InventoryMovement.tenant_id == tenant_id,
    )
    return _movement_filters(
        query, product_id=product_id, warehouse_id=warehouse_id, document_id=document_id,
        date_from=date_from, date_to=date_to, movement_type=movement_type, direction=direction,
    ).count()


def bulk_adjust_stock(db, tenant_id, data, user_id):
    warehouse = get_warehouse(db, tenant_id, data.warehouse_id)
    product_ids = [item.product_id for item in data.items]
    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(422, "No repitas productos dentro de una misma carga.")

    keys = [f"bulk:{tenant_id}:{data.idempotency_key}:{product_id}" for product_id in product_ids]
    existing = db.query(models.InventoryMovement).filter(
        models.InventoryMovement.tenant_id == tenant_id,
        models.InventoryMovement.idempotency_key.in_(keys),
    ).all()
    if existing:
        existing_product_ids = {row.product_id for row in existing}
        if not existing_product_ids.issubset(set(product_ids)):
            raise HTTPException(409, "La clave de idempotencia ya pertenece a otra carga.")
        requested_by_product = {item.product_id: _decimal(item.quantity) for item in data.items}
        for movement in existing:
            matches_payload = (
                movement.movement_type == "bulk_entry"
                and data.mode == "add"
                and _decimal(movement.quantity) == requested_by_product[movement.product_id]
            ) or (
                movement.movement_type == "physical_count"
                and data.mode == "set"
                and _decimal(movement.balance_after) == requested_by_product[movement.product_id]
            )
            if not matches_payload:
                raise HTTPException(409, "La clave de idempotencia ya pertenece a otra carga.")
        if data.mode == "add" and len(existing) != len(product_ids):
            raise HTTPException(409, "La carga ya fue procesada parcialmente con otra composicion.")
        skipped_existing = 0
        if data.mode == "set":
            by_product = {item.product_id: item for item in data.items}
            for product_id in set(product_ids) - existing_product_ids:
                balance = _balance(db, tenant_id, warehouse.id, product_id, lock=False)
                if _decimal(balance.on_hand) != _decimal(by_product[product_id].quantity):
                    raise HTTPException(409, "La clave de idempotencia ya pertenece a otra carga.")
                skipped_existing += 1
        return {"movement_ids": [row.id for row in existing], "applied": len(existing), "skipped": skipped_existing}

    by_product = {item.product_id: item for item in data.items}
    movements = []
    skipped = 0
    try:
        for product_id in sorted(product_ids):
            item = by_product[product_id]
            _get_product(db, tenant_id, product_id)
            balance = _balance(db, tenant_id, warehouse.id, product_id)
            requested = _decimal(item.quantity)
            if data.mode == "add":
                if requested <= ZERO:
                    raise HTTPException(422, "Las entradas masivas deben ser mayores que cero.")
                delta = requested
                movement_type = "bulk_entry"
            else:
                if requested < _decimal(balance.committed):
                    raise HTTPException(409, "El conteo final no puede ser menor que el stock comprometido.")
                delta = requested - _decimal(balance.on_hand)
                movement_type = "physical_count"
                if delta == ZERO:
                    skipped += 1
                    continue
            movement = _record_movement(
                db, balance, delta, movement_type, "bulk_adjustment", None, None,
                user_id, data.reason, f"bulk:{tenant_id}:{data.idempotency_key}:{product_id}",
            )
            movements.append(movement)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"movement_ids": [row.id for row in movements], "applied": len(movements), "skipped": skipped}


def check_availability(db, tenant_id, data):
    warehouse = get_warehouse(db, tenant_id, data.warehouse_id or getattr(get_default_warehouse(db, tenant_id), "id", 0))
    result = []
    for item in data.items:
        product = _get_product(db, tenant_id, item.product_id, inventory_required=False)
        if not product.inventory_enabled:
            continue
        balance = _balance(db, tenant_id, warehouse.id, product.id, lock=False)
        available = _decimal(balance.on_hand) - _decimal(balance.committed)
        requested = _decimal(item.quantity)
        result.append({"product_id": product.id, "requested": requested, "available": available, "sufficient": available >= requested})
    return result


def check_document_availability(db: Session, tenant_id: int, document_id: int):
    document = db.query(models.Cotizacion).filter(
        models.Cotizacion.id == document_id,
        models.Cotizacion.tenant_id == tenant_id,
    ).first()
    if not document:
        raise HTTPException(404, "Documento no encontrado para la empresa autenticada.")
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    default_warehouse = get_default_warehouse(db, tenant_id)
    if not tenant or not tenant.inventory_enabled or not default_warehouse:
        return {
            "inventory_enabled": False,
            "warehouse_id": None,
            "warehouse_name": None,
            "sufficient": True,
            "items": [],
        }
    warehouse = get_warehouse(
        db,
        tenant_id,
        document.warehouse_id or default_warehouse.id,
    )
    lines = []
    for item in document.items:
        if not item.producto_id:
            continue
        product = _get_product(db, tenant_id, item.producto_id, inventory_required=False)
        if not product.inventory_enabled or product.item_type != "inventory":
            continue
        balance = db.query(models.InventoryBalance).filter(
            models.InventoryBalance.tenant_id == tenant_id,
            models.InventoryBalance.warehouse_id == warehouse.id,
            models.InventoryBalance.product_id == product.id,
        ).first()
        available = (
            _decimal(balance.on_hand) - _decimal(balance.committed)
            if balance else ZERO
        )
        requested = _decimal(item.cantidad)
        lines.append({
            "product_id": product.id,
            "product_name": product.nombre,
            "unit": product.unidad_medida,
            "requested": requested,
            "available": available,
            "sufficient": available >= requested,
        })
    return {
        "inventory_enabled": True,
        "warehouse_id": warehouse.id,
        "warehouse_name": warehouse.name,
        "sufficient": all(line["sufficient"] for line in lines),
        "items": lines,
    }


def create_document_holds(db, document, user_id, *, allow_negative=False, override_reason=None):
    tenant = db.query(models.Tenant).filter(models.Tenant.id == document.tenant_id).first()
    if not tenant or not tenant.inventory_enabled or not tenant.inventory_started_at:
        return []
    warehouse_id = document.warehouse_id or getattr(get_default_warehouse(db, document.tenant_id), "id", None)
    inventory_items = []
    for item in sorted(document.items, key=lambda value: (value.producto_id or 0, value.id or 0)):
        if not item.producto_id:
            continue
        product = _get_product(db, document.tenant_id, item.producto_id, inventory_required=False)
        if product.inventory_enabled and product.item_type == "inventory":
            if product.unidad_medida != item.unidad_medida:
                raise HTTPException(409, f"La unidad de '{product.nombre}' no coincide con el catalogo.")
            inventory_items.append((item, product))
    if not inventory_items:
        return []
    if not warehouse_id:
        raise HTTPException(409, "Seleccione un almacen antes de emitir.")
    get_warehouse(db, document.tenant_id, warehouse_id)
    created = []
    for item, product in inventory_items:
        existing = db.query(models.InventoryHold).filter(
            models.InventoryHold.tenant_id == document.tenant_id,
            models.InventoryHold.document_id == document.id,
            models.InventoryHold.document_item_id == item.id,
        ).with_for_update().first()
        if existing:
            if existing.status == "released":
                balance = _balance(db, document.tenant_id, warehouse_id, product.id)
                quantity = _decimal(item.cantidad)
                available = _decimal(balance.on_hand) - _decimal(balance.committed)
                if available < quantity and not allow_negative:
                    raise HTTPException(409, f"Stock insuficiente para '{product.nombre}'. Disponible: {available} {product.unidad_medida}.")
                balance.committed = _decimal(balance.committed) + quantity
                existing.quantity = quantity
                existing.status = "active"
                existing.negative_override = allow_negative
                existing.override_reason = override_reason
                existing.created_by_user_id = user_id
                existing.resolved_at = None
            elif existing.status not in {"active", "converted"}:
                raise HTTPException(409, "La reserva de inventario tiene un estado no recuperable.")
            created.append(existing)
            continue
        balance = _balance(db, document.tenant_id, warehouse_id, product.id)
        quantity = _decimal(item.cantidad)
        available = _decimal(balance.on_hand) - _decimal(balance.committed)
        if available < quantity and not allow_negative:
            raise HTTPException(409, f"Stock insuficiente para '{product.nombre}'. Disponible: {available} {product.unidad_medida}.")
        balance.committed = _decimal(balance.committed) + quantity
        hold = models.InventoryHold(
            tenant_id=document.tenant_id, warehouse_id=warehouse_id, product_id=product.id,
            document_id=document.id, document_item_id=item.id, quantity=quantity,
            created_by_user_id=user_id, negative_override=allow_negative,
            override_reason=override_reason, status="active",
        )
        db.add(hold)
        created.append(hold)
    document.warehouse_id = warehouse_id
    db.flush()
    return created


def finalize_document_inventory(db, document):
    holds = db.query(models.InventoryHold).filter(
        models.InventoryHold.tenant_id == document.tenant_id,
        models.InventoryHold.document_id == document.id,
        models.InventoryHold.status == "active",
    ).order_by(models.InventoryHold.product_id, models.InventoryHold.id).with_for_update().all()
    for hold in holds:
        balance = _balance(db, hold.tenant_id, hold.warehouse_id, hold.product_id)
        balance.committed = max(ZERO, _decimal(balance.committed) - _decimal(hold.quantity))
        _record_movement(
            db, balance, -_decimal(hold.quantity), "sale_out", "fiscal_document",
            document.id, hold.document_item_id, document.usuario_id,
            f"Salida por {document.document_number}",
            f"sale:{document.id}:{hold.document_item_id}", allow_negative=hold.negative_override,
        )
        hold.status = "converted"
        hold.resolved_at = datetime.now()
    return holds


def release_document_holds(db, document, *, reason="Emision rechazada"):
    holds = db.query(models.InventoryHold).filter(
        models.InventoryHold.tenant_id == document.tenant_id,
        models.InventoryHold.document_id == document.id,
        models.InventoryHold.status == "active",
    ).order_by(models.InventoryHold.product_id, models.InventoryHold.id).with_for_update().all()
    for hold in holds:
        balance = _balance(db, hold.tenant_id, hold.warehouse_id, hold.product_id)
        balance.committed = max(ZERO, _decimal(balance.committed) - _decimal(hold.quantity))
        hold.status = "released"
        hold.override_reason = hold.override_reason or reason
        hold.resolved_at = datetime.now()
    return holds


def reverse_document_inventory(db: Session, document, *, user_id=None, reason="Documento anulado"):
    """Restore stock previously deducted by an accepted fiscal document.

    Reversals are derived from immutable sale movements rather than from the
    current document lines.  The movement idempotency key makes repeated void
    confirmations harmless.
    """
    sales = db.query(models.InventoryMovement).filter(
        models.InventoryMovement.tenant_id == document.tenant_id,
        models.InventoryMovement.source_type == "fiscal_document",
        models.InventoryMovement.source_id == document.id,
        models.InventoryMovement.movement_type == "sale_out",
    ).order_by(models.InventoryMovement.product_id, models.InventoryMovement.id).with_for_update().all()

    reversals = []
    for sale in sales:
        balance = _balance(db, sale.tenant_id, sale.warehouse_id, sale.product_id)
        reversal = _record_movement(
            db,
            balance,
            abs(_decimal(sale.quantity)),
            "sale_void_reversal",
            "fiscal_void",
            document.id,
            sale.source_line_id,
            user_id,
            reason,
            f"void:{document.id}:{sale.id}",
        )
        reversal.related_movement_id = sale.id
        reversals.append(reversal)
    return reversals


def ensure_document_void_inventory_safe(db: Session, document):
    """Block a void while an inventory-affecting credit note is active.

    Voiding the original sale after stock was already returned by a credit note
    would duplicate the physical entry. Pending notes are also blocked to avoid
    a race between the fiscal workers.
    """
    conflicting_note = db.query(models.Cotizacion.id).filter(
        models.Cotizacion.tenant_id == document.tenant_id,
        models.Cotizacion.nota_referencia_id == document.id,
        models.Cotizacion.document_kind == "credit_note",
        models.Cotizacion.inventory_impact.in_(["undelivered", "physical_return"]),
        models.Cotizacion.estado.in_(["pendiente", "facturada"]),
    ).first()
    if conflicting_note:
        raise ValueError(
            "No se puede anular el comprobante mientras tenga una nota de crédito activa con impacto de inventario."
        )


def apply_credit_note_inventory(db: Session, note):
    if note.inventory_impact not in {"undelivered", "physical_return"}:
        return None
    original = db.query(models.Cotizacion).filter(
        models.Cotizacion.id == note.nota_referencia_id,
        models.Cotizacion.tenant_id == note.tenant_id,
    ).first()
    if not original:
        return None
    warehouse_id = note.inventory_return_warehouse_id or original.warehouse_id
    if not warehouse_id:
        return None
    get_warehouse(db, note.tenant_id, warehouse_id)

    if note.inventory_impact == "physical_return":
        pending = db.query(models.InventoryReturn).filter(
            models.InventoryReturn.tenant_id == note.tenant_id,
            models.InventoryReturn.credit_note_id == note.id,
        ).first()
        if pending:
            return pending
        pending = models.InventoryReturn(
            tenant_id=note.tenant_id, credit_note_id=note.id,
            warehouse_id=warehouse_id, status="pending",
        )
        db.add(pending)
        db.flush()
        for item in note.items:
            if item.producto_id:
                product = _get_product(db, note.tenant_id, item.producto_id, inventory_required=False)
                if product.inventory_enabled:
                    pending.items.append(models.InventoryReturnItem(
                        product_id=product.id, note_item_id=item.id,
                        authorized_quantity=_decimal(item.cantidad), received_quantity=ZERO,
                    ))
        return pending

    for item in sorted(note.items, key=lambda value: (value.producto_id or 0, value.id or 0)):
        if not item.producto_id:
            continue
        product = _get_product(db, note.tenant_id, item.producto_id, inventory_required=False)
        if not product.inventory_enabled:
            continue
        original_line_id = item.inventory_source_item_id
        sale = db.query(models.InventoryMovement).filter(
            models.InventoryMovement.tenant_id == note.tenant_id,
            models.InventoryMovement.source_type == "fiscal_document",
            models.InventoryMovement.source_id == original.id,
            models.InventoryMovement.source_line_id == original_line_id,
            models.InventoryMovement.movement_type == "sale_out",
        ).first()
        if not sale:
            continue
        already_returned = db.query(models.InventoryMovement).filter(
            models.InventoryMovement.tenant_id == note.tenant_id,
            models.InventoryMovement.source_line_id == original_line_id,
            models.InventoryMovement.movement_type.in_(["credit_undelivered", "return_received"]),
        ).all()
        returned_qty = sum((_decimal(row.quantity) for row in already_returned), ZERO)
        quantity = _decimal(item.cantidad)
        if returned_qty + quantity > abs(_decimal(sale.quantity)):
            raise HTTPException(409, "La nota excede la cantidad descontada originalmente.")
        balance = _balance(db, note.tenant_id, warehouse_id, product.id)
        _record_movement(
            db, balance, quantity, "credit_undelivered", "credit_note", note.id,
            original_line_id, note.usuario_id, f"Cantidad no entregada - {note.document_number}",
            f"credit-stock:{note.id}:{item.id}",
        )
    return None


def receive_return(db: Session, tenant_id: int, return_id: int, data, user_id: int):
    stock_return = db.query(models.InventoryReturn).filter(
        models.InventoryReturn.id == return_id,
        models.InventoryReturn.tenant_id == tenant_id,
    ).with_for_update().first()
    if not stock_return:
        raise HTTPException(404, "Devolucion no encontrada.")
    if stock_return.status == "received":
        return stock_return
    items = {item.id: item for item in stock_return.items}
    for line in data.items:
        item = items.get(line.return_item_id)
        if not item:
            raise HTTPException(404, "Linea de devolucion no encontrada.")
        quantity = _decimal(line.quantity)
        remaining = _decimal(item.authorized_quantity) - _decimal(item.received_quantity)
        if quantity > remaining:
            raise HTTPException(409, "La recepcion excede la cantidad autorizada.")
        balance = _balance(db, tenant_id, stock_return.warehouse_id, item.product_id)
        _record_movement(
            db, balance, quantity, "return_received", "inventory_return", stock_return.id,
            item.note_item_id, user_id, data.reason,
            f"return:{stock_return.id}:{item.id}:{_decimal(item.received_quantity) + quantity}",
        )
        item.received_quantity = _decimal(item.received_quantity) + quantity
    complete = all(_decimal(item.received_quantity) >= _decimal(item.authorized_quantity) for item in stock_return.items)
    stock_return.status = "received" if complete else "partial"
    stock_return.received_at = datetime.now() if complete else None
    stock_return.received_by_user_id = user_id
    db.commit()
    db.refresh(stock_return)
    return stock_return
