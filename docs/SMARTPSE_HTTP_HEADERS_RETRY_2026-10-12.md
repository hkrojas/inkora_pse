# Reintento por Error Fetching http headers

## Estado

Corrección local implementada y probada. No confirmada en Git, fusionada ni desplegada.
Base verificada: main remoto `fa39ce0f76ef2a5369ba8eecefa68a6d4fac0335`, coincidente con health.delivery de producción.
Rama: `codex/smartpse-http-headers-retry`.

## Diagnóstico

La captura del usuario de FA01-266 muestra XML firmado seguido del mensaje del panel `[HTTP] Error Fetching http headers`.
El clasificador productivo devolvía False para ese mensaje: no autorizaba el reintento del registro existente.
Lectura productiva del 12 de octubre a las 19:40 UTC: FA01-264/doc723/job310, FA01-266/doc728/job312 y FA01-267/doc730/job313 pendientes, con XML retenido, sin CDR ni auditoría de reintento del panel.
El mensaje exacto de las otras dos facturas fue reportado por el usuario; no se abrió sesión del panel para corroborarlo.
El circuito CPE tenía dos fallos de transporte y difería la siguiente oportunidad hasta 20:08:59 UTC. Las consultas de confirmación son distintas del reintento del envío.
Evidencia original: worktree de monitoreo `smartpse-circuit-open-retry`, `tmp/audit-http-headers-20261012T194024Z.json`.

## Cambio mínimo

Único archivo runtime modificado: `backend/services/smartpse_panel_client.py`.
Se admite exclusivamente el mensaje completo conocido, normalizando mayúsculas y espacios; se admite punto o exclamación final como en el clasificador CIRCUIT_OPEN existente.
El prefijo HTTP o un timeout genérico no autorizan reintento. Mensajes parciales o acompañados de aceptación, rechazo, duplicado, ticket, pendiente o procesamiento permanecen bloqueados.

Se reutiliza la ruta existente de reintento sobre el registro del proveedor. Conserva los controles de tenant, empresa, RUC, ambiente, tipo, serie, correlativo, XML idéntico y firmado, ausencia de CDR/ticket, lease, permisos y auditoría durable.
Un HTTP200 no implica aceptación. Una respuesta ambigua bloquea otro POST y mantiene conciliación por lectura. Un fallo temporal confirmado por el propio POST conserva los plazos existentes de 15/30 minutos.
No hay migraciones ni cambios de flags, temporizadores, frontend, guías o bajas/resúmenes.

## Verificación local

- 537 pruebas aprobadas en cliente, reintento, worker, secuencias, estado y conciliación (154,27 segundos).
- 14 pruebas PostgreSQL reales aprobadas (17,29 segundos), incluida carrera entre dos jobs para la misma factura con el nuevo mensaje: sólo una autorización/auditoría de reintento.
- Base PostgreSQL local exclusiva `inkora_worker_http_headers_20261012`, loopback 127.0.0.1:55439. No se utilizaron credenciales de producción ni se detuvo el servidor compartido.
- Prueba del worker con el nuevo mensaje: un reintento sobre el registro existente, XML preservado, pendiente hasta CDR válido, sin volver a firmar ni invocar send_signed_xml.
- Pruebas de mensaje exacto, estados no elegibles, CDR existente, XML distinto, ticket, evidencia mal tipada, mensajes contradictorios y respuesta ambigua.
- `git diff --check` aprobado. Main remoto seguía en la misma revisión al finalizar.

No se llamó a SmartPSE/SUNAT, ni se emitió, reenvió, reencoló o alteró documento productivo. Las pruebas usan respuestas sintéticas: no acreditan recuperación productiva.

## Pendiente de publicación

AGENTS.md exige autorización explícita para integrar/publicar y validación fiscal en staging aislado; docs/RELEASE_CANONICO.md exige las puertas de publicación completas para cambios backend/fiscales y un paquete con huella común API/worker/frontend.
Estas puertas de publicación y staging no se ejecutaron en este bloque local. Las excepciones históricas de despliegues anteriores no constituyen autorización para esta publicación.
Tras una publicación autorizada, observar por lectura las consultas programadas de los jobs existentes, sin crear jobs ni consumir correlativos. Confirmar recuperación sólo con CDR validado y la misma identidad/XML.
