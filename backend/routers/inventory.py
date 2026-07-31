from typing import List, Optional
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

import models
from access_control import ELEVATED_TENANT_ROLES, ROLE_ADMIN, ROLE_SUPERADMIN, assert_user_has_roles, get_effective_role
from api_dependencies import get_current_user, get_db_tenant, require_admin
from api_utils import read_validated_upload
from schemas.inventory import (
    AvailabilityLine, AvailabilityRequest, InventoryActivation,
    BulkInventoryAdjustmentCreate, BulkInventoryAdjustmentResponse,
    InventoryAdjustmentCreate, MovementPageResponse, MovementResponse, ProductInventoryConfig,
    StockPageResponse, StockResponse, TransferCreate, WarehouseCreate, WarehouseResponse, WarehouseUpdate,
    ReturnReceiptCreate,
)
from services import inventory_service
from services.import_service import parse_inventory_stock

router = APIRouter(prefix="/inventario", tags=["Inventario"])


def _operator(user: models.User = Depends(get_current_user)):
    return assert_user_has_roles(
        user, ELEVATED_TENANT_ROLES,
        detail="Solo administradores y operadores pueden modificar inventario.",
    )


@router.get("/almacenes", response_model=List[WarehouseResponse])
def warehouses(db: Session = Depends(get_db_tenant), user: models.User = Depends(get_current_user)):
    return db.query(models.Warehouse).filter(
        models.Warehouse.tenant_id == user.tenant_id,
        models.Warehouse.is_active.is_(True),
    ).order_by(models.Warehouse.is_default.desc(), models.Warehouse.name).all()


@router.post("/almacenes", response_model=WarehouseResponse, status_code=201)
def add_warehouse(data: WarehouseCreate, db: Session = Depends(get_db_tenant), user: models.User = Depends(require_admin)):
    return inventory_service.create_warehouse(db, user.tenant_id, data)


@router.patch("/almacenes/{warehouse_id}", response_model=WarehouseResponse)
def edit_warehouse(warehouse_id: int, data: WarehouseUpdate,
                   db: Session = Depends(get_db_tenant), user: models.User = Depends(require_admin)):
    return inventory_service.update_warehouse(db, user.tenant_id, warehouse_id, data)


@router.post("/activar", response_model=WarehouseResponse)
def activate(data: InventoryActivation, db: Session = Depends(get_db_tenant), user: models.User = Depends(require_admin)):
    return inventory_service.activate_inventory(db, user.tenant_id, data)


@router.put("/productos/{product_id}")
def configure_product(product_id: int, data: ProductInventoryConfig, db: Session = Depends(get_db_tenant), user: models.User = Depends(require_admin)):
    return inventory_service.configure_product(db, user.tenant_id, product_id, data, user.id)


@router.get("/existencias", response_model=List[StockResponse])
def stock(warehouse_id: Optional[int] = None, q: Optional[str] = None,
          db: Session = Depends(get_db_tenant), user: models.User = Depends(get_current_user)):
    return inventory_service.list_stock(db, user.tenant_id, warehouse_id=warehouse_id, q=q)


@router.get("/existencias/page", response_model=StockPageResponse)
def stock_page(warehouse_id: Optional[int] = None, q: Optional[str] = Query(default=None, max_length=80),
               status: Optional[str] = Query(default="all", pattern="^(all|available|out|low|negative)$"),
               skip: int = Query(0, ge=0), limit: int = Query(15, ge=1, le=100),
               db: Session = Depends(get_db_tenant), user: models.User = Depends(get_current_user)):
    return inventory_service.list_stock_page(
        db, user.tenant_id, warehouse_id=warehouse_id, q=q, status=status, skip=skip, limit=limit,
    )


@router.get("/alertas")
def alerts(db: Session = Depends(get_db_tenant), user: models.User = Depends(get_current_user)):
    rows = inventory_service.list_stock(db, user.tenant_id)
    stale_since = datetime.now() - timedelta(hours=24)
    stale_holds = db.query(models.InventoryHold).filter(
        models.InventoryHold.tenant_id == user.tenant_id,
        models.InventoryHold.status == "active",
        models.InventoryHold.created_at < stale_since,
    ).count()
    return {
        "low_stock": [row for row in rows if row["status"] == "low"],
        "out_of_stock": [row for row in rows if row["status"] == "out"],
        "negative_stock": [row for row in rows if row["status"] == "negative"],
        "stale_emission_holds": stale_holds,
    }


@router.get("/kardex", response_model=List[MovementResponse])
def kardex(product_id: Optional[int] = None, warehouse_id: Optional[int] = None,
           document_id: Optional[int] = None, desde: Optional[date] = None, hasta: Optional[date] = None,
           movement_type: Optional[str] = None,
           direction: Optional[str] = Query(default=None, pattern="^(entry|exit)$"),
           skip: int = Query(0, ge=0), limit: int = Query(15, ge=1, le=100),
           db: Session = Depends(get_db_tenant), user: models.User = Depends(get_current_user)):
    return inventory_service.list_movements(
        db, user.tenant_id, product_id=product_id,
        warehouse_id=warehouse_id, document_id=document_id,
        date_from=datetime.combine(desde, time.min) if desde else None,
        date_to=datetime.combine(hasta, time.max) if hasta else None,
        movement_type=movement_type, direction=direction, skip=skip, limit=limit,
    )


@router.get("/kardex/page", response_model=MovementPageResponse)
def kardex_page(product_id: Optional[int] = None, warehouse_id: Optional[int] = None,
                document_id: Optional[int] = None, desde: Optional[date] = None, hasta: Optional[date] = None,
                movement_type: Optional[str] = None,
                direction: Optional[str] = Query(default=None, pattern="^(entry|exit)$"),
                skip: int = Query(0, ge=0), limit: int = Query(15, ge=1, le=100),
                db: Session = Depends(get_db_tenant), user: models.User = Depends(get_current_user)):
    return {
        "items": inventory_service.list_movements(
            db, user.tenant_id, product_id=product_id,
            warehouse_id=warehouse_id, document_id=document_id,
            date_from=datetime.combine(desde, time.min) if desde else None,
            date_to=datetime.combine(hasta, time.max) if hasta else None,
            movement_type=movement_type, direction=direction, skip=skip, limit=limit,
        ),
        "total": inventory_service.count_movements(
            db, user.tenant_id, product_id=product_id, warehouse_id=warehouse_id,
            document_id=document_id,
            date_from=datetime.combine(desde, time.min) if desde else None,
            date_to=datetime.combine(hasta, time.max) if hasta else None,
            movement_type=movement_type, direction=direction,
        ),
        "skip": skip,
        "limit": limit,
    }


@router.get("/documentos/search")
def search_inventory_documents(q: str = Query(..., min_length=1, max_length=80),
                               limit: int = Query(20, ge=1, le=50),
                               db: Session = Depends(get_db_tenant), user: models.User = Depends(get_current_user)):
    term = q.strip()
    query = db.query(models.Cotizacion).filter(
        models.Cotizacion.tenant_id == user.tenant_id,
        models.Cotizacion.document_kind == "fiscal_document",
        models.Cotizacion.tipo_comprobante.in_({"01", "03"}),
    )
    normalized = term.upper().replace(" ", "")
    if "-" in normalized:
        series, correlativo = normalized.rsplit("-", 1)
        if correlativo.isdigit():
            query = query.filter(models.Cotizacion.serie == series, models.Cotizacion.correlativo == int(correlativo))
        else:
            query = query.filter(models.Cotizacion.serie.ilike(f"%{term}%"))
    else:
        query = query.filter(or_(
            models.Cotizacion.serie.ilike(f"%{term}%"),
            cast(models.Cotizacion.correlativo, String).ilike(f"%{term}%"),
        ))
    rows = query.order_by(models.Cotizacion.id.desc()).limit(limit).all()
    return [{
        "id": row.id,
        "document_number": row.document_number,
        "document_type": row.tipo_comprobante,
        "issued_at": row.fecha_emision,
    } for row in rows]


@router.post("/disponibilidad", response_model=List[AvailabilityLine])
def availability(data: AvailabilityRequest, db: Session = Depends(get_db_tenant), user: models.User = Depends(get_current_user)):
    return inventory_service.check_availability(db, user.tenant_id, data)


@router.get("/documentos/{document_id}/disponibilidad")
def document_availability(document_id: int, db: Session = Depends(get_db_tenant),
                          user: models.User = Depends(get_current_user)):
    return inventory_service.check_document_availability(db, user.tenant_id, document_id)


@router.post("/ajustes", response_model=MovementResponse)
def adjustment(data: InventoryAdjustmentCreate, db: Session = Depends(get_db_tenant), user: models.User = Depends(_operator)):
    movement = inventory_service.adjust_stock(
        db, user.tenant_id, data, user.id,
        can_override_negative=get_effective_role(user) in {ROLE_ADMIN, ROLE_SUPERADMIN},
    )
    return inventory_service.list_movements(db, user.tenant_id, product_id=movement.product_id, warehouse_id=movement.warehouse_id, limit=1)[0]


@router.post("/cargas", response_model=BulkInventoryAdjustmentResponse)
def bulk_adjustment(data: BulkInventoryAdjustmentCreate, db: Session = Depends(get_db_tenant),
                    user: models.User = Depends(_operator)):
    return inventory_service.bulk_adjust_stock(db, user.tenant_id, data, user.id)


@router.get("/cargas/plantilla")
def stock_import_template(user: models.User = Depends(get_current_user)):
    content = "codigo_interno,producto,cantidad\nSKU-001,Producto de ejemplo,10\n"
    return Response(
        content=content.encode("utf-8-sig"), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=plantilla_stock.csv"},
    )


@router.post("/cargas/preview")
async def preview_stock_import(file: UploadFile = File(...), db: Session = Depends(get_db_tenant),
                               user: models.User = Depends(_operator)):
    ext, raw_bytes = await read_validated_upload(
        file,
        allowed_extensions={"csv", "xlsx"},
        allowed_content_types={
            "text/csv", "application/csv", "text/plain",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/octet-stream",
        },
        max_size_bytes=2 * 1024 * 1024,
    )
    parsed, errors = await run_in_threadpool(parse_inventory_stock, ext, raw_bytes)
    products = db.query(models.Producto).filter(
        models.Producto.tenant_id == user.tenant_id,
        models.Producto.inventory_enabled.is_(True),
        models.Producto.item_type == "inventory",
    ).all()
    by_code = {str(row.codigo_interno).strip().casefold(): row for row in products if row.codigo_interno}
    by_name = {}
    for row in products:
        by_name.setdefault(row.nombre.strip().casefold(), []).append(row)
    resolved, seen = [], set()
    for item in parsed:
        product = by_code.get(item["codigo_interno"].casefold()) if item["codigo_interno"] else None
        if not product and item["nombre"]:
            matches = by_name.get(item["nombre"].casefold(), [])
            if len(matches) == 1:
                product = matches[0]
            elif len(matches) > 1:
                errors.append({"fila": item["fila"], "campo": "producto", "mensaje": "El nombre coincide con varios productos; usa SKU."})
                continue
        if not product:
            errors.append({"fila": item["fila"], "campo": "producto", "mensaje": "Producto inventariable no encontrado."})
            continue
        if product.id in seen:
            errors.append({"fila": item["fila"], "campo": "producto", "mensaje": "Producto repetido en el archivo."})
            continue
        seen.add(product.id)
        resolved.append({
            "row": item["fila"], "product_id": product.id, "product_name": product.nombre,
            "product_code": product.codigo_interno, "quantity": item["quantity"],
        })
    return {"items": resolved, "errors": errors}


@router.post("/transferencias", status_code=201)
def transfer(data: TransferCreate, db: Session = Depends(get_db_tenant), user: models.User = Depends(_operator)):
    result = inventory_service.transfer_stock(
        db, user.tenant_id, data, user.id,
        can_override_negative=get_effective_role(user) in {ROLE_ADMIN, ROLE_SUPERADMIN},
    )
    return {"id": result.id, "status": result.status, "created_at": result.created_at}


@router.get("/devoluciones")
def returns(skip: int = Query(0, ge=0), limit: int = Query(15, ge=1, le=100),
            db: Session = Depends(get_db_tenant), user: models.User = Depends(get_current_user)):
    rows = db.query(models.InventoryReturn).filter(
        models.InventoryReturn.tenant_id == user.tenant_id,
    ).order_by(models.InventoryReturn.created_at.desc()).offset(skip).limit(limit).all()
    product_ids = {item.product_id for row in rows for item in row.items}
    products = {
        product.id: product
        for product in db.query(models.Producto).filter(
            models.Producto.tenant_id == user.tenant_id,
            models.Producto.id.in_(product_ids),
        ).all()
    } if product_ids else {}
    note_ids = {row.credit_note_id for row in rows}
    notes = {
        note.id: note
        for note in db.query(models.Cotizacion).filter(
            models.Cotizacion.tenant_id == user.tenant_id,
            models.Cotizacion.id.in_(note_ids),
        ).all()
    } if note_ids else {}
    return [{
        "id": row.id, "credit_note_id": row.credit_note_id,
        "credit_note_number": getattr(notes.get(row.credit_note_id), "document_number", None),
        "warehouse_id": row.warehouse_id, "status": row.status,
        "created_at": row.created_at,
        "items": [{
            "id": item.id, "product_id": item.product_id,
            "product_name": getattr(products.get(item.product_id), "nombre", None),
            "authorized_quantity": item.authorized_quantity,
            "received_quantity": item.received_quantity,
        } for item in row.items],
    } for row in rows]


@router.post("/devoluciones/{return_id}/recibir")
def receive_return(return_id: int, data: ReturnReceiptCreate,
                   db: Session = Depends(get_db_tenant), user: models.User = Depends(_operator)):
    row = inventory_service.receive_return(db, user.tenant_id, return_id, data, user.id)
    return {"id": row.id, "status": row.status, "received_at": row.received_at}
