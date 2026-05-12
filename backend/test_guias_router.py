from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

import crud
import models
from api_dependencies import get_current_user, get_db_tenant
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from routers import guias as guias_router
from services import secret_box
from services.facturacion_service import FacturacionException


def _test_request(path: str = "/guias-remision/1/emitir") -> Request:
    return Request({
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": [],
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
        "scheme": "http",
    })


def _make_user_and_guia(db_session, suffix: str):
    tenant = make_tenant(db_session, suffix)
    tenant.smartpse_company_id = "77"
    tenant.smartpse_environment = "demo"
    tenant.smartpse_usuario_secundaria = "AB3KPQR9"
    tenant.smartpse_token_acceso = "MX7TNVQG"
    tenant.smartpse_gre_sol_username = "SOLUSER"
    tenant.smartpse_gre_sol_password_enc = secret_box.encrypt_secret("sol-password-demo")
    tenant.smartpse_gre_client_id = "client-id"
    tenant.smartpse_gre_client_secret_enc = secret_box.encrypt_secret("client-secret")
    subscription = models.Subscription(
        tenant_id=tenant.id,
        status=models.SUBSCRIPTION_STATUS_ACTIVE,
        beta_feature_flags={"guides": True},
    )
    db_session.add(subscription)
    db_session.commit()
    user = make_user(db_session, tenant, email=f"{suffix.lower()}@test.com")
    cliente = make_cliente(db_session, tenant, suffix)
    quote = make_quote_via_crud(db_session, tenant, user, cliente)
    fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
    guia = crud.create_guia_remision(
        db_session,
        {
            "cotizacion_id": fiscal.id,
            "fecha_traslado": datetime.now(timezone.utc),
            "motivo_traslado": "01",
            "descripcion_motivo": "VENTA",
            "peso_bruto_total": Decimal("5.00"),
            "unidad_medida_peso": "KGM",
            "numero_bultos": 1,
            "modalidad_traslado": "02",
            "conductor_tipo_doc": "1",
            "conductor_nro_doc": "72758912",
            "conductor_nombres": "KENNEDY",
            "conductor_apellidos": "ROJAS",
            "conductor_licencia": "Q12345678",
            "vehiculo_placa": "ABC123",
            "partida_ubigeo": "150101",
            "partida_direccion": "Av. Origen 100",
            "llegada_ubigeo": "150101",
            "llegada_direccion": "Av. Destino 200",
            "items": [
                {
                    "descripcion": "Paquete de prueba",
                    "cantidad": Decimal("2"),
                    "unidad_medida": "NIU",
                    "codigo_producto": "PK-001",
                }
            ],
        },
        user.id,
        tenant.id,
    )
    return user, guia


def _client_for_user(db_session, user):
    app = FastAPI()
    app.include_router(guias_router.router)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_tenant] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _add_guia(db_session, user, estado: str, correlativo: int):
    guia = models.GuiaRemision(
        tenant_id=user.tenant_id,
        usuario_id=user.id,
        serie="T001",
        correlativo=correlativo,
        fecha_emision=datetime.now(timezone.utc),
        fecha_traslado=datetime.now(timezone.utc),
        estado=estado,
        motivo_traslado="01",
        descripcion_motivo="VENTA",
        peso_bruto_total=Decimal("1.00"),
        unidad_medida_peso="KGM",
        modalidad_traslado="02",
        partida_ubigeo="150101",
        partida_direccion=f"Origen {correlativo}",
        llegada_ubigeo="150101",
        llegada_direccion=f"Destino {correlativo}",
    )
    db_session.add(guia)
    db_session.commit()
    db_session.refresh(guia)
    return guia


def test_emitir_guia_propaga_error_fiscal_con_gre_configurada(db_session):
    user, guia = _make_user_and_guia(db_session, "GR01")

    with patch(
        "routers.guias.facturacion_service.emitir_guia_remision",
        side_effect=FacturacionException("Fallo controlado de guia"),
    ):
        with pytest.raises(HTTPException) as exc:
            guias_router.emitir_guia_remision_endpoint(
                _test_request(f"/guias-remision/{guia.id}/emitir"),
                guia.id,
                db_session,
                user,
                mode="sync",
            )

    assert exc.value.status_code == 400
    assert "Fallo controlado de guia" in exc.value.detail
    assert "credenciales SUNAT GRE" not in exc.value.detail


def test_listar_guias_paginado_devuelve_counts_y_filtra_smartpse_por_backend(db_session):
    user, guia = _make_user_and_guia(db_session, "GP01")
    guia.estado = "pendiente_smartpse"
    guia.sunat_ticket = "T001-000001"
    guia.sunat_hash = "hash-smartpse"
    _add_guia(db_session, user, "pendiente", 2)
    _add_guia(db_session, user, "transit", 3)
    _add_guia(db_session, user, "emitida", 4)
    _add_guia(db_session, user, "anulada", 5)

    other_user, _ = _make_user_and_guia(db_session, "GP02")
    _add_guia(db_session, other_user, "pendiente_smartpse", 99)
    db_session.commit()

    client = _client_for_user(db_session, user)

    response = client.get("/guias-remision/", params={"limit": 2, "tab": "all"})

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"items", "total", "skip", "limit", "counts"}
    assert data["total"] == 5
    assert data["skip"] == 0
    assert data["limit"] == 2
    assert len(data["items"]) == 2
    assert data["counts"] == {
        "all": 5,
        "pending": 2,
        "smartpse": 1,
        "transit": 1,
        "emitted": 1,
        "cancelled": 1,
        "voided": 1,
    }

    smartpse_response = client.get(
        "/guias-remision/",
        params={"limit": 15, "tab": "smartpse"},
    )
    assert smartpse_response.status_code == 200
    smartpse_data = smartpse_response.json()
    assert smartpse_data["total"] == 1
    assert smartpse_data["items"][0]["estado"] == "pendiente_smartpse"
    assert smartpse_data["items"][0]["sunat_ticket"] == "T001-000001"

    search_response = client.get(
        "/guias-remision/",
        params={"limit": 15, "q": "Destino 3"},
    )
    assert search_response.status_code == 200
    search_data = search_response.json()
    assert search_data["total"] == 1
    assert search_data["items"][0]["correlativo"] == 3
