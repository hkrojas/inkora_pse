from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import facturacion


app = FastAPI()
app.include_router(facturacion.router)
client = TestClient(app)


LEGACY_FISCAL_ENDPOINTS = (
    (
        "/retenciones/emitir-legacy",
        "routers.facturacion.facturacion_service.emitir_retencion",
        "/retenciones/emitir",
    ),
    (
        "/percepciones/emitir-legacy",
        "routers.facturacion.facturacion_service.emitir_percepcion",
        "/percepciones/emitir",
    ),
    (
        "/reversiones/enviar-legacy",
        "routers.facturacion.facturacion_service.emitir_reversion",
        "/reversiones/enviar",
    ),
)


@pytest.mark.parametrize("path,service_target,replacement_path", LEGACY_FISCAL_ENDPOINTS)
def test_legacy_fiscal_endpoint_is_gone_and_does_not_emit(
    path,
    service_target,
    replacement_path,
):
    with patch(service_target) as service_call:
        response = client.post(
            path,
            json={
                "tenant_id": 999999,
                "serie": "LEGACY",
                "correlativo": 1,
            },
        )

    assert response.status_code == 410
    assert replacement_path in response.json()["detail"]
    service_call.assert_not_called()
