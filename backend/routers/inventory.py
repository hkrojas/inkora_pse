from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import models
from access_control import ELEVATED_TENANT_ROLES, ROLE_ADMIN, ROLE_SUPERADMIN, assert_user_has_roles, get_effective_role
from api_dependencies import get_current_user, get_db_tenant, require_admin
from schemas.inventory import (
    AvailabilityLine, AvailabilityRequest, InventoryActivation,
    InventoryAdjustmentCreate, MovementResponse, ProductInventoryConfig,
    StockResponse, TransferCreate, WarehouseCreate, WarehouseResponse,
    ReturnReceiptCreate,
)
from services import inventory_service

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
           skip: int = Query(0, ge=0), limit: int = Query(15, ge=1, le=100),
           db: Session = Depends(get_db_tenant), user: models.User = Depends(get_current_user)):
    return inventory_service.list_movements(
        db, user.tenant_id, product_id=product_id,
        warehouse_id=warehouse_id, skip=skip, limit=limit,
    )


@router.post("/disponibilidad", response_model=List[AvailabilityLine])
def availability(data: AvailabilityRequest, db: Session = Depends(get_db_tenant), user: models.User = Depends(get_current_user)):
    return inventory_service.check_availability(db, user.tenant_id, data)


@router.post("/ajustes", response_model=MovementResponse)
def adjustment(data: InventoryAdjustmentCreate, db: Session = Depends(get_db_tenant), user: models.User = Depends(_operator)):
    movement = inventory_service.adjust_stock(
        db, user.tenant_id, data, user.id,
        can_override_negative=get_effective_role(user) in {ROLE_ADMIN, ROLE_SUPERADMIN},
    )
    return inventory_service.list_movements(db, user.tenant_id, product_id=movement.product_id, warehouse_id=movement.warehouse_id, limit=1)[0]


@router.post("/transferencias", status_code=201)
def transfer(data: TransferCreate, db: Session = Depends(get_db_tenant), user: models.User = Depends(_operator)):
    result = inventory_service.transfer_stock(
        db, user.tenant_id, data, user.id,
        can_override_negative=get_effective_role(user) in {ROLE_ADMIN, ROLE_SUPERADMIN},
    )
    return {"id": result.id, "status": result.status, "created_at": result.created_at}


@router.get("/devoluciones")
def returns(db: Session = Depends(get_db_tenant), user: models.User = Depends(get_current_user)):
    rows = db.query(models.InventoryReturn).filter(
        models.InventoryReturn.tenant_id == user.tenant_id,
    ).order_by(models.InventoryReturn.created_at.desc()).all()
    return [{
        "id": row.id, "credit_note_id": row.credit_note_id,
        "warehouse_id": row.warehouse_id, "status": row.status,
        "created_at": row.created_at,
        "items": [{
            "id": item.id, "product_id": item.product_id,
            "authorized_quantity": item.authorized_quantity,
            "received_quantity": item.received_quantity,
        } for item in row.items],
    } for row in rows]


@router.post("/devoluciones/{return_id}/recibir")
def receive_return(return_id: int, data: ReturnReceiptCreate,
                   db: Session = Depends(get_db_tenant), user: models.User = Depends(_operator)):
    row = inventory_service.receive_return(db, user.tenant_id, return_id, data, user.id)
    return {"id": row.id, "status": row.status, "received_at": row.received_at}
