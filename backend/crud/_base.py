"""
crud/_base.py — Helpers compartidos entre dominios CRUD.

Contiene: utilidades de acceso a recursos por tenant, clonado de items,
resolución de documentos fuente, y contexto de hash de passwords.
Estos helpers son importados por los demás módulos del paquete crud/.
"""
from passlib.context import CryptContext
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
import time

import models
from config import settings
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

# ── Concurrencia: retry de correlativo (Fase A) ──────────────────────────
# Bajo carga concurrente, dos transacciones pueden competir por el mismo
# correlativo. El UNIQUE CONSTRAINT previene duplicados, pero el segundo
# usuario recibe un IntegrityError. Este wrapper reintenta transparentemente
# con backoff exponencial corto (50ms, 100ms, 150ms).
MAX_CORRELATIVO_RETRIES = 3
_CORRELATIVO_CONSTRAINT = "uq_cotizaciones_tenant_serie_correlativo"
_SMARTPSE_KNOWN_SERIES_FLOORS = {
    # Empresa demo creada directamente en Smart PSE antes de sincronizar Inkora.
    # Evita reutilizar folios remotos mientras no exista consulta remota de correlativos.
    "20606751509": {
        "F001": 11,
        "B001": 5,
    },
}


def _retry_on_correlativo_conflict(func, *args, **kwargs):
    """Ejecuta *func* reintentando ante IntegrityError de correlativo.

    La función debe aceptar un argumento ``db`` (Session) como primer
    parámetro posicional o keyword. En cada reintento se hace rollback
    para liberar el lock antes de volver a intentar.
    """
    for attempt in range(MAX_CORRELATIVO_RETRIES):
        try:
            return func(*args, **kwargs)
        except IntegrityError as exc:
            db = kwargs.get("db") or (args[0] if args else None)
            if db is not None:
                db.rollback()
            if _CORRELATIVO_CONSTRAINT not in str(exc.orig):
                raise
            if attempt == MAX_CORRELATIVO_RETRIES - 1:
                raise ValueError(
                    "No se pudo asignar un numero correlativo. "
                    "Intente nuevamente."
                ) from exc
            time.sleep(0.05 * (attempt + 1))  # 50ms, 100ms, 150ms


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
                codigo_producto=item.codigo_producto,
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


def _digits_only(value: str | None) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _parse_smartpse_series_floors(raw: str | None) -> dict[str, dict[str, int]]:
    floors: dict[str, dict[str, int]] = {}
    for tenant_chunk in str(raw or "").split(";"):
        tenant_chunk = tenant_chunk.strip()
        if not tenant_chunk or ":" not in tenant_chunk:
            continue
        ruc_raw, series_raw = tenant_chunk.split(":", 1)
        ruc = _digits_only(ruc_raw)
        if not ruc:
            continue
        series_floors: dict[str, int] = {}
        for pair in series_raw.split(","):
            pair = pair.strip()
            if not pair or "=" not in pair:
                continue
            serie_raw, floor_raw = pair.split("=", 1)
            serie = serie_raw.strip().upper()
            try:
                floor = int(str(floor_raw).strip())
            except ValueError:
                continue
            if serie and floor > 0:
                series_floors[serie] = floor
        if series_floors:
            floors[ruc] = series_floors
    return floors


def _smartpse_series_floor_for_tenant(db: Session, tenant_id: int, serie: str) -> int:
    normalized_serie = str(serie or "").strip().upper()
    if not normalized_serie:
        return 0

    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not tenant:
        return 0

    has_smartpse_cpe = bool(
        getattr(tenant, "smartpse_company_id", None)
        or getattr(tenant, "smartpse_usuario_secundaria", None)
        or getattr(tenant, "smartpse_token_acceso", None)
    )
    if not has_smartpse_cpe:
        return 0

    ruc = _digits_only(getattr(tenant, "business_ruc", None))
    if not ruc:
        return 0

    configured = _parse_smartpse_series_floors(settings.SMARTPSE_SERIES_FLOORS)
    configured_floor = configured.get(ruc, {}).get(normalized_serie, 0)
    known_floor = _SMARTPSE_KNOWN_SERIES_FLOORS.get(ruc, {}).get(normalized_serie, 0)
    return max(configured_floor, known_floor)


def _next_correlativo_for_series(db: Session, tenant_id: int, serie: str) -> int:
    last_doc = db.query(models.Cotizacion).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.serie == serie,
    ).order_by(models.Cotizacion.correlativo.desc()).with_for_update().first()
    ultimo_correlativo = last_doc.correlativo if last_doc else 0
    smartpse_floor = _smartpse_series_floor_for_tenant(db, tenant_id, serie)
    return max(ultimo_correlativo or 0, smartpse_floor) + 1


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
