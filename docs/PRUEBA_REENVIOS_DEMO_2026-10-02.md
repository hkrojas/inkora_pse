# Prueba real de reenvíos demo — 2 de octubre de 2026

## Alcance autorizado y aislamiento

El usuario solicitó probar reenvíos en varias demos y preguntó si se podía probar
con una factura productiva ya emitida. Se ejecutaron tres escenarios sobre **la
misma factura demo FDEM-1 existente**, no sobre tres facturas distintas. No se
interpretó la pregunta como autorización para reenviar un documento productivo.

- Seis POST exclusivamente a `/api/cpe/enviar-demo`, sin redirects ni reintentos
  automáticos del transporte. Marcadores exclusivos impiden repetir la ejecución.
- Mismo nombre `20606751509-01-FDEM-00000001` y mismos 7.776 bytes de XML firmado.
- SHA256 XML: `03a83441c03e91fe45d91c36526a71703c5a45705ac7ca46e8ca2a07a50c8430`.
- No llamadas de firma, cambios de ambiente, creación de documentos en Inkora,
  consumo de correlativos productivos ni escrituras en PostgreSQL. Consultas DB
  con transacción explícitamente de sólo lectura. Credenciales sólo en memoria.
- Empresa 384 permaneció activa en producción; el documento 444951 permaneció
  en ambiente demo. El uso del endpoint demo sin cambiar la empresa conserva la
  observación de la prueba anterior; no se extrapola a otras rutas.

## Resultados observados

Ejecución: 3 de octubre 01:17–01:18 UTC, equivalente al 2 de octubre 20:17–20:18 Lima.

| Escenario | Solicitudes | Resultado |
|---|---:|---|
| Reenvíos consecutivos | 2 | Ambas HTTP 200, estado 200, CDR de aceptación código 0 |
| Respuesta descartada por consumidor local y repetición | 2 | Ambas HTTP 200, estado 200, CDR código 0 |
| Dos reenvíos simultáneos del mismo XML | 2 | Una aceptación con CDR 0; otra HTTP 200 con `estado: 500` y `rechazado: false` |

La segunda prueba simula que la aplicación no consume una respuesta que el
observador de la prueba sí recibió. **No reproduce una caída real de SUNAT ni un
timeout de red.** Todos los reenvíos corresponden a un documento ya aceptado en demo.

El resultado global del harness es **fallido**, porque no todas las solicitudes
simultáneas devolvieron aceptación. No se ocultó ese resultado ni se reintentó la
solicitud fallida. El detalle textual del error no fue conservado por el harness;
la causa interna concreta no puede atribuirse a SUNAT o Smart PSE con esta evidencia.
La respuesta `estado: 500` no fue procesada para extraer CDR: no se afirma que
careciera de él. No confundir ese estado del JSON con un HTTP 500.

## Lectura posterior al error, sin nuevos envíos

Se recuperaron nuevamente XML y CDR del panel a las 01:18:50–01:19:00 UTC:

- Registro único coincidente: 444951, ambiente demo.
- XML idéntico byte a byte al original.
- CDR coincide exactamente con la solicitud simultánea aceptada:
  `c542d2e516cfef5fd24f3d70ed75ceb1f0028c19c0cf57ec19ca703a17b73449`.
- Contador de firmas: **306 antes y después**.
- Cola de Inkora sin cambios: 240 trabajos exitosos, 20 fallidos históricos y
  dos pendientes de confirmación; último job 264. No se agregaron documentos.

Las cinco respuestas aceptadas contienen CDR y no XML. Los cinco CDR tienen
huellas distintas, todos referidos a la misma identidad con código 0. Reenviar
no devuelve necesariamente los mismos bytes de la constancia anterior. Inkora
debe conservar su XML y CDR originales válidos.

## Consecuencia para la implementación

El reenvío secuencial del mismo XML funciona en estos casos demo. El ensayo
simultáneo confirma que no se puede asumir una respuesta exitosa para cada
petición concurrente. Son necesarios la exclusión por documento, las reservas
del worker y la conciliación: un error de envío no basta para declarar rechazo
ni para reemplazar un CDR de aceptación ya conservado.

Esto no homologa reenvíos productivos ni la situación de un primer envío sin
CDR o con respuesta perdida. La [guía oficial de Smart PSE](https://smartpse.pe/blog/como-integrar-pse-api-facturacion)
describe `/enviar` y el entorno beta, pero no garantiza en esa página el resultado
de repetir un documento productivo aceptado. Antes de usar una factura real para
una prueba debe confirmarse ese comportamiento con el proveedor y obtenerse
autorización explícita para esa operación productiva.

## Evidencia local

- `pruebas/demo_resend_matrix.py`: harness revisado por un segundo agente.
- `pruebas/demo-resend-matrix-20261003/result.json`: seis solicitudes y resultado fallido.
- `pruebas/demo-resend-matrix-20261003/preflight.json`: última lectura posterior sin envíos.
- `pruebas/demo-resend-matrix-20261003/*-cdr.xml`: cinco CDR demo aceptados.
- `pruebas/demo-matrix-run.log` y `pruebas/demo-matrix-after-read.log`.

No se modificó código productivo ni se publicó una versión como parte de esta prueba.

## Evidencia adicional del historial, 3 de octubre

Una lectura posterior de la ruta oficial de historial identifica, en la misma
ventana de los dos envíos simultáneos, un evento `error` con mensaje
`[HTTP] Unauthorized` (1165038) y otro `aceptado` (1165039), ambos a las
01:18:04 UTC. No se hicieron nuevos envíos para obtener esta información.

Esto aporta el mensaje registrado por el panel, pero no recupera el cuerpo de
la respuesta HTTP original ni demuestra si el fallo de autorización se originó
en Smart PSE o en SUNAT. El historial observado no contiene identificadores de
solicitud; por ello no se atribuye cada evento a una conexión concreta ni se
considera homologada la repetición automática de un POST incierto.

Evidencia: `pruebas/panel-history-readonly-20261003.json` y
`pruebas/panel-history-extra-shape-20261003.json`.
