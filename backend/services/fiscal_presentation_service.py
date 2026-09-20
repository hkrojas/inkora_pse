"""Read-only list classification; never changes a document's fiscal evidence."""
from sqlalchemy import case, func, or_


def presentation_status(document):
    state = getattr(document, 'estado', '')
    error = str(getattr(document, 'sunat_error', '') or '')
    verification = getattr(document, 'provider_verification_status', None)
    if state == 'anulada':
        return 'voided'
    if state == 'borrador':
        return 'draft'
    if verification == 'pending_confirmation' or '1033' in error:
        return 'pending_confirmation'
    if error:
        return 'rejected'
    if verification and verification != 'verified':
        return 'pending'
    if any(getattr(document, name, None) for name in ('has_sunat_cdr', 'sunat_cdr_content', 'sunat_cdr_url')):
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
        (or_(verification == 'pending_confirmation', error.contains('1033')), 'pending_confirmation'),
        (error != '', 'rejected'),
        (~verification.in_(['', 'verified']), 'pending'),
        (has_cdr, 'emitted'),
        else_='pending',
    )
