"""migrate_concurrency_phaseE.py — Fase E del plan de concurrencia.

Crea un partial unique index que previene que una cotización tenga más de
un fiscal_document activo. Es una red de seguridad a nivel de BD: si toda
la lógica de aplicación funciona, nunca se dispara. Pero previene corrupción
si algún edge case escapa.

Uso:
    python migrate_concurrency_phaseE.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from sqlalchemy import create_engine, text
from logging_utils import get_logger

logger = get_logger(__name__)

INDEX_NAME = "uq_one_active_fiscal_per_quote"
INDEX_SQL = f"""
-- Máximo un fiscal_document activo por cotización.
-- Si ya existe un fiscal document no-anulado para una source_quote_id,
-- no se puede insertar otro.
CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME}
ON cotizaciones (tenant_id, source_quote_id)
WHERE document_kind = 'fiscal_document' AND estado != 'anulada';
"""

DROP_SQL = f"DROP INDEX IF EXISTS {INDEX_NAME};"


def run_migration():
    if settings.DATABASE_URL.startswith("sqlite"):
        logger.warning("SQLite no soporta partial indexes. Omitiendo migración Fase E.")
        print("[SKIP] SQLite no soporta partial indexes. Fase E omitida.")
        return

    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        # Verificar si ya existe
        exists = conn.execute(
            text("""
                SELECT 1 FROM pg_indexes
                WHERE indexname = :idx_name
            """),
            {"idx_name": INDEX_NAME},
        ).first()

        if exists:
            print(f"[OK] Index '{INDEX_NAME}' ya existe. Nada que hacer.")
            return

        print(f"[MIGRATING] Creando partial unique index '{INDEX_NAME}'...")
        conn.execute(text(INDEX_SQL))
        conn.commit()
        print(f"[OK] Index '{INDEX_NAME}' creado exitosamente.")

        # Verificar
        exists_after = conn.execute(
            text("""
                SELECT 1 FROM pg_indexes
                WHERE indexname = :idx_name
            """),
            {"idx_name": INDEX_NAME},
        ).first()
        if exists_after:
            print(f"[VERIFIED] Index confirmado en la base de datos.")
        else:
            print("[WARN] Index no encontrado después de crearlo. Verificar manualmente.")


def rollback_migration():
    if settings.DATABASE_URL.startswith("sqlite"):
        print("[SKIP] SQLite no soporta partial indexes.")
        return

    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text(DROP_SQL))
        conn.commit()
        print(f"[OK] Index '{INDEX_NAME}' eliminado.")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "run"
    if action == "rollback":
        rollback_migration()
    else:
        run_migration()
