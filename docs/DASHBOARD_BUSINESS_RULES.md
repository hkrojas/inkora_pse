# Reglas del resumen comercial

El endpoint autenticado `/analytics/dashboard/business` calcula datos de la empresa del usuario. No cambia documentos ni sus estados.

## Cotizaciones y ventas relacionadas

- La cohorte contiene cotizaciones comerciales (`document_kind=quotation`) emitidas en las fechas seleccionadas, con estado `pendiente` o `facturada`. Excluye borradores y anuladas. Aplica los filtros de cliente, producto y moneda.
- Una cotización cuenta como convertida si existe al menos una factura o boleta (`fiscal_document`, tipo `01` o `03`) de la misma empresa con `source_quote_id` igual al ID de esa cotización, estado `pendiente` o `facturada` y fecha de emisión hasta hoy.
- Cada cotización cuenta una sola vez, aunque tenga varios comprobantes relacionados. La aceptación de SUNAT no es requisito: los comprobantes pendientes ya representan ventas registradas.
- La conversión es el estado vigente de la cohorte hasta hoy. Una venta emitida después del período seleccionado puede convertir una cotización de ese período. Anular el único comprobante vigente elimina esa conversión.
- El seguimiento muestra cotizaciones de la misma cohorte sin una venta vigente relacionada. Incluye cotizaciones cuyo estado sigue siendo `facturada` cuando su único comprobante fue anulado: el vínculo efectivo determina el seguimiento.
- El contador refleja todos los resultados; la vista compacta devuelve hasta tres filas, de mayor a menor antigüedad, con `quote_id` para abrir cada cotización.
- Si no hay cotizaciones, el total es cero y el porcentaje es nulo; no se inventa un porcentaje de éxito.

## Historial y fechas

- El historial comienza en la primera fecha de emisión registrada de una cotización o venta reconocida de la empresa. El modelo no dispone de una fecha de creación independiente de la operación. Se excluyen borradores, anuladas y fechas futuras.
- El inicio pertenece a toda la empresa, independiente del cliente, producto o moneda seleccionados. Esos filtros sí afectan los importes de cada mes.
- Con `history_scope=all` (valor predeterminado compatible), el historial termina hoy, independientemente del período seleccionado para indicadores y la cohorte de cotizaciones. Conserva todos los meses completos y los meses intermedios sin movimientos. Una empresa sin actividad recibe un historial vacío.
- El mes actual indica el día de corte. Su comparación usa los mismos días del mes anterior, limitada al último día de ese mes si es más corto; nunca compara el mes anterior completo con un mes actual parcial.
- El importe cotizado suma los totales de las cotizaciones registradas en cada mes. El importe vendido conserva la regla existente: facturas y boletas pendientes o facturadas, menos notas de crédito facturadas, más notas de débito facturadas, en sus propias fechas de emisión y con IGV incluido en el total.

## Filtros de período y agrupación

- `period_scope=selected` es el valor predeterminado: `desde` y `hasta` seleccionan el período de los indicadores, productos, clientes y cohorte de cotizaciones. Su duración máxima es 367 días y la fecha final no puede superar hoy.
- `history_scope=period` hace que el gráfico use exactamente esas mismas fechas. Los importes vendidos del gráfico suman el importe de ventas de la tarjeta, con los mismos filtros y reglas de notas. `history_scope=all` conserva la vista histórica anterior desde la primera actividad hasta hoy.
- `group_by=month` agrupa por meses. `group_by=day` agrupa por días, exige `history_scope=period` y permite hasta 93 días inclusive. La API devuelve todos los días o meses intermedios, incluso con importe cero; el frontend puede reducir etiquetas, nunca omitir importes.
- `period_scope=all` selecciona la primera fecha de actividad de la empresa hasta hoy para todos los indicadores y tablas. Ignora `desde` y `hasta`, fuerza `history_scope=period` y requiere agrupación mensual para permitir historiales de varios años.
- `meta.activity_start` informa la primera actividad de toda la empresa, sin limitarla por cliente, producto o moneda. Es nulo cuando no existe actividad válida. En una empresa vacía, el historial completo devuelve una lista vacía; un período elegido devuelve sus intervalos en cero.
- Cada punto devuelve `period_start` y `period_end` para abrir los registros de su intervalo exacto. Un mes se intersecta con los límites del período; un día devuelve también `date` y sus límites son ese mismo día. Se conservan `year`, `month` y los campos monetarios anteriores.
- Un mes cortado al inicio o al final se marca `is_partial`. Solo el último mes parcial puede informar una comparación: usa la misma franja de días del mes anterior, con sus extremos limitados al último día del mes anterior. Nunca enfrenta un mes completo a uno parcial.
- El saldo vencido es el saldo **actual**, al día de hoy, de comprobantes aceptados emitidos dentro del período elegido y que ya vencieron. Aplica cliente, producto y moneda. No reconstruye el saldo que existía en el pasado; `meta.overdue_as_of` aclara su corte actual.
- Los clientes sin comprar por 60 días se evalúan al cierre del período elegido, excluyendo compras posteriores a ese cierre. Los días sin comprar se cuentan desde su última venta hasta ese cierre.
- El estado de conversión de las cotizaciones se evalúa hasta hoy, aun cuando el período de emisión sea anterior. Los avisos operativos de inventario y errores fiscales también conservan su estado actual.

Las lecturas están agregadas y filtradas por empresa, sin cargar colecciones completas de comprobantes ni hacer consultas por fila. El endpoint realiza seis consultas SQL para períodos seleccionados y siete para todo el historial, por la consulta inicial de su primera fecha. Los importes diarios/mensuales se agrupan en SQL; únicamente se rellenan intervalos vacíos en memoria.
