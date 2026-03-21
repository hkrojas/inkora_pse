from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from passlib.context import CryptContext
from typing import List, Optional

import models
import schemas
import calculations 

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ==========================================
# USUARIOS
# ==========================================

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        nombre_completo=user.nombre_completo,
        rol=user.rol
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# ==========================================
# CLIENTES
# ==========================================

def get_clientes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Cliente).order_by(models.Cliente.razon_social).offset(skip).limit(limit).all()

def create_cliente(db: Session, cliente: schemas.ClienteCreate):
    db_cliente = models.Cliente(**cliente.model_dump())
    try:
        db.add(db_cliente)
        db.commit()
        db.refresh(db_cliente)
        return db_cliente
    except Exception as e:
        db.rollback()
        raise e

def update_cliente(db: Session, cliente_id: int, cliente_data: schemas.ClienteCreate):
    db_cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if db_cliente:
        for key, value in cliente_data.model_dump().items():
            setattr(db_cliente, key, value)
        db.commit()
        db.refresh(db_cliente)
    return db_cliente

def delete_cliente(db: Session, cliente_id: int):
    db_cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if db_cliente:
        db.delete(db_cliente)
        db.commit()
    return db_cliente

# ==========================================
# PRODUCTOS
# ==========================================

def get_productos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Producto).order_by(models.Producto.nombre).offset(skip).limit(limit).all()

def create_producto(db: Session, producto: schemas.ProductoCreate):
    precio_final = producto.precio_unitario
    valor_unitario = precio_final / calculations.FACTOR_IGV
    valor_unitario_redondeado = calculations.redondear(valor_unitario)

    db_producto = models.Producto(
        **producto.model_dump(),
        valor_unitario=valor_unitario_redondeado
    )
    try:
        db.add(db_producto)
        db.commit()
        db.refresh(db_producto)
        return db_producto
    except Exception as e:
        db.rollback()
        raise e

def update_producto(db: Session, producto_id: int, producto_data: schemas.ProductoCreate):
    db_producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
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

def delete_producto(db: Session, producto_id: int):
    db_producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if db_producto:
        db.delete(db_producto)
        db.commit()
    return db_producto

# ==========================================
# COTIZACIONES
# ==========================================

def get_cotizaciones(db: Session, usuario: Optional[models.User] = None, skip: int = 0, limit: int = 100):
    query = db.query(models.Cotizacion)\
        .options(joinedload(models.Cotizacion.cliente), joinedload(models.Cotizacion.usuario))\
        .order_by(desc(models.Cotizacion.id))
    if usuario and getattr(usuario, "rol", "vendedor") not in ["admin", "superadmin"]:
        query = query.filter(models.Cotizacion.usuario_id == usuario.id)
    return query.offset(skip).limit(limit).all()

def get_cotizacion(db: Session, cotizacion_id: int, usuario: Optional[models.User] = None):
    query = db.query(models.Cotizacion)\
        .options(joinedload(models.Cotizacion.cliente), joinedload(models.Cotizacion.items))\
        .filter(models.Cotizacion.id == cotizacion_id)
    if usuario and getattr(usuario, "rol", "vendedor") not in ["admin", "superadmin"]:
        query = query.filter(models.Cotizacion.usuario_id == usuario.id)
    return query.first()

def create_cotizacion(db: Session, cotizacion: schemas.CotizacionCreate, usuario_id: int):
    items_db = []
    items_procesados_para_suma = []

    for item in cotizacion.items:
        calculo = calculations.calcular_item(
            cantidad=item.cantidad, 
            precio_con_igv=item.precio_unitario
        )

        db_item = models.CotizacionItem(
            producto_id=item.producto_id,
            descripcion=item.descripcion,
            cantidad=calculo["cantidad"],
            precio_unitario=calculo["precio_unitario"],
            valor_unitario=calculo["valor_unitario"],
            total_base_igv=calculo["total_base_igv"],
            total_igv=calculo["total_igv"],
            total_item=calculo["total_item"],
            unidad_medida=calculo["unidad_medida"],
            tipo_afectacion_igv=calculo["tipo_afectacion_igv"]
        )
        items_db.append(db_item)
        items_procesados_para_suma.append(calculo)

    totales = calculations.sumarizar_cotizacion(items_procesados_para_suma)

    ultimo_correlativo = db.query(func.max(models.Cotizacion.correlativo)).scalar() or 0
    nuevo_correlativo = ultimo_correlativo + 1

    db_cotizacion = models.Cotizacion(
        cliente_id=cotizacion.cliente_id,
        usuario_id=usuario_id,
        fecha_vencimiento=cotizacion.fecha_vencimiento,
        moneda=cotizacion.moneda,
        tipo_comprobante=cotizacion.tipo_comprobante,
        correlativo=nuevo_correlativo, 
        serie="COT", 
        total_gravada=totales["total_gravada"],
        total_exonerada=totales["total_exonerada"],
        total_inafecta=totales["total_inafecta"],
        total_igv=totales["total_igv"],
        total_venta=totales["total_venta"],
        items=items_db
    )

    try:
        db.add(db_cotizacion)
        db.commit()
        db.refresh(db_cotizacion)
        return get_cotizacion(db, db_cotizacion.id)
    except Exception as e:
        db.rollback()
        raise e

def guardar_respuesta_sunat(db: Session, cotizacion_id: int, data_sunat: dict):
    """Guarda los links devueltos por la API de Facturación en la cotización"""
    db_cot = db.query(models.Cotizacion).filter(models.Cotizacion.id == cotizacion_id).first()
    if db_cot:
        links = data_sunat.get('links', {}) if data_sunat.get('links') else data_sunat.get('sunat_response', {}).get('links', {})
        if links:
            db_cot.sunat_xml_url = links.get('xml')
            db_cot.sunat_pdf_url = links.get('pdf')
            db_cot.sunat_cdr_url = links.get('cdr')
        
        db_cot.estado = "facturada"
        db_cot.sunat_error = None
        
        # Guardar Serie y Correlativo si la API los asignó o modificó
        if data_sunat.get('serie'): db_cot.serie = data_sunat.get('serie')
        if data_sunat.get('correlativo'): 
            try:
                db_cot.correlativo = int(data_sunat.get('correlativo'))
            except: pass

        db.commit()
        db.refresh(db_cot)
    return db_cot