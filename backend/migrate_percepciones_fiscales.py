"""Migracion idempotente: tabla percepciones_fiscales."""

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
    print("=== Migracion percepciones_fiscales ===")
    with engine.connect() as conn:
        if _table_exists(conn, "percepciones_fiscales"):
            print("[OK] percepciones_fiscales ya existe.")
            return

        if engine.dialect.name == "sqlite":
            conn.execute(
                text(
                    """
                    CREATE TABLE percepciones_fiscales (
                        id INTEGER PRIMARY KEY,
                        tenant_id INTEGER NOT NULL,
                        usuario_id INTEGER,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        serie VARCHAR NOT NULL,
                        correlativo VARCHAR NOT NULL,
                        fecha_emision DATETIME NOT NULL,
                        cliente_tipo_doc VARCHAR NOT NULL,
                        cliente_num_doc VARCHAR NOT NULL,
                        cliente_rzn_social VARCHAR NOT NULL,
                        regimen VARCHAR NOT NULL DEFAULT '01',
                        tasa NUMERIC(5, 2) NOT NULL DEFAULT 2,
                        imp_percibido NUMERIC(12, 2) NOT NULL DEFAULT 0,
                        imp_cobrado NUMERIC(12, 2) NOT NULL DEFAULT 0,
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
            for column in (
                "tenant_id",
                "usuario_id",
                "serie",
                "correlativo",
                "fecha_emision",
                "cliente_num_doc",
                "status",
                "ticket",
            ):
                conn.execute(text(f"CREATE INDEX ix_percepciones_fiscales_{column} ON percepciones_fiscales ({column})"))
        else:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS percepciones_fiscales (
                        id SERIAL PRIMARY KEY,
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id),
                        usuario_id INTEGER REFERENCES users(id),
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        serie VARCHAR NOT NULL,
                        correlativo VARCHAR NOT NULL,
                        fecha_emision TIMESTAMP NOT NULL,
                        cliente_tipo_doc VARCHAR NOT NULL,
                        cliente_num_doc VARCHAR NOT NULL,
                        cliente_rzn_social VARCHAR NOT NULL,
                        regimen VARCHAR NOT NULL DEFAULT '01',
                        tasa NUMERIC(5, 2) NOT NULL DEFAULT 2,
                        imp_percibido NUMERIC(12, 2) NOT NULL DEFAULT 0,
                        imp_cobrado NUMERIC(12, 2) NOT NULL DEFAULT 0,
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
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_percepciones_fiscales_tenant_id ON percepciones_fiscales (tenant_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_percepciones_fiscales_usuario_id ON percepciones_fiscales (usuario_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_percepciones_fiscales_serie ON percepciones_fiscales (serie)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_percepciones_fiscales_correlativo ON percepciones_fiscales (correlativo)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_percepciones_fiscales_fecha_emision ON percepciones_fiscales (fecha_emision)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_percepciones_fiscales_cliente_num_doc ON percepciones_fiscales (cliente_num_doc)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_percepciones_fiscales_status ON percepciones_fiscales (status)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_percepciones_fiscales_ticket ON percepciones_fiscales (ticket)"))

        conn.commit()
    print("[OK] percepciones_fiscales listo.")


if __name__ == "__main__":
    run_migration()
