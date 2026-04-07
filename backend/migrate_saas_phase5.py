"""
==========================================================
MIGRACION: Fase 5 - Superadmin / SaaS Billing Domain
==========================================================
Crea las tablas de control SaaS de PrintFlow:
  - subscriptions       (estado y plan de cada tenant)
  - subscription_payments (pagos SaaS tenant → PrintFlow)

SEPARACION DE DOMINIOS:
  - subscriptions/subscription_payments → PrintFlow cobra al tenant
  - pagos                               → tenant cobra a su cliente
  Nunca mezclar.

Ejecutar con:
    cd backend
    python migrate_saas_phase5.py
==========================================================
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from sqlalchemy import inspect, text
from database import engine


def table_exists(inspector, table: str) -> bool:
    return table in inspector.get_table_names()


def column_exists(inspector, table: str, column: str) -> bool:
    try:
        columns = [c["name"] for c in inspector.get_columns(table)]
        return column in columns
    except Exception:
        return False


def run_migration():
    inspector = inspect(engine)

    with engine.begin() as conn:

        # ----------------------------------------------------------
        # 1. Tabla: subscriptions
        # ----------------------------------------------------------
        if not table_exists(inspector, "subscriptions"):
            print("[+] Creando tabla 'subscriptions'...")
            conn.execute(text("""
                CREATE TABLE subscriptions (
                    id              SERIAL PRIMARY KEY,
                    tenant_id       INTEGER NOT NULL UNIQUE REFERENCES tenants(id),
                    status          VARCHAR NOT NULL DEFAULT 'trial',
                    plan_code       VARCHAR NOT NULL DEFAULT 'launch',
                    current_price   NUMERIC(10,2),
                    founder_price   NUMERIC(10,2),
                    billing_started_at TIMESTAMP,
                    billing_due_at  TIMESTAMP,
                    grace_until     TIMESTAMP,
                    max_users       INTEGER DEFAULT 5,
                    max_documents   INTEGER DEFAULT 500,
                    documents_used  INTEGER NOT NULL DEFAULT 0,
                    onboarding_status VARCHAR NOT NULL DEFAULT 'not_started',
                    notes_internal  TEXT,
                    created_at      TIMESTAMP DEFAULT NOW(),
                    updated_at      TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX idx_subscriptions_tenant_id ON subscriptions(tenant_id)"))
            conn.execute(text("CREATE INDEX idx_subscriptions_status ON subscriptions(status)"))
            print("    OK: tabla 'subscriptions' creada.")
        else:
            print("[ ] Tabla 'subscriptions' ya existe, omitiendo creacion.")

        # ----------------------------------------------------------
        # 2. Tabla: subscription_payments
        # ----------------------------------------------------------
        if not table_exists(inspector, "subscription_payments"):
            print("[+] Creando tabla 'subscription_payments'...")
            conn.execute(text("""
                CREATE TABLE subscription_payments (
                    id              SERIAL PRIMARY KEY,
                    tenant_id       INTEGER NOT NULL REFERENCES tenants(id),
                    amount          NUMERIC(10,2) NOT NULL,
                    currency        VARCHAR NOT NULL DEFAULT 'PEN',
                    method          VARCHAR NOT NULL,
                    reference       VARCHAR,
                    paid_at         TIMESTAMP,
                    validated_by_user_id INTEGER REFERENCES users(id),
                    notes           TEXT,
                    created_at      TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX idx_sub_payments_tenant_id ON subscription_payments(tenant_id)"))
            print("    OK: tabla 'subscription_payments' creada.")
        else:
            print("[ ] Tabla 'subscription_payments' ya existe, omitiendo creacion.")

        # ----------------------------------------------------------
        # 3. Crear suscripciones trial para tenants existentes
        #    (para que cada tenant tenga registro desde el inicio)
        # ----------------------------------------------------------
        print("[+] Creando registros trial para tenants sin suscripcion...")
        result = conn.execute(text("""
            INSERT INTO subscriptions (tenant_id, status, plan_code, created_at, updated_at)
            SELECT t.id, 'trial', 'launch', NOW(), NOW()
            FROM tenants t
            LEFT JOIN subscriptions s ON s.tenant_id = t.id
            WHERE s.id IS NULL
        """))
        print(f"    OK: {result.rowcount} suscripciones trial creadas.")

    print("\nMigracion Fase 5 completada exitosamente.")


if __name__ == "__main__":
    run_migration()
