# Recuperación fiscal y entrega con XML firmado

Preparación vigente del 5 de octubre: `PREPARACION_CONTINGENCIA_2026-10-05.md`.
Incluye flags por servicio, observación del primer fallo natural productivo y
contención. Actualiza los límites históricos de las secciones siguientes.

Último bloque local: `REINTENTO_PANEL_SMARTPSE_2026-10-02.md` incorpora un
reintento opt-in del registro existente del panel, precedido por recuperación
de CDR y una reserva durable. Está desactivado y no desplegado; el POST real
sin CDR permanece pendiente de homologación aislada. No confundir ese nuevo
bloque con la recuperación CDR ya publicada.

Fecha de revisión: 2026-10-01. Estado: implementado y verificado localmente;
pendiente de validación del contrato de Smart PSE en staging aislado.

Actualización: el usuario solicitó integrar QR GRE y publicar. El candidato y
la validación conjunta posterior están en `INTEGRACION_FISCAL_QR_2026-10-01.md`;
las referencias sin commit de este informe describen el cierre del bloque inicial.

Actualización 2026-10-02: la homologación demo confirmó firma, envío del mismo
XML, CDR y PDF. La consulta devolvió 404 para facturas aceptadas, tanto demo
como una factura productiva existente consultada por lectura. La corrección
local retira el reenvío basado en 404 y conserva exactamente el XML firmado.
Ver `HOMOLOGACION_SMARTPSE_DEMO_2026-10-02.md`; estas correcciones todavía no
están publicadas y el enrolamiento productivo continúa desactivado.

Alcance posterior autorizado: habilitar primero recuperación automática de CDR
para tenant 5 y mantener desactivada la contingencia completa. El funcionamiento,
las credenciales del panel y los límites de esta fase están documentados en
`SMARTPSE_PANEL_RECOVERY.md`. Las secciones siguientes conservan el informe del
bloque original; la publicación efectiva se acredita con su recibo de despliegue.

## Base productiva comprobada

### Continuación: fases de envío (2026-10-02)

La continuación posterior cierra recuperación de XML sin CDR, inmutabilidad de
evidencia y coordinación separada de firma/envío. Resultados de pruebas y límite
pendiente de homologación: `CIERRE_CONTINGENCIA_2026-10-02.md`.

El bloque de endurecimiento posterior parte de `main`
`c336060527eafc9f438633557d85c9a936e83313`, cuyo árbol coincide con el candidato
`9152c3fac714e06a97708b0879807c1eb4b1d331` desplegado. Los datos del bloque
original que aparecen después se conservan como historial.

Los trabajos nuevos de factura Smart PSE guardan en su snapshot
`submission_state_version=1` y `submission_phase`. No requiere migración.

| Fase | Evidencia local | Acción permitida |
|---|---|---|
| `not_started` | Trabajo creado bajo este contrato; todavía no se inició envío | Firmar si falta XML válido y efectuar el primer envío |
| `possible_submission` | Marcador confirmado antes del POST fiscal | Consultar y recuperar evidencia; nunca reenviar por timeout o 404 |
| `not_submitted` | El cliente comprobó fallo de autenticación antes del POST de ese intento | Reintentar con el mismo XML conservado |
| Ausente, desconocida o contradictoria | Historia no acreditada | Conciliar; no inferir seguridad a partir de `attempts=0`, `sign_only` o falta de CDR |

La fase segura exige versión entera 1 y ausencia de indicadores de envío previo.
Valores de tipo incorrecto no se reinterpretan como evidencia. Reencolar un
trabajo antiguo nunca le asigna retroactivamente una historia segura. El camino
normal `/procesar` también marca el inicio para que activar el piloto más tarde
no convierta una operación ya intentada en un nuevo envío.

Si el snapshot completo no es un objeto JSON, el worker conserva ese contenido
y termina con un error de validación para revisión, sin llamadas fiscales. Las
boletas explícitamente identificadas como tipo 03 conservan su recuperación
anterior cuando la ejecución no comenzó; esta fase no amplía contingencia a boletas.
Antes de publicar, revisar la cola de facturas antiguas: la falta de marcadores
no se corrige reiniciando ni reenviando automáticamente esos documentos.

La recuperación de reservas vencidas utiliza el mismo criterio en Python y
PostgreSQL: un trabajo probado como no enviado conserva emisión; uno incierto
pasa a consulta. Una consulta existente siempre sigue siendo consulta. Se
mantienen límites por empresa, bloqueo de reservas y protección contra resultados
de workers que perdieron su reserva.

Durante firma y envío se usan copias mínimas de los datos y del XML, tomadas
antes de confirmar la transacción. No se accede a relaciones ORM expiradas durante
HTTP. El XML firmado, QR, identidad y correlativo se conservan. La aceptación,
cuota y efectos finales continúan sujetos al resultado fiscal validado.

La repetición real de FDEM-1 en `/enviar-demo` conservó registro y XML, devolvió
un CDR actualizado y no aumentó el contador de firmas. Esto no acredita el
reenvío productivo tras una respuesta perdida. Los estados inciertos siguen
en conciliación y el enrolamiento completo depende de la homologación pendiente.

Este bloque no activa flags remotos ni cambia el PDF. La recuperación de CDR ya
publicada continúa siendo independiente de habilitar contingencia completa.

#### Validación del bloque de fases

- 155 pruebas de backend: fases, cola, contratos de publicación, acciones de
  documentos, recuperación fiscal y de panel, cliente Smart PSE. HTTP externo
  bloqueado; 85,05 segundos, sin fallos.
- 11 pruebas de recuperación SQLite: snapshots válidos y malformados, reserva
  anterior/posterior al marcador, preautenticación y boletas no ejecutadas.
- 34 pruebas PostgreSQL 17 local: paridad Python/SQL, reservas, protección de
  resultados tardíos, concurrencia global/por empresa, notificaciones y circuito
  compartido entre diez empresas; 14,93 segundos, sin fallos.
- Total: 200 pruebas. Evidencia local en `pruebas/phase-backend-tests.log`,
  `pruebas/phase-postgres-tests.log` (los 11 casos SQLite) y
  `pruebas/phase-postgres-retry.log` (34 PostgreSQL). La primera ejecución de
  PostgreSQL encontró el servidor local detenido y no ejecutó esos casos; se
  reinició y la ejecución posterior pasó. El servidor local quedó detenido.
- `git diff --check` sin errores; sin cambios de esquema, frontend, PDF ni
  configuración remota. No se ejecutó un despliegue ni la puerta integral de
  publicación (lint/build/E2E) en este bloque de backend.

- Repositorio: `hkrojas/inkora_pse`, remoto local `inkora_pse`.
- Rama: `codex/fiscal-contingency-recovery`.
- Worktree: `C:\Users\HP\.codex\worktrees\fiscal-contingency-recovery\inkora_smartpse`.
- Base y `main` remoto al iniciar y terminar: `acc2730cd0ba2186c44ac5c0af18d3022149937a`.
- API y frontend publican la misma base `fa6308fcb2de3ed6af31c23abcd01387e2e7a550`
  y huella `e0d499040a1208305fa297b98955c2cd70198f62dcd085df6baad7433b7edd83`.
- `git diff --quiet fa6308fcb2de3ed6af31c23abcd01387e2e7a550 inkora_pse/main`
  confirmó igualdad de contenido. El identificador del merge es distinto, pero
  el árbol coincide con el contenido publicado.
- La raíz histórica fue preservada; la implementación está aislada en el worktree.

## Cambios realizados

### Migración

`backend/alembic/versions/0026_fiscal_provider_circuits.py` agrega coordinación
persistente por proveedor, ambiente y servicio CPE. No almacena documentos ni
credenciales. En PostgreSQL activa RLS y revoca acceso público, anon y authenticated.
El rol de conexión backend debe conservar acceso a esta tabla; verificarlo en staging.

### Backend

Archivos principales: `smartpse_client.py`, `smartpse_response.py`,
`facturacion_service.py`, `emission_queue_service.py`, `emission_leases.py`,
`fiscal_evidence_service.py`, `fiscal_recovery_service.py`,
`fiscal_presentation_service.py`, `_cotizaciones_fiscal.py`, `emission_jobs.py`,
`pdf_storage_service.py`, `document_actions_service.py` y routers de documentos.

1. Congela identidad, ambiente, datos fiscales y XML antes de llamar al proveedor.
2. Para facturas enroladas, solicita la firma con `/api/cpe/generar`, valida firma,
   RUC, tipo, serie, número, fecha, moneda e importes; conserva el XML y su SHA256.
3. Permite generar PDF y QR con ese XML sin afirmar aceptación de SUNAT. El CDR
   se conserva como evidencia independiente. No consume la aceptación, cobranza,
   cuotas o movimientos finales de inventario hasta obtener el resultado definitivo.
4. Envía exactamente el XML conservado mediante `/api/cpe/enviar`.
5. Un timeout o resultado incierto cambia el trabajo a consulta automática.
   Una consulta HTTP 404, incluso estructurada como documento no encontrado,
   conserva la conciliación pendiente y nunca autoriza un nuevo envío: Smart PSE
   devolvió ese resultado para documentos con CDR de aceptación en la homologación.
   Mensajes ambiguos, incluido 0111 sin CDR, mantienen consulta; no se deduce
   una caída o una mala configuración de empresa solo a partir del mensaje.
6. Ante errores de transporte reconocidos, pausa los trabajos afectados:
   primera comprobación a los 15 minutos y siguientes a los 30 minutos.
   Una sola reserva persistente prueba la recuperación entre empresas y réplicas.
   La firma de nuevos documentos puede continuar mientras la entrega está pausada,
   siempre que Smart PSE siga disponible para firmarlos.
7. Un CDR final correspondiente al documento, aceptado o rechazado, confirma
   comunicación y libera la cola con los límites globales y por empresa existentes.
   El orden continúa siendo el de la cola actual; no se agregó reparto round robin.
8. Un rechazo definitivo detiene reintentos, libera reservas de inventario activas
   y bloquea la entrega del PDF como factura. Permite descargar su CDR de rechazo.
9. Los trabajos inciertos sobreviven reinicios y no vuelven automáticamente a
   firmar/enviar. Desactivar el enrolamiento conserva el flujo de trabajos ya iniciados.
10. La actualización con CDR bloquea la fila del documento y refresca el estado
    antes de aplicar efectos, evitando consumo duplicado de cuota con callbacks
    concurrentes. Un documento ya aceptado conserva sus evidencias.
11. El PDF pendiente requiere XML firmado validado; su caché considera XML y QR.
    Los PDFs históricos aceptados y almacenados mantienen su representación.
12. Una factura vencida no inicia ni repite envío. La consulta sigue activa y deja
    una alerta única en AuditLog al vencer. No se agregó notificación externa.

El plazo se calcula hasta el final de los tres días calendario siguientes a la
emisión en Lima, no como 72 horas. Referencia:
[SUNAT: SEE del contribuyente](https://cpe.sunat.gob.pe/sistema_emision/see_contribuyente).

### Frontend

Archivos principales: `ComprobanteNuevoPage.jsx`, `useFiscalTracking.js`,
`fiscalTracking.js`, `documentArtifacts.js`, `documents.js` y
`FiscalDocumentActions.jsx`.

- La emisión utiliza las series configuradas, sin selector de contingencia ni
  sustitución por una serie 0001.
- Los estados internos pendientes se presentan como **Procesando**.
- El seguimiento continúa tras errores de red y confirmaciones pendientes;
  pausa en pestaña oculta o sin conexión y vuelve al recuperar visibilidad/conexión.
- La respuesta final refresca el documento una sola vez. No trata errores de
  transporte como rechazo fiscal confirmado.
- PDF/XML disponibles dependen de evidencia fiscal válida; el CDR puede llegar después.

## Límites del bloque

- El flujo separado de firma/envío empieza con facturas 01. Boletas conservan el
  flujo anterior con mejoras comunes de evidencia, consulta y presentación.
- Notas, GRE y operaciones por lote mantienen sus rutas propias. No se agregó
  coordinación de caída de CPE a la emisión de guías ni se modificó su QR/PDF.
- La activación interna por empresa cumple la puerta de incorporación gradual:
  `FISCAL_CONTINGENCY_TENANT_IDS` vacío inicialmente, IDs separados por coma o `*`.
  Una vez incorporada la empresa, la detección y recuperación son automáticas.
  La pausa operativa existente de un tenant sigue deteniendo nuevos envíos.
- No se modificaron producción, configuración remota, correlativos reales ni
  credenciales. No hubo llamadas fiscales reales o demo. No se hizo commit,
  merge, push, despliegue ni migración remota.

## Tests ejecutados

Evidencia local en `pruebas/`, excluida de Git. Python usado: instalación local
Python 3.13; el objetivo declarado del proyecto es Python 3.11, pendiente de
verificar en el contenedor candidato de staging.

| Verificación | Comando / evidencia | Resultado |
|---|---|---|
| Regresión backend completa | `pytest -q`, `final-backend-regression.log` | 814 aprobadas antes de los últimos ajustes de seguridad |
| Regresión fiscal crítica | Selección fiscal/colas/pagos/normalización/worker; `critical-final-check.log` | 216 aprobadas |
| Ajustes finales | `pytest -q test_fiscal_contingency_recovery.py test_emission_queue.py test_emission_worker_postgres.py test_fiscal_page_endpoints.py test_smartpse_response_normalization.py test_document_actions_consistency.py test_document_actions_recovery.py`; `final-safety-check.log` | 107 aprobadas, incluido el nuevo caso sin CDR |
| PostgreSQL real: worker | `test_emission_worker_postgres.py`, incluido en el ajuste final | 18 aprobadas: diez empresas, reserva única, réplicas, fencing y CDR concurrente |
| PostgreSQL real: GRE/migraciones | `gre-postgres.log` | 10 aprobadas |
| PostgreSQL real: cotizaciones/inventario | `quotes-postgres.log` | 2 aprobadas |
| Frontend | `npm test`; `frontend-tests-final.log` | 54 aprobadas |
| Lint | `npm run lint`; `frontend-lint-final.log` | Sin errores |
| Build y presupuesto | `npm run build`, `npm run check:bundle`; logs finales | Aprobados |
| Navegador: suite existente | `scripts/run_e2e_local.py`; `e2e-local.log` | 133 aprobadas |
| Navegador: recuperación nueva | Playwright CLI con el hook real y respuestas interceptadas | 503 → pendiente → aceptado; pestaña oculta/offline → online; un refresco final |
| PDF sin CDR | `factura-firmada-pendiente.pdf` y PNG renderizado | XML firmado sintético, QR visible y sin afirmación de aceptación |
| Contratos de empaquetado | `validate_features`, `validate_backend_import_closure`, `git diff --check` | Aprobados; no se creó paquete de publicación |

Los tests bloquearon HTTP externo al proveedor. El PostgreSQL de pruebas fue un
cluster local desechable en loopback, detenido al finalizar. Los escenarios
concurrentes se probaron contra PostgreSQL 17 real, no solo SQLite.

## Riesgos restantes y siguiente paso

**P1 de habilitación:** validar el contrato real de Smart PSE en staging aislado.
La [documentación de Smart PSE](https://smartpse.pe/documentacion) y su
[guía de integración](https://smartpse.pe/blog/como-integrar-pse-api-facturacion)
describen firma y envío por separado, pero el alcance de `/enviar` aparece mezclado
con GRE en algunas secciones. Los mocks locales no prueban disponibilidad,
campos, tiempos ni respuestas del proveedor para CPE en la cuenta de Inkora.

El siguiente bloque es una homologación aislada y autorizada: factura 01,
firma sin CDR, envío del mismo XML, timeout seguido de consulta, 404 estructurado,
CDR de aceptación/rechazo y PDF antes/después del CDR. También verificar Python
3.11, permisos de la nueva tabla y compatibilidad del paquete API/frontend/worker.

**Publicación:** este cambio fiscal crítico no se declara listo para producción
sin staging aislado, según AGENTS.md. La autorización anterior de omitir staging
correspondía a la publicación anterior del worker. Esta revisión conserva los
cambios sin publicar. Tras la homologación, revisar/confirmar cambios y ejecutar
`docs/RELEASE_CANONICO.md` con una única huella para API, frontend y worker.

**Rollback:** retirar el enrolamiento impide incorporar nuevas facturas y deja
recuperar las ya iniciadas con esta versión. Volver directamente al worker anterior
con trabajos de firma/envío abiertos no está homologado: primero detener el
consumidor y reconciliar/drenar o retener esos trabajos. Conservar documentos,
XML, jobs y migración; no borrar evidencia ni recalcular correlativos para revertir.
