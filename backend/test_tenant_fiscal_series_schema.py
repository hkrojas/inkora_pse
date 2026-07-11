import pytest
from pydantic import ValidationError

from schemas.tenants import TenantSaaSUpdate


def test_superadmin_accepts_valid_invoice_and_boleta_series():
    payload = TenantSaaSUpdate(
        fiscal_invoice_series="fa01",
        fiscal_boleta_series="bb01",
    )

    assert payload.fiscal_invoice_series == "FA01"
    assert payload.fiscal_boleta_series == "BB01"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("fiscal_invoice_series", "E001", "serie de factura debe iniciar con F"),
        ("fiscal_boleta_series", "EB01", "serie de boleta debe iniciar con B"),
    ],
)
def test_superadmin_rejects_series_with_invalid_document_prefix(field, value, message):
    with pytest.raises(ValidationError, match=message):
        TenantSaaSUpdate(**{field: value})
