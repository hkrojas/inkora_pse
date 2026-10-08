"""services/emission_queue_service.py — Cola durable para emisión fiscal."""
import asyncio
import hashlib
import json
import math
import signal
import threading
from datetime import datetime, timedelta
from threading import Thread
from types import SimpleNamespace
from uuid import uuid4
from xml.etree import ElementTree as ET

from sqlalchemy.orm import Session, joinedload

import crud
import models
from services import fiscal_evidence_service, fiscal_recovery_service, fiscal_submission_state, smartpse_response, smartpse_client, smartpse_panel_client, panel_retry_state
from access_control import DOCUMENT_EMITTER_ROLES, get_effective_role
from config import settings
from database import SessionLocal, apply_tenant_context, reset_tenant_context
from logging_utils import get_logger
from services import (
    emission_leases,
    beta_feature_flags,
    facturacion_service,
    fiscal_artifact_service,
    fiscal_provider_service,
    inventory_service,
    pdf_storage_service,
    sale_dispatch_service,
    void_recovery_service,
)
from services.facturacion_background_service import process_direct_sunat_emission_bg
from services.fiscal_balance_service import ensure_credit_note_within_available_amount

logger = get_logger(__name__)

EMISSION_MODE_SYNC = "sync"
EMISSION_MODE_ASYNC = "async"
EMISSION_ALLOWED_SUBSCRIPTION_STATUSES = {
    models.SUBSCRIPTION_STATUS_ACTIVE,
    models.SUBSCRIPTION_STATUS_TRIAL,
    "grace",
}
EMISSION_BLOCKED_NO_ACTIVE_SUBSCRIPTION_MESSAGE = (
    "El tenant no tiene una suscripción activa para emitir."
)

EMISSION_ERROR_TRANSIENT = "transient"
EMISSION_ERROR_AMBIGUOUS = "ambiguous"
EMISSION_ERROR_PROVIDER_POLICY = "provider_policy"
EMISSION_ERROR_VALIDATION = "validation"
EMISSION_ERROR_TERMINAL = "terminal"

# Graceful shutdown flag
_shutdown_requested = threading.Event()
_worker_wakeup = None


class NonRetryableEmissionValidationError(RuntimeError):
    """Validation failure that must finish the job without retries."""


def request_worker_shutdown() -> None:
    """Senala al worker que termine el ciclo actual."""
    _shutdown_requested.set()
    if _worker_wakeup is not None:
        _worker_wakeup.pulse()
    logger.info("worker_shutdown_requested", extra={"event": "worker_shutdown_requested"})


def is_shutdown_requested() -> bool:
    return _shutdown_requested.is_set()


def _install_signal_handlers() -> None:
    """Instala handlers para SIGTERM/SIGINT en el proceso worker."""
    def _handle_signal(signum, frame):
        logger.info(
            "worker_signal_received",
            extra={"event": "worker_signal_received", "context": f"signal={signum}"},
        )
        request_worker_shutdown()

    try:
        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)
    except ValueError:
        # No se puede instalar señales fuera del thread principal; ignorar.
        pass


def resolve_emission_mode(requested_mode: str | None = None, *,
                          tenant_id: int | None = None, tipo_comprobante: str | None = None) -> str:
    mode_candidate = requested_mode if isinstance(requested_mode, str) else None
    mode = (mode_candidate or settings.EMISSION_MODE_DEFAULT or EMISSION_MODE_SYNC).strip().lower()
    if mode not in {EMISSION_MODE_SYNC, EMISSION_MODE_ASYNC}:
        raise ValueError("Modo de emision invalido. Use 'sync' o 'async'.")
    # Enrolled invoices must persist their submission fence through the worker,
    # even when an older client explicitly asks to send synchronously.
    if tenant_id is not None and tipo_comprobante == "01" and fiscal_recovery_service.enabled(tenant_id):
        return EMISSION_MODE_ASYNC
    return mode


def _build_job_result_snapshot(result: dict | None) -> dict:
    result = result or {}
    sunat_response = result.get("sunat_response") or {}
    return {
        "success": bool(result.get("success")),
        "serie": result.get("serie"),
        "correlativo": result.get("correlativo"),
        "ticket": result.get("ticket") or sunat_response.get("ticket"),
        "provider_endpoint": result.get("provider_endpoint"),
        "provider_status_code": result.get("provider_status_code"),
        "sunat_response": sunat_response,
        **({"recovery_source": result["recovery_source"]} if result.get("recovery_source") else {}),
    }


def build_job_acceptance_payload(
    job: models.DocumentEmissionJob,
    *,
    message: str,
    resource_id: int,
    resource_type: str,
    internal_order_number: str | None = None,
) -> dict:
    deferred = job.status == models.EMISSION_JOB_STATUS_CONTINGENCY_PENDING
    pending_confirmation = job.status == models.EMISSION_JOB_STATUS_PENDING_CONFIRMATION
    return {
        "success": True,
        "queued": True,
        "deferred": deferred,
        "pending_confirmation": pending_confirmation,
        "message": (
            "Documento reservado en contingencia; queda pendiente de envio y validacion fiscal."
            if deferred
            else message
        ),
        "job_id": job.id,
        "job_status": job.status,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "internal_order_number": internal_order_number,
    }


def _initial_cpe_job_status(user: models.User, *, signing_first: bool = False) -> str:
    tenant = getattr(user, "tenant", None)
    if tenant and bool(getattr(tenant, "fiscal_contingency_mode", False)) and not signing_first:
        return models.EMISSION_JOB_STATUS_CONTINGENCY_PENDING
    return models.EMISSION_JOB_STATUS_QUEUED


def enqueue_fiscal_document_job(
    db: Session,
    fiscal_document: models.Cotizacion,
    user: models.User,
    *,
    tipo_comprobante: str,
):
    idempotency_key = f"emit:fiscal:{fiscal_document.id}"
    existing = crud.get_emission_job_by_key(db, fiscal_document.tenant_id, idempotency_key)
    provider = "smartpse"
    initial_status = _initial_cpe_job_status(user, signing_first=(tipo_comprobante == "01" and fiscal_recovery_service.enabled(user.tenant_id)))
    if existing:
        if existing.status in {
            models.EMISSION_JOB_STATUS_QUEUED,
            models.EMISSION_JOB_STATUS_PROCESSING,
            models.EMISSION_JOB_STATUS_RETRY,
            models.EMISSION_JOB_STATUS_PENDING_CONFIRMATION,
            models.EMISSION_JOB_STATUS_CONTINGENCY_PENDING,
            models.EMISSION_JOB_STATUS_SUCCEEDED,
        }:
            return existing, False
        existing = crud.requeue_emission_job(
            db,
            existing.id,
            payload_snapshot=existing.payload_snapshot or {"tipo_comprobante": tipo_comprobante},
            provider=provider,
            target_status=initial_status,
        )
        return existing, False

    prepared = facturacion_service.prepare_sale_document(fiscal_document, db, user, tipo_comprobante)
    submission_state = fiscal_submission_state.initial_state() if tipo_comprobante == "01" else {}
    job = crud.create_emission_job(
        db,
        tenant_id=fiscal_document.tenant_id,
        created_by_user_id=user.id,
        resource_type=models.EMISSION_JOB_RESOURCE_COTIZACION,
        resource_id=fiscal_document.id,
        action=models.EMISSION_JOB_ACTION_EMIT_FISCAL,
        provider=provider,
        idempotency_key=idempotency_key,
        payload_snapshot={"tipo_comprobante": tipo_comprobante, "prepared_sale": prepared,
                          "recovery_flow": tipo_comprobante == "01" and fiscal_recovery_service.enabled(user.tenant_id),
                          **submission_state},
        max_attempts=settings.EMISSION_MAX_ATTEMPTS,
        initial_status=initial_status,
    )
    return job, True


def enqueue_note_job(
    db: Session,
    nota: models.Cotizacion,
    user: models.User,
    *,
    tipo_nota: str,
    cod_motivo: str,
    descripcion_motivo: str,
):
    idempotency_key = f"emit:note:{nota.id}"
    existing = crud.get_emission_job_by_key(db, nota.tenant_id, idempotency_key)
    initial_status = _initial_cpe_job_status(user)
    if existing:
        if existing.status in {
            models.EMISSION_JOB_STATUS_QUEUED,
            models.EMISSION_JOB_STATUS_PROCESSING,
            models.EMISSION_JOB_STATUS_RETRY,
            models.EMISSION_JOB_STATUS_PENDING_CONFIRMATION,
            models.EMISSION_JOB_STATUS_CONTINGENCY_PENDING,
            models.EMISSION_JOB_STATUS_SUCCEEDED,
        }:
            return existing, False
        existing = crud.requeue_emission_job(
            db,
            existing.id,
            payload_snapshot={
                "tipo_nota": tipo_nota,
                "cod_motivo": cod_motivo,
                "descripcion_motivo": descripcion_motivo,
            },
            provider="smartpse",
            target_status=initial_status,
        )
        return existing, False

    job = crud.create_emission_job(
        db,
        tenant_id=nota.tenant_id,
        created_by_user_id=user.id,
        resource_type=models.EMISSION_JOB_RESOURCE_COTIZACION,
        resource_id=nota.id,
        action=models.EMISSION_JOB_ACTION_EMIT_NOTE,
        provider="smartpse",
        idempotency_key=idempotency_key,
        payload_snapshot={
            "tipo_nota": tipo_nota,
            "cod_motivo": cod_motivo,
            "descripcion_motivo": descripcion_motivo,
        },
        max_attempts=settings.EMISSION_MAX_ATTEMPTS,
        initial_status=initial_status,
    )
    return job, True


def enqueue_void_document_job(
    db: Session,
    comprobante: models.Cotizacion,
    user: models.User,
    *,
    motivo: str,
):
    # Serialize duplicate requests and batch reservation across API replicas.
    # NO KEY UPDATE serializes reservations without blocking the FK KEY SHARE
    # used by a concurrent note INSERT that already owns its source row.
    db.query(models.Tenant).filter(models.Tenant.id == user.tenant_id).with_for_update(key_share=True).one()
    if comprobante.tenant_id != user.tenant_id:
        raise ValueError("El comprobante no pertenece a la empresa autenticada.")
    comprobante = db.query(models.Cotizacion).filter_by(
        id=comprobante.id, tenant_id=user.tenant_id,
    ).populate_existing().with_for_update().one()
    idempotency_key = f"void:fiscal:{comprobante.id}"
    existing = crud.get_emission_job_by_key(db, comprobante.tenant_id, idempotency_key)
    if existing:
        # Never erase the frozen identity/evidence or submit another batch after
        # uncertainty or rejection. A failed cancellation requires review.
        db.commit()
        return existing, False
    void_recovery_service.ensure_no_active_notes(db, comprobante)
    inventory_service.ensure_document_void_inventory_safe(db, comprobante)
    if sale_dispatch_service.active_dispatch_allocation_exists(db, comprobante.tenant_id, comprobante.id):
        raise ValueError("La baja requiere resolver antes las reservas o cobertura GRE.")
    snapshot = void_recovery_service.prepare_snapshot(db, comprobante, user, motivo)
    job = crud.create_emission_job(
        db,
        tenant_id=comprobante.tenant_id,
        created_by_user_id=user.id,
        resource_type=models.EMISSION_JOB_RESOURCE_COTIZACION,
        resource_id=comprobante.id,
        action=models.EMISSION_JOB_ACTION_VOID_FISCAL,
        provider="smartpse",
        idempotency_key=idempotency_key,
        payload_snapshot=snapshot,
        max_attempts=settings.EMISSION_MAX_ATTEMPTS,
    )
    return job, True


def enqueue_guide_job(
    db: Session,
    guia: models.GuiaRemision,
    user: models.User,
):
    idempotency_key = f"emit:guide:{guia.id}"
    existing = crud.get_emission_job_by_key(db, guia.tenant_id, idempotency_key)
    initial_status = _initial_cpe_job_status(user)
    snapshot = {
        "tipo_documento": guia.tipo_documento,
        "serie": guia.serie,
        "correlativo": guia.correlativo,
        "dispatch_id": guia.dispatch_id,
        "emission_environment": guia.emission_environment,
    }
    if existing:
        if existing.status in {
            models.EMISSION_JOB_STATUS_QUEUED,
            models.EMISSION_JOB_STATUS_PROCESSING,
            models.EMISSION_JOB_STATUS_RETRY,
            models.EMISSION_JOB_STATUS_PENDING_CONFIRMATION,
            models.EMISSION_JOB_STATUS_CONTINGENCY_PENDING,
            models.EMISSION_JOB_STATUS_SUCCEEDED,
        }:
            return existing, False
        existing = crud.requeue_emission_job(
            db,
            existing.id,
            payload_snapshot=snapshot,
            provider="smartpse",
            target_status=initial_status,
        )
        return existing, False

    job = crud.create_emission_job(
        db,
        tenant_id=guia.tenant_id,
        created_by_user_id=user.id,
        resource_type=models.EMISSION_JOB_RESOURCE_GUIA,
        resource_id=guia.id,
        action=models.EMISSION_JOB_ACTION_EMIT_GUIDE,
        provider="smartpse",
        idempotency_key=idempotency_key,
        payload_snapshot=snapshot,
        max_attempts=settings.EMISSION_MAX_ATTEMPTS,
        initial_status=initial_status,
    )
    return job, True


def enqueue_guide_consult_job(db: Session, guia: models.GuiaRemision, user: models.User):
    """Queue status reconciliation without ever resending the GRE."""
    idempotency_key = f"consult:guide:{guia.id}"
    existing = crud.get_emission_job_by_key(db, guia.tenant_id, idempotency_key)
    snapshot = {"ticket": guia.sunat_ticket, "serie": guia.serie, "correlativo": guia.correlativo}
    if existing:
        if existing.status in {
            models.EMISSION_JOB_STATUS_QUEUED,
            models.EMISSION_JOB_STATUS_PROCESSING,
            models.EMISSION_JOB_STATUS_RETRY,
            models.EMISSION_JOB_STATUS_SUCCEEDED,
        }:
            return existing, False
        # A pending confirmation is not a definitive fiscal result. Requeue it
        # only when the operator explicitly requests another consultation; this
        # path never calls /despatch/send and therefore cannot duplicate the GRE.
        return crud.requeue_emission_job(
            db, existing.id, payload_snapshot=snapshot, provider="smartpse",
            target_status=models.EMISSION_JOB_STATUS_QUEUED,
        ), False
    return crud.create_emission_job(
        db,
        tenant_id=guia.tenant_id,
        created_by_user_id=user.id,
        resource_type=models.EMISSION_JOB_RESOURCE_GUIA,
        resource_id=guia.id,
        action=models.EMISSION_JOB_ACTION_CONSULT_GUIDE,
        provider="smartpse",
        idempotency_key=idempotency_key,
        payload_snapshot=snapshot,
        max_attempts=settings.EMISSION_MAX_ATTEMPTS,
    ), True


def _retry_delay_seconds(attempts: int) -> int:
    base = max(settings.EMISSION_RETRY_BASE_SECONDS, 1)
    exponent = max(attempts - 1, 0)
    return min(base * (2 ** exponent), 300)


def _is_retryable_error(message: str) -> bool:
    normalized = (message or "").lower()
    retryable_fragments = (
        "timeout",
        "tiempo de espera",
        "no se pudo conectar",
        "connection",
        "server error",
        "internal server error",
        "error interno",
        "ticket no existe",
        "ticket no encontrado",
        "en proceso",
        "procesando",
        "todavia no ha sido procesado",
    )
    return any(fragment in normalized for fragment in retryable_fragments)


def _classify_emission_error(message: str) -> str:
    """Clasifica errores sin convertir estados ambiguos en rechazos fiscales."""
    normalized = (message or "").lower()
    provider_policy_fragments = (
        "[0111]",
        "no tiene el perfil para enviar comprobantes",
        "rejected by policy",
    )
    ambiguous_fragments = (
        "[1033]",
        "[http] bad request",
        "http 400",
        "status 400",
        "smart pse remote verification missing",
        "no devolvio cdr",
        "sin cdr",
        "no puede marcarse como aceptado",
    )
    if any(fragment in normalized for fragment in provider_policy_fragments):
        return EMISSION_ERROR_PROVIDER_POLICY
    if any(fragment in normalized for fragment in ambiguous_fragments):
        return EMISSION_ERROR_AMBIGUOUS
    if _is_retryable_error(message):
        return EMISSION_ERROR_TRANSIENT
    return EMISSION_ERROR_TERMINAL


def _must_hold_exhausted_consultation(
    job: models.DocumentEmissionJob,
    error_classification: str,
) -> bool:
    """Keep an inconclusive GRE query out of the definitive failure state."""
    return (
        job.action in {
            models.EMISSION_JOB_ACTION_CONSULT_FISCAL,
            models.EMISSION_JOB_ACTION_CONSULT_GUIDE,
        }
        and error_classification == EMISSION_ERROR_TRANSIENT
        and (job.attempts or 0) >= (job.max_attempts or settings.EMISSION_MAX_ATTEMPTS)
    )


def _apply_optional_tenant_context(db: Session, tenant_id: int):
    bind = getattr(db, "bind", None)
    dialect_name = getattr(getattr(bind, "dialect", None), "name", "")
    if dialect_name == "postgresql":
        return apply_tenant_context(db, tenant_id)
    return None


def _run_async_syncsafe(coro) -> None:
    try:
        asyncio.run(coro)
        return
    except RuntimeError as exc:
        if "asyncio.run() cannot be called from a running event loop" not in str(exc):
            raise

    error_holder: list[BaseException] = []

    def _runner():
        try:
            asyncio.run(coro)
        except BaseException as thread_exc:  # pragma: no cover - ruta defensiva
            error_holder.append(thread_exc)

    thread = Thread(target=_runner, daemon=False)
    thread.start()
    thread.join()
    if error_holder:
        raise error_holder[0]


def _load_job_user(db: Session, job: models.DocumentEmissionJob):
    user = None
    if job.created_by_user_id:
        user = crud.get_user_by_id(db, job.created_by_user_id)
    if user:
        return user
    return db.query(models.User).options(joinedload(models.User.tenant)).filter(
        models.User.tenant_id == job.tenant_id,
    ).order_by(models.User.id.asc()).first()


def _raise_non_retryable_validation(message: str) -> None:
    raise NonRetryableEmissionValidationError(
        f"Validacion previa de emision fallida: {message}"
    )


def _resolve_job_tenant(db: Session, job: models.DocumentEmissionJob, user: models.User):
    tenant = getattr(user, "tenant", None)
    if tenant and tenant.id == job.tenant_id:
        return tenant
    return (
        db.query(models.Tenant)
        .options(joinedload(models.Tenant.subscription))
        .filter(models.Tenant.id == job.tenant_id)
        .first()
    )


def _ensure_user_can_run_emission_job(job: models.DocumentEmissionJob, user: models.User) -> None:
    if user.tenant_id != job.tenant_id:
        _raise_non_retryable_validation(
            "El usuario creador del job no pertenece al tenant del job."
        )
    if not getattr(user, "is_active", True):
        _raise_non_retryable_validation(
            "El usuario creador del job esta inactivo o bloqueado."
        )
    try:
        effective_role = get_effective_role(user)
    except Exception:
        _raise_non_retryable_validation(
            "El usuario creador del job tiene un rol invalido para emision."
        )
    if effective_role not in DOCUMENT_EMITTER_ROLES:
        _raise_non_retryable_validation(
            "El usuario creador del job no tiene rol emisor valido."
        )


def _ensure_tenant_can_run_emission_job(db: Session, tenant: models.Tenant | None) -> None:
    if not tenant:
        _raise_non_retryable_validation("Tenant del job no encontrado.")
    if not getattr(tenant, "is_active", False):
        _raise_non_retryable_validation("Tenant inactivo o suspendido.")

    subscription = getattr(tenant, "subscription", None) or crud.get_subscription_by_tenant(
        db,
        tenant.id,
    )
    subscription_status = str(getattr(subscription, "status", "") or "").strip().lower()
    if subscription_status in EMISSION_ALLOWED_SUBSCRIPTION_STATUSES:
        return

    _raise_non_retryable_validation(
        EMISSION_BLOCKED_NO_ACTIVE_SUBSCRIPTION_MESSAGE
    )


def _ensure_provider_available_for_job(job: models.DocumentEmissionJob, tenant: models.Tenant) -> None:
    if fiscal_provider_service.has_smartpse_credentials(tenant):
        return
    reason = fiscal_provider_service.smartpse_block_reason(tenant)
    _raise_non_retryable_validation(
        f"Proveedor fiscal Smart PSE no disponible: {reason or 'credenciales incompletas.'}"
    )


def _resolve_job_feature_key(db: Session, job: models.DocumentEmissionJob) -> str | None:
    if job.action == models.EMISSION_JOB_ACTION_EMIT_NOTE:
        note = _get_tenant_cotizacion(db, job.tenant_id, job.resource_id)
        if not note:
            _raise_non_retryable_validation("Nota fiscal del job no encontrada.")
        payload_snapshot = job.payload_snapshot or {}
        tipo_nota = (
            payload_snapshot.get("tipo_nota")
            or getattr(note, "tipo_comprobante", None)
            or getattr(note, "document_kind", None)
        )
        try:
            return beta_feature_flags.feature_for_note_type(tipo_nota)
        except ValueError:
            document_kind = str(getattr(note, "document_kind", "") or "").lower()
            if document_kind == "credit_note":
                return beta_feature_flags.FISCAL_FEATURE_CREDIT_NOTES
            if document_kind == "debit_note":
                return beta_feature_flags.FISCAL_FEATURE_DEBIT_NOTES
            _raise_non_retryable_validation(
                "Tipo de nota no soportado para feature flags fiscales."
            )
    if job.action in {models.EMISSION_JOB_ACTION_EMIT_GUIDE, models.EMISSION_JOB_ACTION_CONSULT_GUIDE}:
        return beta_feature_flags.FISCAL_FEATURE_GUIDES
    if job.action == models.EMISSION_JOB_ACTION_VOID_FISCAL:
        return beta_feature_flags.FISCAL_FEATURE_VOIDING
    return None


def _ensure_feature_flag_available_for_job(
    db: Session,
    job: models.DocumentEmissionJob,
    tenant: models.Tenant,
) -> None:
    feature_key = _resolve_job_feature_key(db, job)
    if not feature_key:
        return
    if beta_feature_flags.is_feature_enabled_for_tenant(tenant, feature_key):
        return
    _raise_non_retryable_validation(
        (
            "Funcion fiscal disponible en beta controlada pero no activada "
            f"para este tenant: {feature_key}."
        )
    )


def _resolve_fiscal_document_limit_kind(db: Session, job: models.DocumentEmissionJob) -> str:
    fiscal_document = _get_tenant_cotizacion(db, job.tenant_id, job.resource_id)
    if not fiscal_document:
        _raise_non_retryable_validation("Documento fiscal del job no encontrado.")

    payload_snapshot = job.payload_snapshot or {}
    tipo_comprobante = payload_snapshot.get("tipo_comprobante") or fiscal_document.tipo_comprobante
    serie = str(getattr(fiscal_document, "serie", "") or "").upper()
    if tipo_comprobante == "01" or serie.startswith("F"):
        return models.USAGE_LIMIT_KIND_FACTURA
    if tipo_comprobante == "03" or serie.startswith("B"):
        return models.USAGE_LIMIT_KIND_BOLETA
    _raise_non_retryable_validation(
        f"Tipo de comprobante no soportado para limites de emision: {tipo_comprobante}."
    )


def _resolve_note_limit_kind(db: Session, job: models.DocumentEmissionJob) -> str:
    note = _get_tenant_cotizacion(db, job.tenant_id, job.resource_id)
    if not note:
        _raise_non_retryable_validation("Nota fiscal del job no encontrada.")

    payload_snapshot = job.payload_snapshot or {}
    tipo_nota = str(payload_snapshot.get("tipo_nota") or "").strip().lower()
    tipo_comprobante = str(getattr(note, "tipo_comprobante", "") or "").strip()
    document_kind = str(getattr(note, "document_kind", "") or "").strip().lower()
    if tipo_comprobante == "07" or tipo_nota in {"07", "credito", "credit", "nc"} or document_kind == "credit_note":
        return models.USAGE_LIMIT_KIND_NOTA_CREDITO
    if tipo_comprobante == "08" or tipo_nota in {"08", "debito", "debit", "nd"} or document_kind == "debit_note":
        return models.USAGE_LIMIT_KIND_NOTA_DEBITO
    _raise_non_retryable_validation(
        "Tipo de nota no soportado para limites de emision."
    )


def _resolve_job_limit_kind(db: Session, job: models.DocumentEmissionJob) -> str | None:
    if job.action == models.EMISSION_JOB_ACTION_EMIT_FISCAL:
        return _resolve_fiscal_document_limit_kind(db, job)
    if job.action == models.EMISSION_JOB_ACTION_EMIT_NOTE:
        return _resolve_note_limit_kind(db, job)
    if job.action == models.EMISSION_JOB_ACTION_EMIT_GUIDE:
        return models.USAGE_LIMIT_KIND_GUIA
    return None


def _ensure_limits_available_for_job(
    db: Session,
    job: models.DocumentEmissionJob,
    user: models.User,
) -> None:
    try:
        if job.action == models.EMISSION_JOB_ACTION_EMIT_FISCAL:
            crud.check_document_limit(db, job.tenant_id)

        limit_kind = _resolve_job_limit_kind(db, job)
        if limit_kind:
            crud.check_emission_quota(
                db,
                job.tenant_id,
                user.id,
                limit_kind,
            )
    except crud.QuotaExceededError as exc:
        _raise_non_retryable_validation(f"Limite de emision agotado: {exc}")
    except ValueError as exc:
        _raise_non_retryable_validation(str(exc))


def _validate_job_execution_context(
    db: Session,
    job: models.DocumentEmissionJob,
    user: models.User,
) -> None:
    prepared = (job.payload_snapshot or {}).get("prepared_sale") or {}
    tenant = _resolve_job_tenant(db, job, user)
    if prepared and tenant:
        if ("provider_environment" in prepared
                and prepared["provider_environment"] != tenant.smartpse_environment):
            _raise_non_retryable_validation("El ambiente fiscal cambio desde el encolado; requiere revision.")
        if str((prepared.get("payload", {}).get("company") or {}).get("ruc")) != str(tenant.business_ruc):
            _raise_non_retryable_validation("El RUC emisor cambio desde el encolado; requiere revision.")
    if job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL:
        # Reconcile an existing fiscal operation even if its creator/subscription
        # changed. This grants no permission to submit a new document.
        if user.tenant_id != job.tenant_id:
            _raise_non_retryable_validation("El usuario no pertenece al tenant del job.")
        tenant = _resolve_job_tenant(db, job, user)
        if not tenant:
            _raise_non_retryable_validation("Tenant del job no encontrado.")
        _ensure_provider_available_for_job(job, tenant)
        return
    _ensure_user_can_run_emission_job(job, user)
    tenant = _resolve_job_tenant(db, job, user)
    _ensure_tenant_can_run_emission_job(db, tenant)
    _ensure_feature_flag_available_for_job(db, job, tenant)
    _ensure_provider_available_for_job(job, tenant)
    _ensure_limits_available_for_job(db, job, user)


def _get_tenant_cotizacion(db: Session, tenant_id: int, cotizacion_id: int):
    return db.query(models.Cotizacion).options(
        joinedload(models.Cotizacion.cliente),
        joinedload(models.Cotizacion.items),
        joinedload(models.Cotizacion.usuario).joinedload(models.User.tenant),
        joinedload(models.Cotizacion.source_quote),
        joinedload(models.Cotizacion.nota_referencia),
    ).filter(
        models.Cotizacion.id == cotizacion_id,
        models.Cotizacion.tenant_id == tenant_id,
    ).first()


def _get_tenant_guia(db: Session, tenant_id: int, guia_id: int):
    return db.query(models.GuiaRemision).options(
        joinedload(models.GuiaRemision.items),
        joinedload(models.GuiaRemision.cotizacion).joinedload(models.Cotizacion.cliente),
        joinedload(models.GuiaRemision.usuario).joinedload(models.User.tenant),
        joinedload(models.GuiaRemision.dispatch).joinedload(models.SaleDispatch.lines),
    ).filter(
        models.GuiaRemision.id == guia_id,
        models.GuiaRemision.tenant_id == tenant_id,
    ).first()


def _stored_sale_rejection(document, payload):
    """Only a readable rejection CDR matching document and issuer is terminal."""
    if not document.sunat_cdr_content:
        return None
    company = payload.get("company") if isinstance(payload, dict) else None
    if not isinstance(company, dict) or not company.get("ruc"):
        return None
    try:
        root = ET.fromstring(document.sunat_cdr_content)
        issuer = root.findtext(".//cac:ReceiverParty/cac:PartyIdentification/cbc:ID", namespaces=smartpse_response.NS)
        if str(issuer or "").strip() != str(company["ruc"]).strip():
            return None
        smartpse_response.validate_sale_cdr(document.sunat_cdr_content, payload)
    except smartpse_client.SmartPSEDefinitiveRejection as exc:
        return facturacion_service.FacturacionRejectedException(str(exc),
            {"cdr": document.sunat_cdr_content, "recovery_source": "inkora_existing_cdr"})
    except (ET.ParseError, smartpse_client.SmartPSEException):
        pass
    return None


def _sale_response_payload(job, document, tenant):
    prepared = (job.payload_snapshot or {}).get("prepared_sale") or {}
    return prepared.get("payload") or fiscal_evidence_service.expected_sale_payload(document, tenant)


def _lock_sale_response_document(db, job, document, tenant, response, *, api_failure_recorded=False):
    """A late provider response cannot replace a locally proven rejection."""
    document = db.query(models.Cotizacion).filter_by(id=document.id, tenant_id=job.tenant_id).populate_existing().with_for_update().one()
    if not (document.estado == "facturada" and document.sunat_accepted):
        rejection = _stored_sale_rejection(document, fiscal_evidence_service.expected_sale_payload(document, tenant))
        if rejection:
            rejection.provider_response = response
            if response.get("api_transport_failure") is True and not api_failure_recorded:
                rejection.partial_result = {"api_transport_failure": True}
            raise rejection
    return document


def _matching_cdr_acceptance_conflict(document, payload, response):
    if not isinstance(response, dict):
        return None
    cdr = response.get("cdr_xml") or smartpse_response.extract_cdr_xml(response.get("provider_response") or response)
    if not cdr:
        return None
    try:
        root = ET.fromstring(cdr)
        issuer = root.findtext(".//cac:ReceiverParty/cac:PartyIdentification/cbc:ID", namespaces=smartpse_response.NS)
        if str(issuer or "").strip() != str(payload["company"]["ruc"]).strip():
            return None
        smartpse_response.validate_sale_cdr(cdr, payload)
    except (ET.ParseError, smartpse_client.SmartPSEException):
        return None
    return {"kind": "contradictory_cdr", "document_id": document.id,
        "identity": f"{document.serie}-{document.correlativo}", "issuer_ruc": str(payload["company"]["ruc"]),
        "stored_cdr_sha256": hashlib.sha256(document.sunat_cdr_content.encode()).hexdigest(),
        "received_cdr_sha256": hashlib.sha256(cdr.encode()).hexdigest()}


def _finish_stored_sale_rejection(db, job, document, payload, response):
    rejection = _stored_sale_rejection(document, payload)
    if not rejection:
        return False
    document.provider_verification_status = "rejected"
    document.sunat_error = document.sunat_error or str(rejection)
    document.provider_verification_error = document.provider_verification_error or str(rejection)
    inventory_service.release_document_holds(db, document, reason=document.sunat_error)
    conflict = _matching_cdr_acceptance_conflict(document, payload, response)
    if conflict:
        details = json.dumps(conflict, sort_keys=True)
        if not db.query(models.AuditLog.id).filter_by(action="fiscal_cdr_conflict", entity_type="cotizacion",
                entity_id=document.id, details=details).first():
            db.add(models.AuditLog(user_id=job.created_by_user_id, action="fiscal_cdr_conflict",
                entity_type="cotizacion", entity_id=document.id, details=details))
        previous = job.result_snapshot if isinstance(job.result_snapshot, dict) else {}
        job.result_snapshot = dict(previous, cdr_conflict=conflict)
    crud.mark_emission_job_failed(db, job.id,
        error_message="CDR contradictorios para el mismo documento; requiere conciliacion fiscal." if conflict else str(rejection),
        error_classification=EMISSION_ERROR_AMBIGUOUS if conflict else EMISSION_ERROR_TERMINAL)
    return True


def _sale_network_user(user):
    """Read the fiscal transport columns before committing the HTTP boundary."""
    tenant = user.tenant
    network_tenant = SimpleNamespace(**{
        key: getattr(tenant, key) for key in (
            "id", "business_ruc", "smartpse_company_id", "smartpse_environment",
            "smartpse_usuario_secundaria", "smartpse_token_acceso",
        )
    })
    return SimpleNamespace(id=user.id, tenant_id=user.tenant_id, tenant=network_tenant)


def _transition_uncertain_invoice(db, job):
    snapshot = dict(job.payload_snapshot or {})
    snapshot.pop("sign_only", None)
    if snapshot.get("retry_signed_after_not_found"):
        snapshot["send_started"] = True
        snapshot.pop("retry_signed_after_not_found", None)
    job.payload_snapshot = snapshot
    job.action = models.EMISSION_JOB_ACTION_CONSULT_FISCAL
    db.commit()


def _reconcile_uncertain_invoice(db, job, user):
    _transition_uncertain_invoice(db, job)
    return _process_consult_fiscal_job(db, job, user)


def _process_emit_fiscal_job(
    db: Session,
    job: models.DocumentEmissionJob,
    user: models.User,
) -> dict:
    fiscal_document = _get_tenant_cotizacion(db, job.tenant_id, job.resource_id)
    if not fiscal_document:
        raise RuntimeError("No se encontró el documento fiscal a emitir.")

    payload_snapshot = job.payload_snapshot or {}
    guarded_invoice = job.provider == "smartpse" and fiscal_document.tipo_comprobante == "01"
    if guarded_invoice and (not fiscal_submission_state.can_submit(payload_snapshot)
                            or not payload_snapshot.get("prepared_sale")):
        return _reconcile_uncertain_invoice(db, job, user)
    if fiscal_recovery_service.enabled_for_job(job) and fiscal_document.tipo_comprobante == "01":
        return _process_recoverable_invoice(db, job, user, fiscal_document)
    network_user = user
    if guarded_invoice:
        network_user = _sale_network_user(user)
        payload_snapshot = fiscal_submission_state.mark_possible(payload_snapshot)
        job.payload_snapshot = payload_snapshot
    emission_leases.before_provider(db)
    result = facturacion_service.emitir_factura(
        fiscal_document,
        db,
        network_user,
        tipo_doc_override=payload_snapshot.get("tipo_comprobante"),
        prepared_sale=payload_snapshot.get("prepared_sale"),
    )
    emission_leases.check(db, result)
    fiscal_document = _lock_sale_response_document(db, job, fiscal_document, user.tenant, result)
    if result.get("pending"):
        prepared = payload_snapshot.get("prepared_sale") or {}
        fiscal_evidence_service.retain_sale_evidence(db, fiscal_document,
            result.get("provider_response") or {},
            payload=prepared.get("payload") or fiscal_evidence_service.expected_sale_payload(fiscal_document, user.tenant),
            partial_result=result)
    fiscal_document = _lock_sale_response_document(db, job, fiscal_document, user.tenant, result)
    persisted_document = crud.guardar_respuesta_sunat(
        db,
        fiscal_document.id,
        result,
        tenant_id=job.tenant_id,
    )

    if result.get("cdr_xml") and persisted_document:
        try:
            _run_async_syncsafe(
                fiscal_artifact_service.persist_cdr_artifact(
                    db,
                    persisted_document,
                    result.get("cdr_xml"),
                )
            )
        except Exception as cdr_err:
            logger.warning(
                "cdr_artifact_persist_failed_but_emission_ok",
                extra={
                    "event": "cdr_artifact_persist_failed_but_emission_ok",
                    "context": f"document_id={fiscal_document.id}",
                    "error": str(cdr_err),
                },
            )

    # PDF generation is a side-effect; failure should not mark the fiscal job as failed.
    try:
        _run_async_syncsafe(pdf_storage_service.process_pdf_background(fiscal_document.id, job.tenant_id))
    except Exception as pdf_err:
        logger.error(
            "pdf_generation_failed_but_emission_ok",
            extra={
                "event": "pdf_generation_failed_but_emission_ok",
                "context": f"document_id={fiscal_document.id}",
                "error": str(pdf_err),
            },
        )
    return result


def _panel_retry_enabled(job, tenant):
    snapshot = job.payload_snapshot
    return (
        isinstance(snapshot, dict) and type(snapshot.get("submission_state_version")) is int
        and snapshot.get("submission_state_version") == fiscal_submission_state.VERSION
        and snapshot.get("submission_phase") == fiscal_submission_state.POSSIBLE_SUBMISSION
        and snapshot.get("send_started") is True and snapshot.get("recovery_flow") is True
        and job.provider == "smartpse" and job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
        and job.resource_type == models.EMISSION_JOB_RESOURCE_COTIZACION
        and smartpse_panel_client.retry_enabled_for_tenant(job.tenant_id)
        and smartpse_panel_client.enabled_for_tenant(job.tenant_id)
        and fiscal_recovery_service.enabled(job.tenant_id)
        and tenant and tenant.id == job.tenant_id
    )


def _panel_retry_xml(job, document, tenant):
    if (document.tenant_id != job.tenant_id or document.document_kind != "fiscal_document"
            or document.tipo_comprobante != "01" or document.estado in {"facturada", "anulada"}
            or document.sunat_accepted or document.provider_verification_status == "rejected"
            or document.sunat_cdr_content or document.sunat_cdr_url
            or not fiscal_evidence_service.has_deliverable_xml(document)):
        return None
    prepared = (job.payload_snapshot or {}).get("prepared_sale")
    if not isinstance(prepared, dict) or not isinstance(prepared.get("payload"), dict):
        return None
    payload = prepared["payload"]
    company = payload.get("company")
    if (not isinstance(company, dict)
            or prepared.get("provider_environment") not in {"demo", "produccion"}
            or prepared["provider_environment"] != tenant.smartpse_environment
            or str(payload.get("tipoDoc")) != "01"
            or str(company.get("ruc")) != str(tenant.business_ruc)
            or str(payload.get("serie")) != str(document.serie)
            or str(payload.get("correlativo")).lstrip("0") != str(document.correlativo).lstrip("0")
            or prepared.get("nombre_archivo") != facturacion_service.smartpse_ubl_service.build_smartpse_filename(payload)):
        return None
    try:
        fiscal_evidence_service.validate_signed_sale_xml(document.sunat_xml_content, payload)
    except smartpse_client.SmartPSEException:
        return None
    return document.sunat_xml_content


def _reserve_panel_retry_attempt(db, job_id, user_id, expected_xml, metadata,
                                 *, expected_previous_id=None, receipt=None):
    """Persist a fenced attempt under the document lock before allowing panel I/O."""
    if db.info.get("emission_lease", (None, None))[0] != job_id:
        return False
    emission_leases.check(db)
    job = crud.get_emission_job(db, job_id)
    user = db.query(models.User).options(joinedload(models.User.tenant).joinedload(models.Tenant.subscription)).filter_by(
        id=user_id, tenant_id=job.tenant_id).populate_existing().first()
    if not user or job.created_by_user_id != user.id or not _panel_retry_enabled(job, user.tenant):
        db.rollback()
        return False
    try:
        _ensure_user_can_run_emission_job(job, user)
        _ensure_tenant_can_run_emission_job(db, user.tenant)
        _ensure_provider_available_for_job(job, user.tenant)
        if user.tenant.fiscal_contingency_mode:
            db.rollback()
            return False
        fiscal_recovery_service.reserve_probe(db, user.tenant)
    except (NonRetryableEmissionValidationError, fiscal_recovery_service.ProviderPaused):
        db.rollback()
        return False
    # reserve_probe commits, so acquire both fences and the document lock anew.
    emission_leases.check(db)
    job = db.query(models.DocumentEmissionJob).filter_by(id=job_id).populate_existing().one()
    document = db.query(models.Cotizacion).filter_by(
        id=job.resource_id, tenant_id=job.tenant_id).populate_existing().with_for_update().first()
    user = db.query(models.User).options(joinedload(models.User.tenant).joinedload(models.Tenant.subscription)).filter_by(
        id=user_id, tenant_id=job.tenant_id).populate_existing().first()
    try:
        if not user or job.created_by_user_id != user.id or user.tenant.fiscal_contingency_mode:
            db.rollback()
            return False
        _ensure_user_can_run_emission_job(job, user)
        _ensure_tenant_can_run_emission_job(db, user.tenant)
        _ensure_provider_available_for_job(job, user.tenant)
        facturacion_service._smartpse_demo_mode(user)
    except (NonRetryableEmissionValidationError, facturacion_service.FacturacionException):
        db.rollback()
        return False
    if (not document or not _panel_retry_enabled(job, user.tenant)
            or _panel_retry_xml(job, document, user.tenant) != expected_xml
            or metadata.get("environment") != user.tenant.smartpse_environment
            or str(metadata.get("provider_company_id") or "") != str(user.tenant.smartpse_company_id or "")
            or metadata.get("xml_sha256") != hashlib.sha256(expected_xml.encode()).hexdigest()
            or metadata.get("state") != "error"
            or not smartpse_panel_client.transient_retry_error(metadata.get("provider_error_message"))
            or not str(metadata.get("provider_document_id") or "").isdigit()
            or int(metadata["provider_document_id"]) < 1):
        db.rollback()
        return False
    if fiscal_recovery_service.note_deadline_alert(db, job, document):
        db.rollback()
        return False
    response = document.provider_response if isinstance(document.provider_response, dict) else {}
    evidence = response.get("inkora_evidence") or {}
    eligible, previous = panel_retry_state.eligibility(db, job, document)
    if (not eligible or (previous or {}).get("id") != expected_previous_id
            or (previous and any(previous.get(key) != str(metadata.get(key))
                for key in ("environment", "xml_sha256", "provider_company_id", "provider_document_id")))):
        db.rollback()
        return False
    marker = {"version": 1, "id": str(uuid4()), "state": "possible_submission", "job_id": job.id,
              "sequence": previous["sequence"] + 1 if previous else 1,
              "previous_attempt_id": previous["id"] if previous else None,
              "started_at": emission_leases.db_now(db).isoformat(),
              "environment": metadata["environment"], "xml_sha256": metadata["xml_sha256"],
              "provider_company_id": str(metadata["provider_company_id"]),
              "provider_document_id": str(metadata["provider_document_id"])}
    job.payload_snapshot = dict(job.payload_snapshot, panel_retry_attempt=marker)
    document.provider_response = dict(response, inkora_evidence=dict(evidence, panel_retry_attempt=marker))
    db.add(models.AuditLog(user_id=user.id, action="fiscal_panel_retry_started", entity_type="cotizacion",
        entity_id=document.id, details=json.dumps(marker, sort_keys=True)))
    emission_leases.before_provider(db)  # Last operation: fenced commit, no ORM reads before POST.
    if receipt is not None:
        receipt.update(marker)
    return True


def _complete_panel_retry_attempt(db, job_id, receipt, response):
    """Only the synchronous result of this reserved POST can complete its marker."""
    outcome = response.get("panel_retry_outcome")
    if (not receipt or response.get("panel_retry_attempted") is not True
            or response.get("panel_retry_status") != "confirmed_transient_failure"
            or type(response.get("provider_status_code")) is not int
            or response["provider_status_code"] != 200
            or not isinstance(outcome, dict)
            or set(outcome) != {"source", "response_sha256", "message"}
            or outcome.get("source") != "retry_response"
            or not isinstance(outcome.get("response_sha256"), str)
            or len(outcome["response_sha256"]) != 64
            or any(ch not in "0123456789abcdef" for ch in outcome["response_sha256"])
            or not smartpse_panel_client.confirmed_transient_retry_error(outcome.get("message"))):
        return None
    if db.info.get("emission_lease", (None, None))[0] != job_id:
        return None
    emission_leases.check(db, response)
    job = db.query(models.DocumentEmissionJob).filter_by(id=job_id).populate_existing().one()
    document = db.query(models.Cotizacion).filter_by(
        id=job.resource_id, tenant_id=job.tenant_id).populate_existing().with_for_update().one()
    provider_response = document.provider_response if isinstance(document.provider_response, dict) else {}
    evidence = provider_response.get("inkora_evidence")
    if (not isinstance(evidence, dict) or evidence.get("panel_retry_attempt") != receipt
            or (job.payload_snapshot or {}).get("panel_retry_attempt") != receipt
            or receipt.get("state") != "possible_submission"
            or document.sunat_accepted or document.sunat_cdr_content or document.sunat_cdr_url
            or document.estado in {"facturada", "anulada"}
            or document.provider_verification_status == "rejected"):
        return None
    now = emission_leases.db_now(db)
    marker = dict(receipt, state="confirmed_transient_failure", completed_at=now.isoformat(),
                  next_retry_at=(now + timedelta(seconds=fiscal_recovery_service.retry_seconds(
                      receipt["sequence"]))).isoformat(), outcome=dict(outcome))
    job.payload_snapshot = dict(job.payload_snapshot, panel_retry_attempt=marker)
    document.provider_response = dict(provider_response, inkora_evidence=dict(evidence, panel_retry_attempt=marker))
    db.add(models.AuditLog(user_id=job.created_by_user_id, action="fiscal_panel_retry_completed",
        entity_type="cotizacion", entity_id=document.id, details=json.dumps(marker, sort_keys=True)))
    emission_leases.before_provider(db)
    return marker


def _try_panel_invoice_retry(db, job, user, document, pending_error):
    partial = pending_error.partial_result
    if (db.info.get("emission_lease", (None, None))[0] != job.id
            or not isinstance(partial, dict) or partial.get("pending") is not True
            or not _panel_retry_enabled(job, user.tenant)):
        return None
    xml = _panel_retry_xml(job, document, user.tenant)
    eligible, previous = panel_retry_state.eligibility(db, job, document)
    if (not xml or not eligible
            or fiscal_recovery_service.note_deadline_alert(db, job, document)):
        return None
    prepared = job.payload_snapshot["prepared_sale"]
    job_id, user_id = job.id, user.id
    network_user = _sale_network_user(user)
    emission_leases.before_provider(db)  # The client's listing/XML reads also run outside SQL transactions.
    metadata = {"recovery_source": "smartpse_panel"}
    receipt = {}
    if partial.get("api_transport_failure") is True:
        metadata["api_transport_failure"] = True
    try:
        response = smartpse_panel_client.get_default_client().retry_invoice(
            network_user.tenant, prepared["nombre_archivo"], environment=prepared["provider_environment"],
            expected_xml=xml, before_submit=lambda state: _reserve_panel_retry_attempt(
                db, job_id, user_id, xml, state,
                expected_previous_id=(previous or {}).get("id"), receipt=receipt))
    except smartpse_client.SmartPSEException as exc:
        if (getattr(exc, "response_data", None) or {}).get("panel_retry_attempted") is not True:
            return None
        response = exc.response_data
    emission_leases.check(db, response)
    if response.get("cdr"):
        verified = facturacion_service.validate_sale_response_xml(prepared["payload"], response, frozen_xml=xml)
        try:
            result = smartpse_response.build_smartpse_result(prepared["payload"], verified,
                endpoint="smartpse_panel_retry_reconciliation", status_code=200, require_cdr=True)
        except smartpse_client.SmartPSEDefinitiveRejection as exc:
            raise facturacion_service.FacturacionRejectedException(
                str(exc), verified, partial_result=metadata) from exc
        result.update(metadata, provider_verification_status="verified",
                      provider_verified_at=datetime.now().isoformat())
        return result
    if response.get("panel_retry_attempted") is not True:
        return None
    completed = _complete_panel_retry_attempt(db, job_id, receipt, response)
    if completed:
        metadata["panel_retry_next_at"] = completed["next_retry_at"]
    # An uncertain panel POST does not establish an API CPE outage. Preserve
    # only the API transport failure independently observed before this attempt.
    raise facturacion_service.FacturacionException(
        "Reintento del panel pendiente de CDR; se mantiene la conciliacion.",
        response, partial_result=dict(metadata, pending=True, xml=xml))


def _process_consult_fiscal_job(
    db: Session,
    job: models.DocumentEmissionJob,
    user: models.User,
) -> dict:
    """Recover CDR first; an explicitly enrolled invoice may retry through its panel record."""
    fiscal_document = _get_tenant_cotizacion(db, job.tenant_id, job.resource_id)
    if not fiscal_document:
        raise RuntimeError("No se encontró el documento fiscal a conciliar.")

    payload_snapshot = job.payload_snapshot or {}
    probe_token = None
    if fiscal_recovery_service.enabled_for_job(job):
        probe_token = fiscal_recovery_service.reserve_probe(db, user.tenant)
    fiscal_recovery_service.note_deadline_alert(db, job, fiscal_document)
    network_document, network_user = fiscal_document, user
    if payload_snapshot.get("prepared_sale"):
        # Frozen lookups need no ORM relationships after the network boundary.
        network_tenant = SimpleNamespace(**{
            key: getattr(user.tenant, key) for key in (
                "id", "business_ruc", "smartpse_company_id", "smartpse_environment",
                "smartpse_usuario_secundaria", "smartpse_token_acceso",
            )
        })
        network_document = SimpleNamespace(**{
            key: getattr(fiscal_document, key) for key in (
                "id", "tenant_id", "tipo_comprobante", "serie", "correlativo", "sunat_xml_content",
            )
        })
        network_user = SimpleNamespace(id=user.id, tenant_id=user.tenant_id, tenant=network_tenant)
    db.commit()  # never hold an SQL transaction during provider consultation
    emission_leases.before_provider(db)
    # Smart PSE can return 404 even for an accepted invoice. Only positively
    # identified panel failures may enter the independently gated retry path.
    try:
        result = facturacion_service.consultar_documento_fiscal(
            network_document, network_user, tipo_doc_override=payload_snapshot.get("tipo_comprobante"),
            prepared_sale=payload_snapshot.get("prepared_sale"))
    except facturacion_service.FacturacionException as exc:
        if isinstance(exc, facturacion_service.FacturacionRejectedException):
            raise
        result = _try_panel_invoice_retry(db, job, user, fiscal_document, exc)
        if result is None:
            raise
    emission_leases.check(db, result)
    api_failure_recorded = False
    if fiscal_recovery_service.enabled_for_job(job):
        if result.get("api_transport_failure") is True:
            fiscal_recovery_service.service_failed(db, user.tenant, token=probe_token)
            api_failure_recorded = True
        elif result.get("recovery_source") != "smartpse_panel":
            fiscal_recovery_service.service_recovered(db, user.tenant, token=probe_token)
    if result.get("recovery_source") == "smartpse_panel" and not fiscal_document.sunat_xml_content:
        fiscal_document = _lock_sale_response_document(db, job, fiscal_document, user.tenant, result,
            api_failure_recorded=api_failure_recorded)
        if not fiscal_evidence_service.retain_sale_evidence(db, fiscal_document,
                result.get("provider_response") or {},
                payload=payload_snapshot["prepared_sale"]["payload"], partial_result=result):
            raise facturacion_service.FacturacionException("No se pudo conservar el XML firmado recuperado.",
                result.get("provider_response"), partial_result=result)
    fiscal_document = _lock_sale_response_document(db, job, fiscal_document, user.tenant, result,
        api_failure_recorded=api_failure_recorded)
    persisted_document = crud.guardar_respuesta_sunat(
        db,
        fiscal_document.id,
        result,
        tenant_id=job.tenant_id,
    )

    if result.get("cdr_xml") and persisted_document:
        try:
            _run_async_syncsafe(
                fiscal_artifact_service.persist_cdr_artifact(
                    db,
                    persisted_document,
                    result.get("cdr_xml"),
                )
            )
        except Exception as cdr_err:
            logger.warning(
                "cdr_artifact_persist_failed_but_reconciliation_ok",
                extra={
                    "event": "cdr_artifact_persist_failed_but_reconciliation_ok",
                    "context": f"document_id={fiscal_document.id}",
                    "error": str(cdr_err),
                },
            )

    try:
        _run_async_syncsafe(
            pdf_storage_service.process_pdf_background(fiscal_document.id, job.tenant_id)
        )
    except Exception as pdf_err:
        logger.error(
            "pdf_generation_failed_but_reconciliation_ok",
            extra={
                "event": "pdf_generation_failed_but_reconciliation_ok",
                "context": f"document_id={fiscal_document.id}",
                "error": str(pdf_err),
            },
        )
    return result


def _process_recoverable_invoice(db, job, user, document):
    snapshot = dict(job.payload_snapshot or {})
    if not fiscal_submission_state.can_submit(snapshot) or not snapshot.get("prepared_sale"):
        return _reconcile_uncertain_invoice(db, job, user)
    if not snapshot.get("recovery_flow"):
        snapshot["recovery_flow"] = True
        job.payload_snapshot = dict(snapshot)
        db.commit()
    prepared = snapshot.get("prepared_sale")
    client = smartpse_client.get_default_client()
    demo = facturacion_service._smartpse_demo_mode(user)
    if fiscal_recovery_service.note_deadline_alert(db, job, document):
        raise NonRetryableEmissionValidationError("Vencio el plazo de envio de la factura; requiere revision fiscal.")
    if not fiscal_evidence_service.has_deliverable_xml(document):
        sign_probe = fiscal_recovery_service.reserve_probe(db, user.tenant, service="cpe:sign")
        snapshot["sign_only"] = True
        job.payload_snapshot = dict(snapshot)
        network_user = _sale_network_user(user)
        emission_leases.before_provider(db)
        response = client.sign_xml(network_user.tenant, prepared["nombre_archivo"], prepared["unsigned_xml"], demo=demo)
        emission_leases.check(db, response)
        if not fiscal_evidence_service.retain_sale_evidence(db, document, response, payload=prepared["payload"]):
            raise facturacion_service.FacturacionException("Evidencia XML invalida: no se obtuvo firma verificable.", response)
        document.provider_verification_status = "signed_pending"
        snapshot["signed_ready"] = True
        job.payload_snapshot = dict(snapshot)
        db.commit()
        fiscal_recovery_service.service_recovered(db, user.tenant, token=sign_probe, service="cpe:sign")
        try:
            _run_async_syncsafe(pdf_storage_service.process_pdf_background(document.id, job.tenant_id))
        except Exception:
            logger.exception("signed_invoice_pdf_pending document_id=%s", document.id)
    if fiscal_recovery_service.note_deadline_alert(db, job, document):
        raise NonRetryableEmissionValidationError("Vencio el plazo de envio de la factura; requiere revision fiscal.")
    if user.tenant.fiscal_contingency_mode:
        raise fiscal_recovery_service.ProviderPaused(emission_leases.db_now(db) + timedelta(seconds=settings.FISCAL_RECOVERY_MAX_SECONDS))
    token = fiscal_recovery_service.reserve_probe(db, user.tenant)
    snapshot = fiscal_submission_state.mark_possible(job.payload_snapshot or {})
    snapshot["send_count"] = int(snapshot.get("send_count") or 0) + 1
    job.payload_snapshot = snapshot
    network_user = _sale_network_user(user)
    signed_xml = document.sunat_xml_content
    emission_leases.before_provider(db)
    response = client.send_signed_xml(network_user.tenant, prepared["nombre_archivo"], signed_xml, demo=demo)
    response = dict(response)
    try:
        response = facturacion_service.validate_sale_response_xml(
            prepared["payload"], response, frozen_xml=signed_xml)
        result = smartpse_response.build_smartpse_result(prepared["payload"], response,
            endpoint="/api/cpe/enviar-demo" if demo else "/api/cpe/enviar", status_code=200, require_cdr=True)
    except smartpse_client.SmartPSEDefinitiveRejection as exc:
        raise facturacion_service.FacturacionRejectedException(str(exc), response) from exc
    if not result.get("pending"):
        result["provider_verification_status"] = "verified"
        result["provider_verified_at"] = datetime.now().isoformat()
        fiscal_recovery_service.service_recovered(db, user.tenant, token=token)
    emission_leases.check(db, result)
    document = _lock_sale_response_document(db, job, document, user.tenant, result)
    persisted = crud.guardar_respuesta_sunat(db, document.id, result, tenant_id=job.tenant_id)
    if result.get("cdr_xml") and persisted:
        try:
            _run_async_syncsafe(fiscal_artifact_service.persist_cdr_artifact(db, persisted, result["cdr_xml"]))
        except Exception:
            logger.exception("cdr_artifact_persist_pending document_id=%s", document.id)
    return result


def _process_emit_note_job(
    db: Session,
    job: models.DocumentEmissionJob,
    user: models.User,
) -> dict:
    nota = _get_tenant_cotizacion(db, job.tenant_id, job.resource_id)
    if not nota:
        raise RuntimeError("No se encontró la nota a emitir.")
    doc_afectado = nota.nota_referencia
    if not doc_afectado:
        raise RuntimeError("La nota no tiene documento afectado referenciado.")

    payload_snapshot = job.payload_snapshot or {}
    try:
        doc_afectado = db.query(models.Cotizacion).filter_by(
            id=doc_afectado.id, tenant_id=job.tenant_id,
        ).populate_existing().with_for_update().one()
        void_recovery_service.ensure_note_source_available(db, doc_afectado)
        ensure_credit_note_within_available_amount(db, job.tenant_id, nota.id)
    except ValueError as exc:
        crud.guardar_error_sunat(db, nota.id, str(exc), tenant_id=job.tenant_id)
        _raise_non_retryable_validation(str(exc))

    emission_leases.before_provider(db)
    result = facturacion_service.emitir_nota(
        nota=nota,
        doc_afectado=doc_afectado,
        user=user,
        cod_motivo=payload_snapshot.get("cod_motivo"),
        descripcion=payload_snapshot.get("descripcion_motivo"),
        tipo_nota=payload_snapshot.get("tipo_nota"),
    )
    emission_leases.check(db, result)
    updated_note = crud.guardar_respuesta_sunat(db, nota.id, result, tenant_id=job.tenant_id)
    if result.get("cdr_xml") and updated_note:
        try:
            _run_async_syncsafe(
                fiscal_artifact_service.persist_cdr_artifact(
                    db,
                    updated_note,
                    result.get("cdr_xml"),
                )
            )
        except Exception as cdr_err:
            logger.warning(
                "cdr_artifact_persist_failed_but_emission_ok",
                extra={
                    "event": "cdr_artifact_persist_failed_but_emission_ok",
                    "context": f"document_id={nota.id}",
                    "error": str(cdr_err),
                },
            )
    if (
        result.get("success")
        and updated_note
        and updated_note.estado != "facturada"
    ):
        _raise_non_retryable_validation(
            updated_note.sunat_error or "La nota no pudo marcarse como aceptada."
        )
    # PDF generation is a side-effect; failure should not mark the job as failed.
    try:
        _run_async_syncsafe(pdf_storage_service.process_pdf_background(nota.id, job.tenant_id))
    except Exception as pdf_err:
        logger.error(
            "pdf_generation_failed_but_emission_ok",
            extra={
                "event": "pdf_generation_failed_but_emission_ok",
                "context": f"document_id={nota.id}",
                "error": str(pdf_err),
            },
        )
    return result


def _process_void_fiscal_job(
    db: Session,
    job: models.DocumentEmissionJob,
    user: models.User,
) -> dict:
    comprobante = _get_tenant_cotizacion(db, job.tenant_id, job.resource_id)
    if not comprobante:
        raise RuntimeError("No se encontró el comprobante a anular.")

    try:
        void_recovery_service.ensure_no_active_notes(db, comprobante)
        inventory_service.ensure_document_void_inventory_safe(db, comprobante)
        if sale_dispatch_service.active_dispatch_allocation_exists(db, comprobante.tenant_id, comprobante.id):
            raise ValueError("La baja requiere resolver antes las reservas o cobertura GRE.")
    except ValueError as exc:
        _raise_non_retryable_validation(str(exc))
    try:
        result = void_recovery_service.process(db, job, comprobante, user)
    except ValueError as exc:
        _raise_non_retryable_validation(str(exc))
    emission_leases.check(db, result)
    if result.get("success") and not result.get("pending"):
        crud.anular_cotizacion(db, comprobante.id, tenant_id=job.tenant_id)
    return result


def _process_emit_guide_job(
    db: Session,
    job: models.DocumentEmissionJob,
    user: models.User,
) -> dict:
    guia = _get_tenant_guia(db, job.tenant_id, job.resource_id)
    if not guia:
        raise RuntimeError("No se encontró la guía a emitir.")

    try:
        validation = sale_dispatch_service.validate_guide_for_emission(db, guia)
        if not validation["valid"]:
            messages = "; ".join(error["message"] for error in validation["errors"])
            _raise_non_retryable_validation(messages)
        if not guia.frozen_payload or not guia.frozen_xml:
            _raise_non_retryable_validation("La guía no tiene payload/XML congelado antes del encolado.")
        # End the short validation locks before the external HTTP call.
        db.commit()
        emission_leases.before_provider(db)
        result = facturacion_service.emitir_guia_remision(
            guia, user, prepared_payload=guia.frozen_payload, prepared_xml=guia.frozen_xml
        )
        emission_leases.check(db, result)
        sale_dispatch_service.lock_guide_result_scope(db, guia)
        persisted = crud.guardar_respuesta_sunat_gre(
            db, guia.id, result, tenant_id=job.tenant_id, commit=False
        )
        if result.get("success") and not result.get("pending"):
            sale_dispatch_service.apply_guide_result(db, persisted, accepted=True)
        elif not result.get("success"):
            sale_dispatch_service.apply_guide_result(db, persisted, accepted=False, rejected=True)
        db.commit()
        return result
    except facturacion_service.FacturacionRejectedException as exc:
        emission_leases.check(db, exc.provider_response)
        sale_dispatch_service.lock_guide_result_scope(db, guia)
        guia.estado = "rechazada"
        guia.sunat_error = str(exc)
        guia.provider_response = exc.provider_response
        guia.rejected_at = datetime.now()
        sale_dispatch_service.apply_guide_result(db, guia, accepted=False, rejected=True)
        db.commit()
        raise
    except emission_leases.LeaseLost:
        raise
    except Exception as exc:
        emission_leases.check(db)
        crud.guardar_error_sunat_gre(db, guia.id, str(exc), tenant_id=job.tenant_id)
        raise


def _process_consult_guide_job(db: Session, job: models.DocumentEmissionJob, user: models.User) -> dict:
    """Reconcile an already submitted guide. This path never calls /despatch/send."""
    guia = _get_tenant_guia(db, job.tenant_id, job.resource_id)
    if not guia:
        raise RuntimeError("No se encontró la guía a conciliar.")
    db.commit()  # never keep an SQL transaction open during provider consultation
    try:
        emission_leases.before_provider(db)
        result = facturacion_service.consultar_guia_remision(guia, user)
    except facturacion_service.FacturacionRejectedException as exc:
        emission_leases.check(db, exc.provider_response)
        sale_dispatch_service.lock_guide_result_scope(db, guia)
        guia.estado = "rechazada"
        guia.sunat_error = str(exc)
        guia.provider_response = exc.provider_response
        guia.rejected_at = datetime.now()
        sale_dispatch_service.apply_guide_result(db, guia, accepted=False, rejected=True)
        db.commit()
        raise
    emission_leases.check(db, result)
    sale_dispatch_service.lock_guide_result_scope(db, guia)
    persisted = crud.guardar_respuesta_sunat_gre(
        db, guia.id, result, tenant_id=job.tenant_id, commit=False
    )
    if result.get("success") and not result.get("pending"):
        sale_dispatch_service.apply_guide_result(db, persisted, accepted=True)
    db.commit()
    return result


def _process_emission_job(job_id: int, *, db_session: Session | None = None) -> bool:
    db = db_session or SessionLocal()
    owns_session = db_session is None
    tenant_token = None
    try:
        job = crud.get_emission_job(db, job_id)
        if not job:
            logger.warning(
                "emission_job_missing",
                extra={"event": "emission_job_missing", "context": f"job_id={job_id}"},
            )
            return False

        if job.lease_token and db.info.get("emission_lease") != (job.id, job.lease_token):
            raise emission_leases.LeaseLost()
        if job.payload_snapshot is not None and not isinstance(job.payload_snapshot, dict):
            raise NonRetryableEmissionValidationError("Snapshot fiscal no reconocido; requiere revisión.")
        tenant_token = _apply_optional_tenant_context(db, job.tenant_id)
        user = _load_job_user(db, job)
        if not user:
            raise RuntimeError("No se encontró un usuario del tenant para ejecutar la emisión.")
        crud.mark_emission_job_attempt_started(db, job.id)
        db.expire(job)
        job = crud.get_emission_job(db, job.id)
        if job.provider == "smartpse" and job.action == models.EMISSION_JOB_ACTION_EMIT_FISCAL:
            document = _get_tenant_cotizacion(db, job.tenant_id, job.resource_id)
            if document and document.tipo_comprobante == "01":
                snapshot = job.payload_snapshot or {}
                if not fiscal_submission_state.can_submit(snapshot) or not snapshot.get("prepared_sale"):
                    # Change only the action before checking the execution
                    # context. Reconciliation keeps its existing tenant checks
                    # and cannot submit, even if the creator is now inactive.
                    _transition_uncertain_invoice(db, job)
        _validate_job_execution_context(db, job, user)

        if job.action == models.EMISSION_JOB_ACTION_EMIT_FISCAL:
            result = _process_emit_fiscal_job(db, job, user)
        elif job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL:
            result = _process_consult_fiscal_job(db, job, user)
        elif job.action == models.EMISSION_JOB_ACTION_EMIT_NOTE:
            result = _process_emit_note_job(db, job, user)
        elif job.action == models.EMISSION_JOB_ACTION_VOID_FISCAL:
            result = _process_void_fiscal_job(db, job, user)
        elif job.action == models.EMISSION_JOB_ACTION_EMIT_GUIDE:
            result = _process_emit_guide_job(db, job, user)
        elif job.action == models.EMISSION_JOB_ACTION_CONSULT_GUIDE:
            result = _process_consult_guide_job(db, job, user)
        else:
            raise RuntimeError(f"Acción de job no soportada: {job.action}")

        provider_ticket = result.get("ticket") or (result.get("sunat_response") or {}).get("ticket")
        if job.action in {models.EMISSION_JOB_ACTION_EMIT_FISCAL, models.EMISSION_JOB_ACTION_CONSULT_FISCAL}:
            persisted = _get_tenant_cotizacion(db, job.tenant_id, job.resource_id)
            if not persisted or persisted.estado != "facturada" or not persisted.sunat_accepted:
                result = dict(result, pending=True)
        if result.get("pending") and job.action in {models.EMISSION_JOB_ACTION_EMIT_FISCAL, models.EMISSION_JOB_ACTION_CONSULT_FISCAL}:
            job.provider_ticket = provider_ticket
            crud.mark_emission_job_retry(db, job.id,
                error_message="Pendiente de respuesta fiscal definitiva.",
                retry_in_seconds=fiscal_recovery_service.retry_seconds(job.attempts),
                error_classification=EMISSION_ERROR_AMBIGUOUS,
                action=models.EMISSION_JOB_ACTION_CONSULT_FISCAL)
        elif result.get("pending") and job.action == models.EMISSION_JOB_ACTION_VOID_FISCAL:
            job.provider_ticket = provider_ticket or job.provider_ticket
            crud.mark_emission_job_retry(db, job.id,
                error_message=result.get("confirmation_error") or "Baja pendiente de CDR definitivo; se consulta sin reenviar.",
                retry_in_seconds=fiscal_recovery_service.retry_seconds(job.attempts),
                error_classification=EMISSION_ERROR_AMBIGUOUS)
        elif result.get("pending"):
            crud.mark_emission_job_pending_confirmation(db, job.id,
                error_message="Smart PSE/SUNAT mantiene la guia pendiente de resultado definitivo.",
                error_classification=EMISSION_ERROR_AMBIGUOUS,
                result_snapshot=_build_job_result_snapshot(result), provider_ticket=provider_ticket)
        else:
            crud.mark_emission_job_succeeded(
                db,
                job.id,
                result_snapshot=_build_job_result_snapshot(result),
                provider_ticket=provider_ticket,
            )
        logger.info(
            "emission_job_succeeded",
            extra={"event": "emission_job_succeeded", "context": f"job_id={job.id} action={job.action}"},
        )
        return True
    except emission_leases.LeaseLost:
        raise
    except fiscal_recovery_service.ProviderPaused as exc:
        job = crud.get_emission_job(db, job_id)
        if job:
            seconds = max(1, int((exc.until - emission_leases.db_now(db)).total_seconds()))
            if (job.action == models.EMISSION_JOB_ACTION_EMIT_FISCAL
                    and fiscal_submission_state.can_submit(job.payload_snapshot)):
                document = _get_tenant_cotizacion(db, job.tenant_id, job.resource_id)
                if document and document.tipo_comprobante == "01":
                    remaining = max(1, int((fiscal_recovery_service.invoice_deadline(document)
                                          - emission_leases.db_now(db)).total_seconds()))
                    seconds = min(seconds, remaining)
            crud.mark_emission_job_retry(db, job.id, error_message=str(exc),
                retry_in_seconds=seconds, error_classification=EMISSION_ERROR_TRANSIENT)
        return False
    except NonRetryableEmissionValidationError as exc:
        emission_leases.check(db)
        message = str(exc)
        job = crud.get_emission_job(db, job_id)
        if job:
            crud.mark_emission_job_failed(
                db,
                job.id,
                error_message=message,
                error_classification=EMISSION_ERROR_VALIDATION,
            )
            logger.warning(
                "emission_job_validation_failed",
                extra={
                    "event": "emission_job_validation_failed",
                    "context": f"job_id={job.id}",
                },
            )
        return False
    except smartpse_client.SmartPSENotSubmitted as exc:
        emission_leases.check(db)
        job = crud.get_emission_job(db, job_id)
        if (job and job.action == models.EMISSION_JOB_ACTION_EMIT_FISCAL
                and fiscal_recovery_service.enabled_for_job(job)):
            snapshot = fiscal_submission_state.mark_not_submitted(job.payload_snapshot or {})
            snapshot.pop("sign_only", None)
            job.payload_snapshot = snapshot
            db.commit()
            crud.mark_emission_job_retry(db, job.id, error_message=str(exc),
                retry_in_seconds=fiscal_recovery_service.retry_seconds(job.attempts),
                error_classification=EMISSION_ERROR_TRANSIENT,
                action=models.EMISSION_JOB_ACTION_EMIT_FISCAL)
        else:
            raise
        return False
    except Exception as exc:
        emission_leases.check(db)
        message = str(exc)
        job = crud.get_emission_job(db, job_id)
        if job:
            error_classification = _classify_emission_error(message)
            sale_job = job.action in {models.EMISSION_JOB_ACTION_EMIT_FISCAL, models.EMISSION_JOB_ACTION_CONSULT_FISCAL}
            sign_only = (job.payload_snapshot or {}).get("sign_only") and not (job.payload_snapshot or {}).get("send_started")
            if sign_only and 400 <= (getattr(exc, "status_code", None) or 0) < 500:
                error_classification = EMISSION_ERROR_VALIDATION
            partial = getattr(exc, "partial_result", None)
            internal_api_failure = isinstance(partial, dict) and partial.get("api_transport_failure") is True
            api_failure_recorded = False
            if sale_job and not sign_only and internal_api_failure and fiscal_recovery_service.enabled_for_job(job):
                # This commits; record the outage before acquiring the document's terminal-state lock.
                fiscal_recovery_service.service_failed(db, user.tenant)
                api_failure_recorded = True
            if sale_job:
                document = _get_tenant_cotizacion(db, job.tenant_id, job.resource_id)
                if document:
                    document = db.query(models.Cotizacion).filter_by(id=document.id, tenant_id=job.tenant_id).populate_existing().with_for_update().one()
                    if document.estado == "facturada" and document.sunat_accepted:
                        crud.mark_emission_job_succeeded(db, job.id, result_snapshot={"success": True, "source": "existing_accepted_cdr"})
                        return True
                    payload = _sale_response_payload(job, document, user.tenant)
                    terminal_payload = fiscal_evidence_service.expected_sale_payload(document, user.tenant)
                    response = getattr(exc, "provider_response", None) or getattr(exc, "response_data", None) or {}
                    if _finish_stored_sale_rejection(db, job, document, terminal_payload, response):
                        return False
                    fiscal_evidence_service.retain_sale_evidence(db, document, response, payload=payload,
                        status_code=getattr(exc, "status_code", None), partial_result=getattr(exc, "partial_result", None))
                    document = db.query(models.Cotizacion).filter_by(id=document.id, tenant_id=job.tenant_id).populate_existing().with_for_update().one()
                    if document.estado == "facturada" and document.sunat_accepted:
                        crud.mark_emission_job_succeeded(db, job.id, result_snapshot={"success": True, "source": "existing_accepted_cdr"})
                        return True
                    terminal_payload = fiscal_evidence_service.expected_sale_payload(document, user.tenant)
                    if _finish_stored_sale_rejection(db, job, document, terminal_payload, response):
                        return False
                    if document.estado != "facturada":
                        document.sunat_error = message
                        document.provider_verification_status = "pending_confirmation"
                        document.provider_verification_error = message
                    db.commit()
                    if fiscal_evidence_service.has_deliverable_xml(document):
                        try:
                            _run_async_syncsafe(pdf_storage_service.process_pdf_background(document.id, job.tenant_id))
                        except Exception:
                            logger.exception("retained_invoice_pdf_pending document_id=%s", document.id)
            transport_error = ((getattr(exc, "status_code", None) or 0) >= 500
                or any(fragment in message.lower() for fragment in ("timeout", "timed out", "connection", "conexion", "conexión", "no se pudo conectar", "service unavailable", "servicio no disponible")))
            probe = (db.info.get("fiscal_probe") or (None, None))[1]
            provider_response = getattr(exc, "provider_response", None) or getattr(exc, "response_data", None) or {}
            partial_result = getattr(exc, "partial_result", None)
            api_transport_failure = (isinstance(partial_result, dict)
                                     and partial_result.get("api_transport_failure") is True)
            if api_transport_failure:
                transport_error = True
            if probe and str(provider_response.get("estado")) == "202":
                transport_error = True
            retry_signing = (
                sale_job and job.action == models.EMISSION_JOB_ACTION_EMIT_FISCAL
                and sign_only and transport_error
                and isinstance(exc, (smartpse_client.SmartPSEException, facturacion_service.FacturacionException))
                and not (400 <= (getattr(exc, "status_code", None) or 0) < 500)
                and fiscal_recovery_service.enabled_for_job(job)
                and fiscal_submission_state.can_submit(job.payload_snapshot)
            )
            if retry_signing:
                fiscal_recovery_service.service_failed(db, user.tenant, service="cpe:sign")
                if fiscal_recovery_service.note_deadline_alert(db, job, document):
                    crud.mark_emission_job_failed(db, job.id,
                        error_message="Vencio el plazo de firma/envio de la factura; requiere revision fiscal.",
                        error_classification=EMISSION_ERROR_VALIDATION)
                else:
                    remaining = max(1, int((fiscal_recovery_service.invoice_deadline(document)
                                          - emission_leases.db_now(db)).total_seconds()))
                    crud.mark_emission_job_retry(db, job.id, error_message=message,
                        retry_in_seconds=min(fiscal_recovery_service.retry_seconds(job.attempts), remaining),
                        error_classification=EMISSION_ERROR_TRANSIENT,
                        action=models.EMISSION_JOB_ACTION_EMIT_FISCAL)
                return False
            if (sale_job and transport_error and not api_failure_recorded
                    and fiscal_recovery_service.enabled_for_job(job) and not sign_only
                    and (api_transport_failure or provider_response.get("recovery_source") != "smartpse_panel")):
                fiscal_recovery_service.service_failed(db, user.tenant)
            should_reconcile_fiscal = (
                sale_job and not sign_only and not isinstance(exc, facturacion_service.FacturacionRejectedException)
                and (error_classification in {EMISSION_ERROR_AMBIGUOUS, EMISSION_ERROR_PROVIDER_POLICY, EMISSION_ERROR_TRANSIENT}
                     or ((job.payload_snapshot or {}).get("submission_phase") == fiscal_submission_state.POSSIBLE_SUBMISSION)
                     or transport_error or (job.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL
                                            and not isinstance(exc, facturacion_service.FacturacionRejectedException)))
            )
            if should_reconcile_fiscal:
                retry_in = fiscal_recovery_service.retry_seconds(job.attempts or 1)
                # Panel cooldown counts actual POSTs, not intervening CDR reads.
                # The reservation rechecks the durable deadline even if another
                # operation wakes this job early.
                if isinstance(partial_result, dict) and partial_result.get("panel_retry_next_at"):
                    retry_in = max(1, math.ceil((datetime.fromisoformat(
                        partial_result["panel_retry_next_at"]) - emission_leases.db_now(db)).total_seconds()))
                crud.mark_emission_job_retry(
                    db,
                    job.id,
                    error_message=message,
                    retry_in_seconds=retry_in,
                    error_classification=error_classification,
                    action=models.EMISSION_JOB_ACTION_CONSULT_FISCAL,
                )
            elif sale_job and isinstance(exc, facturacion_service.FacturacionRejectedException):
                # A rejection becomes definitive only with a matching rejection CDR.
                document = db.query(models.Cotizacion).filter_by(id=job.resource_id,
                    tenant_id=job.tenant_id).populate_existing().with_for_update().first()
                if document and document.estado == "facturada" and document.sunat_accepted:
                    crud.mark_emission_job_succeeded(db, job.id,
                        result_snapshot={"success": True, "source": "existing_accepted_cdr"})
                    return True
                if document and _finish_stored_sale_rejection(db, job, document,
                        fiscal_evidence_service.expected_sale_payload(document, user.tenant), provider_response):
                    return False
                cdr = smartpse_response.extract_cdr_xml(getattr(exc, "provider_response", None))
                confirmed = False
                if cdr and document:
                    payload = fiscal_evidence_service.expected_sale_payload(document, user.tenant)
                    confirmed = _stored_sale_rejection(SimpleNamespace(sunat_cdr_content=cdr), payload) is not None
                if confirmed:
                    document.sunat_cdr_content = cdr
                    document.provider_verification_status = "rejected"
                    inventory_service.release_document_holds(db, document, reason=message)
                    db.commit()
                    if (fiscal_recovery_service.enabled_for_job(job) and not api_failure_recorded
                            and provider_response.get("recovery_source") != "smartpse_panel"):
                        fiscal_recovery_service.service_recovered(db, user.tenant, token=probe)
                    crud.mark_emission_job_failed(db, job.id, error_message=message,
                        error_classification=EMISSION_ERROR_TERMINAL)
                else:
                    crud.mark_emission_job_retry(db, job.id, error_message=message,
                        retry_in_seconds=fiscal_recovery_service.retry_seconds(job.attempts),
                        error_classification=EMISSION_ERROR_AMBIGUOUS,
                        action=models.EMISSION_JOB_ACTION_CONSULT_FISCAL)
                logger.warning(
                    "emission_job_reconciliation_scheduled",
                    extra={
                        "event": "emission_job_reconciliation_scheduled",
                        "context": f"job_id={job.id} classification={error_classification}",
                    },
                )
            elif (
                error_classification in {
                    EMISSION_ERROR_AMBIGUOUS,
                    EMISSION_ERROR_PROVIDER_POLICY,
                }
                or _must_hold_exhausted_consultation(job, error_classification)
            ):
                crud.mark_emission_job_pending_confirmation(
                    db,
                    job.id,
                    error_message=message,
                    error_classification=error_classification,
                )
                logger.warning(
                    "emission_job_pending_confirmation job_id=%s action=%s classification=%s",
                    job.id,
                    job.action,
                    error_classification,
                    extra={
                        "event": "emission_job_pending_confirmation",
                        "context": (
                            f"job_id={job.id} action={job.action} "
                            f"classification={error_classification}"
                        ),
                    },
                )
            elif (
                (job.attempts or 0) < (job.max_attempts or settings.EMISSION_MAX_ATTEMPTS)
                and error_classification == EMISSION_ERROR_TRANSIENT
            ):
                retry_in = _retry_delay_seconds(job.attempts or 1)
                crud.mark_emission_job_retry(
                    db,
                    job.id,
                    error_message=message,
                    retry_in_seconds=retry_in,
                    error_classification=error_classification,
                )
                logger.warning(
                    "emission_job_retry_scheduled",
                    extra={
                        "event": "emission_job_retry_scheduled",
                        "context": f"job_id={job.id} retry_in={retry_in}s",
                    },
                )
            else:
                crud.mark_emission_job_failed(
                    db,
                    job.id,
                    error_message=message,
                    error_classification=error_classification,
                )
                logger.error(
                    "emission_job_failed job_id=%s action=%s classification=%s",
                    job.id,
                    job.action,
                    error_classification,
                    extra={
                        "event": "emission_job_failed",
                        "context": (
                            f"job_id={job.id} action={job.action} "
                            f"classification={error_classification}"
                        ),
                    },
                )
        return False
    finally:
        db.info.pop("fiscal_probe", None)
        db.info.pop("fiscal_sign_probe", None)
        if tenant_token is not None:
            reset_tenant_context(tenant_token)
        if owns_session:
            db.close()


def process_emission_job(job_id: int, *, db_session: Session | None = None, lease_token: str | None = None) -> bool:
    db = db_session or SessionLocal()
    try:
        if lease_token:
            emission_leases.attach(db, job_id, lease_token)
        return _process_emission_job(job_id, db_session=db)
    except emission_leases.LeaseLost as exc:
        db.rollback()
        emission_leases.detach(db)
        if lease_token:
            snapshot = _build_job_result_snapshot(exc.result) if isinstance(exc.result, dict) else None
            emission_leases.record_late_result(db, job_id, lease_token, snapshot)
        logger.warning("emission_lease_lost", extra={"event": "emission_lease_lost", "context": f"job_id={job_id}"})
        return False
    finally:
        emission_leases.detach(db)
        if db_session is None:
            db.close()


def process_next_available_job(*, db_session: Session | None = None) -> bool:
    db = db_session or SessionLocal()
    owns_session = db_session is None
    try:
        stale_before = datetime.now() - timedelta(
            seconds=max(settings.EMISSION_PROCESSING_TIMEOUT_SECONDS, 30)
        )
        crud.recover_stale_processing_jobs(db, stale_before=stale_before)
        crud.recover_pending_fiscal_reconciliations(db)
        job = crud.claim_next_emission_job(db)
        if not job:
            return False
        return process_emission_job(job.id, db_session=db)
    finally:
        if owns_session:
            db.close()


def _recover_stale_jobs(db: Session) -> int:
    stale_before = datetime.now() - timedelta(
        seconds=max(settings.EMISSION_PROCESSING_TIMEOUT_SECONDS, 30)
    )
    return crud.recover_stale_processing_jobs(db, stale_before=stale_before)


def _recover_stale_jobs_if_due(
    db: Session,
    *,
    now_monotonic: float,
    next_recovery_at: float,
    recovery_interval_seconds: int,
) -> float:
    """Recover stale jobs on a separate cadence from normal queue polling."""
    if now_monotonic < next_recovery_at:
        return next_recovery_at

    _recover_stale_jobs(db)
    recovered = crud.recover_pending_fiscal_reconciliations(db)
    if recovered:
        logger.info(
            "pending_fiscal_reconciliations_requeued",
            extra={
                "event": "pending_fiscal_reconciliations_requeued",
                "context": f"count={recovered}",
            },
        )
    return now_monotonic + recovery_interval_seconds


def _process_single_job(job_id: int, lease_token: str | None = None) -> None:
    """Wrapper para ejecutar un job en un thread del pool."""
    try:
        process_emission_job(job_id, lease_token=lease_token)
    except Exception:
        logger.exception(
            "worker_thread_unexpected_error",
            extra={"event": "worker_thread_unexpected_error", "context": f"job_id={job_id}"},
        )


def run_worker_loop() -> None:
    from services.emission_worker_runtime import run
    run()
