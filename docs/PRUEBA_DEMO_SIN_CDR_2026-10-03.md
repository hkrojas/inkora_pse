# Prueba real demo: XML firmado sin CDR y recuperación independiente

## Identidad y autorización

El usuario autorizó ejecutar las pruebas demo el sábado 3 de octubre, sin esperar
a soporte. Se utilizó exclusivamente la empresa 688, tenant 6, RUC 20610027351,
configurada en demo y comprobada por API y consulta PostgreSQL de solo lectura.
Serie dedicada `FCTG`, documento `FCTG-1`, registro del proveedor `447073`.
La empresa productiva 384 y su configuración no se modificaron.

Preflight vivo: identidad de empresa y tenant, ambiente demo activo, listado
vacío y ausencia del documento. Transporte con rutas permitidas explícitas,
redirecciones desactivadas, cero reintentos automáticos y marcadores exclusivos
con fsync antes de cada operación externa. Revisión independiente previa.

## Resultados externos

| Paso | Resultado comprobado |
|---|---|
| Solo firma `/api/cpe/generar-demo` | HTTP 200, XML firmado válido, sin CDR. Un único intento. |
| Listado del panel después de firmar | Registro 447073 en `firmado`, con XML, sin CDR ni ticket, ambiente demo. |
| Un POST del panel `/reintentar` desde `firmado` | HTTP 422. Se descartó el cuerpo intencionalmente; no se atribuye un motivo textual no observado. Sin CDR y contador sin cambio. No se repitió. |
| Primer envío API `/api/cpe/enviar-demo` | HTTP 200, estado 200, rechazado=false y CDR. No devolvió nuevamente XML. |
| Descartar evidencia de la respuesta en el cliente | La respuesta de envío no se usó para conciliar; el observador conservó únicamente metadata, nunca el CDR como fuente de recuperación. |
| Recuperación independiente desde el panel | CDR de aceptación código 0, identidad coincidente y XML idéntico byte a byte. |
| Invocar el conector de reintento sobre el aceptado | `cdr_available`, mismo CDR, cero llamadas al callback de envío y cero POST fiscales. El transporte prohibía POST fiscal. |

Contador `firmas_usadas`: 0 antes de la firma, 1 después de firmar y 1 después
de los intentos y recuperación. No se firmó de nuevo ni cambió la numeración.

XML original SHA256:
`972e4232102da6e6f1834c37f2c36f12bce1dffd97ebbc503e8b59b9619eee6b`.
CDR recuperado SHA256:
`c7d54871997be60552706d6e24ce20074a9706d7671153dadfcdefae552f97eb`.

La firma terminó a las 21:04 del 3 de octubre, hora de Lima, y el envío y
recuperación a las 21:13. Las evidencias registran las horas equivalentes UTC.

## Qué demuestra y qué no

### Alcance de la conclusión

Se comprobó un documento real demo que inicialmente tenía XML firmado y no
tenía CDR, su primer envío con el XML conservado, la recuperación independiente
de evidencia descartada y la prevención de otro envío una vez disponible el CDR.

La prueba encontró un límite concreto del panel: este intento desde `firmado`
recibió 422. No justifica ampliar el worker para reenviar cualquier estado. El
guard de producción permanece limitado a errores temporales explícitos.

Descartar la respuesta del cliente no equivale a provocar una caída de SUNAT
ni prueba que SUNAT no haya recibido el envío. Tampoco homologa reintentos
repetidos tras un resultado incierto. No se alteró un estado remoto ni se borró
un CDR para fabricar una caída. La validación de ese caso específico continúa
pendiente; las pruebas actuales sí reducen la incertidumbre del flujo seguro.

No se habilitaron flags remotos, no se desplegó código y no se escribieron datos
en la base productiva de Inkora. La factura existe únicamente como prueba demo
en Smart PSE; no es una emisión aceptada por SUNAT producción.

## Replay local del worker con evidencia real

Se reutilizaron exactamente `signed.xml`, `payload.json` y `recovered-cdr.xml`
en SQLite en memoria, tenant 6 y empresa demo 688. El worker, el CRUD de
persistencia fiscal, la validación criptográfica, QR, PDF, empaquetado del CDR y
consumo de cuota ejecutaron su código real. Los únicos reemplazos fueron los
clientes de transporte, la subida de artefactos y la fábrica de sesiones del
PDF, que apuntó a la misma base desechable.

La primera consulta local mantuvo el documento pendiente sin CDR: XML
entregable, QR calculado desde la firma real, PDF generado de 17 649 bytes y
cuota cero. La segunda recuperó el CDR real del panel sin devolver otro XML:
el documento y su cotización quedaron facturados, la firma original se conservó
y la cuota pasó a uno. Un segundo job independiente de consulta dejó la cuota
en uno y mantuvo exactamente el XML y CDR originales.

No hubo llamadas HTTP ni conexiones externas; firma, envío, procesamiento,
autenticación CPE y reintento fiscal tuvieron cero llamadas. El socket local
privado que Windows necesita para asyncio permaneció permitido.

Comando desde la raíz del worktree con Python 3.11: `python pruebas/pytest_offline.py ../pruebas/test_demo688_reconciliation.py -q`.
Resultado: **1 passed in 4.90s**. Evidencia:
`pruebas/demo688-reconciliation-local-20261003/result.json` y `pending.pdf`.
Esta parte comprueba la integración local con los artefactos del proveedor;
no constituye una ejecución del worker desplegado ni una prueba de concurrencia
PostgreSQL. La generación del PDF se verificó por código y contenido binario; no se hizo una revisión visual nueva de su diseño.

## Evidencias y ejecutores

En `pruebas/demo688-sign-only-20261003/`:

- `result.json`, `panel-after-sign.json`, `signed.xml`, `payload.json`.
- `panel-attempt-result.json`: intento único HTTP 422 y conciliación posterior.
- `send-once-result.json`, `recovered-cdr.xml`.
- `accepted-retry-guard.json`: retorno del CDR sin nuevo POST.

Ejecutores: `pruebas/demo688_sign_only.py`, `demo688_panel_attempt.py` y
`demo688_send_once.py`. Sus marcadores no deben borrarse para repetir acciones;
los modos `--run` quedan bloqueados después del primer intento.

## Referencia externa

La documentación oficial distingue la operación de solo firma y sus rutas demo:
https://smartpse.pe/documentacion y
https://smartpse.pe/blog/como-integrar-pse-api-facturacion.
Los resultados de crédito reportados arriba proceden de la medición de esta
prueba; las dos páginas consultadas no son consistentes sobre el cobro demo.
