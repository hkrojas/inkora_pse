from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
CORE_MIGRATION_PATH = BACKEND_DIR / "migrations" / "001_scalability_indexes.sql"
OPTIONAL_TRGM_MIGRATION_PATH = (
    BACKEND_DIR / "migrations" / "002_optional_pg_trgm_indexes.sql"
)


def test_static_scalability_indexes_migrations_are_split_and_idempotent():
    """Static validation only; Supabase must still run and verify the SQL."""
    assert CORE_MIGRATION_PATH.exists()
    assert OPTIONAL_TRGM_MIGRATION_PATH.exists()
    core_sql = CORE_MIGRATION_PATH.read_text(encoding="utf-8").lower()
    optional_sql = OPTIONAL_TRGM_MIGRATION_PATH.read_text(encoding="utf-8").lower()

    required_indexes = [
        "idx_clientes_tenant_numero_documento",
        "idx_clientes_tenant_razon_social",
        "idx_productos_tenant_codigo_interno",
        "idx_productos_tenant_nombre",
        "idx_cotizaciones_tenant_kind_estado_fecha",
        "idx_cotizaciones_tenant_source_kind_estado",
        "idx_cotizaciones_tenant_fecha_vencimiento",
        "idx_cotizaciones_tenant_cliente",
        "idx_cotizacion_items_cotizacion_id",
        "idx_cotizacion_items_producto_id",
        "idx_pagos_tenant_fecha_pago",
        "idx_pagos_tenant_fiscal_document",
        "idx_pagos_tenant_source_quote",
        "idx_emission_jobs_claim",
    ]

    for index_name in required_indexes:
        assert f"create index if not exists {index_name}" in core_sql

    assert "pg_trgm" not in core_sql
    assert "using gin" not in core_sql
    assert "create extension if not exists pg_trgm" in optional_sql
    assert "using gin (razon_social gin_trgm_ops)" in optional_sql
    assert "using gin (nombre gin_trgm_ops)" in optional_sql
