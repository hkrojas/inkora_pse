from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool


def make_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def setup_schema(engine):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE tenants (
                    id INTEGER PRIMARY KEY,
                    is_active BOOLEAN DEFAULT 1
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE subscriptions (
                    id INTEGER PRIMARY KEY,
                    tenant_id INTEGER NOT NULL,
                    status VARCHAR NOT NULL,
                    plan_code VARCHAR NOT NULL,
                    documents_used INTEGER NOT NULL DEFAULT 0,
                    beta_feature_flags JSON,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE cotizaciones (
                    id INTEGER PRIMARY KEY,
                    tenant_id INTEGER NOT NULL,
                    serie VARCHAR,
                    document_kind VARCHAR,
                    source_quote_id INTEGER,
                    nota_referencia_id INTEGER,
                    total_gravada NUMERIC(12, 2),
                    total_exonerada NUMERIC(12, 2),
                    total_inafecta NUMERIC(12, 2),
                    total_igv NUMERIC(12, 2),
                    total_venta NUMERIC(12, 2),
                    estado VARCHAR,
                    tipo_comprobante VARCHAR,
                    fecha_vencimiento TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE pagos (
                    id INTEGER PRIMARY KEY,
                    tenant_id INTEGER NOT NULL,
                    cotizacion_id INTEGER NOT NULL,
                    source_quote_id INTEGER,
                    fiscal_document_id INTEGER,
                    tipo VARCHAR,
                    monto_pagado NUMERIC(12, 2),
                    fecha_pago TIMESTAMP
                )
                """
            )
        )


def scalar(engine, sql, params=None):
    with engine.connect() as conn:
        return conn.execute(text(sql), params or {}).scalar()


def test_dry_run_does_not_write_changes():
    from migrate_beta_integrity import run_integrity_check

    engine = make_engine()
    setup_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO tenants (id, is_active) VALUES (1, 1)"))

    report = run_integrity_check(engine=engine, apply=False, echo=False)

    assert report.exit_code == 0
    assert scalar(engine, "SELECT COUNT(*) FROM subscriptions") == 0
    assert any("Crear Subscription trial para tenant 1" in action for action in report.planned_actions)


def test_apply_creates_trial_subscription_for_tenant_without_subscription():
    from migrate_beta_integrity import run_integrity_check

    engine = make_engine()
    setup_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO tenants (id, is_active) VALUES (1, 1)"))

    report = run_integrity_check(engine=engine, apply=True, echo=False)

    assert report.exit_code == 0
    assert scalar(engine, "SELECT status FROM subscriptions WHERE tenant_id = 1") == "trial"
    assert scalar(engine, "SELECT plan_code FROM subscriptions WHERE tenant_id = 1") == "launch"
    assert any("Subscription trial creada para tenant 1" in action for action in report.applied_actions)


def test_unknown_subscription_status_fails():
    from migrate_beta_integrity import run_integrity_check

    engine = make_engine()
    setup_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO tenants (id, is_active) VALUES (1, 1)"))
        conn.execute(
            text(
                """
                INSERT INTO subscriptions (tenant_id, status, plan_code, documents_used)
                VALUES (1, 'mystery', 'launch', 0)
                """
            )
        )

    report = run_integrity_check(engine=engine, apply=False, echo=False)

    assert report.exit_code == 1
    assert any("Subscription.status desconocido" in blocker for blocker in report.blockers)


def test_duplicate_subscription_fails():
    from migrate_beta_integrity import run_integrity_check

    engine = make_engine()
    setup_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO tenants (id, is_active) VALUES (1, 1)"))
        conn.execute(
            text(
                """
                INSERT INTO subscriptions (tenant_id, status, plan_code, documents_used)
                VALUES (1, 'trial', 'launch', 0), (1, 'active', 'launch', 0)
                """
            )
        )

    report = run_integrity_check(engine=engine, apply=False, echo=False)

    assert report.exit_code == 1
    assert any("Tenant 1 tiene 2 subscriptions" in blocker for blocker in report.blockers)


def test_apply_links_legacy_payment_with_exactly_one_accepted_fiscal_document():
    from migrate_beta_integrity import run_integrity_check

    engine = make_engine()
    setup_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO tenants (id, is_active) VALUES (1, 1)"))
        conn.execute(
            text(
                """
                INSERT INTO subscriptions (tenant_id, status, plan_code, documents_used)
                VALUES (1, 'trial', 'launch', 0)
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO cotizaciones (
                    id, tenant_id, serie, document_kind, source_quote_id,
                    total_gravada, total_exonerada, total_inafecta, total_igv, total_venta,
                    estado, tipo_comprobante
                ) VALUES (
                    10, 1, 'F001', 'fiscal_document', 5,
                    100, 0, 0, 18, 118,
                    'facturada', '01'
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO pagos (
                    id, tenant_id, cotizacion_id, source_quote_id,
                    fiscal_document_id, tipo, monto_pagado
                ) VALUES (20, 1, 5, 5, NULL, 'pago', 50)
                """
            )
        )

    report = run_integrity_check(engine=engine, apply=True, echo=False)

    assert report.exit_code == 0
    assert scalar(engine, "SELECT fiscal_document_id FROM pagos WHERE id = 20") == 10


def test_ambiguous_legacy_payment_is_not_linked_and_fails():
    from migrate_beta_integrity import run_integrity_check

    engine = make_engine()
    setup_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO tenants (id, is_active) VALUES (1, 1)"))
        conn.execute(
            text(
                """
                INSERT INTO subscriptions (tenant_id, status, plan_code, documents_used)
                VALUES (1, 'trial', 'launch', 0)
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO cotizaciones (
                    id, tenant_id, serie, document_kind, source_quote_id,
                    total_gravada, total_exonerada, total_inafecta, total_igv, total_venta,
                    estado, tipo_comprobante
                ) VALUES
                (10, 1, 'F001', 'fiscal_document', 5, 100, 0, 0, 18, 118, 'facturada', '01'),
                (11, 1, 'F002', 'fiscal_document', 5, 100, 0, 0, 18, 118, 'facturada', '01')
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO pagos (
                    id, tenant_id, cotizacion_id, source_quote_id,
                    fiscal_document_id, tipo, monto_pagado
                ) VALUES (20, 1, 5, 5, NULL, 'pago', 50)
                """
            )
        )

    report = run_integrity_check(engine=engine, apply=True, echo=False)

    assert report.exit_code == 1
    assert scalar(engine, "SELECT fiscal_document_id FROM pagos WHERE id = 20") is None
    assert any("Pago legacy 20 tiene 2 fiscales aceptados candidatos" in blocker for blocker in report.blockers)


def test_advance_payment_is_not_converted():
    from migrate_beta_integrity import run_integrity_check

    engine = make_engine()
    setup_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO tenants (id, is_active) VALUES (1, 1)"))
        conn.execute(
            text(
                """
                INSERT INTO subscriptions (tenant_id, status, plan_code, documents_used)
                VALUES (1, 'trial', 'launch', 0)
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO cotizaciones (
                    id, tenant_id, serie, document_kind, source_quote_id,
                    total_gravada, total_exonerada, total_inafecta, total_igv, total_venta,
                    estado, tipo_comprobante
                ) VALUES (10, 1, 'F001', 'fiscal_document', 5, 100, 0, 0, 18, 118, 'facturada', '01')
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO pagos (
                    id, tenant_id, cotizacion_id, source_quote_id,
                    fiscal_document_id, tipo, monto_pagado
                ) VALUES (20, 1, 5, 5, NULL, 'adelanto', 50)
                """
            )
        )

    report = run_integrity_check(engine=engine, apply=True, echo=False)

    assert report.exit_code == 0
    assert scalar(engine, "SELECT fiscal_document_id FROM pagos WHERE id = 20") is None
    assert scalar(engine, "SELECT tipo FROM pagos WHERE id = 20") == "adelanto"


def test_note_without_reference_fails():
    from migrate_beta_integrity import run_integrity_check

    engine = make_engine()
    setup_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO tenants (id, is_active) VALUES (1, 1)"))
        conn.execute(
            text(
                """
                INSERT INTO subscriptions (tenant_id, status, plan_code, documents_used)
                VALUES (1, 'trial', 'launch', 0)
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO cotizaciones (
                    id, tenant_id, serie, document_kind, nota_referencia_id,
                    total_gravada, total_exonerada, total_inafecta, total_igv, total_venta,
                    estado, tipo_comprobante
                ) VALUES (10, 1, 'FC01', 'credit_note', NULL, 100, 0, 0, 18, 118, 'facturada', '07')
                """
            )
        )

    report = run_integrity_check(engine=engine, apply=False, echo=False)

    assert report.exit_code == 1
    assert any("Nota 10 no tiene nota_referencia_id" in blocker for blocker in report.blockers)


def test_indexes_are_created_idempotently():
    from migrate_beta_integrity import run_integrity_check

    engine = make_engine()
    setup_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO tenants (id, is_active) VALUES (1, 1)"))
        conn.execute(
            text(
                """
                INSERT INTO subscriptions (tenant_id, status, plan_code, documents_used)
                VALUES (1, 'trial', 'launch', 0)
                """
            )
        )

    first = run_integrity_check(engine=engine, apply=True, echo=False)
    second = run_integrity_check(engine=engine, apply=True, echo=False)

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert second.applied_actions == []
    assert scalar(
        engine,
        "SELECT COUNT(*) FROM sqlite_master WHERE type = 'index' AND name = 'idx_beta_pagos_fiscal'",
    ) == 1


def test_apply_second_run_does_not_modify_data_again():
    from migrate_beta_integrity import run_integrity_check

    engine = make_engine()
    setup_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO tenants (id, is_active) VALUES (1, 1)"))
        conn.execute(
            text(
                """
                INSERT INTO cotizaciones (
                    id, tenant_id, serie, document_kind,
                    total_gravada, total_exonerada, total_inafecta, total_igv, total_venta,
                    estado, tipo_comprobante
                ) VALUES (10, 1, 'COT', NULL, NULL, NULL, NULL, NULL, NULL, 'pendiente', '00')
                """
            )
        )

    first = run_integrity_check(engine=engine, apply=True, echo=False)
    second = run_integrity_check(engine=engine, apply=True, echo=False)

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert second.applied_actions == []
    assert scalar(engine, "SELECT document_kind FROM cotizaciones WHERE id = 10") == "quotation"


def test_postgresql_prefiscal_index_sql_is_partial():
    from migrate_beta_integrity import prefiscal_unapplied_index_sql

    sql = prefiscal_unapplied_index_sql("postgresql")

    assert "WHERE fiscal_document_id IS NULL" in sql
    assert "ON pagos (tenant_id, source_quote_id, tipo)" in sql


def test_sqlite_prefiscal_index_sql_is_not_partial():
    from migrate_beta_integrity import prefiscal_unapplied_index_sql

    sql = prefiscal_unapplied_index_sql("sqlite")

    assert "WHERE fiscal_document_id IS NULL" not in sql
    assert "fiscal_document_id" in sql
