import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

import models
from config import settings
from database import engine
from logging_utils import configure_logging, get_logger
from routers import (
    auth,
    clientes,
    cotizaciones,
    dashboard,
    facturacion,
    guias,
    legacy_frozen,
    pagos,
    productos,
    superadmin,
    tenants,
)

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
    app.include_router(facturacion.router)
    app.include_router(guias.router)
    app.include_router(superadmin.router)
    app.include_router(dashboard.router)

    # Compatibilidad temporal: endpoints congelados aislados fuera del launch scope.
    app.include_router(legacy_frozen.router)

    return app


app = create_app()
