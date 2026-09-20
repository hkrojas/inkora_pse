# Fase 0 — Descubrimiento y clasificación de listas de precios

**Estado:** diseño y plantilla de investigación. La fase no está cerrada hasta completar la matriz de cobertura y cumplir sus criterios de aceptación.

## Propósito y límites

Inkora necesita representar listas comerciales variables de imprentas y negocios afines sin convertir cada formato de papel, sobre o bolsa en una tabla nueva del sistema. Este documento define cómo descubrir los patrones reales antes de diseñar una migración.

Esta fase no crea tablas de base de datos, migraciones, endpoints, OCR, RAG, embeddings, proveedores externos ni modelos conversacionales. Los documentos de origen son evidencia de trabajo; no son productos y no se deben subir al repositorio.

## Corpus a recopilar

- Mínimo: 20 listas reales. Objetivo: 30 a 40.
- Procedencia: al menos cinco imprentas o negocios afines.
- Formatos: fotografías, PDF, Excel, manuscritos y listas con tachaduras o correcciones.
- Tratamiento: crear una copia anonimizada y una transcripción sanitizada. No registrar nombre comercial, teléfono, RUC, cliente, dirección, cuenta bancaria ni nombre de trabajador.
- Identificador: `P0-###`, estable y sin datos de la empresa fuente.

Cada muestra debe registrar: familia, dimensiones, moneda, si el valor es costo o venta, unidad y cantidad base, vigencia, mínimos, tramos, recargos, fórmula, redondeo, confianza de transcripción y ambigüedades. Si alguno no se conoce, se marca `pendiente_de_confirmacion`; nunca se infiere.

## Patrones aprobados para clasificar

| Patrón | Uso | Atributos típicos | Resultado esperado |
|---|---|---|---|
| Búsqueda directa | Un artículo tiene un importe explícito | formato, material, acabado | importe por unidad base |
| Matriz de dimensiones | Filas y columnas forman una combinación | ancho, alto, material | importe de la intersección |
| Tramos por cantidad | El importe depende del rango solicitado | cantidad mínima/máxima | precio o total por tramo |
| Composición de materiales | Un producto final combina componentes | capas, color, tamaño | suma de componentes y recargos |
| Medida, área o peso | La medida determina el cálculo | ancho, alto, gramaje, área | importe proporcional, con unidad explícita |
| Base más recargos | Existe un precio base y adicionales | urgencia, color, acabado | desglose base + recargos |
| Mínimo comercial | Se cobra un mínimo aunque el cálculo sea menor | mínimo, moneda | máximo entre cálculo y mínimo |
| Costo más margen | El precio de venta se deriva de un costo | costo, margen, impuesto si aplica | costo y precio separados |

Una lista puede pertenecer a más de un patrón. Un caso no representable se registra como `sin_patron` con explicación; no se fuerza a encajar.

## Transcripciones iniciales sanitizadas

Las dos imágenes compartidas sirven únicamente como semillas de clasificación. Los importes no se etiquetan como costo o venta porque la evidencia visual no lo confirma; ese dato debe validarlo el administrador del tenant.

### P0-001 — Autocopiativo por composición

| Tamaño | Componente | Importe observado por millar | Confianza |
|---|---:|---:|---|
| A12 | CB | 25 | alta |
| A12 | CFB | 26 | alta |
| A12 | CF | 24 | alta |
| A4 | CB | 31 | alta |
| A4 | CFB | 32 | alta |
| A4 | CF | 30 | alta |
| Oficio | CB | 36 | alta |
| Oficio | CFB | 38 | alta |
| Oficio | CF | 35 | alta |

La misma fuente muestra resultados para una a cuatro copias. Por ejemplo, A12: 49, 75, 101 y 127. Esto cubre **composición de materiales** y puede incluir una regla de `cantidad_de_copias`. Se debe confirmar si los resultados incluyen merma, armado, impuestos o redondeo antes de tratarlos como fórmula comercial.

### P0-002 — Sobres por medida y material

La tabla observada contiene descripciones, ancho, alto y columnas de precio por millar para Bond y Manila. La transcripción de filas legibles se conserva en `sanitized-examples.json`; celdas tachadas, borrosas o aparentemente corregidas se marcan ambiguas, no se convierten en un valor definitivo. Este caso cubre **matriz de dimensiones**, **búsqueda directa** y, si se usa la medida como entrada, **medida/área**.

## Registro de ambigüedades

Cada hallazgo debe registrarse con uno de estos estados:

- `confirmado`: verificado por la fuente administradora.
- `legible_sin_confirmar`: se puede leer, pero falta confirmar significado comercial.
- `ambiguo`: tachado, incompleto, inconsistente o ilegible.
- `pendiente_de_confirmacion`: dato indispensable no proporcionado, por ejemplo moneda o costo/venta.

Una importación futura puede proponer valores `legible_sin_confirmar`, pero no podrá publicarlos sin la revisión del administrador tenant.

## Ejemplos exigidos antes de cerrar la fase

1. Actualización: una lista publicada aumenta 10 %, se duplica como nueva versión y la anterior permanece consultable.
2. Composición: autocopiativo con CB, CFB y CF, incluyendo el desglose de cada componente.
3. Corrección: una celda transcrita se corrige en borrador y no altera una versión publicada.

## Criterios de aceptación

- Al menos 90 % de las muestras recopiladas se representa con los patrones anteriores o con un patrón nuevo documentado.
- Toda muestra tiene moneda, unidad/cantidad base y clasificación costo/venta o una marca explícita de pendiente.
- Toda ambigüedad queda visible en la matriz de cobertura; no hay inferencias silenciosas.
- Existen ejemplos sanitizados de actualización y composición.
- No se selecciona ni prueba proveedor de IA durante esta fase.

Los datos de prueba estructurados se encuentran en [sanitized-examples.json](sanitized-examples.json) y la matriz operativa en [phase-0-coverage-matrix.md](phase-0-coverage-matrix.md).
