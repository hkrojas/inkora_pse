from decimal import Decimal


DOCUMENT_KIND_QUOTATION = "quotation"
DOCUMENT_KIND_FISCAL_DOCUMENT = "fiscal_document"
DOCUMENT_KIND_CREDIT_NOTE = "credit_note"
DOCUMENT_KIND_DEBIT_NOTE = "debit_note"

DOCUMENT_STATUS_PENDING = "pendiente"
DOCUMENT_STATUS_ISSUED = "facturada"
DOCUMENT_STATUS_VOIDED = "anulada"

FISCAL_DOCUMENT_KINDS = {
    DOCUMENT_KIND_FISCAL_DOCUMENT,
    DOCUMENT_KIND_CREDIT_NOTE,
    DOCUMENT_KIND_DEBIT_NOTE,
}


def build_internal_order_number(tenant_id: int, correlativo: int) -> str:
    return f"ORD-{tenant_id:04d}-{correlativo:06d}"


def get_document_kind_for_note(tipo_nota: str) -> str:
    normalized = (tipo_nota or "").strip().lower()
    if normalized == "credito":
        return DOCUMENT_KIND_CREDIT_NOTE
    if normalized == "debito":
        return DOCUMENT_KIND_DEBIT_NOTE
    raise ValueError("Tipo de nota invalido. Use 'credito' o 'debito'.")


def is_quote_document(document) -> bool:
    return getattr(document, "document_kind", DOCUMENT_KIND_QUOTATION) == DOCUMENT_KIND_QUOTATION


def is_fiscal_document(document) -> bool:
    return getattr(document, "document_kind", None) == DOCUMENT_KIND_FISCAL_DOCUMENT


def is_note_document(document) -> bool:
    return getattr(document, "document_kind", None) in {
        DOCUMENT_KIND_CREDIT_NOTE,
        DOCUMENT_KIND_DEBIT_NOTE,
    }


def is_fiscal_family_document(document) -> bool:
    return getattr(document, "document_kind", None) in FISCAL_DOCUMENT_KINDS


def resolve_source_quote_id(document) -> int | None:
    if is_quote_document(document):
        return getattr(document, "id", None)
    return getattr(document, "source_quote_id", None) or getattr(document, "id", None)


def calculate_payment_status(total_venta, monto_pagado) -> str:
    total = Decimal(str(total_venta or 0))
    paid = Decimal(str(monto_pagado or 0))
    if paid <= 0:
        return "pendiente"
    if paid >= total:
        return "pagado"
    return "parcial"
