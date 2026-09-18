# Homologación PostgreSQL de despachos y Guías

## Ejecución local del 15 de septiembre de 2026

- Commit base: `640528c4aac2f97e01b4c648aca34582e51c2c84`.
- Rama: `codex/smartpse-backend`.
- Motor aislado: PostgreSQL `17.4`, puerto local `55432`.
- Base de migración: `inkora_gre_test`.
- Base de restauración: `inkora_gre_restore_test`.
- Proveedor fiscal: no invocado; esta homologación usa únicamente datos sintéticos.

## Resultado de migración

Se preparó un esquema representativo en `0020_tenant_fiscal_contingency` con
facturas aceptadas y pendientes, líneas repetidas, una salida de inventario y
una guía histórica. Se generó un respaldo en formato custom antes de aplicar
la nueva revisión.

`0021_sale_dispatch_guides` se aplicó correctamente y dejó una sola cabeza. Se
comprobó:

- creación de `sale_dispatches`, `sale_dispatch_lines` y
  `guide_external_references`;
- `guia_remision_items.cantidad` en `NUMERIC(18,4)`;
- facturas tipo `01` históricas en conciliación `required`;
- cotizaciones no fiscales en `not_required`;
- conservación de facturas, líneas, guía y movimiento de inventario.

El respaldo anterior a `0021` se restauró en una segunda base. La revisión
restaurada fue `0020_tenant_fiscal_contingency`, con los conteos originales y
sin las tablas nuevas.

## Resultado de concurrencia

La suite PostgreSQL ejecutó cuatro escenarios con sesiones y transacciones
independientes, liberadas simultáneamente mediante una barrera:

- dos reservas de 60 sobre 100: una reserva y un conflicto por exceso;
- reservas de 40 y 60: ambas se confirman y el disponible termina en cero;
- dos solicitudes con la misma clave: un solo despacho persistido;
- edición y cancelación concurrentes: estado final cancelado, reservas
  liberadas y cero movimientos de inventario adicionales.

La primera ejecución descubrió que PostgreSQL rechaza `FOR UPDATE` cuando se
aplica sobre las relaciones opcionales cargadas con `LEFT JOIN`. El servicio
ahora bloquea primero la fila base de factura o despacho y carga sus relaciones
en una consulta separada, manteniendo el bloqueo dentro de la transacción.

Resultado final: `4 passed` en PostgreSQL 17.4.

## Ejecución repetible

Desde `backend/`, usando exclusivamente una base local desechable:

```powershell
$env:INKORA_TEST_POSTGRES_URL='postgresql://postgres@127.0.0.1:55432/inkora_gre_concurrency_test'
$env:INKORA_REQUIRE_POSTGRES_TESTS='1'
pytest -q test_sale_dispatch_postgres.py
```

La suite recrea el esquema de la base indicada y falla si el destino no es
local o su nombre no empieza con `inkora_gre_`.
