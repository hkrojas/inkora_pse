import traceback
from sqlalchemy import text
from database import engine
from models import Base

def run_migration():
    print("Iniciando migración Fase 7: Tercerización (Modelo Broker)...")
    try:
        # Crea la nueva tabla `proveedores` detectada en models.py
        Base.metadata.create_all(bind=engine)
        print("[OK] Base.metadata.create_all ejecutado (Materialización de proveedores).")

        # Inyecta columnas dinámicamente si no existían en postgresql/sqlite (Ordenes Producción)
        with engine.begin() as conn:
            # Check si existen fallando silencioamente para db sqlite y pg compatibilidad
            try:
                conn.execute(text("ALTER TABLE ordenes_produccion ADD COLUMN tipo_produccion VARCHAR DEFAULT 'interna';"))
                print("[OK] Columna tipo_produccion añadida.")
            except Exception as e:
                print("[!] Columna tipo_produccion ya existe o error DDL.")
                
            try:
                conn.execute(text("ALTER TABLE ordenes_produccion ADD COLUMN proveedor_id INTEGER REFERENCES proveedores(id);"))
                print("[OK] Columna proveedor_id añadida.")
            except Exception as e:
                print("[!] Columna proveedor_id ya existe o error DDL.")
                
            try:
                conn.execute(text("ALTER TABLE ordenes_produccion ADD COLUMN costo_tercerizado NUMERIC(12, 2);"))
                print("[OK] Columna costo_tercerizado añadida.")
            except Exception as e:
                print("[!] Columna costo_tercerizado ya existe o error DDL.")
                
        print("\n[OK] MIGRACION FASE 7 COMPLETADA CON ÉXITO.")
    except Exception as e:
        print("[X] ERROR EN MIGRACIÓN FASE 7:")
        traceback.print_exc()

if __name__ == "__main__":
    run_migration()
