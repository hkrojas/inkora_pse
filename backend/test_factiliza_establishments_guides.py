from datetime import datetime, timedelta, timezone
from decimal import Decimal

import crud
import models
import schemas
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from schemas.inventory import WarehouseCreate, WarehouseUpdate
from services import factiliza_lookup_service, inventory_service, sale_dispatch_service


def _snapshot(address="AV. PRINCIPAL 100, LIMA - LIMA - LIMA"):
    return [
        {
            "sunat_code": "0000",
            "name": "Establecimiento principal",
            "ubigeo": "150101",
            "address": address,
            "is_main": True,
        },
        {
            "sunat_code": "0002",
            "name": "SU. SUCURSAL",
            "ubigeo": "150103",
            "address": "AV. ANEXO 200, LIMA - LIMA - ATE",
            "is_main": False,
        },
    ]


def test_factiliza_lookup_normalizes_main_and_annexes(monkeypatch):
    company = {
        "numero": "20606751509",
        "direccion_completa": "AV. PRINCIPAL 100, LIMA - LIMA - LIMA",
        "ubigeo_sunat": "150101",
    }
    annexes = [{
        "codigo": "2",
        "tipo_establecimiento": "SU. SUCURSAL",
        "direccion_completa": "AV. ANEXO 200, LIMA - LIMA - ATE",
        "ubigeo_sunat": "150103",
    }]

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    responses = iter([company, annexes])
    monkeypatch.setattr(factiliza_lookup_service.settings, "FACTILIZA_API_TOKEN", "test-token")
    monkeypatch.setattr(factiliza_lookup_service.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        factiliza_lookup_service,
        "_request",
        lambda *_args, **_kwargs: next(responses),
    )

    locations = factiliza_lookup_service.fetch_company_locations("20606751509")

    assert [row["sunat_code"] for row in locations] == ["0000", "0002"]
    assert locations[0]["is_main"] is True
    assert locations[1]["ubigeo"] == "150103"


def test_factiliza_lookup_treats_missing_annexes_as_empty():
    class FakeResponse:
        status_code = 404

        @staticmethod
        def json():
            return {
                "message": "No hay anexos registrados con el número de RUC 20606751509",
                "data": None,
            }

    class FakeClient:
        @staticmethod
        def get(_path):
            return FakeResponse()

    result = factiliza_lookup_service._request(
        FakeClient(),
        "/ruc/anexo/20606751509",
        empty_annexes_on_not_found=True,
    )

    assert result == []


def test_sync_is_idempotent_and_shared_warehouse_does_not_mutate_fiscal_identity(db_session):
    tenant = make_tenant(db_session, "90001")
    user = make_user(db_session, tenant, email="factiliza-sync@test.pe")
    default = models.Warehouse(
        tenant_id=tenant.id,
        code="PRINCIPAL",
        name="Almacén principal",
        is_default=True,
        is_active=True,
    )
    db_session.add(default)
    db_session.commit()

    first = inventory_service.sync_factiliza_establishments(
        db_session, tenant.id, tenant.business_ruc, _snapshot(), user_id=user.id
    )
    second = inventory_service.sync_factiliza_establishments(
        db_session, tenant.id, tenant.business_ruc, _snapshot(), user_id=user.id
    )

    assert first["establishments_created"] == 2
    assert first["warehouses_created"] == 1
    assert first["warehouses_linked"] == 1
    assert second["establishments_created"] == 0
    assert db_session.query(models.TenantEstablishment).filter_by(tenant_id=tenant.id).count() == 2
    assert db_session.query(models.Warehouse).filter_by(tenant_id=tenant.id).count() == 2

    main = db_session.query(models.TenantEstablishment).filter_by(
        tenant_id=tenant.id, sunat_code="0000"
    ).one()
    shared = inventory_service.create_warehouse(
        db_session,
        tenant.id,
        WarehouseCreate(
            code="STAND-02",
            name="Stand segundo piso",
            location="Interior 202",
            establishment_id=main.id,
        ),
    )
    inventory_service.update_warehouse(
        db_session,
        tenant.id,
        shared.id,
        WarehouseUpdate(
            name="Stand renovado",
            location="Interior 204",
            establishment_id=main.id,
        ),
    )
    db_session.refresh(main)
    assert main.name == "Establecimiento principal"
    assert main.address == "AV. PRINCIPAL 100, LIMA - LIMA - LIMA"
    assert main.verified_at is not None


def test_tenant_onboarding_persists_factiliza_snapshot_in_same_transaction(db_session):
    tenant = crud.create_tenant(
        db_session,
        schemas.TenantCreate(
            business_name="Empresa onboarding",
            business_ruc="20606751509",
            business_address="Dirección ingresada",
        ),
        factiliza_locations=_snapshot(),
    )

    warehouses = db_session.query(models.Warehouse).filter_by(tenant_id=tenant.id).all()
    establishments = db_session.query(models.TenantEstablishment).filter_by(tenant_id=tenant.id).all()
    assert len(warehouses) == 2
    assert len(establishments) == 2
    assert next(row for row in warehouses if row.is_default).establishment.sunat_code == "0000"


def test_sales_guide_uses_persisted_source_establishment(db_session):
    tenant = make_tenant(db_session, "90002")
    user = make_user(db_session, tenant, email="factiliza-guide@test.pe")
    client = make_cliente(db_session, tenant, "90002")
    quote = make_quote_via_crud(db_session, tenant, user, client)
    invoice = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
    invoice.estado = "facturada"
    invoice.sunat_cdr_content = "<ApplicationResponse/>"
    invoice.provider_verification_status = "verified"
    default = models.Warehouse(
        tenant_id=tenant.id,
        code="PRINCIPAL",
        name="Almacén principal",
        is_default=True,
        is_active=True,
    )
    db_session.add(default)
    db_session.flush()
    invoice.warehouse_id = default.id
    db_session.commit()
    inventory_service.sync_factiliza_establishments(
        db_session, tenant.id, tenant.business_ruc, _snapshot(), user_id=user.id
    )

    context = sale_dispatch_service.get_sales_document_dispatch_context(
        db_session, tenant.id, invoice.id
    )
    assert context["source_location"]["ready"] is True
    assert context["source_location"]["establishment"]["sunat_code"] == "0000"

    payload = schemas.SaleDispatchFromDocumentCreate(
        fiscal_document_id=invoice.id,
        idempotency_key="factiliza-guide-source-0001",
        fecha_traslado=datetime.now(timezone.utc) + timedelta(days=1),
        peso_bruto_total=Decimal("1.000"),
        modalidad_traslado="02",
        partida_ubigeo="999999",
        partida_direccion="ORIGEN NO AUTORIZADO",
        llegada_ubigeo="150103",
        llegada_direccion="AV. DESTINO 200",
        vehiculo_placa="ABC123",
        conductor_nro_doc="72758912",
        conductor_nombres="ANA",
        conductor_apellidos="ROJAS",
        conductor_licencia="Q12345678",
        lines=[schemas.DispatchLineSelection(
            fiscal_document_item_id=invoice.items[0].id,
            quantity=Decimal("1"),
            confirmed_as_goods=True,
        )],
    )
    dispatch, _ = sale_dispatch_service.create_from_document(
        db_session, tenant.id, user.id, payload
    )
    guide = dispatch.guides[0]
    assert guide.partida_codigo_local == "0000"
    assert guide.partida_ubigeo == "150101"
    assert guide.partida_direccion == "AV. PRINCIPAL 100, LIMA - LIMA - LIMA"
    assert sale_dispatch_service.validate_guide_for_emission(db_session, guide)["valid"] is True

    invoice.warehouse_id = None
    dispatch.warehouse_id = None
    db_session.commit()
    validation = sale_dispatch_service.validate_guide_for_emission(db_session, guide)
    assert any(error["code"] == "SOURCE_ESTABLISHMENT_REQUIRED" for error in validation["errors"])
