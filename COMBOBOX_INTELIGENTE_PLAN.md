# Plan — Comboboxes inteligentes para clientes y productos

> Aplicación: cotizaciones, facturas, boletas y notas.
> Status: ClientCombobox v3 ya implementado en `CotizacionesPage`. Falta replicar patrón en producto, automatizar persistencia y propagar a `ComprobanteNuevoPage`.

---

## 1. Objetivo

Permitir al usuario **buscar, autocompletar, editar y crear** clientes y productos sin salir del formulario, y que la **base de datos se sincronice automáticamente** al confirmar la operación (Guardar cotización / Emitir comprobante), respetando los **campos obligatorios de ApísPeru / SUNAT** cuando el documento es fiscal.

### UX clave
- Cliente y producto: campos integrados en el formulario, no botones que abren modales.
- Búsqueda en tiempo real escribiendo en cualquiera de los campos clave (RUC o nombre / código o nombre).
- Edición inline de campos no críticos (correo, teléfono, dirección, precio).
- Persistencia diferida: la BD se actualiza al confirmar la cotización / emisión, no por cada tecla.

---

## 2. UX Smells actuales (producto)

| # | Smell | Dónde |
|---|---|---|
| P1 | `ProductCombobox` aún es un solo trigger con dropdown — no permite buscar por código y nombre en columnas separadas | `frontend/src/components/ui/ProductCombobox.jsx` |
| P2 | No hay manera de **crear un producto nuevo** desde la línea de la cotización; solo "usar descripción libre" (que pierde reutilización) | mismo archivo |
| P3 | El **precio** y la **descripción** no son editables tras seleccionar (se sobreescriben con los del catálogo) — bloquea casos legítimos como precio especial por cliente | `CotizacionesPage` líneas 581-596 |
| P4 | No existe **generador de código** automático cuando el usuario quiere registrar un producto — debe pensarlo manualmente | catálogo de productos en general |
| P5 | Las ediciones que hace el usuario en una línea **no se reflejan en el catálogo** — quedan solo en la cotización | flujo completo |
| P6 | El mismo flujo se repite tres veces (cotizaciones, comprobantes, guías) con código duplicado | `CotizacionesPage`, `ComprobanteNuevoPage`, `GuiasPage` |

---

## 3. UX Decisions

### D1 — Patrón "spreadsheet de línea" para producto
Cada línea del detalle expone tres campos visibles e independientes:

| Columna | Comportamiento |
|---|---|
| **Código** | Input + dropdown que filtra catálogo por `codigo_interno`. Al seleccionar autocompleta nombre/precio/unidad/IGV. |
| **Nombre / Descripción** | Input + dropdown que filtra catálogo por `nombre`. Misma capacidad de selección. |
| **Cant.** / **P. Unit.** / **Total** | Editables siempre, también cuando hay producto seleccionado (overridable). |

Si el usuario escribe en cualquiera de los dos primeros y **no hay coincidencia**, el sistema muestra un indicador inline "Producto nuevo — se registrará al guardar" + botón opcional **"Generar código"**.

### D2 — Generador de código de producto
- Backend nuevo: `GET /productos/codigo-sugerido` → devuelve `PROD-<6 chars hex>` único en el tenant.
- Frontend: botón ⟳ junto al campo Código cuando está vacío y se escribió un nombre.
- Validación: si el usuario escribe un código que ya existe → tooltip "Este código ya está registrado para «X», ¿deseas usarlo?".

### D3 — Persistencia diferida y "upsert" al confirmar
El frontend mantiene el estado local de cada línea con un `_dirty` flag (cliente, items). Al pulsar **Guardar cotización** / **Emitir** se ejecuta una secuencia orquestada en el frontend:

```
1. clientUpsert()    → POST /clientes/ o PUT /clientes/{id}, según _dirty
2. productUpserts()  → en paralelo para cada item _dirty (POST o PUT)
3. createCotizacion()→ con cliente_id y producto_id ya resueltos
4. (opcional) emitirComprobante()
```

Razones para no exponer creación inline en el endpoint de cotización:
- Mantiene `CotizacionCreate` simple (sin payloads anidados).
- Preserva separación de responsabilidades — los CRUD de cliente/producto siguen siendo la fuente de verdad.
- Permite reusar el mismo orquestador en `ComprobanteNuevoPage`.
- Si una etapa falla (ej. cliente con RUC inválido), no se consume correlativo SUNAT.

### D4 — Edición de cliente seleccionado se traduce en `PUT`
Hoy `ClientCombobox` bloquea (readonly) los campos cuando hay cliente seleccionado. Cambio:
- Los campos **no críticos** (correo, teléfono, dirección) son **editables** aun con cliente seleccionado.
- Los campos **identitarios** (tipo_documento, número_documento, razón_social) siguen readonly — cambiarlos implicaría cambiar de cliente.
- Si el usuario edita y los valores difieren → marcar `_dirty=true`. Al guardar, dispara `PUT /clientes/{id}`.
- Indicador visual sutil debajo: "Estos cambios actualizarán al cliente «X» en el catálogo".

### D5 — Matriz de validación por tipo de documento
Antes de habilitar el botón "Emitir / Guardar", validar según el tipo:

| Documento | Cliente: tipo_documento | Cliente: número | Cliente: dirección | Cliente: razón social | Items mínimos |
|---|---|---|---|---|---|
| Cotización (00) | cualquiera | recomendado | opcional | requerido | 1 con cant/precio>0 |
| Boleta (03) | 1, 4, 7 o 0 | requerido si total > 700 PEN | opcional | requerido | 1 con afectación válida |
| Factura (01) | **6 (RUC)** | **11 dígitos** | **requerido** | **requerido** | 1 con afectación válida |
| Nota crédito/débito (07/08) | hereda del comprobante afectado | — | — | — | hereda |

Por línea (cuando es comprobante fiscal 01/03):
- `unidad_medida` requerido (NIU por defecto)
- `tipo_afectacion_igv` requerido (10 por defecto)
- `descripcion` ≥ 1 carácter
- `cantidad > 0`, `precio_unitario > 0`

Si el producto se va a crear inline para un comprobante fiscal, **se exige código** (autogenerable) para que SUNAT pueda identificarlo en el XML UBL.

### D6 — Componente compartido
Crear un único `useDocumentForm()` hook + presentational `DocumentFormShell` reutilizable por:
- `CotizacionesPage` (kind="quotation")
- `ComprobanteNuevoPage` (kind="01"|"03")

El hook centraliza:
- Estado de cliente y items (con `_dirty` flags)
- Validación por kind (tabla D5)
- Orquestador `submit()` que ejecuta upserts + creación
- Manejo de errores parcial (si falla product upsert, no crear cotización)

---

## 4. Plan por fases

### Fase 0 — Fundamentos (frontend + backend)

**Frontend** (~ 2 archivos nuevos):
1. `frontend/src/lib/utils/upsert.js` — orquestador `submitQuoteWithUpserts({ client, items, payload })` que devuelve `{ clienteId, items: [{producto_id, ...}] }` listo para enviar.
2. `frontend/src/lib/utils/validateDocument.js` — `validateForKind(kind, { client, items, total })` con la matriz D5; devuelve `{ ok, errors }`.

**Backend** (~ 1 endpoint nuevo, 0 cambios al modelo):
1. `GET /productos/codigo-sugerido` en `routers/productos.py` — devuelve `{ codigo: "PROD-AB12CD" }` único en el tenant. Implementación: random 6 hex, comprobar contra `Producto.codigo_interno` en bucle (max 5 intentos).

### Fase 1 — Reescribir `ProductCombobox` (componente standalone)

Reemplazar `frontend/src/components/ui/ProductCombobox.jsx` por una **fila de 3 inputs coordinados**: Código + Nombre + (precio se queda en su columna actual de la tabla).

API del componente:
```jsx
<ProductCombobox
  products={catalog}
  value={{ producto_id, codigo, descripcion }}
  onChange={(next) => ...}             // dispara con _dirty=true cuando hay edición libre
  onGenerateCode={async () => 'PROD-AB12CD'}
  size="cell"                           // variante compacta para spreadsheet
/>
```

Comportamiento:
- Escribir en código → dropdown filtra por `codigo_interno`.
- Escribir en nombre → dropdown filtra por `nombre`.
- Seleccionar opción → autocompleta y marca `_dirty=false` salvo que el usuario edite después.
- Sin coincidencia + nombre escrito → indicador "Nuevo — se registrará al guardar" + botón ⟳ (genera código si está vacío).
- Editar después de seleccionar → `_dirty=true`, marca visual (•).

### Fase 2 — Integrar en `CotizacionesPage` (sin cambiar API del backend)

Cambios en `NuevaCotizacionForm`:
1. Reemplazar render de `<ProductCombobox>` actual.
2. Tracking por línea: `_dirty`, `_isNew`, `_codigo`, `_nombre`, `_precio`.
3. `handleSubmit()` ahora llama:
   ```js
   const { cliente_id, items } = await submitQuoteWithUpserts({
     client: clientForm,    // del ClientCombobox
     items: lineItems,
     productosSvc,
     clientesSvc,
   });
   await svc.create({ cliente_id, items, ... });
   ```
4. ClientCombobox: aplicar D4 (correo/tel/dirección editables aun con cliente seleccionado, marcando `_dirty`).

### Fase 3 — Aplicar a `ComprobanteNuevoPage` (facturas / boletas)

1. Sustituir el bloque de cliente actual por `<ClientCombobox>` con prop `kind={tipo}` que ajusta:
   - tipo 01 (factura) → fuerza `tipo_documento='6'`, exige RUC y dirección.
   - tipo 03 (boleta) → permite varios tipos, dirección opcional.
2. Sustituir el bloque de producto/item por el nuevo `<ProductCombobox size="cell">` y la misma lógica de upsert.
3. Antes de pulsar **Emitir**, ejecutar `validateForKind(tipo, ...)`. Si falla, abrir el panel de errores existente (ya implementado en fase anterior).
4. Confirmar con `ConfirmEmitDialog` (ya existente) y luego `submitQuoteWithUpserts(...)` + `emitirComprobante(...)`.

Nota crítica de seguridad SUNAT: el orquestador debe **completar todos los upserts antes** de invocar `emitirComprobante`. Si falla la emisión, los productos/clientes ya quedan en BD (es comportamiento aceptable y deseable).

### Fase 4 — Plantilla compartida `useDocumentForm`

Mover la lógica común a un hook:
- `useDocumentForm({ kind, initial, productos, clientes })`
- Devuelve: `{ client, setClientField, items, setItem, addItem, removeItem, errors, isValid, submit }`
- Internamente integra orquestador + validación.

Refactor de `CotizacionesPage` y `ComprobanteNuevoPage` para consumirlo.

### Fase 5 — Pruebas y QA manual

Casos a verificar:
1. Crear cotización con cliente nuevo + 2 productos nuevos → 1 POST cliente + 2 POST productos + 1 POST cotización.
2. Crear cotización con cliente existente (modificando teléfono) + producto existente (modificando precio) → 1 PUT cliente + 1 PUT producto + 1 POST cotización.
3. Emitir factura (01) sin RUC → bloqueo en frontend con mensaje claro, no se llega a SUNAT.
4. Emitir factura (01) con producto nuevo sin código → autogeneración antes del POST productos.
5. Falla en POST productos a mitad de camino → no se crea la cotización; toast "Error al guardar producto X, intenta de nuevo".
6. Edición de un dato readonly (RUC) → bloqueado, requiere "Cambiar cliente" (X).

---

## 5. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Orquestación parcial deja datos huérfanos (cliente creado pero cotización falla) | Aceptable — el cliente queda en catálogo. Documentar en el toast de error. |
| Doble POST cliente si el usuario hace doble clic | Deshabilitar botón submit + flag `submitting` en el orquestador (ya hay precedente). |
| Conflicto de código de producto entre dos usuarios concurrentes | Backend reintenta hasta 5 veces con random distinto; en colisión final → 409. Frontend muestra "Genera otro código". |
| Cambios en cliente afectan facturas históricas (referencia por id, no copia) | **Sí afecta.** Mostrar tooltip "Esto actualizará al cliente para futuros documentos. Los emitidos no cambian." |
| Validación SUNAT rompe en producción por reglas no contempladas | La matriz D5 es la fuente única. Cualquier regla nueva se documenta ahí, no se duplica en componentes. |
| Coupling entre `useDocumentForm` y los dos pages → cambios costosos | Tipar bien la API del hook desde el inicio; evitar fugas de detalles del kind hacia los componentes. |

---

## 6. Criterios de aceptación

- [ ] En cotización: usuario puede buscar producto por código **o** nombre con dropdown en cada campo.
- [ ] En cotización: usuario puede crear producto nuevo escribiendo nombre + (opcional) generar código.
- [ ] En cotización: al guardar, productos nuevos quedan en `/productos/`, ediciones de existentes se aplican (PUT).
- [ ] En cotización: cambios de teléfono/correo/dirección de cliente existente se persisten al guardar.
- [ ] En factura/boleta: misma UX, con validación de RUC/dirección obligatorios para tipo 01.
- [ ] Sin regresión: cotizaciones simples (cliente y producto existentes, sin edición) siguen funcionando con el mismo número de requests.
- [ ] El backend solo expone un endpoint nuevo (`/productos/codigo-sugerido`); todo el resto es coordinación frontend.

---

## 7. Estimación de esfuerzo

| Fase | LoC frontend | LoC backend | Riesgo |
|---|---|---|---|
| 0 — Fundamentos | ~150 | ~25 | bajo |
| 1 — ProductCombobox | ~280 | 0 | medio |
| 2 — Cotizaciones integration | ~120 (delta) | 0 | medio |
| 3 — ComprobanteNuevoPage | ~180 (delta) | 0 | medio-alto (SUNAT) |
| 4 — Hook compartido | ~200 (refactor) | 0 | medio |
| 5 — QA manual | — | — | alto si no se prueba bien |

Total estimado: ~930 LoC frontend, ~25 LoC backend, 1 endpoint nuevo.

---

## 8. Orden de ejecución recomendado

1. **Fase 0 + Fase 1** juntas (fundamentos + ProductCombobox standalone, sin tocar pages aún).
2. **Fase 2** — integrar en CotizacionesPage y validar con QA local.
3. **Fase 3** — aplicar a ComprobanteNuevoPage (alto riesgo SUNAT, hacer junto a un test real con APIsPeru staging).
4. **Fase 4** — refactor opcional si la duplicación duele; si no, dejar para después del lanzamiento.
5. **Fase 5** — pruebas manuales antes de cerrar.
