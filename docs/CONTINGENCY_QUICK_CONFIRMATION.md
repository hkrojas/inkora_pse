# Confirmación rápida después de un reintento de contingencia

## Alcance

Sobre PR52 (`beb9567e47385aa398a5fb31a7569649a858bd8c`), el worker compartido
reserva una consulta adicional a los 15 segundos de terminar un reintento real
del panel Smart PSE que no devuelve CDR definitivo. Mantiene el mismo documento,
job, XML firmado, correlativo y validaciones de CDR existentes.

Sólo afecta facturas incorporadas al piloto de contingencia y autorizadas por
los controles existentes de recuperación/reintento. No agrega workers, flags,
migraciones, cambios de interfaz ni acciones para guías o bajas.

## Comportamiento

- `panel_confirmation` se guarda en el snapshot del job, separado del marcador
  fiscal auditado `panel_retry_attempt`. Está ligado a su UUID, job, tenant y documento.
- Se reserva junto con el permiso durable del POST; una interrupción justo antes
  del POST puede dejar una consulta conservadora, nunca autorización de reenvío.
- La respuesta del POST ajusta el vencimiento a 15 segundos desde su recepción.
  Un CDR inmediato continúa por la validación terminal existente.
- El scheduler usa `available_at`; libera el slot durante la espera. No usa
  `sleep(15)`, nuevos hilos ni sondeo periódico adicional.
- La consulta consume la marca bajo lease y commit antes de contactar al proveedor.
  Nunca entra al fallback que reintenta el envío, incluso ejecutada tarde tras reinicio.
- Si aún está pendiente, vuelve al intervalo normal de recuperación (15–30 minutos).
  Sólo otro POST autorizado puede reservar otra consulta rápida.
- El circuito de protección sigue teniendo prioridad. Los 15 segundos son el
  vencimiento programado, no una garantía de ejecución exacta con worker ocupado,
  detenido o proveedor pausado.
- Si se interrumpe después de consumir la marca y antes de consultar, el mecanismo
  habitual de recuperación de leases conserva la conciliación; no se repite la
  aceleración. No se modifican ni reencolan jobs históricos para probarla.

Una ejecución de conciliación puede realizar más de un GET del proveedor cuando
necesita buscar el documento o recuperar el CDR. Se limita la ejecución rápida por
reintento; no se promete exactamente una petición HTTP.

## Verificación y publicación

Las pruebas focalizadas cubren aceptación, rechazo definitivo, CDR ajeno, respuesta
pendiente, timeout, POST lento, despertar temprano, reinicio tardío, nueva secuencia,
identidad/tenant, persistencia PostgreSQL y lease vencido. Todas usan datos sintéticos
y proveedores simulados; no emiten ni reintentan documentos productivos.

El perfil canónico es completo por modificar backend fiscal. La publicación requiere
además staging aislado según `AGENTS.md` y `docs/RELEASE_CANONICO.md`. La excepción de
staging del recibo PR52 sólo cubre aquel clasificador y no se aplica automáticamente
a este cambio. El recibo final debe identificar las puertas realmente completadas.
