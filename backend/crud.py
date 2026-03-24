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
        rol=user.rol,
        tenant_id=user.tenant_id  # MULTITENANCIA
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# ==========================================
# TENANTS
# ==========================================

def get_tenant(db: Session, tenant_id: int):
    return db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()

def create_tenant(db: Session, tenant: schemas.TenantCreate):
    db_tenant = models.Tenant(**tenant.model_dump())
    try:
        db.add(db_tenant)
        db.commit()
        db.refresh(db_tenant)
        return db_tenant
    except Exception as e:
        db.rollback()
        raise e

def update_tenant(db: Session, tenant_id: int, data: schemas.TenantUpdate):
    db_tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if db_tenant:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(db_tenant, key, value)
        db.commit()
        db.refresh(db_tenant)
    return db_tenant

# ==========================================
# CLIENTES
# ==========================================

def get_clientes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Cliente).order_by(models.Cliente.razon_social).offset(skip).limit(limit).all()

def create_cliente(db: Session, cliente: schemas.ClienteCreate, tenant_id: int):
    db_cliente = models.Cliente(**cliente.model_dump(), tenant_id=tenant_id)
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

def create_producto(db: Session, producto: schemas.ProductoCreate, tenant_id: int):
    precio_final = producto.precio_unitario
    valor_unitario = precio_final / calculations.FACTOR_IGV
    valor_unitario_redondeado = calculations.redondear(valor_unitario)

    db_producto = models.Producto(
        **producto.model_dump(),
        valor_unitario=valor_unitario_redondeado,
        tenant_id=tenant_id  # MULTITENANCIA
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

def create_cotizacion(db: Session, cotizacion: schemas.CotizacionCreate, usuario_id: int, tenant_id: int):
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
        tenant_id=tenant_id,  # MULTITENANCIA
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

# ==========================================
# ANULACIÓN Y NOTAS DE CRÉDITO/DÉBITO
# ==========================================

def anular_cotizacion(db: Session, cotizacion_id: int):
    """Marca un comprobante como 'anulada' tras confirmación exitosa de SUNAT."""
    db_cot = db.query(models.Cotizacion).filter(models.Cotizacion.id == cotizacion_id).first()
    if not db_cot:
        return None
    try:
        db_cot.estado = "anulada"
        db.commit()
        db.refresh(db_cot)
        return db_cot
    except Exception as e:
        db.rollback()
        raise e

def crear_nota_credito_debito(
    db: Session,
    doc_afectado: models.Cotizacion,
    usuario_id: int,
    tipo_nota: str,  # "credito" o "debito"
    cod_motivo: str,
    descripcion_motivo: str
):
    """
    Crea un nuevo registro de Cotizacion que representa la Nota de Crédito (07) o Débito (08),
    clonando los items del documento afectado y vinculándolo via nota_referencia_id.
    """
    # Determinar tipo de comprobante y serie
    tipo_comprobante = "07" if tipo_nota == "credito" else "08"
    serie_origen = doc_afectado.serie  # Ej: F001, B001
    serie_nota = "FC01" if serie_origen.startswith("F") else "BC01"

    # Obtener correlativo propio para esta serie de notas
    ultimo_correlativo = db.query(func.max(models.Cotizacion.correlativo)).filter(
        models.Cotizacion.serie == serie_nota
    ).scalar() or 0
    nuevo_correlativo = ultimo_correlativo + 1

    # Clonar items del documento afectado
    items_nota = []
    for item_orig in doc_afectado.items:
        items_nota.append(models.CotizacionItem(
            producto_id=item_orig.producto_id,
            descripcion=item_orig.descripcion,
            cantidad=item_orig.cantidad,
            precio_unitario=item_orig.precio_unitario,
            valor_unitario=item_orig.valor_unitario,
            total_base_igv=item_orig.total_base_igv,
            total_igv=item_orig.total_igv,
            total_item=item_orig.total_item,
            unidad_medida=item_orig.unidad_medida,
            tipo_afectacion_igv=item_orig.tipo_afectacion_igv
        ))

    # Crear registro de la nota
    db_nota = models.Cotizacion(
        serie=serie_nota,
        correlativo=nuevo_correlativo,
        cliente_id=doc_afectado.cliente_id,
        usuario_id=usuario_id,
        tenant_id=doc_afectado.tenant_id,  # MULTITENANCIA: hereda del doc afectado
        moneda=doc_afectado.moneda,
        tipo_comprobante=tipo_comprobante,
        estado="pendiente",
        total_gravada=doc_afectado.total_gravada,
        total_exonerada=doc_afectado.total_exonerada,
        total_inafecta=doc_afectado.total_inafecta,
        total_igv=doc_afectado.total_igv,
        total_venta=doc_afectado.total_venta,
        nota_referencia_id=doc_afectado.id,
        items=items_nota
    )

    try:
        db.add(db_nota)
        db.commit()
        db.refresh(db_nota)
        return db_nota
    except Exception as e:
        db.rollback()
        raise e

# ==========================================
# GUÍAS DE REMISIÓN
# ==========================================

def get_guias_remision(db: Session, usuario: models.User = None, skip: int = 0, limit: int = 100):
    query = db.query(models.GuiaRemision)\
        .options(joinedload(models.GuiaRemision.items))\
        .order_by(desc(models.GuiaRemision.id))
    if usuario and getattr(usuario, "rol", "vendedor") not in ["admin", "superadmin"]:
        query = query.filter(models.GuiaRemision.usuario_id == usuario.id)
    return query.offset(skip).limit(limit).all()

def get_guia_remision(db: Session, guia_id: int, usuario: models.User = None):
    query = db.query(models.GuiaRemision)\
        .options(joinedload(models.GuiaRemision.items))\
        .filter(models.GuiaRemision.id == guia_id)
    if usuario and getattr(usuario, "rol", "vendedor") not in ["admin", "superadmin"]:
        query = query.filter(models.GuiaRemision.usuario_id == usuario.id)
    return query.first()

def create_guia_remision(db: Session, data: dict, usuario_id: int, tenant_id: int):
    """Crea una Guía de Remisión con sus items."""
    items_data = data.pop("items", [])
    
    # Correlativo auto-incremental por serie
    serie = data.get("serie", "T001")
    ultimo = db.query(func.max(models.GuiaRemision.correlativo)).filter(
        models.GuiaRemision.serie == serie
    ).scalar() or 0
    
    items_db = [models.GuiaRemisionItem(**item) for item in items_data]
    
    db_guia = models.GuiaRemision(
        **data,
        usuario_id=usuario_id,
        tenant_id=tenant_id,  # MULTITENANCIA
        correlativo=ultimo + 1,
        items=items_db
    )
    
    try:
        db.add(db_guia)
        db.commit()
        db.refresh(db_guia)
        return get_guia_remision(db, db_guia.id)
    except Exception as e:
        db.rollback()
        raise e

def guardar_respuesta_sunat_gre(db: Session, guia_id: int, data_sunat: dict):
    """Guarda la respuesta SUNAT en una Guía de Remisión."""
    db_guia = db.query(models.GuiaRemision).filter(models.GuiaRemision.id == guia_id).first()
    if db_guia:
        links = data_sunat.get('links', {}) or data_sunat.get('sunat_response', {}).get('links', {})
        if links:
            db_guia.sunat_xml_url = links.get('xml')
            db_guia.sunat_pdf_url = links.get('pdf')
            db_guia.sunat_cdr_url = links.get('cdr')
        db_guia.estado = "emitida"
        db_guia.sunat_error = None
        db.commit()
        db.refresh(db_guia)
    return db_guia