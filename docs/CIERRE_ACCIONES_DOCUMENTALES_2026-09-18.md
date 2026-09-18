# Cierre y auditoría de acciones documentales

## Alcance aprobado

Corrección posterior a `AUDITORIA_ACCIONES_DOCUMENTALES_2026-09-18.md`. Fuente: raíz canónica, revisión base `640528c4aac2f97e01b4c648aca34582e51c2c84`, comparada con el paquete operativo de SHA256 `173e56aec15cdddd738d8ec9420d217a3b93e353c098af074322457273b9df50`. Se preservan los cambios locales, sin commits ni restauraciones de archivos. No se aplican migraciones ni se alteran credenciales, series, correlativos, inventario o evidencias fiscales.

## Correcciones

| Hallazgo | Implementación y verificación |
|---|---|
| Menús distintos | `ActionMenu` común para Cotizaciones y acciones fiscales; tokens, iconos, espaciado, foco, Escape, navegación por flechas y posicionamiento limitado al viewport. Inspección en navegador integrado, temas claro/oscuro y ancho móvil 390. |
| Reenvío poco reconocible | Etiqueta provista por backend: “Reenviar a Smart PSE” cuando corresponde. Un resultado incierto mantiene el control deshabilitado y explica el bloqueo. No se debilitan las restricciones de reintento. |
| Seguimiento perdido | Consulta del trabajo, progreso, recuperación tras recarga, actualización silenciosa de datos y mensaje de conciliación. La consulta del trabajo NO consulta directamente al proveedor ni lo reenvía. |
| Emitidas SUNAT truncada en 100 | Paginación y filtros en servidor, 15 por página. Prueba con 185 documentos y búsqueda del documento 185; prueba API de folio con ceros iniciales. |
| Acciones fiscales divergentes | Facturas, Boletas, Emitidas SUNAT y detalle reutilizan `FiscalDocumentActions`; permisos, flags, estados y bloqueos provienen de `/acciones`. Se conserva la validación independiente de cada POST. |
| Anulados entre rechazados / contadores solapados | Clasificación SQL excluyente compartida con la presentación de los esquemas. No se cambia el resultado fiscal guardado. |
| Teclado inconsistente | Escape cierra ambos menús y devuelve foco; End alcanza la última acción, también en móvil. |
| Cobertura insuficiente | Tests de coherencia de filtros/estado/acciones, suspensión, búsqueda posterior a 100 y seguimiento sin aceptación ficticia. El guard de entrega exige los componentes compartidos, además de contratos y activos. |

Durante la comparación se corrigió también la presentación de fechas de historial/emitidas: se reutiliza `formatFiscalDate` para no mostrar el día anterior por conversión local de una fecha ISO. No se modifica la fecha persistida ni XML.

## Pruebas y límites

- Regresión backend: 655 aprobadas; PostgreSQL aislado: 4 GRE y 2 cotizaciones/inventario, sin omisiones. PostgreSQL local 17.4; no se afirma equivalencia exacta con Supabase 17.6.
- Frontend: 47 tests aprobados; lint y build correctos. Guard ampliado: 5 tests aprobados nuevamente. Advertencias no bloqueantes: FastAPI `on_event`, Browserslist desactualizado y aviso de revisión de scripts de esbuild en Vercel.
- Navegador integrado sobre `frontend/e2e/action-consistency.html`: datos sintéticos, llamadas externas interceptadas y bloqueadas por defecto, router en memoria y estado de trabajo de prueba persistido en la sesión. Reenvío simulado → cola → procesamiento → por conciliar; recarga recupera trabajo; modal permanece abierto al llegar al resultado; ningún POST al proveedor real.
- Comprobados menú de cotización, menú fiscal, bloqueo 1033, opciones de notas/guías/archivos, página 13/13 (181–185), filtro 000185, Escape/End y temas. Las opciones fiscales productivas se revisarán por lectura, sin ejecutarlas.
- Detector estático de Impeccable en los cuatro archivos de menús: sin hallazgos. No equivale a una certificación WCAG ni una auditoría total de Inkora.

## Auditoría final del bloque

Integridad: se usa una implementación común, no dos menús parecidos mantenidos por separado. Las acciones sensibles siguen dependiendo de permisos del backend, no de CSS ni del estado enviado por cliente.

| Dimensión | Evaluación /4 | Evidencia y límite |
|---|---:|---|
| Accesibilidad | 3 | Foco, Escape, flechas, Home/End, nombres accesibles; falta evaluación WCAG integral. |
| Rendimiento | 3 | 15 documentos por petición, polling cancelable solo para trabajos activos; las filas pendientes todavía consultan su elegibilidad individualmente. |
| Responsive | 3 | Menú contenido en viewport y opciones táctiles de 44 px; las tablas heredadas no se rediseñaron íntegramente. |
| Temas | 4 | Menú compartido consume tokens y fue inspeccionado en claro/oscuro. |
| Integridad | 4 | Estados excluyentes, acciones centralizadas, contratos conservados y paquete identificable. |
| Total | 17/20 | Bueno para el bloque revisado; no representa homologación fiscal. |

Pendientes separados: conciliación de comprobantes con resultado incierto, homologación real GRE/Smart PSE, validación histórica estricta de CDR y obligatoriedad de las puertas de CI remotas. Los tests simulados no resuelven estos pendientes. El éxito de un trabajo por sí solo no muestra aceptación fiscal.

### Hallazgos restantes de la última revisión (no ocultados)

1. **P2 — Búsqueda de cotizaciones por folio completo.** `COT-000277` no devuelve resultados; `277` sí encuentra la cotización (y otras coincidencias). Confirmado en navegador y `backend/crud/_cotizaciones_quotes.py`, que busca serie/correlativo por separado. Esta consulta comercial no fue modificada en la entrega; la búsqueda de comprobantes fiscales sí admite folio completo. Recomendación: normalizar el folio comercial en un bloque focalizado con pruebas (`impeccable harden`).
2. **P2 — Densidad de tabla comercial a ancho intermedio.** En la ventana integrada de aproximadamente 1000 px, las columnas y acciones de COT-000277 quedan demasiado juntas. Los menús funcionan y no quedan recortados; no se rediseñó la tabla heredada. Recomendación: revisar ancho mínimo/desplazamiento y transición a tarjetas (`impeccable adapt`, después `impeccable polish`).

No se detectó un P0/P1 nuevo en los recorridos de este bloque. Esto no garantiza ausencia de errores en módulos o escenarios no ejercitados. El fixture de navegador es reproducible, pero aún no existe una puerta remota obligatoria que ejecute toda esa secuencia visual.

La skill `inkora-p1-operator` mantuvo separados la recuperación operativa y el núcleo fiscal; `impeccable`/`senior-frontend` guiaron la reutilización del diseño, teclado y revisión responsive. El procedimiento Vercel exige preparar la entrega antes de promoverla. Mejoras futuras no bloqueantes: agrupar consultas de elegibilidad (`impeccable optimize`) y completar revisión global de accesibilidad antes de `impeccable polish`.

## Entrega

Paquete: `tmp/actions-consistency-20260918`, 366 archivos; proyección worker de 216 archivos backend idénticos. SHA256 **1755dc0ee9a6e22395b991f51e185b0c2437826c42ff94326643abab01a74a73**. Comparación contra entrega anterior: 17 archivos nuevos/modificados del bloque, cero eliminados; sin cambios en modelos, migraciones, favicon, fuentes, inventario o generadores fiscales/PDF.

| Componente | Identificador | Resultado |
|---|---|---|
| Railway API | `ba13de3d-c5b3-433a-b61b-bce16abf9259` | SUCCESS, `/health` ok y huella correcta, 223/223 contratos OpenAPI |
| Railway worker | `068c918f-aa60-4ba9-b696-0a57bcd1d6f2` | SUCCESS, proyección verificada y arranque sin excepción |
| Vercel | `dpl_DGxsd51QcaXBerk8BSdaBg4yR6Yc` | READY, validado antes de promover a `https://inkora-pse.vercel.app` |
| Supabase | `0022_gre_sales_documents` | Revisión comprobada por SELECT; proyecto ACTIVE_HEALTHY; sin migración |

API y frontend público devuelven la misma huella. Favicon 200, SHA256 idéntico al baseline aprobado. Worker: se acredita contenido por proyección y despliegue; su servidor de salud no prueba por sí mismo procesamiento de un trabajo real. No se crearon trabajos fiscales para verificarlo.

Rollback de aplicación disponible: API `e69c1933-68b1-47b2-a01c-79dfa69ce38b`, worker `4984f823-266b-4d38-a436-d93a0de0daba`, Vercel `dpl_GqpGrpDcgnGzJKZTnEwRsvoJAw39`. Nunca restaurar datos fiscales como rollback de código.

Verificación productiva final, solo lectura:

- Facturas: 182 = 174 aceptadas + 2 pendientes + 4 rechazadas + 2 anuladas; cero borradores. Rechazadas ya no incluye F001-000012.
- Boletas: 2 aceptadas; menú con XML/CDR, seguimiento, recuperación, guía, notas, compartir y baja según contrato del backend.
- Emitidas SUNAT: 184 documentos, 13 páginas; última página 181–184 muestra FA01-000004 a FA01-000001. Filtro `000180` encuentra su documento.
- FA01-000180: el mismo menú y bloqueo de reenvío por historial incierto desde Facturas, Emitidas y detalle. No ofrece notas/baja/guía sobre ese documento incierto.
- COT-000277: menú con Editar, Duplicar, Copiar enlace y Eliminar; no se ejecutaron estas acciones. Capturas comparadas con menú fiscal y verificación de Escape.
- Consola: sin errores en los recorridos comprobados. Logs HTTP Railway de 20:29:00 a 20:36:04 UTC: 77 solicitudes devueltas, ninguna >=400. Logs Vercel nivel error, ventana 10 minutos: sin registros devueltos. Es una inspección acotada, no observación de 24 horas ni prueba de todos los endpoints.
- Papelería: consulta explícita de configuración confirma empresa activa, entorno `produccion`, serie factura `FA01` y boleta `BB01`. Sin lectura de claves ni cambio de configuración.

El conector Vercel devolvió 403 por alcance de autenticación; se utilizó la CLI ya autenticada para inspeccionar, comprobar y promover. No se cambiaron permisos ni se desactivó protección de despliegues.
