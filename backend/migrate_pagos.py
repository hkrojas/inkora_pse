"""
==========================================================
MIGRACIÓN: Motor Financiero (Fase 3 SaaS)
==========================================================
Agrega la tabla `pagos` y las columnas calculadas
`monto_pagado` y `saldo_pendiente` a `cotizaciones`.
==========================================================
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix encoding for Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith('cp'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from sqlalchemy import text, inspect
import psycopg2
from database import engine

def column_exists(inspector, table, column):
    try:
        return column in [c["name"] for c in inspector.get_columns(table)]
    except Exception:
        return False

def table_exists(inspector, table):
    return table in inspector.get_table_names()

def run_migration():
    inspector = inspect(engine)

    with engine.connect() as conn:
        print("=" * 60)
        print("MIGRACION FASE 3: MOTOR FINANCIERO (Pagos y Adelantos)")
        print("=" * 60)

        # 1. Crear tabla Pagos
        print("\n[PASO 1] Crear tabla 'pagos'...")
        if not table_exists(inspector, "pagos"):
            conn.execute(text("""
                CREATE TABLE pagos (
                    id SERIAL PRIMARY KEY,
                    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
                    cotizacion_id INTEGER NOT NULL REFERENCES cotizaciones(id),
                    monto_pagado NUMERIC(12, 2) NOT NULL,
                    metodo_pago VARCHAR NOT NULL,
                    fecha_pago TIMESTAMP DEFAULT NOW(),
                    referencia_operacion VARCHAR,
                    tipo VARCHAR DEFAULT 'adelanto'
                )
            """))
            print("  [+] Tabla 'pagos' creada")
            
            # Crear indices para pagos
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pagos_tenant ON pagos (tenant_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pagos_cotizacion ON pagos (cotizacion_id)"))
            print("  [+] Índices para 'pagos' creados")
        else:
            print("  [=] Tabla 'pagos' ya existe")

        # 2. Agregar columnas a Cotizaciones
        print("\n[PASO 2] Columnas en 'cotizaciones'...")
        if not column_exists(inspector, "cotizaciones", "monto_pagado"):
            conn.execute(text("""
                ALTER TABLE cotizaciones 
                ADD COLUMN monto_pagado NUMERIC(12, 2) DEFAULT 0.0,
                ADD COLUMN saldo_pendiente NUMERIC(12, 2) DEFAULT 0.0
            """))
            print("  [+] Columnas 'monto_pagado' y 'saldo_pendiente' agregadas")
            
            # Inicializar los valores (backfill)
            conn.execute(text("""
                UPDATE cotizaciones 
                SET monto_pagado = 0.0,
                    saldo_pendiente = total_venta
            """))
            print("  [+] Registros existentes inicializados (saldo = total_venta)")
        else:
            print("  [=] Columnas financieras en 'cotizaciones' ya existen")

        conn.commit()

        print("\n" + "=" * 60)
        print("[OK] MIGRACION FASE 3 COMPLETADA")
        print("=" * 60)

if __name__ == "__main__":
    run_migration()
