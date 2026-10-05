# Contingencia: preparación y primer caso productivo

## Decisión y estado

El 5 de octubre el usuario indicó que el fallo temporal real se comprobará
cuando ocurra naturalmente en producción y que, por ahora, se deje preparado.
No se requieren más emisiones demo ni series para cerrar esta preparación.
La serie demo FERR y sus evidencias existentes se conservan.

El candidato está implementado en `codex/contingency-send-phases`, sin commit,
integración ni publicación. Este documento actualiza el estado operativo de
los informes anteriores; no acredita un despliegue ni la homologación de una
respuesta temporal real del proveedor.

- Base remota comprobada: `c336060527eafc9f438633557d85c9a936e83313`.
- Huella del contenido local revisado:
  `95c7a5e79745f8e898c404eba77075750bd0540289feec263cd844fe6cff5c28`.
- Identificación local: `pruebas/contingency-integrated-review-content-20261005.json`.
  Es una revisión de contenido, no un manifiesto de publicación.
- Alcance inicial: facturas tipo 01. La recuperación CDR publicada para tenant 5
  y la contingencia nueva son entregas distintas.

## Flujo preparado

Corrección durante el cierre de publicación: la API impone cola durable para
facturas tipo 01 del tenant incorporado, incluso si un cliente solicita
`mode=sync` o el default del ambiente fuera sync. El tenant procede del usuario
autenticado. Ocho pruebas aprobaron, incluidas tres llamadas al router real que
crean un único documento/job sin contactar al proveedor. Los demás tipos y
empresas conservan su contrato. La huella inicial indicada arriba se sustituye
por la del paquete canónico del recibo de despliegue.

1. Congelar empresa, ambiente, identidad y datos de la factura. Firmar una vez,
   validar y conservar el XML. Preparar PDF/QR con esos datos aunque falte CDR.
2. Registrar duraderamente el posible envío antes de HTTP. Usar el mismo XML,
   serie y correlativo; no crear otra factura como recuperación.
3. Ante una caída de transporte comprobada, coordinar la pausa de las empresas
   incorporadas en el circuito del mismo servicio y ambiente. Una sola reserva
   prueba la recuperación; primera espera de 15 minutos, siguientes de 30.
   Firma y envío tienen circuitos separados. Un error de validación individual
   o un campo JSON `estado: 500` no demuestra una caída compartida.
4. Consultar primero el resultado existente. Recuperar XML/CDR del panel cuando
   corresponda, validando identidad y firma. Un 404 o la falta de CDR no permite
   concluir que el primer envío nunca llegó.
5. El reintento del panel requiere todos los permisos y flags, un registro con
   error temporal concreto, XML idéntico, ausencia de CDR/ticket y plazo vigente.
   Guardar el intento y su secuencia antes del POST al registro existente.
6. Una respuesta explícita compatible de fallo temporal confirma el fin de ese
   intento y permite otro después de 15/30 minutos, con nueva consulta previa.
   Una respuesta perdida, desconocida o contradictoria mantiene consultas y
   bloquea nuevos POST automáticos de ese historial.
7. Sólo un CDR correspondiente al documento determina el resultado fiscal.
   Actualizar documento y cotización, conservar artefactos y aplicar la cuota
   una sola vez. Al vencer el plazo, detener firma/envíos y continuar consultando
   los intentos previos, dejando alerta de auditoría.

El circuito del panel no se usa como prueba de recuperación de la API. El PDF
pendiente representa los datos firmados; no afirma aceptación de SUNAT.

## Configuración preparada para la primera empresa

La siguiente tabla es el objetivo para una habilitación posterior del tenant 5,
PAPELERÍA GRÁFICA Y PUBLICITARIA. No se aplicaron estos cambios remotos.

| Variable | API | Worker |
|---|---|---|
| `FISCAL_CONTINGENCY_TENANT_IDS` | `5` | `5` |
| `SMARTPSE_PANEL_RECOVERY_TENANT_IDS` | vacío | `5` |
| `SMARTPSE_PANEL_RETRY_TENANT_IDS` | vacío | `5` |
| `SMARTPSE_PANEL_EMAIL`, `SMARTPSE_PANEL_PASSWORD` | sin configurar para este flujo | verificar presencia de las credenciales existentes, sin imprimir valores |
| `FISCAL_RECOVERY_FIRST_SECONDS` | `900` | `900` |
| `FISCAL_RECOVERY_MAX_SECONDS` | `1800` | `1800` |

Conservar el worker actual: `run_emission_worker.py`, modo `notify`, concurrencia
1 y límites existentes. No hace falta crear otro servicio para este alcance.
La empresa conserva su ambiente productivo original; no cambiarla a demo.
Usar IDs explícitos; no incorporar todas las empresas con `*` durante el piloto.
Verificar también la pausa manual vigente de la empresa antes de habilitarla.

## Antes de publicar

1. Revalidar remoto y despliegue vigente. Si `main` avanzó, integrar sus cambios
   en este candidato y revisar su compatibilidad antes de generar un paquete.
2. Cerrar revisión e integración con los controles de `RELEASE_CANONICO.md`,
   incluidos contratos, regresión pertinente y PostgreSQL local para concurrencia.
   Las pruebas previas quedan registradas en los informes enlazados abajo;
   cualquier cambio posterior requiere comprobar su efecto.
3. Generar el paquete canónico desde un candidato registrado y limpio, verificar
   su nueva huella y conservar los IDs de la entrega productiva anterior.
   No publicar la raíz histórica ni usar esta huella local como aprobación de paquete.
4. Publicar API compatible primero, worker y frontend con el mismo contenido.
   Verificar salud, arranque real del worker y huella en los tres servicios.
5. Habilitar la primera empresa por separado, con autorización de publicación
   y habilitación. Resolver el control de staging del alcance crítico; la
   excepción anterior autorizada por el usuario fue un despliegue gradual.
   La decisión de observar un fallo natural no sustituye los controles locales
   ni implica que ya se hayan cambiado las variables productivas.

No se requiere una migración nueva para este candidato. La tabla de circuitos
de 0026 ya existe; comprobar su presencia y acceso por lectura antes de publicar.

## Observar el primer fallo natural

Registrar una ventana acotada, tenant/documento/job y la versión desplegada.
Usar logs recientes y, si está disponible, una transacción de sólo lectura.
No forzar el fallo, consumir correlativos de prueba ni repetir facturas aceptadas.

| Comprobación | Evidencia esperada |
|---|---|
| Clasificación del fallo | HTTP real, origen API/panel y categoría; distinguir error temporal de rechazo/validación |
| Documento entregable | XML firmado validado, huella conservada, mismo monto/productos/serie/número y PDF/QR disponibles |
| Pausa compartida | scope del servicio/ambiente, `next_probe_at` y una sola reserva de prueba cuando el circuito esté abierto |
| Reintento | auditorías `fiscal_panel_retry_started` y `fiscal_panel_retry_completed`, UUID/secuencia/predecesor y siguiente hora permitida |
| Respuesta del proveedor | `panel_retry_status`; para fallo temporal confirmado, hash del cuerpo y mensaje sanitizado; nunca secretos ni sesión |
| Resultado incierto | consultas activas, sin una nueva tentativa automática posterior al intento ambiguo |
| Resultado final | CDR verificado, estado sincronizado en Inkora, artefactos conservados y cuota aplicada una sola vez |

Si la respuesta real difiere del contrato estricto local, el sistema conserva
conciliación. Registrar la diferencia sanitizada y ajustar el parser en otro
bloque revisado; no ampliar automáticamente mensajes ni estados permitidos.
El primer caso debe distinguirse de fallos históricos que carecen de ambiente
congelado y marcadores; no reencolar esos documentos para fabricar una prueba.

## Contención si se detecta un problema

- Para detener nuevos reintentos del panel, retirar el ID de
  `SMARTPSE_PANEL_RETRY_TENANT_IDS` en el worker mediante una acción operativa
  autorizada. Mantener recuperación de CDR y consultas.
- Para detener nuevas incorporaciones a contingencia, retirar el ID de
  `FISCAL_CONTINGENCY_TENANT_IDS` en API y worker. Los trabajos ya iniciados
  conservan `recovery_flow`: no regresan a `/procesar` como si fueran nuevos.
  Retirar también el flag de reintento para detener sus POST.
- Un cambio de variables no cancela un POST que ya está en vuelo. Consultar su
  resultado; no eliminar marcadores, auditoría, XML ni CDR.
- El retorno a una aplicación anterior exige revisar que entienda los nuevos
  snapshots antes de reiniciar su worker. Si no es compatible, detener el worker
  durante la intervención y resolver conciliación con una versión compatible.
  No ejecutar rollback automático ni restaurar datos fiscales/correlativos.

## Evidencias existentes y pendiente externo

La revisión adicional del 5 de octubre comprobó por lectura las barreras de
enrolamiento, CDR antes de POST, retirada de retry y bloqueo tras respuesta
perdida; no encontró nuevos P1 en ese alcance. La identificación local de las
15:18 UTC confirmó la misma huella, 382 archivos, assets, funcionalidades,
cierre de imports e inclusión del nuevo módulo. `git diff --check` aprobó y
el remoto conservaba la base indicada. No se repitieron suites ni se hicieron
peticiones fiscales como parte de este cierre documental.

- `VALIDACION_CONTINGENCIA_WORKER_2026-10-03.md`: regresión, PostgreSQL, navegador
  aislado y flujo demo real con pérdida controlada de respuesta.
- `REINTENTOS_CONTROLADOS_PANEL_2026-10-05.md`: historial durable y secuencia de
  reintentos, concurrencia y protección contra respuestas tardías.
- `PRUEBA_ERROR_DEMO_2074_2026-10-05.md`: FERR-1 real, error de validación,
  reintento del mismo registro sin nueva firma y corrección del contrato `state`.
- `pruebas/demo-panel-state-contract-20261005.log`: 213 casos aprobados después
  de esa corrección; las respuestas temporales de esos tests son simuladas.

Pendiente externo: observar una respuesta temporal real elegible y el cierre
con CDR durante una caída natural. Por decisión del usuario, esa observación
se hará posteriormente en producción. La preparación local no depende de
seguir creando facturas demo, y la contingencia todavía no está desplegada.
