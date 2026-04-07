"""crud/pagos.py — Pagos y adelantos de cliente al tenant."""
from sqlalchemy.orm import Session

import models
import schemas
from services.document_flow_service import is_note_document
from crud._base import (
    _get_tenant_resource,
    resolve_payment_anchor_document,
)
from services.document_flow_service import DOCUMENT_STATUS_VOIDED


def registrar_pago(db: Session, cotizacion_id: int, pago_data: schemas.PagoCreate, tenant_id: int):
    from decimal import Decimal

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

    saldo_actual = (source_quote.total_venta or Decimal("0")) - (source_quote.monto_pagado or Decimal("0"))
    monto = Decimal(str(pago_data.monto_pagado))

    if monto > saldo_actual:
        raise ValueError(
            f"El monto ({monto}) excede el saldo pendiente ({saldo_actual}). "
            f"Total venta: {source_quote.total_venta}, Ya pagado: {source_quote.monto_pagado}"
        )

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

    nuevo_pagado = (source_quote.monto_pagado or Decimal("0")) + monto
    source_quote.monto_pagado = nuevo_pagado
    source_quote.saldo_pendiente = (source_quote.total_venta or Decimal("0")) - nuevo_pagado

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
    source_quote, _ = resolve_payment_anchor_document(db, cotizacion_id, tenant_id)
    if not source_quote:
        return []
    return db.query(models.Pago).filter(
        models.Pago.cotizacion_id == source_quote.id,
        models.Pago.tenant_id == tenant_id,
    ).order_by(models.Pago.fecha_pago.desc()).all()
