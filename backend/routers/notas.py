from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy.orm import Session

import crud
import models
import schemas
from api_dependencies import get_current_user, get_db_tenant, require_document_emitter, require_emission_allowed
from models.tenants import USAGE_LIMIT_KIND_NOTA_CREDITO, USAGE_LIMIT_KIND_NOTA_DEBITO
from services import beta_feature_flags, emission_queue_service, note_adjustment_service

router = APIRouter(prefix="/notas", tags=["notas-v2"])


def _http_error(exc: ValueError):
    detail = str(exc)
    status = 404 if "no encontr" in detail.lower() else 422
    raise HTTPException(status_code=status, detail=detail) from exc


def _note_or_404(db: Session, tenant_id: int, note_id: int):
    note = db.query(models.Cotizacion).filter(
        models.Cotizacion.id == note_id,
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.tipo_comprobante.in_(("07", "08")),
    ).first()
    if not note:
        raise HTTPException(404, "Nota no encontrada para la empresa.")
    return note


def _require_note_feature(db, user, tipo_nota):
    beta_feature_flags.require_fiscal_feature_enabled(
        db,
        user.tenant_id,
        beta_feature_flags.feature_for_note_type(tipo_nota),
        current_user=user,
    )


@router.get("/contexto/{document_id}")
def note_context(
    document_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    try:
        return note_adjustment_service.get_note_context(db, current_user.tenant_id, document_id)
    except ValueError as exc:
        _http_error(exc)


@router.post("/", status_code=201)
def create_note_draft(
    payload: schemas.FiscalNoteDraftCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    _require_note_feature(db, current_user, payload.tipo_nota)
    try:
        note, created = note_adjustment_service.create_draft(
            db, current_user.tenant_id, current_user.id, payload, idempotency_key,
        )
        result = note_adjustment_service.serialize_note(db, note)
        result["created"] = created
        result["message"] = "Borrador guardado"
        return result
    except ValueError as exc:
        _http_error(exc)


@router.patch("/{note_id}")
def update_note_draft(
    note_id: int,
    payload: schemas.FiscalNoteDraftUpdate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
):
    _require_note_feature(db, current_user, payload.tipo_nota)
    try:
        note = note_adjustment_service.update_draft(
            db, current_user.tenant_id, current_user.id, note_id, payload,
        )
        return note_adjustment_service.serialize_note(db, note)
    except ValueError as exc:
        _http_error(exc)


@router.delete("/{note_id}", status_code=204)
def delete_note_draft(
    note_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
):
    try:
        note_adjustment_service.delete_draft(db, current_user.tenant_id, note_id)
        return Response(status_code=204)
    except ValueError as exc:
        _http_error(exc)


@router.get("/{note_id}")
def get_note(
    note_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    return note_adjustment_service.serialize_note(
        db, _note_or_404(db, current_user.tenant_id, note_id),
    )


@router.post("/{note_id}/emitir")
def emit_note(
    note_id: int,
    mode: str = Query(default="async", pattern="^async$"),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
    _emission_check: models.User = Depends(require_emission_allowed),
):
    note = _note_or_404(db, current_user.tenant_id, note_id)
    tipo_nota = "credito" if note.tipo_comprobante == "07" else "debito"
    _require_note_feature(db, current_user, tipo_nota)
    if not current_user.is_superadmin:
        quota_kind = USAGE_LIMIT_KIND_NOTA_CREDITO if tipo_nota == "credito" else USAGE_LIMIT_KIND_NOTA_DEBITO
        try:
            crud.check_emission_quota(db, current_user.tenant_id, current_user.id, quota_kind)
        except crud.QuotaExceededError as exc:
            raise HTTPException(402, "Se alcanzo la cuota de notas fiscales.") from exc
    try:
        note, numbered = note_adjustment_service.assign_number_for_emission(
            db, current_user.tenant_id, note_id,
        )
        if note.estado == "facturada":
            raise HTTPException(409, "La nota ya fue aceptada por SUNAT y es inmutable.")
        if note.estado != "pendiente":
            raise HTTPException(409, "La nota no se puede reenviar desde su estado actual.")
        job, created = emission_queue_service.enqueue_note_job(
            db,
            note,
            current_user,
            tipo_nota=tipo_nota,
            cod_motivo=note.nota_motivo_codigo,
            descripcion_motivo=note.nota_motivo_descripcion,
        )
        return {
            "job_id": job.id,
            "resource_id": note.id,
            "status": job.status,
            "created": created,
            "number_assigned": numbered,
            "message": "Nota en cola para emision fiscal.",
        }
    except ValueError as exc:
        _http_error(exc)


@router.post("/{note_id}/crear-reemplazo", status_code=201)
def create_replacement(
    note_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
):
    note = _note_or_404(db, current_user.tenant_id, note_id)
    if note.nota_motivo_codigo not in {"02", "03"} or note.estado != "facturada":
        raise HTTPException(409, "El reemplazo solo aplica a notas 02/03 aceptadas.")
    if note.nota_reemplazo_id:
        return {"replacement_id": note.nota_reemplazo_id, "created": False}
    source = note.nota_referencia
    if not source:
        raise HTTPException(409, "La nota no conserva su comprobante de origen.")
    payload = schemas.CotizacionCreate(
        cliente_id=source.cliente_id,
        fecha_vencimiento=source.fecha_vencimiento,
        moneda=source.moneda,
        tipo_comprobante=source.tipo_comprobante,
        observaciones=source.observaciones,
        condicion_pago=source.condicion_pago,
        warehouse_id=source.warehouse_id,
        cuotas_pago=source.cuotas_pago or [],
        items=[
            schemas.CotizacionItemCreate(
                producto_id=item.producto_id,
                codigo_producto=item.codigo_producto,
                descripcion=item.descripcion,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                unidad_medida=item.unidad_medida,
                tipo_afectacion_igv=item.tipo_afectacion_igv,
            )
            for item in source.items or []
        ],
    )
    replacement = crud.create_cotizacion(
        db, payload, current_user.id, current_user.tenant_id,
    )
    note.nota_reemplazo_id = replacement.id
    db.commit()
    return {
        "replacement_id": replacement.id,
        "created": True,
        "message": "Comprobante reemplazante creado como borrador para revision.",
    }
