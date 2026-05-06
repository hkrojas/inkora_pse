from __future__ import annotations

import json

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

import models  # noqa: F401 - registra modelos en metadata
from cleanup_beta_test_data import EXPECTED_ALEMBIC_VERSION, run_cleanup
from database import Base


def make_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def setup_schema(engine):
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR NOT NULL)"))
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
            {"version": EXPECTED_ALEMBIC_VERSION},
        )


def scalar(engine, sql, params=None):
    with engine.connect() as conn:
        return conn.execute(text(sql), params or {}).scalar()


def rows(engine, sql, params=None):
    with engine.connect() as conn:
        return conn.execute(text(sql), params or {}).mappings().all()


def valid_apply_env(tmp_path, **overrides):
    backup = tmp_path / "backup.dump"
    backup.write_text("fake backup", encoding="utf-8")
    env = {
        "DATABASE_URL": "sqlite://",
        "ENVIRONMENT": "staging",
        "ALLOW_BETA_DATA_CLEANUP": "true",
        "BETA_DATA_CLEANUP_CONFIRM": "CLEAN_TEST_RECORDS",
        "BETA_DB_BACKUP_PATH": str(backup),
        "BETA_CLEANUP_MODE": "test_tenants_only",
    }
    env.update(overrides)
    return env


def seed_tenant(conn, tenant_id, name, ruc, *, active=True):
    conn.execute(
        text(
            """
            INSERT INTO tenants (id, business_name, business_ruc, business_address, is_active)
            VALUES (:id, :name, :ruc, 'Av. Test 123', :active)
            """
        ),
        {"id": tenant_id, "name": name, "ruc": ruc, "active": active},
    )


def seed_user(conn, user_id, tenant_id, email, *, superadmin=False, active=True, rol="admin"):
    conn.execute(
        text(
            """
            INSERT INTO users (
                id, email, hashed_password, nombre_completo, rol,
                is_superadmin, is_active, must_change_password, tenant_id
            )
            VALUES (
                :id, :email, 'hash', :email, :rol,
                :superadmin, :active, :must_change_password, :tenant_id
            )
            """
        ),
        {
            "id": user_id,
            "tenant_id": tenant_id,
            "email": email,
            "rol": rol,
            "superadmin": superadmin,
            "active": active,
            "must_change_password": False,
        },
    )


def seed_subscription(conn, tenant_id, *, flags=None, status="trial"):
    conn.execute(
        text(
            """
            INSERT INTO subscriptions (
                tenant_id, status, plan_code, documents_used, beta_feature_flags,
                onboarding_status, is_pilot
            )
            VALUES (:tenant_id, :status, 'launch', 0, :flags, 'not_started', :is_pilot)
            """
        ),
        {"tenant_id": tenant_id, "status": status, "flags": json.dumps(flags or {}), "is_pilot": False},
    )


def seed_business_rows(conn, tenant_id, user_id, *, suffix):
    cliente_id = 100 + suffix
    producto_id = 200 + suffix
    cotizacion_id = 300 + suffix
    guia_id = 400 + suffix
    conn.execute(
        text(
            """
            INSERT INTO clientes (id, tenant_id, tipo_documento, numero_documento, razon_social)
            VALUES (:id, :tenant_id, '6', :doc, :name)
            """
        ),
        {"id": cliente_id, "tenant_id": tenant_id, "doc": f"20{suffix:09d}", "name": f"Cliente {suffix}"},
    )
    conn.execute(
        text(
            """
            INSERT INTO productos (id, tenant_id, nombre, precio_unitario)
            VALUES (:id, :tenant_id, :name, 118)
            """
        ),
        {"id": producto_id, "tenant_id": tenant_id, "name": f"Producto {suffix}"},
    )
    conn.execute(
        text(
            """
            INSERT INTO cotizaciones (
                id, tenant_id, cliente_id, usuario_id, serie, correlativo,
                document_kind, estado, tipo_comprobante, total_venta
            )
            VALUES (
                :id, :tenant_id, :cliente_id, :usuario_id, 'COT', :corr,
                'quotation', 'pendiente', '00', 118
            )
            """
        ),
        {
            "id": cotizacion_id,
            "tenant_id": tenant_id,
            "cliente_id": cliente_id,
            "usuario_id": user_id,
            "corr": suffix,
        },
    )
    conn.execute(
        text(
            """
            INSERT INTO cotizacion_items (
                cotizacion_id, producto_id, descripcion, cantidad, precio_unitario
            )
            VALUES (:cotizacion_id, :producto_id, 'Item', 1, 118)
            """
        ),
        {"cotizacion_id": cotizacion_id, "producto_id": producto_id},
    )
    conn.execute(
        text(
            """
            INSERT INTO pagos (
                tenant_id, cotizacion_id, source_quote_id, monto_pagado, metodo_pago, tipo
            )
            VALUES (:tenant_id, :cotizacion_id, :cotizacion_id, 10, 'Yape', 'adelanto')
            """
        ),
        {"tenant_id": tenant_id, "cotizacion_id": cotizacion_id},
    )
    conn.execute(
        text(
            """
            INSERT INTO guias_remision (
                id, tenant_id, cotizacion_id, usuario_id, serie, correlativo,
                fecha_traslado, motivo_traslado, peso_bruto_total
            )
            VALUES (
                :id, :tenant_id, :cotizacion_id, :usuario_id, 'T001', :corr,
                CURRENT_TIMESTAMP, '01', 1
            )
            """
        ),
        {
            "id": guia_id,
            "tenant_id": tenant_id,
            "cotizacion_id": cotizacion_id,
            "usuario_id": user_id,
            "corr": suffix,
        },
    )
    conn.execute(
        text(
            """
            INSERT INTO guia_remision_items (guia_id, descripcion, cantidad)
            VALUES (:guia_id, 'Item guia', 1)
            """
        ),
        {"guia_id": guia_id},
    )
    conn.execute(
        text(
            """
            INSERT INTO document_emission_jobs (
                tenant_id, created_by_user_id, resource_type, resource_id,
                action, status, priority, attempts, max_attempts,
                idempotency_key, available_at, created_at, updated_at
            )
            VALUES (
                :tenant_id, :user_id, 'cotizacion', :cotizacion_id,
                'emit_fiscal_document', 'queued', 100, 0, 5,
                :key, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "cotizacion_id": cotizacion_id,
            "key": f"job-{suffix}",
        },
    )


def seed_common(engine):
    with engine.begin() as conn:
        seed_tenant(conn, 1, "Inkora Admin", "00000000000")
        seed_user(conn, 1, 1, "default-superadmin@test.local", superadmin=True, rol="superadmin")
        seed_tenant(conn, 2, "Inkora E2E Staging", "20999999991")
        seed_user(conn, 2, 2, "e2e@test.local")
        seed_subscription(conn, 2)
        seed_tenant(conn, 3, "Cliente Real SAC", "20111111111")
        seed_user(conn, 3, 3, "real@test.local")
        seed_subscription(conn, 3)
        seed_business_rows(conn, 2, 2, suffix=2)
        seed_business_rows(conn, 3, 3, suffix=3)


def test_dry_run_no_escribe_datos():
    engine = make_engine()
    setup_schema(engine)
    seed_common(engine)

    report = run_cleanup(engine=engine, env={"DATABASE_URL": "sqlite://"}, apply=False, echo=False)

    assert report.exit_code == 0
    assert scalar(engine, "SELECT COUNT(*) FROM clientes WHERE tenant_id = 2") == 1
    assert scalar(engine, "SELECT is_active FROM tenants WHERE id = 2") == 1


def test_apply_sin_confirmacion_falla(tmp_path):
    engine = make_engine()
    setup_schema(engine)
    seed_common(engine)

    report = run_cleanup(engine=engine, env={"DATABASE_URL": "sqlite://"}, apply=True, echo=False)

    assert report.exit_code == 1
    assert any("ALLOW_BETA_DATA_CLEANUP" in blocker for blocker in report.blockers)
    assert scalar(engine, "SELECT COUNT(*) FROM clientes WHERE tenant_id = 2") == 1


def test_apply_sin_backup_falla():
    engine = make_engine()
    setup_schema(engine)
    seed_common(engine)

    report = run_cleanup(
        engine=engine,
        env={
            "DATABASE_URL": "sqlite://",
            "ENVIRONMENT": "staging",
            "ALLOW_BETA_DATA_CLEANUP": "true",
            "BETA_DATA_CLEANUP_CONFIRM": "CLEAN_TEST_RECORDS",
        },
        apply=True,
        echo=False,
    )

    assert report.exit_code == 1
    assert any("BETA_DB_BACKUP_PATH" in blocker for blocker in report.blockers)
    assert scalar(engine, "SELECT COUNT(*) FROM clientes WHERE tenant_id = 2") == 1


def test_apply_no_toca_alembic_version_y_solo_limpia_tenants_test(tmp_path):
    engine = make_engine()
    setup_schema(engine)
    seed_common(engine)

    report = run_cleanup(engine=engine, env=valid_apply_env(tmp_path), apply=True, echo=False)

    assert report.exit_code == 0
    assert scalar(engine, "SELECT version_num FROM alembic_version") == EXPECTED_ALEMBIC_VERSION
    assert scalar(engine, "SELECT COUNT(*) FROM clientes WHERE tenant_id = 2") == 0
    assert scalar(engine, "SELECT COUNT(*) FROM cotizaciones WHERE tenant_id = 2") == 0
    assert scalar(engine, "SELECT COUNT(*) FROM document_emission_jobs WHERE tenant_id = 2") == 0
    assert scalar(engine, "SELECT is_active FROM tenants WHERE id = 2") == 0
    assert scalar(engine, "SELECT COUNT(*) FROM clientes WHERE tenant_id = 3") == 1
    assert scalar(engine, "SELECT is_active FROM tenants WHERE id = 3") == 1


def test_superadmin_propio_se_crea_y_default_se_desactiva(tmp_path):
    engine = make_engine()
    setup_schema(engine)
    seed_common(engine)

    env = valid_apply_env(
        tmp_path,
        BETA_SUPERADMIN_EMAIL="owner@example.com",
        BETA_SUPERADMIN_PASSWORD="TempPassword123!",
        BETA_DEFAULT_SUPERADMIN_EMAIL="default-superadmin@test.local",
        BETA_DEFAULT_SUPERADMIN_ACTION="disable",
    )
    report = run_cleanup(engine=engine, env=env, apply=True, echo=False)

    assert report.exit_code == 0
    owner = rows(engine, "SELECT is_superadmin, is_active, rol, tenant_id FROM users WHERE email = 'owner@example.com'")[0]
    assert owner["is_superadmin"] == 1
    assert owner["is_active"] == 1
    assert owner["rol"] == "superadmin"
    assert scalar(engine, "SELECT business_name FROM tenants WHERE id = :id", {"id": owner["tenant_id"]}) == "Inkora Admin"
    assert scalar(engine, "SELECT is_active FROM users WHERE email = 'default-superadmin@test.local'") == 0


def test_no_permite_cero_superadmins_activos(tmp_path):
    engine = make_engine()
    setup_schema(engine)
    with engine.begin() as conn:
        seed_tenant(conn, 1, "Inkora Admin", "00000000000")
        seed_user(conn, 1, 1, "default-superadmin@test.local", superadmin=True, rol="superadmin")

    env = valid_apply_env(
        tmp_path,
        BETA_DEFAULT_SUPERADMIN_EMAIL="default-superadmin@test.local",
        BETA_DEFAULT_SUPERADMIN_ACTION="disable",
    )
    report = run_cleanup(engine=engine, env=env, apply=True, echo=False)

    assert report.exit_code == 1
    assert any("cero superadmins activos" in blocker for blocker in report.blockers)
    assert scalar(engine, "SELECT is_active FROM users WHERE email = 'default-superadmin@test.local'") == 1


def test_crea_tenant_real_usuario_subscription_y_flags_seguros(tmp_path):
    engine = make_engine()
    setup_schema(engine)
    seed_common(engine)

    env = valid_apply_env(
        tmp_path,
        BETA_TENANT_RUC="20600000001",
        BETA_TENANT_NAME="Tenant Beta Real",
        BETA_TENANT_ADDRESS="Av. Fiscal 100",
        BETA_TENANT_ADMIN_EMAIL="admin@tenant-real.pe",
        BETA_TENANT_ADMIN_PASSWORD="TenantPassword123!",
        BETA_PLAN_CODE="beta",
        BETA_SUBSCRIPTION_STATUS="trial",
    )
    report = run_cleanup(engine=engine, env=env, apply=True, echo=False)

    assert report.exit_code == 0
    tenant_id = scalar(engine, "SELECT id FROM tenants WHERE business_ruc = '20600000001'")
    assert tenant_id is not None
    user = rows(engine, "SELECT tenant_id, is_superadmin, is_active, rol FROM users WHERE email = 'admin@tenant-real.pe'")[0]
    assert user["tenant_id"] == tenant_id
    assert user["is_superadmin"] == 0
    assert user["is_active"] == 1
    assert user["rol"] == "admin"
    sub = rows(engine, "SELECT status, plan_code, beta_feature_flags FROM subscriptions WHERE tenant_id = :tenant_id", {"tenant_id": tenant_id})[0]
    assert sub["status"] == "trial"
    assert sub["plan_code"] == "beta"
    flags = json.loads(sub["beta_feature_flags"])
    assert all(value is False for value in flags.values())
    assert flags["direct_sunat"] is False


def test_enable_flags_no_puede_encender_direct_sunat(tmp_path):
    engine = make_engine()
    setup_schema(engine)
    seed_common(engine)

    env = valid_apply_env(
        tmp_path,
        BETA_TENANT_RUC="20600000002",
        BETA_TENANT_NAME="Tenant Beta Flags",
        BETA_TENANT_ADDRESS="Av. Fiscal 200",
        BETA_TENANT_ADMIN_EMAIL="admin2@tenant-real.pe",
        BETA_TENANT_ADMIN_PASSWORD="TenantPassword123!",
        BETA_ENABLE_FLAGS="credit_notes,direct_sunat",
    )
    report = run_cleanup(engine=engine, env=env, apply=True, echo=False)

    assert report.exit_code == 1
    assert any("direct_sunat" in blocker for blocker in report.blockers)
    assert scalar(engine, "SELECT COUNT(*) FROM tenants WHERE business_ruc = '20600000002'") == 0


def test_no_borra_audit_logs_por_defecto(tmp_path):
    engine = make_engine()
    setup_schema(engine)
    seed_common(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details)
                VALUES (2, 'test.action', 'tenant', 2, 'audit test')
                """
            )
        )

    report = run_cleanup(engine=engine, env=valid_apply_env(tmp_path), apply=True, echo=False)

    assert report.exit_code == 0
    assert scalar(engine, "SELECT COUNT(*) FROM audit_logs") == 1
