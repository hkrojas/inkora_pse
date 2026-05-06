"""
test_user_creation.py — Validaciones globales de email en entorno multi-tenant
=============================================================================
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import crud
import schemas
from conftest import make_tenant, make_user
from database import current_tenant_id


def test_get_user_by_email_global_bypasses_tenant_filter(db_session):
    tenant_a = make_tenant(db_session, "UGE01")
    tenant_b = make_tenant(db_session, "UGE02")
    make_user(db_session, tenant_b, email="shared@test.com")

    token = current_tenant_id.set(tenant_a.id)
    try:
        assert crud.get_user_by_email(db_session, "shared@test.com") is None
        assert crud.get_user_by_email_global(db_session, "shared@test.com") is not None
    finally:
        current_tenant_id.reset(token)


def test_create_user_duplicate_email_raises_value_error_even_with_tenant_context(db_session):
    tenant_a = make_tenant(db_session, "UGE11")
    tenant_b = make_tenant(db_session, "UGE12")
    make_user(db_session, tenant_b, email="duplicate@test.com")

    token = current_tenant_id.set(tenant_a.id)
    try:
        with pytest.raises(ValueError, match="Ya existe un usuario con ese email"):
            crud.create_user(
                db_session,
                schemas.UserRegisterRequest(
                    email="duplicate@test.com",
                    nombre_completo="Duplicado",
                    tenant_id=tenant_a.id,
                ),
                forced_role="vendedor",
            )
    finally:
        current_tenant_id.reset(token)
