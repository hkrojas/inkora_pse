from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
MIGRATION_PATH = BACKEND_DIR / "migrations" / "001_scalability_indexes.sql"


def test_scalability_indexes_migration_is_idempotent_and_complete():
    assert MIGRATION_PATH.exists()
    sql = MIGRATION_PATH.read_text(encoding="utf-8").lower()

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
        assert f"create index if not exists {index_name}" in sql

    assert "create extension if not exists pg_trgm" in sql
    assert "using gin (razon_social gin_trgm_ops)" in sql
    assert "using gin (nombre gin_trgm_ops)" in sql
