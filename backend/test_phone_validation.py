import pytest
from pydantic import ValidationError
from types import SimpleNamespace

from schemas.clientes import ClienteCreate
from schemas.tenants import TenantAdminUpdate
from services.bank_account_validation import validate_and_normalize_bank_accounts
from services.comunicacion_service import generar_link_whatsapp
from services.phone_validation import normalize_peru_mobile


def test_normalize_peru_mobile_strips_country_code_and_symbols():
    assert normalize_peru_mobile("+51 987-654-321") == "987654321"


def test_tenant_admin_update_rejects_invalid_business_phone():
    with pytest.raises(ValidationError, match="Telefono de contacto"):
        TenantAdminUpdate(business_phone="812345678")


def test_cliente_create_rejects_invalid_whatsapp():
    with pytest.raises(ValidationError, match="WhatsApp"):
        ClienteCreate(
            tipo_documento="6",
            numero_documento="20100099991",
            razon_social="Cliente Demo SAC",
            whatsapp="123456789",
        )


def test_cliente_create_normalizes_valid_mobile_fields():
    cliente = ClienteCreate(
        tipo_documento="6",
        numero_documento="20100099991",
        razon_social="Cliente Demo SAC",
        telefono="+51 987 654 321",
    )
    assert cliente.telefono == "987654321"


def test_wallet_number_requires_valid_peruvian_mobile():
    with pytest.raises(ValueError, match="numero asociado"):
        validate_and_normalize_bank_accounts(
            [
                {
                    "tipo": "wallet",
                    "proveedor": "Yape",
                    "titular": "Inkora Demo",
                    "numero": "123456789",
                }
            ]
        )


def test_generar_link_whatsapp_returns_empty_for_invalid_mobile():
    cotizacion = SimpleNamespace(
        moneda="PEN",
        serie="COT1",
        correlativo="000001",
        total_venta="150.00",
        cliente=SimpleNamespace(numero_documento="20100099991"),
    )
    assert generar_link_whatsapp(cotizacion, "123456789", "https://demo.test/cotizacion") == ""
