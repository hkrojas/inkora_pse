"""
migrate_auth_passwords.py — Seguridad de contraseñas

Agrega dos columnas a la tabla `users` para soportar el flujo de
contraseña temporal y cambio forzado en primer login.

Columnas:
  - must_change_password  BOOLEAN NOT NULL DEFAULT FALSE
  - password_changed_at   TIMESTAMP NULL

Usuarios existentes quedan con must_change_password=False (acceso normal).

Uso:
    cd backend
    python migrate_auth_passwords.py

Seguro de ejecutar múltiples veces (idempotente).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from database import engine


def _col_exists_pg(conn, table: str, column: str) -> bool:
    try:
        conn.execute(text(f"SELECT {column} FROM {table} LIMIT 1"))
        return True
    except Exception:
        conn.rollback()
        return False


def _col_exists_sqlite(conn, table: str, column: str) -> bool:
    result = conn.execute(text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in result.fetchall())


def run_migration():
    print("=== Migración: Seguridad de contraseñas ===\n")

    with engine.connect() as conn:
        dialect = engine.dialect.name
        print(f"Dialecto: {dialect}\n")

        col_exists = _col_exists_sqlite if dialect == "sqlite" else _col_exists_pg

        # --- must_change_password ---
        if col_exists(conn, "users", "must_change_password"):
            print("[OK] must_change_password ya existe.")
        else:
            print("[MIGRANDO] Agregando must_change_password a users...")
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            conn.commit()
            print("[OK] must_change_password agregada.")

        # --- password_changed_at ---
        if col_exists(conn, "users", "password_changed_at"):
            print("[OK] password_changed_at ya existe.")
        else:
            print("[MIGRANDO] Agregando password_changed_at a users...")
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN password_changed_at TIMESTAMP NULL"
            ))
            conn.commit()
            print("[OK] password_changed_at agregada.")

        print("\n=== Migración completada ===")


if __name__ == "__main__":
    run_migration()
