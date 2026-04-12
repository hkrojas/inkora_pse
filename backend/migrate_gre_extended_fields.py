"""migrate_gre_extended_fields.py - Agrega campos GRE adicionales para guias.

Campos alineados al swagger de ApisPeru para probar variantes del payload de
guia de remision mas cercanas al esquema oficial.

Uso:
    cd backend
    python migrate_gre_extended_fields.py
"""
import traceback

from sqlalchemy import text

from database import engine
from models import Base


def run_migration():
    print("Iniciando migracion GRE extendida para guias_remision ...")
    try:
        Base.metadata.create_all(bind=engine)
        print("[OK] Base.metadata.create_all ejecutado.")

        ddl_statements = [
            "ALTER TABLE guias_remision ADD COLUMN sustento_peso VARCHAR;",
            "ALTER TABLE guias_remision ADD COLUMN ind_transbordo BOOLEAN;",
            "ALTER TABLE guias_remision ADD COLUMN num_contenedor VARCHAR;",
            "ALTER TABLE guias_remision ADD COLUMN cod_puerto VARCHAR;",
            "ALTER TABLE guias_remision ADD COLUMN transportista_nro_mtc VARCHAR;",
            "ALTER TABLE guias_remision ADD COLUMN vehiculo_nro_circulacion VARCHAR;",
            "ALTER TABLE guias_remision ADD COLUMN vehiculo_cod_emisor VARCHAR;",
            "ALTER TABLE guias_remision ADD COLUMN vehiculo_nro_autorizacion VARCHAR;",
        ]

        with engine.begin() as conn:
            for ddl in ddl_statements:
                column_name = ddl.split("ADD COLUMN", 1)[1].strip().split(" ", 1)[0]
                try:
                    conn.execute(text(ddl))
                    print(f"[OK] Columna {column_name} anadida.")
                except Exception:
                    print(f"[!] {column_name} ya existe o error DDL (ignorado).")

        print("\n[OK] MIGRACION GRE EXTENDIDA COMPLETADA.")
    except Exception:
        print("[X] ERROR EN MIGRACION GRE EXTENDIDA:")
        traceback.print_exc()


if __name__ == "__main__":
    run_migration()
