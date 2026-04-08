"""
migrate_phase9_beta.py — Fase 9: Beta Cerrada

Migraciones idempotentes para preparar la base de datos existente para
las funcionalidades de beta cerrada.

Tareas:
  1. Agregar columna `is_pilot` a la tabla `subscriptions` (si no existe).
     Los tenants existentes quedan con is_pilot=False (default).

Uso:
    cd backend
    python migrate_phase9_beta.py

Seguro de ejecutar múltiples veces (idempotente).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text

from database import engine


def column_exists(connection, table: str, column: str) -> bool:
    """Verifica si una columna existe en una tabla (compatible SQLite y PostgreSQL)."""
    result = connection.execute(
        f"SELECT column_name FROM information_schema.columns "
        f"WHERE table_name='{table}' AND column_name='{column}'"
    )
    return result.fetchone() is not None


def column_exists_sqlite(connection, table: str, column: str) -> bool:
    """Verifica si una columna existe en SQLite usando PRAGMA."""
    result = connection.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in result.fetchall()]
    return column in columns


def run_migration():
    print("=== Migración Fase 9: Beta Cerrada ===\n")

    with engine.connect() as conn:
        dialect = engine.dialect.name
        print(f"Dialecto de base de datos: {dialect}")

        # Detectar si is_pilot ya existe
        if dialect == "sqlite":
            exists = column_exists_sqlite(conn, "subscriptions", "is_pilot")
        else:
            # PostgreSQL y otros
            try:
                conn.execute(text("SELECT is_pilot FROM subscriptions LIMIT 1"))
                exists = True
            except Exception:
                conn.rollback()
                exists = False

        if exists:
            print("[OK] Columna `is_pilot` ya existe en `subscriptions`. Nada que hacer.")
        else:
            print("[MIGRANDO] Agregando columna `is_pilot` a `subscriptions`...")
            conn.execute(
                text("ALTER TABLE subscriptions ADD COLUMN is_pilot BOOLEAN NOT NULL DEFAULT FALSE")
            )
            conn.commit()
            print("[OK] Columna `is_pilot` agregada exitosamente.")

        print("\n=== Migración Fase 9 completada ===")


if __name__ == "__main__":
    run_migration()
