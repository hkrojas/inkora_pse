from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import HTTPException

import crud
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from routers import guias as guias_router
from services.facturacion_service import FacturacionException


def _make_user_and_guia(db_session, suffix: str):
    tenant = make_tenant(db_session, suffix)
    tenant.apisperu_token = "fake_token"
    db_session.commit()
    user = make_user(db_session, tenant, email=f"{suffix.lower()}@test.com")
    cliente = make_cliente(db_session, tenant, suffix)
    quote = make_quote_via_crud(db_session, tenant, user, cliente)
    fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
    guia = crud.create_guia_remision(
        db_session,
        {
            "cotizacion_id": fiscal.id,
            "fecha_traslado": datetime.now(timezone.utc),
            "motivo_traslado": "01",
            "descripcion_motivo": "VENTA",
            "peso_bruto_total": Decimal("5.00"),
            "unidad_medida_peso": "KGM",
            "numero_bultos": 1,
            "modalidad_traslado": "02",
            "conductor_tipo_doc": "1",
            "conductor_nro_doc": "72758912",
            "conductor_nombres": "KENNEDY",
            "conductor_apellidos": "ROJAS",
            "conductor_licencia": "Q12345678",
            "vehiculo_placa": "ABC123",
            "partida_ubigeo": "150101",
            "partida_direccion": "Av. Origen 100",
            "llegada_ubigeo": "150101",
            "llegada_direccion": "Av. Destino 200",
            "items": [
                {
                    "descripcion": "Paquete de prueba",
                    "cantidad": Decimal("2"),
                    "unidad_medida": "NIU",
                    "codigo_producto": "PK-001",
                }
            ],
        },
        user.id,
        tenant.id,
    )
    return user, guia


def test_emitir_guia_devuelve_advertencia_gre_en_error(db_session):
    user, guia = _make_user_and_guia(db_session, "GR01")

    with patch(
        "routers.guias.facturacion_service.emitir_guia_remision",
        side_effect=FacturacionException("Fallo controlado de guia"),
    ):
        with pytest.raises(HTTPException) as exc:
            guias_router.emitir_guia_remision_endpoint(guia.id, db_session, user)

    assert exc.value.status_code == 400
    assert "Fallo controlado de guia" in exc.value.detail
    assert "SUNAT Nueva GRE" in exc.value.detail
