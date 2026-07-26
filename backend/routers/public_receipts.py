from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from database import get_db
from rate_limit import limiter
from schemas.public_receipts import PublicReceiptLookup, PublicReceiptResponse
from crud.public_receipts import lookup_public_receipt


router = APIRouter(prefix="/public/comprobantes", tags=["public-receipts"])


@router.post(
    "/consulta",
    response_model=PublicReceiptResponse,
    summary="Consultar un comprobante emitido por Inkora",
)
@limiter.limit("10/minute")
def consult_public_receipt(
    request: Request,
    response: Response,
    lookup: PublicReceiptLookup,
    db: Session = Depends(get_db),
):
    result = lookup_public_receipt(db, lookup)
    response.headers["Cache-Control"] = "no-store"
    if not result:
        raise HTTPException(
            status_code=404,
            detail="No encontramos un comprobante que coincida con todos los datos.",
            headers={"Cache-Control": "no-store"},
        )
    return result
