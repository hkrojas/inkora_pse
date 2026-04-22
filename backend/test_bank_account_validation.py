import pytest
from pydantic import ValidationError

from schemas.tenants import TenantAdminUpdate
from services.bank_account_validation import validate_and_normalize_bank_accounts


def test_validate_and_normalize_bank_accounts_strips_separators():
    methods = [
        {
            "tipo": "bank",
            "banco": "BCP",
            "tipo_cuenta": "Cta Ahorro",
            "moneda": "Soles",
            "cuenta": "191-7292029-0-56",
            "cci": "002-191-007292029056-55",
        }
    ]

    normalized = validate_and_normalize_bank_accounts(methods)

    assert normalized[0]["cuenta"] == "1917292029056"
    assert normalized[0]["cci"] == "00219100729202905655"


def test_validate_and_normalize_bank_accounts_rejects_invalid_interbank_length():
    methods = [
        {
            "tipo": "bank",
            "banco": "Interbank",
            "tipo_cuenta": "Cta Ahorro",
            "moneda": "Soles",
            "cuenta": "123456789012",
            "cci": "",
        }
    ]

    with pytest.raises(ValueError, match="Interbank"):
        validate_and_normalize_bank_accounts(methods)


def test_tenant_admin_update_rejects_invalid_cci_length():
    with pytest.raises(ValidationError, match="20 digitos"):
        TenantAdminUpdate(
            bank_accounts=[
                {
                    "tipo": "bank",
                    "banco": "BBVA",
                    "tipo_cuenta": "Cta Ahorro",
                    "moneda": "Soles",
                    "cuenta": "001101230000012345",
                    "cci": "12345",
                }
            ]
        )
