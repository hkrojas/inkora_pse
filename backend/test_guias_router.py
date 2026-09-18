import base64
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import FastAPI
from fastapi.testclient import TestClient

import crud
import models
import schemas
from api_dependencies import (
    get_current_user,
    get_db_tenant,
    require_document_emitter,
    require_emission_allowed,
)
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from routers import guias as guias_router
from services import sale_dispatch_service


def _make_user_and_guia(db_session, suffix: str):
    tenant = make_tenant(db_session, suffix)
    tenant.smartpse_company_id = "77"
    tenant.smartpse_environment = "demo"
    tenant.smartpse_usuario_secundaria = "AB3KPQR9"
    tenant.smartpse_token_acceso = "MX7TNVQG"
    tenant.smartpse_gre_sol_username = "SOLUSER"
    tenant.smartpse_gre_sol_password_enc = "sol-password-demo"
    tenant.smartpse_gre_client_id = "client-id"
    tenant.smartpse_gre_client_secret_enc = "client-secret"
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
    fiscal.estado = "facturada"
    fiscal.sunat_cdr_content = "<ApplicationResponse/>"
    fiscal.provider_verification_status = "verified"
    db_session.commit()
    dispatch, _ = sale_dispatch_service.create_from_invoice(
        db_session, tenant.id, user.id,
        schemas.SaleDispatchFromInvoiceCreate(
            fiscal_document_id=fiscal.id,
            idempotency_key=f"router-{suffix}-dispatch",
            fecha_traslado=datetime.now(timezone.utc),
            peso_bruto_total=Decimal("5.00"),
            numero_bultos=1,
            modalidad_traslado="02",
            conductor_tipo_doc="1",
            conductor_nro_doc="72758912",
            conductor_nombres="KENNEDY",
            conductor_apellidos="ROJAS",
            conductor_licencia="Q12345678",
            vehiculo_placa="ABC123",
            partida_ubigeo="150101",
            partida_direccion="Av. Origen 100",
            llegada_ubigeo="150101",
            llegada_direccion="Av. Destino 200",
            lines=[schemas.DispatchLineSelection(
                fiscal_document_item_id=fiscal.items[0].id,
                quantity=fiscal.items[0].cantidad,
                confirmed_as_goods=True,
            )],
        ),
    )
    guia = dispatch.guides[0]
    return user, guia


def _client_for_user(db_session, user):
    app = FastAPI()
    app.include_router(guias_router.router)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_tenant] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_document_emitter] = lambda: user
    app.dependency_overrides[require_emission_allowed] = lambda: user
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


def test_emitir_guia_bloquea_reemision_desde_estado_fiscal(db_session):
    user, guia = _make_user_and_guia(db_session, "GR01")
    guia.estado = "pendiente_smartpse"
    db_session.commit()

    response = _client_for_user(db_session, user).post(
        f"/guias-remision/{guia.id}/emitir",
        params={"mode": "async"},
    )

    assert response.status_code == 400
    assert "conciliar sin reenviar" in response.json()["detail"]


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


def test_descargas_gre_son_aisladas_por_tenant_y_exponen_cdr(db_session):
    user, guia = _make_user_and_guia(db_session, "GART01")
    cdr_xml = "<ApplicationResponse>aceptada</ApplicationResponse>"
    guia.sunat_xml_content = "<DespatchAdvice/>"
    guia.provider_response = {
        "cdr": base64.b64encode(cdr_xml.encode("utf-8")).decode("ascii"),
    }
    db_session.commit()
    client = _client_for_user(db_session, user)

    detail = client.get(f"/guias-remision/{guia.id}")
    assert detail.status_code == 200
    assert detail.json()["cdr_disponible"] is True

    cdr = client.get(f"/guias-remision/{guia.id}/cdr")
    assert cdr.status_code == 200
    assert cdr.content.decode("utf-8") == cdr_xml
    assert "attachment" in cdr.headers["content-disposition"]

    xml = client.get(f"/guias-remision/{guia.id}/xml")
    assert xml.status_code == 200
    assert xml.content.decode("utf-8") == "<DespatchAdvice/>"

    other_user, _ = _make_user_and_guia(db_session, "GART02")
    other_client = _client_for_user(db_session, other_user)
    assert other_client.get(f"/guias-remision/{guia.id}/cdr").status_code == 404


def test_emitir_guia_solo_acepta_cola_asincrona_e_idempotente(db_session):
    user, guia = _make_user_and_guia(db_session, "GQUEUE01")
    client = _client_for_user(db_session, user)

    sync_response = client.post(f"/guias-remision/{guia.id}/emitir", params={"mode": "sync"})
    assert sync_response.status_code == 400
    assert "exclusivamente por cola" in sync_response.json()["detail"]

    first = client.post(f"/guias-remision/{guia.id}/emitir", params={"mode": "async"})
    second = client.post(f"/guias-remision/{guia.id}/emitir", params={"mode": "async"})
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["job_id"] == second.json()["job_id"]


def test_detalle_guia_expone_acciones_y_recupera_job(db_session):
    user, guia = _make_user_and_guia(db_session, "GDETAIL01")
    client = _client_for_user(db_session, user)

    detail = client.get(f"/guias-remision/{guia.id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["dispatch_id"] == guia.dispatch_id
    assert body["dispatch_status"] == models.DISPATCH_STATUS_DRAFT
    assert body["reservation_status"] == models.DISPATCH_RESERVATION_ACTIVE
    assert body["actions"]["edit"]["enabled"] is True
    assert body["actions"]["validate"]["enabled"] is True
    assert body["actions"]["emit"]["enabled"] is True
    assert body["actions"]["consult"]["enabled"] is False
    assert body["emission_job"] is None

    queued = client.post(f"/guias-remision/{guia.id}/emitir", params={"mode": "async"})
    assert queued.status_code == 202
    refreshed = client.get(f"/guias-remision/{guia.id}").json()
    assert refreshed["emission_job"]["id"] == queued.json()["job_id"]
    assert refreshed["emission_job"]["status"] in {"queued", "contingency_pending"}
    assert refreshed["actions"]["edit"]["enabled"] is False
