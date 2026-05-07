"""Alembic environment for Inkora.

This Alembic tree starts after the manual pre-beta bootstrap:

    python backend/run_launch_migrations.py --strict
    python backend/migrate_beta_integrity.py --apply
    alembic -c backend/alembic.ini stamp 0001_prebeta_baseline

The first revision is a no-op baseline marker. It must not be used to create a
new database from scratch. New schema changes after the baseline should be
implemented as Alembic revisions and reviewed before applying.
"""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from alembic import context
from sqlalchemy import engine_from_config, pool


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Frozen tables exist in the legacy codebase but are outside current launch
# scope. Keep this list explicit so future autogenerate reviews can decide when
# to include one intentionally.
FROZEN_TABLES = {
    "insumos",
    "recetas_bom",
    "proveedores",
    "ordenes_produccion",
    "ordenes_produccion_detalle",
    "alertas_inventario",
}


def get_database_url() -> str:
    """Return DATABASE_URL without hardcoding secrets."""
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url:
        return strip_internal_database_url_flags(database_url)

    try:
        from config import settings
    except Exception as exc:  # pragma: no cover - exercised by Alembic CLI.
        raise RuntimeError(
            "DATABASE_URL no esta configurada. Define DATABASE_URL en el entorno "
            "antes de ejecutar Alembic."
        ) from exc

    return strip_internal_database_url_flags(settings.DATABASE_URL)


def strip_internal_database_url_flags(database_url: str) -> str:
    """Remove app-only URL flags before handing the DSN to SQLAlchemy."""
    if "?" not in database_url:
        return database_url

    parsed = urlsplit(database_url)
    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() != "pgbouncer"
    ]
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(query_items, doseq=True),
            parsed.fragment,
        )
    )


def get_target_metadata():
    """Load SQLAlchemy metadata after sys.path and environment are ready."""
    import models

    return models.Base.metadata


def include_object(object_, name, type_, reflected, compare_to):
    """Exclude frozen tables from future autogenerate unless explicitly enabled."""
    if type_ == "table" and name in FROZEN_TABLES:
        return False

    table = getattr(object_, "table", None)
    if table is not None and table.name in FROZEN_TABLES:
        return False

    return True


def run_migrations_offline() -> None:
    """Run migrations in offline mode without creating an Engine."""
    context.configure(
        url=get_database_url(),
        target_metadata=get_target_metadata(),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode using DATABASE_URL/config settings."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_target_metadata(),
            include_object=include_object,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
