# backend/database.py
# PrintFlow SaaS B2B - Multitenancia con filtro global automatico
# ================================================================

from contextvars import ContextVar, Token

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from config import settings
from logging_utils import get_logger

# ==========================================
# CONEXION A BASE DE DATOS
# ==========================================

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
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


def activate_tenant_context(tenant_id: int | None) -> Token:
    """Activa el tenant en el contexto async/thread local."""
    return current_tenant_id.set(tenant_id)


def reset_tenant_context(token: Token) -> None:
    """Restaura el contexto tenant previo."""
    current_tenant_id.reset(token)


def apply_tenant_context(db: Session, tenant_id: int) -> Token:
    """Sincroniza tenant_id en ContextVar y en la sesion SQL actual."""
    token = activate_tenant_context(tenant_id)
    db.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
        {"tid": str(tenant_id)},
    )
    return token


# ==========================================
# FILTRO AUTOMATICO DE TENANT (do_orm_execute)
# ==========================================

@event.listens_for(Session, "do_orm_execute")
def _add_tenant_filter(orm_execute_state):
    """Inyecta filtro WHERE tenant_id = X en todas las queries ORM."""
    if not orm_execute_state.is_select:
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
    except Exception:
        logger.exception("database_session_error")
        db.rollback()
        raise
    finally:
        reset_tenant_context(tenant_token)
        db.close()
