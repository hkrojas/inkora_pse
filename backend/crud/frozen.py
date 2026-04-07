"""crud/frozen.py — Dominios congelados: MRP, BOM, proveedores, alertas."""
from sqlalchemy.orm import Session, joinedload

import models
import schemas


# ==========================================
# PROVEEDORES (Broker)
# ==========================================

def get_proveedores(db: Session, tenant_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Proveedor).filter(models.Proveedor.tenant_id == tenant_id).offset(skip).limit(limit).all()


def create_proveedor(db: Session, proveedor: schemas.ProveedorCreate, tenant_id: int):
    db_proveedor = models.Proveedor(**proveedor.model_dump(), tenant_id=tenant_id)
    db.add(db_proveedor)
    db.commit()
    db.refresh(db_proveedor)
    return db_proveedor


def update_proveedor(db: Session, proveedor_id: int, proveedor: schemas.ProveedorUpdate, tenant_id: int):
    db_proveedor = db.query(models.Proveedor).filter(models.Proveedor.id == proveedor_id, models.Proveedor.tenant_id == tenant_id).first()
    if not db_proveedor:
        return None
    for var, value in proveedor.model_dump(exclude_unset=True).items():
        setattr(db_proveedor, var, value)
    db.commit()
    db.refresh(db_proveedor)
    return db_proveedor


def delete_proveedor(db: Session, proveedor_id: int, tenant_id: int):
    db_proveedor = db.query(models.Proveedor).filter(models.Proveedor.id == proveedor_id, models.Proveedor.tenant_id == tenant_id).first()
    if not db_proveedor:
        return False
    db.delete(db_proveedor)
    db.commit()
    return True


# ==========================================
# INSUMOS / MATERIA PRIMA
# ==========================================

def get_insumos(db: Session, tenant_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Insumo).filter(
        models.Insumo.tenant_id == tenant_id
    ).offset(skip).limit(limit).all()


def create_insumo(db: Session, insumo: schemas.InsumoCreate, tenant_id: int):
    db_insumo = models.Insumo(
        tenant_id=tenant_id,
        nombre=insumo.nombre,
        unidad_compra=insumo.unidad_compra,
        unidad_consumo=insumo.unidad_consumo,
        factor_conversion=insumo.factor_conversion,
        costo_promedio=insumo.costo_promedio,
        stock_actual=insumo.stock_actual,
        umbral_minimo=insumo.umbral_minimo
    )
    db.add(db_insumo)
    db.commit()
    db.refresh(db_insumo)
    return db_insumo


def update_insumo(db: Session, insumo_id: int, insumo_data: schemas.InsumoCreate, tenant_id: int):
    db_insumo = db.query(models.Insumo).filter(
        models.Insumo.id == insumo_id,
        models.Insumo.tenant_id == tenant_id
    ).first()
    if db_insumo:
        for key, value in insumo_data.model_dump().items():
            setattr(db_insumo, key, value)
        db.commit()
        db.refresh(db_insumo)
    return db_insumo


def delete_insumo(db: Session, insumo_id: int, tenant_id: int):
    db_insumo = db.query(models.Insumo).filter(
        models.Insumo.id == insumo_id,
        models.Insumo.tenant_id == tenant_id
    ).first()
    if db_insumo:
        db.delete(db_insumo)
        db.commit()
    return db_insumo


# ==========================================
# BOM / RECETAS
# ==========================================

def get_recetas_producto(db: Session, producto_id: int, tenant_id: int):
    return (
        db.query(models.RecetaBOM)
        .join(models.Producto, models.RecetaBOM.producto_id == models.Producto.id)
        .filter(
            models.RecetaBOM.producto_id == producto_id,
            models.Producto.tenant_id == tenant_id,
        )
        .all()
    )


def create_receta_bom(db: Session, receta: schemas.RecetaBOMCreate, tenant_id: int):
    db_receta = models.RecetaBOM(
        tenant_id=tenant_id,
        producto_id=receta.producto_id,
        insumo_id=receta.insumo_id,
        cantidad_base_necesaria=receta.cantidad_base_necesaria,
        porcentaje_merma_estandar=receta.porcentaje_merma_estandar
    )
    db.add(db_receta)
    db.commit()
    db.refresh(db_receta)
    return db_receta


# ==========================================
# ÓRDENES DE PRODUCCIÓN (MRP)
# ==========================================

def get_ordenes_produccion(db: Session, tenant_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.OrdenProduccion).filter(
        models.OrdenProduccion.tenant_id == tenant_id
    ).options(
        joinedload(models.OrdenProduccion.detalles),
        joinedload(models.OrdenProduccion.proveedor)
    ).order_by(models.OrdenProduccion.id.desc()).offset(skip).limit(limit).all()


def generar_orden_produccion(db: Session, cotizacion_id: int, tenant_id: int, tipo_produccion: str = "interna", proveedor_id: int = None, costo_tercerizado=None):
    from decimal import Decimal

    db_cotizacion = db.query(models.Cotizacion).filter(
        models.Cotizacion.id == cotizacion_id,
        models.Cotizacion.tenant_id == tenant_id
    ).first()

    if not db_cotizacion:
        raise ValueError("Cotización no encontrada o no pertenece al Tenant")

    orden_previa = db.query(models.OrdenProduccion).filter(
        models.OrdenProduccion.cotizacion_id == cotizacion_id
    ).first()
    if orden_previa:
        raise ValueError(f"Ya existe una Orden de Producción (ID: {orden_previa.id}) para este documento.")

    db_orden = models.OrdenProduccion(
        tenant_id=tenant_id,
        cotizacion_id=cotizacion_id,
        estado="en_cola",
        tipo_produccion=tipo_produccion,
        proveedor_id=proveedor_id,
        costo_tercerizado=costo_tercerizado
    )
    db.add(db_orden)
    db.flush()

    for item in db_cotizacion.items:
        if not item.producto_id:
            continue

        recetas = db.query(models.RecetaBOM).filter(
            models.RecetaBOM.producto_id == item.producto_id
        ).all()

        cantidad_vendida = Decimal(str(item.cantidad))
        for receta in recetas:
            cant_base = Decimal(str(receta.cantidad_base_necesaria))
            merma_pct = Decimal(str(receta.porcentaje_merma_estandar)) / Decimal("100")

            neta = cantidad_vendida * cant_base
            merma = neta * merma_pct
            total = neta + merma

            db_detalle = models.OrdenProduccionDetalle(
                orden_id=db_orden.id,
                insumo_id=receta.insumo_id,
                cantidad_requerida_neta=neta,
                cantidad_merma=merma,
                cantidad_total_descontar=total
            )
            db.add(db_detalle)

    try:
        db.commit()
        db.refresh(db_orden)
        return db_orden
    except Exception as e:
        db.rollback()
        raise e


def update_orden_produccion_status(db: Session, orden_id: int, nuevo_estado: str, tenant_id: int):
    from datetime import datetime
    db_orden = db.query(models.OrdenProduccion).filter(
        models.OrdenProduccion.id == orden_id,
        models.OrdenProduccion.tenant_id == tenant_id
    ).first()

    if not db_orden:
        return None

    db_orden.estado = nuevo_estado
    if nuevo_estado == "finalizada":
        db_orden.fecha_fin = datetime.now()

    db.commit()
    db.refresh(db_orden)
    return db_orden


def verificar_stock_y_generar_alertas(db: Session, tenant_id: int):
    insumos_criticos = db.query(models.Insumo).filter(
        models.Insumo.tenant_id == tenant_id,
        models.Insumo.stock_actual <= models.Insumo.umbral_minimo
    ).all()

    for insumo in insumos_criticos:
        alerta_existente = db.query(models.AlertaInventario).filter(
            models.AlertaInventario.insumo_id == insumo.id,
            models.AlertaInventario.resuelta == False  # noqa: E712
        ).first()

        if not alerta_existente:
            nueva_alerta = models.AlertaInventario(
                tenant_id=tenant_id,
                insumo_id=insumo.id,
                mensaje=f"STOCK CRÍTICO: {insumo.nombre} (Stock: {insumo.stock_actual} | Umbral: {insumo.umbral_minimo})",
                resuelta=False
            )
            db.add(nueva_alerta)
