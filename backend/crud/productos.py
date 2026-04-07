"""crud/productos.py — CRUD de Productos."""
from sqlalchemy.orm import Session

import models
import schemas
from services import calculations
from crud._base import get_producto_for_tenant


def get_productos(
    db: Session,
    tenant_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    q: str | None = None,
):
    from sqlalchemy import or_
    query = db.query(models.Producto)
    if tenant_id is not None:
        query = query.filter(models.Producto.tenant_id == tenant_id)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                models.Producto.nombre.ilike(term),
                models.Producto.codigo_interno.ilike(term),
                models.Producto.descripcion.ilike(term),
            )
        )
    return query.order_by(models.Producto.nombre).offset(skip).limit(limit).all()


def create_producto(db: Session, producto: schemas.ProductoCreate, tenant_id: int):
    precio_final = producto.precio_unitario
    valor_unitario = precio_final / calculations.FACTOR_IGV
    valor_unitario_redondeado = calculations.redondear(valor_unitario)

    db_producto = models.Producto(
        **producto.model_dump(),
        valor_unitario=valor_unitario_redondeado,
        tenant_id=tenant_id
    )
    try:
        db.add(db_producto)
        db.commit()
        db.refresh(db_producto)
        return db_producto
    except Exception as e:
        db.rollback()
        raise e


def update_producto(db: Session, producto_id: int, producto_data: schemas.ProductoCreate, tenant_id: int):
    db_producto = get_producto_for_tenant(db, producto_id, tenant_id)
    if db_producto:
        update_data = producto_data.model_dump()
        if 'precio_unitario' in update_data:
            precio = update_data['precio_unitario']
            valor = precio / calculations.FACTOR_IGV
            update_data['valor_unitario'] = calculations.redondear(valor)
        for key, value in update_data.items():
            setattr(db_producto, key, value)
        db.commit()
        db.refresh(db_producto)
    return db_producto


def delete_producto(db: Session, producto_id: int, tenant_id: int):
    db_producto = get_producto_for_tenant(db, producto_id, tenant_id)
    if db_producto:
        db.delete(db_producto)
        db.commit()
    return db_producto
