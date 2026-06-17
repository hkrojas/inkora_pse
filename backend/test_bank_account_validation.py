import pytest
from pydantic import ValidationError

from models import Tenant
from schemas.tenants import TenantAdminUpdate, TenantResponse
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


def test_validate_and_normalize_bank_accounts_ignores_payment_qr_meta():
    normalized = validate_and_normalize_bank_accounts(
        [
            {"tipo": "payment_qr_image", "url": "https://cdn.test/qr-cobro.png"},
            {"tipo": "wallet", "proveedor": "Yape", "numero": "999888777"},
        ]
    )

    assert normalized == [
        {
            "tipo": "wallet",
            "proveedor": "Yape",
            "titular": "",
            "numero": "999888777",
            "nota": "",
        }
    ]


def test_validate_and_normalize_bank_accounts_preserves_communication_templates():
    normalized = validate_and_normalize_bank_accounts(
        [
            {
                "tipo": "communication_templates",
                "whatsapp_message": "Hola {cliente}, descarga {url}",
                "email_subject": "Cotizacion {numero}",
                "email_body": "Documento: {url}",
            },
            {"tipo": "wallet", "proveedor": "Yape", "numero": "999888777"},
        ]
    )

    assert normalized[0] == {
        "tipo": "communication_templates",
        "whatsapp_message": "Hola {cliente}, descarga {url}",
        "email_subject": "Cotizacion {numero}",
        "email_body": "Documento: {url}",
    }
    assert normalized[1]["tipo"] == "wallet"


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


@pytest.mark.parametrize("cuenta", ["1234567890", "12345678901", "123456789012", "1234567890123"])
def test_validate_and_normalize_bank_accounts_accepts_banco_nacion_range(cuenta):
    normalized = validate_and_normalize_bank_accounts(
        [
            {
                "tipo": "bank",
                "banco": "Banco de la Nacion",
                "tipo_cuenta": "Cuenta Detraccion",
                "moneda": "Soles",
                "cuenta": cuenta,
                "cci": "",
            }
        ]
    )

    assert normalized[0]["cuenta"] == cuenta


def test_validate_and_normalize_bank_accounts_preserves_quote_visibility_flag():
    normalized = validate_and_normalize_bank_accounts(
        [
            {
                "tipo": "bank",
                "banco": "BCP",
                "tipo_cuenta": "Cta Corriente",
                "moneda": "Soles",
                "cuenta": "1919870450013",
                "cci": "00219100987045001355",
                "mostrar_en_cotizaciones": False,
            }
        ]
    )

    assert normalized[0]["mostrar_en_cotizaciones"] is False


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


def test_tenant_response_exposes_payment_qr_image_url():
    payload = TenantResponse.model_validate(
        {
            "id": 1,
            "is_active": True,
            "business_name": "Inkora Demo SAC",
            "business_ruc": "20600000001",
            "payment_qr_filename": "https://cdn.test/qr-cobro.png",
        }
    ).model_dump()

    assert payload["payment_qr_filename"] == "https://cdn.test/qr-cobro.png"


def test_tenant_response_resolves_payment_qr_from_bank_accounts_meta():
    tenant = Tenant(
        id=1,
        is_active=True,
        business_name="Inkora Demo SAC",
        business_ruc="20600000001",
        bank_accounts=[
            {"tipo": "wallet", "proveedor": "Yape", "numero": "999888777"},
            {"tipo": "payment_qr_image", "url": "https://cdn.test/qr-cobro.png"},
        ],
    )

    payload = TenantResponse.model_validate(tenant).model_dump()

    assert payload["payment_qr_filename"] == "https://cdn.test/qr-cobro.png"
