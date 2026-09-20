from types import SimpleNamespace

from services.document_download_service import build_document_download_filename


def test_pdf_download_filename_uses_snapshot_receiver_document():
    document = SimpleNamespace(
        serie="COT",
        correlativo=52,
        cliente_snapshot={"numero_documento": "20123456789"},
        cliente=None,
    )
    assert build_document_download_filename(document) == "COT-000052_20123456789.pdf"


def test_pdf_download_filename_is_sanitized():
    document = SimpleNamespace(
        serie="COT/../",
        correlativo=1,
        cliente_snapshot={"numero_documento": "72.758.912"},
        cliente=None,
    )
    assert build_document_download_filename(document) == "COT-000001_72758912.pdf"
