# Fase 0 — Matriz de cobertura

**Estado:** plantilla de ejecución. Los registros `PENDIENTE` son cuotas de investigación, no muestras ya recopiladas. Solo `P0-001` y `P0-002` son observaciones sanitizadas iniciales.

| ID | Fuente esperada | Patrón principal | Patrones secundarios | Costo/venta | Moneda y unidad | Estado |
|---|---|---|---|---|---|---|
| P0-001 | Foto anonimizada: autocopiativo | composición | cantidad de copias | pendiente | pendiente, millar | patrón validado; semántica comercial pendiente |
| P0-002 | Foto anonimizada: sobres | matriz de dimensiones | búsqueda directa | pendiente | pendiente, millar | normalización validada; celdas ambiguas pendientes |
| P0-003 | Excel de imprenta A | búsqueda directa | base más recargos | por confirmar | por confirmar | PENDIENTE |
| P0-004 | PDF de imprenta A | tramos por cantidad | mínimo comercial | por confirmar | por confirmar | PENDIENTE |
| P0-005 | Manuscrito de imprenta A | composición | redondeo | por confirmar | por confirmar | PENDIENTE |
| P0-006 | Foto de imprenta B | matriz de dimensiones | medida/área | por confirmar | por confirmar | PENDIENTE |
| P0-007 | Excel de imprenta B | costo más margen | mínimo comercial | por confirmar | por confirmar | PENDIENTE |
| P0-008 | PDF de imprenta B | búsqueda directa | tramos por cantidad | por confirmar | por confirmar | PENDIENTE |
| P0-009 | Foto de imprenta B | base más recargos | redondeo | por confirmar | por confirmar | PENDIENTE |
| P0-010 | Foto de imprenta C | composición | tramos por cantidad | por confirmar | por confirmar | PENDIENTE |
| P0-011 | Excel de imprenta C | medida/área | mínimo comercial | por confirmar | por confirmar | PENDIENTE |
| P0-012 | PDF de imprenta C | matriz de dimensiones | búsqueda directa | por confirmar | por confirmar | PENDIENTE |
| P0-013 | Manuscrito de imprenta C | tramos por cantidad | base más recargos | por confirmar | por confirmar | PENDIENTE |
| P0-014 | Foto de imprenta D | búsqueda directa | costo más margen | por confirmar | por confirmar | PENDIENTE |
| P0-015 | Excel de imprenta D | composición | mínimo comercial | por confirmar | por confirmar | PENDIENTE |
| P0-016 | PDF de imprenta D | medida/área | redondeo | por confirmar | por confirmar | PENDIENTE |
| P0-017 | Foto de imprenta D | matriz de dimensiones | tramos por cantidad | por confirmar | por confirmar | PENDIENTE |
| P0-018 | Excel de negocio afín E | búsqueda directa | base más recargos | por confirmar | por confirmar | PENDIENTE |
| P0-019 | Foto de negocio afín E | tramos por cantidad | mínimo comercial | por confirmar | por confirmar | PENDIENTE |
| P0-020 | Manuscrito de negocio afín E | costo más margen | composición | por confirmar | por confirmar | PENDIENTE |

## Instrucciones para completar una fila

1. Sustituir la descripción genérica de la fuente por un identificador anonimizado, nunca por datos de la empresa.
2. Adjuntar solo una transcripción sanitizada, no el original.
3. Confirmar moneda, unidad base y naturaleza del valor (`cost` o `sale`).
4. Anotar fórmula, recargos, vigencia, mínimos, redondeos y celdas ambiguas.
5. Marcar la muestra `representada`, `requiere_variacion` o `sin_patron` y justificarla.

La cobertura se considera suficiente al tener al menos 20 muestras reales de cinco procedencias y 90 % en estado `representada` o `requiere_variacion` documentada.

La validación inicial de las dos muestras disponibles está documentada en [phase-0-two-sample-validation.md](phase-0-two-sample-validation.md). Esta prueba permite comenzar un núcleo MVP, pero no equivale al cierre estadístico de la Fase 0.
