from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import crud
import models
import schemas
from api_dependencies import (
    get_current_user,
    get_db_tenant,
    require_payment_manager,
)
from api_utils import raise_internal_server_error

router = APIRouter(tags=["pagos"])


# ==========================================
# PAGOS / ADELANTOS (dominio: cliente → tenant)
# ==========================================

@router.post("/cotizaciones/{cotizacion_id}/pagos", response_model=schemas.PagoResponse)
def registrar_adelanto_pago(
    cotizacion_id: int,
    pago_data: schemas.PagoCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_payment_manager),
):
    cotizacion = crud.get_cotizacion(db, cotizacion_id, current_user)
    if not cotizacion:
        raise HTTPException(404, "Documento no encontrado o sin acceso")
    try:
        return crud.registrar_pago(
            db=db,
            cotizacion_id=cotizacion_id,
            pago_data=pago_data,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise_internal_server_error(
            "registrar_adelanto_pago",
            "No se pudo registrar el pago.",
            exc,
        )


@router.get("/cotizaciones/{cotizacion_id}/pagos", response_model=List[schemas.PagoResponse])
def listar_pagos(
    cotizacion_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    cotizacion = crud.get_cotizacion(db, cotizacion_id, current_user)
    if not cotizacion:
        raise HTTPException(404, "Documento no encontrado o sin acceso")
    return crud.get_pagos_cotizacion(db, cotizacion_id, current_user.tenant_id)

