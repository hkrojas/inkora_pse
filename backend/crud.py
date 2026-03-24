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

    totales = calculations.sumarizar_cotizacion(items_procesados_para_suma)

    # ---------------------------------------------------------
    # BLOQUEO TRANSACCIONAL: Prevención de Race Conditions (Fase 5)
    # ---------------------------------------------------------
    # Bloqueamos la última fila de la serie para este tenant específico
    # Asegura que 2 hilos concurrentes no lean el mismo MAX(correlativo)
    last_doc = db.query(models.Cotizacion).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.serie == "COT"
    ).order_by(
        models.Cotizacion.correlativo.desc()
    ).with_for_update().first()
    
    ultimo_correlativo = last_doc.correlativo if last_doc else 0
    nuevo_correlativo = ultimo_correlativo + 1
    # ---------------------------------------------------------

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

# ==========================================
# PAGOS / ADELANTOS
# ==========================================

def registrar_pago(db: Session, cotizacion_id: int, pago_data: schemas.PagoCreate, tenant_id: int):
    """
    Registra un pago/adelanto para una cotización.
    
    REGLAS DE NEGOCIO:
    a) Crea el registro en tabla pagos.
    b) Suma monto_pagado al campo monto_pagado de la Cotización padre.
    c) Recalcula saldo_pendiente = total_venta - monto_pagado.
    d) Todo en una sola transacción atómica.
    """
    from decimal import Decimal
    
    # Obtener cotización
    db_cot = db.query(models.Cotizacion).filter(
        models.Cotizacion.id == cotizacion_id
    ).first()
    
    if not db_cot:
        raise ValueError("Cotización no encontrada")
    
    # Validar que el pago no exceda el saldo pendiente
    saldo_actual = (db_cot.total_venta or Decimal("0")) - (db_cot.monto_pagado or Decimal("0"))
    monto = Decimal(str(pago_data.monto_pagado))
    
    if monto > saldo_actual:
        raise ValueError(
            f"El monto ({monto}) excede el saldo pendiente ({saldo_actual}). "
            f"Total venta: {db_cot.total_venta}, Ya pagado: {db_cot.monto_pagado}"
        )
    
    # a) Crear registro de pago
    db_pago = models.Pago(
        tenant_id=tenant_id,
        cotizacion_id=cotizacion_id,
        monto_pagado=monto,
        metodo_pago=pago_data.metodo_pago,
        referencia_operacion=pago_data.referencia_operacion,
        tipo=pago_data.tipo
    )
    
    # b) Actualizar monto_pagado de la cotización
    nuevo_pagado = (db_cot.monto_pagado or Decimal("0")) + monto
    db_cot.monto_pagado = nuevo_pagado
    
    # c) Recalcular saldo_pendiente
    db_cot.saldo_pendiente = (db_cot.total_venta or Decimal("0")) - nuevo_pagado
    
    # d) Transacción atómica
    try:
        db.add(db_pago)
        db.commit()
        db.refresh(db_pago)
        db.refresh(db_cot)
        return db_pago
    except Exception as e:
        db.rollback()
        raise e

def get_pagos_cotizacion(db: Session, cotizacion_id: int):
    """Obtiene todos los pagos de una cotización."""
    return db.query(models.Pago).filter(
        models.Pago.cotizacion_id == cotizacion_id
    ).order_by(models.Pago.fecha_pago.desc()).all()

# ==========================================
# GESTIÓN DE PROVEEDORES (BROKER)
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
    if not db_proveedor: return None
    for var, value in proveedor.model_dump(exclude_unset=True).items():
        setattr(db_proveedor, var, value)
    db.commit()
    db.refresh(db_proveedor)
    return db_proveedor

def delete_proveedor(db: Session, proveedor_id: int, tenant_id: int):
    db_proveedor = db.query(models.Proveedor).filter(models.Proveedor.id == proveedor_id, models.Proveedor.tenant_id == tenant_id).first()
    if not db_proveedor: return False
    db.delete(db_proveedor)
    db.commit()
    return True

# ==========================================
# MOTOR DE PRODUCCIÓN (MRP / BOM)
# ==========================================

def get_insumos(db: Session, tenant_id: int, skip: int = 0, limit: int = 100):
    """Obtiene el catálogo de Insumos/Materia Prima"""
    return db.query(models.Insumo).filter(
        models.Insumo.tenant_id == tenant_id
    ).offset(skip).limit(limit).all()

def create_insumo(db: Session, insumo: schemas.InsumoCreate, tenant_id: int):
    """Registra una nueva Materia Prima/Insumo en el Tenant M"""
    db_insumo = models.Insumo(
        tenant_id=tenant_id,
        nombre=insumo.nombre,
        unidad_compra=insumo.unidad_compra,
        unidad_consumo=insumo.unidad_consumo,
        factor_conversion=insumo.factor_conversion,
        costo_promedio=insumo.costo_promedio,
        stock_actual=insumo.stock_actual
    )
    db.add(db_insumo)
    db.commit()
    db.refresh(db_insumo)
    return db_insumo

def get_recetas_producto(db: Session, producto_id: int):
    """Obtiene la BOM de un Producto"""
    return db.query(models.RecetaBOM).filter(
        models.RecetaBOM.producto_id == producto_id
    ).all()

def create_receta_bom(db: Session, receta: schemas.RecetaBOMCreate, tenant_id: int):
    """Añade un Insumo a la BOM de un Producto"""
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

def generar_orden_produccion(db: Session, cotizacion_id: int, tenant_id: int, tipo_produccion: str = "interna", proveedor_id: int = None, costo_tercerizado = None):
    """
    Ruta Crítica MRP: Genera la orden de trabajo calculando requerimientos de material
    basados en lo vendido (Cotización) multiplicando la RecetaBOM + Mermas.
    Soporta asignación a talleres externos (Modelo Broker).
    """
    from decimal import Decimal
    
    # 1. Obtener la Cotización y sus lineas
    db_cotizacion = db.query(models.Cotizacion).filter(
        models.Cotizacion.id == cotizacion_id,
        models.Cotizacion.tenant_id == tenant_id
    ).first()
    
    if not db_cotizacion:
        raise ValueError("Cotización no encontrada o no pertenece al Tenant")
        
    # Evitar duplicidad de órdenes activas (opcional)
    orden_previa = db.query(models.OrdenProduccion).filter(
        models.OrdenProduccion.cotizacion_id == cotizacion_id
    ).first()
    if orden_previa:
        raise ValueError(f"Ya existe una Orden de Producción (ID: {orden_previa.id}) para este documento.")

    # 2. Iniciar Cabecera de Orden Producción
    db_orden = models.OrdenProduccion(
        tenant_id=tenant_id,
        cotizacion_id=cotizacion_id,
        estado="en_cola",
        tipo_produccion=tipo_produccion,
        proveedor_id=proveedor_id,
        costo_tercerizado=costo_tercerizado
    )
    db.add(db_orden)
    db.flush() # Flush para obtener el orden_id sin auto-commit total

    # 3. Explotar la Lista de Materiales (BOM)
    for item in db_cotizacion.items:
        if not item.producto_id:
            continue # Si hay item sin ID producto base, ignora
            
        # Buscar recetas vinculadas al producto
        recetas = db.query(models.RecetaBOM).filter(
            models.RecetaBOM.producto_id == item.producto_id
        ).all()
        
        # Calcular los consumos a partir de la BOM
        cantidad_vendida = Decimal(str(item.cantidad))
        for receta in recetas:
            cant_base = Decimal(str(receta.cantidad_base_necesaria))
            merma_pct = Decimal(str(receta.porcentaje_merma_estandar)) / Decimal("100")
            
            # MATEMÁTICA DEL MOTOR MRP:
            neta = cantidad_vendida * cant_base
            merma = neta * merma_pct
            total = neta + merma
            
            # Insertar necesidad teórica a descontar
            db_detalle = models.OrdenProduccionDetalle(
                orden_id=db_orden.id,
                insumo_id=receta.insumo_id,
                cantidad_requerida_neta=neta,
                cantidad_merma=merma,
                cantidad_total_descontar=total
            )
            db.add(db_detalle)
            
    # Commit Atómico (Cabecera + Todos los detalles MRP generados)
    try:
        db.commit()
        db.refresh(db_orden)
        return db_orden
    except Exception as e:
        db.rollback()
        raise e

# ==========================================
# FASE 8: BUSINESS INTELLIGENCE Y ALERTAS
# ==========================================

def get_dashboard_stats(db: Session, tenant_id: int):
    from sqlalchemy import func
    
    ingresos = db.query(func.sum(models.Pago.monto_pagado)).filter(models.Pago.tenant_id == tenant_id).scalar() or 0
    saldos = db.query(func.sum(models.Cotizacion.saldo_pendiente)).filter(models.Cotizacion.tenant_id == tenant_id).scalar() or 0
    costos = db.query(func.sum(models.OrdenProduccion.costo_tercerizado)).filter(models.OrdenProduccion.tenant_id == tenant_id).scalar() or 0
    
    top_productos_query = db.query(
        models.Producto.nombre
    ).join(
        models.CotizacionItem, models.Producto.id == models.CotizacionItem.producto_id
    ).join(
        models.Cotizacion, models.CotizacionItem.cotizacion_id == models.Cotizacion.id
    ).filter(
        models.Cotizacion.tenant_id == tenant_id
    ).group_by(
        models.Producto.id
    ).order_by(
        func.sum(models.CotizacionItem.cantidad).desc()
    ).limit(5).all()
    
    top_productos = [p.nombre for p in top_productos_query]
    
    return {
        "ingresos_totales": ingresos,
        "saldos_por_cobrar": saldos,
        "costos_tercerizacion": costos,
        "top_productos": top_productos
    }

def verificar_stock_y_generar_alertas(db: Session, tenant_id: int):
    """
    Background Task: Mapea insumos debajo de su umbral y genera alertas 
    únicas no resueltas.
    """
    insumos_criticos = db.query(models.Insumo).filter(
        models.Insumo.tenant_id == tenant_id,
        models.Insumo.stock_actual <= models.Insumo.umbral_minimo
    ).all()

    for insumo in insumos_criticos:
        alerta_existente = db.query(models.AlertaInventario).filter(
            models.AlertaInventario.insumo_id == insumo.id,
            models.AlertaInventario.resuelta == False
        ).first()

        if not alerta_existente:
            nueva_alerta = models.AlertaInventario(
                tenant_id=tenant_id,
                insumo_id=insumo.id,
                mensaje=f"STOCK CRÍTICO: {insumo.nombre} (Stock: {insumo.stock_actual} | Umbral: {insumo.umbral_minimo})",
                resuelta=False
            )
            db.add(nueva_alerta)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error generando alertas de inventario: {e}")