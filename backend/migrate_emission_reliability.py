"""
MIGRACION: Confiabilidad de Emision
==================================

Refuerza invariantes operativas para emision fiscal:
1. Unicidad tenant + serie + correlativo en cotizaciones.
2. Unicidad tenant + serie + correlativo en guias.
3. Una sola factura/boleta activa por cotizacion origen.

Ejecutar con:
    cd backend
    python migrate_emission_reliability.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

from database import engine


def _print_duplicate_rows(conn, sql: str, label: str) -> None:
    rows = conn.execute(text(sql)).fetchall()
    if not rows:
        return
    print(f"[ERROR] Se encontraron duplicados antes de crear {label}:")
    for row in rows[:10]:
        print(f"    {tuple(row)}")
    raise RuntimeError(f"No se puede crear {label} mientras existan duplicados.")


def run_migration():
    with engine.begin() as conn:
        _print_duplicate_rows(
            conn,
            """
            SELECT tenant_id, serie, correlativo, COUNT(*) AS total
            FROM cotizaciones
            WHERE serie IS NOT NULL AND correlativo IS NOT NULL
            GROUP BY tenant_id, serie, correlativo
            HAVING COUNT(*) > 1
            """,
            "uq_cotizaciones_tenant_serie_correlativo",
        )

        _print_duplicate_rows(
            conn,
            """
            SELECT tenant_id, serie, correlativo, COUNT(*) AS total
            FROM guias_remision
            WHERE serie IS NOT NULL AND correlativo IS NOT NULL
            GROUP BY tenant_id, serie, correlativo
            HAVING COUNT(*) > 1
            """,
            "uq_guias_remision_tenant_serie_correlativo",
        )

        _print_duplicate_rows(
            conn,
            """
            SELECT tenant_id, source_quote_id, COUNT(*) AS total
            FROM cotizaciones
            WHERE source_quote_id IS NOT NULL
              AND document_kind = 'fiscal_document'
              AND estado != 'anulada'
            GROUP BY tenant_id, source_quote_id
            HAVING COUNT(*) > 1
            """,
            "uq_cotizaciones_one_active_fiscal_per_quote",
        )

        print("[+] Creando indices de confiabilidad de emision...")
        conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_cotizaciones_tenant_serie_correlativo
                ON cotizaciones(tenant_id, serie, correlativo)
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_guias_remision_tenant_serie_correlativo
                ON guias_remision(tenant_id, serie, correlativo)
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_cotizaciones_one_active_fiscal_per_quote
                ON cotizaciones(tenant_id, source_quote_id)
                WHERE source_quote_id IS NOT NULL
                  AND document_kind = 'fiscal_document'
                  AND estado != 'anulada'
                """
            )
        )
        print("    OK: indices de confiabilidad creados/verificados.")


if __name__ == "__main__":
    run_migration()
