# Recuperación fiscal y entrega con XML firmado

Fecha de revisión: 2026-10-01. Estado: implementado y verificado localmente;
pendiente de validación del contrato de Smart PSE en staging aislado.

## Base productiva comprobada

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
   Una consulta HTTP 404 estructurada que confirme documento no encontrado
   permite reenviar el mismo XML, dentro del plazo y con permisos vigentes.
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
