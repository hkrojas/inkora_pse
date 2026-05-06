"""Migracion idempotente: cliente_id en guias_remision.

Permite crear guias de remision con destinatario directo, no solo mediante
cotizacion relacionada.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text

from database import engine


def _column_exists(conn, table: str, column: str) -> bool:
    if engine.dialect.name == "sqlite":
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
    print("=== Migracion guias_remision.cliente_id ===")
    with engine.connect() as conn:
        if _column_exists(conn, "guias_remision", "cliente_id"):
            print("[OK] guias_remision.cliente_id ya existe.")
            return

        print("[MIGRANDO] Agregando guias_remision.cliente_id...")
        conn.execute(text("ALTER TABLE guias_remision ADD COLUMN cliente_id INTEGER"))
        if engine.dialect.name != "sqlite":
            conn.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM pg_constraint
                            WHERE conname = 'fk_guias_remision_cliente_id'
                        ) THEN
                            ALTER TABLE guias_remision
                            ADD CONSTRAINT fk_guias_remision_cliente_id
                            FOREIGN KEY (cliente_id) REFERENCES clientes(id);
                        END IF;
                    END $$;
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_guias_remision_cliente_id "
                    "ON guias_remision (cliente_id)"
                )
            )
        conn.commit()
    print("[OK] guias_remision.cliente_id listo.")


if __name__ == "__main__":
    run_migration()
