"""
crud/_base.py — Helpers compartidos entre dominios CRUD.

Contiene: utilidades de acceso a recursos por tenant, clonado de items,
resolución de documentos fuente, y contexto de hash de passwords.
Estos helpers son importados por los demás módulos del paquete crud/.
"""
from passlib.context import CryptContext
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

import models
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
    is_fiscal_document,
    is_fiscal_family_document,
    is_note_document,
    is_quote_document,
    resolve_source_quote_id,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
