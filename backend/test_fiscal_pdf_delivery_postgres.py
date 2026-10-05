"""Independent PostgreSQL transactions changing state during PDF external I/O."""
import asyncio
from io import BytesIO

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import update

import models
from routers import cotizaciones as router
from services import pdf_storage_service as pdf
from test_panel_retry_postgres import factory, clear_jobs, prepare, sign_xml  # noqa: F401
from test_pdf_generator import _make_request


@pytest.mark.parametrize("stage", ["upload", "download", "public_url", "internal_url"])
@pytest.mark.parametrize("status", ["rejected", "anulada"])
def test_committed_status_change_during_io_blocks_pdf(factory, sign_xml, monkeypatch, stage, status):
    data = prepare(factory, sign_xml, monkeypatch, jobs=1)
    def change_in_independent_transaction():
        with factory() as other:
            # This must complete while the renderer/Storage is running.
            # A row lock before external I/O would make this time out.
            from sqlalchemy import text
            other.execute(text("SET LOCAL lock_timeout='3s'"))
            values = {"provider_verification_status": "rejected"} if status == "rejected" else {"estado": "anulada"}
            other.execute(update(models.Cotizacion).where(
                models.Cotizacion.id == data["document_id"],
                models.Cotizacion.tenant_id == data["tenant_id"],
            ).values(**values))
            other.commit()
    with factory() as db:
        document = db.get(models.Cotizacion, data["document_id"])
        user = db.get(models.User, data["user_id"])
        reference = "supabase-private://audit/fiscal-" + pdf._pdf_source_fingerprint(document)[:12] + ".pdf"
        if stage != "upload":
            document.sunat_pdf_url = reference
            db.commit()
        monkeypatch.setattr(pdf.pdf_generator, "create_comprobante_pdf", lambda *args: BytesIO(b"%PDF synthetic"))
        def upload(*args):
            if stage == "upload":
                change_in_independent_transaction()
            return reference
        def download(*args):
            change_in_independent_transaction()
            return b"%PDF must be blocked"
        monkeypatch.setattr(pdf.storage_service, "upload_to_storage", upload)
        monkeypatch.setattr(pdf.storage_service, "download_private_storage_reference", download)
        def resolve_url(*args):
            change_in_independent_transaction()
            return "https://signed.test/must-be-blocked.pdf"
        monkeypatch.setattr(router, "_resolve_pdf_download_url", resolve_url)
        with pytest.raises(HTTPException) as caught:
            if stage == "public_url":
                asyncio.run(router.descargar_pdf_publico(_make_request(), document.uuid_publico, None, db))
            elif stage == "internal_url":
                asyncio.run(router.descargar_pdf_interno(_make_request(), document.id, BackgroundTasks(), False, db, user))
            else:
                asyncio.run(router.descargar_pdf_interno_como_archivo(_make_request(), document.id, db, user))
        assert caught.value.status_code == 409
        db.rollback()
    with factory() as db:
        document = db.get(models.Cotizacion, data["document_id"])
        if stage == "upload":
            assert document.sunat_pdf_url is None
        assert document.provider_verification_status == "rejected" if status == "rejected" else document.estado == "anulada"
