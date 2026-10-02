# Recuperación automática de evidencia Smart PSE

## Alcance autorizado el 2 de octubre de 2026

Habilitar primero recuperación de CDR para PAPELERÍA GRÁFICA Y PUBLICITARIA
(tenant 5). Mantener `FISCAL_CONTINGENCY_TENANT_IDS` vacío. Esta entrega no
habilita el flujo de firma y envío separado, ni resuelve reenvíos cuando SUNAT
nunca produjo un CDR. No reencolar trabajos históricos fallidos por rutina.

## Flujo

1. La emisión normal conserva su contrato actual y congela identidad, ambiente
   y datos del comprobante antes del envío.
2. Ante respuesta incierta, el worker consulta el resultado sin emitir de nuevo.
3. Para facturas 01 enroladas, si la consulta CPE devuelve 404 o no incluye CDR,
   se busca el documento exacto en el panel con una sesión autenticada.
4. Se exige empresa, RUC, tipo, nombre y ambiente originales. Sin ambiente
   congelado se bloquea esta recuperación: no se infiere desde la configuración
   actual. Los snapshots históricos pueden necesitar revisión individual.
5. Se descarga el CDR. Si falta XML local, se descarga también el XML del mismo
   documento. Se verifica firma y correspondencia fiscal con los datos congelados.
6. Sólo evidencia válida actualiza el estado y los artefactos de Inkora. El
   estado visual del panel no acredita aceptación. Un CDR de rechazo conserva
   su tratamiento de rechazo. Sin CDR se sigue pendiente.

La reconciliación no invoca `/procesar`, `/generar` ni `/enviar`, y no consume
correlativos. Una consulta 404 no autoriza reenviar: se observó ese resultado
incluso para facturas aceptadas. La persistencia conserva los controles existentes
de tenant, lease e idempotencia de cuota/documento.

## Configuración y secretos

Worker Railway, servicio `17a2668a-d2dc-4f77-a13e-b651ba1adbe5`:

- `SMARTPSE_PANEL_RECOVERY_TENANT_IDS=5` al activar el candidato validado.
- `SMARTPSE_PANEL_EMAIL` y `SMARTPSE_PANEL_PASSWORD`: secretos del panel, nunca
  credenciales SOL. La contraseña se introduce en un formulario local y se
  transmite a Railway por stdin del CLI, sin argumentos, archivos ni logs.
- `FISCAL_CONTINGENCY_TENANT_IDS` permanece vacío.

La API puede conservar el enrolamiento panel vacío: la recuperación automática
se ejecuta en el worker. El paquete de código y su huella sí son comunes a API,
worker y frontend. Configurar secretos con `--skip-deploys`; publicar por el
procedimiento canónico, no mediante un despliegue implícito de variables.

La sesión web permanece sólo en memoria, con TTL de 15 minutos, exclusión mutua,
una renovación por consulta y enfriamiento por autenticación fallida o límite
de uso. Origen HTTPS fijo, sin redirecciones externas, hasta cinco páginas,
4 MB por página y 2 MB por artefacto. Presupuesto de recuperación de 60 segundos
con timeout de lectura acotado; el aborto de una lectura bloqueada puede tardar
hasta el timeout vigente. No se comparte la sesión con otros procesos.

## Verificación y límites

Prueba externa permitida: leer FA01-228 existente; comparar CDR SHA256
`3783c5bcf7f553d20bb2c7f430652d0e25a7aed00c73754af1091c2ad07ec1f2` y validar XML
firmado. No modificar su estado ni provocar un error productivo para probar.
Los escenarios timeout → recuperación y documentos ajenos se ejercitan con
datos sintéticos. Una lectura de panel recupera evidencia histórica, no prueba
que el servicio de envío de SUNAT esté disponible; no abre ni cierra su circuito.

Las rutas web pertenecen al panel y no a un contrato API público estable. Un
cambio del proveedor debe fallar conservando el pendiente. Si el circuito SUNAT
está abierto, la programación existente puede diferir la siguiente consulta.
Esta fase cubre facturas; boletas, notas y guías conservan sus flujos actuales.

## Publicación y retirada

Usar `docs/RELEASE_CANONICO.md`, identidad remota verificada y una sola huella.
El recibo de despliegue debe registrar pruebas, paquete, tres despliegues y
activación efectiva; este documento por sí solo no acredita publicación.

Para retirar sólo esta función, vaciar `SMARTPSE_PANEL_RECOVERY_TENANT_IDS` del
worker y aplicar el cambio autorizado. Conservar todos los XML/CDR y estados.
Para rollback de aplicación usar los IDs del recibo anterior y comprobar primero
los trabajos activos. Nunca revertir datos, correlativos o evidencia fiscal.
