"""Harden public grants and add production lookup indexes."""
from __future__ import annotations

from alembic import op


revision = "0006_prod_security_perf"
down_revision = "0005_smartpse_scale_indexes"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute(
        """
        DO $$
        DECLARE role_name text;
        BEGIN
            FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated']
            LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
                    EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM %I', role_name);
                    EXECUTE format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM %I', role_name);
                    EXECUTE format('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM %I', role_name);
                    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM %I', role_name);
                    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM %I', role_name);
                    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM %I', role_name);
                END IF;
            END LOOP;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        DECLARE role_name text;
        BEGIN
            IF to_regprocedure('public.rls_auto_enable()') IS NOT NULL THEN
                REVOKE EXECUTE ON FUNCTION public.rls_auto_enable() FROM public;
                FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated']
                LOOP
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
                        EXECUTE format('REVOKE EXECUTE ON FUNCTION public.rls_auto_enable() FROM %I', role_name);
                    END IF;
                END LOOP;
            END IF;
        END
        $$;
        """
    )

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    index_sql = [
        "CREATE INDEX IF NOT EXISTS ix_clientes_tenant_id ON clientes (tenant_id)",
        "CREATE INDEX IF NOT EXISTS ix_clientes_tenant_razon_social ON clientes (tenant_id, razon_social)",
        "CREATE INDEX IF NOT EXISTS ix_clientes_tenant_numero_documento ON clientes (tenant_id, numero_documento)",
        "CREATE INDEX IF NOT EXISTS ix_clientes_razon_social_trgm ON clientes USING gin (razon_social gin_trgm_ops)",
        "CREATE INDEX IF NOT EXISTS ix_clientes_numero_documento_trgm ON clientes USING gin (numero_documento gin_trgm_ops)",
        "CREATE INDEX IF NOT EXISTS ix_productos_tenant_id ON productos (tenant_id)",
        "CREATE INDEX IF NOT EXISTS ix_productos_tenant_nombre ON productos (tenant_id, nombre)",
        "CREATE INDEX IF NOT EXISTS ix_productos_tenant_codigo ON productos (tenant_id, codigo_interno)",
        "CREATE INDEX IF NOT EXISTS ix_productos_nombre_trgm ON productos USING gin (nombre gin_trgm_ops)",
        "CREATE INDEX IF NOT EXISTS ix_productos_codigo_trgm ON productos USING gin (codigo_interno gin_trgm_ops)",
        "CREATE INDEX IF NOT EXISTS ix_cotizacion_items_cotizacion_id ON cotizacion_items (cotizacion_id)",
        "CREATE INDEX IF NOT EXISTS ix_cotizacion_items_producto_id ON cotizacion_items (producto_id)",
        "CREATE INDEX IF NOT EXISTS ix_cotizaciones_cliente_id ON cotizaciones (cliente_id)",
        "CREATE INDEX IF NOT EXISTS ix_cotizaciones_usuario_id ON cotizaciones (usuario_id)",
        "CREATE INDEX IF NOT EXISTS ix_cotizaciones_tenant_estado_fecha ON cotizaciones (tenant_id, estado, fecha_emision)",
        "CREATE INDEX IF NOT EXISTS ix_pagos_tenant_id ON pagos (tenant_id)",
        "CREATE INDEX IF NOT EXISTS ix_pagos_cotizacion_id ON pagos (cotizacion_id)",
        "CREATE INDEX IF NOT EXISTS ix_pagos_fiscal_document_id ON pagos (fiscal_document_id)",
        "CREATE INDEX IF NOT EXISTS ix_pagos_source_quote_id ON pagos (source_quote_id)",
        "CREATE INDEX IF NOT EXISTS ix_guias_remision_cliente_id ON guias_remision (cliente_id)",
        "CREATE INDEX IF NOT EXISTS ix_guias_remision_cotizacion_id ON guias_remision (cotizacion_id)",
        "CREATE INDEX IF NOT EXISTS ix_guias_remision_fiscal_document_id ON guias_remision (fiscal_document_id)",
        "CREATE INDEX IF NOT EXISTS ix_guias_remision_source_quote_id ON guias_remision (source_quote_id)",
        "CREATE INDEX IF NOT EXISTS ix_guias_remision_usuario_id ON guias_remision (usuario_id)",
        "CREATE INDEX IF NOT EXISTS ix_guia_remision_items_guia_id ON guia_remision_items (guia_id)",
        "CREATE INDEX IF NOT EXISTS ix_document_emission_jobs_claim ON document_emission_jobs (status, available_at, priority, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_users_tenant_id ON users (tenant_id)",
    ]
    for statement in index_sql:
        op.execute(statement)


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        return

    for index_name in [
        "ix_users_tenant_id",
        "ix_document_emission_jobs_claim",
        "ix_guia_remision_items_guia_id",
        "ix_guias_remision_usuario_id",
        "ix_guias_remision_source_quote_id",
        "ix_guias_remision_fiscal_document_id",
        "ix_guias_remision_cotizacion_id",
        "ix_guias_remision_cliente_id",
        "ix_pagos_source_quote_id",
        "ix_pagos_fiscal_document_id",
        "ix_pagos_cotizacion_id",
        "ix_pagos_tenant_id",
        "ix_cotizaciones_tenant_estado_fecha",
        "ix_cotizaciones_usuario_id",
        "ix_cotizaciones_cliente_id",
        "ix_cotizacion_items_producto_id",
        "ix_cotizacion_items_cotizacion_id",
        "ix_productos_codigo_trgm",
        "ix_productos_nombre_trgm",
        "ix_productos_tenant_codigo",
        "ix_productos_tenant_nombre",
        "ix_productos_tenant_id",
        "ix_clientes_numero_documento_trgm",
        "ix_clientes_razon_social_trgm",
        "ix_clientes_tenant_numero_documento",
        "ix_clientes_tenant_razon_social",
        "ix_clientes_tenant_id",
    ]:
        op.execute(f"DROP INDEX IF EXISTS {index_name}")
