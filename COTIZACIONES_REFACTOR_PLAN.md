# Plan de Refactor — Sección Cotizaciones (frontend)

> Alcance: archivo [frontend/src/pages/CotizacionesPage.jsx](frontend/src/pages/CotizacionesPage.jsx).
> Objetivo: (1) eliminar botones muertos y redundantes, (2) alinear los campos del UI con lo que realmente necesita la API de facturación/boleta, (3) reorganizar la vista en dos flujos claros: **crear** e **historial**.
> Referencias clave leídas antes de escribir este plan:
> - Schema [backend/schemas/cotizaciones.py](backend/schemas/cotizaciones.py) (CotizacionCreate, FacturarPayload, NotaCreate, AnulacionCreate)
> - Modelo [backend/models/cotizaciones.py](backend/models/cotizaciones.py) (totales, detracción, anticipos, notas)
> - Servicio [backend/services/facturacion_service.py](backend/services/facturacion_service.py) (payload ApísPeru, `_build_payment_terms`, `_aplicar_detraccion`)
> - Router [backend/routers/facturacion.py](backend/routers/facturacion.py) (`/cotizaciones/{id}/facturar`, `/notas/emitir`, `/bajas/anular`)
> - Doc [APISPERU_VALIDACION_DOCUMENTOS.md](APISPERU_VALIDACION_DOCUMENTOS.md) (campos mínimos por tipo de documento)

---

## 1. Diagnóstico del estado actual

### 1.1 Confusión conceptual del flujo

El UI mezcla dos pasos que en el backend son **secuenciales**:

1. **Crear cotización comercial** → `POST /cotizaciones/` (siempre `document_kind=quotation`, serie `COT`).
2. **Emitir fiscal desde cotización** → `POST /cotizaciones/{id}/facturar` con `FacturarPayload` (genera F001 / B001, contacta ApísPeru).

En el form actual, el selector `Tipo comprobante` ofrece `00 / 01 / 03` durante la creación y el botón dice *"Emitir Comprobante"*. Pero la llamada real solo crea la cotización — `tipo_comprobante` en `CotizacionCreate` es solo una **intención**; no dispara emisión SUNAT. El usuario cree que emitió, pero el documento sigue como cotización comercial.

**Evidencia en el código**:
- [CotizacionesPage.jsx:290-293](frontend/src/pages/CotizacionesPage.jsx#L290-L293) — el submit solo llama a `svc.create(data)` y nunca a `/cotizaciones/{id}/facturar`.
- [CotizacionesPage.jsx:342-354](frontend/src/pages/CotizacionesPage.jsx#L342-L354) — `handleSave` solo invoca `create`.

### 1.2 Botones redundantes / muertos

| Ubicación | Problema |
|---|---|
| Header `Ver Historial` + `NUEVA COTIZACIÓN` ([L373-387](frontend/src/pages/CotizacionesPage.jsx#L373-L387)) | Son dos botones que hacen de switcher. El segundo no tiene sentido cuando `view === 'create'` (ya estás creando). Y el form visible repite el mismo título `"Nueva Cotización"`. |
| `+ Nuevo Cliente` ([L110-112](frontend/src/pages/CotizacionesPage.jsx#L110-L112)) | No tiene `onClick`. Botón muerto. |
| `Anular Documento` ([L402-405](frontend/src/pages/CotizacionesPage.jsx#L402-L405)) | Sin `onClick`. Existe endpoint `/bajas/anular`. |
| `Nota de Crédito` / `Nota de Débito` ([L407-414](frontend/src/pages/CotizacionesPage.jsx#L407-L414)) | Sin `onClick`. Existe endpoint `/notas/emitir`. |
| Acciones de fila: Imprimir, PDF, XML, WhatsApp ([L587-598](frontend/src/pages/CotizacionesPage.jsx#L587-L598)) | Ninguna tiene `onClick`. Los URL ya existen en el modelo (`sunat_pdf_url`, `sunat_xml_url`, `sunat_cdr_url`) y hay `comunicacion_service.generar_link_whatsapp`. |
| Estado SUNAT hardcodeado "Aceptado" ([L580-583](frontend/src/pages/CotizacionesPage.jsx#L580-L583)) | Todas las filas se pintan como aceptadas aunque el documento pueda estar con `sunat_error`, pendiente, o ser una cotización que no emite. |
| `Entrega` con reloj amarillo fijo ([L574-578](frontend/src/pages/CotizacionesPage.jsx#L574-L578)) | Decorativo, sin dato real. |
| `MODO PRODUCCIÓN` ([L415-420](frontend/src/pages/CotizacionesPage.jsx#L415-L420)) | Hardcodeado; no refleja `ENVIRONMENT`. |
| Header `TC SUNAT compra/venta` y `SUNAT SYNC` | Visibles en el screenshot, hardcodeados (3.429 / 3.436). Ya existe `GET /sunat/exchange-rate` con caché 30 min. |

### 1.3 Campos que la API de facturación acepta y el UI no captura

| Campo | Tipo | Schema/Modelo | Impacto si falta |
|---|---|---|---|
| `fecha_vencimiento` | datetime | `CotizacionCreate.fecha_vencimiento` | Necesario para `formaPago.Credito` y `cuotas` en el payload ApísPeru ([facturacion_service.py:442-457](backend/services/facturacion_service.py#L442-L457)). Sin esto, toda factura sale como "Contado". |
| `condicion_pago` | str (`contado` / `credito_7/15/30/60`) | `CotizacionCreate.condicion_pago` | Determina `formaPago.tipo` en ApísPeru. Si se omite, siempre es Contado. |
| `observaciones` | str | `CotizacionCreate.observaciones` | Va como `observacion` en el payload de factura/boleta. |
| `unidad_medida` por item | str (NIU, ZZ, KGM, H87, BG...) | `CotizacionItemCreate.unidad_medida` | Va como `unidad` en `details[]`. Actualmente fuerza NIU para todo, rompe en servicios (`ZZ`). |
| `tipo_afectacion_igv` por item | str (10 grav, 20 exo, 30 ina, 40 exp) | `CotizacionItemCreate.tipo_afectacion_igv` | Si hay ítems exonerados el total_exonerada queda mal y el backend recalcula `porcentajeIgv=18` a todo. |
| Validación cliente según tipo comprobante | — | ApísPeru exige RUC para factura, DNI/RUC para boleta | Sin validar, el payload sale y ApísPeru devuelve 400 tarde. |

### 1.4 Cálculos incorrectos en el listado histórico

```jsx
// CotizacionesPage.jsx:566-569
{fmt(item.total_gravada || (item.total_venta / 1.18))}   // Subtotal
{fmt(item.total_igv || (item.total_venta - (item.total_venta / 1.18)))}  // IGV
```

- El backend ya devuelve `total_gravada`, `total_igv`, `total_exonerada`, `total_inafecta` por separado.
- El fallback `total_venta / 1.18` asume 18% sobre todo → incorrecto cuando hay líneas exoneradas/inafectas.
- Solución: consumir directamente los campos del backend.

### 1.5 Resumen de deuda

- 8 botones sin handler.
- 3 indicadores hardcodeados (estado SUNAT, modo producción, TC SUNAT).
- 6 campos del schema no expuestos (fecha_vencimiento, condición pago, observaciones, unidad, afectación IGV, validación cliente).
- 1 confusión de flujo (crear ≠ emitir).

---

## 2. Nueva arquitectura de la vista

Divido `CotizacionesPage.jsx` en **tres tabs** dentro del mismo page-shell. Esto reemplaza el switcher `create / history` por una navegación más explícita.

```
┌──────────────────────────────────────────────────────────┐
│  Cotizaciones                                            │
│  [Nueva cotización] [Historial] [Emitidas SUNAT]         │
├──────────────────────────────────────────────────────────┤
│  (contenido de la tab activa)                            │
└──────────────────────────────────────────────────────────┘
```

- **Nueva cotización** (`view=create`) — form embedded, flujo limpio de 1 paso.
- **Historial** (`view=history`) — todas las cotizaciones comerciales (`document_kind=quotation`, serie `COT`). Desde acá se emite factura/boleta.
- **Emitidas SUNAT** (`view=fiscal`) — documentos fiscales (`document_kind=fiscal_document`). Acá viven las acciones de anulación y notas.

Separar `historial` de `emitidas` elimina la necesidad de mostrar `tipo_comprobante` mezclado y simplifica filtros.

### 2.1 Tab "Nueva cotización" — form rediseñado

**Orden propuesto** (top-down):

1. **Sección Cliente y fechas** (compacta, 1 fila en desktop):
   - Cliente (autocompletar existente) + botón **+ Nuevo cliente** funcional (abre Modal con `ClienteCreate`).
   - Moneda (PEN/USD).
   - Fecha de emisión (read-only, hoy).
   - Fecha de vencimiento (opcional, se activa al elegir "Crédito").
   - Condición de pago: `Contado | Crédito 7 | 15 | 30 | 60 días` (auto-calcula fecha_vencimiento).

2. **Sección líneas** (el spreadsheet actual, mejorado):
   - Columnas: Producto · Descripción · Cantidad · Unidad · Afectación IGV · P. Unit. (incl. IGV) · Total.
   - `Unidad` y `Afectación IGV` ocultos por defecto detrás de un toggle **"Avanzado"** (para los usuarios que no necesitan el detalle SUNAT no hay ruido).
   - Por defecto `NIU` + `10` (Gravado), igual que el backend.
   - Presets rápidos: "Servicio" → `ZZ` + `10`; "Producto" → `NIU` + `10`; "Exonerado" → `ZZ` + `20`.

3. **Sección observaciones / notas internas**:
   - Textarea `observaciones` (se incluye en el PDF y en el XML).

4. **Panel de totales** (lateral o inferior, sticky):
   - Subtotal gravado · Subtotal exonerado · Subtotal inafecto · IGV · **Total**.
   - Detalle dinámico según `tipo_afectacion_igv` de cada línea.

5. **Footer de acciones**:
   - **Único botón primario**: `Guardar cotización`. Un solo paso, nombre claro.
   - Secundario: `Limpiar formulario`.

**Eliminar del form de creación**:
- Selector `Tipo comprobante` (00 / 01 / 03). Ya no tiene sentido mezclarlo con la creación: la emisión fiscal es un **segundo paso** desde el historial (botón "Facturar" / "Emitir boleta" por fila).

### 2.2 Tab "Historial" (cotizaciones comerciales)

- Tabla con: F. emisión, N° interno (`internal_order_number`), Cliente, Moneda, Total, Saldo pendiente, Estado pago (pagado / parcial / vencido / pendiente), Estado emisión (no emitida / emitida / anulada).
- Acciones por fila (solo las que tienen backend funcionando):
  - 👁 **Ver detalle** (ruta existente `/cotizaciones/:id`).
  - 🧾 **Emitir factura** → modal compacto con selector Factura/Boleta + serie override opcional, llama `POST /cotizaciones/{id}/facturar` con `FacturarPayload`.
  - 📄 **Descargar PDF cotización** (solo si hay `sunat_pdf_url` o endpoint local de PDF).
  - 💬 **WhatsApp** → usa `comunicacion_service.generar_link_whatsapp` (actualmente solo backend; exponer endpoint o replicar la lógica en frontend contra el teléfono del cliente).
- Una vez emitida, la fila muestra link al documento fiscal (`linked_fiscal_document_number`) y desactiva "Emitir".

### 2.3 Tab "Emitidas SUNAT" (documentos fiscales)

- Filtros: DNI/RUC · razón social · Tipo (Factura/Boleta/NC/ND) · Serie · Rango fechas · Moneda · Estado SUNAT.
- Columnas: F. emisión · Tipo (FACTURA/BOLETA/NC/ND) · Serie-Núm · Cliente · Moneda · Subtotal · IGV · Total · Estado SUNAT real · Acciones.
- **Estado SUNAT real** por fila:
  - Aceptado — si tiene `sunat_xml_url` y no hay `sunat_error`.
  - Pendiente — si es `async` y aún no llega CDR.
  - Rechazado — si hay `sunat_error`.
  - Anulado — si `estado === 'anulada'`.
- Acciones por fila (conectadas):
  - 🖨 **Imprimir PDF** — abrir `sunat_pdf_url`.
  - 📥 **Descargar XML** — abrir `sunat_xml_url`.
  - 📥 **Descargar CDR** — abrir `sunat_cdr_url`.
  - 💬 **WhatsApp** — link a cliente.
  - 📝 **Nota de crédito / débito** — modal con `NotaCreate` (motivo código + descripción, `comprobante_afectado_id`).
  - 🗑 **Anular** — modal con `AnulacionCreate` (motivo).

Las acciones "Anular Documento / Nota de Crédito / Nota de Débito" del header del historial actual **desaparecen**; se vuelven acciones por fila contextuales.

---

## 3. Entregables (tareas concretas)

Todas sobre [frontend/src/pages/CotizacionesPage.jsx](frontend/src/pages/CotizacionesPage.jsx) salvo indicación contraria.

### 3.1 Limpieza

- [ ] Quitar el selector `Tipo comprobante` del form de creación.
- [ ] Renombrar el único botón de submit a `Guardar cotización` (sin lógica condicional por tipo).
- [ ] Quitar del header el botón redundante `NUEVA COTIZACIÓN` cuando `view === 'create'`; dejar solo el breadcrumb/título dinámico o un tab-bar.
- [ ] Reemplazar `Ver Historial / NUEVA COTIZACIÓN` por tab-bar de 3 tabs (Nueva · Historial · Emitidas).
- [ ] Eliminar de la vista historial el bloque `Anular Documento | Nota de Crédito | Nota de Débito | MODO PRODUCCIÓN`.
- [ ] Eliminar `TC SUNAT compra/venta` y `SUNAT SYNC` del header global si son hardcoded; si se quieren, mover a un componente reutilizable que consuma `GET /sunat/exchange-rate`.

### 3.2 Nuevos campos en el form

- [ ] Campo `fecha_vencimiento` (date input, visible solo si condicion_pago ≠ "contado").
- [ ] Campo `condicion_pago` con valores alineados a [CONDICION_PAGO_VALORES](backend/schemas/clientes.py#L7).
- [ ] Campo `observaciones` (textarea, debajo de líneas).
- [ ] Por línea: select `unidad_medida` (NIU, ZZ, KGM, H87, BG, ...).
- [ ] Por línea: select `tipo_afectacion_igv` (10, 20, 30, 40).
- [ ] Toggle "Avanzado" que muestra/oculta las dos columnas anteriores.
- [ ] Panel de totales con breakdown: gravado / exonerado / inafecto / IGV / total.

### 3.3 Validaciones de emisión

Ejecutar al abrir el modal **Emitir factura/boleta** (no al crear cotización):

- [ ] Si `tipo=01` (Factura) → exigir que el cliente tenga `tipo_documento='RUC'` y 11 dígitos. Si es DNI, mostrar CTA "Cambiar cliente" o "Actualizar documento a RUC".
- [ ] Si `tipo=03` (Boleta) → permitir DNI o RUC.
- [ ] Pre-chequeo visual de totales (si total == 0 bloquear).

El backend ya valida vía `_validar_pre_emision` ([facturacion.py:104](backend/routers/facturacion.py#L104)), pero el pre-check en UI ahorra un round-trip.

### 3.4 Conectar botones muertos

- [ ] `+ Nuevo cliente` → abrir Modal reusable con `ClienteCreate`, al guardar refrescar dropdown y auto-seleccionar.
- [ ] Acción fila `Descargar PDF` → `window.open(item.sunat_pdf_url)`.
- [ ] Acción fila `Descargar XML` → `window.open(item.sunat_xml_url)`.
- [ ] Acción fila `CDR` → `window.open(item.sunat_cdr_url)` (solo en tab Emitidas).
- [ ] Acción fila `WhatsApp` → abrir `https://wa.me/{telefono}?text={...}` en nueva pestaña. Idealmente exponer endpoint `GET /cotizaciones/{id}/whatsapp-link` que llame a [comunicacion_service.generar_link_whatsapp](backend/services/comunicacion_service.py) para evitar duplicar lógica.
- [ ] Acción fila `Nota de crédito/débito` → modal con selector `cod_motivo` (catálogo SUNAT 09) + textarea `descripcion_motivo` + submit a `POST /notas/emitir` con `NotaCreate`.
- [ ] Acción fila `Anular` → modal simple con `motivo` + submit a `POST /bajas/anular` con `AnulacionCreate`.

### 3.5 Cálculos del listado

- [ ] Sustituir `item.total_gravada || (item.total_venta / 1.18)` por `item.total_gravada` directo (el backend lo entrega).
- [ ] Idem para `total_igv`.
- [ ] Mostrar `total_exonerada` / `total_inafecta` solo si son > 0 (fila expandible o tooltip).

### 3.6 Estado SUNAT real

- [ ] Reemplazar la etiqueta "Aceptado" hardcoded por un helper `getSunatStatus(item)`:
  ```js
  if (item.estado === 'anulada') return { label: 'ANULADO', tone: 'red' };
  if (item.sunat_error) return { label: 'RECHAZADO', tone: 'red', tooltip: item.sunat_error };
  if (item.sunat_xml_url) return { label: 'ACEPTADO', tone: 'green' };
  if (item.document_kind === 'fiscal_document') return { label: 'PENDIENTE', tone: 'amber' };
  return { label: '—', tone: 'slate' };
  ```
- [ ] Eliminar la columna `Entrega` con reloj fijo hasta que exista un estado real de entrega en el modelo (no existe hoy).

---

## 4. Orden de implementación sugerido

Cada fase deja la app funcional; se puede mergear en PRs separados.

1. **Fase 1 — Limpieza visual** (bajo riesgo, alto impacto percibido): 3.1 + 3.5 + 3.6. Quita botones muertos y cálculos frágiles.
2. **Fase 2 — Separación crear / emitir**: tabs + modal "Emitir factura/boleta" + validación cliente (3.3 + parte de 3.4). Elimina la confusión de flujo.
3. **Fase 3 — Campos fiscales completos**: 3.2. Expone fecha_vencimiento, condicion_pago, observaciones, unidad y afectación.
4. **Fase 4 — Acciones sobre documentos emitidos**: notas, anulación, descargas (resto de 3.4).

---

## 5. Fuera de alcance (no tocar en este refactor)

- El modelo de datos (`Cotizacion`, `CotizacionItem`) ya soporta todo lo necesario — no se requiere migración.
- El `document_kind` y la relación `source_quote_id ↔ derived_documents` ya funciona y no se altera.
- La emisión directa a SUNAT (sin ApísPeru) queda igual; el frontend sigue llamando al mismo endpoint `/facturar`.
- Frozen: MRP, AI-suggestions, multi-plan subscriptions — no tocar ([backend/FROZEN_DOMAINS.md](backend/FROZEN_DOMAINS.md)).

---

## 6. Checklist rápida para QA

Post-implementación, verificar en dev:

- [ ] Crear cotización contado → sale sin fecha_vencimiento.
- [ ] Crear cotización crédito 30 → fecha_vencimiento se auto-calcula y viaja al backend.
- [ ] Agregar línea exonerada (afectación 20) → totales muestran `total_exonerada` separado.
- [ ] Desde historial, emitir Factura con cliente DNI → UI bloquea antes de llamar al backend.
- [ ] Desde historial, emitir Factura con cliente RUC → `/cotizaciones/{id}/facturar` responde OK y aparece en tab Emitidas con estado Aceptado.
- [ ] En tab Emitidas, descargar PDF/XML/CDR abre el archivo real del bucket.
- [ ] Anular un documento emitido → estado pasa a ANULADO y desaparece de "cobranzas".
- [ ] Nota de crédito sobre factura emitida → aparece nueva fila tipo NC con referencia visible.
