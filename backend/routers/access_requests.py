from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

import models
import schemas
from api_dependencies import get_db, get_superadmin
from rate_limit import limiter
from services import access_request_service


router = APIRouter(tags=["access-requests"])


@router.post(
    "/access-requests",
    response_model=schemas.AccessRequestCreated,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/hour")
def create_access_request(
    request: Request,
    data: schemas.AccessRequestCreate,
    db: Session = Depends(get_db),
):
    return access_request_service.create_access_request(
        db,
        data,
        ip_address=request.client.host if request.client else None,
    )


@router.post(
    "/access-requests/status",
    response_model=schemas.AccessRequestPublicStatus,
)
@limiter.limit("30/minute")
def access_request_status(
    request: Request,
    data: schemas.AccessRequestStatusLookup,
    db: Session = Depends(get_db),
):
    return access_request_service.get_public_status(db, data.request_token)


@router.get(
    "/superadmin/access-requests",
    response_model=schemas.AccessRequestPageResponse,
)
def list_access_requests(
    status_filter: str | None = Query(default="pending", alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    return access_request_service.list_access_requests(
        db,
        status=status_filter,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/superadmin/access-requests/{request_id}/approve",
    response_model=schemas.AccessRequestAdminResponse,
)
def approve_access_request(
    request_id: int,
    data: schemas.AccessRequestReview,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    return access_request_service.approve_access_request(db, request_id, admin, data)


@router.post(
    "/superadmin/access-requests/{request_id}/reject",
    response_model=schemas.AccessRequestAdminResponse,
)
def reject_access_request(
    request_id: int,
    data: schemas.AccessRequestReview,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_superadmin),
):
    return access_request_service.reject_access_request(db, request_id, admin, data)
