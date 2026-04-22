"""
MIGRACION: Cola Durable de Emision Fiscal
=========================================
Crea la tabla `document_emission_jobs` para desacoplar el request HTTP
de la emision real hacia ApisPeru/SUNAT.

Ejecutar con:
    cd backend
    python migrate_emission_jobs.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text

from database import engine


def table_exists(inspector, table: str) -> bool:
    return table in inspector.get_table_names()


def run_migration():
    inspector = inspect(engine)

    with engine.begin() as conn:
        if table_exists(inspector, "document_emission_jobs"):
            print("[ ] Tabla 'document_emission_jobs' ya existe, omitiendo creación.")
            return

        print("[+] Creando tabla 'document_emission_jobs'...")
        conn.execute(
            text(
                """
                CREATE TABLE document_emission_jobs (
                    id SERIAL PRIMARY KEY,
                    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
                    created_by_user_id INTEGER NULL REFERENCES users(id),
                    resource_type VARCHAR NOT NULL,
                    resource_id INTEGER NOT NULL,
                    action VARCHAR NOT NULL,
                    provider VARCHAR NULL,
                    status VARCHAR NOT NULL DEFAULT 'queued',
                    priority INTEGER NOT NULL DEFAULT 100,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 5,
                    idempotency_key VARCHAR NOT NULL UNIQUE,
                    payload_snapshot JSON NULL,
                    result_snapshot JSON NULL,
                    provider_ticket VARCHAR NULL,
                    last_error TEXT NULL,
                    available_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    locked_at TIMESTAMP NULL,
                    processing_started_at TIMESTAMP NULL,
                    finished_at TIMESTAMP NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX idx_document_emission_jobs_dispatch
                ON document_emission_jobs(status, available_at, priority, created_at)
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX idx_document_emission_jobs_tenant_resource
                ON document_emission_jobs(tenant_id, resource_type, resource_id)
                """
            )
        )
        print("    OK: tabla 'document_emission_jobs' creada.")


if __name__ == "__main__":
    run_migration()
