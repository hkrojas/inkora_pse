# Resumen diario: consulta y estados en frontend

Bloque frontend autorizado después del cierre backend de confirmación. Base:
`inkora_pse/main`, PR36, `c0ae8b3bd029d055d4911437393933dc16213990`.
Worktree: `C:/Users/HP/.codex/worktrees/boletas-worker/inkora_smartpse`,
rama `codex/boletas-worker`. Cambios sin commit, preparados para revisión separada.

## Resultado

- Cada resumen permite consultar mediante `POST /resumen-diario/{id}/consultar`.
  La consulta usa el backend preparado en el bloque anterior; no vuelve a emitir.
- Un ticket o una respuesta sin estado nunca se presentan como aceptación.
  Se distinguen pendiente de confirmación, aceptación y rechazo con su motivo.
- Los registros históricos `sent` no bastan para acreditar un CDR. Se muestran
  como «Enviado · consultar estado» hasta obtener una respuesta confirmada del
  backend. El filtro y los contadores «Enviados» conservan su significado de
  almacenamiento, sin llamarlos aceptados.
- La confirmación visual se conserva durante la visita a esta página, asociada
  al ID y `updated_at`. Al volver a entrar se requiere consultar nuevamente;
  el backend devuelve los CDR terminales válidos sin llamar otra vez al proveedor.
  No se migran ni se reinterpretan permanentemente los registros históricos.
- Se bloquean solicitudes simultáneas y doble clic durante envío/consulta.
  Después de cada resultado se recargan filtros, contadores y paginación con los
  parámetros actuales, evitando restaurar una vista anterior.
- Ante un envío incierto (red, timeout o 5xx), se cierra el formulario y se indica
  consultar el listado antes de reenviar. No existe reenvío ni polling automático.
- Catálogo19: `1 = adicionar`, `2 = modificar`, `3 = anular`.
- El formulario utiliza la fecha de Lima mediante el helper existente, evitando
  proponer mañana cuando UTC cambia de día antes que Perú.
- El número RC mostrado sigue el contrato compartido actual del backend: fecha
  del resumen, correlativo de cinco posiciones y conservación de referencias ya
  normalizadas. No duplica fechas. No se modifica la construcción fiscal backend.
- Se conserva el foco al escribir la serie-correlativo del detalle.
- Se corrige el ancho heredado de las columnas en móvil para que el estado y el
  botón de consulta no se recorten dentro de la tabla.

## Archivos

- `frontend/src/pages/ResumenDiarioPage.jsx`
- `frontend/src/pages/ResumenDiarioPage.css`
- `frontend/src/lib/utils/dailySummary.js`
- `frontend/src/lib/utils/dailySummary.test.js`

## Verificación

- `npm test`: **62 pruebas aprobadas**, incluyendo seis pruebas nuevas de
  estados históricos, resultados inciertos, número RC y catálogo19.
- `npm run lint`: aprobado.
- `npm run build`: aprobado.
- `npm run check:bundle`: aprobado; entrada compartida 46.23 KiB gzip,
  shell 40.86 KiB gzip, estilos globales 77.21 KiB gzip, dentro de los presupuestos.
- `backend/test_operational_frontend_contracts.py`: **1 prueba aprobada**.
- Playwright CLI contra Vite local 5173 y API 8000 interceptada íntegramente con
  datos sintéticos: pendiente con ticket, aceptación después de consulta, rechazo
  con motivo, consulta 502 que conserva pendiente, histórico enviado consultable,
  ausencia de estado, doble clic sin consulta duplicada y filtros actualizados.
- Formulario simulado: boleta S/1,180, `estado=2`, base S/1,000 e IGV S/180 conservados
  en el payload. Envío 502: una sola solicitud, formulario cerrado y resumen
  pendiente visible; ninguna emisión externa ni correlativo productivo.
- Vista móvil 390px: documento 390px, tabla 326px y celda de estado 294px,
  con etiqueta y botón dentro de sus límites, sin desbordamiento ni recorte.
  Fecha inicial observada: 2026-10-05 en Lima mientras UTC ya era 2026-10-06.
- Evidencia y scripts manuales locales en `frontend/output/playwright/`, ignorados
  por Git. Los errores de red 502 fueron respuestas simuladas intencionales; no
  hubo errores JavaScript ni solicitudes inesperadas en las comprobaciones.

## Límites y publicación

Este bloque no modifica worker, colas, configuración, reintentos, contingencia,
PDF, CDR de ventas, inventario ni migraciones. Facturas y boletas conservan el
flujo compartido. La consulta necesita el backend del cierre anterior: debe
publicarse primero una API compatible, según `docs/RELEASE_CANONICO.md`.

No se fusionó ni se desplegó. No hay una nueva huella ni nuevos identificadores
productivos que entregar. Antes de producción quedan staging aislado, revisión
de los riesgos fiscales pendientes de la auditoría, incorporación de avances
posteriores de main y los controles del paquete canónico con la misma huella
para frontend, API y worker. Estas comprobaciones locales no sustituyen staging.

Los siguientes bloques backend pendientes incluyen ownership por cada documento
del resumen, totales desde datos persistidos, plazos fiscales, idempotencia del
envío manual y reserva de correlativos. No quedan resueltos por esta interfaz.
