"""
Migracion idempotente: moneda para productos.

Agrega `productos.moneda` para permitir catalogar precios en PEN o USD.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text

from database import engine


def run_migration():
    print("=== Migracion productos.moneda ===")
    with engine.connect() as conn:
        dialect = engine.dialect.name
        if dialect == "sqlite":
            columns = [row[1] for row in conn.execute(text("PRAGMA table_info(productos)")).fetchall()]
            exists = "moneda" in columns
        else:
            try:
                conn.execute(text("SELECT moneda FROM productos LIMIT 1"))
                exists = True
            except Exception:
                conn.rollback()
                exists = False

        if exists:
            print("[OK] productos.moneda ya existe.")
            return

        print("[MIGRANDO] Agregando productos.moneda...")
        conn.execute(text("ALTER TABLE productos ADD COLUMN moneda VARCHAR DEFAULT 'PEN'"))
        conn.execute(text("UPDATE productos SET moneda = 'PEN' WHERE moneda IS NULL OR moneda = ''"))
        conn.commit()
        print("[OK] productos.moneda agregada.")


if __name__ == "__main__":
    run_migration()
