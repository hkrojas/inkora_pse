# Validación del resumen diario — 7 de octubre de 2026

## Fuente y alcance

Worktree limpio `boletas-resumen-validacion`, rama `codex/boletas-resumen-validacion`,
desde main remoto/productivo `210ac3f7fe57675545e42e93d193c3fc634abf83` (PR 42).
Se verificó que conserva PR 36 y las correcciones posteriores de cotizaciones,
fechas, calendario, encabezados, nuevo comprobante y gráfico del dashboard.
La raíz Desktop y el worktree histórico `boletas-worker` se conservan.
Se aplicaron deltas del borrador pendiente; no se sustituyeron archivos fiscales
completos por sus versiones anteriores.

Este bloque añade confirmación por CDR y consulta del resumen existente,
protección frente a respuestas tardías, una interfaz que distingue pendiente,
aceptado y rechazado, y los códigos 2=modificar/3=anular. Los cambios backend y
frontend se conservan en commits separados. No modifica worker, cola, reintentos,
contingencia, cálculo fiscal, Storage, PDFs ni migraciones. Facturas y boletas
conservan su flujo individual compartido.

## Evidencia local

- 187 pruebas backend focalizadas aprobadas sobre esta base, incluidas fechas
  desde cotización, CDR, contingencia, PDF, seguridad y flags.
- 4 pruebas PostgreSQL aprobadas en una base local exclusiva y desechable
  `inkora_summary_boletas_20261007`: respuestas tardías no borran un CDR terminal.
- 8 pruebas de navegador focalizadas: consulta sin reenvío, bloqueo de solicitud
  duplicada, aceptación/pendiente/rechazo, códigos del catálogo, ticket y error
  ambiguo. Respuestas sintéticas locales, sin llamadas fiscales externas.
- Inspección visual móvil y escritorio, temas claro/oscuro; controles y tabla
  dentro del ancho disponible. Botón de consulta móvil con altura mínima 44px.
- La puerta canónica incluye obligatoriamente la nueva suite PostgreSQL y el
  contrato `POST /resumen-diario/{resumen_id}/consultar`.

La regresión completa y la identidad final se registrarán al terminar la puerta
canónica. Los logs y capturas están en `pruebas/` y `frontend/test-results/`,
excluidos del paquete publicable.

## Condición para producción

El proyecto Railway `a0e3fddd-4e31-48ee-ac32-89bc295249c4` solo presenta el
entorno `production`. No se encontró staging de Inkora en el inventario disponible.
Se solicitó identificar un staging existente, sin pedir claves ni duplicar
credenciales o datos productivos.

AGENTS.md, regla 12: «Si el módulo cambia datos o procesos críticos, no puede
pasar a producción sin staging aislado». Este bloque cambia la evidencia fiscal
de aceptación del resumen y su uso como origen de guía. Por tanto, las pruebas
locales no permiten aprobar todavía el despliegue. Aplicar
`docs/STAGING_POSTGRES_RUNBOOK.md` y validar estos casos antes de integrar:

1. Envío con ticket sin CDR permanece pendiente.
2. Consulta con CDR correspondiente al lote y RUC confirma aceptación/rechazo.
3. Consulta con timeout o CDR ajeno conserva pendiente, sin reenvío.
4. Respuestas tardías no sobrescriben un CDR terminal.
5. Empresa ajena, rol no emisor, tenant suspendido y flag deshabilitado no consultan.
6. Guía solo usa un resumen con CDR aceptado; boleta individual conserva su flujo.

No habilitar `daily_summary` para nuevas empresas. Permanecen pendientes los
otros bloques de la auditoría: detalle desde documentos propios persistidos,
cobertura XML de notas/operaciones no gravadas, identidad del comprador,
idempotencia manual y reserva de correlativos. No se reparan marcas históricas
productivas ni se consumen correlativos reales para probar.

## Entrega productiva que permanece vigente

Main `210ac3f7fe57675545e42e93d193c3fc634abf83`.
Huella `52208028cee298cd5522290e6753b01b435ece4cd568b3268ef319f655f1e905`.
API deployment `d4deda7a-67c4-472e-93f1-1ad5d395db6b`.
Worker deployment `0eafbc13-bbc7-4d95-80e5-612e3a12dec9`.
Frontend deployment `dpl_2XTBJLNAT1igUeiXoiSaPp2WkhZU`.
Estos identificadores pertenecen a PR 42, no al resumen pendiente.
