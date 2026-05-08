# backend/database.py
# Inkora SaaS B2B - Multitenancia con filtro global automatico
# ================================================================

from contextvars import ContextVar, Token
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from config import settings
from logging_utils import get_logger

# ==========================================
# CONEXION A BASE DE DATOS
# ==========================================


def _strip_internal_database_url_flags(database_url: str) -> str:
    """Remove app-only URL flags before handing the DSN to psycopg2."""
    if "?" not in database_url:
        return database_url

    parsed = urlsplit(database_url)
    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() != "pgbouncer"
    ]
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(query_items, doseq=True),
            parsed.fragment,
        )
    )

engine_kwargs = {
    "pool_pre_ping": settings.DB_POOL_PING,
    "echo": False,
}

if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update(
        {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_timeout": settings.DB_POOL_TIMEOUT_SECONDS,
            "pool_recycle": settings.DB_POOL_RECYCLE_SECONDS,
        }
    )

def _database_url_uses_transaction_pooler(database_url: str) -> bool:
    """Detect Supabase/PgBouncer transaction pooler URLs."""
    normalized = (database_url or "").lower()
    if "pgbouncer" in normalized:
        return True
    parsed = urlsplit(database_url)
    host = (parsed.hostname or "").lower()
    return parsed.port == 6543 or "pooler.supabase.com" in host


# Si la URL apunta al pooler transaccional, no se usan session vars.
# PgBouncer/Supavisor transaction mode no garantiza estado por sesion.
USES_PGBOUNCER = _database_url_uses_transaction_pooler(settings.DATABASE_URL)
USES_SQLITE = settings.DATABASE_URL.startswith("sqlite")

engine = create_engine(
    _strip_internal_database_url_flags(settings.DATABASE_URL),
    **engine_kwargs,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
logger = get_logger(__name__)

# ==========================================
# MULTITENANCIA: Variable de Contexto Global
# ==========================================

current_tenant_id: ContextVar[int | None] = ContextVar(
    "current_tenant_id",
    default=None,
)
SKIP_TENANT_FILTER_OPTION = "skip_tenant_filter"


def activate_tenant_context(tenant_id: int | None) -> Token:
    """Activa el tenant en el contexto async/thread local."""
    return current_tenant_id.set(tenant_id)


def reset_tenant_context(token: Token) -> None:
    """Restaura el contexto tenant previo."""
    current_tenant_id.reset(token)


def apply_tenant_context(db: Session, tenant_id: int) -> Token:
    """Sincroniza tenant_id en ContextVar y en la sesion SQL actual.

    Con PgBouncer en modo transaccional, ``set_config`` no es confiable
    porque cada query puede usar una conexion fisica distinta.
    En ese caso solo se activa el ContextVar (el filtro ``do_orm_execute``
    ya lo lee directamente).
    """
    token = activate_tenant_context(tenant_id)
    if not USES_PGBOUNCER and not USES_SQLITE:
        db.execute(
            text("SELECT set_config('app.current_tenant_id', :tid, true)"),
            {"tid": str(tenant_id)},
        )
    return token


def without_tenant_filter(query):
    """Devuelve un query/statement ORM sin inyeccion automatica de tenant."""
    return query.execution_options(**{SKIP_TENANT_FILTER_OPTION: True})


# ==========================================
# FILTRO AUTOMATICO DE TENANT (do_orm_execute)
# ==========================================

@event.listens_for(Session, "do_orm_execute")
def _add_tenant_filter(orm_execute_state):
    """Inyecta filtro WHERE tenant_id = X en todas las queries ORM."""
    if not orm_execute_state.is_select:
        return
    if orm_execute_state.execution_options.get(SKIP_TENANT_FILTER_OPTION):
        return

    tenant_id = current_tenant_id.get(None)
    if tenant_id is None:
        return

    stmt = orm_execute_state.statement
    for mapper_entity in orm_execute_state.all_mappers:
        mapped_class = mapper_entity.class_
        if hasattr(mapped_class, "tenant_id"):
            stmt = stmt.filter(mapped_class.tenant_id == tenant_id)

    orm_execute_state.statement = stmt


# ==========================================
# DEPENDENCIA FastAPI: get_db()
# ==========================================

def get_db():
    """
    Generador de dependencia para obtener una sesion de SQLAlchemy.
    Se asegura de cerrar la sesion y limpiar el contexto tenant.
    """
    db = SessionLocal()
    tenant_token = activate_tenant_context(None)
    try:
        yield db
    except Exception as exc:
        from fastapi import HTTPException as _HTTPException
        if not isinstance(exc, _HTTPException):
            logger.exception("database_session_error")
            db.rollback()
        raise
    finally:
        try:
            reset_tenant_context(tenant_token)
        except ValueError:
            # El token fue creado en un contexto async diferente (anyio threadpool).
            # En ese caso, simplemente limpiamos el ContextVar en el contexto actual.
            current_tenant_id.set(None)
        db.close()
