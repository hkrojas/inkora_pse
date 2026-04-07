"""
==========================================================
MIGRACION: Fase 4 - Trazabilidad documental transicional
==========================================================
Agrega identidad documental explicita y referencias
operativas entre cotizacion, documento fiscal, guias y pagos.

Ejecutar con:
    cd backend
    python migrate_document_flow_phase4.py
==========================================================
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    import io

    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer,
        encoding="utf-8",
        errors="replace",
    )

from sqlalchemy import inspect, text

from database import engine


def column_exists(inspector, table: str, column: str) -> bool:
    try:
        columns = [c["name"] for c in inspector.get_columns(table)]
        return column in columns
    except Exception:
        return False


def index_exists(inspector, table: str, index_name: str) -> bool:
    try:
        return index_name in [idx["name"] for idx in inspector.get_indexes(table)]
    except Exception:
        return False


def add_column_if_missing(conn, inspector, table: str, column: str, ddl: str) -> None:
    if column_exists(inspector, table, column):
        print(f"  [=] {table}.{column} ya existe")
        return
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
    print(f"  [+] {table}.{column} agregado")


def create_index_if_missing(conn, inspector, table: str, index_name: str, column: str) -> None:
    if index_exists(inspector, table, index_name):
        print(f"  [=] Indice {index_name} ya existe")
        return
    conn.execute(text(f"CREATE INDEX {index_name} ON {table} ({column})"))
    print(f"  [+] Indice {index_name} creado")


def run_migration():
    inspector = inspect(engine)

    with engine.connect() as conn:
        print("=" * 60)
        print("MIGRACION FASE 4 - TRAZABILIDAD DOCUMENTAL")
        print("=" * 60)

        print("\n[PASO 1] Campos transicionales en cotizaciones...")
        add_column_if_missing(
            conn,
            inspector,
            "cotizaciones",
            "document_kind",
            "VARCHAR DEFAULT 'quotation' NOT NULL",
        )
        add_column_if_missing(
            conn,
            inspector,
            "cotizaciones",
            "internal_order_number",
            "VARCHAR",
        )
        add_column_if_missing(
            conn,
            inspector,
            "cotizaciones",
            "source_quote_id",
            "INTEGER REFERENCES cotizaciones(id)",
        )

        print("\n[PASO 2] Backfill de identidad documental legacy...")
        conn.execute(
            text(
                """
                UPDATE cotizaciones
                SET document_kind = CASE
                    WHEN nota_referencia_id IS NOT NULL AND tipo_comprobante = '07' THEN 'credit_note'
                    WHEN nota_referencia_id IS NOT NULL AND tipo_comprobante = '08' THEN 'debit_note'
                    WHEN source_quote_id IS NOT NULL THEN 'fiscal_document'
                    WHEN tipo_comprobante IN ('01', '03') AND serie <> 'COT' THEN 'fiscal_document'
                    ELSE 'quotation'
                END
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE cotizaciones
                SET internal_order_number = CONCAT(
                    'ORD-',
                    LPAD(CAST(tenant_id AS VARCHAR), 4, '0'),
                    '-',
                    LPAD(CAST(COALESCE(correlativo, id) AS VARCHAR), 6, '0')
                )
                WHERE internal_order_number IS NULL
                """
            )
        )
        print("  [+] Backfill de document_kind e internal_order_number completado")

        print("\n[PASO 3] Campos de trazabilidad en guias_remision...")
        add_column_if_missing(
            conn,
            inspector,
            "guias_remision",
            "source_quote_id",
            "INTEGER REFERENCES cotizaciones(id)",
        )
        add_column_if_missing(
            conn,
            inspector,
            "guias_remision",
            "fiscal_document_id",
            "INTEGER REFERENCES cotizaciones(id)",
        )
        add_column_if_missing(
            conn,
            inspector,
            "guias_remision",
            "internal_order_number",
            "VARCHAR",
        )

        print("\n[PASO 4] Campos de trazabilidad en pagos...")
        add_column_if_missing(
            conn,
            inspector,
            "pagos",
            "source_quote_id",
            "INTEGER REFERENCES cotizaciones(id)",
        )
        add_column_if_missing(
            conn,
            inspector,
            "pagos",
            "fiscal_document_id",
            "INTEGER REFERENCES cotizaciones(id)",
        )
        add_column_if_missing(
            conn,
            inspector,
            "pagos",
            "internal_order_number",
            "VARCHAR",
        )

        print("\n[PASO 5] Indices...")
        create_index_if_missing(
            conn,
            inspector,
            "cotizaciones",
            "idx_cotizaciones_document_kind",
            "document_kind",
        )
        create_index_if_missing(
            conn,
            inspector,
            "cotizaciones",
            "idx_cotizaciones_source_quote_id",
            "source_quote_id",
        )
        create_index_if_missing(
            conn,
            inspector,
            "cotizaciones",
            "idx_cotizaciones_internal_order_number",
            "internal_order_number",
        )
        create_index_if_missing(
            conn,
            inspector,
            "guias_remision",
            "idx_guias_internal_order_number",
            "internal_order_number",
        )
        create_index_if_missing(
            conn,
            inspector,
            "pagos",
            "idx_pagos_internal_order_number",
            "internal_order_number",
        )

        conn.commit()

        print("\n" + "=" * 60)
        print("[OK] MIGRACION FASE 4 COMPLETADA")
        print("=" * 60)


if __name__ == "__main__":
    run_migration()
