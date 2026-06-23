import asyncio

import pytest

from conftest import make_cliente, make_cotizacion, make_tenant, make_user
from routers import facturacion as facturacion_router
import schemas
from services.document_flow_service import (
    DOCUMENT_KIND_CREDIT_NOTE,
    DOCUMENT_KIND_FISCAL_DOCUMENT,
)


def _numbered(db, doc, serie: str, correlativo: int):
    doc.serie = serie
    doc.correlativo = correlativo
    db.commit()
    db.refresh(doc)
    return doc


def test_facturas_emitidas_page_filtra_tipo_conteos_y_tenant(db_session):
    tenant = make_tenant(db_session, "FP01")
    other_tenant = make_tenant(db_session, "FP02")
    user = make_user(db_session, tenant, email="fiscal-page@test.com")
    cliente = make_cliente(db_session, tenant, "FP01")
    other_user = make_user(db_session, other_tenant, email="other-fiscal@test.com")
    other_cliente = make_cliente(db_session, other_tenant, "FP02")

    emitted = _numbered(db_session, make_cotizacion(
        db_session,
        tenant,
        user,
        cliente,
        document_kind=DOCUMENT_KIND_FISCAL_DOCUMENT,
        tipo_comprobante="01",
        estado="facturada",
    ), "F001", 1)
    emitted.sunat_cdr_content = "<ApplicationResponse/>"
    pending = _numbered(db_session, make_cotizacion(
        db_session,
        tenant,
        user,
        cliente,
        document_kind=DOCUMENT_KIND_FISCAL_DOCUMENT,
        tipo_comprobante="01",
        estado="pendiente",
    ), "F001", 2)
    rejected = _numbered(db_session, make_cotizacion(
        db_session,
        tenant,
        user,
        cliente,
        document_kind=DOCUMENT_KIND_FISCAL_DOCUMENT,
        tipo_comprobante="03",
        estado="pendiente",
    ), "B001", 1)
    rejected.sunat_error = "Rechazado por SUNAT"
    other_emitted = _numbered(db_session, make_cotizacion(
        db_session,
        other_tenant,
        other_user,
        other_cliente,
        document_kind=DOCUMENT_KIND_FISCAL_DOCUMENT,
        tipo_comprobante="01",
        estado="facturada",
    ), "F001", 1)
    other_emitted.sunat_cdr_content = "<ApplicationResponse/>"
    db_session.commit()

    page = facturacion_router.list_facturas_emitidas_page(
        skip=0,
        limit=15,
        tipo_comprobante="01",
        tab="all",
        estado=None,
        moneda=None,
        desde=None,
        hasta=None,
        q=None,
        db=db_session,
        current_user=user,
    )

    assert page["total"] == 2
    assert {item.id for item in page["items"]} == {emitted.id, pending.id}
    assert page["counts"]["all"] == 2
    assert page["counts"]["emitted"] == 1
    assert page["counts"]["pending"] == 1
    assert page["counts"]["rejected"] == 0


def test_facturas_emitidas_page_no_cuenta_xml_sin_cdr_como_aceptada(db_session):
    tenant = make_tenant(db_session, "FP11")
    user = make_user(db_session, tenant, email="fiscal-pending-cdr@test.com")
    cliente = make_cliente(db_session, tenant, "FP11")
    doc = _numbered(db_session, make_cotizacion(
        db_session,
        tenant,
        user,
        cliente,
        document_kind=DOCUMENT_KIND_FISCAL_DOCUMENT,
        tipo_comprobante="01",
        estado="facturada",
    ), "F001", 1)
    doc.sunat_xml_content = "<Invoice/>"
    db_session.commit()

    page = facturacion_router.list_facturas_emitidas_page(
        skip=0,
        limit=15,
        tipo_comprobante="01",
        tab="all",
        estado=None,
        moneda=None,
        desde=None,
        hasta=None,
        q=None,
        db=db_session,
        current_user=user,
    )

    assert page["counts"]["emitted"] == 0
    assert page["counts"]["pending"] == 1
    assert page["items"][0].sunat_accepted is False


def test_guardar_respuesta_sunat_persiste_trazabilidad_smartpse(db_session):
    import crud

    tenant = make_tenant(db_session, "FP12")
    user = make_user(db_session, tenant, email="fiscal-trace@test.com")
    cliente = make_cliente(db_session, tenant, "FP12")
    doc = _numbered(db_session, make_cotizacion(
        db_session,
        tenant,
        user,
        cliente,
        document_kind=DOCUMENT_KIND_FISCAL_DOCUMENT,
        tipo_comprobante="01",
        estado="pendiente",
    ), "F001", 1)
    provider_response = {"estado": 200, "mensaje": "Aceptado por SUNAT", "cdr": "<ApplicationResponse/>"}

    updated = crud.guardar_respuesta_sunat(
        db_session,
        doc.id,
        {
            "success": True,
            "xml": "<Invoice/>",
            "cdr_xml": "<ApplicationResponse/>",
            "provider_response": provider_response,
            "provider_endpoint": "/api/cpe/procesar",
            "provider_status_code": 200,
            "provider_document_name": "20123456789-01-F001-00000001",
            "provider_verification_status": "verified",
        },
        tenant_id=tenant.id,
    )

    assert updated.provider_response == provider_response
    assert updated.provider_endpoint == "/api/cpe/procesar"
    assert updated.provider_status_code == 200
    assert updated.provider_document_name == "20123456789-01-F001-00000001"
    assert updated.provider_verification_status == "verified"
    assert updated.provider_verified_at is not None
    assert updated.cdr_artifact_status == "pending"
    assert updated.pdf_artifact_status == "pending"


def test_fiscal_document_list_response_expone_flags_de_archivos_sin_contenido(db_session):
    tenant = make_tenant(db_session, "FP13")
    user = make_user(db_session, tenant, email="fiscal-files@test.com")
    cliente = make_cliente(db_session, tenant, "FP13")
    doc = _numbered(db_session, make_cotizacion(
        db_session,
        tenant,
        user,
        cliente,
        document_kind=DOCUMENT_KIND_FISCAL_DOCUMENT,
        tipo_comprobante="01",
        estado="facturada",
    ), "F001", 1)
    doc.sunat_xml_content = "<Invoice/>"
    doc.sunat_cdr_content = "<ApplicationResponse/>"
    db_session.commit()
    db_session.refresh(doc)

    payload = schemas.FiscalDocumentListResponse.model_validate(doc).model_dump()

    assert payload["has_sunat_xml"] is True
    assert payload["has_sunat_cdr"] is True
    assert payload["provider_verification_status"] is None
    assert payload["cdr_artifact_status"] is None
    assert payload["pdf_artifact_status"] is None
    assert "sunat_xml_content" not in payload
    assert "sunat_cdr_content" not in payload


def test_facturas_emitidas_page_no_cuenta_cdr_sin_verificacion_smartpse(db_session):
    tenant = make_tenant(db_session, "FP14")
    user = make_user(db_session, tenant, email="fiscal-unverified@test.com")
    cliente = make_cliente(db_session, tenant, "FP14")
    doc = _numbered(db_session, make_cotizacion(
        db_session,
        tenant,
        user,
        cliente,
        document_kind=DOCUMENT_KIND_FISCAL_DOCUMENT,
        tipo_comprobante="01",
        estado="facturada",
    ), "F001", 1)
    doc.sunat_xml_content = "<Invoice/>"
    doc.sunat_cdr_content = "<ApplicationResponse/>"
    doc.provider_verification_status = "failed"
    db_session.commit()

    page = facturacion_router.list_facturas_emitidas_page(
        skip=0,
        limit=15,
        tipo_comprobante="01",
        tab="all",
        estado=None,
        moneda=None,
        desde=None,
        hasta=None,
        q=None,
        db=db_session,
        current_user=user,
    )

    assert page["counts"]["emitted"] == 0
    assert page["counts"]["pending"] == 1
    assert page["items"][0].sunat_accepted is False


def test_retry_fiscal_artifacts_requiere_cdr_persistido(db_session):
    tenant = make_tenant(db_session, "FP15")
    user = make_user(db_session, tenant, email="fiscal-retry-missing@test.com")
    cliente = make_cliente(db_session, tenant, "FP15")
    doc = _numbered(db_session, make_cotizacion(
        db_session,
        tenant,
        user,
        cliente,
        document_kind=DOCUMENT_KIND_FISCAL_DOCUMENT,
        tipo_comprobante="01",
        estado="facturada",
    ), "F001", 1)

    with pytest.raises(facturacion_router.HTTPException) as exc_info:
        asyncio.run(facturacion_router.retry_fiscal_artifacts(doc.id, db_session, user))

    assert exc_info.value.status_code == 409


def test_retry_fiscal_artifacts_regenera_pdf_y_cdr_desde_contenido(db_session, monkeypatch):
    tenant = make_tenant(db_session, "FP16")
    user = make_user(db_session, tenant, email="fiscal-retry-ok@test.com")
    cliente = make_cliente(db_session, tenant, "FP16")
    doc = _numbered(db_session, make_cotizacion(
        db_session,
        tenant,
        user,
        cliente,
        document_kind=DOCUMENT_KIND_FISCAL_DOCUMENT,
        tipo_comprobante="01",
        estado="facturada",
    ), "F001", 1)
    doc.sunat_cdr_content = "<ApplicationResponse/>"
    db_session.commit()

    async def fake_cdr(db, comprobante, cdr_xml):
        comprobante.sunat_cdr_url = "supabase-private://bucket/cdr.zip"
        comprobante.cdr_artifact_status = "ready"
        db.commit()
        return comprobante.sunat_cdr_url

    async def fake_pdf(db, comprobante):
        comprobante.sunat_pdf_url = "supabase-private://bucket/doc.pdf"
        comprobante.pdf_artifact_status = "ready"
        db.commit()
        return comprobante.sunat_pdf_url

    monkeypatch.setattr(facturacion_router.fiscal_artifact_service, "persist_cdr_artifact", fake_cdr)
    monkeypatch.setattr(facturacion_router.pdf_storage_service, "generate_and_upload_pdf", fake_pdf)

    result = asyncio.run(facturacion_router.retry_fiscal_artifacts(doc.id, db_session, user))

    assert result["ok"] is True
    assert result["cdr_artifact_status"] == "ready"
    assert result["pdf_artifact_status"] == "ready"
    assert result["has_cdr"] is True
    assert result["has_pdf"] is True


def test_facturas_emitidas_page_busqueda_no_filtra_otro_tenant(db_session):
    tenant = make_tenant(db_session, "FP03")
    other_tenant = make_tenant(db_session, "FP04")
    user = make_user(db_session, tenant, email="fiscal-search@test.com")
    cliente = make_cliente(db_session, tenant, "FP03", numero_documento="20191308868")
    other_user = make_user(db_session, other_tenant, email="other-search@test.com")
    other_cliente = make_cliente(db_session, other_tenant, "FP04")
    emitted = _numbered(db_session, make_cotizacion(
        db_session,
        tenant,
        user,
        cliente,
        document_kind=DOCUMENT_KIND_FISCAL_DOCUMENT,
        tipo_comprobante="01",
        estado="facturada",
    ), "F001", 1)
    emitted.sunat_cdr_content = "<ApplicationResponse/>"
    other_emitted = _numbered(db_session, make_cotizacion(
        db_session,
        other_tenant,
        other_user,
        other_cliente,
        document_kind=DOCUMENT_KIND_FISCAL_DOCUMENT,
        tipo_comprobante="01",
        estado="facturada",
    ), "F001", 1)
    other_emitted.sunat_cdr_content = "<ApplicationResponse/>"
    db_session.commit()

    page = facturacion_router.list_facturas_emitidas_page(
        skip=0,
        limit=15,
        tipo_comprobante="01",
        tab="emitted",
        estado=None,
        moneda=None,
        desde=None,
        hasta=None,
        q="20191308868",
        db=db_session,
        current_user=user,
    )

    assert page["total"] == 1
    assert page["items"][0].cliente.numero_documento == "20191308868"
    assert page["counts"]["all"] == 1


def test_notas_page_conteos_credito_debito(db_session):
    tenant = make_tenant(db_session, "FP05")
    user = make_user(db_session, tenant, email="notes-page@test.com")
    cliente = make_cliente(db_session, tenant, "FP05")
    credit_note = _numbered(db_session, make_cotizacion(
        db_session,
        tenant,
        user,
        cliente,
        document_kind=DOCUMENT_KIND_CREDIT_NOTE,
        tipo_comprobante="07",
        estado="facturada",
    ), "FC01", 1)
    credit_note.sunat_cdr_content = "<ApplicationResponse/>"
    debit_note = _numbered(db_session, make_cotizacion(
        db_session,
        tenant,
        user,
        cliente,
        document_kind="debit_note",
        tipo_comprobante="08",
        estado="pendiente",
    ), "FD01", 1)
    db_session.commit()

    page = facturacion_router.list_notas_page(
        skip=0,
        limit=15,
        tipo_nota=None,
        tab="all",
        estado=None,
        desde=None,
        hasta=None,
        q=None,
        db=db_session,
        current_user=user,
    )

    assert page["total"] == 2
    assert {item.id for item in page["items"]} == {credit_note.id, debit_note.id}
    assert page["counts"]["all"] == 2
    assert page["counts"]["emitted"] == 1
    assert page["counts"]["pending"] == 1
