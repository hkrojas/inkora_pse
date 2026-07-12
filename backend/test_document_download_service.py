from types import SimpleNamespace

from services.document_download_service import build_document_download_filename


def test_pdf_download_filename_uses_document_and_receiver_ruc():
    document = SimpleNamespace(
        serie="FA01",
        correlativo=1,
        cliente_snapshot={"numero_documento": "20216656149"},
        cliente=None,
    )

    assert build_document_download_filename(document) == "FA01-000001_20216656149.pdf"


def test_pdf_download_filename_uses_receiver_document_when_not_ruc():
    document = SimpleNamespace(
        serie="B001",
        correlativo=24,
        cliente_snapshot={"numero_documento": "72758912"},
        cliente=None,
    )

    assert build_document_download_filename(document) == "B001-000024_72758912.pdf"
