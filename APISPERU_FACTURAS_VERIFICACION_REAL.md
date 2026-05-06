# Verificacion Real de Documentos via ApisPeru

## Estado

Los flujos de **facturas**, **boletas**, **notas**, **baja de factura**, **retenciones**, **percepciones** y **reversiones** estan **operativos** para el emisor:

- RUC emisor: `20606751509`
- Razon social: `PAPELERIA GRAFICA Y PUBLICITARIA SAC.`

La validacion se hizo con emisiones reales contra ApisPeru y respuesta de aceptacion de SUNAT/APisPeru.

## Conclusion

Los flujos de factura, boleta, nota, baja de factura, retencion, percepcion y reversion **funcionan correctamente** en estos puntos:

- el backend construye un JSON valido para ApisPeru
- ApisPeru acepta el documento
- se recibe `cdrResponse.code = "0"`
- se recibe y/o recupera `xml`, `cdr`, `qr` y `pdf`
- el documento queda persistido como `facturada` o `anulada` cuando corresponde
- el PDF interno puede construirse con los datos devueltos por ApisPeru

El flujo esta **operativo**, con una excepcion puntual:

- la subida del PDF interno a Supabase Storage falla por politica RLS

## Flujos verificados

- `facturas` (`tipoDoc = "01"`)
- `boletas` (`tipoDoc = "03"`)
- `notas de credito` (`tipoDoc = "07"`)
- `notas de debito` (`tipoDoc = "08"`)
- `baja de factura` (`voided/send` + `voided/status`)
- `retenciones` (`retention/send`)
- `percepciones` (`perception/send`)
- `reversiones` (`reversion/send` + `reversion/status`)

## Campos probados del JSON

Estos campos fueron probados en emision real y aceptados por ApisPeru en facturas y boletas:

- `ublVersion`
- `tipoOperacion`
- `tipoDoc`
- `serie`
- `correlativo`
- `fechaEmision`
- `tipoMoneda`
- `company`
- `client`
- `mtoOperGravadas`
- `mtoIGV`
- `valorVenta`
- `totalImpuestos`
- `subTotal`
- `mtoImpVenta`
- `mtoImporteTotal`
- `details`
- `legends`
- `formaPago`

## Estructura validada

### company

- `ruc`
- `razonSocial`
- `nombreComercial`
- `address`

### client

- `tipoDoc`
- `numDoc`
- `rznSocial`
- `address`

### details

Por item:

- `codProducto`
- `unidad`
- `descripcion`
- `cantidad`
- `mtoValorUnitario`
- `mtoValorVenta`
- `mtoBaseIgv`
- `porcentajeIgv`
- `igv`
- `tipAfeIgv`
- `totalImpuestos`
- `mtoPrecioUnitario`

### legends

- `code`
- `value`

### formaPago

- `moneda`
- `tipo`

## Respuesta aceptada observada

La aceptacion real se valido con estas condiciones:

- `success = true`
- `sunatResponse.success = true`
- `sunatResponse.cdrResponse.code = "0"`
- `sunatResponse.cdrResponse.description = "La Factura numero ... ha sido aceptada"` o `"La Boleta numero ... ha sido aceptada"`

## Artefactos recuperados de ApisPeru

En la validacion real se guardaron estos artefactos por documento:

- payload enviado
- respuesta completa del backend
- respuesta cruda del proveedor
- XML inline devuelto por emision
- XML descargado desde ApisPeru
- CDR ZIP
- QR payload
- QR SVG oficial
- PDF de ApisPeru
- PDF interno estilizado

## Evidencia de la prueba

Lote principal de facturas con artefactos completos:

- [pruebas/apisperu_facturas_full_artifacts_20260430_090145](</C:/Users/HP/Desktop/mi_proyecto_cotizaciones/pruebas/apisperu_facturas_full_artifacts_20260430_090145>)

Resumen consolidado de facturas:

- [manifest_final.json](</C:/Users/HP/Desktop/mi_proyecto_cotizaciones/pruebas/apisperu_facturas_full_artifacts_20260430_090145/manifest_final.json>)

Prueba puntual de factura + PDF interno:

- [pruebas/apisperu_factura_pdf_interno_20260430_085719](</C:/Users/HP/Desktop/mi_proyecto_cotizaciones/pruebas/apisperu_factura_pdf_interno_20260430_085719>)

Lote principal de boletas con artefactos completos:

- [pruebas/apisperu_boletas_full_artifacts_20260430_094132](</C:/Users/HP/Desktop/mi_proyecto_cotizaciones/pruebas/apisperu_boletas_full_artifacts_20260430_094132>)

Resumen consolidado de boletas:

- [manifest_final.json](</C:/Users/HP/Desktop/mi_proyecto_cotizaciones/pruebas/apisperu_boletas_full_artifacts_20260430_094132/manifest_final.json>)

Lote principal de notas con artefactos completos:

- [pruebas/apisperu_notas_full_artifacts_20260430_095014](</C:/Users/HP/Desktop/mi_proyecto_cotizaciones/pruebas/apisperu_notas_full_artifacts_20260430_095014>)

Resumen consolidado de notas:

- [manifest_final.json](</C:/Users/HP/Desktop/mi_proyecto_cotizaciones/pruebas/apisperu_notas_full_artifacts_20260430_095014/manifest_final.json>)

Lote principal de bajas con artefactos completos:

- [Pruebas/apisperu_bajas_full_artifacts_20260430_101912](</C:/Users/HP/Desktop/mi_proyecto_cotizaciones/Pruebas/apisperu_bajas_full_artifacts_20260430_101912>)

Resumen consolidado de bajas:

- [manifest_final.json](</C:/Users/HP/Desktop/mi_proyecto_cotizaciones/Pruebas/apisperu_bajas_full_artifacts_20260430_101912/manifest_final.json>)

Lote principal de reversiones con artefactos completos:

- [Pruebas/apisperu_reversiones_full_artifacts_20260430_103430](</C:/Users/HP/Desktop/mi_proyecto_cotizaciones/Pruebas/apisperu_reversiones_full_artifacts_20260430_103430>)

Resumen consolidado de reversiones:

- [manifest_final.json](</C:/Users/HP/Desktop/mi_proyecto_cotizaciones/Pruebas/apisperu_reversiones_full_artifacts_20260430_103430/manifest_final.json>)

Lote principal de retenciones y percepciones con artefactos completos:

- [Pruebas/apisperu_retenciones_percepciones_full_artifacts_20260430_110022](</C:/Users/HP/Desktop/mi_proyecto_cotizaciones/Pruebas/apisperu_retenciones_percepciones_full_artifacts_20260430_110022>)

Resumen consolidado de retenciones y percepciones:

- [manifest_final.json](</C:/Users/HP/Desktop/mi_proyecto_cotizaciones/Pruebas/apisperu_retenciones_percepciones_full_artifacts_20260430_110022/manifest_final.json>)

## Receptores usados en la validacion real

- `20549781234`
- `20531247896`
- `20547896321`
- `20569874125`
- `20587412563`
- `20596321478`
- `20587496325`
- `20569874512`
- `20587412598`
- `20569874136`

## Resultado de las baterias

- facturas probadas: `10`
- facturas aceptadas: `10`
- facturas rechazadas: `0`
- boletas probadas: `10`
- boletas aceptadas: `10`
- boletas rechazadas: `0`
- notas de credito probadas: `10`
- notas de credito aceptadas: `10`
- notas de credito rechazadas: `0`
- notas de debito probadas: `10`
- notas de debito aceptadas: `10`
- notas de debito rechazadas: `0`
- bajas de factura probadas: `10`
- bajas de factura aceptadas: `10`
- bajas de factura rechazadas: `0`
- bajas de boleta probadas: `10`
- bajas de boleta aceptadas: `0`
- bajas de boleta rechazadas: `10`
- retenciones probadas: `10`
- retenciones aceptadas: `10`
- retenciones rechazadas: `0`
- percepciones probadas: `10`
- percepciones aceptadas: `10`
- percepciones rechazadas: `0`
- reversiones probadas: `10`
- reversiones aceptadas: `10`
- reversiones rechazadas: `0`

## Tiempos observados

Promedios observados en facturas:

- emision y aceptacion ApisPeru: `3.093s`
- descarga XML desde ApisPeru: `1.701s`
- descarga PDF desde ApisPeru: `2.089s`
- construccion de PDF interno: `0.054s`

Promedios observados en boletas:

- emision y aceptacion ApisPeru: `4.408s`
- descarga XML desde ApisPeru: `3.501s`
- descarga PDF desde ApisPeru: `2.53s`
- construccion de PDF interno: `0.087s`

Promedios observados en notas de credito:

- emision y aceptacion ApisPeru: `2.34s`

Promedios observados en notas de debito:

- emision y aceptacion ApisPeru: `2.62s`

Promedios observados en bajas de factura:

- emision de la factura base: `4.331s`
- envio y aceptacion de la baja: `3.897s`

Promedios observados en retenciones:

- emision y aceptacion ApisPeru: `3.329s`

Promedios observados en percepciones:

- emision y aceptacion ApisPeru: `1.807s`

Promedios observados en reversiones:

- envio y aceptacion de la reversion: `5.523s`

## Unico problema pendiente

El unico problema confirmado en este flujo es la **subida del PDF interno a Supabase Storage**.

Estado actual:

- la factura se emite y queda aceptada
- la boleta se emite y queda aceptada
- la nota de credito se emite y queda aceptada
- la nota de debito se emite y queda aceptada
- el PDF interno se puede generar
- la subida a Supabase falla con `403 Unauthorized`
- motivo observado: politica `RLS`

Impacto:

- no invalida la emision fiscal
- no invalida la aceptacion de ApisPeru
- no invalida la construccion del PDF interno
- si afecta el almacenamiento final del PDF en la nube

## Nota sobre el logo

ApisPeru si devuelve/genera PDF con logo porque lo tiene configurado en su plataforma.

Nuestro PDF interno no esta mostrando logo para este emisor porque en la base de datos el tenant tiene:

- `logo_filename = null`

Por lo tanto, el problema del logo en el PDF interno no es del flujo fiscal ni del render de PDF, sino de configuracion del tenant.

## Resumen diario

Estado actual:

- **no operativo**

Prueba real mas reciente:

- [pruebas/apisperu_resumen_diario_20260430_100517](</C:/Users/HP/Desktop/mi_proyecto_cotizaciones/pruebas/apisperu_resumen_diario_20260430_100517>)

Resultado observado:

- `status_code = 200`
- ApisPeru devuelve XML
- `sunatResponse.success = false`
- error `2992`

Error real:

- `El XML no contiene el tag de la tasa del tributo de la linea`

Conclusion tecnica actual:

- el backend envia el payload
- ApisPeru responde
- pero el proveedor genera el XML del resumen sin `cbc:Percent` para IGV
- por eso `summary/send` no puede considerarse operativo hoy en beta

## Baja de boleta

Estado actual:

- **no operativa**

Prueba real mas reciente:

- [Pruebas/apisperu_bajas_full_artifacts_20260430_101912](</C:/Users/HP/Desktop/mi_proyecto_cotizaciones/Pruebas/apisperu_bajas_full_artifacts_20260430_101912>)

Resultado observado:

- `10/10` fallidas
- todas con error `2992`
- el comprobante base queda `facturada`, no `anulada`

Conclusion tecnica actual:

- la baja de boleta usa `summary/send`
- hereda exactamente el mismo bloqueo que `resumen diario`
- hoy no puede marcarse como operativa en beta

## Reversiones

Estado actual:

- **operativas**

Prueba real mas reciente:

- [Pruebas/apisperu_reversiones_full_artifacts_20260430_103430](</C:/Users/HP/Desktop/mi_proyecto_cotizaciones/Pruebas/apisperu_reversiones_full_artifacts_20260430_103430>)

Resultado observado:

- `10/10` aceptadas
- todas con `cdr_code = "0"`
- usan `reversion/send` y `reversion/status`

Observacion:

- en esta familia no existe hoy un PDF interno de Inkora equivalente al de facturas/boletas/notas
- si se guardo el PDF del proveedor, XML y CDR

## Retenciones y percepciones

Estado actual:

- **operativas**

Prueba real mas reciente:

- [Pruebas/apisperu_retenciones_percepciones_full_artifacts_20260430_110022](</C:/Users/HP/Desktop/mi_proyecto_cotizaciones/Pruebas/apisperu_retenciones_percepciones_full_artifacts_20260430_110022>)

Resultado observado:

- retenciones: `10/10` aceptadas
- percepciones: `10/10` aceptadas
- todas con `cdr_code = "0"`

Observacion:

- en estas familias no existe hoy un PDF interno de Inkora equivalente al de facturas/boletas/notas
- si se guardo el PDF del proveedor, XML y CDR por cada caso

- el backend envia el payload
- ApisPeru responde
- pero el proveedor genera un XML de resumen sin el nodo de tasa/percent del tributo IGV
- por eso `summary/send` sigue rechazado actualmente

En este momento, `resumen diario` no se puede considerar operativo como si lo estan `facturas`, `boletas` y `notas`.
