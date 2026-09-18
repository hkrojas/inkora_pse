# Auditoría de divergencia y recuperación acotada — 18/09/2026

## Estado de lectura

La primera parte registra el diagnóstico y la publicación acotada inicial. La sección **Recuperación ampliada** al final registra el trabajo posterior; no confundir pruebas locales con despliegues ya verificados.

## Resultado inicial: ROJO para recuperación integral; acciones e identidad visual recuperadas y publicadas

No fue exclusivamente un problema de caché. La raíz y `_release_guides_prod` contienen líneas divergentes de desarrollo. Publicar la raíz completa para corregir series también publicó versiones anteriores de funciones operativas. Volver íntegramente a la otra carpeta tampoco es seguro: perdería correcciones recientes de Guías, paginación y contingencia.

Base raíz: `640528c4aac2f97e01b4c648aca34582e51c2c84` con cambios locales. Referencia de recuperación: `_release_guides_prod` (`a7b514c`). Ancestro común: `653e229dc9087753192fe1bebf6b95dc64dc5e97`.

La comparación es de contenido normalizado, no solo commits. Una diferencia no constituye por sí sola una regresión; algunas son avances que deben conservarse. No se han probado manualmente todas las funciones ni se declara completo el sistema.

## Hallazgos y alcance

| Prioridad | Hallazgo | Evidencia | Riesgo / tratamiento |
|---|---|---|---|
| P1 | Acciones de Facturas y Boletas reducidas y ocultas fuera del hover | `DocumentList.jsx` y estilos; navegador integrado | Recuperar acciones visibles y menú accesible, sin habilitar reenvíos ambiguos |
| P1 | Faltan rutas de reintento y recuperación de archivos | OpenAPI productivo: sin POST de reintento ni artifacts/retry | Recuperar backend compatible antes del frontend; preservar identidad fiscal |
| P1 | Inventario conserva cliente de seis operaciones que no existen en API | `services/inventory.js`; OpenAPI y router | Siguiente bloque: almacenes, existencias paginadas, búsqueda documental, plantilla, preview y carga masiva |
| P1 | Administración y configuración incompletas frente a la entrega anterior | Comparación de routers/schemas/modelos; Smart PSE companies y upload-payment-qr ausentes en OpenAPI | Recuperar de forma separada, con permisos y dependencias completas |
| P2 | Identidad visual antigua y fuentes faltantes | Favicon azul coincide con ancestro; build advierte dos WOFF2 inexistentes | Restaurar favicon verde y fuentes exactas de la referencia, sin rediseño |
| P2 | Landing, consulta pública y solicitudes de acceso faltan o difieren | Archivos de la referencia ausentes en raíz | Auditar dependencias y seguridad antes de recuperar; no confundir con módulos fiscales internos |

La comparación inicial encontró 61 archivos frontend diferentes y 26 contratos de router presentes en la referencia y ausentes en raíz. El conteo de contratos es estático (método/ruta declarada, antes de prefijos). Tras recuperar dos POST quedan 24 contratos anteriores pendientes de evaluar. No significa que todos se usen en producción ni que todos deban copiarse.

Confirmado en la API productiva antes de esta entrega: `PUT /cotizaciones/{cotizacion_id}` y `GET /inventario/documentos/{document_id}/disponibilidad` sí existen. No se deben eliminar sus correcciones actuales.

Lectura en navegador integrado: Inventario sí muestra 142 registros, 15 por página (10 páginas), mediante la consulta de existencias existente. La falta del contrato paginado nuevo no impide esa vista actual; la edición de almacenes y carga masiva siguen requiriendo recuperación. Cotizaciones muestra 284 documentos y 19 páginas de 15: no se perdió el historial. Estos recuentos corresponden a la sesión revisada, no son cifras fijas del producto.

## Cambio mínimo implementado

- Acciones permanentes Ver / PDF / Más, descargas autenticadas, compartir, detalle y entrada a Guías.
- Consulta backend de acciones permitidas por documento y tenant.
- Reintento restringido a fallos corregibles, sin alterar serie/correlativo; bloqueado ante resultado incierto, 1033, ticket, operación en curso, CDR o historial ambiguo.
- Recuperación de archivos separada de emisión fiscal; fallo de PDF no reenvía.
- Presentación POR CONCILIAR para resultados pendientes de confirmación, sin convertirlos en rechazo definitivo.
- Favicon verde y fuentes originales faltantes.

Archivos principales: `backend/routers/facturacion.py`, `backend/services/document_actions_service.py`, `backend/services/pdf_storage_service.py`, `frontend/src/components/documents/DocumentList.jsx`, `FiscalDocumentActions.jsx`, `fiscalDocumentActions.css`, `frontend/src/lib/utils/documentArtifacts.js`, `frontend/index.html` y estáticos indicados.

## Límites preservados

No se modifican credenciales fiscales, empresa, entorno fiscal, series configuradas, correlativos, datos fiscales, inventario productivo, lógica de cobranza ni migraciones. No se envían comprobantes ni se solicita baja real. El worker existente conserva sus controles. Esta entrega no resuelve la conciliación pendiente de facturas ni la homologación GRE.

La skill `inkora-p1-operator` limita esta recuperación a un bloque y exige pruebas; por eso no se fusionan indiscriminadamente las dos carpetas. Impeccable guía la reutilización de botones y estilos existentes, sin un nuevo diseño.

## Pruebas ejecutadas

`backend/venv/Scripts/python.exe -m pytest backend/test_document_actions_recovery.py backend/test_operational_frontend_contracts.py backend/test_emission_queue.py backend/test_facturacion_guards.py backend/test_cotizaciones.py -q`

Resultado: **121 passed**. Incluye tenant ajeno, permisos, suspensión, contingencia, 1033, duplicidad de petición, identidad fiscal y cero nuevos movimientos de inventario. Usa SQLite y simulación; no acredita concurrencia PostgreSQL real ni aceptación SUNAT.

`npm run lint` y `npm run build`: correctos. Advertencia no bloqueante de Browserslist desactualizado. Las advertencias de fuentes desaparecen al restaurar los dos archivos.

Navegador integrado contra fixture local, sin llamadas al proveedor: menú completo en documento aceptado, reintento deshabilitado para ambiguo, confirmación del reintento permitido y mensaje de contingencia pendiente (no aceptación ficticia). Consola sin errores en esas comprobaciones. No se enviaron WhatsApp/correos ni bajas.

## Entrega reproducible

`tmp/package_actions_recovery.ps1` compara SHA256 del árbol previo con una lista explícita de archivos permitidos y crea un paquete nuevo. Excluye pruebas históricas, salidas de operadores, entornos, logs, credenciales y carpetas auxiliares. `release-manifest.json` identifica también los estáticos; no se publica directamente el árbol de trabajo completo.

El paquete publicado es `tmp/actions-recovery-release-v2`; el primer paquete de trabajo no se publicó porque contenía fixtures históricos, excluidos en la versión final.

Railway API: despliegue `258df439-0ba4-427c-89db-c55df745d952`, SUCCESS, arranque correcto y `/health` ok. Los tres contratos de acciones/reintento/archivos están presentes en OpenAPI después de publicar. Sin migración ni despliegue del worker. La etiqueta estática de `/health` conserva `640528c-cotizaciones-r2`; no usarla como huella fiable del contenido: para esta entrega se usan el ID de despliegue y el manifiesto SHA256 `DC90ADFCCAFED46F6A2F42BC5C4105BCB006A12E1DD1A0CF7507BD1336CF2971`.

Vercel: compilación `dpl_6djj5UPbk7iwJNohz6bKxKPi4jLJ`, READY, 17 segundos; preparada con entorno production y posteriormente promovida a `https://inkora-pse.vercel.app`. HTML público apunta a `index-CptUaBhd.js` y favicon versionado. Favicon remoto idéntico al restaurado. Ambos WOFF2 responden 200 con `font/woff2`.

Comprobación productiva en navegador integrado: Ver / PDF / Más visibles sin hover (opacidad 1), menú de FA01-000178 con detalle, guía, XML/CDR, compartir, archivos y baja. FA01-000180 muestra POR CONCILIAR y reintento deshabilitado con motivo autoritativo del backend. Las consultas de acciones retornan 200. GET autenticado del PDF existente `/cotizaciones/527/pdf/download` devuelve 200 (986 ms); la apertura de una pestaña blob no quedó observable en el navegador integrado, por lo que no se acredita una inspección visual de ese PDF en esta prueba.

Railway: consulta de logs HTTP de los últimos 10 minutos al cierre, límite 100, sin respuestas >=400 devueltas; arranque sin excepción. Navegador sin errores de consola en las comprobaciones realizadas. Es una ventana acotada, no monitoreo de 24 horas ni garantía de ausencia de errores en flujos no ejercitados.

## Siguiente bloque

Recuperar exclusivamente los seis contratos de inventario y sus servicios/esquemas/pruebas; verificar el frontend contra el mismo backend. Después, administración y configuración. No hacer rollback de datos ni copiar toda la referencia.

## Recuperación ampliada — bloques implementados posteriormente

Se compararon fuentes normalizadas y símbolos/rutas contra el ancestro, preservando el árbol local. La comparación estática final no encuentra rutas de la referencia ausentes en la raíz recuperada. Esto no equivale a declarar homologadas todas las operaciones fiscales.

| Bloque | Recuperado / conservado | Verificación y límites |
|---|---|---|
| Facturas y boletas | Acciones permanentes, detalle, PDF/XML/CDR, compartir, Guías, baja elegible, regeneración y reintento condicionado | Se conservan 1033/resultado ambiguo bloqueados, serie por tenant y descarga autenticada. Ningún envío real |
| Cotizaciones | PUT transaccional, número conservado, PDF actualizado, historial paginado y disponibilidad | Se conservó la implementación raíz y sus bloqueos; no se sustituyó por la versión sin paginación |
| Inventario | Edición de almacén, existencias paginadas, búsqueda documental, plantilla, preview y carga masiva | Stock por tenant/almacén; CSV/XLSX; repetidos y cantidades inválidas rechazados; rollback completo; recibo persistente de idempotencia incluso con delta cero |
| Productos/clientes | Stock inicial, búsqueda, filtros, paginación, formularios y datos consultados | Stock inicial restringido a admin, almacén validado; no se modifica unidad con kardex ni se activa inventario indiscriminadamente |
| Configuración | Subida/recorte de QR de pago, bancos visibles en cotización, plantillas de correo/WhatsApp, colores PDF | Identidad fiscal y secretos no editables por tenant; actualización de PDF comercial, no de documentos fiscales históricos |
| PDF comercial/fiscal | Formato Inkora, cliente documental, bancos/QR, colores, cuatro decimales visibles y pie compacto | PDF sintético renderizado e inspeccionado. Generador GRE actual conservado; no se copió el anterior |
| Cobranza | Acción rápida para registrar pago del saldo con confirmación | Reutiliza endpoint y restricciones existentes; no altera cálculo del saldo ni registra pagos reales |
| Superadmin | users-detail, lista/alta/edición/sincronización/activación de empresa Smart PSE y consultas de auditoría | Solo superadmin; sincronización exige RUC exacto, no primer resultado aproximado; nunca se imprimen secretos |
| Acceso público | Solicitudes de acceso, estado con token, aprobación/rechazo y consulta pública de comprobante | Tablas ya existentes; consulta exige identidad documental, fecha e importe; no devuelve URLs privadas ni cliente; rate limit |
| Navegación/estilo | Landing, login, búsqueda global, notificaciones, menú de usuario, select con búsqueda remota, Drawer y combobox | Reutilización del diseño existente; favicon verde y fuentes fijados por huella; sin ocultar módulos fiscales existentes |
| Protección fiscal puntual | Eliminación de detracción automática por superar importe; serialización de datos explícitos; bloqueo de baja con nota de inventario activa | Pruebas sin proveedor. No se altera metadata de comprobantes ya emitidos ni se habilitan reenvíos históricos |

### Diferencias deliberadamente no copiadas

- `ENABLE_ADVANCED_FISCAL` de la referencia ocultaba módulos por defecto: no se incorpora.
- Reenvíos de la referencia menos restrictivos y borrado automático de metadata de detracción: no se incorporan. Una corrección de datos fiscales existentes requiere diagnóstico propio.
- El helper de error final de la referencia libera reservas al fallar: no se incorpora indiscriminadamente; un resultado ambiguo conserva su bloqueo y conciliación.
- Reversión de inventario ya existe en raíz; se mantiene su clave de idempotencia y bloqueo por GRE. Se recupera la protección adicional frente a notas activas, no otra salida/entrada duplicada.
- Columnas de precio a 10 decimales y estados adicionales de artefactos de la referencia no se incorporan sin migración. Supabase conserva precios/cantidades a cuatro decimales. Esta entrega no cambia esquema.
- Las diferencias del reloj fiscal, fecha de conversión de cotización y cálculo decimal frontend requieren un bloque fiscal específico antes de afirmar paridad total. No se mezclan cambios de fecha/importe de documentos existentes con la recuperación de interfaz.
- Cambios cosméticos de paginación en módulos auxiliares no significan pérdida de función; la navegación existente permanece.
- Readiness con escritura/borrado de objetos de Storage no se copia a una comprobación de lectura.

### Pruebas y evidencia ampliada

Inventario, permisos, PDF, solicitudes, consulta pública, comunicación y Smart PSE admin cuentan con tests focalizados. La suite general inicial halló expectativas antiguas de correlativo de descarga de seis dígitos (el código ya usaba ocho antes de esta recuperación) y una sanitización de nombre de archivo con doble guion. Se corrigieron las expectativas obsoletas y la sanitización real; no se cambió la numeración de documentos.

PostgreSQL local aislado: servidor 17.4, bases exclusivas `inkora_gre_recovery_20260918` y `inkora_quote_recovery_20260918`. Supabase reportó 17.6: no se declara equivalencia exacta de versión. Pruebas sincronizadas mediante barreras, no simples llamadas secuenciales. Se añade concurrencia de carga masiva con igual clave, un único recibo y movimiento.

Navegador integrado sobre fixture local que intercepta llamadas API y nunca las reenvía: Configuración, editor visual/colores, Superadmin/usuarios, inventario y carga masiva. Se detectó una omisión de `metrics` en el fixture de usuarios; se corrigió el fixture conforme al contrato real. No fue una escritura ni una consulta al tenant productivo. La validación visual no sustituye los tests de backend.

### Prevención

`contracts/operational_routes.json` fija todos los métodos/rutas operativos aprobados. `test_release_guard.py` verifica su conservación y demuestra que eliminar PUT de cotizaciones falla. `contracts/release_assets.json` fija favicon/fuentes. `scripts/release_guard.py` genera y comprueba un paquete inmutable con SHA256; API y frontend exponen la misma huella, sin secretos. `scripts/verify_recovery.ps1` detiene publicación ante tests/lint/build fallidos y exige bases locales cuando se solicita PostgreSQL.

El procedimiento completo, rollback y límites están en [RELEASE_CANONICO.md](RELEASE_CANONICO.md). Estos controles están implementados en el repositorio; no se afirma que una protección de rama remota obligue a ejecutarlos. La skill `inkora-p1-operator` motivó la separación de bloques y preservación fiscal; Impeccable/senior-frontend guiaron la recuperación del diseño existente, y la skill PDF exigió renderizar el documento de prueba.

### Cierre de validación local

`scripts/verify_recovery.ps1 -RequirePostgres`: **643 backend + 4 PostgreSQL GRE + 2 PostgreSQL cotizaciones/inventario + 44 frontend**, todos aprobados. Lint y build correctos. Advertencias: deprecación `on_event` en FastAPI y Browserslist desactualizado; no bloquean esta entrega. No hubo tests PostgreSQL omitidos en este comando.

La comparación contra OpenAPI productivo exige **223/223 contratos operativos**. Se excluyeron explícitamente cinco rutas solo local/test, no funcionalidades productivas. Suite del guard repetida después de ajustar ese baseline: 5 aprobadas.

Paquete inmutable: `tmp/operational-recovery-20260918`, 359 archivos, revisión base `640528c4aac2f97e01b4c648aca34582e51c2c84`, huella **173e56aec15cdddd738d8ec9420d217a3b93e353c098af074322457273b9df50**. Proyección worker: 215 archivos backend idénticos en `tmp/operational-recovery-worker-20260918`, sin introducir el Dockerfile de la API en su contexto de compilación.

API Railway `e69c1933-68b1-47b2-a01c-79dfa69ce38b`: SUCCESS, `/health` informa esa huella; OpenAPI 223/223. Primer intento worker `89c20bc7-8eab-40d0-aef2-58f175db1e2d` falló en build por contexto backend/Dockerfile raíz: no llegó a arrancar. Se corrigió mediante proyección, manteniendo configuración y secretos del servicio, sin alterar código de aplicación.

Rollback previo registrado: API `258df439-0ba4-427c-89db-c55df745d952`; worker `92312a1d-86ec-4646-a41e-e007c23d94c6`; Vercel `dpl_6djj5UPbk7iwJNohz6bKxKPi4jLJ`. No restaurar datos para revertir aplicación.

### Entrega ampliada publicada y comprobación final

| Componente | Despliegue actual | Resultado |
|---|---|---|
| Railway API | `e69c1933-68b1-47b2-a01c-79dfa69ce38b` | SUCCESS; salud `ok`; 223/223 contratos operativos presentes |
| Railway worker | `4984f823-266b-4d38-a436-d93a0de0daba` | SUCCESS mediante proyección backend verificada; arranque registrado sin excepción |
| Vercel | `dpl_GqpGrpDcgnGzJKZTnEwRsvoJAw39` | READY y promovido a `https://inkora-pse.vercel.app` |
| Supabase | Esquema existente `0022` | Inspección de compatibilidad de solo lectura; sin migración ni restauración de datos |

API `/health.delivery` y frontend `/release.json` devolvieron la misma revisión y SHA256 `173e56aec15cdddd738d8ec9420d217a3b93e353c098af074322457273b9df50` después de promover. El favicon público responde 200 y coincide con la huella aprobada. El bundle público es `index-B_5stC0S.js`.

La identidad del worker se acredita por su proyección de 215 archivos idénticos al paquete aprobado y el ID de despliegue. No se pudo leer `/app/release.json` dentro del contenedor por ausencia de llaves SSH; no se crearon accesos nuevos. Su log disponible dice `Starting Container`; no se afirma haber procesado un trabajo fiscal real ni que el pequeño servidor de salud compruebe la actividad del bucle del worker.

Verificación final en navegador integrado con sesión real, sin guardar formularios ni emitir:

- Facturas: listado de 182 documentos, acciones visibles y menú; FA01-000179/180 continúan POR CONCILIAR. El despliegue no los reenvía ni cambia su numeración.
- Inventario: 141 registros y dos almacenes, paginación y acceso a carga masiva; sin errores de consola en la revisión.
- Cotizaciones: 284 registros, 19 páginas de 15. COT-000277 conserva cinco líneas y total S/ 220.00; detalle, PDF, compartir y acciones de emisión visibles. No se pulsaron guardar, emitir ni registrar pago.
- Los recuentos son fotografías de lectura, no invariantes del sistema. Las operaciones de escritura se verificaron con pruebas aisladas, no alterando documentos de Papelería.

Consulta final de logs HTTP Railway, últimos 10 minutos y límite 100, con filtro `>=400`: sin resultados devueltos. Consola sin errores en las páginas comprobadas. Esta evidencia es acotada: no constituye vigilancia de 24 horas ni prueba de todos los escenarios fiscales.

**Estado de cierre:** funcionalidades operativas perdidas identificadas recuperadas y publicadas; diferencias fiscales deliberadas y límites de homologación listados arriba siguen abiertos. No declarar equivalencia total de comportamiento ni homologación SUNAT a partir del número de rutas o pruebas simuladas. Falta convertir las puertas locales de publicación en controles obligatorios de CI/protección remota; mientras tanto, el runbook debe aplicarse explícitamente a cada entrega.
