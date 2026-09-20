from main import app


def test_frontend_operational_contracts_are_published():
    operations = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }
    assert {
        ("PATCH", "/inventario/almacenes/{warehouse_id}"),
        ("GET", "/inventario/existencias/page"),
        ("GET", "/inventario/documentos/search"),
        ("GET", "/inventario/cargas/plantilla"),
        ("POST", "/inventario/cargas/preview"),
        ("POST", "/inventario/cargas"),
        ("PUT", "/cotizaciones/{cotizacion_id}"),
        ("GET", "/cotizaciones/{cotizacion_id}/pdf/download"),
        ("GET", "/inventario/documentos/{document_id}/disponibilidad"),
        ("GET", "/facturacion/comprobantes/{comprobante_id}/despacho-contexto"),
        ("GET", "/facturacion/comprobantes/{comprobante_id}/guias"),
        ("POST", "/facturacion/comprobantes/{comprobante_id}/conciliar-despacho-historico"),
        ("POST", "/guias-remision/desde-comprobante"),
        ("GET", "/facturas-emitidas/{comprobante_id}/acciones"),
        ("POST", "/facturas-emitidas/{comprobante_id}/reintentar"),
        ("POST", "/facturacion/{comprobante_id}/artifacts/retry"),
    } <= operations
