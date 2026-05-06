"""Verificacion y saneamiento seguro pre-beta.

Este script no crea columnas ni reemplaza las migraciones launch. Verifica que
el esquema ya exista, aplica solo backfills no destructivos bajo --apply y falla
si encuentra datos ambiguos que requieren revision manual.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from typing import Iterable

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


CRITICAL_COLUMNS = {
    "subscriptions": {
        "tenant_id",
        "status",
        "plan_code",
        "documents_used",
        "beta_feature_flags",
    },
    "cotizaciones": {
        "tenant_id",
        "document_kind",
        "source_quote_id",
        "nota_referencia_id",
        "total_gravada",
        "total_exonerada",
        "total_inafecta",
        "total_igv",
        "total_venta",
        "estado",
        "tipo_comprobante",
        "fecha_vencimiento",
    },
    "pagos": {
        "tenant_id",
        "cotizacion_id",
        "source_quote_id",
        "fiscal_document_id",
        "tipo",
        "monto_pagado",
        "fecha_pago",
    },
    "tenants": {"id", "is_active"},
}

ALLOWED_SUBSCRIPTION_STATUSES = {
    "active",
    "trial",
    "grace",
    "suspended",
    "payment_required",
    "cancelled",
    "expired",
}
VALID_DOCUMENT_KINDS = {"quotation", "fiscal_document", "credit_note", "debit_note"}
TOTAL_COLUMNS = (
    "total_gravada",
    "total_exonerada",
    "total_inafecta",
    "total_igv",
    "total_venta",
)


@dataclass
class IntegrityReport:
    checks_ok: list[str] = field(default_factory=list)
    planned_actions: list[str] = field(default_factory=list)
    applied_actions: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        return 1 if self.blockers else 0


def _rows(conn, sql: str, params: dict | None = None):
    return conn.execute(text(sql), params or {}).mappings().all()


def _scalar(conn, sql: str, params: dict | None = None):
    return conn.execute(text(sql), params or {}).scalar()


def _column_names(db_engine: Engine, table: str) -> set[str]:
    inspector = inspect(db_engine)
    table_names = set(inspector.get_table_names())
    if table not in table_names:
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _validate_critical_columns(db_engine: Engine, report: IntegrityReport) -> bool:
    all_ok = True
    for table, required_columns in CRITICAL_COLUMNS.items():
        existing_columns = _column_names(db_engine, table)
        for column in sorted(required_columns):
            if column not in existing_columns:
                report.blockers.append(
                    f"Falta columna critica {table}.{column}. "
                    "Ejecuta launch_migrations y las revisiones Alembic pendientes antes de migrate_beta_integrity."
                )
                all_ok = False
        if existing_columns and required_columns.issubset(existing_columns):
            report.checks_ok.append(f"Columnas criticas OK en {table}.")
    return all_ok


def prefiscal_unapplied_index_sql(dialect_name: str) -> str:
    if dialect_name == "postgresql":
        return (
            "CREATE INDEX IF NOT EXISTS idx_beta_pagos_prefiscal_unapplied "
            "ON pagos (tenant_id, source_quote_id, tipo) "
            "WHERE fiscal_document_id IS NULL"
        )
    return (
        "CREATE INDEX IF NOT EXISTS idx_beta_pagos_prefiscal_unapplied "
        "ON pagos (tenant_id, source_quote_id, tipo, fiscal_document_id)"
    )


def _index_definitions(dialect_name: str) -> tuple[tuple[str, str, str], ...]:
    return (
        (
            "idx_beta_cot_fiscal_lookup",
            "cotizaciones",
            "CREATE INDEX IF NOT EXISTS idx_beta_cot_fiscal_lookup "
            "ON cotizaciones (tenant_id, document_kind, estado, tipo_comprobante)",
        ),
        (
            "idx_beta_cot_notes_balance",
            "cotizaciones",
            "CREATE INDEX IF NOT EXISTS idx_beta_cot_notes_balance "
            "ON cotizaciones (tenant_id, nota_referencia_id, document_kind, estado)",
        ),
        (
            "idx_beta_cot_source_lookup",
            "cotizaciones",
            "CREATE INDEX IF NOT EXISTS idx_beta_cot_source_lookup "
            "ON cotizaciones (tenant_id, source_quote_id, document_kind, estado, id)",
        ),
        (
            "idx_beta_pagos_fiscal",
            "pagos",
            "CREATE INDEX IF NOT EXISTS idx_beta_pagos_fiscal "
            "ON pagos (tenant_id, fiscal_document_id)",
        ),
        (
            "idx_beta_cot_vencimiento_fiscal",
            "cotizaciones",
            "CREATE INDEX IF NOT EXISTS idx_beta_cot_vencimiento_fiscal "
            "ON cotizaciones (tenant_id, document_kind, estado, fecha_vencimiento)",
        ),
        (
            "idx_beta_pagos_prefiscal_unapplied",
            "pagos",
            prefiscal_unapplied_index_sql(dialect_name),
        ),
    )


def _index_exists(conn, dialect_name: str, table: str, index_name: str) -> bool:
    if dialect_name == "sqlite":
        return (
            _scalar(
                conn,
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'index'
                  AND tbl_name = :table_name
                  AND name = :index_name
                """,
                {"table_name": table, "index_name": index_name},
            )
            is not None
        )
    if dialect_name == "postgresql":
        return (
            _scalar(
                conn,
                """
                SELECT 1
                FROM pg_indexes
                WHERE tablename = :table_name
                  AND indexname = :index_name
                """,
                {"table_name": table, "index_name": index_name},
            )
            is not None
        )
    return index_name in {
        index["name"] for index in inspect(conn).get_indexes(table)
    }


def _quote_values(values: Iterable[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _collect_blockers(conn, report: IntegrityReport) -> None:
    duplicate_subscriptions = _rows(
        conn,
        """
        SELECT tenant_id, COUNT(*) AS total
        FROM subscriptions
        GROUP BY tenant_id
        HAVING COUNT(*) > 1
        """,
    )
    for row in duplicate_subscriptions:
        report.blockers.append(
            f"Tenant {row['tenant_id']} tiene {row['total']} subscriptions; resolver manualmente."
        )

    unknown_statuses = _rows(
        conn,
        f"""
        SELECT tenant_id, status
        FROM subscriptions
        WHERE LOWER(COALESCE(status, '')) NOT IN ({_quote_values(sorted(ALLOWED_SUBSCRIPTION_STATUSES))})
        """,
    )
    for row in unknown_statuses:
        report.blockers.append(
            "Subscription.status desconocido "
            f"para tenant {row['tenant_id']}: {row['status']!r}."
        )

    invalid_document_kinds = _rows(
        conn,
        f"""
        SELECT id, tenant_id, document_kind
        FROM cotizaciones
        WHERE document_kind IS NOT NULL
          AND TRIM(document_kind) != ''
          AND document_kind NOT IN ({_quote_values(sorted(VALID_DOCUMENT_KINDS))})
        """,
    )
    for row in invalid_document_kinds:
        report.blockers.append(
            f"document_kind invalido en cotizacion {row['id']} "
            f"(tenant {row['tenant_id']}): {row['document_kind']!r}."
        )

    notes_without_reference = _rows(
        conn,
        """
        SELECT id, tenant_id
        FROM cotizaciones
        WHERE (
            document_kind IN ('credit_note', 'debit_note')
            OR tipo_comprobante IN ('07', '08')
        )
          AND nota_referencia_id IS NULL
        """,
    )
    for row in notes_without_reference:
        report.blockers.append(
            f"Nota {row['id']} no tiene nota_referencia_id; no se corrige automaticamente."
        )

    note_reference_issues = _rows(
        conn,
        """
        SELECT
            note.id AS note_id,
            note.tenant_id AS note_tenant_id,
            ref.id AS ref_id,
            ref.tenant_id AS ref_tenant_id,
            ref.document_kind AS ref_document_kind,
            ref.tipo_comprobante AS ref_tipo_comprobante
        FROM cotizaciones note
        LEFT JOIN cotizaciones ref ON ref.id = note.nota_referencia_id
        WHERE (
            note.document_kind IN ('credit_note', 'debit_note')
            OR note.tipo_comprobante IN ('07', '08')
        )
          AND note.nota_referencia_id IS NOT NULL
          AND (
            ref.id IS NULL
            OR ref.tenant_id != note.tenant_id
            OR ref.document_kind != 'fiscal_document'
            OR ref.tipo_comprobante NOT IN ('01', '03')
          )
        """,
    )
    for row in note_reference_issues:
        if row["ref_id"] is None:
            report.blockers.append(
                f"Nota {row['note_id']} referencia un documento inexistente."
            )
        elif row["ref_tenant_id"] != row["note_tenant_id"]:
            report.blockers.append(
                f"Nota {row['note_id']} referencia documento de otro tenant."
            )
        else:
            report.blockers.append(
                f"Nota {row['note_id']} referencia documento no fiscal aceptable "
                f"({row['ref_document_kind']}/{row['ref_tipo_comprobante']})."
            )

    fiscal_documents_without_source = _rows(
        conn,
        """
        SELECT id, tenant_id
        FROM cotizaciones
        WHERE document_kind = 'fiscal_document'
          AND source_quote_id IS NULL
        """,
    )
    for row in fiscal_documents_without_source:
        report.blockers.append(
            f"Fiscal document {row['id']} tiene source_quote_id NULL; no se puede inferir con seguridad."
        )

    legacy_payments_cross_tenant = _rows(
        conn,
        """
        SELECT p.id, p.tenant_id, p.source_quote_id, q.tenant_id AS quote_tenant_id
        FROM pagos p
        JOIN cotizaciones q ON q.id = p.source_quote_id
        WHERE p.tipo = 'pago'
          AND p.fiscal_document_id IS NULL
          AND p.source_quote_id IS NOT NULL
          AND q.tenant_id != p.tenant_id
        """,
    )
    cross_tenant_payment_ids = {row["id"] for row in legacy_payments_cross_tenant}
    for row in legacy_payments_cross_tenant:
        report.blockers.append(
            f"Pago legacy {row['id']} tiene source_quote_id {row['source_quote_id']} "
            "apuntando a otra empresa/tenant."
        )

    legacy_payment_candidates = _rows(
        conn,
        """
        SELECT
            p.id AS payment_id,
            p.tenant_id,
            p.source_quote_id,
            COUNT(c.id) AS candidates
        FROM pagos p
        LEFT JOIN cotizaciones c
          ON c.tenant_id = p.tenant_id
         AND c.source_quote_id = p.source_quote_id
         AND c.document_kind = 'fiscal_document'
         AND c.estado = 'facturada'
         AND c.tipo_comprobante IN ('01', '03')
        WHERE p.tipo = 'pago'
          AND p.fiscal_document_id IS NULL
          AND p.source_quote_id IS NOT NULL
        GROUP BY p.id, p.tenant_id, p.source_quote_id
        """,
    )
    for row in legacy_payment_candidates:
        if row["payment_id"] in cross_tenant_payment_ids:
            continue
        candidates = int(row["candidates"] or 0)
        if candidates == 0:
            report.blockers.append(
                f"Pago legacy {row['payment_id']} no tiene fiscal aceptado candidato."
            )
        elif candidates > 1:
            report.blockers.append(
                f"Pago legacy {row['payment_id']} tiene {candidates} fiscales aceptados candidatos; resolver manualmente."
            )


def _plan_or_apply_missing_subscriptions(conn, report: IntegrityReport, *, apply: bool) -> None:
    missing_tenants = _rows(
        conn,
        """
        SELECT t.id
        FROM tenants t
        WHERE NOT EXISTS (
            SELECT 1
            FROM subscriptions s
            WHERE s.tenant_id = t.id
        )
        ORDER BY t.id
        """,
    )
    subscription_columns = _column_names(conn.engine, "subscriptions")
    for row in missing_tenants:
        tenant_id = row["id"]
        if not apply:
            report.planned_actions.append(f"Crear Subscription trial para tenant {tenant_id}.")
            continue

        columns = ["tenant_id", "status", "plan_code", "documents_used"]
        values = [":tenant_id", "'trial'", "'launch'", "0"]
        if "created_at" in subscription_columns:
            columns.append("created_at")
            values.append("CURRENT_TIMESTAMP")
        if "updated_at" in subscription_columns:
            columns.append("updated_at")
            values.append("CURRENT_TIMESTAMP")
        if "beta_feature_flags" in subscription_columns:
            columns.append("beta_feature_flags")
            values.append("'{}'")

        conn.execute(
            text(
                f"""
                INSERT INTO subscriptions ({", ".join(columns)})
                VALUES ({", ".join(values)})
                """
            ),
            {"tenant_id": tenant_id},
        )
        report.applied_actions.append(f"Subscription trial creada para tenant {tenant_id}.")


def _plan_or_apply_null_totals(conn, report: IntegrityReport, *, apply: bool) -> None:
    for column in TOTAL_COLUMNS:
        count = int(
            _scalar(
                conn,
                f"SELECT COUNT(*) FROM cotizaciones WHERE {column} IS NULL",
            )
            or 0
        )
        if count <= 0:
            continue
        if not apply:
            report.planned_actions.append(
                f"Normalizar {count} filas con cotizaciones.{column} NULL a 0."
            )
            continue

        result = conn.execute(
            text(f"UPDATE cotizaciones SET {column} = 0 WHERE {column} IS NULL")
        )
        if result.rowcount:
            report.applied_actions.append(
                f"Normalizadas {result.rowcount} filas con cotizaciones.{column} NULL a 0."
            )


def _plan_or_apply_document_kind_backfill(conn, report: IntegrityReport, *, apply: bool) -> None:
    count = int(
        _scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM cotizaciones
            WHERE document_kind IS NULL
               OR TRIM(document_kind) = ''
            """,
        )
        or 0
    )
    if count <= 0:
        return
    if not apply:
        report.planned_actions.append(
            f"Backfill deterministico de document_kind en {count} cotizaciones."
        )
        return

    result = conn.execute(
        text(
            """
            UPDATE cotizaciones
            SET document_kind = CASE
                WHEN tipo_comprobante IN ('01', '03') AND COALESCE(serie, '') != 'COT'
                    THEN 'fiscal_document'
                WHEN tipo_comprobante = '07' AND nota_referencia_id IS NOT NULL
                    THEN 'credit_note'
                WHEN tipo_comprobante = '08' AND nota_referencia_id IS NOT NULL
                    THEN 'debit_note'
                ELSE 'quotation'
            END
            WHERE document_kind IS NULL
               OR TRIM(document_kind) = ''
            """
        )
    )
    if result.rowcount:
        report.applied_actions.append(
            f"Backfill deterministico de document_kind aplicado en {result.rowcount} cotizaciones."
        )


def _eligible_legacy_payment_links(conn):
    return _rows(
        conn,
        """
        SELECT p.id AS payment_id, MIN(c.id) AS fiscal_document_id
        FROM pagos p
        JOIN cotizaciones c
          ON c.tenant_id = p.tenant_id
         AND c.source_quote_id = p.source_quote_id
         AND c.document_kind = 'fiscal_document'
         AND c.estado = 'facturada'
         AND c.tipo_comprobante IN ('01', '03')
        WHERE p.tipo = 'pago'
          AND p.fiscal_document_id IS NULL
          AND p.source_quote_id IS NOT NULL
        GROUP BY p.id
        HAVING COUNT(c.id) = 1
        """
    )


def _plan_or_apply_legacy_payment_links(conn, report: IntegrityReport, *, apply: bool) -> None:
    links = _eligible_legacy_payment_links(conn)
    for row in links:
        payment_id = row["payment_id"]
        fiscal_document_id = row["fiscal_document_id"]
        if not apply:
            report.planned_actions.append(
                f"Enlazar pago legacy {payment_id} con fiscal_document_id {fiscal_document_id}."
            )
            continue

        result = conn.execute(
            text(
                """
                UPDATE pagos
                SET fiscal_document_id = :fiscal_document_id
                WHERE id = :payment_id
                  AND tipo = 'pago'
                  AND fiscal_document_id IS NULL
                """
            ),
            {
                "payment_id": payment_id,
                "fiscal_document_id": fiscal_document_id,
            },
        )
        if result.rowcount:
            report.applied_actions.append(
                f"Pago legacy {payment_id} enlazado con fiscal_document_id {fiscal_document_id}."
            )


def _plan_or_apply_indexes(conn, report: IntegrityReport, *, apply: bool, dialect_name: str) -> None:
    for index_name, table_name, ddl in _index_definitions(dialect_name):
        if _index_exists(conn, dialect_name, table_name, index_name):
            continue
        if not apply:
            report.planned_actions.append(f"Crear indice {index_name}.")
            continue
        conn.execute(text(ddl))
        report.applied_actions.append(f"Indice {index_name} creado/verificado.")


def run_integrity_check(
    *,
    engine: Engine | None = None,
    apply: bool = False,
    echo: bool = True,
) -> IntegrityReport:
    if engine is None:
        from database import engine as default_engine

        engine = default_engine

    report = IntegrityReport()
    dialect_name = engine.dialect.name
    report.checks_ok.append(f"Dialecto detectado: {dialect_name}.")

    if not _validate_critical_columns(engine, report):
        if echo:
            print_report(report, apply=apply)
        return report

    with engine.begin() as conn:
        _collect_blockers(conn, report)

        if report.blockers:
            report.warnings.append("Hay bloqueantes; no se aplicaron correcciones.")
            if echo:
                print_report(report, apply=apply)
            return report

        _plan_or_apply_missing_subscriptions(conn, report, apply=apply)
        _plan_or_apply_null_totals(conn, report, apply=apply)
        _plan_or_apply_document_kind_backfill(conn, report, apply=apply)
        _plan_or_apply_legacy_payment_links(conn, report, apply=apply)
        _plan_or_apply_indexes(conn, report, apply=apply, dialect_name=dialect_name)

    if echo:
        print_report(report, apply=apply)
    return report


def print_report(report: IntegrityReport, *, apply: bool) -> None:
    mode = "apply" if apply else "dry-run"
    print("=" * 72)
    print(f"migrate_beta_integrity.py - reporte ({mode})")
    print("=" * 72)

    def section(title: str, values: list[str]) -> None:
        print(f"\n[{title}]")
        if not values:
            print("  - Ninguno.")
            return
        for value in values:
            print(f"  - {value}")

    section("checks OK", report.checks_ok)
    section("acciones que se aplicarian", report.planned_actions)
    section("acciones aplicadas", report.applied_actions)
    section("bloqueantes", report.blockers)
    section("advertencias", report.warnings)
    print(f"\nexit_code={report.exit_code}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verifica y sanea datos criticos pre-beta sin crear columnas."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Solo reporta acciones. Default.")
    mode.add_argument("--apply", action="store_true", help="Aplica correcciones seguras.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    apply_changes = bool(args.apply)
    try:
        report = run_integrity_check(apply=apply_changes, echo=True)
        return report.exit_code
    except SQLAlchemyError as exc:
        print(f"[ERROR] Error de base de datos ejecutando migrate_beta_integrity: {exc}")
        return 2
    except Exception as exc:
        print(f"[ERROR] Error inesperado ejecutando migrate_beta_integrity: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
