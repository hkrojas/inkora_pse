from fastapi import APIRouter, Depends, HTTPException

import models
from api_dependencies import get_current_user
from services.sunat_exchange_rate_service import (
    SunatExchangeRateError,
    get_exchange_rate,
)

router = APIRouter(tags=["sunat"])


@router.get(
    "/sunat/exchange-rate",
    summary="Tipo de cambio SUNAT",
)
def read_sunat_exchange_rate(
    current_user: models.User = Depends(get_current_user),
):
    try:
        return get_exchange_rate()
    except SunatExchangeRateError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
