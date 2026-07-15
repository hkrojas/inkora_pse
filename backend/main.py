import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

import models
from config import settings
from database import SessionLocal, engine
from logging_utils import configure_logging, get_logger
from routers import (
    auth,
    clientes,
    cotizaciones,
    dashboard,
    facturacion,
    guias,
    inventory,
    legacy_frozen,
    notas,
    ops,
    pagos,
    productos,
    reportes,
    superadmin,
    sunat,
    tenants,
)

from rate_limit import limiter

configure_logging(level=settings.LOG_LEVEL, environment=settings.ENVIRONMENT)
logger = get_logger(__name__)


def create_app() -> FastAPI:
    if settings.INIT_DB_ON_STARTUP:
        logger.warning(
            "init_db_on_startup_enabled",
            extra={"event": "init_db_on_startup_enabled"},
        )
        models.Base.metadata.create_all(bind=engine)

    app = FastAPI(title="Sistema Cotizaciones SUNAT")
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.exception(
                "request_failed",
                extra={
                    "event": "request_failed",
                    "path": request.url.path,
                    "method": request.method,
                    "request_id": request_id,
                    "duration_ms": duration_ms,
                },
            )
            raise

        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            "request_completed",
            extra={
                "event": "request_completed",
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "request_id": request_id,
                "duration_ms": duration_ms,
            },
        )
        response.headers.setdefault("X-Request-Id", request_id)
        return response

    app.include_router(auth.router)
    app.include_router(tenants.router)
    app.include_router(clientes.router)
    app.include_router(productos.router)
    app.include_router(cotizaciones.router)
    app.include_router(pagos.router)
    app.include_router(reportes.router)
    app.include_router(facturacion.router)
    app.include_router(notas.router)
    app.include_router(guias.router)
    app.include_router(inventory.router)
    app.include_router(superadmin.router)
    app.include_router(dashboard.router)
    app.include_router(sunat.router)
    app.include_router(ops.router)

    # Compatibilidad temporal local: endpoints congelados fuera del launch scope.
    if settings.is_local:
        app.include_router(legacy_frozen.router)

    @app.get("/health", tags=["ops"])
    def health_check():
        return {"status": "ok", "environment": settings.ENVIRONMENT}

    @app.on_event("startup")
    def _startup_db_ping() -> None:
        """Falla rápido si la base de datos no es alcanzable al arrancar."""
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
            logger.info("db_ping_ok", extra={"event": "db_ping_ok"})
        except Exception as exc:
            logger.error(
                "db_ping_failed",
                extra={"event": "db_ping_failed", "error": str(exc)},
            )
            raise RuntimeError(f"No se pudo conectar a la base de datos: {exc}") from exc

    return app


app = create_app()
