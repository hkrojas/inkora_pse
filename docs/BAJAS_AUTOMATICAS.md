# Bajas automáticas por el worker existente

Base: `inkora_pse/main` `210ac3f7fe57675545e42e93d193c3fc634abf83`, que conserva la base productiva PR 36 y las correcciones posteriores de contingencia, PDF, CDR, fechas y diseño móvil. Implementación en un worktree limpio y rama `codex/boletas-bajas-auto`.

## Alcance operativo

Inkora continúa enviando boletas y notas individualmente. No se crea un segundo resumen para aceptar un documento que ya tiene CDR individual aceptado. Cuando un usuario solicita una baja, el worker existente prepara y procesa automáticamente un RC para boletas/notas de boleta, o una RA para facturas/notas de factura. No hace falta armar ni enviar ese lote manualmente desde Resumen diario.

La solicitud exige declarar que el documento no fue entregado ni puesto a disposición del cliente. Una operación ya entregada requiere revisar una nota de crédito. El servidor conserva los controles actuales de empresa autenticada, ownership, usuario emisor, empresa activa, suscripción y feature flag `voiding` por empresa. La declaración, usuario, motivo, fecha, XML, identidad y respuestas se conservan en el job existente; no se agrega una tabla ni una variable de infraestructura.

El plazo de baja se calcula en hora de Perú usando la fecha persistida de recepción/verificación del CDR individual: hasta siete días calendario después de esa fecha. Sin esa fecha, sin CDR legible que corresponda al documento o fuera del plazo, se exige conciliación. No se inventa una fecha para documentos históricos. La fecha de referencia del RC es la de emisión del documento y su fecha de generación es la actual. El nombre del lote usa la fecha de generación y un correlativo de cinco dígitos, compartiendo namespace con resúmenes registrados manualmente.

Las notas de boleta incluyen la referencia a su boleta. El XML del resumen conserva moneda y bases gravadas/exoneradas/inafectas/exportación/gratuitas. Las notas de crédito que ya movieron inventario requieren conciliación previa: no se aplica la reversión de una venta como si fuera una nota. El documento original no se da de baja mientras tenga notas vigentes o pendientes, reservas de despacho o cobertura GRE. Los borradores de nota no consumen número si el origen tiene una baja en curso. Los locks de origen serializan solicitudes de baja y creación/numeración de notas; el lock de empresa es `NO KEY UPDATE` para no bloquear las FK de sus inserts.

## Confirmación y recuperación

`POST /bajas/anular` exige `confirmed_not_delivered: true` y siempre devuelve el job asíncrono, incluso para un cliente que solicite `mode=sync`. Ambos puntos de entrada de la interfaz envían esta declaración y muestran seguimiento mediante el hook fiscal compartido.

Antes de la primera llamada al proveedor se confirma en la base `void_send_started=true`, junto con el lote congelado. Después de ese punto, un timeout, excepción, caída del proceso o lease vencido habilita consultas al mismo nombre de archivo, nunca otro envío ni otro correlativo. Las solicitudes repetidas recuperan el mismo job y no borran evidencia. Un CDR rechazado que corresponda al lote termina el job sin anular el documento. Un CDR ausente, inválido, de otro lote o de otro RUC mantiene la conciliación pendiente.

Solo un ApplicationResponse con un único DocumentResponse, identidad del lote correcta y código SUNAT 0 permite marcar el documento anulado y aplicar la reversión existente de inventario. Un HTTP 200 o ticket no son aceptación. La evidencia se confirma antes de aplicar el resultado local para poder recuperarlo si el proceso se interrumpe. La reversión conserva la idempotencia existente de movimientos. Las bajas históricas sin este protocolo congelado necesitan revisión manual y no se reenviarán automáticamente.

Un fallo posterior a un posible envío también bloquea nuevas notas y preparación de guías sobre el origen hasta conciliarlo; un CDR de rechazo definitivo que corresponda al lote sí libera ese bloqueo. Una baja histórica sin evidencia de envío fiable también queda bloqueada para conciliación. La reserva de bajas respeta el orden de locks documento origen → empresa usado por las GRE. El worker conserva sus contratos actuales de leases y tenant suspendido.

## Pruebas y publicación

- `backend/test_void_recovery.py`: aceptación, rechazo, CDR incorrecto, incertidumbre, fechas, ownership, notas, API, identidad y reversión real de stock una sola vez; proveedor simulado.
- `backend/test_emission_worker_postgres.py`: API simultánea, reserva de lotes diferentes, recuperación de lease vencido, ausencia de locks durante I/O y carrera nota/baja; PostgreSQL local exclusivo.
- `frontend/e2e/void-recovery.spec.js`: dos entradas de bajas, temas claro/oscuro, 320/390/1440 px, declaración obligatoria, seguimiento y un único POST; respuestas sintéticas.
- Regresión completa, contratos, lint, build, presupuesto de bundle, revisión visual y CI Python 3.11 antes de integrar.

Este cambio afecta estados fiscales e inventario. La regla 12 de `AGENTS.md` exige staging aislado antes de producción. PostgreSQL local y mocks no equivalen a homologación Smart PSE/SUNAT. En staging deben comprobarse RC y RA con CDR auténtico, su nombre de archivo, recuperación tras interrupción, rechazo sin reversión y stock después de aceptación. No usar documentos ni correlativos productivos para esas pruebas.

El endurecimiento separado del resumen **manual** de PR 43 no está incorporado en esta rama: es otro bloque revisable y tampoco debe considerarse publicado. Este bloque cubre las bajas automáticas; no añade un cron de resúmenes de aceptación o modificación.

Para la entrega, incorporar cualquier avance posterior de main y repetir las puertas pertinentes. Aplicar exclusivamente `docs/RELEASE_CANONICO.md`, con la misma huella para API, worker y frontend, API compatible primero y verificación posterior por lectura. Sin migraciones remotas en este bloque. Registrar commit de main, huella e IDs de servicios solo después de un despliegue efectivo.

## Homologación demo posterior

El 8 de octubre se probaron BBAJ-1 y FBAJ-1 en la empresa demo 688, su envío
individual y sus bajas RC/RA con CDR código 0. La consulta de bajas demo ahora
indica explícitamente `environment=demo`, requisito confirmado con el proveedor
real. Los mismos trabajos se recuperaron sin reenviar; la repetición posterior
no realizó llamadas fiscales. Series, identificadores, evidencias y límites en
[SERIES_DEMO_BAJAS_2026-10-08.md](SERIES_DEMO_BAJAS_2026-10-08.md).
La puerta de staging aislado antes de producción continúa pendiente.

## Referencias oficiales

- [SUNAT: SEE-OSE, envío individual de boletas y bajas](https://cpe.sunat.gob.pe/informacion_general/operador_servicios_electronicos).
- [SUNAT: boletas y resumen diario](https://cpe.sunat.gob.pe/tipos_de_comprobantes/boleta).
- [SUNAT: notas de crédito](https://cpe.sunat.gob.pe/tipos_de_comprobantes/nota_de_credito).
- [SUNAT: guía del resumen de boletas, notas y estados](https://cpe.sunat.gob.pe/sites/default/files/inline-files/GUIA_Resumen_de_Boletas_11-01-2018%20%282%29_2_0.pdf).
- [SUNAT: estructura del nombre de archivo RC](https://www.sunat.gob.pe/legislacion/superin/2019/anexoXIII-2-C-114-2019.pdf).
- [SUNAT: estructura del nombre de archivo RA](https://www.sunat.gob.pe/legislacion/superin/2019/anexoXIII-1-B-114-2019.pdf).
