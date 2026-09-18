from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text

from config import settings
from database import SessionLocal, USES_PGBOUNCER
from services import storage_service


router = APIRouter(tags=["ops"])


def _require_ops_token(x_internal_token: str | None = Header(default=None)) -> None:
    expected = settings.INTERNAL_PROVISIONING_TOKEN.strip()
    if not expected:
        raise HTTPException(503, "Readiness interno no configurado.")
    if x_internal_token != expected:
        raise HTTPException(403, "Token interno invalido.")


@router.get("/ops/readiness")
def readiness(_: None = Depends(_require_ops_token)):
    checks: dict[str, dict] = {}

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        checks["database"] = {
            "ok": True,
            "uses_transaction_pooler": USES_PGBOUNCER,
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
        }
    except Exception as exc:
        checks["database"] = {"ok": False, "error": type(exc).__name__}

    try:
        storage = storage_service.check_storage_ready()
        checks["storage"] = {
            "ok": bool(storage["configured"]),
            "bucket": storage["bucket"],
            "uses_server_key": storage.get("uses_server_key", False),
        }
    except Exception as exc:
        checks["storage"] = {"ok": False, "error": type(exc).__name__}

    checks["runtime"] = {
        "ok": True,
        "environment": settings.ENVIRONMENT,
        "fiscal_env": settings.FISCAL_ENV,
        "emission_worker_concurrency": settings.EMISSION_WORKER_CONCURRENCY,
    }

    ok = all(component.get("ok") for component in checks.values())
    return {"ok": ok, "checks": checks}
