"""crud/productos.py — CRUD de Productos."""
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

import models
import schemas
from services import calculations
from crud._base import get_producto_for_tenant


class ProductoEnUsoError(Exception):
    """Se usa cuando el catalogo ya esta referenciado por documentos."""


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
        precio_final = calculations.redondear_precio_unitario(precio)
        return precio_final, calculations.redondear_extendido(precio_final)

    if precio_incluye_igv:
        precio_final = calculations.redondear_precio_unitario(precio)
        valor_unitario = calculations.redondear_extendido(precio_final / calculations.FACTOR_IGV)
        return precio_final, valor_unitario

    valor_unitario = calculations.redondear_extendido(precio)
    precio_final = calculations.redondear_precio_unitario(precio * calculations.FACTOR_IGV)
    return precio_final, valor_unitario


def _ensure_inventory_balance(db: Session, product: models.Producto) -> None:
    """Create the zero balance that makes a catalog item immediately visible."""
    if not product.inventory_enabled or product.item_type != "inventory":
        return
    warehouse = db.query(models.Warehouse).filter(
        models.Warehouse.tenant_id == product.tenant_id,
        models.Warehouse.is_default.is_(True),
        models.Warehouse.is_active.is_(True),
    ).first()
    if not warehouse:
        warehouse = models.Warehouse(
            tenant_id=product.tenant_id,
            code="PRINCIPAL",
            name="Almacén principal",
            is_default=True,
            is_active=True,
        )
        db.add(warehouse)
        db.flush()
    exists = db.query(models.InventoryBalance.id).filter(
        models.InventoryBalance.tenant_id == product.tenant_id,
        models.InventoryBalance.warehouse_id == warehouse.id,
        models.InventoryBalance.product_id == product.id,
    ).first()
    if not exists:
        db.add(models.InventoryBalance(
            tenant_id=product.tenant_id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            on_hand=0,
            committed=0,
            minimum_stock=0,
        ))


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
        db.flush()
        _ensure_inventory_balance(db, db_producto)
        db.commit()
        db.refresh(db_producto)
        return db_producto
    except Exception as e:
        db.rollback()
        raise e


def _producto_model_from_schema(
    producto: schemas.ProductoCreate,
    tenant_id: int,
) -> models.Producto:
    payload = producto.model_dump(exclude={"precio_incluye_igv"})
    precio_final, valor_unitario = _resolve_product_prices(
        precio_referencia=producto.precio_unitario,
        precio_incluye_igv=producto.precio_incluye_igv,
        tipo_afectacion_igv=producto.tipo_afectacion_igv,
    )
    payload["precio_unitario"] = precio_final
    payload["valor_unitario"] = valor_unitario
    return models.Producto(**payload, tenant_id=tenant_id)


def create_productos_bulk(
    db: Session,
    productos: list[schemas.ProductoCreate],
    tenant_id: int,
) -> list[models.Producto]:
    db_productos = [
        _producto_model_from_schema(producto, tenant_id)
        for producto in productos
    ]
    if not db_productos:
        return []
    try:
        db.add_all(db_productos)
        db.flush()
        for db_producto in db_productos:
            _ensure_inventory_balance(db, db_producto)
        db.commit()
        return db_productos
    except Exception as e:
        db.rollback()
        raise e


def update_producto(db: Session, producto_id: int, producto_data: schemas.ProductoCreate, tenant_id: int):
    db_producto = get_producto_for_tenant(db, producto_id, tenant_id)
    if db_producto:
        update_data = producto_data.model_dump(
            exclude={"precio_incluye_igv"},
            exclude_unset=True,
        )
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
        _ensure_inventory_balance(db, db_producto)
        db.commit()
        db.refresh(db_producto)
    return db_producto


def delete_producto(db: Session, producto_id: int, tenant_id: int):
    db_producto = get_producto_for_tenant(db, producto_id, tenant_id)
    if db_producto:
        usado_en_documentos = (
            db.query(models.CotizacionItem.id)
            .join(models.Cotizacion, models.CotizacionItem.cotizacion_id == models.Cotizacion.id)
            .filter(
                models.CotizacionItem.producto_id == producto_id,
                models.Cotizacion.tenant_id == tenant_id,
            )
            .first()
        )
        if usado_en_documentos:
            raise ProductoEnUsoError(
                "No se puede eliminar un producto usado en cotizaciones o comprobantes. "
                "Mantenerlo preserva el historial comercial."
            )
        db.delete(db_producto)
        db.commit()
    return db_producto
