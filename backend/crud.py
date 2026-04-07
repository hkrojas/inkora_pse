from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from passlib.context import CryptContext
from typing import List, Optional

from access_control import can_access_all_tenant_resources, normalize_role
import models
import schemas
import calculations 
from services.document_flow_service import (
    DOCUMENT_KIND_CREDIT_NOTE,
    DOCUMENT_KIND_DEBIT_NOTE,
    DOCUMENT_KIND_FISCAL_DOCUMENT,
    DOCUMENT_KIND_QUOTATION,
    DOCUMENT_STATUS_ISSUED,
    DOCUMENT_STATUS_PENDING,
    DOCUMENT_STATUS_VOIDED,
    build_internal_order_number,
    get_document_kind_for_note,
    is_fiscal_document,
    is_fiscal_family_document,
    is_note_document,
    is_quote_document,
    resolve_source_quote_id,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ==========================================
# USUARIOS
# ==========================================

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).options(joinedload(models.User.tenant)).filter(models.User.email == email).first()

def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).options(joinedload(models.User.tenant)).filter(models.User.id == user_id).first()

def create_user(
    db: Session,
    user: schemas.UserRegisterRequest,
    *,
    forced_role: str = "vendedor",
    is_superadmin: bool = False,
):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        nombre_completo=user.nombre_completo,
        rol=normalize_role(forced_role),
        is_superadmin=is_superadmin,
        tenant_id=user.tenant_id  # MULTITENANCIA
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return get_user_by_id(db, db_user.id)

# ==========================================
# TENANTS
# ==========================================

def get_tenant(db: Session, tenant_id: int):
    return db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()

def get_tenant_by_ruc(db: Session, business_ruc: str):
    return db.query(models.Tenant).filter(models.Tenant.business_ruc == business_ruc).first()

def create_tenant(db: Session, tenant: schemas.TenantCreate):
    if get_tenant_by_ruc(db, tenant.business_ruc):
        raise ValueError("Ya existe una empresa registrada con ese RUC.")

    db_tenant = models.Tenant(**tenant.model_dump())
    try:
        db.add(db_tenant)
        db.flush()  # obtener id antes del commit
        # Auto-crear suscripcion en estado trial para nuevos tenants
        sub = models.Subscription(tenant_id=db_tenant.id)
        db.add(sub)
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


def _get_tenant_resource(db: Session, model, resource_id: int, tenant_id: int):
    return db.query(model).filter(
        model.id == resource_id,
        model.tenant_id == tenant_id,
    ).first()


def get_cliente_for_tenant(db: Session, cliente_id: int, tenant_id: int):
    return _get_tenant_resource(db, models.Cliente, cliente_id, tenant_id)


def get_producto_for_tenant(db: Session, producto_id: int, tenant_id: int):
    return _get_tenant_resource(db, models.Producto, producto_id, tenant_id)


def _clone_cotizacion_items(source_items):
    items_clonados = []
    for item in source_items:
        items_clonados.append(
            models.CotizacionItem(
                producto_id=item.producto_id,
                descripcion=item.descripcion,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                valor_unitario=item.valor_unitario,
                total_base_igv=item.total_base_igv,
                total_igv=item.total_igv,
                total_item=item.total_item,
                unidad_medida=item.unidad_medida,
                tipo_afectacion_igv=item.tipo_afectacion_igv,
            )
        )
    return items_clonados


def _next_correlativo_for_series(db: Session, tenant_id: int, serie: str) -> int:
    last_doc = db.query(models.Cotizacion).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.serie == serie,
    ).order_by(models.Cotizacion.correlativo.desc()).with_for_update().first()
    ultimo_correlativo = last_doc.correlativo if last_doc else 0
    return ultimo_correlativo + 1


def get_source_quote(db: Session, document: models.Cotizacion | None):
    if not document:
        return None
    if is_quote_document(document):
        return document
    source_quote_id = resolve_source_quote_id(document)
    if not source_quote_id:
        return None
    return _get_tenant_resource(db, models.Cotizacion, source_quote_id, document.tenant_id)


def get_latest_fiscal_document_for_quote(db: Session, quote_id: int, tenant_id: int):
    return db.query(models.Cotizacion).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.source_quote_id == quote_id,
        models.Cotizacion.document_kind == DOCUMENT_KIND_FISCAL_DOCUMENT,
        models.Cotizacion.estado != DOCUMENT_STATUS_VOIDED,
    ).order_by(models.Cotizacion.id.desc()).first()


def resolve_fiscal_document_reference(db: Session, document_id: int, tenant_id: int):
    document = _get_tenant_resource(db, models.Cotizacion, document_id, tenant_id)
    if not document:
        return None
    if is_fiscal_family_document(document):
        return document
    if is_quote_document(document):
        return get_latest_fiscal_document_for_quote(db, document.id, tenant_id)
    return None


def resolve_payment_anchor_document(db: Session, document_id: int, tenant_id: int):
    document = _get_tenant_resource(db, models.Cotizacion, document_id, tenant_id)
    if not document:
        return None, None

    source_quote = get_source_quote(db, document)
    fiscal_document = document if is_fiscal_document(document) else None

    if source_quote and fiscal_document is None:
        fiscal_document = get_latest_fiscal_document_for_quote(db, source_quote.id, tenant_id)

    return source_quote, fiscal_document

# ==========================================
# CLIENTES
# ==========================================

def get_clientes(
    db: Session,
    tenant_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    q: str | None = None,
):
    """Lista clientes con búsqueda opcional por nombre, documento o nombre comercial."""
    from sqlalchemy import or_
    query = db.query(models.Cliente)
    if tenant_id is not None:
        query = query.filter(models.Cliente.tenant_id == tenant_id)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                models.Cliente.razon_social.ilike(term),
                models.Cliente.numero_documento.ilike(term),
                models.Cliente.nombre_comercial.ilike(term),
                models.Cliente.contacto.ilike(term),
            )
        )
    return query.order_by(models.Cliente.razon_social).offset(skip).limit(limit).all()

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

def update_cliente(db: Session, cliente_id: int, cliente_data: schemas.ClienteCreate, tenant_id: int):
    """Actualización completa (PUT) de un cliente."""
    db_cliente = get_cliente_for_tenant(db, cliente_id, tenant_id)
    if db_cliente:
        for key, value in cliente_data.model_dump().items():
            setattr(db_cliente, key, value)
        db.commit()
        db.refresh(db_cliente)
    return db_cliente

def patch_cliente(db: Session, cliente_id: int, updates: dict, tenant_id: int):
    """Actualización parcial (PATCH) de un cliente."""
    db_cliente = get_cliente_for_tenant(db, cliente_id, tenant_id)
    if not db_cliente:
        return None
    for key, value in updates.items():
        setattr(db_cliente, key, value)
    db.commit()
    db.refresh(db_cliente)
    return db_cliente

def delete_cliente(db: Session, cliente_id: int, tenant_id: int):
    db_cliente = get_cliente_for_tenant(db, cliente_id, tenant_id)
    if db_cliente:
        db.delete(db_cliente)
        db.commit()
    return db_cliente

# ==========================================
# PRODUCTOS
# ==========================================

def get_productos(
    db: Session,
    tenant_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    q: str | None = None,
):
    """Lista productos con búsqueda opcional por nombre, código o descripción."""
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

# ==========================================
# COTIZACIONES
# ==========================================

def get_cotizaciones(db: Session, usuario: Optional[models.User] = None, skip: int = 0, limit: int = 100):
    query = db.query(models.Cotizacion)\
        .options(
            joinedload(models.Cotizacion.cliente),
            joinedload(models.Cotizacion.usuario).joinedload(models.User.tenant),
            joinedload(models.Cotizacion.derived_documents),
        )\
        .filter(models.Cotizacion.source_quote_id.is_(None))\
        .order_by(desc(models.Cotizacion.id))
    if usuario and getattr(usuario, "tenant_id", None):
        query = query.filter(models.Cotizacion.tenant_id == usuario.tenant_id)
    if usuario and not can_access_all_tenant_resources(usuario):
        query = query.filter(models.Cotizacion.usuario_id == usuario.id)
    return query.offset(skip).limit(limit).all()

def get_cotizacion(db: Session, cotizacion_id: int, usuario: Optional[models.User] = None):
    query = db.query(models.Cotizacion)\
        .options(
            joinedload(models.Cotizacion.cliente),
            joinedload(models.Cotizacion.items),
            joinedload(models.Cotizacion.usuario).joinedload(models.User.tenant),
            joinedload(models.Cotizacion.derived_documents),
            joinedload(models.Cotizacion.source_quote),
        )\
        .filter(models.Cotizacion.id == cotizacion_id)
    if usuario and getattr(usuario, "tenant_id", None):
        query = query.filter(models.Cotizacion.tenant_id == usuario.tenant_id)
    if usuario and not can_access_all_tenant_resources(usuario):
        query = query.filter(models.Cotizacion.usuario_id == usuario.id)
    return query.first()

def get_cotizacion_by_uuid(db: Session, uuid_publico: str):
    """BÃºsqueda pÃºblica por UUID (Fase 3)."""
    return db.query(models.Cotizacion)\
        .options(joinedload(models.Cotizacion.cliente), joinedload(models.Cotizacion.tenant))\
        .filter(models.Cotizacion.uuid_publico == uuid_publico)\
        .first()

def create_cotizacion(db: Session, cotizacion: schemas.CotizacionCreate, usuario_id: int, tenant_id: int):
    db_cliente = get_cliente_for_tenant(db, cotizacion.cliente_id, tenant_id)
    if not db_cliente:
        raise ValueError("Cliente no encontrado o no pertenece al tenant actual.")

    items_db = []
    items_procesados_para_suma = []

    for item in cotizacion.items:
        db_producto = None
        if item.producto_id is not None:
            db_producto = get_producto_for_tenant(db, item.producto_id, tenant_id)
            if not db_producto:
                raise ValueError(
                    "Uno de los productos no existe o no pertenece al tenant actual."
                )

        # unidad_medida y tipo_afectacion_igv: item > producto > default
        unidad_medida = (
            item.unidad_medida
            or (db_producto.unidad_medida if db_producto else None)
            or "NIU"
        )
        tipo_afectacion_igv = (
            item.tipo_afectacion_igv
            or (db_producto.tipo_afectacion_igv if db_producto else None)
            or "10"
        )

        calculo = calculations.calcular_item(
            cantidad=item.cantidad,
            precio_con_igv=item.precio_unitario,
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
            unidad_medida=unidad_medida,
            tipo_afectacion_igv=tipo_afectacion_igv,
        )
        items_db.append(db_item)
        items_procesados_para_suma.append(calculo)

    totales = calculations.sumarizar_cotizacion(items_procesados_para_suma)

    # ---------------------------------------------------------
    # BLOQUEO TRANSACCIONAL: PrevenciÃ³n de Race Conditions (Fase 5)
    # ---------------------------------------------------------
    # Bloqueamos la Ãºltima fila de la serie para este tenant especÃ­fico
    # Asegura que 2 hilos concurrentes no lean el mismo MAX(correlativo)
    last_doc = db.query(models.Cotizacion).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.serie == "COT"
    ).order_by(
        models.Cotizacion.correlativo.desc()
    ).with_for_update().first()
    
    ultimo_correlativo = last_doc.correlativo if last_doc else 0
    nuevo_correlativo = ultimo_correlativo + 1
    internal_order_number = build_internal_order_number(tenant_id, nuevo_correlativo)
    # ---------------------------------------------------------

    # condicion_pago: toma el de la cotizacion o hereda del cliente
    condicion_pago = (
        getattr(cotizacion, "condicion_pago", None)
        or getattr(db_cliente, "condicion_pago", None)
    )

    db_cotizacion = models.Cotizacion(
        cliente_id=db_cliente.id,
        usuario_id=usuario_id,
        tenant_id=tenant_id,
        fecha_vencimiento=cotizacion.fecha_vencimiento,
        moneda=cotizacion.moneda,
        tipo_comprobante=cotizacion.tipo_comprobante,
        document_kind=DOCUMENT_KIND_QUOTATION,
        internal_order_number=internal_order_number,
        correlativo=nuevo_correlativo,
        serie="COT",
        observaciones=getattr(cotizacion, "observaciones", None),
        condicion_pago=condicion_pago,
        total_gravada=totales["total_gravada"],
        total_exonerada=totales["total_exonerada"],
        total_inafecta=totales["total_inafecta"],
        total_igv=totales["total_igv"],
        total_venta=totales["total_venta"],
        items=items_db,
    )

    try:
        db.add(db_cotizacion)
        db.commit()
        db.refresh(db_cotizacion)
        return get_cotizacion(db, db_cotizacion.id)
    except Exception as e:
        db.rollback()
        raise e


def create_fiscal_document_from_quote(
    db: Session,
    quote: models.Cotizacion,
    usuario_id: int,
    tipo_comprobante: str,
):
    if not is_quote_document(quote):
        raise ValueError("Solo se puede facturar una cotizacion comercial.")

    fiscal_document_existente = get_latest_fiscal_document_for_quote(
        db,
        quote.id,
        quote.tenant_id,
    )
    if fiscal_document_existente:
        raise ValueError("La cotizacion ya tiene un documento fiscal asociado.")

    serie = "F001" if tipo_comprobante == "01" else "B001"
    nuevo_correlativo = _next_correlativo_for_series(db, quote.tenant_id, serie)
    items_documento = _clone_cotizacion_items(quote.items)

    fiscal_document = models.Cotizacion(
        serie=serie,
        correlativo=nuevo_correlativo,
        cliente_id=quote.cliente_id,
        usuario_id=usuario_id,
        tenant_id=quote.tenant_id,
        fecha_vencimiento=quote.fecha_vencimiento,
        moneda=quote.moneda,
        tipo_comprobante=tipo_comprobante,
        estado=DOCUMENT_STATUS_PENDING,
        document_kind=DOCUMENT_KIND_FISCAL_DOCUMENT,
        source_quote_id=quote.id,
        internal_order_number=quote.internal_order_number,
        total_gravada=quote.total_gravada,
        total_exonerada=quote.total_exonerada,
        total_inafecta=quote.total_inafecta,
        total_igv=quote.total_igv,
        total_venta=quote.total_venta,
        sujeta_detraccion=quote.sujeta_detraccion,
        porcentaje_detraccion=quote.porcentaje_detraccion,
        monto_detraccion=quote.monto_detraccion,
        cuenta_banco_nacion=quote.cuenta_banco_nacion,
        anticipos_deducidos=quote.anticipos_deducidos,
        total_anticipos=quote.total_anticipos,
        items=items_documento,
    )

    try:
        db.add(fiscal_document)
        db.flush()  # obtener id antes del commit
        # Fase 9: incrementar contador de documentos usados en la suscripcion
        sub = get_subscription_by_tenant(db, quote.tenant_id)
        if sub is not None:
            sub.documents_used = (sub.documents_used or 0) + 1
        db.commit()
        db.refresh(fiscal_document)
        return get_cotizacion(db, fiscal_document.id)
    except Exception as e:
        db.rollback()
        raise e

def guardar_respuesta_sunat(
    db: Session,
    cotizacion_id: int,
    data_sunat: dict,
    tenant_id: int | None = None,
):
    """Guarda los links devueltos por la API de FacturaciÃ³n en la cotizaciÃ³n"""
    query = db.query(models.Cotizacion).filter(models.Cotizacion.id == cotizacion_id)
    if tenant_id is not None:
        query = query.filter(models.Cotizacion.tenant_id == tenant_id)
    db_cot = query.first()
    if db_cot:
        links = data_sunat.get('links', {}) if data_sunat.get('links') else data_sunat.get('sunat_response', {}).get('links', {})
        if links:
            db_cot.sunat_xml_url = links.get('xml')
            db_cot.sunat_pdf_url = links.get('pdf')
            db_cot.sunat_cdr_url = links.get('cdr')
        
        db_cot.estado = DOCUMENT_STATUS_ISSUED
        db_cot.sunat_error = None
        
        # Guardar Serie y Correlativo si la API los asignÃ³ o modificÃ³
        if data_sunat.get('serie'): db_cot.serie = data_sunat.get('serie')
        if data_sunat.get('correlativo'): 
            try:
                db_cot.correlativo = int(data_sunat.get('correlativo'))
            except: pass

        if db_cot.source_quote_id:
            source_quote = _get_tenant_resource(
                db,
                models.Cotizacion,
                db_cot.source_quote_id,
                db_cot.tenant_id,
            )
            if source_quote:
                source_quote.estado = DOCUMENT_STATUS_ISSUED

        db.commit()
        db.refresh(db_cot)
    return db_cot

# ==========================================
# ANULACIÃ“N Y NOTAS DE CRÃ‰DITO/DÃ‰BITO
# ==========================================

def anular_cotizacion(db: Session, cotizacion_id: int, tenant_id: int | None = None):
    """Marca un comprobante como 'anulada' tras confirmaciÃ³n exitosa de SUNAT."""
    query = db.query(models.Cotizacion).filter(models.Cotizacion.id == cotizacion_id)
    if tenant_id is not None:
        query = query.filter(models.Cotizacion.tenant_id == tenant_id)
    db_cot = query.first()
    if not db_cot:
        return None
    try:
        db_cot.estado = DOCUMENT_STATUS_VOIDED
        if db_cot.source_quote_id:
            source_quote = _get_tenant_resource(
                db,
                models.Cotizacion,
                db_cot.source_quote_id,
                db_cot.tenant_id,
            )
            if source_quote:
                fiscal_document_restante = get_latest_fiscal_document_for_quote(
                    db,
                    source_quote.id,
                    source_quote.tenant_id,
                )
                if (
                    not fiscal_document_restante
                    or fiscal_document_restante.id == db_cot.id
                    or fiscal_document_restante.estado == DOCUMENT_STATUS_VOIDED
                ):
                    source_quote.estado = DOCUMENT_STATUS_PENDING
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
    Crea un nuevo registro de Cotizacion que representa la Nota de CrÃ©dito (07) o DÃ©bito (08),
    clonando los items del documento afectado y vinculÃ¡ndolo via nota_referencia_id.
    """
    # Determinar tipo de comprobante y serie
    tipo_comprobante = "07" if tipo_nota == "credito" else "08"
    document_kind = get_document_kind_for_note(tipo_nota)
    serie_origen = doc_afectado.serie  # Ej: F001, B001
    serie_nota = "FC01" if serie_origen.startswith("F") else "BC01"

    # ---------------------------------------------------------
    # BLOQUEO TRANSACCIONAL: PrevenciÃ³n de Race Conditions (Fase 5)
    # ---------------------------------------------------------
    last_doc = db.query(models.Cotizacion).filter(
        models.Cotizacion.tenant_id == doc_afectado.tenant_id,
        models.Cotizacion.serie == serie_nota
    ).order_by(models.Cotizacion.correlativo.desc())\
    .with_for_update().first()
    
    ultimo_correlativo = last_doc.correlativo if last_doc else 0
    nuevo_correlativo = ultimo_correlativo + 1
    # ---------------------------------------------------------

    source_quote_id = resolve_source_quote_id(doc_afectado)
    items_nota = _clone_cotizacion_items(doc_afectado.items)

    # Crear registro de la nota
    db_nota = models.Cotizacion(
        serie=serie_nota,
        correlativo=nuevo_correlativo,
        cliente_id=doc_afectado.cliente_id,
        usuario_id=usuario_id,
        tenant_id=doc_afectado.tenant_id,  # MULTITENANCIA: hereda del doc afectado
        moneda=doc_afectado.moneda,
        tipo_comprobante=tipo_comprobante,
        estado=DOCUMENT_STATUS_PENDING,
        document_kind=document_kind,
        source_quote_id=source_quote_id,
        internal_order_number=doc_afectado.internal_order_number,
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
# GUÃAS DE REMISIÃ“N
# ==========================================

def get_guias_remision(db: Session, usuario: models.User = None, skip: int = 0, limit: int = 100):
    query = db.query(models.GuiaRemision)\
        .options(joinedload(models.GuiaRemision.items))\
        .order_by(desc(models.GuiaRemision.id))
    if usuario and getattr(usuario, "tenant_id", None):
        query = query.filter(models.GuiaRemision.tenant_id == usuario.tenant_id)
    if usuario and not can_access_all_tenant_resources(usuario):
        query = query.filter(models.GuiaRemision.usuario_id == usuario.id)
    return query.offset(skip).limit(limit).all()

def get_guia_remision(db: Session, guia_id: int, usuario: models.User = None):
    query = db.query(models.GuiaRemision)\
        .options(joinedload(models.GuiaRemision.items))\
        .filter(models.GuiaRemision.id == guia_id)
    if usuario and getattr(usuario, "tenant_id", None):
        query = query.filter(models.GuiaRemision.tenant_id == usuario.tenant_id)
    if usuario and not can_access_all_tenant_resources(usuario):
        query = query.filter(models.GuiaRemision.usuario_id == usuario.id)
    return query.first()

def create_guia_remision(db: Session, data: dict, usuario_id: int, tenant_id: int):
    """Crea una GuÃ­a de RemisiÃ³n con sus items."""
    items_data = data.pop("items", [])
    cotizacion_id = data.get("cotizacion_id")
    source_quote_id = None
    fiscal_document_id = None
    internal_order_number = None
    if cotizacion_id is not None:
        cotizacion = _get_tenant_resource(db, models.Cotizacion, cotizacion_id, tenant_id)
        if not cotizacion:
            raise ValueError("La cotizacion de origen no existe o no pertenece al tenant actual.")

        source_quote = get_source_quote(db, cotizacion)
        if source_quote:
            source_quote_id = source_quote.id
            internal_order_number = source_quote.internal_order_number

        if is_fiscal_document(cotizacion):
            fiscal_document_id = cotizacion.id
        elif source_quote_id:
            fiscal_document = get_latest_fiscal_document_for_quote(db, source_quote_id, tenant_id)
            if fiscal_document:
                fiscal_document_id = fiscal_document.id

    serie = data.get("serie") or "T001"
    
    # ---------------------------------------------------------
    # BLOQUEO TRANSACCIONAL: PrevenciÃ³n de Race Conditions (Fase 5)
    # ---------------------------------------------------------
    last_guia = db.query(models.GuiaRemision).filter(
        models.GuiaRemision.tenant_id == tenant_id,
        models.GuiaRemision.serie == serie
    ).order_by(models.GuiaRemision.correlativo.desc())\
    .with_for_update().first()
    
    ultimo_correlativo_guia = last_guia.correlativo if last_guia else 0
    nuevo_correlativo = ultimo_correlativo_guia + 1
    # ---------------------------------------------------------
    
    items_db = [models.GuiaRemisionItem(**item) for item in items_data]
    
    db_guia = models.GuiaRemision(
        **data,
        serie=serie,
        source_quote_id=source_quote_id,
        fiscal_document_id=fiscal_document_id,
        internal_order_number=internal_order_number,
        usuario_id=usuario_id,
        tenant_id=tenant_id,  # MULTITENANCIA
        correlativo=nuevo_correlativo,
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

def guardar_respuesta_sunat_gre(
    db: Session,
    guia_id: int,
    data_sunat: dict,
    tenant_id: int | None = None,
):
    """Guarda la respuesta SUNAT en una GuÃ­a de RemisiÃ³n."""
    query = db.query(models.GuiaRemision).filter(models.GuiaRemision.id == guia_id)
    if tenant_id is not None:
        query = query.filter(models.GuiaRemision.tenant_id == tenant_id)
    db_guia = query.first()
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
    Registra un pago/adelanto para una cotizaciÃ³n.
    
    REGLAS DE NEGOCIO:
    a) Crea el registro en tabla pagos.
    b) Suma monto_pagado al campo monto_pagado de la CotizaciÃ³n padre.
    c) Recalcula saldo_pendiente = total_venta - monto_pagado.
    d) Todo en una sola transacciÃ³n atÃ³mica.
    """
    from decimal import Decimal

    # Verificar el documento original ANTES de resolver el ancla.
    # Si se pasa el id de una nota de crédito/débito directamente, rechazarlo.
    _raw_doc = _get_tenant_resource(db, models.Cotizacion, cotizacion_id, tenant_id)
    if _raw_doc and is_note_document(_raw_doc):
        raise ValueError("No se pueden registrar pagos sobre notas de credito o debito.")

    source_quote, fiscal_document = resolve_payment_anchor_document(db, cotizacion_id, tenant_id)
    if not source_quote:
        raise ValueError("Cotizacion no encontrada")
    if is_note_document(fiscal_document):
        raise ValueError("No se pueden registrar pagos sobre notas de credito o debito.")
    if fiscal_document and fiscal_document.estado == DOCUMENT_STATUS_VOIDED:
        raise ValueError("No se pueden registrar pagos sobre comprobantes anulados.")
    
    # Validar que el pago no exceda el saldo pendiente
    saldo_actual = (source_quote.total_venta or Decimal("0")) - (source_quote.monto_pagado or Decimal("0"))
    monto = Decimal(str(pago_data.monto_pagado))
    
    if monto > saldo_actual:
        raise ValueError(
            f"El monto ({monto}) excede el saldo pendiente ({saldo_actual}). "
            f"Total venta: {source_quote.total_venta}, Ya pagado: {source_quote.monto_pagado}"
        )
    
    # a) Crear registro de pago
    from datetime import datetime as _dt
    fecha_pago = getattr(pago_data, "fecha_pago", None) or _dt.now()
    db_pago = models.Pago(
        tenant_id=tenant_id,
        cotizacion_id=source_quote.id,
        source_quote_id=source_quote.id,
        fiscal_document_id=getattr(fiscal_document, "id", None),
        internal_order_number=source_quote.internal_order_number,
        monto_pagado=monto,
        metodo_pago=pago_data.metodo_pago,
        fecha_pago=fecha_pago,
        referencia_operacion=pago_data.referencia_operacion,
        tipo=pago_data.tipo,
    )
    
    # b) Actualizar monto_pagado de la cotizaciÃ³n
    nuevo_pagado = (source_quote.monto_pagado or Decimal("0")) + monto
    source_quote.monto_pagado = nuevo_pagado
    
    # c) Recalcular saldo_pendiente
    source_quote.saldo_pendiente = (source_quote.total_venta or Decimal("0")) - nuevo_pagado
    
    # d) TransacciÃ³n atÃ³mica
    try:
        db.add(db_pago)
        db.commit()
        db.refresh(db_pago)
        db.refresh(source_quote)
        return db_pago
    except Exception as e:
        db.rollback()
        raise e

def get_pagos_cotizacion(db: Session, cotizacion_id: int, tenant_id: int):
    """Obtiene todos los pagos de una cotizaciÃ³n."""
    source_quote, _ = resolve_payment_anchor_document(db, cotizacion_id, tenant_id)
    if not source_quote:
        return []
    return db.query(models.Pago).filter(
        models.Pago.cotizacion_id == source_quote.id,
        models.Pago.tenant_id == tenant_id,
    ).order_by(models.Pago.fecha_pago.desc()).all()

# ==========================================
# GESTIÃ“N DE PROVEEDORES (BROKER)
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
# MOTOR DE PRODUCCIÃ“N (MRP / BOM)
# ==========================================

def get_insumos(db: Session, tenant_id: int, skip: int = 0, limit: int = 100):
    """Obtiene el catÃ¡logo de Insumos/Materia Prima"""
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
        stock_actual=insumo.stock_actual,
        umbral_minimo=insumo.umbral_minimo
    )
    db.add(db_insumo)
    db.commit()
    db.refresh(db_insumo)
    return db_insumo

def update_insumo(db: Session, insumo_id: int, insumo_data: schemas.InsumoCreate, tenant_id: int):
    """Actualiza una Materia Prima/Insumo del tenant actual"""
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
    """Elimina una Materia Prima/Insumo del tenant actual"""
    db_insumo = db.query(models.Insumo).filter(
        models.Insumo.id == insumo_id,
        models.Insumo.tenant_id == tenant_id
    ).first()
    if db_insumo:
        db.delete(db_insumo)
        db.commit()
    return db_insumo

def get_recetas_producto(db: Session, producto_id: int, tenant_id: int):
    """Obtiene la BOM de un Producto. Filtra por tenant para evitar lectura cruzada."""
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
    """AÃ±ade un Insumo a la BOM de un Producto"""
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

def get_ordenes_produccion(db: Session, tenant_id: int, skip: int = 0, limit: int = 100):
    """Lectura de Todas las Ã“rdenes Taller/TercerizaciÃ³n activos."""
    return db.query(models.OrdenProduccion).filter(
        models.OrdenProduccion.tenant_id == tenant_id
    ).options(
        joinedload(models.OrdenProduccion.detalles),
        joinedload(models.OrdenProduccion.proveedor)
    ).order_by(models.OrdenProduccion.id.desc()).offset(skip).limit(limit).all()

def generar_orden_produccion(db: Session, cotizacion_id: int, tenant_id: int, tipo_produccion: str = "interna", proveedor_id: int = None, costo_tercerizado = None):
    """
    Ruta CrÃ­tica MRP: Genera la orden de trabajo calculando requerimientos de material
    basados en lo vendido (CotizaciÃ³n) multiplicando la RecetaBOM + Mermas.
    Soporta asignaciÃ³n a talleres externos (Modelo Broker).
    """
    from decimal import Decimal
    
    # 1. Obtener la CotizaciÃ³n y sus lineas
    db_cotizacion = db.query(models.Cotizacion).filter(
        models.Cotizacion.id == cotizacion_id,
        models.Cotizacion.tenant_id == tenant_id
    ).first()
    
    if not db_cotizacion:
        raise ValueError("CotizaciÃ³n no encontrada o no pertenece al Tenant")
        
    # Evitar duplicidad de Ã³rdenes activas (opcional)
    orden_previa = db.query(models.OrdenProduccion).filter(
        models.OrdenProduccion.cotizacion_id == cotizacion_id
    ).first()
    if orden_previa:
        raise ValueError(f"Ya existe una Orden de ProducciÃ³n (ID: {orden_previa.id}) para este documento.")

    # 2. Iniciar Cabecera de Orden ProducciÃ³n
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
            
            # MATEMÃTICA DEL MOTOR MRP:
            neta = cantidad_vendida * cant_base
            merma = neta * merma_pct
            total = neta + merma
            
            # Insertar necesidad teÃ³rica a descontar
            db_detalle = models.OrdenProduccionDetalle(
                orden_id=db_orden.id,
                insumo_id=receta.insumo_id,
                cantidad_requerida_neta=neta,
                cantidad_merma=merma,
                cantidad_total_descontar=total
            )
            db.add(db_detalle)
            
    # Commit AtÃ³mico (Cabecera + Todos los detalles MRP generados)
    try:
        db.commit()
        db.refresh(db_orden)
        return db_orden
    except Exception as e:
        db.rollback()
        raise e

def update_orden_produccion_status(db: Session, orden_id: int, nuevo_estado: str, tenant_id: int):
    """Actualiza el estado de la OP y registra fecha de fin si aplica."""
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

# ==========================================
# FASE 8: BUSINESS INTELLIGENCE Y ALERTAS
# ==========================================

def get_dashboard_stats(db: Session, tenant_id: int):
    from sqlalchemy import func
    from datetime import datetime as _dt
    from decimal import Decimal as _D

    ingresos = db.query(func.sum(models.Pago.monto_pagado)).filter(
        models.Pago.tenant_id == tenant_id
    ).scalar() or _D("0")

    saldos = db.query(func.sum(models.Cotizacion.saldo_pendiente)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "quotation",
        models.Cotizacion.estado != "anulada",
    ).scalar() or _D("0")

    costos = db.query(func.sum(models.OrdenProduccion.costo_tercerizado)).filter(
        models.OrdenProduccion.tenant_id == tenant_id
    ).scalar() or _D("0")

    # Documentos vencidos: fecha_vencimiento pasada y saldo > 0
    ahora = _dt.now()
    vencidos_count = db.query(func.count(models.Cotizacion.id)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "quotation",
        models.Cotizacion.estado != "anulada",
        models.Cotizacion.fecha_vencimiento < ahora,
        models.Cotizacion.saldo_pendiente > 0,
    ).scalar() or 0

    saldo_vencido = db.query(func.sum(models.Cotizacion.saldo_pendiente)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "quotation",
        models.Cotizacion.estado != "anulada",
        models.Cotizacion.fecha_vencimiento < ahora,
        models.Cotizacion.saldo_pendiente > 0,
    ).scalar() or _D("0")

    # Documentos emitidos este mes (fiscal)
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    emitidos_mes = db.query(func.count(models.Cotizacion.id)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "fiscal_document",
        models.Cotizacion.estado == "facturada",
        models.Cotizacion.fecha_emision >= inicio_mes,
    ).scalar() or 0

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
        "saldo_vencido": saldo_vencido,
        "costos_tercerizacion": costos,
        "documentos_emitidos_mes": emitidos_mes,
        "documentos_vencidos": vencidos_count,
        "top_productos": top_productos,
    }


def get_cobranza_vencida(
    db: Session,
    tenant_id: int,
    skip: int = 0,
    limit: int = 100,
) -> list:
    """
    Lista cotizaciones con fecha_vencimiento superada y saldo pendiente > 0.
    Solo opera sobre cotizaciones (document_kind=quotation), no sobre documentos fiscales.
    """
    from datetime import datetime as _dt
    ahora = _dt.now()
    return (
        db.query(models.Cotizacion)
        .options(
            joinedload(models.Cotizacion.cliente),
        )
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.document_kind == "quotation",
            models.Cotizacion.estado != "anulada",
            models.Cotizacion.fecha_vencimiento < ahora,
            models.Cotizacion.saldo_pendiente > 0,
        )
        .order_by(models.Cotizacion.fecha_vencimiento.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_cobranza_resumen(db: Session, tenant_id: int) -> dict:
    """Resumen de cobranza para el panel."""
    from sqlalchemy import func
    from datetime import datetime as _dt
    from decimal import Decimal as _D
    ahora = _dt.now()
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    base = db.query(models.Cotizacion).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "quotation",
        models.Cotizacion.estado != "anulada",
    )

    total_por_cobrar = db.query(func.sum(models.Cotizacion.saldo_pendiente)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "quotation",
        models.Cotizacion.estado != "anulada",
        models.Cotizacion.saldo_pendiente > 0,
    ).scalar() or _D("0")

    total_vencido = db.query(func.sum(models.Cotizacion.saldo_pendiente)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "quotation",
        models.Cotizacion.estado != "anulada",
        models.Cotizacion.fecha_vencimiento < ahora,
        models.Cotizacion.saldo_pendiente > 0,
    ).scalar() or _D("0")

    total_pagado_mes = db.query(func.sum(models.Pago.monto_pagado)).filter(
        models.Pago.tenant_id == tenant_id,
        models.Pago.fecha_pago >= inicio_mes,
    ).scalar() or _D("0")

    docs_pendientes = db.query(func.count(models.Cotizacion.id)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "quotation",
        models.Cotizacion.estado != "anulada",
        models.Cotizacion.saldo_pendiente > 0,
        models.Cotizacion.fecha_vencimiento >= ahora,
    ).scalar() or 0

    docs_vencidos = db.query(func.count(models.Cotizacion.id)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "quotation",
        models.Cotizacion.estado != "anulada",
        models.Cotizacion.fecha_vencimiento < ahora,
        models.Cotizacion.saldo_pendiente > 0,
    ).scalar() or 0

    docs_pagados_mes = db.query(func.count(models.Cotizacion.id)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "quotation",
        models.Cotizacion.monto_pagado >= models.Cotizacion.total_venta,
        models.Cotizacion.total_venta > 0,
    ).scalar() or 0

    return {
        "total_por_cobrar": total_por_cobrar,
        "total_vencido": total_vencido,
        "total_pagado_mes": total_pagado_mes,
        "documentos_pendientes": docs_pendientes,
        "documentos_vencidos": docs_vencidos,
        "documentos_pagados_mes": docs_pagados_mes,
    }


def get_reporte_mensual(db: Session, tenant_id: int, anio: int, mes: int) -> list:
    """
    Devuelve todos los documentos fiscales emitidos en el mes dado.
    Útil para exportar a Excel para el contador.
    """
    from datetime import date
    inicio = date(anio, mes, 1)
    if mes == 12:
        fin = date(anio + 1, 1, 1)
    else:
        fin = date(anio, mes + 1, 1)

    return (
        db.query(models.Cotizacion)
        .options(
            joinedload(models.Cotizacion.cliente),
            joinedload(models.Cotizacion.items),
        )
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.document_kind == "fiscal_document",
            models.Cotizacion.estado != "anulada",
            models.Cotizacion.fecha_emision >= inicio,
            models.Cotizacion.fecha_emision < fin,
        )
        .order_by(models.Cotizacion.fecha_emision.asc())
        .all()
    )

def verificar_stock_y_generar_alertas(db: Session, tenant_id: int):
    """
    Background Task: Mapea insumos debajo de su umbral y genera alertas 
    Ãºnicas no resueltas.
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
                mensaje=f"STOCK CRÃTICO: {insumo.nombre} (Stock: {insumo.stock_actual} | Umbral: {insumo.umbral_minimo})",
                resuelta=False
            )
            db.add(nueva_alerta)

# ==========================================
# FASE 13: SUPERADMIN CONTROL TOWER
# ==========================================

def get_all_tenants(db: Session, skip: int = 0, limit: int = 100):
    """(GLOBAL) Lista todas las imprentas registradas."""
    return db.query(models.Tenant).order_by(models.Tenant.id.desc()).offset(skip).limit(limit).all()

def update_tenant_saas(db: Session, tenant_id: int, updates: dict):
    """(GLOBAL) Actualiza límites, planes o credenciales SUNAT."""
    db_tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not db_tenant:
        return None
    
    for key, value in updates.items():
        if value is not None:
            setattr(db_tenant, key, value)
    
    db.commit()
    db.refresh(db_tenant)
    return db_tenant

def delete_tenant(db: Session, tenant_id: int):
    """(GLOBAL) Elimina un tenant y todos sus datos."""
    db_tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not db_tenant:
        return None
    
    try:
        db.delete(db_tenant)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e

def get_all_users(db: Session, skip: int = 0, limit: int = 100):
    """(GLOBAL) Lista todos los usuarios del sistema."""
    return db.query(models.User).options(joinedload(models.User.tenant)).order_by(models.User.id.desc()).offset(skip).limit(limit).all()

def create_audit_log(db: Session, user_id: int, action: str, entity_type: str = None, entity_id: int = None, details: str = None, ip_address: str = None):
    """Crea un registro de auditoría."""
    log = models.AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address
    )
    db.add(log)
    db.commit()
    return log

def get_audit_logs(db: Session, skip: int = 0, limit: int = 100):
    """Obtiene todos los logs de auditoría."""
    return db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).offset(skip).limit(limit).all()


# ==========================================
# FASE 5: SUBSCRIPTION CRUD
# ==========================================
# Dominio SaaS: PrintFlow controla acceso y pagos de sus tenants.
# NO mezclar con Pago (dominio operativo del tenant hacia sus clientes).

def get_subscription_by_tenant(db: Session, tenant_id: int) -> models.Subscription | None:
    """Recupera la suscripcion SaaS de un tenant."""
    return (
        db.query(models.Subscription)
        .filter(models.Subscription.tenant_id == tenant_id)
        .first()
    )


def get_or_create_subscription(db: Session, tenant_id: int) -> models.Subscription:
    """Recupera o crea (en estado trial) la suscripcion de un tenant."""
    sub = get_subscription_by_tenant(db, tenant_id)
    if sub:
        return sub
    sub = models.Subscription(tenant_id=tenant_id)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def update_subscription_fields(
    db: Session,
    tenant_id: int,
    updates: dict,
) -> models.Subscription:
    """Actualiza campos arbitrarios de la suscripcion de un tenant."""
    sub = get_or_create_subscription(db, tenant_id)
    for key, value in updates.items():
        setattr(sub, key, value)
    db.commit()
    db.refresh(sub)
    return sub


def register_subscription_payment(
    db: Session,
    tenant_id: int,
    data: schemas.SubscriptionPaymentCreate,
    validated_by_user_id: int,
) -> models.SubscriptionPayment:
    """
    Registra un pago SaaS de un tenant a PrintFlow.
    Dominio exclusivo: NO es un pago de cliente al tenant.
    """
    from datetime import datetime as dt
    payment = models.SubscriptionPayment(
        tenant_id=tenant_id,
        amount=data.amount,
        currency=data.currency,
        method=data.method,
        reference=data.reference,
        paid_at=data.paid_at or dt.now(),
        validated_by_user_id=validated_by_user_id,
        notes=data.notes,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def get_subscription_payments(
    db: Session,
    tenant_id: int,
    skip: int = 0,
    limit: int = 50,
) -> list[models.SubscriptionPayment]:
    """Lista los pagos SaaS registrados para un tenant."""
    return (
        db.query(models.SubscriptionPayment)
        .filter(models.SubscriptionPayment.tenant_id == tenant_id)
        .order_by(models.SubscriptionPayment.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_all_tenants_with_subscription(
    db: Session,
    skip: int = 0,
    limit: int = 100,
) -> list[models.Tenant]:
    """Lista todos los tenants con su suscripcion cargada (para panel superadmin)."""
    from sqlalchemy.orm import joinedload
    return (
        db.query(models.Tenant)
        .options(joinedload(models.Tenant.subscription))
        .order_by(models.Tenant.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


# ============================================================
# FASE 9: BETA CERRADA — MÉTRICAS OPERATIVAS
# ============================================================

def get_tenant_actividad(db: Session, tenant_id: int) -> dict:
    """
    Devuelve métricas de uso operativo de un tenant para seguimiento de beta.
    Todas las queries son ligeras y apropiadas para 5-10 tenants piloto.
    """
    from datetime import datetime as _dt, timedelta
    from sqlalchemy import func

    tenant = get_tenant(db, tenant_id)
    if not tenant:
        return {}

    sub = get_subscription_by_tenant(db, tenant_id)

    clientes_count = db.query(func.count(models.Cliente.id)).filter(
        models.Cliente.tenant_id == tenant_id
    ).scalar() or 0

    productos_count = db.query(func.count(models.Producto.id)).filter(
        models.Producto.tenant_id == tenant_id
    ).scalar() or 0

    usuarios_count = db.query(func.count(models.User.id)).filter(
        models.User.tenant_id == tenant_id
    ).scalar() or 0

    cotizaciones_count = db.query(func.count(models.Cotizacion.id)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "quotation",
    ).scalar() or 0

    documentos_fiscales_count = db.query(func.count(models.Cotizacion.id)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind.in_(["fiscal_document", "credit_note", "debit_note"]),
    ).scalar() or 0

    hace_30_dias = _dt.now() - timedelta(days=30)
    documentos_fiscales_ultimo_mes = db.query(func.count(models.Cotizacion.id)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind.in_(["fiscal_document", "credit_note", "debit_note"]),
        models.Cotizacion.fecha_emision >= hace_30_dias,
    ).scalar() or 0

    guias_count = db.query(func.count(models.GuiaRemision.id)).filter(
        models.GuiaRemision.tenant_id == tenant_id
    ).scalar() or 0

    pagos_count = db.query(func.count(models.Pago.id)).filter(
        models.Pago.tenant_id == tenant_id
    ).scalar() or 0

    ultimo_fiscal = (
        db.query(models.Cotizacion)
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.document_kind.in_(["fiscal_document", "credit_note", "debit_note"]),
        )
        .order_by(models.Cotizacion.fecha_emision.desc())
        .first()
    )

    return {
        "tenant_id": tenant_id,
        "business_name": tenant.business_name,
        "business_ruc": tenant.business_ruc,
        "clientes_count": clientes_count,
        "productos_count": productos_count,
        "usuarios_count": usuarios_count,
        "cotizaciones_count": cotizaciones_count,
        "documentos_fiscales_count": documentos_fiscales_count,
        "documentos_fiscales_ultimo_mes": documentos_fiscales_ultimo_mes,
        "guias_count": guias_count,
        "pagos_count": pagos_count,
        "ultimo_documento_fiscal_fecha": getattr(ultimo_fiscal, "fecha_emision", None),
        "subscription_status": getattr(sub, "status", None),
        "onboarding_status": getattr(sub, "onboarding_status", None),
        "documents_used": getattr(sub, "documents_used", 0),
        "max_documents": getattr(sub, "max_documents", None),
    }


def get_beta_resumen_data(db: Session) -> list[dict]:
    """
    Devuelve resumen compacto de todos los tenants para el panel de operaciones beta.
    Optimizado para 5-10 tenants piloto; una query por tenant es aceptable.
    """
    from sqlalchemy import func

    tenants = db.query(models.Tenant).order_by(models.Tenant.id.desc()).all()
    result = []

    for tenant in tenants:
        sub = get_subscription_by_tenant(db, tenant.id)

        clientes_count = db.query(func.count(models.Cliente.id)).filter(
            models.Cliente.tenant_id == tenant.id
        ).scalar() or 0

        productos_count = db.query(func.count(models.Producto.id)).filter(
            models.Producto.tenant_id == tenant.id
        ).scalar() or 0

        usuarios_count = db.query(func.count(models.User.id)).filter(
            models.User.tenant_id == tenant.id
        ).scalar() or 0

        # Último pago SaaS
        ultimo_pago = (
            db.query(models.SubscriptionPayment)
            .filter(models.SubscriptionPayment.tenant_id == tenant.id)
            .order_by(models.SubscriptionPayment.paid_at.desc())
            .first()
        )

        result.append({
            "tenant_id": tenant.id,
            "business_name": tenant.business_name,
            "business_ruc": tenant.business_ruc,
            "is_active": tenant.is_active,
            "is_pilot": getattr(sub, "is_pilot", False) if sub else False,
            "subscription_status": getattr(sub, "status", None),
            "onboarding_status": getattr(sub, "onboarding_status", None),
            "plan_code": getattr(sub, "plan_code", None),
            "current_price": getattr(sub, "current_price", None),
            "founder_price": getattr(sub, "founder_price", None),
            "billing_due_at": getattr(sub, "billing_due_at", None),
            "documents_used": getattr(sub, "documents_used", 0),
            "max_documents": getattr(sub, "max_documents", None),
            "clientes_count": clientes_count,
            "productos_count": productos_count,
            "usuarios_count": usuarios_count,
            "ultimo_pago_saas_fecha": getattr(ultimo_pago, "paid_at", None) if ultimo_pago else None,
            "ultimo_pago_saas_monto": getattr(ultimo_pago, "amount", None) if ultimo_pago else None,
            "notes_internal": getattr(sub, "notes_internal", None),
        })

    return result


def check_document_limit(db: Session, tenant_id: int) -> None:
    """
    Verifica que el tenant no haya superado su límite de documentos fiscales.
    Lanza ValueError si el límite está alcanzado.
    Solo aplica si max_documents está definido en la suscripcion.
    """
    sub = get_subscription_by_tenant(db, tenant_id)
    if sub is None:
        return
    if sub.max_documents is None:
        return
    used = sub.documents_used or 0
    if used >= sub.max_documents:
        raise ValueError(
            f"Límite de documentos alcanzado: {used}/{sub.max_documents}. "
            "Contacte al administrador para ampliar su plan."
        )
