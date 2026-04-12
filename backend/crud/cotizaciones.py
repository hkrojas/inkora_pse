"""crud/cotizaciones.py — Cotizaciones, documentos fiscales, notas."""
from typing import Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

import models
import schemas
from access_control import can_access_all_tenant_resources
from services import calculations
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
    is_fiscal_family_document,
    is_quote_document,
    resolve_source_quote_id,
)
from crud._base import (
    _clone_cotizacion_items,
    _get_tenant_resource,
    _next_correlativo_for_series,
    get_latest_fiscal_document_for_quote,
)
from crud.tenants import get_subscription_by_tenant


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
    return db.query(models.Cotizacion)\
        .options(joinedload(models.Cotizacion.cliente), joinedload(models.Cotizacion.tenant))\
        .filter(models.Cotizacion.uuid_publico == uuid_publico)\
        .first()


def create_cotizacion(db: Session, cotizacion: schemas.CotizacionCreate, usuario_id: int, tenant_id: int):
    from crud._base import get_cliente_for_tenant, get_producto_for_tenant
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

    last_doc = db.query(models.Cotizacion).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.serie == "COT"
    ).order_by(
        models.Cotizacion.correlativo.desc()
    ).with_for_update().first()

    ultimo_correlativo = last_doc.correlativo if last_doc else 0
    nuevo_correlativo = ultimo_correlativo + 1
    internal_order_number = build_internal_order_number(tenant_id, nuevo_correlativo)

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
        saldo_pendiente=totales["total_venta"],
        items=items_db,
    )

    try:
        db.add(db_cotizacion)
        db.commit()
        db.refresh(db_cotizacion)
        # Ensure saldo_pendiente = total_venta on new quotations.
        # Server-side DEFAULT 0.0 can override the constructor value in pooled connections.
        if not db_cotizacion.saldo_pendiente or db_cotizacion.saldo_pendiente == 0:
            from sqlalchemy import text as _text
            db.execute(
                _text("UPDATE cotizaciones SET saldo_pendiente = :saldo WHERE id = :id"),
                {"saldo": float(totales["total_venta"]), "id": db_cotizacion.id},
            )
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
        db, quote.id, quote.tenant_id,
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
        db.flush()
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
    query = db.query(models.Cotizacion).filter(models.Cotizacion.id == cotizacion_id)
    if tenant_id is not None:
        query = query.filter(models.Cotizacion.tenant_id == tenant_id)
    db_cot = query.first()
    if db_cot:
        links = data_sunat.get("links", {}) if data_sunat.get("links") else data_sunat.get("sunat_response", {}).get("links", {})
        if links:
            db_cot.sunat_xml_url = links.get("xml")
            db_cot.sunat_pdf_url = links.get("pdf")
            db_cot.sunat_cdr_url = links.get("cdr")

        if data_sunat.get("success"):
            db_cot.estado = DOCUMENT_STATUS_ISSUED
            db_cot.sunat_error = None
        else:
            error = (
                data_sunat.get("sunat_error")
                or data_sunat.get("message")
                or data_sunat.get("sunat_response", {}).get("error")
                or data_sunat.get("provider_response", {}).get("error")
            )
            db_cot.sunat_error = str(error) if error else "El proveedor fiscal rechazo la emision."

        if data_sunat.get("serie"):
            db_cot.serie = data_sunat.get("serie")
        if data_sunat.get("correlativo"):
            try:
                db_cot.correlativo = int(data_sunat.get("correlativo"))
            except Exception:
                pass

        if data_sunat.get("success") and db_cot.source_quote_id:
            source_quote = _get_tenant_resource(
                db, models.Cotizacion, db_cot.source_quote_id, db_cot.tenant_id,
            )
            if source_quote:
                source_quote.estado = DOCUMENT_STATUS_ISSUED

        db.commit()
        db.refresh(db_cot)
    return db_cot


def guardar_error_sunat(
    db: Session,
    cotizacion_id: int,
    error: str,
    tenant_id: int | None = None,
):
    query = db.query(models.Cotizacion).filter(models.Cotizacion.id == cotizacion_id)
    if tenant_id is not None:
        query = query.filter(models.Cotizacion.tenant_id == tenant_id)
    db_cot = query.first()
    if db_cot:
        db_cot.sunat_error = str(error)
        db.commit()
        db.refresh(db_cot)
    return db_cot


def anular_cotizacion(db: Session, cotizacion_id: int, tenant_id: int | None = None):
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
                db, models.Cotizacion, db_cot.source_quote_id, db_cot.tenant_id,
            )
            if source_quote:
                fiscal_document_restante = get_latest_fiscal_document_for_quote(
                    db, source_quote.id, source_quote.tenant_id,
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
    tipo_nota: str,
    cod_motivo: str,
    descripcion_motivo: str
):
    tipo_comprobante = "07" if tipo_nota == "credito" else "08"
    document_kind = get_document_kind_for_note(tipo_nota)
    serie_origen = doc_afectado.serie
    serie_nota = "FF01" if serie_origen.startswith("F") else "BB01"

    last_doc = db.query(models.Cotizacion).filter(
        models.Cotizacion.tenant_id == doc_afectado.tenant_id,
        models.Cotizacion.serie == serie_nota
    ).order_by(models.Cotizacion.correlativo.desc()).with_for_update().first()

    ultimo_correlativo = last_doc.correlativo if last_doc else 0
    nuevo_correlativo = ultimo_correlativo + 1

    source_quote_id = resolve_source_quote_id(doc_afectado)
    items_nota = _clone_cotizacion_items(doc_afectado.items)

    db_nota = models.Cotizacion(
        serie=serie_nota,
        correlativo=nuevo_correlativo,
        cliente_id=doc_afectado.cliente_id,
        usuario_id=usuario_id,
        tenant_id=doc_afectado.tenant_id,
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
        nota_motivo_codigo=cod_motivo,
        nota_motivo_descripcion=descripcion_motivo,
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
