import pytest
from pydantic import ValidationError

from schemas.tenants import TenantAdminUpdate, TenantUpdate


@pytest.mark.parametrize("schema", [TenantAdminUpdate, TenantUpdate])
def test_tenant_pdf_colors_accept_hex(schema):
    payload = schema(primary_color="#8DC63F", pdf_note_1_color="#EF4444")

    assert payload.primary_color == "#8DC63F"
    assert payload.pdf_note_1_color == "#EF4444"


@pytest.mark.parametrize("schema", [TenantAdminUpdate, TenantUpdate])
@pytest.mark.parametrize("field", ["primary_color", "pdf_note_1_color"])
def test_tenant_pdf_colors_reject_invalid_values(schema, field):
    with pytest.raises(ValidationError):
        schema(**{field: "blue"})
