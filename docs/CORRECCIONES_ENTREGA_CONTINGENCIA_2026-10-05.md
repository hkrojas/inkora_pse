# Correcciones de entrega de comprobantes y contingencia

Fecha: 5 de octubre de 2026.

## Identidad y alcance

Implementación local en `codex/contingency-delivery-fixes`, worktree limpio creado desde el main remoto `01061042d7d7671a0b4d083ca671e7c75e2c447d`. Al iniciar, producción conservaba la huella `5bf51e2e115b951ee131311bb97d0ab27b7dff2fc0b9b9537b17aeea2b96c271` y base `dbf07ee893ae11e87c2426ac54254f43b9d33484`.

Se corrigieron los problemas del informe anterior de revisión de contingencia y PDF. La raíz histórica del Desktop se conservó intacta. No se hicieron commits, migraciones remotas, nuevas emisiones, reenvíos ni cambios productivos. Estas correcciones todavía no están desplegadas.

## Bloque backend

- Compartir una cotización vinculada resuelve el comprobante fiscal real con filtros de empresa, documento de origen y tipo de recurso. Mensajes y UUID compartido corresponden al mismo comprobante que la descarga interna. Los enlaces públicos antiguos de cotizaciones conservan su significado.
- La generación revalida estado y origen del PDF después de subirlo a Storage. Un bloqueo de fila protege solamente la comprobación final y persistencia; no se mantiene durante renderizado o I/O externo.
- Descargas privadas y enlaces públicos revalidan el estado después de descargar bytes o firmar el enlace. Rechazo/anulación devuelve 409; cambios de referencia o contenido durante la operación devuelven 202 para reintentar. Una referencia antigua no puede compararse con una versión nueva para entregar bytes anteriores.
- Si falla Storage al descargar el CDR y existe una copia XML retenida del CDR, se reconstruye el ZIP desde esa copia. No se inventa CDR cuando no existe.
- El PDF histórico aceptado se conserva. Pasar de pendiente a aceptado con el mismo XML firmado y QR reutiliza el PDF; la llegada del CDR no fuerza una representación distinta.

## Bloque frontend

- El seguimiento recarga el documento al observar cambios relevantes, incluso antes del CDR, para que aparezca el PDF disponible. Incluye `pending_confirmation`.
- Las recargas no terminales se limitan a una cada 15 segundos por documento. Se mantienen los intervalos de seguimiento de 5 o 30 segundos según el trabajo y la pausa al ocultar la página o perder conexión.
- Los trabajos terminales actualizan inmediatamente. Sólo se marca completada la recarga después de una lectura exitosa; una lectura fallida conserva el seguimiento y reintenta.
- Las filas de la lista agrupan recargas en una solicitud compartida. Una lectura de fondo fallida conserva las filas y su seguimiento.
- La nueva emisión navega al identificador fiscal devuelto por backend. El detalle de una cotización vinculada consulta y muestra acciones y estado del comprobante real, sin mostrar aceptación anticipada.
- Una respuesta tardía de otra ruta se descarta; abrir una ruta sin acceso elimina datos y acciones de la anterior.

## Evidencia de pruebas

Las ejecuciones backend se solapan; sus cantidades no deben sumarse como pruebas únicas.

| Verificación | Resultado | Evidencia local en `pruebas/` |
| --- | --- | --- |
| Entrega PDF, generador y recuperación fiscal | 105 aprobadas | `backend-pdf-fixes.log` |
| Entrega PDF, seguridad de recuperación y guardas de release | 38 aprobadas | `backend-delivery-security.log` |
| Entrega PDF, generador y contratos operativos frontend | 56 aprobadas | `backend-pdf-final.log` |
| Últimas guardas de entrega | 19 aprobadas | `backend-delivery-final-delta.log` |
| Generación real de PDF antes de CDR y reutilización tras reconciliación | 1 aprobada | `backend-pending-pdf.log` |
| Concurrencia PostgreSQL real durante upload, descarga y firma de enlaces | 8 aprobadas | `backend-pdf-postgres.log` |
| Tests unitarios frontend | 56 aprobadas | `frontend-delivery-tests.log` |
| Pantallas Playwright, lecturas locales simuladas | 8 aprobadas | `frontend-delivery-e2e.log` |
| ESLint | Sin errores | `frontend-delivery-lint.log` |
| Build Vite | Aprobado | `frontend-delivery-build.log` |

Los dos últimos grupos SQLite de entrega cubren los 20 casos actuales del archivo nuevo. PostgreSQL utilizó una base exclusiva en loopback (`inkora_worker_pdf_delivery_20261005`), transacciones independientes y límite de espera de bloqueo. El servidor local quedó detenido al terminar. El guard de pruebas Python impidió conexiones externas. Playwright interceptó las lecturas HTTP y rechazó llamadas externas o emisiones.

La prueba backend genera bytes PDF reales y verifica conservación de XML firmado, QR y referencia PDF al obtener CDR. La respuesta PDF de las pantallas es una fixture; no representa una prueba visual del PDF productivo. La plantilla del PDF no cambió.

`git diff --check` aprobado. Revisión backend independiente cerró las carreras detectadas durante Storage y firma de enlaces.

## Límites y siguiente etapa

- No se observó ni provocó una caída natural de SUNAT en producción para esta corrección. La evidencia de recuperación se obtiene con respuestas locales controladas.
- La revalidación protege nuevas entregas; un enlace firmado ya entregado mantiene su vigencia de Storage hasta expirar.
- No se cambiaron correlativos, política de reenvíos, circuito del proveedor ni esquema de datos.
- La publicación requiere la revisión e integración del candidato y el procedimiento canónico de release, con las puertas completas de publicación. Las pruebas focalizadas de este informe no sustituyen ese procedimiento.
