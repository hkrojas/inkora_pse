# Error inducido en demo — 5 de octubre de 2026

El usuario autorizó provocar un error mediante una factura demo. Se utilizó
únicamente la empresa 688 del tenant 6, RUC 20610027351, comprobada en demo
por API y consulta PostgreSQL de sólo lectura. Se reservó una serie exclusiva,
FERR-1, distinta de FCTG-1/FCTG-2. La única alteración fue UBLVersionID 9.9
en el XML de prueba; no se modificaron configuraciones, credenciales o documentos
aceptados. Los marcadores de inicio impiden repetir firma/envío tras perder respuesta.

## Resultado externo

- Un POST `/api/cpe/generar-demo`: HTTP 200, XML firmado validado, sin CDR.
- Un POST `/api/cpe/enviar-demo`: HTTP 200, cuerpo `estado: 500`,
  `rechazado: true`, error 2074, sin XML/CDR/ticket en la respuesta.
- El panel creó el documento 450164 en `rechazado`, con XML firmado,
  sin CDR/ticket y sin error temporal elegible.
- El conector no habilita reintento de esa fila; no se ejecutó POST del panel.
- Firmas usadas: 2 antes, 3 después. Una firma demo consumida.
- XML firmado SHA256:
  `c5167eb3b0cf19b115a0635ce418cc71ef083b5f19352ce193bc26f0738da019`.

No hubo llamadas fiscales productivas ni escrituras en Inkora. La factura existe
únicamente como prueba negativa en Smart PSE demo. No se repitió el envío ni se
corrigió/regeneró para obtener artificialmente un resultado diferente.

Esta prueba demuestra un rechazo real sin CDR. No provoca ni homologa una caída
de SUNAT: el documento se construyó intencionalmente con una versión inválida.
La documentación oficial distingue rechazos de validación previa sin CDR de
rechazos con constancia y recomienda reintentar sólo fallos temporales:
https://smartpse.pe/documentacion.

## Clasificación del worker

El valor `estado: 500` del cuerpo no es el código HTTP de esta llamada, que fue
200. Una prueba local adicional reconstruye la forma de la respuesta observada
con un mensaje sintético del error 2074: no activa el circuito compartido, no
reenvía, no consume cuota ni marca aceptación. Al faltar CDR, el estado local
mantiene conciliación; no se presenta como un rechazo fiscal acreditado por CDR.

Prueba: `test_demo_observed_2074_body_estado_500_is_not_http_outage` en
`backend/test_panel_retry_worker.py`. Resultado: 1 aprobada, 64 no seleccionadas
en 4,15 s. Evidencia: `pruebas/demo-negative-2074-worker-20261005.log`.

Evidencia externa saneada: `pruebas/demo688-negative-ubl-20261005/result.json`,
`payload.json`, `unsigned.xml`, `signed.xml`, `sign.marker` y `send.marker`.
Los cuerpos completos de respuesta y credenciales no se conservaron.

Sigue pendiente la respuesta de un reintento real ante un fallo temporal de
disponibilidad. El catálogo público revisado no ofrece una opción para provocar
esa caída en demo. Enviar otros documentos inválidos produciría pruebas de
validación, sin resolver ese contrato pendiente.

## Reintento del mismo FERR-1 — 10:04–10:05 Lima

El usuario autorizó continuar conservando la serie. Se ejecutó una sola prueba
manual del POST del panel sobre el documento demo 450164 ya rechazado. Es una
comprobación externa del contrato; el worker automático sigue bloqueando los
reintentos de rechazos de validación. No se crearon más documentos o series.

- HTTP 200, `Content-Type: application/json`.
- Respuesta con claves exactas `ok`, `message`, `state`.
- `ok: false`, `state: rechazado`, mensaje del error 2074.
- Documento y ambiente conservados; sin CDR.
- XML idéntico byte a byte al firmado originalmente.
- Firmas usadas: 3 antes y 3 después. El POST no volvió a firmar en este caso.
- La respuesta no se clasifica como fallo temporal y no habilita otro intento.

Evidencia: `pruebas/demo688-negative-ubl-20261005/panel-contract-result.json`
y `panel-contract.marker`. El estado del cuerpo se reconstruyó localmente
desde los campos ya conservados; la coincidencia exacta con el SHA256 del
cuerpo original acredita esa reconstrucción, sin repetir el POST.

La prueba reveló una incompatibilidad local: el parser sólo admitía `ok` y
`message`, por lo que el campo adicional `state` impediría reconocer también
un fallo temporal. Se corrigió para admitir ese campo exclusivamente con
valor `error` y mensaje temporal explícito; cualquier estado rechazado,
aceptado, pendiente, desconocido o mal formado conserva la consulta.
La variante `state: error` con mensaje temporal sigue siendo sintética;
la respuesta externa comprobada fue `state: rechazado` y error 2074.

Las pruebas del cliente, secuencia del worker y replay con XML/CDR demo
aprobaron 213 casos en 7,84 s. Evidencia:
`pruebas/demo-panel-state-contract-20261005.log`. Los archivos de producción
no se publicaron. El candidato local actualizado tiene huella
`95c7a5e79745f8e898c404eba77075750bd0540289feec263cd844fe6cff5c28`;
features, assets, importaciones e inclusión del módulo aprobaron sobre 382
archivos. No es un paquete publicable; conserva los controles de integración.
