"""Migracion idempotente: tabla reversiones_fiscales."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text

from database import engine


def _table_exists(conn, table: str) -> bool:
    if engine.dialect.name == "sqlite":
        result = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:table"),
            {"table": table},
        ).first()
        return result is not None

    result = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_name = :table_name
            LIMIT 1
            """
        ),
        {"table_name": table},
    ).first()
    return result is not None


def run_migration():
    print("=== Migracion reversiones_fiscales ===")
    with engine.connect() as conn:
        if _table_exists(conn, "reversiones_fiscales"):
            print("[OK] reversiones_fiscales ya existe.")
            return

        if engine.dialect.name == "sqlite":
            conn.execute(
                text(
                    """
                    CREATE TABLE reversiones_fiscales (
                        id INTEGER PRIMARY KEY,
                        tenant_id INTEGER NOT NULL,
                        usuario_id INTEGER,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        correlativo VARCHAR NOT NULL,
                        fec_generacion DATETIME NOT NULL,
                        fec_comunicacion DATETIME NOT NULL,
                        details_count INTEGER NOT NULL DEFAULT 0,
                        status VARCHAR NOT NULL DEFAULT 'pending',
                        success BOOLEAN NOT NULL DEFAULT 0,
                        ticket VARCHAR,
                        sunat_error TEXT,
                        sunat_hash VARCHAR,
                        provider_endpoint VARCHAR,
                        provider_status_code INTEGER,
                        payload_snapshot JSON,
                        provider_response JSON,
                        FOREIGN KEY(tenant_id) REFERENCES tenants(id),
                        FOREIGN KEY(usuario_id) REFERENCES users(id)
                    )
                    """
                )
            )
            for column in ("tenant_id", "usuario_id", "correlativo", "fec_comunicacion", "status", "ticket"):
                conn.execute(text(f"CREATE INDEX ix_reversiones_fiscales_{column} ON reversiones_fiscales ({column})"))
        else:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS reversiones_fiscales (
                        id SERIAL PRIMARY KEY,
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id),
                        usuario_id INTEGER REFERENCES users(id),
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        correlativo VARCHAR NOT NULL,
                        fec_generacion TIMESTAMP NOT NULL,
                        fec_comunicacion TIMESTAMP NOT NULL,
                        details_count INTEGER NOT NULL DEFAULT 0,
                        status VARCHAR NOT NULL DEFAULT 'pending',
                        success BOOLEAN NOT NULL DEFAULT FALSE,
                        ticket VARCHAR,
                        sunat_error TEXT,
                        sunat_hash VARCHAR,
                        provider_endpoint VARCHAR,
                        provider_status_code INTEGER,
                        payload_snapshot JSONB,
                        provider_response JSONB
                    )
                    """
                )
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_reversiones_fiscales_tenant_id ON reversiones_fiscales (tenant_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_reversiones_fiscales_usuario_id ON reversiones_fiscales (usuario_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_reversiones_fiscales_correlativo ON reversiones_fiscales (correlativo)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_reversiones_fiscales_fec_comunicacion ON reversiones_fiscales (fec_comunicacion)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_reversiones_fiscales_status ON reversiones_fiscales (status)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_reversiones_fiscales_ticket ON reversiones_fiscales (ticket)"))

        conn.commit()
    print("[OK] reversiones_fiscales listo.")


if __name__ == "__main__":
    run_migration()
