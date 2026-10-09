"""Exact fiscal-note read contracts and budgets, on SQLite and optional local PG."""
from datetime import datetime
import hashlib
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import joinedload

import models
import schemas
from conftest import make_cliente, make_tenant, make_user
from test_read_egress import db_session, statements  # noqa: F401; isolated dual-engine fixture
from routers import facturacion as router


@pytest.fixture
def notes(db_session):
    db = db_session
    tenant = make_tenant(db, "NRD")
    user = make_user(db, tenant, email="notes-read@test.local")
    client = make_cliente(db, tenant, "NRD", numero_documento="20123456781")
    source = models.Cotizacion(tenant_id=tenant.id, usuario_id=user.id, cliente_id=client.id,
        serie="COT", correlativo=7, document_kind="quotation", estado="pendiente", tipo_comprobante="00",
        sunat_xml_content="q" * 50000, sunat_cdr_content="r" * 50000,
        provider_response={"unused": "x" * 50000})
    reference = models.Cotizacion(tenant_id=tenant.id, usuario_id=user.id, cliente_id=client.id,
        serie="F001", correlativo=1234567, document_kind="fiscal_document", estado="facturada", tipo_comprobante="01",
        sunat_xml_url="https://example.test/xml", sunat_cdr_content="c" * 50000,
        provider_verification_status="verified")
    db.add_all([source, reference])
    db.flush()
    cases = [
        ("borrador", None, None, None, None, None),
        ("pendiente", "pending_confirmation", "áñ😀" * 10000, None, "valid", None),
        ("pendiente", "pending_confirmation", "áñ😀" * 10000, None, "wrong", None),
        ("facturada", "verified", "xml", "cdr", None, None),
        ("anulada", "verified", "xml", "cdr", "valid", None),
        ("pendiente", "rejected", "xml", None, "valid", "rechazado"),
        ("pendiente", "", "", "", None, ""),
        ("pendiente", None, None, None, None, "consulta pendiente"),
        ("pendiente", "verified", "xml", None, "valid", None),
        ("facturada", "verified", None, "url", None, None),
        ("pendiente", "processing", "xml", "cdr", None, None),
        ("pendiente", None, " ", None, "valid", None),
    ]
    for i, (state, verification, xml, cdr, evidence, error) in enumerate(cases):
        fingerprint = hashlib.sha256(xml.encode()).hexdigest() if evidence == "valid" else evidence
        db.add(models.Cotizacion(tenant_id=tenant.id, usuario_id=user.id, cliente_id=client.id,
            source_quote_id=source.id if i else None, nota_referencia_id=reference.id if i else None,
            serie="FC01" if i % 2 == 0 else "FD01", correlativo=i+1,
            document_kind="credit_note" if i % 2 == 0 else "debit_note", tipo_comprobante="07" if i % 2 == 0 else "08",
            fecha_emision=datetime(2026, 9, i+1), estado=state, provider_verification_status=verification,
            sunat_xml_content=xml, sunat_cdr_content=cdr if cdr != "url" else None,
            sunat_cdr_url="https://example.test/cdr" if cdr == "url" else None,
            sunat_xml_url="https://example.test/xml" if cdr == "url" else None,
            provider_response={"inkora_evidence": {"signed_xml_sha256": fingerprint}, "large": "x" * 50000},
            sunat_error=error, nota_motivo_codigo="01", nota_motivo_descripcion="Ajuste contractual",
            sunat_qr_svg="q" * 50000))
    db.commit()
    scope = SimpleNamespace(id=user.id, tenant_id=tenant.id, rol=user.rol, is_superadmin=False)
    db.expunge_all()
    return scope


def note_page(db, user, **overrides):
    params = dict(skip=0, limit=15, tipo_nota=None, tab="all", estado=None, desde=None, hasta=None, q=None)
    params.update(overrides)
    return router.list_notas_page(db=db, current_user=user, **params)


@pytest.mark.parametrize("tab", ["all", "draft", "emitted", "pending", "rejected", "voided"])
@pytest.mark.parametrize("skip,limit", [(0, 15), (10, 100), (100, 15)])
def test_note_page_exact_legacy_contract_and_two_queries(db_session, notes, tab, skip, limit):
    db = db_session
    base = db.query(models.Cotizacion).filter(models.Cotizacion.tenant_id == notes.tenant_id,
        models.Cotizacion.document_kind.in_(["credit_note", "debit_note"]))
    counts = router._fiscal_doc_counts(base)
    filtered = base.filter(router._fiscal_doc_tab_filter(tab)) if tab != "all" else base
    legacy = filtered.options(joinedload(models.Cotizacion.cliente), joinedload(models.Cotizacion.source_quote),
        joinedload(models.Cotizacion.nota_referencia)).order_by(models.Cotizacion.id.desc()).offset(skip).limit(limit).all()
    expected = [schemas.FiscalNoteListResponse.model_validate(row).model_dump(mode="json") for row in legacy]
    db.expunge_all()
    with statements(db) as sql:
        result = schemas.FiscalNotePageResponse.model_validate(note_page(db, notes, tab=tab, skip=skip, limit=limit)).model_dump(mode="json")
    assert result == dict(items=expected, total=counts[tab], counts=counts, skip=skip, limit=limit)
    assert len(sql) == 2
    assert "sunat_qr_svg" not in sql[1]
    assert "cotizacion_items" not in sql[1]
    assert len(db.identity_map) == 0  # Neither notes nor related documents become ORM entities.


def test_note_filters_http_limits_and_tenant_scope(db_session, notes):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from api_dependencies import get_current_user, get_db_tenant
    db = db_session
    other = make_tenant(db, "NRDX")
    other_user = make_user(db, other, email="notes-other@test.local")
    other_client = make_cliente(db, other, "NRDX", numero_documento="20987654321")
    foreign = models.Cotizacion(tenant_id=other.id, usuario_id=other_user.id, cliente_id=other_client.id,
        serie="FX01", correlativo=1, document_kind="credit_note", tipo_comprobante="07", estado="pendiente")
    db.add(foreign)
    db.commit()
    for filters, total in [({"tipo_nota": "credito"}, 6), ({"tipo_nota": "08"}, 6),
        ({"tipo_nota": "nc"}, 6), ({"tipo_nota": "nd"}, 6), ({"tipo_nota": "07"}, 6), ({"tipo_nota": "debito"}, 6),
        ({"estado": "anulada"}, 1), ({"q": "Ajuste contractual"}, 12), ({"q": "20123456781"}, 12),
        ({"q": "FX01"}, 0), ({"q": "not-found"}, 0),
        ({"desde": "2026-09-03", "hasta": "2026-09-05"}, 3)]:
        with statements(db) as sql:
            result = note_page(db, notes, **filters)
        assert result["total"] == total
        assert len(sql) == 2

    app = FastAPI()
    app.include_router(router.router)
    app.dependency_overrides[get_db_tenant] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: notes
    with TestClient(app) as client:
        for limit in (15, 100):
            with statements(db) as sql:
                response = client.get(f"/notas/page?limit={limit}")
            assert response.status_code == 200
            assert response.json()["total"] == 12
            assert len(sql) == 2
        assert client.get("/notas/page").json()["limit"] == 15
        assert client.get("/notas/page?limit=101").status_code == 422
        assert client.get("/notas/page?desde=invalid").status_code == 400

    own = db.query(models.Cotizacion).filter_by(tenant_id=notes.tenant_id, serie="FC01").first()
    own.cliente_id = other_client.id
    own.source_quote_id = foreign.id
    own.nota_referencia_id = foreign.id
    own_id = own.id
    db.commit()
    db.expunge_all()
    with statements(db) as sql:
        page = note_page(db, notes)
    projected = next(item for item in page["items"] if item.id == own_id)
    assert projected.cliente is projected.source_quote is projected.nota_referencia is None
    assert len(sql) == 2
    assert note_page(db, notes, q="20987654321")["total"] == 0
