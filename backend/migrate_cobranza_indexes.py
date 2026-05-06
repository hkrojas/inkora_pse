"""
Migracion idempotente: indices para cobranza.

Optimiza:
- listado de documentos con saldo pendiente por tenant y vencimiento
- resumen mensual de pagos por tenant y fecha de pago
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text

from database import engine


def run_migration():
    print("=== Migracion indices cobranza ===")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_cotizaciones_cobranza_active
            ON cotizaciones (tenant_id, fecha_vencimiento, id)
            WHERE document_kind = 'quotation'
              AND estado <> 'anulada'
              AND saldo_pendiente > 0
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pagos_cobranza_mes
            ON pagos (tenant_id, fecha_pago, cotizacion_id)
        """))
        conn.commit()
    print("[OK] indices de cobranza listos.")


if __name__ == "__main__":
    run_migration()
