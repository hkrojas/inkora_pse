# backend/database.py
# PrintFlow SaaS B2B - Multitenancia con filtro global automático
# ================================================================

from contextvars import ContextVar
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from config import settings

# ==========================================
# CONEXIÓN A BASE DE DATOS (Neon PostgreSQL)
# ==========================================

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# ==========================================
# MULTITENANCIA: Variable de Contexto Global
# ==========================================
# Esta ContextVar es thread-safe y async-safe. Cada request de FastAPI
# tiene su propio contexto, por lo que no hay riesgo de cross-tenant leaks.

current_tenant_id: ContextVar[int | None] = ContextVar("current_tenant_id", default=None)

# ==========================================
# FILTRO AUTOMÁTICO DE TENANT (do_orm_execute)
# ==========================================
# Intercepta TODAS las queries ORM (SELECT, UPDATE, DELETE) y, si el modelo
# tiene la columna 'tenant_id', inyecta automáticamente:
#   WHERE tenant_id = <current_tenant_id>
# Esto GARANTIZA aislamiento de datos entre empresas sin modificar cada query.

@event.listens_for(Session, "do_orm_execute")
def _add_tenant_filter(orm_execute_state):
    """Inyecta filtro WHERE tenant_id = X en todas las queries ORM."""
    # Solo aplicar a SELECTs (las escrituras se manejan en CRUD)
    if not orm_execute_state.is_select:
        return

    tenant_id = current_tenant_id.get(None)
    if tenant_id is None:
        return  # Sin tenant activo (ej: login, registro) → no filtrar

    # Iterar sobre las entidades mapeadas en la query
    # y añadir filtro si tienen columna tenant_id
    if orm_execute_state.is_select:
        stmt = orm_execute_state.statement
        # Obtener las entidades del FROM de la query
        for mapper_entity in orm_execute_state.all_mappers:
            mapped_class = mapper_entity.class_
            # Verificar si el modelo tiene columna tenant_id
            if hasattr(mapped_class, "tenant_id"):
                stmt = stmt.filter(mapped_class.tenant_id == tenant_id)
        
        orm_execute_state.statement = stmt


# ==========================================
# DEPENDENCIA FastAPI: get_db()
# ==========================================

def get_db():
    """
    Generador de dependencia para obtener una sesión de SQLAlchemy.
    Se asegura de que la sesión se cierre correctamente después de cada solicitud.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        print(f"ERROR: Excepción durante la sesión de BD, haciendo rollback: {e}")
        db.rollback()
        raise
    finally:
        db.close()
