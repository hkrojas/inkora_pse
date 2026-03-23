"""
==========================================================
MIGRACIÓN: Fases 1-7 del Sistema de Facturación Electrónica
==========================================================
Ejecutar UNA SOLA VEZ con:
    cd backend
    python migrate_fases_1_7.py

Este script es IDEMPOTENTE: verifica si cada columna/tabla
existe antes de crearla, por lo que es seguro ejecutar
múltiples veces sin errores.
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
from database import engine

def column_exists(inspector, table: str, column: str) -> bool:
    """Verifica si una columna existe en una tabla."""
    try:
        columns = [c["name"] for c in inspector.get_columns(table)]
        return column in columns
    except Exception:
        return False

def table_exists(inspector, table: str) -> bool:
    """Verifica si una tabla existe."""
    return table in inspector.get_table_names()

def run_migration():
    inspector = inspect(engine)
    
    with engine.connect() as conn:
        print("=" * 60)
        print("MIGRACIÓN - Sistema de Facturación Electrónica")
        print("=" * 60)
        
        # ======================================================
        # FASE 1: Campos UBL 2.1 en tabla 'cotizaciones'
        # ======================================================
        print("\n📋 FASE 1: Campos UBL 2.1 en 'cotizaciones'...")
        
        alter_columns_cotizaciones = {
            "tipo_de_cambio": "NUMERIC(10, 4)",
            "sujeta_detraccion": "BOOLEAN DEFAULT FALSE",
            "porcentaje_detraccion": "NUMERIC(5, 2)",
            "monto_detraccion": "NUMERIC(12, 2)",
            "cuenta_banco_nacion": "VARCHAR",
            "anticipos_deducidos": "JSON",
            "total_anticipos": "NUMERIC(12, 2) DEFAULT 0.0",
            "nota_referencia_id": "INTEGER REFERENCES cotizaciones(id)",
        }
        
        for col_name, col_type in alter_columns_cotizaciones.items():
            if not column_exists(inspector, "cotizaciones", col_name):
                sql = f"ALTER TABLE cotizaciones ADD COLUMN {col_name} {col_type}"
                conn.execute(text(sql))
                print(f"  ✅ Añadida columna: cotizaciones.{col_name}")
            else:
                print(f"  ⏩ Ya existe: cotizaciones.{col_name}")
        
        # ======================================================
        # FASE 4: Campo ubigeo en 'clientes' (si no existe)
        # ======================================================
        print("\n📋 FASE 4: Campo 'ubigeo' en 'clientes'...")
        if not column_exists(inspector, "clientes", "ubigeo"):
            conn.execute(text("ALTER TABLE clientes ADD COLUMN ubigeo VARCHAR"))
            print("  ✅ Añadida columna: clientes.ubigeo")
        else:
            print("  ⏩ Ya existe: clientes.ubigeo")
        
        # ======================================================
        # FASE 7: Tablas de Guías de Remisión
        # ======================================================
        print("\n📋 FASE 7: Tablas de Guías de Remisión...")
        
        if not table_exists(inspector, "guias_remision"):
            conn.execute(text("""
                CREATE TABLE guias_remision (
                    id SERIAL PRIMARY KEY,
                    serie VARCHAR DEFAULT 'T001',
                    correlativo INTEGER,
                    fecha_emision TIMESTAMP DEFAULT NOW(),
                    fecha_traslado TIMESTAMP,
                    estado VARCHAR DEFAULT 'pendiente',
                    
                    cotizacion_id INTEGER REFERENCES cotizaciones(id),
                    usuario_id INTEGER REFERENCES users(id),
                    
                    motivo_traslado VARCHAR DEFAULT '01',
                    descripcion_motivo VARCHAR,
                    peso_bruto_total NUMERIC(12, 3),
                    unidad_medida_peso VARCHAR DEFAULT 'KGM',
                    numero_bultos INTEGER,
                    modalidad_traslado VARCHAR DEFAULT '01',
                    
                    transportista_ruc VARCHAR,
                    transportista_razon_social VARCHAR,
                    
                    conductor_tipo_doc VARCHAR DEFAULT '1',
                    conductor_nro_doc VARCHAR,
                    conductor_nombres VARCHAR,
                    conductor_apellidos VARCHAR,
                    conductor_licencia VARCHAR,
                    vehiculo_placa VARCHAR,
                    
                    partida_ubigeo VARCHAR,
                    partida_direccion VARCHAR,
                    llegada_ubigeo VARCHAR,
                    llegada_direccion VARCHAR,
                    
                    sunat_xml_url VARCHAR,
                    sunat_pdf_url VARCHAR,
                    sunat_cdr_url VARCHAR,
                    sunat_error TEXT
                )
            """))
            print("  ✅ Tabla 'guias_remision' creada")
        else:
            print("  ⏩ Tabla 'guias_remision' ya existe")
        
        if not table_exists(inspector, "guia_remision_items"):
            conn.execute(text("""
                CREATE TABLE guia_remision_items (
                    id SERIAL PRIMARY KEY,
                    guia_id INTEGER REFERENCES guias_remision(id) ON DELETE CASCADE,
                    
                    descripcion VARCHAR,
                    cantidad NUMERIC(12, 2),
                    unidad_medida VARCHAR DEFAULT 'NIU',
                    codigo_producto VARCHAR,
                    peso_item NUMERIC(12, 3)
                )
            """))
            print("  ✅ Tabla 'guia_remision_items' creada")
        else:
            print("  ⏩ Tabla 'guia_remision_items' ya existe")
        
        # ======================================================
        # CREAR ÍNDICES
        # ======================================================
        print("\n📋 Creando índices...")
        
        indices = [
            ("idx_guias_remision_usuario", "guias_remision", "usuario_id"),
            ("idx_guias_remision_estado", "guias_remision", "estado"),
            ("idx_guia_items_guia_id", "guia_remision_items", "guia_id"),
            ("idx_cotizaciones_nota_ref", "cotizaciones", "nota_referencia_id"),
        ]
        
        existing_indices = []
        for table_name in ["guias_remision", "guia_remision_items", "cotizaciones"]:
            if table_exists(inspector, table_name):
                for idx in inspector.get_indexes(table_name):
                    existing_indices.append(idx["name"])
        
        for idx_name, tbl, col in indices:
            if idx_name not in existing_indices:
                try:
                    conn.execute(text(f"CREATE INDEX {idx_name} ON {tbl} ({col})"))
                    print(f"  ✅ Índice '{idx_name}' creado")
                except Exception:
                    print(f"  ⏩ Índice '{idx_name}' ya existe (skip)")
            else:
                print(f"  ⏩ Índice '{idx_name}' ya existe")
        
        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 60)

if __name__ == "__main__":
    run_migration()
