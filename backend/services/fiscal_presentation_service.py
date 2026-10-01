"""Read-only list classification; never changes a document's fiscal evidence."""
from sqlalchemy import case, func, or_


def presentation_status(document):
    state = getattr(document, 'estado', '')
    error = str(getattr(document, 'sunat_error', '') or '')
    verification = getattr(document, 'provider_verification_status', None)
    has_cdr = any(getattr(document, name, None) for name in ('has_sunat_cdr', 'sunat_cdr_content', 'sunat_cdr_url'))
    if state == 'anulada':
        return 'voided'
    if state == 'borrador':
        return 'draft'
    if state == 'facturada' and verification == 'verified' and has_cdr:
        return 'emitted'
    if verification == 'rejected':
        return 'rejected'
    if verification == 'pending_confirmation' or error:
        return 'pending_confirmation'
    if verification and verification != 'verified':
        return 'pending'
    if has_cdr:
        return 'emitted'
    return 'pending'


def presentation_status_expression(model):
    error = func.coalesce(model.sunat_error, '')
    verification = func.coalesce(model.provider_verification_status, '')
    has_cdr = or_(func.coalesce(model.sunat_cdr_url, '') != '', func.coalesce(model.sunat_cdr_content, '') != '')
    # Ordered CASE makes filters disjoint, including voided documents with old errors.
    return case(
        (model.estado == 'anulada', 'voided'),
        (model.estado == 'borrador', 'draft'),
        ((model.estado == 'facturada') & (verification == 'verified') & has_cdr, 'emitted'),
        (verification == 'rejected', 'rejected'),
        (or_(verification == 'pending_confirmation', error != ''), 'pending_confirmation'),
        (~verification.in_(['', 'verified']), 'pending'),
        (has_cdr, 'emitted'),
        else_='pending',
    )
