from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

import crud
import schemas
from access_control import (
    DOCUMENT_EMITTER_ROLES,
    PAYMENT_MANAGER_ROLES,
    ROLE_ADMIN,
    ROLE_OPERADOR,
    ROLE_SUPERADMIN,
    ROLE_VENDEDOR,
)
from api_dependencies import require_admin, require_document_emitter, require_payment_manager
from database import Base
import models
import tenant_access


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def _create_tenant(db_session, suffix: str, *, is_active: bool = True):
    tenant = models.Tenant(
        business_name=f"Tenant {suffix}",
        business_ruc=f"201000000{suffix.zfill(2)}",
        is_active=is_active,
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


def _create_user(db_session, tenant, *, email: str, rol: str, is_superadmin: bool = False):
    user = models.User(
        email=email,
        hashed_password="hashed",
        nombre_completo=email,
        rol=rol,
        is_superadmin=is_superadmin,
        tenant_id=tenant.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return crud.get_user_by_id(db_session, user.id)


def _create_cliente(db_session, tenant, suffix: str):
    cliente = models.Cliente(
        tenant_id=tenant.id,
        tipo_documento="6",
        numero_documento=f"104000000{suffix.zfill(2)}",
        razon_social=f"Cliente {suffix}",
    )
    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)
    return cliente


def _create_producto(db_session, tenant, suffix: str):
    producto = models.Producto(
        tenant_id=tenant.id,
        nombre=f"Producto {suffix}",
        precio_unitario=Decimal("118.00"),
        valor_unitario=Decimal("100.00"),
        unidad_medida="NIU",
        tipo_afectacion_igv="10",
    )
    db_session.add(producto)
    db_session.commit()
    db_session.refresh(producto)
    return producto


def _create_cotizacion(db_session, tenant, user, cliente, *, total="118.00"):
    cotizacion = models.Cotizacion(
        tenant_id=tenant.id,
        cliente_id=cliente.id,
        usuario_id=user.id,
        fecha_emision=datetime.now(timezone.utc),
        serie="COT",
        correlativo=1,
        total_gravada=Decimal("100.00"),
        total_igv=Decimal("18.00"),
        total_venta=Decimal(total),
        saldo_pendiente=Decimal(total),
    )
    db_session.add(cotizacion)
    db_session.commit()
    db_session.refresh(cotizacion)
    return cotizacion


def test_create_cotizacion_rechaza_cliente_de_otro_tenant(db_session):
    tenant_a = _create_tenant(db_session, "11")
    tenant_b = _create_tenant(db_session, "12")
    usuario_a = _create_user(
        db_session,
        tenant_a,
        email="vendedor-a@test.com",
        rol=ROLE_VENDEDOR,
    )
    cliente_b = _create_cliente(db_session, tenant_b, "21")

    payload = schemas.CotizacionCreate(
        cliente_id=cliente_b.id,
        fecha_vencimiento=None,
        moneda="PEN",
        tipo_comprobante="00",
        items=[
            schemas.CotizacionItemCreate(
                descripcion="Servicio manual",
                cantidad=Decimal("1"),
                precio_unitario=Decimal("118.00"),
            )
        ],
    )

    with pytest.raises(ValueError):
        crud.create_cotizacion(db_session, payload, usuario_a.id, tenant_a.id)


def test_create_cotizacion_rechaza_producto_de_otro_tenant(db_session):
    tenant_a = _create_tenant(db_session, "13")
    tenant_b = _create_tenant(db_session, "14")
    usuario_a = _create_user(
        db_session,
        tenant_a,
        email="vendedor-b@test.com",
        rol=ROLE_VENDEDOR,
    )
    cliente_a = _create_cliente(db_session, tenant_a, "22")
    producto_b = _create_producto(db_session, tenant_b, "31")

    payload = schemas.CotizacionCreate(
        cliente_id=cliente_a.id,
        fecha_vencimiento=None,
        moneda="PEN",
        tipo_comprobante="00",
        items=[
            schemas.CotizacionItemCreate(
                producto_id=producto_b.id,
                descripcion="Producto externo",
                cantidad=Decimal("1"),
                precio_unitario=Decimal("118.00"),
            )
        ],
    )

    with pytest.raises(ValueError):
        crud.create_cotizacion(db_session, payload, usuario_a.id, tenant_a.id)


def test_get_cotizacion_restringe_vendedor_y_habilita_operador(db_session):
    tenant = _create_tenant(db_session, "15")
    owner = _create_user(
        db_session,
        tenant,
        email="owner@test.com",
        rol=ROLE_VENDEDOR,
    )
    other_vendor = _create_user(
        db_session,
        tenant,
        email="other@test.com",
        rol=ROLE_VENDEDOR,
    )
    operador = _create_user(
        db_session,
        tenant,
        email="operador@test.com",
        rol=ROLE_OPERADOR,
    )
    cliente = _create_cliente(db_session, tenant, "23")
    cotizacion = _create_cotizacion(db_session, tenant, owner, cliente)

    assert crud.get_cotizacion(db_session, cotizacion.id, other_vendor) is None
    assert crud.get_cotizacion(db_session, cotizacion.id, owner) is not None
    assert crud.get_cotizacion(db_session, cotizacion.id, operador) is not None


def test_require_admin_y_roles_sensibles(db_session):
    tenant = _create_tenant(db_session, "16")
    vendedor = _create_user(
        db_session,
        tenant,
        email="vendedor@test.com",
        rol=ROLE_VENDEDOR,
    )
    admin = _create_user(
        db_session,
        tenant,
        email="admin@test.com",
        rol=ROLE_ADMIN,
    )
    operador = _create_user(
        db_session,
        tenant,
        email="operador-roles@test.com",
        rol=ROLE_OPERADOR,
    )
    superadmin = _create_user(
        db_session,
        tenant,
        email="superadmin@test.com",
        rol=ROLE_SUPERADMIN,
        is_superadmin=True,
    )

    with pytest.raises(HTTPException) as admin_exc:
        require_admin(vendedor)
    assert admin_exc.value.status_code == 403

    assert require_admin(admin) == admin
    with pytest.raises(HTTPException):
        require_admin(operador)
    assert require_admin(superadmin) == superadmin

    with pytest.raises(HTTPException):
        require_document_emitter(vendedor)
    assert require_document_emitter(admin) == admin
    assert require_document_emitter(operador) == operador
    assert require_document_emitter(superadmin) == superadmin

    with pytest.raises(HTTPException):
        require_payment_manager(vendedor)

    assert require_payment_manager(admin) == admin
    assert require_payment_manager(operador) == operador

    assert ROLE_ADMIN in DOCUMENT_EMITTER_ROLES
    assert ROLE_OPERADOR in DOCUMENT_EMITTER_ROLES
    assert ROLE_ADMIN in PAYMENT_MANAGER_ROLES
    assert ROLE_OPERADOR in PAYMENT_MANAGER_ROLES


def test_tenant_admin_update_permite_identidad_visible_y_bloquea_ruc():
    payload = schemas.TenantAdminUpdate(
        business_name="  Imprenta Demo SAC  ",
        business_address="  Av. Demo 456, Lima  ",
    )

    assert payload.business_name == "Imprenta Demo SAC"
    assert payload.business_address == "Av. Demo 456, Lima"

    with pytest.raises(ValidationError):
        schemas.TenantAdminUpdate(business_ruc="20600000000")

    with pytest.raises(ValidationError):
        schemas.TenantAdminUpdate(business_name=" ", business_address="Av")


def test_usuario_inactivo_queda_bloqueado_para_roles_sensibles(db_session):
    tenant = _create_tenant(db_session, "17", is_active=False)
    suspended_admin = _create_user(
        db_session,
        tenant,
        email="suspended@test.com",
        rol=ROLE_ADMIN,
    )
    suspended_admin = crud.get_user_by_id(db_session, suspended_admin.id)

    with pytest.raises(HTTPException) as exc:
        require_document_emitter(suspended_admin)
    assert exc.value.status_code == 403


def test_get_pagos_cotizacion_filtra_por_tenant(db_session):
    tenant_a = _create_tenant(db_session, "18")
    tenant_b = _create_tenant(db_session, "19")
    user_a = _create_user(
        db_session,
        tenant_a,
        email="pagos-a@test.com",
        rol=ROLE_ADMIN,
    )
    user_b = _create_user(
        db_session,
        tenant_b,
        email="pagos-b@test.com",
        rol=ROLE_ADMIN,
    )
    cliente_a = _create_cliente(db_session, tenant_a, "24")
    cliente_b = _create_cliente(db_session, tenant_b, "25")
    cot_a = _create_cotizacion(db_session, tenant_a, user_a, cliente_a)
    cot_b = _create_cotizacion(db_session, tenant_b, user_b, cliente_b)

    pago_a = models.Pago(
        tenant_id=tenant_a.id,
        cotizacion_id=cot_a.id,
        monto_pagado=Decimal("20.00"),
        metodo_pago="Yape",
    )
    pago_b = models.Pago(
        tenant_id=tenant_b.id,
        cotizacion_id=cot_b.id,
        monto_pagado=Decimal("30.00"),
        metodo_pago="Transferencia",
    )
    db_session.add_all([pago_a, pago_b])
    db_session.commit()

    pagos_a = crud.get_pagos_cotizacion(db_session, cot_a.id, tenant_a.id)
    pagos_b_wrong_tenant = crud.get_pagos_cotizacion(db_session, cot_a.id, tenant_b.id)

    assert len(pagos_a) == 1
    assert pagos_a[0].tenant_id == tenant_a.id
    assert pagos_b_wrong_tenant == []


def test_document_lookup_token_prioriza_dniruc_token_antes_del_token_empresa(monkeypatch):
    tenant = type("TenantStub", (), {"apisperu_token": "tenant-token"})()
    user = type(
        "UserStub",
        (),
        {"tenant": tenant, "apisperu_token": None},
    )()

    monkeypatch.setattr(tenant_access.settings, "DNIRUC_TOKEN", "dniruc-token")
    monkeypatch.setattr(tenant_access.settings, "API_TOKEN", "global-token")

    token = tenant_access.get_document_lookup_token(user)

    assert token == "dniruc-token"


def test_document_lookup_token_usa_token_empresa_si_no_hay_dniruc(monkeypatch):
    tenant = type("TenantStub", (), {"apisperu_token": "tenant-token"})()
    user = type(
        "UserStub",
        (),
        {"tenant": tenant, "apisperu_token": None},
    )()

    monkeypatch.setattr(tenant_access.settings, "DNIRUC_TOKEN", "")
    monkeypatch.setattr(tenant_access.settings, "API_TOKEN", "global-token")

    token = tenant_access.get_document_lookup_token(user)

    assert token == "tenant-token"


def test_company_bank_accounts_usa_solo_datos_del_tenant():
    tenant = type("TenantStub", (), {"bank_accounts": []})()
    user = type(
        "UserStub",
        (),
        {
            "tenant": tenant,
            "bank_accounts": [
                {
                    "banco": "Banco Legacy",
                    "cuenta": "123456",
                }
            ],
        },
    )()

    accounts = tenant_access.get_company_bank_accounts(user)

    assert accounts == []


def test_apisperu_token_ignora_fallback_legacy_de_usuario(monkeypatch):
    tenant = type("TenantStub", (), {"apisperu_token": None})()
    user = type(
        "UserStub",
        (),
        {
            "tenant": tenant,
            "apisperu_token": "legacy-user-token",
        },
    )()

    monkeypatch.setattr(tenant_access.settings, "API_TOKEN", "")

    token = tenant_access.get_apisperu_token(user)

    assert token is None
