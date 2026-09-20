"""Tenant-scoped national transfers between establishments."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import models
import schemas
from access_control import ELEVATED_TENANT_ROLES, assert_user_has_roles
from api_dependencies import get_current_user, get_db_tenant, require_admin, require_emission_allowed
from services import beta_feature_flags, internal_transfer_service


router = APIRouter(tags=["internal-transfers"])


def _operator(user: models.User = Depends(get_current_user)):
    return assert_user_has_roles(
        user,
        ELEVATED_TENANT_ROLES,
        detail="Solo administradores y operadores pueden gestionar traslados internos.",
    )


def _require_feature(db: Session, user: models.User):
    beta_feature_flags.require_fiscal_feature_enabled(
        db,
        user.tenant_id,
        beta_feature_flags.FISCAL_FEATURE_INTERNAL_TRANSFERS,
        current_user=user,
    )


def _raise_error(exc: internal_transfer_service.InternalTransferError):
    detail = {"code": exc.code, "message": str(exc)}
    if exc.context is not None:
        detail["context"] = exc.context
    raise HTTPException(status_code=exc.status_code, detail=detail)


@router.get("/establecimientos", response_model=list[schemas.EstablishmentResponse])
def establishments(
    include_inactive: bool = False,
    db: Session = Depends(get_db_tenant),
    user: models.User = Depends(get_current_user),
):
    _require_feature(db, user)
    return internal_transfer_service.list_establishments(db, user.tenant_id, include_inactive=include_inactive)


@router.post("/establecimientos", response_model=schemas.EstablishmentResponse, status_code=201)
def add_establishment(
    data: schemas.EstablishmentCreate,
    db: Session = Depends(get_db_tenant),
    user: models.User = Depends(require_admin),
    _active: models.User = Depends(require_emission_allowed),
):
    _require_feature(db, user)
    try:
        return internal_transfer_service.create_establishment(db, user.tenant_id, user.id, data)
    except internal_transfer_service.InternalTransferError as exc:
        _raise_error(exc)


@router.put("/establecimientos/{establishment_id}", response_model=schemas.EstablishmentResponse)
def edit_establishment(
    establishment_id: int,
    data: schemas.EstablishmentUpdate,
    db: Session = Depends(get_db_tenant),
    user: models.User = Depends(require_admin),
    _active: models.User = Depends(require_emission_allowed),
):
    _require_feature(db, user)
    try:
        return internal_transfer_service.update_establishment(db, user.tenant_id, establishment_id, data)
    except internal_transfer_service.InternalTransferError as exc:
        _raise_error(exc)


@router.post("/establecimientos/{establishment_id}/verificar", response_model=schemas.EstablishmentResponse)
def verify_establishment(
    establishment_id: int,
    data: schemas.EstablishmentVerify,
    db: Session = Depends(get_db_tenant),
    user: models.User = Depends(require_admin),
    _active: models.User = Depends(require_emission_allowed),
):
    _require_feature(db, user)
    try:
        return internal_transfer_service.verify_establishment(db, user.tenant_id, establishment_id, user.id, data)
    except internal_transfer_service.InternalTransferError as exc:
        _raise_error(exc)


@router.get("/traslados-internos")
def list_internal_transfers(
    skip: int = Query(0, ge=0),
    limit: int = Query(15, ge=1, le=100),
    db: Session = Depends(get_db_tenant),
    user: models.User = Depends(get_current_user),
):
    _require_feature(db, user)
    return internal_transfer_service.list_transfers(db, user.tenant_id, skip=skip, limit=limit)


@router.post("/traslados-internos", status_code=201)
def create_internal_transfer(
    data: schemas.InternalTransferCreate,
    db: Session = Depends(get_db_tenant),
    user: models.User = Depends(_operator),
    _active: models.User = Depends(require_emission_allowed),
):
    _require_feature(db, user)
    try:
        transfer, _ = internal_transfer_service.create_transfer(db, user.tenant_id, user.id, data)
        return internal_transfer_service.transfer_context(db, user.tenant_id, transfer.id)
    except internal_transfer_service.InternalTransferError as exc:
        db.rollback()
        _raise_error(exc)


@router.get("/traslados-internos/{transfer_id}")
@router.get("/traslados-internos/{transfer_id}/contexto")
def internal_transfer_context(
    transfer_id: int,
    db: Session = Depends(get_db_tenant),
    user: models.User = Depends(get_current_user),
):
    _require_feature(db, user)
    try:
        return internal_transfer_service.transfer_context(db, user.tenant_id, transfer_id)
    except internal_transfer_service.InternalTransferError as exc:
        _raise_error(exc)


@router.put("/traslados-internos/{transfer_id}")
def edit_internal_transfer(
    transfer_id: int,
    data: schemas.InternalTransferUpdate,
    db: Session = Depends(get_db_tenant),
    user: models.User = Depends(_operator),
    _active: models.User = Depends(require_emission_allowed),
):
    _require_feature(db, user)
    try:
        internal_transfer_service.update_transfer(db, user.tenant_id, transfer_id, data)
        return internal_transfer_service.transfer_context(db, user.tenant_id, transfer_id)
    except internal_transfer_service.InternalTransferError as exc:
        db.rollback()
        _raise_error(exc)


@router.post("/traslados-internos/{transfer_id}/despachos", status_code=201)
def create_internal_dispatch(
    transfer_id: int,
    data: schemas.InternalTransferDispatchCreate,
    db: Session = Depends(get_db_tenant),
    user: models.User = Depends(_operator),
    _active: models.User = Depends(require_emission_allowed),
):
    _require_feature(db, user)
    try:
        dispatch, _ = internal_transfer_service.create_dispatch(db, user.tenant_id, transfer_id, user.id, data)
        return {"dispatch_id": dispatch.id, "context": internal_transfer_service.transfer_context(db, user.tenant_id, transfer_id)}
    except internal_transfer_service.InternalTransferError as exc:
        db.rollback()
        _raise_error(exc)


@router.post("/traslados-internos/{transfer_id}/cancelar")
def cancel_internal_transfer(
    transfer_id: int,
    db: Session = Depends(get_db_tenant),
    user: models.User = Depends(_operator),
    _active: models.User = Depends(require_emission_allowed),
):
    _require_feature(db, user)
    try:
        internal_transfer_service.cancel_transfer(db, user.tenant_id, transfer_id)
        return internal_transfer_service.transfer_context(db, user.tenant_id, transfer_id)
    except internal_transfer_service.InternalTransferError as exc:
        db.rollback()
        _raise_error(exc)


@router.post("/traslados-internos/despachos/{dispatch_id}/confirmar-salida")
def confirm_internal_departure(
    dispatch_id: int,
    data: schemas.InternalTransferDepartureConfirm,
    db: Session = Depends(get_db_tenant),
    user: models.User = Depends(_operator),
    _active: models.User = Depends(require_emission_allowed),
):
    _require_feature(db, user)
    try:
        dispatch = internal_transfer_service.confirm_departure(
            db, user.tenant_id, dispatch_id, user.id, data.idempotency_key
        )
        return internal_transfer_service.transfer_context(db, user.tenant_id, dispatch.transfer_id)
    except internal_transfer_service.InternalTransferError as exc:
        db.rollback()
        _raise_error(exc)


@router.post("/traslados-internos/despachos/{dispatch_id}/recepciones", status_code=201)
def receive_internal_dispatch(
    dispatch_id: int,
    data: schemas.InternalTransferReceiptCreate,
    db: Session = Depends(get_db_tenant),
    user: models.User = Depends(_operator),
    _active: models.User = Depends(require_emission_allowed),
):
    _require_feature(db, user)
    try:
        receipt, _ = internal_transfer_service.receive_dispatch(
            db, user.tenant_id, dispatch_id, user.id, data
        )
        return {
            "receipt_id": receipt.id,
            "context": internal_transfer_service.transfer_context(db, user.tenant_id, receipt.dispatch.transfer_id),
        }
    except internal_transfer_service.InternalTransferError as exc:
        db.rollback()
        _raise_error(exc)
