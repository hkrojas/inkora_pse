# Homologación Smart PSE en demo — 2 de octubre de 2026

## Resultado

Firma, envío del mismo XML, CDR de prueba y PDF comprobados con el proveedor
real en demo. Ese resultado no acredita aceptación fiscal productiva. El CDR
demo contiene placeholders de certificado/firma beta y no constituye una firma
SUNAT verificable. Recuperación mediante consulta de factura **no homologada**: la API
devuelve HTTP 404 para documentos aceptados que sí aparecen en el panel con CDR.
El flujo separado de contingencia sigue sin empresas habilitadas en producción.

La revisión posterior distingue el resultado observado de su causa: Inkora
utilizó para facturas una ruta documentada para tickets de resúmenes y GRE.
Su compatibilidad con búsqueda de facturas no está demostrada. No se atribuye
el 404 a un defecto del proveedor sin confirmar primero ese contrato.

## Autorización, fuente y aislamiento

El usuario confirmó el cierre de emisiones del día y autorizó iniciar las
pruebas demo; también autorizó trabajo con agentes y lectura del panel abierto.
La cola productiva no tenía trabajos queued, processing, retry o
contingency_pending ni facturas pending_confirmation. Las dos guías históricas
pending_confirmation están excluidas de la recuperación automática del worker.

- Main remoto verificado: `b41d5e8cdbe4ae96e133dbd3c2eaccd9cb216e25`.
- Su árbol coincide con la base desplegada `45bc2b58d1ec76378b8cc50e78f6c3e920cb180a`.
- Huella productiva conservada: `8650ea89ad8ed357863bb0cf29533047d62a33c988bba00d788095f2094fb6b8`.
- Correcciones locales: rama `codex/smartpse-demo-consult-guard`, worktree limpio
  desde ese main. La raíz histórica no se utilizó como árbol de implementación.
- Aplicación y worker de la prueba usaron SQLite local y archivos locales;
  PostgreSQL productivo se consultó mediante transacciones de solo lectura.
- Credenciales remotas permanecieron en memoria. El tenant local usa credenciales
  sintéticas; no se copiaron credenciales productivas a SQLite ni archivos.
- Allowlist HTTP del harness: autenticación, lectura/cambio del ambiente de la
  empresa seleccionada y rutas demo para una sola identidad `FDEM-00000001`.
- Se cambió temporalmente el ambiente de esa empresa en Smart PSE a demo y se
  restauró a producción dentro de finally, con lectura de confirmación posterior.
- No se crearon comprobantes FDEM en Inkora productivo ni se consumieron sus
  correlativos. El contador de firmas del proveedor pasó de 304 a 305.

## Evidencia real

| Comprobación | Resultado |
| --- | --- |
| POST `/api/cpe/generar-demo` | HTTP 200; XML firmado recibido y verificado criptográficamente |
| PDF antes del envío | Generado con QR y sin CDR; marca DEMO visible agregada por el harness |
| POST `/api/cpe/enviar-demo` | HTTP 200; se envió base64 del XML extraído, sin volver a firmar |
| CDR | Código 0, referencia FDEM-00000001 y RUC coincidentes |
| Worker local | Un intento; job succeeded, documento facturada y verificación verified |
| Panel Smart PSE | Documento 444951, entorno Demo, Aceptado, XML y CDR disponibles |
| CDR descargado del panel | Coincide byte a byte con el recibido mediante la API |
| QR y PDF | Ambos PDF A4 de una página; QR coincide con el payload fiscal; no declaran aceptación |
| Restauración | Empresa remota activa en producción; cola productiva sin trabajos nuevos |

La marca DEMO se aplicó a los artefactos locales del harness. No se modificó
el generador productivo ni se declara que automáticamente marque los PDFs demo.
El PDF previo y posterior al CDR tiene la misma representación visual.

## Hallazgos y correcciones locales

### 1. HTTP 404 no acredita ausencia fiscal

La consulta `/api/cpe/consultar/{nombre_archivo}` devolvió `Documento o ticket no
encontrado` para FDEM-00000001 después de recibir su CDR. Ocurrió mientras la
empresa estaba en demo; añadir `environment=demo` en el cuerpo de otra consulta
tampoco resolvió el caso. Una lectura de la factura productiva FA01-229, ya
aceptada con CDR, produjo el mismo 404. No se reenviaron estos documentos.

Se retiró la rama que interpretaba ese 404 como permiso para enviar nuevamente.
Los trabajos conservan su XML y estado pendiente de conciliación. Los snapshots
heredados con `retry_signed_after_not_found` también pasan a consulta y pierden
esa autorización. Una factura firmada que todavía no intentó enviarse conserva
su primer envío permitido.

### 2. Normalización alteraba la huella del XML conservado

El XML real firmado terminaba con un salto de línea. La normalización de XML
plano aplicaba strip al guardar la respuesta de envío, cambiando su SHA256 sin
actualizar la evidencia original. La firma criptográfica seguía siendo válida,
pero en estado pendiente el PDF podía perder la condición de entregable.

Se conserva el texto original completo al reconocer XML plano. La detección
del formato puede inspeccionar una copia sin espacios; el XML devuelto conserva
sus bytes UTF-8, incluidos LF/CRLF. La lógica de CDR no se modificó.

## Verificación local

- El caso de preservación reprodujo tres fallos antes del fix.
- 35 pruebas aprobadas: preservación XML, normalización Smart PSE y contingencia.
- 63 pruebas adicionales aprobadas: `test_emission_queue.py`,
  `test_document_actions_consistency.py`, `test_document_actions_recovery.py`
  y `test_fiscal_page_endpoints.py`. Total: 98 pruebas distintas aprobadas.
- Relectura offline de la respuesta real del proveedor con el normalizador
  corregido: mismo XML y SHA256, firma válida, CDR coincidente y PDF entregable
  en estado pendiente. Resultado: `pruebas/real-demo-evidence-replay.json`
  en el worktree de la corrección. No realizó llamadas externas.
- `git diff --check` aprobado. No hubo cambios de frontend ni migraciones;
  todavía no se ejecutó una puerta de integración/publicación completa.
- No se hicieron nuevas firmas para probar los fixes: las regresiones son
  offline y utilizan certificados sintéticos o evidencia previamente recibida.

## Pendiente antes de habilitar

Primero debe confirmarse con Smart PSE el mecanismo admitido para consultar facturas
que devuelva el estado y CDR de una identidad ya enviada. El enlace del panel
requiere una sesión de navegador y no constituye un contrato API homologado para
el worker. Un timeout seguido de 404 debe permanecer incierto, sin reenvío.

Estas correcciones locales no fueron fusionadas ni desplegadas. La evidencia
principal permanece en el worktree de la prueba, bajo
`pruebas/smartpse-demo-20261002/`: report.json, sign-response.json,
send-response.json, consult-diagnostics.json, panel-verification.json,
signed.xml, cdr.xml, signed-pending.pdf, accepted.pdf y demo.sqlite.
Inspección visual y QR: `pruebas/demo-evidence-review/inspection.json`.

Contrato consultado: [documentación de Smart PSE](https://smartpse.pe/documentacion)
y [guía de integración](https://smartpse.pe/blog/como-integrar-pse-api-facturacion).
Los resultados reales tienen prioridad sobre las ambigüedades entre ambas páginas.

## Consulta concreta para soporte del proveedor

La factura demo FDEM-00000001 figura aceptada en el panel (documento 444951)
y cuenta con CDR código 0 obtenido por `/api/cpe/enviar-demo`. Sin embargo,
`GET /api/cpe/consultar/{RUC}-01-FDEM-00000001` devuelve HTTP 404 con
`Documento o ticket no encontrado`, incluso estando la empresa en demo.
Una consulta de la factura productiva FA01-00000229, también aceptada y con
CDR en el panel (documento 444844), responde igual. ¿Cuál es el endpoint
soportado, autenticación y formato para recuperar estado y CDR de facturas 01
por identidad, tanto en demo como producción, tras perder la respuesta del envío?
¿Qué respuesta permite distinguir ausencia comprobada de una consulta no soportada?

Este texto es un borrador local; no se envió ningún mensaje al proveedor.

## Revisión de conexión posterior a la observación del usuario

Se auditó el cliente local y se realizaron tres lecturas remotas acotadas,
además de obtener un token CPE nuevo, sin cambiar ambientes ni emitir documentos.
Evidencia: `pruebas/smartpse-demo-20261002/connection-audit.json`, 20:26 UTC.

- Host comprobado: `https://panel.smartpse.pe`; sin redirecciones HTTP.
- GET de la empresa 384: credenciales CPE coincidentes con Inkora, comparación
  en memoria sin registrar secretos; empresa y runtime en producción.
- POST de autenticación CPE: HTTP 200. Consulta con Bearer CPE nuevo,
  Accept y Content-Type application/json; sin cuerpo ni query adicionales.
- El snapshot del job 263 coincide literalmente con la identidad del documento
  FA01-229: `20606751509-01-FA01-00000229`.
- GET con ese nombre y GET con el sufijo `.xml`: ambos HTTP 404 JSON,
  `Documento o ticket no encontrado`. Se registraron URL, hora, ambiente y
  respuesta saneada para que el diagnóstico sea reproducible.
- Offline, un espía de transporte confirmó el mismo método, ruta y tipo de
  autenticación del cliente. No se detectó un error determinista de RUC o
  numeración en la factura demo original; su consulta ocurrió mientras la
  empresa estaba en demo.

El GET anterior con cuerpo `environment=demo` no demuestra selección efectiva
del ambiente: ese parámetro no está documentado para esta consulta de facturas.
Los enlaces `/panel/documentos/{id}/cdr` utilizan sesión de navegador; no se
extrapolan como un endpoint público para el worker.

Conclusión limitada: conexión/autenticación y construcción del identificador
comprobadas; contrato de recuperación de facturas aún sin confirmar. El uso de
`consultar` como búsqueda general de facturas fue una extrapolación de Inkora.
Las protecciones locales contra reenvíos basados en 404 siguen siendo necesarias,
independientemente de cómo se resuelva el contrato. No se añadieron cambios de
código durante esta segunda auditoría.

### Contraste final con el panel y autenticación

- La respuesta de la lista del panel identifica el documento 444951, empresa
  384, como `20606751509-01-FDEM-00000001`, tipo 01, ambiente demo,
  `ticket=null` y `has_cdr=true`. El nombre coincide exactamente con la consulta.
  El estado de aceptación demo no acredita aceptación fiscal productiva.
- La autenticación CPE real devuelve un Bearer opaco, no un JWT que permita
  inspeccionar claims. No se deduce el alcance a partir de claims inexistentes.
  Evidencia saneada: `pruebas/smartpse-demo-20261002/auth-scope-audit.json`.
- A las 20:33 UTC se hizo una lectura adicional de la misma factura productiva
  FA01-00000229 usando el token administrativo: HTTP 401, sin redirección ni
  CDR. Con el Bearer CPE nuevo la respuesta había sido HTTP 404. Cambiar al
  token administrativo no resuelve esta consulta. Evidencia saneada:
  `pruebas/smartpse-demo-20261002/alternate-auth-audit.json`.
- No se identificó otra ruta pública documentada de Smart PSE para esta
  recuperación. Las rutas de FactuSmart pertenecen a otro contrato, dominio
  y autenticación; no se probaron como si fueran compatibles.

Se solicitó autorización al usuario para enviar la consulta técnica al WhatsApp
de soporte enlazado en el panel. A la fecha de esta actualización no se envió
ningún mensaje. La recuperación automática completa sigue pendiente de un
contrato confirmado; estas verificaciones no habilitan la contingencia.

### Consulta de otras facturas productivas existentes

Por solicitud del usuario se amplió la muestra a FA01-227 y FA01-228, jobs
261 y 262 del tenant 5. A las 20:52 UTC del 2 de octubre se obtuvo un Bearer
CPE nuevo y se consultó cada identidad canónica una sola vez por GET: ambas
respondieron 404, `Documento o ticket no encontrado`, sin CDR. Inkora ya
las tenía facturadas, verificadas y con CDR. No hubo firma, envío ni cambios
de ambiente, documentos, estados o correlativos.

Se descargaron los CDR mediante los enlaces visibles del panel para los
documentos 443611 y 444364. Esto comprueba que el panel permite recuperar
la evidencia de facturas existentes, pero no acredita autenticación CPE
para esas rutas de navegador ni una integración autónoma del worker.

Ambos CDR tienen código 0, identidad coincidente y son idénticos byte a byte
a los guardados en Inkora. Además se consultó el enlace exacto observado de
FA01-228 usando solo Bearer CPE, sin cookies del navegador: devolvió HTTP 302
a `/login`, sin CDR. Esta comprobación confirma que ese enlace no funciona
con la autenticación CPE usada por el worker. Evidencia adicional:
`pruebas/smartpse-demo-20261002/existing-panel-cpe-auth.json`.

Evidencias saneadas en el worktree de homologación:
`pruebas/smartpse-demo-20261002/existing-invoices-read.json` y
`pruebas/smartpse-demo-20261002/existing-invoices-cdr-comparison.json`.

## Prototipo de recuperación mediante sesión del panel

El 2 de octubre se probó un conector local independiente del navegador abierto.
El usuario introdujo sus credenciales en un formulario loopback; contraseña y
cookies se conservaron únicamente en memoria y la sesión se cerró al terminar.
El formulario no registra cuerpos de peticiones ni guarda las credenciales.

Resultado real: login HTTP 302 a `/dashboard`, lectura de documentos HTTP 200
(`Client/Documents/Index`) y recuperación del CDR de FA01-00000228, empresa 384,
documento Smart PSE 444364, ambiente producción. Se validaron empresa, identidad
y código 0 del CDR. Su SHA256 es
`3783c5bcf7f553d20bb2c7f430652d0e25a7aed00c73754af1091c2ad07ec1f2`,
idéntico al archivo descargado anteriormente y contrastado con Inkora.
Este prototipo no realizó verificación criptográfica independiente de la firma
del CDR. No emitió, reenvió ni modificó estados o documentos productivos.

El primer intento descartó indebidamente una redirección que no comenzara por
`/panel`. Se corrigió para comprobar acceso a la ruta conocida de documentos,
sin seguir destinos arbitrarios. Tres casos offline verifican redirecciones
de entrada a `/`, `/dashboard` y `/panel`. Cuatro casos negativos adicionales
bloquean CDR de otra empresa, otro número, HTML de login y cruce de empresa.

Evidencia saneada en este worktree: `pruebas/smartpse-panel-probe-result.json`.
Prototipos aislados en `pruebas/smartpse_panel_probe.py` y
`pruebas/smartpse_panel_probe_form.py`. No están integrados en el worker ni
desplegados. Esta prueba demuestra recuperación por sesión del panel para un
documento existente; no homologa aún renovación de sesión, cambios del panel,
concurrencia, documentos ausentes o actualización fiscal productiva. El
enrolamiento de contingencia permanece vacío.
