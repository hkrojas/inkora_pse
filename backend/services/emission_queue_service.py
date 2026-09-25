"""services/emission_queue_service.py — Cola durable para emisión fiscal."""
import asyncio
import signal
import threading
from datetime import datetime, timedelta
from threading import Thread

from sqlalchemy.orm import Session, joinedload

import crud
import models
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


def resolve_emission_mode(requested_mode: str | None = None) -> str:
    mode_candidate = requested_mode if isinstance(requested_mode, str) else None
    mode = (mode_candidate or settings.EMISSION_MODE_DEFAULT or EMISSION_MODE_SYNC).strip().lower()
    if mode not in {EMISSION_MODE_SYNC, EMISSION_MODE_ASYNC}:
        raise ValueError("Modo de emision invalido. Use 'sync' o 'async'.")
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


def _initial_cpe_job_status(user: models.User) -> str:
    tenant = getattr(user, "tenant", None)
    if tenant and bool(getattr(tenant, "fiscal_contingency_mode", False)):
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
            payload_snapshot={"tipo_comprobante": tipo_comprobante},
            provider=provider,
            target_status=initial_status,
        )
        return existing, False

    job = crud.create_emission_job(
        db,
        tenant_id=fiscal_document.tenant_id,
        created_by_user_id=user.id,
        resource_type=models.EMISSION_JOB_RESOURCE_COTIZACION,
        resource_id=fiscal_document.id,
        action=models.EMISSION_JOB_ACTION_EMIT_FISCAL,
        provider=provider,
        idempotency_key=idempotency_key,
        payload_snapshot={"tipo_comprobante": tipo_comprobante},
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
    idempotency_key = f"void:fiscal:{comprobante.id}"
    existing = crud.get_emission_job_by_key(db, comprobante.tenant_id, idempotency_key)
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
            payload_snapshot={"motivo": motivo},
            provider="smartpse",
        )
        return existing, False

    job = crud.create_emission_job(
        db,
        tenant_id=comprobante.tenant_id,
        created_by_user_id=user.id,
        resource_type=models.EMISSION_JOB_RESOURCE_COTIZACION,
        resource_id=comprobante.id,
        action=models.EMISSION_JOB_ACTION_VOID_FISCAL,
        provider="smartpse",
        idempotency_key=idempotency_key,
        payload_snapshot={"motivo": motivo},
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


def _process_emit_fiscal_job(
    db: Session,
    job: models.DocumentEmissionJob,
    user: models.User,
) -> dict:
    fiscal_document = _get_tenant_cotizacion(db, job.tenant_id, job.resource_id)
    if not fiscal_document:
        raise RuntimeError("No se encontró el documento fiscal a emitir.")

    payload_snapshot = job.payload_snapshot or {}
    emission_leases.before_provider(db)
    result = facturacion_service.emitir_factura(
        fiscal_document,
        db,
        user,
        tipo_doc_override=payload_snapshot.get("tipo_comprobante"),
    )
    emission_leases.check(db, result)
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


def _process_consult_fiscal_job(
    db: Session,
    job: models.DocumentEmissionJob,
    user: models.User,
) -> dict:
    """Reconcile an already submitted sale document without sending it again."""
    fiscal_document = _get_tenant_cotizacion(db, job.tenant_id, job.resource_id)
    if not fiscal_document:
        raise RuntimeError("No se encontró el documento fiscal a conciliar.")

    payload_snapshot = job.payload_snapshot or {}
    db.commit()  # never hold an SQL transaction during provider consultation
    emission_leases.before_provider(db)
    result = facturacion_service.consultar_documento_fiscal(
        fiscal_document,
        user,
        tipo_doc_override=payload_snapshot.get("tipo_comprobante"),
    )
    emission_leases.check(db, result)
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

    payload_snapshot = job.payload_snapshot or {}
    try:
        inventory_service.ensure_document_void_inventory_safe(db, comprobante)
        if sale_dispatch_service.active_dispatch_allocation_exists(db, comprobante.tenant_id, comprobante.id):
            raise ValueError("La baja requiere resolver antes las reservas o cobertura GRE.")
    except ValueError as exc:
        _raise_non_retryable_validation(str(exc))
    emission_leases.before_provider(db)
    result = facturacion_service.anular_comprobante(
        comprobante,
        payload_snapshot.get("motivo") or "ANULACION EN COLA",
        user,
    )
    emission_leases.check(db, result)
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
        tenant_token = _apply_optional_tenant_context(db, job.tenant_id)
        user = _load_job_user(db, job)
        if not user:
            raise RuntimeError("No se encontró un usuario del tenant para ejecutar la emisión.")
        crud.mark_emission_job_attempt_started(db, job.id)
        db.expire(job)
        job = crud.get_emission_job(db, job.id)
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
        if result.get("pending"):
            crud.mark_emission_job_pending_confirmation(
                db, job.id,
                error_message="Smart PSE/SUNAT mantiene la guía pendiente de resultado definitivo.",
                error_classification=EMISSION_ERROR_AMBIGUOUS,
                result_snapshot=_build_job_result_snapshot(result),
                provider_ticket=provider_ticket,
            )
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
    except Exception as exc:
        emission_leases.check(db)
        message = str(exc)
        job = crud.get_emission_job(db, job_id)
        if job:
            error_classification = _classify_emission_error(message)
            should_reconcile_fiscal = (
                job.action == models.EMISSION_JOB_ACTION_EMIT_FISCAL
                and error_classification == EMISSION_ERROR_AMBIGUOUS
                and "smart pse remote verification missing" in message.lower()
            )
            if should_reconcile_fiscal:
                retry_in = _retry_delay_seconds(job.attempts or 1)
                crud.mark_emission_job_retry(
                    db,
                    job.id,
                    error_message=message,
                    retry_in_seconds=retry_in,
                    error_classification=error_classification,
                    action=models.EMISSION_JOB_ACTION_CONSULT_FISCAL,
                )
                logger.warning(
                    "emission_job_reconciliation_scheduled",
                    extra={
                        "event": "emission_job_reconciliation_scheduled",
                        "context": f"job_id={job.id} retry_in={retry_in}s",
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
