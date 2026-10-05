# Reenvío productivo autorizado de FA01-230

## Autorización y alcance

El usuario pidió expresamente reenviar la última factura emitida en producción
para observar el resultado. La lectura previa identificó FA01-230 de tenant 5,
documento 647, job 264, registro Smart PSE 445232. Se realizó **un solo POST** a
`https://panel.smartpse.pe/api/cpe/enviar` el 3 de octubre de 2026 entre 01:56:18
y 01:56:32 UTC (2 de octubre, 20:56 Lima).

La prueba usó directamente el contrato de envío de XML firmado de Smart PSE;
no pulsó el botón de reintento de Inkora ni ejecutó su worker. Por ello verifica
el comportamiento del proveedor, no reproduce íntegramente el reintento histórico.

- Misma identidad `20606751509-01-FA01-00000230`.
- Exactamente los mismos 7.556 bytes de XML firmado que Inkora y el panel guardaban.
- XML SHA256: `ad4213c1b48e5211888e1f126eb972fb4ece9f9e35d47206cdea8fdd04c0486f`.
- CDR original código 0; SHA256 `2703119c74c8ebd68bfa43abdd0919543d7631b50d45e404cecd6c7de6b794b5`.
- Firma e identidad del XML verificadas antes del envío. CDR y XML del panel
  idénticos a los de Inkora antes de la prueba.
- Sin regeneración, firma, nuevos correlativos, jobs, cambios de configuración,
  escrituras SQL, redirects ni reintentos automáticos. Secretos sólo en memoria.
- Un marcador exclusivo impide repetir la solicitud incluso ante un timeout.

## Resultado observado

HTTP **200**, JSON **estado 500**, `rechazado: false`. Respuesta:

> [1033] El comprobante fue registrado previamente con otros datos

El detalle identifica FA01-00000230 como informado anteriormente. La respuesta
**no contiene CDR ni XML**. La solicitud tardó 2,609 segundos.

El texto «otros datos» apareció pese a haberse enviado exactamente el XML
original. En este caso no demuestra cambio de número, contenido o firma.
Tampoco permite afirmar que el caso histórico comunicado por el usuario tuvo
la misma causa: aún no se identificó aquella factura ni su evidencia original.

## Efecto en el panel y estado posterior

La lectura posterior de Smart PSE a las 01:57:58 UTC muestra el registro único
445232 en **state `error`**, con el mensaje 1033 del reenvío, `has_cdr: true`
y `has_signed_xml: true`. No se ha corregido manualmente ese estado del proveedor.

El panel conserva exactamente los XML y CDR originales. Inkora continúa con
FA01-230 aceptada, job exitoso y su evidencia original sin cambios. El contador
de firmas se mantuvo en **306**. No se creó otro documento desde esta prueba.
No se consultó directamente SUNAT después del reenvío: la evidencia de aceptación
es el CDR original código 0 que permanece íntegro.

## Consecuencia para contingencia

1. Reenviar un documento ya aceptado no garantiza recuperar XML/CDR; aquí produjo
   1033 y cambió la presentación del registro en el panel a error.
2. Hay que conservar y validar el CDR original y consultar/recuperar evidencia
   después de un resultado ambiguo. El error de un intento posterior no debe
   degradar un documento cuya aceptación ya está acreditada.
3. La recuperación del panel lee CDR/XML disponibles independientemente de
   `state`; es relevante para este resultado observado.
4. El ensayo no resuelve el caso de un primer envío nunca recibido por SUNAT.
   No autoriza a habilitar reenvíos productivos generales ni la contingencia completa.
5. La etiqueta `error` en Smart PSE requiere aclaración/corrección del proveedor
   manteniendo el CDR original; no intentar repararla con más envíos.

No se modificó código de ejecución, desplegó una versión ni activó contingencia.
El 1033 de este ensayo debe distinguirse de una regresión del worker desplegado.

## Evidencia

- `pruebas/production_repeat_preflight.py`: identificación y comprobación de lectura.
- `pruebas/production_repeat_once.py`: solicitud única autorizada, sin reintentos.
- `pruebas/production-repeat-last-20261003/preflight.json`.
- `pruebas/production-repeat-last-20261003/result.json`.
- `pruebas/production-repeat-last-20261003/response-redacted.json`.
- `pruebas/production-repeat-last-20261003/panel-row-after.json`.
- Originales y descargas posteriores en esa misma carpeta; no contienen credenciales.

**No ejecutar nuevamente el harness ni borrar su marcador.**
