from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

import models
from conftest import make_tenant
from database import get_db
from main import app
from rate_limit import limiter


@pytest.fixture(autouse=True)
def reset_public_lookup_rate_limit():
    limiter.reset()
    yield
    limiter.reset()


def _client(db_session) -> TestClient:
    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def _document(
    db,
    tenant,
    *,
    tipo_comprobante="01",
    document_kind="fiscal_document",
    serie="F001",
    correlativo=184,
    estado="facturada",
    total="498.00",
    sunat_error=None,
    with_cdr=True,
):
    document = models.Cotizacion(
        tenant_id=tenant.id,
        serie=serie,
        correlativo=correlativo,
        fecha_emision=datetime(2026, 7, 18, 10, 30),
        moneda="PEN",
        estado=estado,
        document_kind=document_kind,
        tipo_comprobante=tipo_comprobante,
        total_gravada=Decimal("422.03"),
        total_igv=Decimal("75.97"),
        total_venta=Decimal(total),
        sunat_pdf_url="cotizaciones/demo.pdf",
        sunat_xml_content="<Invoice />",
        sunat_cdr_content="cdr-demo" if with_cdr else None,
        sunat_error=sunat_error,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def _payload(**overrides):
    payload = {
        "ruc": "20123400001",
        "tipo_comprobante": "01",
        "serie": "F001",
        "correlativo": "00000184",
        "fecha_emision": "2026-07-18",
        "importe_total": "498.00",
    }
    payload.update(overrides)
    return payload


def test_public_lookup_returns_only_safe_fiscal_data(db_session):
    tenant = make_tenant(db_session, "00001")
    _document(db_session, tenant)

    with _client(db_session) as client:
        response = client.post("/public/comprobantes/consulta", json=_payload())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "encontrado": True,
        "emisor": tenant.business_name,
        "tipo_comprobante": "01",
        "numero": "F001-00000184",
        "fecha_emision": "2026-07-18",
        "moneda": "PEN",
        "importe_total": "498.00",
        "estado": "ACEPTADO",
        "evidencias": {"pdf": True, "xml": True, "cdr": True},
    }
    serialized = response.text
    assert "cliente" not in serialized
    assert "sunat_cdr_content" not in serialized
    assert "sunat_pdf_url" not in serialized
    assert "tenant_id" not in serialized


def test_public_lookup_never_crosses_tenants(db_session):
    first_tenant = make_tenant(db_session, "00001")
    second_tenant = make_tenant(db_session, "00002")
    _document(db_session, first_tenant)
    _document(db_session, second_tenant, total="780.00")

    with _client(db_session) as client:
        mismatch = client.post(
            "/public/comprobantes/consulta",
            json=_payload(ruc=second_tenant.business_ruc, importe_total="498.00"),
        )
        match = client.post(
            "/public/comprobantes/consulta",
            json=_payload(ruc=second_tenant.business_ruc, importe_total="780.00"),
        )
    app.dependency_overrides.clear()

    assert mismatch.status_code == 404
    assert mismatch.headers["cache-control"] == "no-store"
    assert match.status_code == 200
    assert match.json()["emisor"] == second_tenant.business_name


def test_public_lookup_supports_invoice_receipt_and_related_notes(db_session):
    tenant = make_tenant(db_session, "00001")
    variants = [
        ("01", "fiscal_document", "F001", 184),
        ("03", "fiscal_document", "B001", 185),
        ("07", "credit_note", "FC01", 186),
        ("08", "debit_note", "FD01", 187),
    ]
    for tipo, kind, serie, correlativo in variants:
        _document(
            db_session,
            tenant,
            tipo_comprobante=tipo,
            document_kind=kind,
            serie=serie,
            correlativo=correlativo,
        )

    with _client(db_session) as client:
        for tipo, _, serie, correlativo in variants:
            response = client.post(
                "/public/comprobantes/consulta",
                json=_payload(
                    tipo_comprobante=tipo,
                    serie=serie,
                    correlativo=str(correlativo),
                ),
            )
            assert response.status_code == 200
            assert response.json()["tipo_comprobante"] == tipo
    app.dependency_overrides.clear()


def test_public_lookup_excludes_quotes_and_uses_generic_not_found(db_session):
    tenant = make_tenant(db_session, "00001")
    _document(
        db_session,
        tenant,
        tipo_comprobante="01",
        document_kind="quotation",
    )

    with _client(db_session) as client:
        response = client.post("/public/comprobantes/consulta", json=_payload())
    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {
        "detail": "No encontramos un comprobante que coincida con todos los datos."
    }


def test_public_lookup_maps_voided_rejected_and_pending_states(db_session):
    tenant = make_tenant(db_session, "00001")
    variants = [
        ("F001", 181, "anulada", None, True, "ANULADO"),
        ("F002", 182, "pendiente", "Rechazado por SUNAT", False, "RECHAZADO"),
        ("F003", 183, "pendiente", None, False, "EN_PROCESO"),
    ]
    for serie, correlativo, estado, error, with_cdr, _ in variants:
        _document(
            db_session,
            tenant,
            serie=serie,
            correlativo=correlativo,
            estado=estado,
            sunat_error=error,
            with_cdr=with_cdr,
        )

    with _client(db_session) as client:
        for serie, correlativo, _, _, _, expected in variants:
            response = client.post(
                "/public/comprobantes/consulta",
                json=_payload(serie=serie, correlativo=str(correlativo)),
            )
            assert response.status_code == 200
            assert response.json()["estado"] == expected
    app.dependency_overrides.clear()


def test_public_lookup_rejects_unsupported_documents_and_extra_fields(db_session):
    with _client(db_session) as client:
        unsupported = client.post(
            "/public/comprobantes/consulta",
            json=_payload(tipo_comprobante="09"),
        )
        extra_field = client.post(
            "/public/comprobantes/consulta",
            json={**_payload(), "tenant_id": 99},
        )
        zero_correlativo = client.post(
            "/public/comprobantes/consulta",
            json=_payload(correlativo="0"),
        )
    app.dependency_overrides.clear()

    assert unsupported.status_code == 422
    assert extra_field.status_code == 422
    assert zero_correlativo.status_code == 422


def test_public_lookup_is_rate_limited(db_session):
    with _client(db_session) as client:
        responses = [
            client.post("/public/comprobantes/consulta", json=_payload())
            for _ in range(11)
        ]
    app.dependency_overrides.clear()

    assert responses[9].status_code == 404
    assert responses[10].status_code == 429
