# Validacion Manual de Documentos ApisPeru

## Objetivo

Este archivo deja una guia corta y operativa para validar cada documento fiscal en ApisPeru, tanto desde Swagger UI como desde el backend de Inkora.

No reemplaza el flujo detallado de [APISPERU_FLUJO_EMISION.md](/C:/Users/HP/Desktop/mi_proyecto_cotizaciones/APISPERU_FLUJO_EMISION.md). Su funcion es servir como checklist de validacion por documento.

## Preparacion general

Antes de probar cualquier documento:

1. Confirmar que el `Bearer token` corresponde a la empresa emisora correcta.
2. Confirmar que el RUC del `company` coincide con la empresa configurada en ApisPeru.
3. Confirmar que `serie` y `correlativo` no choquen con una emision previa.
4. Confirmar que el ambiente de la empresa es el esperado: beta o produccion.
5. Probar primero en Swagger UI si se quiere aislar el comportamiento del proveedor.
6. Probar luego desde el backend para verificar que Inkora arma el payload correctamente.

## Regla de lectura de resultados

- Documentos inmediatos:
  - `200` y `sunatResponse.success = true` significa aceptado.
  - `400` suele ser error de validacion de payload.
  - `500` suele indicar fallo interno del proveedor.
- Documentos con ticket:
  - `send` puede devolver ticket sin cerrar aun la emision.
  - Luego se debe consultar `status`.

## Endpoints por familia

### Respuesta inmediata

- Factura / Boleta: `POST /invoice/send`
- Nota de credito / debito: `POST /note/send`
- Retencion: `POST /retention/send`
- Percepcion: `POST /perception/send`

### Asincronos con ticket

- Resumen diario: `POST /summary/send` y luego `GET /summary/status`
- Comunicacion de baja: `POST /voided/send` y luego `GET /voided/status`
- Guia de remision: `POST /despatch/send` y luego `GET /despatch/status`
- Reversion: `POST /reversion/send` y luego `GET /reversion/status`

### Endpoints auxiliares

- XML: probar `POST /invoice/xml`, `POST /note/xml`, `POST /despatch/xml`, etc.
- PDF: probar `POST /invoice/pdf`, `POST /note/pdf`, `POST /despatch/pdf`, etc.
- QR: usar el endpoint disponible solo si aplica al documento.

## 1. Factura

### Endpoint

- `POST /invoice/send`

### Campos minimos a validar

- `tipoDoc = "01"`
- `company` completo
- `client.tipoDoc = "6"` para RUC
- `serie` de factura
- `correlativo`
- `details[]`
- totales e impuestos coherentes

### Checklist

1. Validar que el cliente tenga RUC.
2. Validar que los items tengan cantidad, unidad, descripcion y montos consistentes.
3. Validar que `mtoOperGravadas`, `mtoIGV`, `valorVenta`, `subTotal` y `mtoImpVenta` cierren.
4. Emitir.
5. Descargar XML y PDF.

### Resultado esperado

- `200`
- `sunatResponse.success = true`
- descripcion de aceptacion

## 2. Boleta

### Endpoint

- `POST /invoice/send`

### Campos minimos a validar

- `tipoDoc = "03"`
- `client.tipoDoc = "1"` si se usa DNI
- `serie` de boleta
- `correlativo`
- `details[]`

### Checklist

1. Validar tipo de documento del cliente.
2. Validar montos e impuestos igual que factura.
3. Emitir.
4. Descargar XML y PDF.

### Resultado esperado

- `200`
- `sunatResponse.success = true`

## 3. Nota de credito

### Endpoint

- `POST /note/send`

### Campos minimos a validar

- `tipoDoc = "07"`
- documento afectado
- `codMotivo`
- `desMotivo`
- `details[]`

### Checklist

1. Confirmar que el comprobante afectado exista.
2. Confirmar que el motivo de nota sea valido.
3. Confirmar que el payload referencia correctamente el documento afectado.
4. Emitir.
5. Descargar XML y PDF.

### Resultado esperado

- `200`
- `sunatResponse.success = true`

## 4. Nota de debito

### Endpoint

- `POST /note/send`

### Campos minimos a validar

- `tipoDoc = "08"`
- documento afectado
- `codMotivo`
- `desMotivo`

### Checklist

1. Confirmar documento afectado.
2. Confirmar motivo valido.
3. Emitir.
4. Descargar XML y PDF.

### Resultado esperado

- `200`
- `sunatResponse.success = true`

## 5. Resumen diario de boletas

### Endpoint

- `POST /summary/send`
- `GET /summary/status`

### Campos minimos a validar

- fecha de generacion
- fecha de resumen
- correlativo del resumen
- `details[]` con `tipoDoc`, `serieNro`, `estado`

### Checklist

1. Confirmar que las boletas incluidas existan.
2. Confirmar que `estado` sea el correcto segun catalogo.
3. Enviar `summary/send`.
4. Guardar ticket.
5. Consultar `summary/status` hasta cierre.

### Resultado esperado

- `send` devuelve ticket
- `status` cierra con exito

### Observacion actual

- Este documento tuvo bloqueos reales en pruebas previas. No asumir exito sin revisar `status`.

## 6. Comunicacion de baja

### Endpoint

- `POST /voided/send`
- `GET /voided/status`

### Campos minimos a validar

- fecha de generacion
- fecha de comunicacion
- correlativo
- `details[]` con documento a dar de baja y motivo

### Checklist

1. Confirmar que el comprobante a dar de baja exista y sea anulable.
2. Confirmar que el motivo este informado.
3. Enviar `voided/send`.
4. Guardar ticket.
5. Consultar `voided/status`.

### Resultado esperado

- `send` con ticket
- `status` aceptado

## 7. Guia de remision

### Endpoint

- `POST /despatch/send`
- `GET /despatch/status`
- `POST /despatch/xml`
- `POST /despatch/pdf`

### Campos minimos a validar

- `tipoDoc = "09"`
- `company`
- `destinatario`
- `envio.codTraslado`
- `envio.modTraslado`
- `envio.fecTraslado`
- `envio.pesoTotal`
- `envio.undPesoTotal`
- `envio.llegada`
- `envio.partida`
- `details[]`

### Campos adicionales a validar

- Si `modTraslado = "01"`:
  - `transportista.tipoDoc`
  - `transportista.numDoc`
  - `transportista.rznSocial`
  - `transportista.placa`
  - `transportista.choferTipoDoc`
  - `transportista.choferDoc`
  - `tercero`
- Si `modTraslado = "02"`:
  - `vehiculo.placa`
  - `choferes[]`

### Checklist

1. Probar primero `POST /despatch/xml`.
2. Probar luego `POST /despatch/pdf`.
3. Si ambos salen bien, probar `POST /despatch/send`.
4. Si `send` devuelve ticket, consultar `GET /despatch/status`.
5. Si `send` devuelve `500`, guardar payload y respuesta exacta.

### Resultado esperado

- `xml` y `pdf` deben responder correctamente.
- `send` deberia aceptar o devolver ticket.

### Observacion actual

- En las pruebas reales de este proyecto, `despatch/xml` y `despatch/pdf` respondieron bien, pero `despatch/send` devolvio `500` con error interno del proveedor.
- Eso ya fue reproducido manualmente en Swagger UI con el payload real de prueba.

## 8. Retencion

### Endpoint

- `POST /retention/send`

### Campos minimos a validar

- emisor
- receptor
- comprobantes asociados
- montos
- regimen de retencion

### Checklist

1. Confirmar base imponible y monto retenido.
2. Confirmar documentos asociados.
3. Emitir.
4. Descargar XML y PDF si aplica.

### Resultado esperado

- `200`
- `sunatResponse.success = true`

## 9. Percepcion

### Endpoint

- `POST /perception/send`

### Campos minimos a validar

- emisor
- cliente
- documentos base
- regimen de percepcion
- montos

### Checklist

1. Confirmar tasa y regimen correctos.
2. Confirmar documentos relacionados.
3. Emitir.
4. Descargar XML y PDF si aplica.

### Resultado esperado

- `200`
- `sunatResponse.success = true`

## 10. Reversion

### Endpoint

- `POST /reversion/send`
- `GET /reversion/status`

### Campos minimos a validar

- fecha
- correlativo
- items incluidos
- estado correspondiente

### Checklist

1. Confirmar que el documento a revertir sea valido para este flujo.
2. Enviar `reversion/send`.
3. Guardar ticket.
4. Consultar `reversion/status`.

### Resultado esperado

- `send` con ticket
- `status` aceptado

## Evidencia minima que siempre conviene guardar

Para cualquier validacion real, guardar:

1. Payload enviado.
2. Response crudo.
3. XML si existe.
4. PDF si existe.
5. QR si aplica.
6. Ticket si aplica.
7. Resultado de `status` si aplica.

## Orden recomendado de validacion

1. Factura
2. Boleta
3. Nota de credito
4. Nota de debito
5. Retencion
6. Percepcion
7. Resumen diario
8. Comunicacion de baja
9. Reversion
10. Guia de remision

## Criterio practico para diagnosticar

- Si `xml` falla: el payload esta mal o faltan datos.
- Si `xml` funciona y `send` falla con `400`: hay validacion del proveedor o de SUNAT.
- Si `xml` funciona y `send` falla con `500`: el problema probablemente esta del lado del proveedor.
- Si `send` devuelve ticket pero `status` no cierra: el problema esta en la etapa asincrona.
