"""
test_auth.py — Fase 7: Auth y seguridad
========================================
Cubre:
  - login exitoso y retorno de token JWT
  - login fallido (contraseña incorrecta, email desconocido)
  - token inválido / expirado rechazado por get_current_user
  - tenant suspendido no puede hacer login
  - tenant suspendido bloqueado en rutas protegidas
  - superadmin no bloqueado aunque tenant sea inactivo
  - require_admin / require_document_emitter / require_payment_manager
  - acceso denegado por rol insuficiente

Ejecutar:
    cd backend
    python -m pytest test_auth.py -v
"""
import sys
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from jose import jwt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from conftest import make_tenant, make_user
from access_control import (
    ROLE_ADMIN,
    ROLE_OPERADOR,
    ROLE_SUPERADMIN,
    ROLE_VENDEDOR,
    assert_active_tenant_access,
    assert_login_allowed,
)
from api_dependencies import require_admin, require_document_emitter, require_payment_manager
from config import settings
import security


# ============================================================================
# AUTH: authenticate_user
# ============================================================================

class TestAuthenticateUser:
    """Tests directos de la función authenticate_user de security.py."""

    def test_login_exitoso_retorna_usuario(self, db_session):
        tenant = make_tenant(db_session, "A01")
        user = make_user(db_session, tenant, email="ok@test.com", password="mipassword")

        result = security.authenticate_user(db_session, "ok@test.com", "mipassword")

        assert result is not False
        assert result.email == "ok@test.com"

    def test_login_falla_con_contrasena_incorrecta(self, db_session):
        tenant = make_tenant(db_session, "A02")
        make_user(db_session, tenant, email="user@test.com", password="correcta")

        result = security.authenticate_user(db_session, "user@test.com", "INCORRECTA")

        assert result is False

    def test_login_falla_con_email_desconocido(self, db_session):
        tenant = make_tenant(db_session, "A03")

        result = security.authenticate_user(db_session, "noexiste@test.com", "cualquier")

        assert result is False

    def test_login_falla_con_email_vacio(self, db_session):
        result = security.authenticate_user(db_session, "", "password")
        assert result is False


# ============================================================================
# JWT: creación y decodificación de token
# ============================================================================

class TestJWTCreationAndDecode:
    """Tests de create_access_token_with_claims y validación del token."""

    def test_token_contiene_claims_correctos(self, db_session):
        tenant = make_tenant(db_session, "B01")
        user = make_user(db_session, tenant, email="claims@test.com", rol=ROLE_OPERADOR)

        token = security.create_access_token_with_claims(user)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        assert payload["sub"] == "claims@test.com"
        assert payload["tenant_id"] == tenant.id
        assert payload["rol"] == ROLE_OPERADOR
        assert payload["is_superadmin"] is False

    def test_token_expira_con_delta_negativo(self, db_session):
        tenant = make_tenant(db_session, "B02")
        user = make_user(db_session, tenant, email="exp@test.com")

        # Token con expiración en el pasado
        token = security.create_access_token_with_claims(user, expires_delta=timedelta(seconds=-1))

        with pytest.raises(HTTPException) as exc_info:
            security.get_current_user(db_session, token)
        assert exc_info.value.status_code == 401

    def test_token_invalido_falla_con_401(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            security.get_current_user(db_session, "token.completamente.invalido")
        assert exc_info.value.status_code == 401

    def test_token_firmado_con_clave_diferente_falla(self, db_session):
        tenant = make_tenant(db_session, "B03")
        user = make_user(db_session, tenant, email="fakekey@test.com")

        # Token firmado con clave incorrecta
        bad_token = jwt.encode(
            {"sub": user.email, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            key="clave_incorrecta",
            algorithm=settings.ALGORITHM,
        )

        with pytest.raises(HTTPException) as exc_info:
            security.get_current_user(db_session, bad_token)
        assert exc_info.value.status_code == 401

    def test_token_valido_retorna_usuario(self, db_session):
        tenant = make_tenant(db_session, "B04")
        user = make_user(db_session, tenant, email="valid@test.com")

        token = security.create_access_token_with_claims(user)
        result = security.get_current_user(db_session, token)

        assert result.email == "valid@test.com"


# ============================================================================
# TENANT SUSPENDIDO: bloqueo de acceso
# ============================================================================

class TestTenantSuspendedAccess:
    """Tenant suspendido (is_active=False) debe bloquear login y rutas protegidas."""

    def test_login_bloqueado_si_tenant_suspendido(self, db_session):
        tenant = make_tenant(db_session, "C01", is_active=False)
        user = make_user(db_session, tenant, email="suspended@test.com", password="pass")

        # authenticate_user aún devuelve el usuario (no valida activo)
        authed = security.authenticate_user(db_session, "suspended@test.com", "pass")
        assert authed is not False  # se autenticó con credenciales

        # Pero assert_login_allowed sí debe rechazarlo
        with pytest.raises(HTTPException) as exc_info:
            assert_login_allowed(authed)
        assert exc_info.value.status_code == 403

    def test_assert_active_tenant_access_bloquea_tenant_inactivo(self, db_session):
        tenant = make_tenant(db_session, "C02", is_active=False)
        user = make_user(db_session, tenant, email="inactive@test.com")

        with pytest.raises(HTTPException) as exc_info:
            assert_active_tenant_access(user)
        assert exc_info.value.status_code == 403
        assert "suspendido" in exc_info.value.detail.lower() or "inactivo" in exc_info.value.detail.lower()

    def test_superadmin_no_bloqueado_por_tenant_inactivo(self, db_session):
        tenant = make_tenant(db_session, "C03", is_active=False)
        sa = make_user(
            db_session,
            tenant,
            email="superadmin@test.com",
            rol=ROLE_SUPERADMIN,
            is_superadmin=True,
        )

        # Superadmin pasa el check aunque el tenant esté inactivo
        result = assert_active_tenant_access(sa)
        assert result.email == "superadmin@test.com"

    def test_require_document_emitter_bloquea_tenant_suspendido(self, db_session):
        tenant = make_tenant(db_session, "C04", is_active=False)
        admin = make_user(db_session, tenant, email="emitter@test.com", rol=ROLE_ADMIN)

        with pytest.raises(HTTPException) as exc_info:
            require_document_emitter(admin)
        assert exc_info.value.status_code == 403


# ============================================================================
# ROLES: require_* dependencies
# ============================================================================

class TestRoleRequirements:
    """Dependencias de rol lanzan 403 para roles insuficientes."""

    def _make_active_tenant_with_user(self, db_session, suffix: str, rol: str, is_superadmin: bool = False):
        tenant = make_tenant(db_session, suffix)
        return make_user(db_session, tenant, email=f"{suffix}@test.com", rol=rol, is_superadmin=is_superadmin)

    def test_vendedor_no_puede_emitir_documentos(self, db_session):
        user = self._make_active_tenant_with_user(db_session, "D01", ROLE_VENDEDOR)
        with pytest.raises(HTTPException) as exc_info:
            require_document_emitter(user)
        assert exc_info.value.status_code == 403

    def test_operador_puede_emitir_documentos(self, db_session):
        user = self._make_active_tenant_with_user(db_session, "D02", ROLE_OPERADOR)
        result = require_document_emitter(user)
        assert result.email == "D02@test.com"

    def test_admin_puede_emitir_documentos(self, db_session):
        user = self._make_active_tenant_with_user(db_session, "D03", ROLE_ADMIN)
        result = require_document_emitter(user)
        assert result is not None

    def test_vendedor_no_puede_gestionar_pagos(self, db_session):
        user = self._make_active_tenant_with_user(db_session, "D04", ROLE_VENDEDOR)
        with pytest.raises(HTTPException) as exc_info:
            require_payment_manager(user)
        assert exc_info.value.status_code == 403

    def test_admin_puede_gestionar_pagos(self, db_session):
        user = self._make_active_tenant_with_user(db_session, "D05", ROLE_ADMIN)
        result = require_payment_manager(user)
        assert result is not None

    def test_vendedor_no_puede_acceder_a_admin(self, db_session):
        user = self._make_active_tenant_with_user(db_session, "D06", ROLE_VENDEDOR)
        with pytest.raises(HTTPException) as exc_info:
            require_admin(user)
        assert exc_info.value.status_code == 403

    def test_operador_no_puede_acceder_a_admin(self, db_session):
        user = self._make_active_tenant_with_user(db_session, "D07", ROLE_OPERADOR)
        with pytest.raises(HTTPException) as exc_info:
            require_admin(user)
        assert exc_info.value.status_code == 403

    def test_admin_puede_acceder_a_admin(self, db_session):
        user = self._make_active_tenant_with_user(db_session, "D08", ROLE_ADMIN)
        result = require_admin(user)
        assert result is not None

    def test_superadmin_pasa_todos_los_role_checks(self, db_session):
        user = self._make_active_tenant_with_user(
            db_session, "D09", ROLE_SUPERADMIN, is_superadmin=True
        )
        assert require_admin(user) is not None
        assert require_document_emitter(user) is not None
        assert require_payment_manager(user) is not None


# ============================================================================
# EJECUCIÓN DIRECTA
# ============================================================================

if __name__ == "__main__":
    import pytest as _pytest
    _pytest.main([__file__, "-v", "--tb=short"])
