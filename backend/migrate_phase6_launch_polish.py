"""
Migración Fase 6 — Launch Workflow Polish
=========================================
Agrega columnas nuevas a las tablas existentes:

  clientes:
    - whatsapp          VARCHAR  nullable
    - contacto          VARCHAR  nullable
    - condicion_pago    VARCHAR  nullable  (contado | credito_7 | credito_15 | credito_30 | credito_60)
    - direccion_entrega VARCHAR  nullable
    - observaciones     TEXT     nullable

  cotizaciones:
    - observaciones     TEXT     nullable
    - condicion_pago    VARCHAR  nullable

Ejecutar UNA sola vez contra la base de datos de producción/desarrollo.
Es idempotente: usa "IF NOT EXISTS" o captura el error de columna ya existente.
"""

import sys
import os

# Ajusta el path para importar desde el directorio backend
sys.path.insert(0, os.path.dirname(__file__))

from database import engine
from sqlalchemy import text


MIGRATIONS = [
    # ── clientes ─────────────────────────────────────────────────────────────
    ("clientes", "whatsapp",          "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS whatsapp VARCHAR"),
    ("clientes", "contacto",          "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS contacto VARCHAR"),
    ("clientes", "condicion_pago",    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS condicion_pago VARCHAR"),
    ("clientes", "direccion_entrega", "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS direccion_entrega VARCHAR"),
    ("clientes", "observaciones",     "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS observaciones TEXT"),
    # ── cotizaciones ─────────────────────────────────────────────────────────
    ("cotizaciones", "observaciones",  "ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS observaciones TEXT"),
    ("cotizaciones", "condicion_pago", "ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS condicion_pago VARCHAR"),
]


def run():
    errors = []
    with engine.connect() as conn:
        for tabla, columna, sql in MIGRATIONS:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"  ✓  {tabla}.{columna}")
            except Exception as exc:
                conn.rollback()
                msg = f"  ✗  {tabla}.{columna}: {exc}"
                print(msg)
                errors.append(msg)

    if errors:
        print(f"\n⚠️  {len(errors)} columna(s) con error (puede que ya existan con tipo diferente).")
    else:
        print("\n✅ Migración Fase 6 completada sin errores.")


if __name__ == "__main__":
    print("Ejecutando migración Fase 6 — Launch Workflow Polish...\n")
    run()
