from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parent
    / "alembic"
    / "versions"
    / "0006_production_security_and_performance.py"
)


def test_production_hardening_migration_revokes_public_supabase_roles():
    content = MIGRATION.read_text(encoding="utf-8")

    assert "FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated']" in content
    assert "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM %I" in content
    assert "REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM %I" in content
    assert "REVOKE EXECUTE ON FUNCTION public.rls_auto_enable()" in content


def test_production_hardening_migration_adds_worker_and_fk_indexes():
    content = MIGRATION.read_text(encoding="utf-8")

    expected_indexes = [
        "ix_document_emission_jobs_claim",
        "ix_clientes_tenant_id",
        "ix_productos_tenant_id",
        "ix_cotizacion_items_cotizacion_id",
        "ix_pagos_fiscal_document_id",
        "ix_guia_remision_items_guia_id",
    ]
    for index_name in expected_indexes:
        assert index_name in content


def test_production_hardening_migration_enables_pg_trgm_for_search():
    content = MIGRATION.read_text(encoding="utf-8")

    assert "CREATE EXTENSION IF NOT EXISTS pg_trgm" in content
    assert "gin_trgm_ops" in content
