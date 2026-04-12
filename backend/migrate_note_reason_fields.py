"""migrate_note_reason_fields.py - Agrega columnas para persistir el motivo de notas.

Estas columnas permiten reconstruir correctamente el payload requerido por
ApisPeru para descargar PDF/XML de notas de credito y debito despues de la
emision inicial.

Uso:
    cd backend
    python migrate_note_reason_fields.py
"""
import traceback

from sqlalchemy import text

from database import engine
from models import Base


def run_migration():
    print(
        "Iniciando migracion de motivos de notas: "
        "cotizaciones.nota_motivo_codigo / cotizaciones.nota_motivo_descripcion ..."
    )
    try:
        Base.metadata.create_all(bind=engine)
        print("[OK] Base.metadata.create_all ejecutado.")

        with engine.begin() as conn:
            try:
                conn.execute(
                    text("ALTER TABLE cotizaciones ADD COLUMN nota_motivo_codigo VARCHAR;")
                )
                print("[OK] Columna nota_motivo_codigo anadida.")
            except Exception:
                print("[!] nota_motivo_codigo ya existe o error DDL (ignorado).")

            try:
                conn.execute(
                    text("ALTER TABLE cotizaciones ADD COLUMN nota_motivo_descripcion TEXT;")
                )
                print("[OK] Columna nota_motivo_descripcion anadida.")
            except Exception:
                print("[!] nota_motivo_descripcion ya existe o error DDL (ignorado).")

        print("\n[OK] MIGRACION DE MOTIVOS DE NOTAS COMPLETADA.")
    except Exception:
        print("[X] ERROR EN MIGRACION DE MOTIVOS DE NOTAS:")
        traceback.print_exc()


if __name__ == "__main__":
    run_migration()
