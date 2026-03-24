"""
==========================================================
MIGRACIÓN: Motor de Producción (Fase 4 SaaS)
==========================================================
Agrega las tablas Insumos, RecetasBOM, OrdenesProduccion 
y Detalles automáticos para el cálculo de mermas.
==========================================================
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix encoding for Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith('cp'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from sqlalchemy import inspect
from database import engine, Base
import models  # Important to bind the metadata

def run_migration():
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    with engine.begin() as conn:
        print("=" * 60)
        print("MIGRACION FASE 4: MOTOR DE PRODUCCIÓN (BOM / MRP)")
        print("=" * 60)

        # Usar la vía rápida de SQLAlchemy para materializar las tablas
        # Base.metadata.create_all generará solo las tablas que NO existen.
        print("\n[+] Detectando y Creando nuevas tablas: insumos, recetas_bom, ordenes_produccion, ordenes_produccion_detalle...")
        Base.metadata.create_all(bind=engine)
        
        print("\n  [=] ¡Estructuras sincronizadas a nivel de motor DB!")

        print("\n" + "=" * 60)
        print("[OK] MIGRACION FASE 4 COMPLETADA")
        print("=" * 60)

if __name__ == "__main__":
    run_migration()
