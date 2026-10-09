# Corrección local del clasificador de reintentos Smart PSE

## Identidad y alcance

- Rama: `codex/smartpse-circuit-open-retry`.
- Base verificada contra main remoto y delivery productivo: `548e324429b5c2ef94ccb34150187e21ed435a5a`.
- Huella productiva al iniciar: `4e8dc79b50f952d54f76a1bbeccef5d63f2b3196f93036c1e6b5373e1e65edfe`.
- Implementación aislada; no se alteró la raíz histórica Desktop.
- Alcance: clasificador compartido de elegibilidad y resultado temporal confirmado del reintento del panel. Sin cambios de worker, migraciones, flags, frontend o datos productivos.

## Diagnóstico

La revisión por lectura de FA01-258 (tenant 5, documento 706, job 294) observó el registro Smart PSE 455570 en estado `error`, XML firmado disponible y sin CDR. El mensaje era:

`[CIRCUIT_OPEN] SUNAT no responde, reintente en unos segundos`

El worker sí consultaba y programaba consultas posteriores. El clasificador anterior sólo admitía categorías HTTP temporales y no autorizaba el reintento de ese registro. La última comprobación de panel de este diagnóstico fue a las 22:13 UTC del 9 de octubre; no constituye una lectura posterior al cambio.

## Corrección

Se admite ese mensaje específico completo, tolerando mayúsculas, espacios y puntuación terminal simple. Un marcador CIRCUIT_OPEN aislado, mensajes desconocidos y mensajes con información contradictoria no habilitan el reintento.

El flujo existente conserva sus controles: empresa y ambiente congelados, factura 01, XML idéntico al almacenado, ausencia de CDR y ticket, revisión del registro justo antes del envío, permisos y flags vigentes, lease y reserva durable con auditoría. El POST va a `/panel/documentos/{id}/reintentar` del registro existente, sin enviar un nuevo payload de factura ni consumir otro correlativo.

Un reconocimiento del POST no implica aceptación. Sólo un CDR válido y coincidente permite cerrar como aceptada. Una respuesta perdida o ambigua mantiene consulta y bloquea otro POST. Un fallo temporal confirmado en la respuesta soportada permite un intento posterior tras el intervalo existente: 900 segundos inicialmente y 1800 segundos después. El texto del proveedor «unos segundos» no altera esos intervalos.

## Verificación local

Entorno explícito de pruebas: ENVIRONMENT=test, FISCAL_ENV=beta, DATABASE_URL=sqlite://. Proveedor y panel simulados; ningún POST fiscal remoto ni consumo de correlativos productivos.

Primera ejecución:

```text
python -m pytest -q test_smartpse_panel_retry.py test_panel_retry_worker.py test_panel_retry_state.py test_panel_retry_sequence.py test_smartpse_panel_client.py test_smartpse_panel_reconciliation.py --disable-warnings --tb=short
487 passed in 118.42s
```

Después se ampliaron los casos de concurrencia y respuesta con estado error al mensaje CIRCUIT_OPEN, y se ejecutaron ambos casos para las dos categorías:

```text
python -m pytest -q test_smartpse_panel_retry.py -k "failure_shape_with_explicit_error_state or concurrent_retry_calls" --disable-warnings --tb=short
4 passed, 241 deselected in 0.29s
```

Cobertura añadida: mensaje observado y variantes de formato, mensajes contradictorios bloqueados, un solo POST al registro existente, CDR previo sin POST, XML modificado/ajeno bloqueado, aceptación únicamente desde CDR, cuota contada una vez, intervalos de 15/30 minutos, respuesta perdida sin segundo POST y dos llamadas concurrentes con una sola autorización.

`git diff --check` pasó. Main remoto seguía en la base indicada al terminar las pruebas.

## Estado de entrega y límites

Corrección local sin commit, integración ni despliegue. No se reencoló ni reenvió FA01-258. Se espera que el job existente evalúe el nuevo clasificador en su próxima consulta una vez publicada la corrección, sujeto a los controles vigentes y al estado que entonces presente el panel. No se garantiza aceptación por SUNAT.

No se ejecutó staging ni PostgreSQL real para este cambio; las pruebas del worker usaron SQLite y las de concurrencia del cliente fueron offline. Antes de publicar corresponde autorización explícita y el procedimiento canónico, incluida verificación de main vigente, gates de integración aplicables, identidad común API/frontend/worker y revisión posterior por lectura. No publicar este árbol sobre avances posteriores de otro chat sin integrarlos primero.
