"""
migrate_fiscal_pdf_artifacts.py
================================

Agrega columnas para persistir artefactos fiscales oficiales devueltos por
ApisPeru y usarlos en el PDF propio:

  - sunat_xml_content
  - sunat_hash
  - sunat_qr_payload
  - sunat_qr_svg
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text

from database import engine


MIGRATIONS = [
    (
        "cotizaciones",
        "sunat_xml_content",
        "ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS sunat_xml_content TEXT",
    ),
    (
        "cotizaciones",
        "sunat_hash",
        "ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS sunat_hash VARCHAR",
    ),
    (
        "cotizaciones",
        "sunat_qr_payload",
        "ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS sunat_qr_payload JSON",
    ),
    (
        "cotizaciones",
        "sunat_qr_svg",
        "ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS sunat_qr_svg TEXT",
    ),
]


def run():
    errors = []
    with engine.connect() as conn:
        for tabla, columna, sql in MIGRATIONS:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"  [OK]  {tabla}.{columna}")
            except Exception as exc:
                conn.rollback()
                msg = f"  [ERR] {tabla}.{columna}: {exc}"
                print(msg)
                errors.append(msg)

    if errors:
        print(f"\n[WARN] {len(errors)} columna(s) con error.")
    else:
        print("\n[OK] Migracion de artefactos fiscales completada sin errores.")


if __name__ == "__main__":
    print("Ejecutando migracion de artefactos fiscales...\n")
    run()
