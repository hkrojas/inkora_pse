import asyncio
import zipfile
from io import BytesIO
from unittest.mock import Mock, patch

import crud
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from services import facturacion_service, fiscal_artifact_service, storage_service


def _run(coro):
    return asyncio.run(coro)


def _make_fiscal_document(db_session):
    tenant = make_tenant(db_session, "CDR01")
    user = make_user(db_session, tenant, email="cdr@test.com")
    cliente = make_cliente(db_session, tenant, "CDR01", numero_documento="20191308868")
    quote = make_quote_via_crud(db_session, tenant, user, cliente)
    fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
    fiscal.serie = "F001"
    fiscal.correlativo = 42
    db_session.commit()
    db_session.refresh(fiscal)
    return tenant, user, fiscal


def test_package_cdr_xml_as_zip_contains_cdr_xml_file():
    cdr_zip = fiscal_artifact_service.package_cdr_xml_as_zip(
        "<ApplicationResponse>OK</ApplicationResponse>",
        filename="R-20123456789-01-F001-00000042.xml",
    )

    with zipfile.ZipFile(BytesIO(cdr_zip)) as archive:
        assert archive.namelist() == ["R-20123456789-01-F001-00000042.xml"]
        assert archive.read("R-20123456789-01-F001-00000042.xml").decode("utf-8") == (
            "<ApplicationResponse>OK</ApplicationResponse>"
        )


def test_persist_cdr_artifact_uploads_zip_to_tenant_scoped_private_storage(db_session):
    tenant, _, fiscal = _make_fiscal_document(db_session)
    private_ref = storage_service.build_private_storage_reference(
        f"cotizaciones/tenant_{tenant.id}/cdr/R-F001-00000042.zip"
    )

    with patch(
        "services.fiscal_artifact_service.storage_service.upload_to_storage",
        new=Mock(return_value=private_ref),
    ) as upload:
        result = _run(
            fiscal_artifact_service.persist_cdr_artifact(
                db_session,
                fiscal,
                "<ApplicationResponse>OK</ApplicationResponse>",
            )
        )

    assert result == private_ref
    assert fiscal.sunat_cdr_url == private_ref
    upload.assert_called_once()
    file_bytes, folder_name, filename, content_type = upload.call_args.args
    assert folder_name == f"cotizaciones/tenant_{tenant.id}/cdr"
    assert filename == "R-F001-00000042.zip"
    assert content_type == "application/zip"
    with zipfile.ZipFile(BytesIO(file_bytes)) as archive:
        assert archive.read("R-F001-00000042.xml").decode("utf-8") == "<ApplicationResponse>OK</ApplicationResponse>"


def test_persist_cdr_artifact_returns_existing_private_reference_without_reupload(db_session):
    _, _, fiscal = _make_fiscal_document(db_session)
    fiscal.sunat_cdr_url = storage_service.build_private_storage_reference("cotizaciones/tenant_1/cdr/existing.zip")
    db_session.commit()

    with patch(
        "services.fiscal_artifact_service.storage_service.upload_to_storage",
        new=Mock(side_effect=AssertionError("CDR should not be uploaded twice")),
    ):
        result = _run(
            fiscal_artifact_service.persist_cdr_artifact(
                db_session,
                fiscal,
                "<ApplicationResponse>OK</ApplicationResponse>",
            )
        )

    assert result == fiscal.sunat_cdr_url


def test_descargar_archivo_cdr_uses_private_storage_reference(db_session):
    _, user, fiscal = _make_fiscal_document(db_session)
    fiscal.sunat_cdr_url = storage_service.build_private_storage_reference("cotizaciones/tenant_1/cdr/R-F001-00000042.zip")
    db_session.commit()

    with patch(
        "services.facturacion_service.storage_service.download_private_storage_reference",
        return_value=b"cdr-zip",
    ) as download:
        content = facturacion_service.descargar_archivo("cdr", fiscal, user)

    assert content == b"cdr-zip"
    download.assert_called_once_with(fiscal.sunat_cdr_url)
