"""crud/productos.py — CRUD de Productos."""
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

import models
import schemas
from services import calculations
from crud._base import get_producto_for_tenant


def count_productos(
    db: Session,
    tenant_id: int | None = None,
    q: str | None = None,
) -> int:
    query = db.query(func.count(models.Producto.id))
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
    return query.scalar() or 0


def get_productos(
    db: Session,
    tenant_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    q: str | None = None,
):
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


def _resolve_product_prices(
    *,
    precio_referencia,
    precio_incluye_igv: bool,
    tipo_afectacion_igv: str,
):
    precio = calculations.to_decimal(precio_referencia)

    if tipo_afectacion_igv != "10":
        precio_final = calculations.redondear(precio)
        return precio_final, precio_final

    if precio_incluye_igv:
        precio_final = calculations.redondear(precio)
        valor_unitario = calculations.redondear(precio / calculations.FACTOR_IGV)
        return precio_final, valor_unitario

    valor_unitario = calculations.redondear(precio)
    precio_final = calculations.redondear(precio * calculations.FACTOR_IGV)
    return precio_final, valor_unitario


def create_producto(db: Session, producto: schemas.ProductoCreate, tenant_id: int):
    payload = producto.model_dump(exclude={"precio_incluye_igv"})
    precio_final, valor_unitario = _resolve_product_prices(
        precio_referencia=producto.precio_unitario,
        precio_incluye_igv=producto.precio_incluye_igv,
        tipo_afectacion_igv=producto.tipo_afectacion_igv,
    )
    payload["precio_unitario"] = precio_final
    payload["valor_unitario"] = valor_unitario

    db_producto = models.Producto(
        **payload,
        tenant_id=tenant_id,
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
        update_data = producto_data.model_dump(exclude={"precio_incluye_igv"})
        if 'precio_unitario' in update_data:
            precio_final, valor_unitario = _resolve_product_prices(
                precio_referencia=producto_data.precio_unitario,
                precio_incluye_igv=producto_data.precio_incluye_igv,
                tipo_afectacion_igv=producto_data.tipo_afectacion_igv,
            )
            update_data['precio_unitario'] = precio_final
            update_data['valor_unitario'] = valor_unitario
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
