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
