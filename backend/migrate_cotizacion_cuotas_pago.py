"""Migracion idempotente: cuotas_pago en cotizaciones.

Guarda el cronograma fiscal de facturas al credito segun SUNAT.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text

from database import engine


def _column_exists(conn, table: str, column: str) -> bool:
    dialect = engine.dialect.name
    if dialect == "sqlite":
        columns = [
            row[1]
            for row in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        ]
        return column in columns

    result = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = :table_name
              AND column_name = :column_name
            LIMIT 1
            """
        ),
        {"table_name": table, "column_name": column},
    ).first()
    return result is not None


def run_migration():
    print("=== Migracion cotizaciones.cuotas_pago ===")
    with engine.connect() as conn:
        if _column_exists(conn, "cotizaciones", "cuotas_pago"):
            print("[OK] cotizaciones.cuotas_pago ya existe.")
            return

        column_type = "JSON" if engine.dialect.name == "sqlite" else "JSONB"
        print("[MIGRANDO] Agregando cotizaciones.cuotas_pago...")
        conn.execute(
            text(f"ALTER TABLE cotizaciones ADD COLUMN cuotas_pago {column_type}")
        )
        conn.commit()
    print("[OK] cotizaciones.cuotas_pago listo.")


if __name__ == "__main__":
    run_migration()
