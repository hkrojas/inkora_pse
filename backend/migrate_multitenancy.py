"""
==========================================================
MIGRACIÓN: Multitenancia Core (Fase 1 SaaS)
==========================================================
Ejecutar UNA SOLA VEZ con:
    cd backend
    python migrate_multitenancy.py

Acciones:
1. Crea la tabla 'tenants'.
2. Crea un Tenant inicial basado en los datos del primer User.
3. Añade 'tenant_id' en: users, clientes, productos, cotizaciones, guias_remision.
4. Asigna el tenant_id del tenant inicial a todos los registros existentes.
5. Crea índices para filtrado por tenant.

Este script es IDEMPOTENTE.
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
        print("MIGRACION MULTITENANCIA - PrintFlow SaaS B2B")
        print("=" * 60)

        # ======================================================
        # PASO 1: Crear tabla 'tenants'
        # ======================================================
        print("\n[PASO 1] Tabla 'tenants'...")

        if not table_exists(inspector, "tenants"):
            conn.execute(text("""
                CREATE TABLE tenants (
                    id SERIAL PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT NOW(),
                    is_active BOOLEAN DEFAULT TRUE,

                    business_name VARCHAR NOT NULL,
                    business_ruc VARCHAR NOT NULL UNIQUE,
                    business_address VARCHAR,
                    business_phone VARCHAR,
                    logo_filename VARCHAR,

                    primary_color VARCHAR DEFAULT '#2563EB',
                    pdf_note_1 TEXT,
                    pdf_note_1_color VARCHAR DEFAULT '#FF0000',
                    pdf_note_2 TEXT,

                    bank_accounts JSON,

                    apisperu_token VARCHAR,
                    apisperu_url VARCHAR
                )
            """))
            print("  [+] Tabla 'tenants' creada")
        else:
            print("  [=] Tabla 'tenants' ya existe")

        conn.commit()

        # ======================================================
        # PASO 2: Crear Tenant inicial desde datos del primer User
        # ======================================================
        print("\n[PASO 2] Tenant inicial...")

        tenant_count = conn.execute(text("SELECT COUNT(*) FROM tenants")).scalar()
        if tenant_count == 0:
            # Buscar el primer user con datos de empresa
            first_user = conn.execute(text("""
                SELECT id, business_name, business_ruc, business_address,
                       business_phone, logo_filename, primary_color,
                       pdf_note_1, pdf_note_1_color, pdf_note_2,
                       bank_accounts, apisperu_token, apisperu_url
                FROM users
                WHERE business_ruc IS NOT NULL
                ORDER BY id ASC
                LIMIT 1
            """)).mappings().first()

            if first_user:
                conn.execute(text("""
                    INSERT INTO tenants (
                        business_name, business_ruc, business_address,
                        business_phone, logo_filename, primary_color,
                        pdf_note_1, pdf_note_1_color, pdf_note_2,
                        bank_accounts, apisperu_token, apisperu_url
                    ) VALUES (
                        :business_name, :business_ruc, :business_address,
                        :business_phone, :logo_filename, :primary_color,
                        :pdf_note_1, :pdf_note_1_color, :pdf_note_2,
                        CAST(:bank_accounts AS JSON), :apisperu_token, :apisperu_url
                    )
                """), {
                    "business_name": first_user["business_name"] or "Empresa Default",
                    "business_ruc": first_user["business_ruc"],
                    "business_address": first_user["business_address"],
                    "business_phone": first_user["business_phone"],
                    "logo_filename": first_user["logo_filename"],
                    "primary_color": first_user["primary_color"] or "#2563EB",
                    "pdf_note_1": first_user["pdf_note_1"],
                    "pdf_note_1_color": first_user["pdf_note_1_color"] or "#FF0000",
                    "pdf_note_2": first_user["pdf_note_2"],
                    "bank_accounts": str(first_user["bank_accounts"]) if first_user["bank_accounts"] else None,
                    "apisperu_token": first_user["apisperu_token"],
                    "apisperu_url": first_user["apisperu_url"]
                })
                print("  [+] Tenant inicial creado desde datos del User #" + str(first_user["id"]))
            else:
                conn.execute(text("""
                    INSERT INTO tenants (business_name, business_ruc)
                    VALUES ('Empresa Default', '00000000000')
                """))
                print("  [+] Tenant default creado (sin datos de User)")
        else:
            print(f"  [=] Ya existen {tenant_count} tenant(s)")

        conn.commit()

        # Obtener el ID del primer tenant
        tenant_id = conn.execute(text("SELECT id FROM tenants ORDER BY id ASC LIMIT 1")).scalar()
        print(f"  [i] Tenant principal ID: {tenant_id}")

        # ======================================================
        # PASO 3: Añadir tenant_id en tablas operativas
        # ======================================================
        print("\n[PASO 3] Columnas tenant_id...")

        tables_to_update = ["users", "clientes", "productos", "cotizaciones", "guias_remision"]

        for table in tables_to_update:
            if not table_exists(inspector, table):
                print(f"  [!] Tabla '{table}' no existe, saltando")
                continue

            if not column_exists(inspector, table, "tenant_id"):
                # Añadir como nullable primero
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN tenant_id INTEGER"))
                print(f"  [+] Columna tenant_id agregada a '{table}'")

                # Asignar el tenant inicial a registros existentes
                conn.execute(text(f"UPDATE {table} SET tenant_id = :tid"), {"tid": tenant_id})
                print(f"  [+] Registros de '{table}' asignados al Tenant #{tenant_id}")

                # Ahora hacer NOT NULL y FK
                conn.execute(text(f"ALTER TABLE {table} ALTER COLUMN tenant_id SET NOT NULL"))
                conn.execute(text(
                    f"ALTER TABLE {table} ADD CONSTRAINT fk_{table}_tenant "
                    f"FOREIGN KEY (tenant_id) REFERENCES tenants(id)"
                ))
                print(f"  [+] FK y NOT NULL aplicados en '{table}.tenant_id'")
            else:
                print(f"  [=] '{table}.tenant_id' ya existe")

        conn.commit()

        # ======================================================
        # PASO 4: Índices de multitenancia
        # ======================================================
        print("\n[PASO 4] Indices de multitenancia...")

        indices = [
            ("idx_users_tenant", "users", "tenant_id"),
            ("idx_clientes_tenant", "clientes", "tenant_id"),
            ("idx_productos_tenant", "productos", "tenant_id"),
            ("idx_cotizaciones_tenant", "cotizaciones", "tenant_id"),
            ("idx_guias_remision_tenant", "guias_remision", "tenant_id"),
            ("idx_tenants_ruc", "tenants", "business_ruc"),
        ]

        for idx_name, tbl, col in indices:
            if not table_exists(inspector, tbl):
                continue
            try:
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {tbl} ({col})"))
                print(f"  [+] Indice '{idx_name}' OK")
            except Exception:
                print(f"  [=] Indice '{idx_name}' ya existe")

        conn.commit()

        print("\n" + "=" * 60)
        print("[OK] MIGRACION MULTITENANCIA COMPLETADA")
        print("=" * 60)


if __name__ == "__main__":
    run_migration()
