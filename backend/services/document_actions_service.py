"""Eligibility for recovered invoice actions; unknown results are never retried."""
import re

import models
from access_control import DOCUMENT_EMITTER_ROLES, get_effective_role
from services import beta_feature_flags, inventory_service, sale_dispatch_service
from services.fiscal_presentation_service import presentation_status


def retry_block_reason(document, jobs, attempt=None):
    if document.document_kind != 'fiscal_document' or document.tipo_comprobante not in {'01', '03'}:
        return 'Solo se pueden reintentar facturas y boletas.'
    if document.estado == 'anulada':
        return 'El comprobante está anulado.'
    if document.sunat_accepted or document.estado == 'facturada':
        return 'El comprobante ya fue procesado; requiere revisión fiscal.'
    if document.sunat_cdr_content or document.sunat_cdr_url:
        return 'Existe un CDR. Revise su resultado antes de emitir otro documento.'
    errors = ' '.join(str(value or '') for value in [
        document.sunat_error, document.provider_verification_error,
        *(job.last_error for job in jobs),
    ]).lower()
    ambiguous = ('1033', 'duplicad', 'ya informado', 'ya fue informado', 'timeout',
                 'tiempo de espera', 'sin cdr', 'no devolvio cdr', 'connection',
                 'no encontrado', 'no existe', 'remote verification', 'http 400')
    if document.provider_verification_status == 'pending_confirmation' or any(word in errors for word in ambiguous):
        return 'Resultado pendiente de conciliación. No se permite reenviar.'
    if any(job.status != 'failed' for job in jobs):
        return 'Ya existe una operación fiscal en curso o procesada.'
    if any(job.provider_ticket for job in jobs):
        return 'Existe un ticket del proveedor; debe conciliarse antes de reenviar.'
    if not document.serie or document.correlativo is None:
        return 'Falta la identidad fiscal del comprobante.'
    if document.sujeta_detraccion:
        return 'La detracción requiere revisión antes de reintentar; no se modificará automáticamente.'
    # A pre-send validation failure is safe to retry after correcting its cause.
    # An unstructured legacy error/transport failure is not proof of rejection.
    preflight = attempt is not None and attempt.error_classification == 'validation'
    rejected_xml = bool(re.search(r'\[3127\]', errors))
    if not preflight and not rejected_xml:
        return 'Falta evidencia de un rechazo corregible. Solicite conciliación.'
    return None


def document_jobs(db, document):
    return db.query(models.DocumentEmissionJob).filter(
        models.DocumentEmissionJob.tenant_id == document.tenant_id,
        models.DocumentEmissionJob.resource_type == models.EMISSION_JOB_RESOURCE_COTIZACION,
        models.DocumentEmissionJob.resource_id == document.id,
    ).order_by(models.DocumentEmissionJob.id.desc()).all()


def latest_attempt(db, jobs, tenant_id):
    if not jobs:
        return None
    return db.query(models.DocumentEmissionAttempt).filter(
        models.DocumentEmissionAttempt.tenant_id == tenant_id,
        models.DocumentEmissionAttempt.job_id.in_([job.id for job in jobs]),
    ).order_by(models.DocumentEmissionAttempt.id.desc()).first()


def available_actions(db, document, user):
    jobs = document_jobs(db, document)
    reason = retry_block_reason(document, jobs, latest_attempt(db, jobs, document.tenant_id))
    emitter = get_effective_role(user) in DOCUMENT_EMITTER_ROLES
    if not emitter:
        reason = 'Su perfil no permite reintentar emisiones.'
    tenant = user.tenant
    active = bool(tenant and tenant.is_active and user.is_active)
    if not tenant or not tenant.is_active or not user.is_active:
        reason = 'La empresa o el usuario no están activos.'
    if tenant and tenant.smartpse_environment == 'produccion':
        configured = tenant.fiscal_invoice_series if document.tipo_comprobante == '01' else tenant.fiscal_boleta_series
        if not configured or document.serie != configured:
            reason = 'La serie del documento no corresponde a la configuración vigente. Requiere revisión fiscal.'
    if jobs:
        attempts = db.query(models.DocumentEmissionAttempt).filter(
            models.DocumentEmissionAttempt.tenant_id == document.tenant_id,
            models.DocumentEmissionAttempt.job_id.in_([job.id for job in jobs]),
        ).all()
        if any(attempt.error_classification in {'ambiguous', 'transient', 'provider_policy'} for attempt in attempts):
            reason = 'El historial contiene un resultado incierto; se requiere conciliación.'
    if db.query(models.InventoryHold.id).filter(
        models.InventoryHold.tenant_id == document.tenant_id,
        models.InventoryHold.document_id == document.id,
        models.InventoryHold.status != 'active',
    ).first():
        reason = 'El inventario requiere conciliación antes del reintento.'
    subscription = db.query(models.Subscription).filter(models.Subscription.tenant_id == document.tenant_id).first()
    subscribed = bool(user.is_superadmin or (subscription and subscription.status in {'active', 'trial', 'grace'}))
    if not subscribed:
        reason = 'La suscripción no permite nuevas operaciones fiscales.'
    can_operate = emitter and active and subscribed
    status = presentation_status(document)
    accepted = status == 'emitted' and document.estado == 'facturada' and bool(document.sunat_xml_content or document.sunat_xml_url)
    def enabled(key):
        return bool(user.is_superadmin or beta_feature_flags.is_feature_enabled_for_subscription(subscription, key))
    void_reason = None
    if not can_operate:
        void_reason = 'Su usuario, empresa o suscripción no permiten esta operación.'
    elif not accepted:
        void_reason = 'Se requiere un comprobante vigente y aceptado, sin resultado incierto.'
    elif not enabled('voiding'):
        void_reason = 'La baja no está habilitada para la empresa.'
    elif any(job.action == models.EMISSION_JOB_ACTION_VOID_FISCAL and job.status != 'failed' for job in jobs):
        void_reason = 'Ya existe una solicitud de baja; revise su seguimiento.'
    else:
        try:
            inventory_service.ensure_document_void_inventory_safe(db, document)
            if sale_dispatch_service.active_dispatch_allocation_exists(db, document.tenant_id, document.id):
                void_reason = 'Resuelva primero las reservas de despacho, guías o salidas vinculadas.'
        except ValueError as exc:
            void_reason = str(exc)
    active_void = any(job.action == models.EMISSION_JOB_ACTION_VOID_FISCAL and job.status != 'failed' for job in jobs)
    latest_job = jobs[0] if jobs else None
    return {
        'retry_emission': reason is None,
        'retry_block_reason': reason,
        'retry_artifacts': emitter and active and document.estado != 'anulada' and bool(document.sunat_cdr_content or document.sunat_cdr_url),
        'void': void_reason is None,
        'void_block_reason': void_reason,
        'credit_note': can_operate and accepted and not active_void and enabled('credit_notes'),
        'debit_note': can_operate and accepted and not active_void and enabled('debit_notes'),
        'create_guide': can_operate and accepted and not active_void and enabled('guides'),
        'fiscal_status': status,
        'retry_label': 'Reenviar a Smart PSE' if (latest_job and latest_job.provider == 'smartpse') or (tenant and tenant.smartpse_company_id) else 'Reintentar envío fiscal',
        'job_id': latest_job.id if latest_job else None,
        'job_status': latest_job.status if latest_job else None,
        'job_action': latest_job.action if latest_job else None,
    }
