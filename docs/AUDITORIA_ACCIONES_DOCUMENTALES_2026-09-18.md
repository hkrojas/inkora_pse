# Nueva auditoría: acciones documentales y coherencia visual

## Resultado

**Amarillo. Recuperación incompleta de experiencia y comportamiento.** La existencia de 223 contratos y un despliegue coherente no acreditaba paridad funcional ni visual. Se rectifica cualquier interpretación del cierre anterior como recuperación completa.

Auditoría de solo lectura del código raíz, comparación selectiva con `_release_guides_prod` y navegador integrado productivo. Sin cambios de código de aplicación, despliegues, escrituras productivas, reenvíos, bajas ni consultas fiscales al proveedor. Único archivo creado: este informe. La skill `inkora-p1-operator` exige diagnóstico antes de implementar; Impeccable exige revisar la implementación y la interfaz, no limitarse al detector.

## Alcance revisado

- Facturas y Boletas: `DocumentList.jsx`, `FiscalDocumentActions.jsx`, `fiscalDocumentActions.css`, `documentArtifacts.js`, `emissionJobs.js`.
- Cotizaciones: historial comercial, menú Más y pestaña Emitidas SUNAT; `CotizacionesPage.jsx`, `services/cotizaciones.js`, `cotizacionesHistory.css`, `globals.css`.
- Backend: acciones permitidas y reintento, filtros y contadores de facturas, recuperación documental, esquema de listado y pruebas relacionadas.
- Navegador real: FA01-000180 pendiente de conciliación, FA01-000173 rechazada, COT-000277, bandeja Emitidas SUNAT y filtro Rechazadas.
- Boletas comparte componente con Facturas: el alcance de código incluye ambas, pero no se ejecutó un envío ni se afirma una nueva prueba visual de Boletas en esta auditoría.

## Hallazgos

| Prioridad | Hallazgo | Evidencia | Impacto / riesgo | Recomendación |
|---|---|---|---|---|
| P2 | Más de Facturas no conserva el diseño de Cotizaciones | FiscalDocumentActions.jsx:138 y CSS:3-9 crean otro menú; capturas del navegador confirman texto plano sin iconos. CotizacionesPage.jsx:2778 conserva iconos y clases compartidas | Pérdida de coherencia y reconocimiento de acciones. La referencia anterior de Facturas usaba `history-actions-more-menu` y `history-actions-mobile-item` | Componente visual compartido, manteniendo el portal necesario para evitar recortes. Recuperar iconos, tipografía, sombra y espacios del diseño Inkora |
| P2 | Reenvío existe, pero su nombre y disponibilidad no son claros | Botón real «Reintentar envío SUNAT»; no existe el texto «Reenviar a Smart PSE» en los dos árboles comparados. En FA01-000180 está deshabilitado por historial incierto; FA01-000173 por conciliación de inventario | El usuario lo percibe como eliminado; tras cargar acciones puede quedar abajo en un menú desplazable. Un texto genérico no indica cómo resolver el bloqueo | Nombre explícito «Reenviar a Smart PSE» si ese es el proveedor, motivo accesible y enlace al seguimiento/revisión. No habilitar reenvío de documentos ambiguos |
| P1 | Se perdió el seguimiento del reintento | La referencia tenía `pollFiscalRetry` y estado visible (`DocumentList.jsx:341`). El actual `FiscalDocumentActions.jsx:115` muestra un toast, cierra modal y recarga una vez, ignorando `shouldPoll` y `job_id` para seguimiento | El resultado posterior del worker no se refleja automáticamente. El usuario no ve progreso ni recupera seguimiento al recargar | Recuperar seguimiento por job, con queued/processing/contingencia/conciliación/resultado final diferenciados. No volver al mensaje incorrecto de aceptación ante cualquier trabajo completado |
| P1 | La bandeja fiscal dentro de Cotizaciones solo permite navegar/buscar los primeros 100 | `services/cotizaciones.js:6`, `CotizacionesPage.jsx:2188,2244,2282`. Navegador: 184 comprobantes, aviso «Mostrando los 100 más recientes» y siete páginas | Los 84 restantes no son alcanzables mediante esa paginación; los filtros locales no los buscan. El historial comercial de 284 cotizaciones NO tiene este límite | Paginación y filtros reales en backend; 15 por página, total autoritativo y búsqueda de comprobantes antiguos |
| P1 | Las acciones dependen de la pantalla de entrada | CotizacionesPage.jsx:3152-3153 permite nota/anular con solo no estar anulada; navegador muestra esas acciones para FA01-000180 POR CONCILIAR y FA01-000173 RECHAZADO. No ofrece reintento/recuperación/CDR como Facturas. La descarga XML depende de URL, no de contenido persistido | Interfaz contradictoria; acciones ofrecidas que el backend puede rechazar y documentos disponibles por una pantalla pero no por otra. No se acredita vulnerabilidad de autorización: no se ejecutaron esas acciones | Política autoritativa de acciones compartida en las bandejas y detalle, preservando diferencias legítimas entre cotización comercial y comprobante fiscal. Descargas por cliente autenticado |
| P1 | Filtros y contadores no usan la misma clasificación que la etiqueta de la fila | `_fiscal_doc_tab_filter` en facturacion.py:214-240 usa CDR/error y no excluye anuladas en emitted/rejected. Navegador: Rechazadas incluye F001-000012 con etiqueta ANULADO; 174+2+5+2=183 frente a 182 facturas | Conteos superpuestos, filtros engañosos y selección incorrecta de documentos a revisar | Clasificación excluyente y consistente con anulación, aceptación y conciliación; pruebas cruzadas API/etiquetas sin modificar los resultados fiscales almacenados |
| P2 | Teclado y comportamiento del desplegable no son consistentes | Escape cierra Facturas y devuelve foco; en COT-000277 se pulsó Escape y el menú siguió abierto. Cotizaciones usa details; Facturas portal con posición calculada una vez, sin seguimiento de scroll | Comportamiento imprevisible; menú puede perder relación espacial con el botón al desplazar. Este último punto se confirma por código, no mediante una prueba móvil | Contrato común de apertura/cierre, Escape, foco, clic exterior y reposicionamiento. Mantener Tab accesible y no exigir roles de menú si se implementa como popover de enlaces |
| P1 | Las pruebas actuales no detectan estas regresiones | 17 tests focalizados pasan. El guard revisa rutas, hashes y marcadores `retry_emission`/`retry_artifacts`; no comprueba consistencia de menús, seguimiento o búsqueda más allá de 100 | Puede aprobarse otra entrega incompleta aunque compile y tenga los endpoints | Añadir regresión de comportamiento y visual de las tres entradas, con datos sintéticos y proveedor simulado, antes de publicar el siguiente arreglo |

### Diferencia visual concreta

| Propiedad | Cotizaciones | Facturas actual |
|---|---|---|
| Opciones | Iconos Lucide y texto | Texto sin iconos |
| Tipografía | 12 px, peso 800 | 13 px, sin ese peso explícito |
| Contenedor | Radio 14 px y `--shadow-floating` | Radio 12 px, sin sombra flotante definida |
| Ancho | Mínimo 192 px | 300 px, limitado al viewport |
| Estructura | Acciones compactas | Cabecera documental, separador y mensajes |

Los mensajes fiscales y el control de foco aportan valor y deben conservarse al normalizar el diseño; no se propone copiar ciegamente el componente anterior. Tampoco se afirma que todas las diferencias sean errores: una cotización comercial puede editarse/duplicarse, mientras una factura aceptada no debe editarse libremente.

### Reenvío: qué está y qué falta

- Existe el POST `/facturas-emitidas/{comprobante_id}/reintentar`; valida tenant, permisos, estado, serie e historial, y conserva identidad fiscal.
- El botón actual aparece al cargar acciones para comprobantes no anulados y no aceptados. Una factura aceptada no debe ofrecer reenvío fiscal.
- FA01-000180: texto «El historial contiene un resultado incierto; se requiere conciliación». Bloqueo correcto que no debe quitarse para recuperar un botón.
- FA01-000173: se muestra «El inventario requiere conciliación antes del reintento». En la bandeja alternativa se lee error de política 0111. Es necesaria revisión del caso, no asumir que todo rechazo admite reenvío.
- La política actual es muy conservadora: exige fallo previo de validación o el código específico 3127, bloquea CDR, detracción, historial incierto y reservas de inventario no activas. Se debe revisar por categorías de evidencia antes de ampliar casos, sin liberar duplicados ni restablecer reservas arbitrariamente.
- Falta mostrar seguimiento y una ruta operativa clara para los bloqueados. «Actualizar lista» solo relee Inkora: no consulta Smart PSE ni concilia por sí mismo.
- Reintentar archivos regenera PDF y persiste CDR disponible; no reenvía ni reconstruye un XML firmado ausente. Esto también debe explicarse, sin presentar esa limitación como una regresión nueva: la referencia revisada tampoco reconstruía XML en ese endpoint.

## Evaluación técnica Impeccable

Veredicto: **no cumple coherencia de implementación** en las acciones documentales. Detector estático: cero avisos en los tres archivos analizados; no detecta la divergencia entre componentes ni sustituye la inspección visual.

| Dimensión | Puntuación /4 | Evidencia y límites |
|---|---:|---|
| Accesibilidad | 2 | Botones etiquetados y foco en Facturas; Escape inconsistente en Cotizaciones. No certificación WCAG ni medición completa de contraste |
| Rendimiento | 3 | Listado Facturas paginado y consulta de acciones al abrir; Cotizaciones carga 100 fiscales además de su página comercial. No perfil de red/CPU exhaustivo |
| Responsive | 2 | Facturas limita ancho/alto al viewport y tiene objetivos de 44 px en móvil; Cotizaciones tiene otro sistema. No se ejecutó matriz móvil en esta auditoría |
| Tema | 3 | Ambos usan tokens, pero tipografía, iconos y elevación divergen. No se alteró el tema del usuario para probar oscuro |
| Integridad | 1 | Seguimiento perdido, acciones distintas y clasificación/paginación contradictorias |
| Total | **11/20** | Evaluación del alcance inspeccionado, no nota de todo Inkora |

Positivo: aislamiento y permisos del reintento comprobados; sin reenvíos ambiguos; descargas autenticadas de Facturas; botones principales visibles; serie conservada; consulta de acciones solo al abrir. Deben mantenerse.

## Cambio mínimo sugerido

Un bloque de **acciones documentales coherentes**: modelo común de acciones y estados, menú visual reutilizable, reenvío explícito con seguimiento, descargas uniformes, y paginación fiscal real. Separar las revisiones de frontend y backend; no requiere inicialmente migración. No cambiar cálculo de importes, fechas, series, resultados fiscales ni política de conciliación para resolver apariencia.

## Archivos que tocaría

- `frontend/src/components/documents/FiscalDocumentActions.jsx` y `fiscalDocumentActions.css`.
- `frontend/src/components/documents/DocumentList.jsx`.
- `frontend/src/pages/CotizacionesPage.jsx` y `CotizacionDetalle.jsx` para conectar el contrato compartido, no copiar lógica fiscal.
- `frontend/src/services/cotizaciones.js` y utilidades de seguimiento/estado.
- Estilos compartidos del menú y pruebas de componentes/E2E.
- `backend/services/document_actions_service.py` y `backend/routers/facturacion.py`: clasificación, motivos de bloqueo y filtros coherentes, con pruebas aisladas. Reutilizar comprobaciones existentes de autorización y elegibilidad.

## Tests/comandos

Ejecutados:

```powershell
backend/venv/Scripts/python.exe -m pytest backend/test_document_actions_recovery.py backend/test_operational_frontend_contracts.py -q
# 17 passed, 25.95 s. SQLite en memoria y mocks; cero emisión real.
node .agents/skills/impeccable/scripts/detect.mjs frontend/src/components/documents/FiscalDocumentActions.jsx frontend/src/components/documents/fiscalDocumentActions.css frontend/src/styles/cotizacionesHistory.css --json
# []
```

Navegador integrado: menús y teclado; estado de dos facturas; bandeja fiscal truncada; anulada en filtro Rechazadas; consola sin errores en los pasos revisados. No hubo clic en confirmar, emitir, reenviar, anular, registrar pago ni compartir.

Antes de publicar la corrección, agregar y ejecutar casos:

1. Misma factura desde Facturas, Boletas (tipo correspondiente), Emitidas SUNAT y detalle: acciones y motivos coherentes.
2. Aceptada, anulada, corregible, 1033, timeout, en cola, contingencia y falta de permisos: nada de aceptación ficticia ni reenvío ambiguo.
3. Reenvío simulado: estados vivos, fallo, consulta de job y recuperación tras recarga, un solo trabajo.
4. 184+ documentos: acceder y buscar el más antiguo; 15 por página y conteo sin solapamientos.
5. XML/CDR en contenido, referencia privada, URL, ausente y error: descarga autenticada y mensaje correcto.
6. Capturas comparativas de menús, teclado/Escape, móvil, zoom, tema claro/oscuro y viewport pequeño; no usar documentos reales para escritura.
7. Tests actuales, `npm run lint`, `npm run build` y guard de entrega, sin confundir su aprobación con paridad funcional.

## Recomendación

**Implementar el bloque después de aprobar este diagnóstico.** La skill operativa impide corregir código como efecto secundario de una auditoría. Prioridad: requisitos y seguimiento con `$impeccable harden`, coherencia de nombres con `$impeccable clarify`, comportamiento adaptable con `$impeccable adapt`, y cierre visual con `$impeccable polish`; repetir `$impeccable audit`. Pueden abordarse uno por uno o en el orden acordado.
