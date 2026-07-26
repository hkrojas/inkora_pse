from decimal import Decimal

from sqlalchemy.orm import Session

import models
from database import without_tenant_filter
from schemas.public_receipts import PublicReceiptLookup
from services.document_flow_service import (
    DOCUMENT_KIND_CREDIT_NOTE,
    DOCUMENT_KIND_DEBIT_NOTE,
    DOCUMENT_KIND_FISCAL_DOCUMENT,
    DOCUMENT_STATUS_VOIDED,
)


DOCUMENT_KIND_BY_TYPE = {
    "01": DOCUMENT_KIND_FISCAL_DOCUMENT,
    "03": DOCUMENT_KIND_FISCAL_DOCUMENT,
    "07": DOCUMENT_KIND_CREDIT_NOTE,
    "08": DOCUMENT_KIND_DEBIT_NOTE,
}


def _money(value) -> Decimal:
    return Decimal(str(value or "0")).quantize(Decimal("0.01"))


def _public_status(document: models.Cotizacion) -> str:
    if document.estado == DOCUMENT_STATUS_VOIDED:
        return "ANULADO"
    if document.sunat_accepted:
        return "ACEPTADO"
    if document.sunat_error:
        return "RECHAZADO"
    return "EN_PROCESO"


def lookup_public_receipt(
    db: Session,
    lookup: PublicReceiptLookup,
) -> dict | None:
    query = (
        db.query(models.Cotizacion, models.Tenant)
        .join(models.Tenant, models.Tenant.id == models.Cotizacion.tenant_id)
        .filter(
            models.Tenant.business_ruc == lookup.ruc,
            models.Cotizacion.tipo_comprobante == lookup.tipo_comprobante,
            models.Cotizacion.document_kind == DOCUMENT_KIND_BY_TYPE[lookup.tipo_comprobante],
            models.Cotizacion.serie == lookup.serie,
            models.Cotizacion.correlativo == int(lookup.correlativo),
        )
    )
    row = without_tenant_filter(query).first()
    if not row:
        return None

    document, tenant = row
    if not document.fecha_emision or document.fecha_emision.date() != lookup.fecha_emision:
        return None
    if _money(document.total_venta) != _money(lookup.importe_total):
        return None

    return {
        "encontrado": True,
        "emisor": tenant.business_name,
        "tipo_comprobante": document.tipo_comprobante,
        "numero": f"{document.serie}-{str(document.correlativo).zfill(8)}",
        "fecha_emision": document.fecha_emision.date(),
        "moneda": document.moneda or "PEN",
        "importe_total": _money(document.total_venta),
        "estado": _public_status(document),
        "evidencias": {
            "pdf": bool(document.sunat_pdf_url),
            "xml": document.has_sunat_xml,
            "cdr": document.has_sunat_cdr,
        },
    }
