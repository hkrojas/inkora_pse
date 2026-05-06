"""Limpieza segura de datos de prueba antes de beta pagada.

Este script no toca el schema, no ejecuta Alembic y no usa proveedores fiscales.
Por defecto corre en dry-run. El modo --apply exige confirmaciones explicitas,
backup existente y alembic_version en 0002_beta_feature_flags.
"""
from __future__ import annotations

import argparse
import os
import secrets
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from passlib.context import CryptContext
from sqlalchemy import bindparam, create_engine, inspect, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError


EXPECTED_ALEMBIC_VERSION = "0002_beta_feature_flags"
DEFAULT_CLEANUP_MODE = "test_tenants_only"
DEFAULT_ADMIN_TENANT_NAME = "Inkora Admin"
DEFAULT_ADMIN_TENANT_RUC = "00000000000"
DEFAULT_FLAGS = {
    "credit_notes": False,
    "debit_notes": False,
    "guides": False,
    "daily_summary": False,
    "voiding": False,
    "reversions": False,
    "retentions": False,
    "perceptions": False,
    "direct_sunat": False,
}
SUPPORTED_FLAGS = set(DEFAULT_FLAGS)
ALLOWED_SUBSCRIPTION_STATUSES = {"active", "trial", "grace"}
TEST_TENANT_MARKERS = ("e2e", "demo", "test", "prueba")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass
class TableAction:
    table: str
    count: int
    action: str


@dataclass
class CleanupReport:
    mode: str
    apply: bool
    database_url_redacted: str = ""
    checks_ok: list[str] = field(default_factory=list)
    planned_actions: list[str] = field(default_factory=list)
    applied_actions: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    table_actions: list[TableAction] = field(default_factory=list)
    generated_password_messages: list[str] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        return 1 if self.blockers else 0


class CleanupAbort(Exception):
    """Aborta una transaccion apply y fuerza rollback."""


DIRECT_TENANT_TABLES = (
    "document_emission_jobs",
    "pagos",
    "guias_remision",
    "resumenes_diarios",
    "retenciones_fiscales",
    "percepciones_fiscales",
    "reversiones_fiscales",
    "ordenes_produccion",
    "cotizaciones",
    "recetas_bom",
    "alertas_inventario",
    "proveedores",
    "insumos",
    "clientes",
    "productos",
    "subscription_payments",
    "usage_limits",
)

JOIN_DELETE_TABLES = (
    ("guia_remision_items", "guia_id", "guias_remision", "id"),
    ("cotizacion_items", "cotizacion_id", "cotizaciones", "id"),
    ("ordenes_produccion_detalle", "orden_id", "ordenes_produccion", "id"),
)


def _bool_env(env: dict[str, str], key: str, default: bool = False) -> bool:
    raw = str(env.get(key, "")).strip().lower()
    if raw in {"1", "true", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _load_backend_dotenv_if_needed() -> None:
    """Carga backend/.env si DATABASE_URL no esta en el proceso actual."""
    if os.getenv("DATABASE_URL"):
        return
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def redact_database_url(database_url: str) -> str:
    parts = urlsplit(database_url or "")
    if parts.password:
        netloc = f"{parts.username or ''}:***@{parts.hostname or ''}"
        if parts.port:
            netloc += f":{parts.port}"
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    return database_url or ""


def _table_exists(engine_or_conn: Engine | Connection, table_name: str) -> bool:
    return table_name in inspect(engine_or_conn).get_table_names()


def _column_names(engine_or_conn: Engine | Connection, table_name: str) -> set[str]:
    inspector = inspect(engine_or_conn)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _execute_rows(conn: Connection, sql: str, params: dict[str, Any] | None = None):
    return conn.execute(text(sql), params or {}).mappings().all()


def _scalar(conn: Connection, sql: str, params: dict[str, Any] | None = None):
    return conn.execute(text(sql), params or {}).scalar()


def _in_stmt(sql: str):
    return text(sql).bindparams(bindparam("tenant_ids", expanding=True))


def _json_expr(conn: Connection) -> str:
    return "CAST(:flags AS JSON)" if conn.engine.dialect.name == "postgresql" else ":flags"


def _now_expr(conn: Connection) -> str:
    return "CURRENT_TIMESTAMP"


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _generated_password(label: str, env: dict[str, str], report: CleanupReport) -> str:
    password = secrets.token_urlsafe(32) + "9a!"
    if _bool_env(env, "BETA_PRINT_GENERATED_PASSWORD_ONCE", False):
        report.generated_password_messages.append(
            f"{label}: password generado una sola vez = {password}"
        )
    else:
        report.generated_password_messages.append(
            f"{label}: password generado y oculto. Define BETA_PRINT_GENERATED_PASSWORD_ONCE=true solo en consola segura si necesitas verlo."
        )
    return password


def _current_alembic_version(conn: Connection) -> str | None:
    if not _table_exists(conn, "alembic_version"):
        return None
    return _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")


def _validate_apply_guards(conn: Connection, env: dict[str, str], report: CleanupReport) -> bool:
    if not report.apply:
        return True

    if env.get("ALLOW_BETA_DATA_CLEANUP") != "true":
        report.blockers.append("ALLOW_BETA_DATA_CLEANUP=true es obligatorio para --apply.")
    if env.get("BETA_DATA_CLEANUP_CONFIRM") != "CLEAN_TEST_RECORDS":
        report.blockers.append("BETA_DATA_CLEANUP_CONFIRM=CLEAN_TEST_RECORDS es obligatorio para --apply.")

    backup_path = env.get("BETA_DB_BACKUP_PATH", "").strip()
    if not backup_path:
        report.blockers.append("BETA_DB_BACKUP_PATH es obligatorio para --apply.")
    elif not Path(backup_path).exists():
        report.blockers.append(f"BETA_DB_BACKUP_PATH no existe: {backup_path}")
    else:
        report.checks_ok.append(f"Backup confirmado: {backup_path}")

    current = _current_alembic_version(conn)
    if current != EXPECTED_ALEMBIC_VERSION:
        report.blockers.append(
            f"alembic_version debe ser {EXPECTED_ALEMBIC_VERSION}; actual={current}."
        )
    else:
        report.checks_ok.append(f"alembic_version OK: {current}.")

    environment = env.get("ENVIRONMENT", env.get("APP_ENV", "")).strip().lower()
    if environment in {"production", "prod"}:
        report.blockers.append("No se permite --apply con ENVIRONMENT=production/prod.")

    database_url = env.get("DATABASE_URL", "")
    host = urlsplit(database_url).hostname or ""
    if host and host not in {"localhost", "127.0.0.1"} and "supabase.com" not in host:
        report.blockers.append(
            f"Host de DATABASE_URL no reconocido para cleanup controlado: {host}."
        )

    return not report.blockers


def _validate_schema(conn: Connection, report: CleanupReport) -> None:
    for table_name in ("tenants", "users", "subscriptions", "alembic_version"):
        if not _table_exists(conn, table_name):
            report.blockers.append(f"Falta tabla requerida {table_name}.")
    if _table_exists(conn, "users") and "tenant_id" not in _column_names(conn, "users"):
        report.blockers.append("users.tenant_id es requerido para crear superadmin tecnico.")
    if _table_exists(conn, "subscriptions") and "beta_feature_flags" not in _column_names(conn, "subscriptions"):
        report.blockers.append(
            "Falta columna subscriptions.beta_feature_flags. Ejecuta Alembic 0002 antes del cleanup."
        )


def _reserved_tenant_filters(env: dict[str, str]) -> tuple[str | None, str | None, str]:
    real_ruc = env.get("BETA_TENANT_RUC", "").strip() or None
    real_name = env.get("BETA_TENANT_NAME", "").strip() or None
    admin_name = env.get("BETA_ADMIN_TENANT_NAME", DEFAULT_ADMIN_TENANT_NAME).strip() or DEFAULT_ADMIN_TENANT_NAME
    return real_ruc, real_name, admin_name


def _resolve_target_tenants(conn: Connection, env: dict[str, str], report: CleanupReport) -> list[dict[str, Any]]:
    mode = env.get("BETA_CLEANUP_MODE", DEFAULT_CLEANUP_MODE).strip() or DEFAULT_CLEANUP_MODE
    if mode not in {"test_tenants_only", "all_test_data"}:
        report.blockers.append("BETA_CLEANUP_MODE debe ser test_tenants_only o all_test_data.")
        return []

    if not _table_exists(conn, "tenants"):
        return []

    real_ruc, real_name, admin_name = _reserved_tenant_filters(env)
    params = {
        "real_ruc": real_ruc,
        "real_name": real_name,
        "admin_name": admin_name,
    }
    if mode == "test_tenants_only":
        rows = _execute_rows(
            conn,
            """
            SELECT id, business_name, business_ruc, is_active
            FROM tenants
            WHERE (
                lower(COALESCE(business_name, '')) LIKE '%e2e%'
                OR lower(COALESCE(business_name, '')) LIKE '%demo%'
                OR lower(COALESCE(business_name, '')) LIKE '%test%'
                OR lower(COALESCE(business_name, '')) LIKE '%prueba%'
            )
            AND (:real_ruc IS NULL OR business_ruc <> :real_ruc)
            AND (:real_name IS NULL OR business_name <> :real_name)
            AND business_name <> :admin_name
            ORDER BY id
            """,
            params,
        )
    else:
        rows = _execute_rows(
            conn,
            """
            SELECT id, business_name, business_ruc, is_active
            FROM tenants
            WHERE (:real_ruc IS NULL OR business_ruc <> :real_ruc)
              AND (:real_name IS NULL OR business_name <> :real_name)
              AND business_name <> :admin_name
            ORDER BY id
            """,
            params,
        )

    tenants = [dict(row) for row in rows]
    if tenants:
        report.checks_ok.append(
            "Tenants objetivo: "
            + ", ".join(f"{row['id']}:{row['business_name']}" for row in tenants)
        )
    else:
        report.warnings.append("No se detectaron tenants objetivo para limpieza.")
    return tenants


def _count_direct(conn: Connection, table: str, tenant_ids: list[int]) -> int:
    if not tenant_ids or not _table_exists(conn, table) or "tenant_id" not in _column_names(conn, table):
        return 0
    stmt = _in_stmt(f"SELECT COUNT(*) FROM {table} WHERE tenant_id IN :tenant_ids")
    return int(conn.execute(stmt, {"tenant_ids": tenant_ids}).scalar() or 0)


def _count_join(conn: Connection, table: str, fk: str, parent: str, parent_id: str, tenant_ids: list[int]) -> int:
    if not tenant_ids or not _table_exists(conn, table) or not _table_exists(conn, parent):
        return 0
    if fk not in _column_names(conn, table) or "tenant_id" not in _column_names(conn, parent):
        return 0
    stmt = _in_stmt(
        f"""
        SELECT COUNT(*)
        FROM {table}
        WHERE {fk} IN (
            SELECT {parent_id}
            FROM {parent}
            WHERE tenant_id IN :tenant_ids
        )
        """
    )
    return int(conn.execute(stmt, {"tenant_ids": tenant_ids}).scalar() or 0)


def _collect_table_counts(conn: Connection, tenant_ids: list[int], report: CleanupReport, env: dict[str, str]) -> None:
    for table, fk, parent, parent_id in JOIN_DELETE_TABLES:
        if not _table_exists(conn, table):
            report.warnings.append(f"Tabla esperada ausente, se omite: {table}.")
            continue
        count = _count_join(conn, table, fk, parent, parent_id, tenant_ids)
        report.table_actions.append(TableAction(table, count, "DELETE por relacion tenant"))

    for table in DIRECT_TENANT_TABLES:
        if not _table_exists(conn, table):
            report.warnings.append(f"Tabla esperada ausente, se omite: {table}.")
            continue
        count = _count_direct(conn, table, tenant_ids)
        report.table_actions.append(TableAction(table, count, "DELETE por tenant"))

    if _table_exists(conn, "users"):
        count = _count_direct(conn, "users", tenant_ids)
        action = "DELETE" if _bool_env(env, "BETA_DELETE_TEST_TENANTS", False) else "desactivar"
        report.table_actions.append(TableAction("users", count, f"{action} usuarios de tenants test"))
    if _table_exists(conn, "subscriptions"):
        count = _count_direct(conn, "subscriptions", tenant_ids)
        action = "DELETE" if _bool_env(env, "BETA_DELETE_TEST_TENANTS", False) else "preservar"
        report.table_actions.append(TableAction("subscriptions", count, action))
    if _table_exists(conn, "tenants"):
        count = len(tenant_ids)
        action = "DELETE" if _bool_env(env, "BETA_DELETE_TEST_TENANTS", False) else "desactivar"
        report.table_actions.append(TableAction("tenants", count, action))
    if _table_exists(conn, "audit_logs"):
        report.table_actions.append(
            TableAction(
                "audit_logs",
                _count_audit_logs_for_tenants(conn, tenant_ids),
                "preservar" if not _bool_env(env, "BETA_CLEAN_AUDIT_LOGS", False) else "DELETE confirmado",
            )
        )


def _count_audit_logs_for_tenants(conn: Connection, tenant_ids: list[int]) -> int:
    if not tenant_ids or not _table_exists(conn, "audit_logs") or not _table_exists(conn, "users"):
        return 0
    stmt = _in_stmt(
        """
        SELECT COUNT(*)
        FROM audit_logs
        WHERE user_id IN (SELECT id FROM users WHERE tenant_id IN :tenant_ids)
           OR (entity_type = 'tenant' AND entity_id IN :tenant_ids)
        """
    )
    return int(conn.execute(stmt, {"tenant_ids": tenant_ids}).scalar() or 0)


def _delete_direct(conn: Connection, table: str, tenant_ids: list[int]) -> int:
    if not tenant_ids or not _table_exists(conn, table) or "tenant_id" not in _column_names(conn, table):
        return 0
    stmt = _in_stmt(f"DELETE FROM {table} WHERE tenant_id IN :tenant_ids")
    return int(conn.execute(stmt, {"tenant_ids": tenant_ids}).rowcount or 0)


def _delete_join(conn: Connection, table: str, fk: str, parent: str, parent_id: str, tenant_ids: list[int]) -> int:
    if not tenant_ids or not _table_exists(conn, table) or not _table_exists(conn, parent):
        return 0
    stmt = _in_stmt(
        f"""
        DELETE FROM {table}
        WHERE {fk} IN (
            SELECT {parent_id}
            FROM {parent}
            WHERE tenant_id IN :tenant_ids
        )
        """
    )
    return int(conn.execute(stmt, {"tenant_ids": tenant_ids}).rowcount or 0)


def _apply_business_cleanup(conn: Connection, tenant_ids: list[int], env: dict[str, str], report: CleanupReport) -> None:
    for table, fk, parent, parent_id in JOIN_DELETE_TABLES:
        deleted = _delete_join(conn, table, fk, parent, parent_id, tenant_ids)
        if deleted:
            report.applied_actions.append(f"{table}: {deleted} filas eliminadas.")

    for table in DIRECT_TENANT_TABLES:
        deleted = _delete_direct(conn, table, tenant_ids)
        if deleted:
            report.applied_actions.append(f"{table}: {deleted} filas eliminadas.")

    if _bool_env(env, "BETA_CLEAN_AUDIT_LOGS", False) and _table_exists(conn, "audit_logs"):
        stmt = _in_stmt(
            """
            DELETE FROM audit_logs
            WHERE user_id IN (SELECT id FROM users WHERE tenant_id IN :tenant_ids)
               OR (entity_type = 'tenant' AND entity_id IN :tenant_ids)
            """
        )
        deleted = int(conn.execute(stmt, {"tenant_ids": tenant_ids}).rowcount or 0)
        report.applied_actions.append(f"audit_logs: {deleted} filas eliminadas por confirmacion.")

    delete_test_tenants = _bool_env(env, "BETA_DELETE_TEST_TENANTS", False)
    if delete_test_tenants:
        if not _bool_env(env, "BETA_CLEAN_AUDIT_LOGS", False) and _count_audit_logs_for_tenants(conn, tenant_ids):
            report.blockers.append(
                "BETA_DELETE_TEST_TENANTS=true requiere BETA_CLEAN_AUDIT_LOGS=true si hay audit_logs relacionados."
            )
            raise CleanupAbort()
        for table in ("users", "subscriptions", "tenants"):
            deleted = _delete_direct(conn, table, tenant_ids) if table != "tenants" else _delete_tenants(conn, tenant_ids)
            if deleted:
                report.applied_actions.append(f"{table}: {deleted} filas eliminadas.")
    else:
        if _table_exists(conn, "users"):
            stmt = _in_stmt("UPDATE users SET is_active = :inactive WHERE tenant_id IN :tenant_ids")
            updated = int(conn.execute(stmt, {"tenant_ids": tenant_ids, "inactive": False}).rowcount or 0)
            if updated:
                report.applied_actions.append(f"users: {updated} usuarios test desactivados.")
        if _table_exists(conn, "tenants"):
            stmt = _in_stmt("UPDATE tenants SET is_active = :inactive WHERE id IN :tenant_ids")
            updated = int(conn.execute(stmt, {"tenant_ids": tenant_ids, "inactive": False}).rowcount or 0)
            if updated:
                report.applied_actions.append(f"tenants: {updated} tenants test desactivados.")


def _delete_tenants(conn: Connection, tenant_ids: list[int]) -> int:
    if not tenant_ids or not _table_exists(conn, "tenants"):
        return 0
    stmt = _in_stmt("DELETE FROM tenants WHERE id IN :tenant_ids")
    return int(conn.execute(stmt, {"tenant_ids": tenant_ids}).rowcount or 0)


def _ensure_admin_tenant(conn: Connection, env: dict[str, str], report: CleanupReport, *, apply: bool) -> int | None:
    admin_name = env.get("BETA_ADMIN_TENANT_NAME", DEFAULT_ADMIN_TENANT_NAME).strip() or DEFAULT_ADMIN_TENANT_NAME
    admin_ruc = env.get("BETA_ADMIN_TENANT_RUC", DEFAULT_ADMIN_TENANT_RUC).strip() or DEFAULT_ADMIN_TENANT_RUC
    admin_address = env.get("BETA_ADMIN_TENANT_ADDRESS", "Tenant tecnico administrativo").strip()

    existing = _execute_rows(
        conn,
        "SELECT id FROM tenants WHERE business_name = :name OR business_ruc = :ruc ORDER BY id",
        {"name": admin_name, "ruc": admin_ruc},
    )
    if existing:
        tenant_id = int(existing[0]["id"])
        if apply:
            conn.execute(
                text(
                    """
                    UPDATE tenants
                    SET business_name = :name,
                        business_ruc = :ruc,
                        business_address = :address,
                        is_active = :active
                    WHERE id = :tenant_id
                    """
                ),
                {"tenant_id": tenant_id, "name": admin_name, "ruc": admin_ruc, "address": admin_address, "active": True},
            )
            report.applied_actions.append(f"Tenant tecnico superadmin preservado/actualizado: {tenant_id}.")
        else:
            report.planned_actions.append(f"Preservar/actualizar tenant tecnico superadmin: {tenant_id}.")
        return tenant_id

    if not apply:
        report.planned_actions.append(f"Crear tenant tecnico superadmin: {admin_name}.")
        return None

    conn.execute(
        text(
            """
            INSERT INTO tenants (business_name, business_ruc, business_address, is_active)
            VALUES (:name, :ruc, :address, :active)
            """
        ),
        {"name": admin_name, "ruc": admin_ruc, "address": admin_address, "active": True},
    )
    tenant_id = int(
        conn.execute(
            text("SELECT id FROM tenants WHERE business_ruc = :ruc"),
            {"ruc": admin_ruc},
        ).scalar_one()
    )
    report.applied_actions.append(f"Tenant tecnico superadmin creado: {tenant_id}.")
    return tenant_id


def _create_or_update_superadmin(conn: Connection, env: dict[str, str], report: CleanupReport, *, apply: bool) -> None:
    email = env.get("BETA_SUPERADMIN_EMAIL", "").strip().lower()
    if not email:
        return
    reset_password = _bool_env(env, "BETA_RESET_SUPERADMIN_PASSWORD", False)
    provided_password = env.get("BETA_SUPERADMIN_PASSWORD", "")

    if not apply:
        report.planned_actions.append(f"Crear/actualizar superadmin propio: {email}.")
        if not provided_password:
            report.planned_actions.append("Se generaria password temporal para superadmin propio.")
        return

    tenant_id = _ensure_admin_tenant(conn, env, report, apply=True)
    user = _execute_rows(conn, "SELECT id FROM users WHERE lower(email) = :email", {"email": email})
    password = provided_password
    if not user and not password:
        password = _generated_password("BETA_SUPERADMIN_PASSWORD", env, report)

    if user:
        user_id = int(user[0]["id"])
        assignments = [
            "tenant_id = :tenant_id",
            "rol = 'superadmin'",
            "is_superadmin = :is_superadmin",
            "is_active = :is_active",
            "must_change_password = :must_change_password",
        ]
        params: dict[str, Any] = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "is_superadmin": True,
            "is_active": True,
            "must_change_password": False,
        }
        if reset_password:
            if not password:
                password = _generated_password("BETA_SUPERADMIN_PASSWORD", env, report)
            assignments.append("hashed_password = :hashed_password")
            params["hashed_password"] = _hash_password(password)
        conn.execute(text(f"UPDATE users SET {', '.join(assignments)} WHERE id = :user_id"), params)
        report.applied_actions.append(f"Superadmin propio actualizado: {email}.")
    else:
        conn.execute(
            text(
                """
                INSERT INTO users (
                    email, hashed_password, nombre_completo, rol,
                    is_superadmin, is_active, must_change_password, tenant_id
                )
                VALUES (
                    :email, :hashed_password, :nombre, 'superadmin',
                    :is_superadmin, :is_active, :must_change_password, :tenant_id
                )
                """
            ),
            {
                "email": email,
                "hashed_password": _hash_password(password),
                "nombre": email,
                "is_superadmin": True,
                "is_active": True,
                "must_change_password": False,
                "tenant_id": tenant_id,
            },
        )
        report.applied_actions.append(f"Superadmin propio creado: {email}.")


def _handle_default_superadmin(conn: Connection, env: dict[str, str], report: CleanupReport, *, apply: bool) -> None:
    default_email = env.get("BETA_DEFAULT_SUPERADMIN_EMAIL", "").strip().lower()
    action = env.get("BETA_DEFAULT_SUPERADMIN_ACTION", "keep").strip().lower() or "keep"
    own_email = env.get("BETA_SUPERADMIN_EMAIL", "").strip().lower()
    if not default_email or action == "keep":
        return
    if action not in {"disable", "delete"}:
        report.blockers.append("BETA_DEFAULT_SUPERADMIN_ACTION debe ser keep, disable o delete.")
        return
    if default_email == own_email:
        report.blockers.append("No se puede aplicar accion default al mismo correo del superadmin propio.")
        return
    if action == "delete" and env.get("BETA_DELETE_DEFAULT_SUPERADMIN_CONFIRM") != "DELETE_DEFAULT_SUPERADMIN":
        report.blockers.append(
            "BETA_DELETE_DEFAULT_SUPERADMIN_CONFIRM=DELETE_DEFAULT_SUPERADMIN es obligatorio para borrar superadmin default."
        )
        return

    if not apply:
        report.planned_actions.append(f"{action} superadmin default: {default_email}.")
        return

    row = _execute_rows(
        conn,
        "SELECT id FROM users WHERE lower(email) = :email AND is_superadmin = :is_superadmin",
        {"email": default_email, "is_superadmin": True},
    )
    if not row:
        report.warnings.append(f"Superadmin default no encontrado: {default_email}.")
        return
    user_id = int(row[0]["id"])
    if action == "disable":
        conn.execute(text("UPDATE users SET is_active = :inactive WHERE id = :id"), {"inactive": False, "id": user_id})
        report.applied_actions.append(f"Superadmin default desactivado: {default_email}.")
    else:
        audit_count = 0
        if _table_exists(conn, "audit_logs"):
            audit_count = int(
                conn.execute(text("SELECT COUNT(*) FROM audit_logs WHERE user_id = :id"), {"id": user_id}).scalar() or 0
            )
        if audit_count:
            report.blockers.append("No se borra superadmin default porque tiene audit_logs asociados; usa disable.")
            raise CleanupAbort()
        conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        report.applied_actions.append(f"Superadmin default eliminado: {default_email}.")


def _upsert_real_tenant(conn: Connection, env: dict[str, str], report: CleanupReport, *, apply: bool) -> int | None:
    provided = [
        env.get("BETA_TENANT_RUC", "").strip(),
        env.get("BETA_TENANT_NAME", "").strip(),
        env.get("BETA_TENANT_ADMIN_EMAIL", "").strip(),
    ]
    if not any(provided):
        return None
    if not all(provided):
        report.blockers.append(
            "Para crear/preservar tenant real se requieren BETA_TENANT_RUC, BETA_TENANT_NAME y BETA_TENANT_ADMIN_EMAIL."
        )
        return None

    ruc = provided[0]
    name = provided[1]
    address = env.get("BETA_TENANT_ADDRESS", "").strip()
    row = _execute_rows(conn, "SELECT id FROM tenants WHERE business_ruc = :ruc", {"ruc": ruc})
    if row:
        tenant_id = int(row[0]["id"])
        if apply:
            conn.execute(
                text(
                    """
                    UPDATE tenants
                    SET business_name = :name,
                        business_address = :address,
                        is_active = :active
                    WHERE id = :tenant_id
                    """
                ),
                {"tenant_id": tenant_id, "name": name, "address": address, "active": True},
            )
            report.applied_actions.append(f"Tenant real preservado/actualizado: {tenant_id}.")
        else:
            report.planned_actions.append(f"Preservar/actualizar tenant real RUC {ruc}.")
        return tenant_id

    if not apply:
        report.planned_actions.append(f"Crear tenant real RUC {ruc}.")
        return None

    conn.execute(
        text(
            """
            INSERT INTO tenants (business_name, business_ruc, business_address, is_active)
            VALUES (:name, :ruc, :address, :active)
            """
        ),
        {"name": name, "ruc": ruc, "address": address, "active": True},
    )
    tenant_id = int(
        conn.execute(
            text("SELECT id FROM tenants WHERE business_ruc = :ruc"),
            {"ruc": ruc},
        ).scalar_one()
    )
    report.applied_actions.append(f"Tenant real creado: {tenant_id}.")
    return tenant_id


def _parse_initial_flags(env: dict[str, str], report: CleanupReport) -> str:
    flags = dict(DEFAULT_FLAGS)
    enable_raw = env.get("BETA_ENABLE_FLAGS", "").strip()
    if enable_raw:
        requested = {item.strip() for item in enable_raw.split(",") if item.strip()}
        unknown = sorted(requested - SUPPORTED_FLAGS)
        if unknown:
            report.blockers.append("BETA_ENABLE_FLAGS contiene flags no soportados: " + ", ".join(unknown))
        for key in requested & SUPPORTED_FLAGS:
            if key == "direct_sunat":
                report.blockers.append("direct_sunat no se habilita desde cleanup_beta_test_data.py.")
                continue
            flags[key] = True
    if _bool_env(env, "BETA_DIRECT_SUNAT", False):
        report.blockers.append("BETA_DIRECT_SUNAT debe permanecer false en este script.")
    flags["direct_sunat"] = False
    import json

    return json.dumps(flags, sort_keys=True)


def _upsert_subscription(conn: Connection, tenant_id: int, env: dict[str, str], report: CleanupReport, *, apply: bool) -> None:
    status = env.get("BETA_SUBSCRIPTION_STATUS", "trial").strip() or "trial"
    plan_code = env.get("BETA_PLAN_CODE", "beta").strip() or "beta"
    if status not in ALLOWED_SUBSCRIPTION_STATUSES:
        report.blockers.append("BETA_SUBSCRIPTION_STATUS debe ser active, trial o grace.")
        return
    flags = _parse_initial_flags(env, report)
    if report.blockers:
        return

    row = _execute_rows(conn, "SELECT id FROM subscriptions WHERE tenant_id = :tenant_id", {"tenant_id": tenant_id})
    expr = _json_expr(conn)
    subscription_columns = _column_names(conn, "subscriptions")
    if not apply:
        report.planned_actions.append(f"Crear/actualizar subscription tenant {tenant_id} status={status} plan={plan_code}.")
        return
    if row:
        assignments = [
            "status = :status",
            "plan_code = :plan_code",
            f"beta_feature_flags = {expr}",
        ]
        if "onboarding_status" in subscription_columns:
            assignments.append("onboarding_status = COALESCE(onboarding_status, 'not_started')")
        if "is_pilot" in subscription_columns:
            assignments.append("is_pilot = COALESCE(is_pilot, :is_pilot)")
        if "updated_at" in subscription_columns:
            assignments.append(f"updated_at = {_now_expr(conn)}")
        conn.execute(
            text(
                f"UPDATE subscriptions SET {', '.join(assignments)} WHERE tenant_id = :tenant_id"
            ),
            {
                "tenant_id": tenant_id,
                "status": status,
                "plan_code": plan_code,
                "flags": flags,
                "is_pilot": False,
            },
        )
        report.applied_actions.append(f"Subscription actualizada para tenant {tenant_id}.")
    else:
        insert_columns = ["tenant_id", "status", "plan_code", "documents_used", "beta_feature_flags"]
        insert_values = [":tenant_id", ":status", ":plan_code", "0", expr]
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "status": status,
            "plan_code": plan_code,
            "flags": flags,
        }
        if "onboarding_status" in subscription_columns:
            insert_columns.append("onboarding_status")
            insert_values.append("'not_started'")
        if "is_pilot" in subscription_columns:
            insert_columns.append("is_pilot")
            insert_values.append(":is_pilot")
            params["is_pilot"] = False
        if "created_at" in subscription_columns:
            insert_columns.append("created_at")
            insert_values.append(_now_expr(conn))
        if "updated_at" in subscription_columns:
            insert_columns.append("updated_at")
            insert_values.append(_now_expr(conn))
        conn.execute(
            text(
                f"""
                INSERT INTO subscriptions ({', '.join(insert_columns)})
                VALUES ({', '.join(insert_values)})
                """
            ),
            params,
        )
        report.applied_actions.append(f"Subscription creada para tenant {tenant_id}.")


def _upsert_real_tenant_admin(conn: Connection, tenant_id: int, env: dict[str, str], report: CleanupReport, *, apply: bool) -> None:
    email = env.get("BETA_TENANT_ADMIN_EMAIL", "").strip().lower()
    if not email:
        return
    password = env.get("BETA_TENANT_ADMIN_PASSWORD", "")
    if not apply:
        report.planned_actions.append(f"Crear/actualizar usuario tenant admin: {email}.")
        if not password:
            report.planned_actions.append("Se generaria password temporal para usuario tenant admin.")
        return
    if not password:
        password = _generated_password("BETA_TENANT_ADMIN_PASSWORD", env, report)
    row = _execute_rows(conn, "SELECT id FROM users WHERE lower(email) = :email", {"email": email})
    if row:
        conn.execute(
            text(
                """
                UPDATE users
                SET tenant_id = :tenant_id,
                    rol = 'admin',
                    is_superadmin = :is_superadmin,
                    is_active = :is_active
                WHERE lower(email) = :email
                """
            ),
            {"tenant_id": tenant_id, "email": email, "is_superadmin": False, "is_active": True},
        )
        report.applied_actions.append(f"Usuario tenant admin actualizado: {email}.")
    else:
        conn.execute(
            text(
                """
                INSERT INTO users (
                    email, hashed_password, nombre_completo, rol,
                    is_superadmin, is_active, must_change_password, tenant_id
                )
                VALUES (
                    :email, :hashed_password, :nombre, 'admin',
                    :is_superadmin, :is_active, :must_change_password, :tenant_id
                )
                """
            ),
            {
                "email": email,
                "hashed_password": _hash_password(password),
                "nombre": email,
                "is_superadmin": False,
                "is_active": True,
                "must_change_password": True,
                "tenant_id": tenant_id,
            },
        )
        report.applied_actions.append(f"Usuario tenant admin creado: {email}.")


def _ensure_active_superadmin(conn: Connection, report: CleanupReport) -> None:
    if not _table_exists(conn, "users"):
        report.blockers.append("No se puede verificar superadmin activo; falta users.")
        raise CleanupAbort()
    count = int(
        conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM users
                WHERE is_superadmin = :is_superadmin
                  AND is_active = :is_active
                """
            ),
            {"is_superadmin": True, "is_active": True},
        ).scalar()
        or 0
    )
    if count < 1:
        report.blockers.append("El cleanup dejaria cero superadmins activos; rollback.")
        raise CleanupAbort()
    report.checks_ok.append(f"Superadmins activos despues del cleanup: {count}.")


def run_cleanup(
    *,
    engine: Engine,
    env: dict[str, str] | None = None,
    apply: bool = False,
    echo: bool = True,
) -> CleanupReport:
    env = dict(env or os.environ)
    mode = env.get("BETA_CLEANUP_MODE", DEFAULT_CLEANUP_MODE).strip() or DEFAULT_CLEANUP_MODE
    report = CleanupReport(mode=mode, apply=apply, database_url_redacted=redact_database_url(env.get("DATABASE_URL", "")))

    try:
        with engine.connect() as conn:
            report.checks_ok.append(f"Dialecto detectado: {engine.dialect.name}.")
            current = _current_alembic_version(conn)
            if current == EXPECTED_ALEMBIC_VERSION:
                report.checks_ok.append(f"alembic_version OK: {current}.")
            else:
                report.blockers.append(
                    f"alembic_version debe ser {EXPECTED_ALEMBIC_VERSION}; actual={current}."
                )
            _validate_schema(conn, report)
            target_tenants = _resolve_target_tenants(conn, env, report)
            tenant_ids = [int(row["id"]) for row in target_tenants]
            _collect_table_counts(conn, tenant_ids, report, env)

            if not apply:
                _create_or_update_superadmin(conn, env, report, apply=False)
                _handle_default_superadmin(conn, env, report, apply=False)
                tenant_id = _upsert_real_tenant(conn, env, report, apply=False)
                if tenant_id is not None or env.get("BETA_TENANT_RUC"):
                    report.planned_actions.append("Configurar tenant real, usuario admin y subscription en --apply.")
                if echo:
                    print_report(report)
                return report

            if report.blockers:
                if echo:
                    print_report(report)
                return report
            if not _validate_apply_guards(conn, env, report):
                if echo:
                    print_report(report)
                return report

        with engine.begin() as conn:
            try:
                _apply_business_cleanup(conn, tenant_ids, env, report)
                _create_or_update_superadmin(conn, env, report, apply=True)
                _handle_default_superadmin(conn, env, report, apply=True)
                real_tenant_id = _upsert_real_tenant(conn, env, report, apply=True)
                if real_tenant_id is not None:
                    _upsert_real_tenant_admin(conn, real_tenant_id, env, report, apply=True)
                    _upsert_subscription(conn, real_tenant_id, env, report, apply=True)
                if report.blockers:
                    raise CleanupAbort()
                _ensure_active_superadmin(conn, report)
            except CleanupAbort:
                raise

    except CleanupAbort:
        report.warnings.append("Apply abortado; transaccion revertida.")
    if echo:
        print_report(report)
    return report


def print_report(report: CleanupReport) -> None:
    mode = "apply" if report.apply else "dry-run"
    print("=" * 76)
    print(f"cleanup_beta_test_data.py - reporte ({mode})")
    print("=" * 76)
    print(f"DATABASE_URL={report.database_url_redacted or '[no definida]'}")
    print(f"cleanup_mode={report.mode}")

    def section(title: str, values: list[str]) -> None:
        print(f"\n[{title}]")
        if not values:
            print("  - Ninguno.")
            return
        for value in values:
            print(f"  - {value}")

    print("\n[conteos por tabla]")
    if not report.table_actions:
        print("  - Ninguno.")
    else:
        for item in report.table_actions:
            print(f"  - {item.table}: {item.count} -> {item.action}")

    section("checks OK", report.checks_ok)
    section("acciones que se aplicarian", report.planned_actions)
    section("acciones aplicadas", report.applied_actions)
    section("passwords temporales", report.generated_password_messages)
    section("bloqueantes", report.blockers)
    section("advertencias", report.warnings)
    print(f"\nexit_code={report.exit_code}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Limpia datos de prueba de beta de forma transaccional y segura."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Solo reporta acciones. Default.")
    mode.add_argument("--apply", action="store_true", help="Aplica limpieza con confirmaciones obligatorias.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    apply_changes = bool(args.apply)
    _load_backend_dotenv_if_needed()
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        print("[ERROR] DATABASE_URL es obligatoria.")
        return 2
    try:
        engine = create_engine(database_url)
        report = run_cleanup(engine=engine, env=dict(os.environ), apply=apply_changes, echo=True)
        return report.exit_code
    except SQLAlchemyError as exc:
        print(f"[ERROR] Error de base de datos ejecutando cleanup_beta_test_data: {exc}")
        return 2
    except Exception as exc:
        print(f"[ERROR] Error inesperado ejecutando cleanup_beta_test_data: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
