"""crud/clientes.py — CRUD de Clientes."""
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

import models
import schemas
from crud._base import get_cliente_for_tenant


def count_clientes(
    db: Session,
    tenant_id: int | None = None,
    q: str | None = None,
) -> int:
    query = db.query(func.count(models.Cliente.id))
    if tenant_id is not None:
        query = query.filter(models.Cliente.tenant_id == tenant_id)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                models.Cliente.razon_social.ilike(term),
                models.Cliente.numero_documento.ilike(term),
                models.Cliente.nombre_comercial.ilike(term),
                models.Cliente.contacto.ilike(term),
            )
        )
    return query.scalar() or 0


def get_clientes(
    db: Session,
    tenant_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    q: str | None = None,
):
    query = db.query(models.Cliente)
    if tenant_id is not None:
        query = query.filter(models.Cliente.tenant_id == tenant_id)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                models.Cliente.razon_social.ilike(term),
                models.Cliente.numero_documento.ilike(term),
                models.Cliente.nombre_comercial.ilike(term),
                models.Cliente.contacto.ilike(term),
            )
        )
    return query.order_by(models.Cliente.razon_social).offset(skip).limit(limit).all()


def create_cliente(db: Session, cliente: schemas.ClienteCreate, tenant_id: int):
    db_cliente = models.Cliente(**cliente.model_dump(), tenant_id=tenant_id)
    try:
        db.add(db_cliente)
        db.commit()
        db.refresh(db_cliente)
        return db_cliente
    except Exception as e:
        db.rollback()
        raise e


def create_clientes_bulk(
    db: Session,
    clientes: list[schemas.ClienteCreate],
    tenant_id: int,
) -> list[models.Cliente]:
    db_clientes = [
        models.Cliente(**cliente.model_dump(), tenant_id=tenant_id)
        for cliente in clientes
    ]
    if not db_clientes:
        return []
    try:
        db.add_all(db_clientes)
        db.commit()
        return db_clientes
    except Exception as e:
        db.rollback()
        raise e


def update_cliente(db: Session, cliente_id: int, cliente_data: schemas.ClienteCreate, tenant_id: int):
    db_cliente = get_cliente_for_tenant(db, cliente_id, tenant_id)
    if db_cliente:
        for key, value in cliente_data.model_dump().items():
            setattr(db_cliente, key, value)
        db.commit()
        db.refresh(db_cliente)
    return db_cliente


def patch_cliente(db: Session, cliente_id: int, updates: dict, tenant_id: int):
    db_cliente = get_cliente_for_tenant(db, cliente_id, tenant_id)
    if not db_cliente:
        return None
    for key, value in updates.items():
        setattr(db_cliente, key, value)
    db.commit()
    db.refresh(db_cliente)
    return db_cliente


def delete_cliente(db: Session, cliente_id: int, tenant_id: int):
    db_cliente = get_cliente_for_tenant(db, cliente_id, tenant_id)
    if db_cliente:
        db.delete(db_cliente)
        db.commit()
    return db_cliente
