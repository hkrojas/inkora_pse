"""Migracion idempotente: codigo_producto en cotizacion_items.

Permite conservar el SKU fiscal usado en el momento de cotizar/facturar.
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
    print("=== Migracion cotizacion_items.codigo_producto ===")
    with engine.connect() as conn:
        if not _column_exists(conn, "cotizacion_items", "codigo_producto"):
            print("[MIGRANDO] Agregando cotizacion_items.codigo_producto...")
            conn.execute(
                text("ALTER TABLE cotizacion_items ADD COLUMN codigo_producto VARCHAR")
            )
        else:
            print("[OK] cotizacion_items.codigo_producto ya existe.")

        print("[MIGRANDO] Backfill desde productos.codigo_interno...")
        if engine.dialect.name == "sqlite":
            conn.execute(
                text(
                    """
                    UPDATE cotizacion_items
                    SET codigo_producto = (
                        SELECT p.codigo_interno
                        FROM productos p
                        WHERE p.id = cotizacion_items.producto_id
                    )
                    WHERE codigo_producto IS NULL
                      AND producto_id IS NOT NULL
                    """
                )
            )
        else:
            conn.execute(
                text(
                    """
                    UPDATE cotizacion_items ci
                    SET codigo_producto = p.codigo_interno
                    FROM productos p
                    WHERE ci.producto_id = p.id
                      AND ci.codigo_producto IS NULL
                      AND p.codigo_interno IS NOT NULL
                      AND p.codigo_interno <> ''
                    """
                )
            )
        conn.commit()
    print("[OK] cotizacion_items.codigo_producto listo.")


if __name__ == "__main__":
    run_migration()
