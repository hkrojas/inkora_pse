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
- El historial termina hoy, independientemente del período seleccionado para indicadores y la cohorte de cotizaciones. Conserva todos los meses completos y los meses intermedios sin movimientos. Una empresa sin actividad recibe un historial vacío.
- El mes actual indica el día de corte. Su comparación usa los mismos días del mes anterior, limitada al último día de ese mes si es más corto; nunca compara el mes anterior completo con un mes actual parcial.
- El importe cotizado suma los totales de las cotizaciones registradas en cada mes. El importe vendido conserva la regla existente: facturas y boletas pendientes o facturadas, menos notas de crédito facturadas, más notas de débito facturadas, en sus propias fechas de emisión y con IGV incluido en el total.

Las lecturas están agregadas y filtradas por empresa. El endpoint realiza seis consultas SQL, sin cargar colecciones completas de comprobantes ni hacer una consulta por fila.
