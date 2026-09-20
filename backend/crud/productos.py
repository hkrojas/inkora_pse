"""crud/productos.py — CRUD de Productos."""
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

import models
import schemas
from services import calculations
from services import inventory_service
from schemas.inventory import InventoryActivation, ProductInventoryConfig
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
    """Resolve precio_unitario (con IGV) and valor_unitario (sin IGV).

    Prices are stored with up to 4 decimal places to preserve user-entered
    precision.  Rounding to 2 decimals is deferred to line-total calculations
    in ``services.calculations``.
    """
    precio = calculations.to_decimal(precio_referencia)
    _PRICE_PRECISION = calculations.Decimal("0.0001")

    if tipo_afectacion_igv != "10":
        precio_final = precio.quantize(_PRICE_PRECISION, rounding=calculations.ROUND_HALF_UP)
        return precio_final, precio_final

    if precio_incluye_igv:
        precio_final = precio.quantize(_PRICE_PRECISION, rounding=calculations.ROUND_HALF_UP)
        valor_unitario = (precio / calculations.FACTOR_IGV).quantize(
            _PRICE_PRECISION, rounding=calculations.ROUND_HALF_UP,
        )
        return precio_final, valor_unitario

    valor_unitario = precio.quantize(_PRICE_PRECISION, rounding=calculations.ROUND_HALF_UP)
    precio_final = (precio * calculations.FACTOR_IGV).quantize(
        _PRICE_PRECISION, rounding=calculations.ROUND_HALF_UP,
    )
    return precio_final, valor_unitario



def create_producto(db: Session, producto: schemas.ProductoCreate, tenant_id: int):
    db.query(models.Tenant).filter(models.Tenant.id == tenant_id).with_for_update().one()
    payload = producto.model_dump(exclude={"precio_incluye_igv", "inventario_inicial"})
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
        if producto.inventario_inicial:
            inventory_service.activate_inventory(db, tenant_id, InventoryActivation(), commit=False)
            inventory_service.configure_product(
                db,
                tenant_id,
                db_producto.id,
                ProductInventoryConfig(
                    item_type="inventory",
                    inventory_enabled=True,
                    warehouse_id=producto.inventario_inicial.warehouse_id,
                    opening_stock=producto.inventario_inicial.opening_stock,
                    minimum_stock=producto.inventario_inicial.minimum_stock,
                ),
                user_id=None,
                commit=False,
            )
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
    payload = producto.model_dump(exclude={"precio_incluye_igv", "inventario_inicial"})
    payload["inventory_enabled"] = False
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
        db.commit()
        return db_productos
    except Exception as e:
        db.rollback()
        raise e


def update_producto(db: Session, producto_id: int, producto_data: schemas.ProductoCreate, tenant_id: int):
    db.query(models.Tenant).filter(models.Tenant.id == tenant_id).with_for_update().one()
    db_producto = get_producto_for_tenant(db, producto_id, tenant_id)
    if db_producto:
        update_data = producto_data.model_dump(exclude={"precio_incluye_igv", "inventario_inicial"}, exclude_unset=True)
        has_movements = db.query(models.InventoryMovement.id).filter(
            models.InventoryMovement.tenant_id == tenant_id,
            models.InventoryMovement.product_id == producto_id,
        ).first()
        if has_movements and update_data.get("unidad_medida", db_producto.unidad_medida) != db_producto.unidad_medida:
            raise ProductoEnUsoError("No se puede cambiar la unidad de un producto que ya tiene kardex.")
        if has_movements and (
            not update_data.get("inventory_enabled", db_producto.inventory_enabled)
            or update_data.get("item_type", db_producto.item_type) != "inventory"
        ):
            raise ProductoEnUsoError("No se puede desactivar un producto que ya tiene movimientos de inventario.")
        if db_producto.inventory_enabled and "inventory_enabled" not in update_data:
            update_data["inventory_enabled"] = True
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
        if producto_data.inventario_inicial:
            inventory_service.activate_inventory(db, tenant_id, InventoryActivation(), commit=False)
            inventory_service.configure_product(
                db, tenant_id, producto_id,
                ProductInventoryConfig(
                    item_type="inventory", inventory_enabled=True,
                    **producto_data.inventario_inicial.model_dump(),
                ), user_id=None, commit=False,
            )
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
        usado_en_inventario = db.query(models.InventoryMovement.id).filter(
            models.InventoryMovement.tenant_id == tenant_id,
            models.InventoryMovement.product_id == producto_id,
        ).first()
        if usado_en_inventario:
            raise ProductoEnUsoError(
                "No se puede eliminar un producto con kardex. Desactivalo para conservar la trazabilidad."
            )
        db.delete(db_producto)
        db.commit()
    return db_producto


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
