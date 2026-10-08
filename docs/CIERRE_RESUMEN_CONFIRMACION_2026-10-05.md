# Resumen diario: confirmación y consulta — bloque backend

## Cambios realizados

Base: main remoto `c0ae8b3bd029d055d4911437393933dc16213990`, PR 36. Rama: `codex/boletas-worker`. Implementación autorizada después de la auditoría y de la elección del usuario: mantener el flujo compartido actual de facturas/boletas y corregir primero el resumen. La raíz Desktop conserva sus cambios históricos; sólo se usa su intérprete Python existente como dependencia de pruebas.

- `backend/services/smartpse_response.py`: el resumen RC valida el CDR mediante las comprobaciones compartidas de facturación: XML legible, resultado fiscal, identidad del lote y contraste del RUC cuando está presente en el CDR. Sin CDR no hay aceptación, aunque el HTTP sea exitoso o exista un ticket. La extracción admite tanto respuestas originales como resultados normalizados persistidos.
- `backend/services/facturacion_service.py`: consulta única del lote usando el cliente Smart PSE existente y la identidad congelada del envío. No firma, reenvía ni genera otro correlativo.
- `backend/routers/facturacion.py`: nueva operación `POST /resumen-diario/{resumen_id}/consultar`, protegida por ownership del tenant autenticado, permiso de emisor, habilitación de emisión, rate limit y flag existente `daily_summary`. Devuelve el resultado persistido sin otra consulta si ya existe un CDR terminal verificable. Un timeout/resultado ambiguo de envío o consulta conserva el resumen pendiente, en lugar de afirmar un rechazo fiscal.
- `backend/crud/resumenes.py`: `sent` y `success=true` se reservan para un CDR aceptado. Pendiente tiene `success=false`. Se conservan ticket, respuesta y evidencia del proveedor. Un bloqueo de fila y recarga impiden que una consulta tardía sobrescriba una aceptación o un rechazo ya confirmado por CDR.
- `backend/services/sale_dispatch_service.py`: los resúmenes históricos marcados `sent` sin un CDR válido dejan de autorizar el origen de una guía. Es un cambio acotado a la evidencia del resumen, necesario para que las marcas antiguas no sigan funcionando como prueba fiscal.
- Pruebas nuevas: confirmación RC, respuestas ambiguas, rechazo, identidad equivocada, ownership, permisos, flags, consulta sin reenvío, resultados terminales y concurrencia PostgreSQL. Fixtures previos de resumen ahora usan un CDR con identidad/código reales sintéticos, en lugar de `<ApplicationResponse/>` sin contenido.

## Facturas, boletas y los S/700

El commit histórico `3b00d8f4891f88c2fd81dd75d69a2d05b0ee18c0` cambió la detracción para que no se active automáticamente sólo por el importe. La venta normal `0101` puede superar S/700; la detracción se construye cuando se solicitó explícitamente con datos válidos. Esta corrección permanece intacta.

La identificación del comprador de una boleta mayor a S/700 es una regla distinta y no es un límite máximo de venta. No se añadió un tope de importe ni una ruta individual separada de boletas. Dos pruebas nuevas envían ventas sintéticas de S/1.180, tipos `01` y `03`, por `emitir_factura`/`invoice/send`, conservando los totales y la verificación fiscal común sin activar detracción automática.

Fuente normativa para la identificación: [SUNAT — boleta de venta electrónica](https://cpe.sunat.gob.pe/tipos_de_comprobantes/boleta).

## Qué no se tocó

No se modificaron worker, configuración, cola, reintentos, piloto de contingencia, correlativos, núcleo de cálculo/detracción, inventario, cobranza, PDFs, Storage, frontend ni migraciones. No hubo emisiones productivas, consultas fiscales reales, reencolados, merge, commits, cambios remotos o despliegues. El nuevo endpoint consulta un resumen RC existente; el envío individual de facturas/boletas conserva su ruta anterior.

## Tests ejecutados

Entorno de pruebas: `ENVIRONMENT=test`, `DATABASE_URL=sqlite://`, clave sintética. Intérprete: `C:/Users/HP/Desktop/inkora_smartpse/backend/venv/Scripts/python.exe`, ejecutado con cwd en el worktree.

Regresión focalizada, seguridad y contratos:

```powershell
python -m pytest -q --tb=line test_resumen_confirmation.py test_apisperu_documentos_matrix.py test_facturacion_comprobante_builder.py test_facturacion_guards.py test_fiscal_submission_leases.py test_smartpse_response_normalization.py test_emission_queue.py test_beta_feature_flags.py test_apisperu_payload_contracts.py test_sale_dispatch_guides.py test_smartpse_facturacion_service.py test_document_download_service.py test_fiscal_contingency.py test_release_guard.py test_operational_frontend_contracts.py
```

Resultado final: **242 pruebas aprobadas**.

Concurrencia:

```powershell
$env:INKORA_SUMMARY_POSTGRES_URL='postgresql://inkora_summary_test@127.0.0.1:5432/inkora_summary_20261005'
$env:INKORA_REQUIRE_POSTGRES_TESTS='1'
python -m pytest -q --tb=line test_resumen_confirmation_postgres.py
```

Resultado: **4 pruebas aprobadas** sobre PostgreSQL 17 local exclusivo y desechable, sin proveedor externo. Una instancia temporal escuchó sólo en loopback durante las pruebas y fue detenida al terminar. El fixture restringe host y prefijo `inkora_summary_`; nunca acepta una base remota. Comprueba aceptación/rechazo frente a respuesta pendiente/timeout de una sesión que ya tenía el objeto anterior en memoria.

Verificación previa de la corrección de detracción: **10 pruebas aprobadas**, seleccionadas de `test_facturacion_comprobante_builder.py` y `test_facturacion_fiscal.py`. `git diff --check` sin errores. Se volvió a obtener main remoto y seguía en la misma referencia productiva.

## Riesgos restantes

- La consulta es una capacidad de backend. No hay botón frontend ni ejecución automática del worker en este bloque.
- Siguen pendientes las etiquetas invertidas de modificar/anular en el formulario, construcción de detalles desde documentos de la empresa, idempotencia de envío manual, cobertura XML de notas/operaciones no gravadas, identidad del comprador y alertas por plazos de boletas.
- Los resúmenes históricos sin identidad/CDR válidos requieren conciliación o revisión. No se repararon datos productivos por rutina.
- No hay homologación Smart PSE/SUNAT real ni validación de staging del bloque. No se declara listo para producción. Antes de integrar/publicar siguen siendo obligatorias las puertas completas de `docs/RELEASE_CANONICO.md`, incluyendo esta suite PostgreSQL, frontend, navegador y verificación remota por lectura. La huella publicable debe salir del candidato confirmado y común a los tres servicios; no se generó un paquete desde cambios sin commit.

## Siguiente paso

Un bloque frontend separado para conectar la consulta del resumen, distinguir pendiente/aceptado/rechazado y corregir los códigos 2=modificar y 3=anular. La automatización del worker y la extensión de contingencia a boletas permanecen fuera de la opción elegida por el usuario.
