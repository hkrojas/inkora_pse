# Validación inicial con dos listas reales

## Resultado

**Amarillo — apto para iniciar un MVP controlado.** Las dos listas encajan en el modelo conceptual sin crear tablas específicas por producto o material. Sin embargo, ambas carecen de moneda, vigencia y confirmación de si el importe es costo o venta; por ello no deben convertirse todavía en una lista publicable.

## Alcance revisado

- `P0-001`: tabla fotografiada de papel autocopiativo, componentes CB/CFB/CF y tamaños A12, A4 y Oficio.
- `P0-002`: tabla fotografiada de sobres por descripción, dimensiones, material Bond/Manila y precio por millar.
- Contratos de `price_catalog_version`, `price_catalog_row`, `price_rule_set` y `price_import_job` descritos en la arquitectura de Fase 1.
- No se probó OCR, ningún modelo de IA ni una importación automática.

## Prueba 1 — Autocopiativo por composición

La tabla queda representada por una fila de precio por cada combinación de tamaño y componente. El número de copias no necesita convertirse en una columna de base de datos.

Regla observada:

```text
total = CB + ((copias - 1) × CFB) + CF
```

| Tamaño | 1 copia | 2 copias | 3 copias | 4 copias | Resultado |
|---|---:|---:|---:|---:|---|
| A12 | 49 | 75 | 101 | 127 | coincide con la fotografía |
| A4 | 61 | 93 | 125 | 157 | coincide con la fotografía |
| Oficio | 71 | 109 | 147 | 185 | coincide con la fotografía |

Las doce combinaciones se reprodujeron exactamente mediante aritmética decimal. Esto valida los patrones `lookup` y `composition` para la muestra. Antes de publicar se debe confirmar qué significa “1 Cop.” en la operación comercial y si existen merma, impresión, acabado, impuesto o cantidad mínima fuera del costo del papel.

Ejemplo normalizado:

```json
{
  "attributes": {"size": "A12", "layer": "CFB"},
  "amount": "26.000000",
  "base_unit": "millar",
  "base_quantity": "1000",
  "amount_kind": "pending_confirmation"
}
```

## Prueba 2 — Sobres por dimensiones y material

Las columnas Bond y Manila se normalizan en filas independientes. De esta forma otro negocio puede utilizar Kraft, Couche u otro material sin requerir una migración ni una columna nueva.

| Descripción | Ancho × alto | Material | Importe observado | Resultado |
|---|---|---|---:|---|
| Pago | 10.8 × 18 cm | Bond | 13.00 | representable |
| Pago | 10.8 × 18 cm | Manila | 11.20 | representable |
| 1/2 Oficio | 19 × 26 cm | Bond | 29.00 | representable |
| 1/2 Oficio | 19 × 26 cm | Manila | 29.70 | representable |

Ejemplo normalizado:

```json
{
  "attributes": {
    "description": "PAGO",
    "width_cm": "10.8",
    "height_cm": "18",
    "material": "MANILA"
  },
  "amount": "11.200000",
  "base_unit": "millar",
  "base_quantity": "1000",
  "amount_kind": "pending_confirmation"
}
```

Las celdas tachadas o borrosas permanecen como ambigüedades dentro de un borrador. No deben rellenarse por aproximación ni publicarse automáticamente.

## Hallazgos

| Prioridad | Hallazgo | Evidencia | Riesgo | Recomendación |
|---|---|---|---|---|
| P1 | Falta identificar costo o venta | Ninguna foto lo indica con certeza | mostrar un costo interno como precio al cliente | exigir `amount_kind` antes de publicar |
| P1 | Falta confirmar moneda | La unidad “millar” aparece, pero no la moneda | cálculos comercialmente inválidos | moneda obligatoria a nivel de versión |
| P1 | La tabla de sobres contiene correcciones/borrosidad | varias celdas no son inequívocas | publicar precios incorrectos | conservar confianza y revisión por celda en borrador |
| P2 | La fórmula de autocopiativo cubre material, no necesariamente el trabajo final | coincidencia aritmética de componentes | cotización incompleta por omitir impresión o acabados | separar costo de material y recargos comerciales |
| P2 | Solo hay dos familias observadas | cobertura actual limitada | descubrir tarde un patrón adicional | construir extensible y ampliar muestras durante el MVP |

## Decisión de avance

Con estas dos muestras se puede comenzar un primer bloque de backend limitado a:

1. catálogos y versiones `draft`/`published`/`archived`;
2. filas con atributos dinámicos;
3. edición manual y auditoría;
4. reglas `lookup` y `composition`;
5. separación obligatoria de costo y venta;
6. aislamiento tenant y pruebas de historial.

Todavía no se considera validado implementar reglas de área, peso, tramos, porcentajes o márgenes porque ninguna de las dos muestras permite verificarlas. Esas operaciones pueden permanecer en el contrato conceptual sin entrar en el primer MVP.

## Tests ejecutados

Se cargó `sanitized-examples.json` y se calcularon las doce combinaciones de autocopiativo con aritmética decimal. Todas coincidieron con los valores visibles de la fuente. La tabla de sobres se comprobó por normalización estructural, no por fórmula, porque ofrece importes directos.

## Siguiente bloque recomendado

Diseñar la migración mínima de backend para catálogos, versiones, filas y auditoría, con PostgreSQL/SQLite y aislamiento tenant. Ese diseño debe revisarse antes de generar o ejecutar cualquier migración.
