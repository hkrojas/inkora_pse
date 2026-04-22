"""
conftest.py — Inkora Phase 7 Test Infrastructure
====================================================
Fixtures compartidos por todos los archivos de test de Fase 7.

Usa SQLite en memoria para aislamiento total sin necesidad de PostgreSQL.
No llama a `apply_tenant_context` (esa función es específica de Postgres).
"""
import sys
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ── path setup ──────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def _bootstrap_test_environment() -> None:
    """
    Defaults de entorno solo para pytest.

    Permite importar `config.py` sin depender del `.env` real y sin pisar
    variables ya definidas por el entorno del usuario o CI.
    """
    bootstrap_db_path = Path(__file__).with_name("pytest_bootstrap.db")
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{bootstrap_db_path.as_posix()}")
    os.environ.setdefault("SECRET_KEY", "pytest-secret-key")


_bootstrap_test_environment()

import models
from database import Base
import crud
import schemas
from access_control import ROLE_ADMIN, ROLE_OPERADOR, ROLE_VENDEDOR, ROLE_SUPERADMIN


# ============================================================================
# DB FIXTURE — SQLite en memoria, aislado por test
# ============================================================================

@pytest.fixture
def db_session():
    """Sesión SQLite in-memory limpia para cada test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


# ============================================================================
# FACTORY HELPERS — crean objetos de dominio en la BD de test
# ============================================================================

def make_tenant(db, suffix: str, *, is_active: bool = True) -> models.Tenant:
    tenant = models.Tenant(
        business_name=f"Imprenta {suffix}",
        business_ruc=f"201234{suffix.zfill(5)}",
        is_active=is_active,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def make_user(
    db,
    tenant: models.Tenant,
    *,
    email: str,
    rol: str = ROLE_ADMIN,
    is_superadmin: bool = False,
    password: str = "testpass",
) -> models.User:
    from security import get_password_hash

    user = models.User(
        email=email,
        hashed_password=get_password_hash(password),
        nombre_completo=email,
        rol=rol,
        is_superadmin=is_superadmin,
        tenant_id=tenant.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    # Reload with tenant relationship populated
    return crud.get_user_by_id(db, user.id)


def make_cliente(
    db,
    tenant: models.Tenant,
    suffix: str,
    *,
    tipo_documento: str = "6",
    numero_documento: str | None = None,
) -> models.Cliente:
    numero = numero_documento or f"204{suffix.zfill(8)}"
    cliente = models.Cliente(
        tenant_id=tenant.id,
        tipo_documento=tipo_documento,
        numero_documento=numero,
        razon_social=f"Cliente {suffix}",
        direccion="Av. Lima 100",
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


def make_producto(db, tenant: models.Tenant, suffix: str) -> models.Producto:
    producto = models.Producto(
        tenant_id=tenant.id,
        nombre=f"Impresión {suffix}",
        precio_unitario=Decimal("118.00"),
        valor_unitario=Decimal("100.00"),
        unidad_medida="NIU",
        tipo_afectacion_igv="10",
    )
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


def make_cotizacion(
    db,
    tenant: models.Tenant,
    user: models.User,
    cliente: models.Cliente,
    *,
    total: str = "118.00",
    monto_pagado: str = "0.00",
    document_kind: str = "quotation",
    estado: str = "pendiente",
    fecha_vencimiento=None,
    tipo_comprobante: str = "00",
) -> models.Cotizacion:
    """Inserta directamente una Cotizacion en BD (sin pasar por crud.create_cotizacion)."""
    cot = models.Cotizacion(
        tenant_id=tenant.id,
        cliente_id=cliente.id,
        usuario_id=user.id,
        fecha_emision=datetime.now(timezone.utc),
        fecha_vencimiento=fecha_vencimiento,
        serie="COT",
        correlativo=1,
        document_kind=document_kind,
        tipo_comprobante=tipo_comprobante,
        estado=estado,
        total_gravada=Decimal("100.00"),
        total_igv=Decimal("18.00"),
        total_venta=Decimal(total),
        monto_pagado=Decimal(monto_pagado),
        saldo_pendiente=Decimal(total) - Decimal(monto_pagado),
    )
    db.add(cot)
    db.commit()
    db.refresh(cot)
    return cot


def make_quote_via_crud(
    db,
    tenant: models.Tenant,
    user: models.User,
    cliente: models.Cliente,
    *,
    precio: str = "118.00",
) -> models.Cotizacion:
    """Usa crud.create_cotizacion para crear una cotizacion con internal_order_number."""
    payload = schemas.CotizacionCreate(
        cliente_id=cliente.id,
        fecha_vencimiento=None,
        moneda="PEN",
        tipo_comprobante="00",
        items=[
            schemas.CotizacionItemCreate(
                descripcion="Impresión de prueba",
                cantidad=Decimal("1"),
                precio_unitario=Decimal(precio),
            )
        ],
    )
    return crud.create_cotizacion(db, payload, user.id, tenant.id)
