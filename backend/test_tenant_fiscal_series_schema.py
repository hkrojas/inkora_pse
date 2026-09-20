import pytest
from pydantic import ValidationError

import schemas


def test_superadmin_normalizes_configured_fiscal_series():
    payload = schemas.TenantSaaSUpdate(
        fiscal_invoice_series="fa01",
        fiscal_invoice_series_floor=178,
        fiscal_boleta_series="bb01",
        fiscal_boleta_series_floor=22,
    )

    assert payload.fiscal_invoice_series == "FA01"
    assert payload.fiscal_invoice_series_floor == 178
    assert payload.fiscal_boleta_series == "BB01"
    assert payload.fiscal_boleta_series_floor == 22


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("fiscal_invoice_series", "B001", "serie de factura debe iniciar con F"),
        ("fiscal_boleta_series", "F001", "serie de boleta debe iniciar con B"),
        ("fiscal_invoice_series", "F01", "4 caracteres alfanumericos"),
    ],
)
def test_superadmin_rejects_invalid_fiscal_series(field, value, message):
    with pytest.raises(ValidationError, match=message):
        schemas.TenantSaaSUpdate(**{field: value})


def test_superadmin_normalizes_all_document_series_in_confirmed_update():
    payload = schemas.TenantFiscalSeriesUpdate(
        fiscal_invoice_series="fa01",
        fiscal_invoice_series_floor=180,
        fiscal_boleta_series="ba01",
        fiscal_boleta_series_floor=72,
        fiscal_gre_remitente_series="ti01",
        fiscal_gre_remitente_series_floor=0,
        fiscal_gre_transportista_series="vi01",
        fiscal_gre_transportista_series_floor=0,
        confirmed=True,
    )

    assert payload.fiscal_gre_remitente_series == "TI01"
    assert payload.fiscal_gre_transportista_series == "VI01"


def test_superadmin_requires_explicit_confirmation_for_fiscal_series():
    with pytest.raises(ValidationError, match="Confirma que revisaste"):
        schemas.TenantFiscalSeriesUpdate(
            fiscal_invoice_series="FA01",
            fiscal_invoice_series_floor=180,
            fiscal_boleta_series="BA01",
            fiscal_boleta_series_floor=72,
            fiscal_gre_remitente_series="TI01",
            fiscal_gre_remitente_series_floor=0,
            fiscal_gre_transportista_series="VI01",
            fiscal_gre_transportista_series_floor=0,
            confirmed=False,
        )
