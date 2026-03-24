import traceback
from sqlalchemy import text
from database import engine
from models import Base

def run_migration():
    print("Iniciando migración Fase 8: Analítica de Datos & Alertas Background...")
    try:
        # Crea la nueva tabla alertas_inventario
        Base.metadata.create_all(bind=engine)
        print("[OK] Base.metadata.create_all ejecutado (Materialización de alertas_inventario).")

        # Inserta columnda de threshold
        with engine.begin() as conn:
            try:
                conn.execute(text("ALTER TABLE insumos ADD COLUMN umbral_minimo NUMERIC(12, 2) DEFAULT 50.00;"))
                print("[OK] Columna umbral_minimo añadida a Insumos.")
            except Exception as e:
                print("[!] Columna umbral_minimo ya existe o error DDL.")
                
        print("\n[OK] MIGRACION FASE 8 COMPLETADA CON ÉXITO.")
    except Exception as e:
        print("[X] ERROR EN MIGRACIÓN FASE 8:")
        traceback.print_exc()

if __name__ == "__main__":
    run_migration()
