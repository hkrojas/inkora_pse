"""migrate_gre_credentials.py — Agrega columnas sunat_gre_client_id y
sunat_gre_client_secret a la tabla tenants.

Estas columnas son requeridas para emitir Guías de Remisión Electrónicas
(Nueva GRE 2022) a través de ApisPeru.  El proveedor exige que la empresa
emisora tenga configuradas las credenciales OAuth2 generadas en el portal
SUNAT (client_id / client_secret) para poder transmitir el UBL al
servicio Nueva GRE de SUNAT.

Uso:
    cd backend
    python migrate_gre_credentials.py
"""
import traceback

from sqlalchemy import text

from database import engine
from models import Base


def run_migration():
    print("Iniciando migración GRE Credentials: columnas sunat_gre_client_id / sunat_gre_client_secret ...")
    try:
        Base.metadata.create_all(bind=engine)
        print("[OK] Base.metadata.create_all ejecutado.")

        with engine.begin() as conn:
            try:
                conn.execute(
                    text("ALTER TABLE tenants ADD COLUMN sunat_gre_client_id VARCHAR;")
                )
                print("[OK] Columna sunat_gre_client_id añadida.")
            except Exception:
                print("[!] sunat_gre_client_id ya existe o error DDL (ignorado).")

            try:
                conn.execute(
                    text("ALTER TABLE tenants ADD COLUMN sunat_gre_client_secret VARCHAR;")
                )
                print("[OK] Columna sunat_gre_client_secret añadida.")
            except Exception:
                print("[!] sunat_gre_client_secret ya existe o error DDL (ignorado).")

        print("\n[OK] MIGRACIÓN GRE CREDENTIALS COMPLETADA.")
    except Exception:
        print("[X] ERROR EN MIGRACIÓN GRE CREDENTIALS:")
        traceback.print_exc()


if __name__ == "__main__":
    run_migration()
