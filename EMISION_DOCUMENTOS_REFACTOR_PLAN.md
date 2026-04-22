# Plan de refactor — Módulo Emisión de Documentos Comerciales

> Cubre Cotizaciones, Boletas, Facturas, Notas Crédito/Débito, Bajas y Guías de Remisión. Auditoría hecha sobre el código real en `frontend/src/pages/`.

---

## Objetivos

1. Eliminar la confusión del tipo de documento creado (identidad inconfundible).
2. Convertir cliente y producto en comboboxes reales con búsqueda tipeable.
3. Validaciones in-line y prevención de emisiones erradas.
4. Total siempre visible y pegado al CTA Emitir.
5. Confirmación obligatoria en toda acción irreversible.
6. Adaptación dinámica del formulario al tipo de doc.
7. Listados unificados con filtros y acciones contextuales.
8. Navegación con teclado fluida.

---

## Fase 0 — Componentes base nuevos

### 0.1 `<DocumentTypeBadge tipo />` y `<DocumentTypeSwitcher />`
- Visualizan el tipo de doc (FACTURA/BOLETA/COTIZACIÓN/GUÍA/NC/ND) con color y tono asignados.
- `Switcher` es un segmented control horizontal, prominente, que reemplaza el `CustomSelect` del campo "Tipo".
- Cambiar tipo dispara reset/migración de campos no compatibles (con confirmación si hay datos).
- Archivo nuevo: `frontend/src/components/documents/DocumentType.jsx`.

### 0.2 `<EntityCombobox />` (cliente / producto / transportista)
- Input + lista virtual con búsqueda tipeable interna.
- Acepta `renderOption(option)` para mostrar columnas (ej. `código · nombre`).
- Acepta `onCreateNew(query)` para CTA "+ Crear cliente: <query>" cuando no hay match.
- Soporta `keyboardNavigation` (Up/Down/Enter/Esc/Tab → siguiente campo).
- Archivo nuevo: `frontend/src/components/ui/EntityCombobox.jsx`.
- Reemplaza:
  - El par `<input + CustomSelect>` de cliente en [ComprobanteNuevoPage.jsx:884-899](frontend/src/pages/ComprobanteNuevoPage.jsx#L884-L899).
  - El `CustomSelect` plano de producto en [ComprobanteNuevoPage.jsx:976-981](frontend/src/pages/ComprobanteNuevoPage.jsx#L976-L981).
  - El select plano de cotización en [GuiasPage.jsx:103-111](frontend/src/pages/GuiasPage.jsx#L103-L111).

### 0.3 `<MoneyInput />`
- `<input type="text" inputMode="decimal">` con prefijo de moneda, alineación derecha estricta, `font-mono`, sin spinners nativos, parseo a número, formateo `1,234.56`.
- Reemplaza todos los `<input type="number">` de monto del módulo.
- Archivo nuevo: `frontend/src/components/ui/MoneyInput.jsx`.

### 0.4 `<FieldError />` + helper `useFieldValidation()`
- Componente que pinta error in-line bajo el input.
- Hook que recibe schema simple y devuelve `errors: { [field]: string }` reactivo al cambio.
- Sustituye los `toast('...', 'error')` de validación en [ComprobanteNuevoPage.jsx:518-544](frontend/src/pages/ComprobanteNuevoPage.jsx#L518-L544) y [NotasPage.jsx:73-74](frontend/src/pages/NotasPage.jsx#L73-L74).

### 0.5 `<ConfirmEmitDialog />`
- Modal de confirmación irreversible. Muestra: tipo de doc + serie/correlativo previsto + cliente + monto total + advertencia explícita.
- Variante `mode="emit"` (primary) y `mode="void"` (danger) — última basada en el patrón ya existente de [BajasPage.jsx:121-156](frontend/src/pages/BajasPage.jsx#L121-L156).
- Archivo nuevo: `frontend/src/components/documents/ConfirmEmitDialog.jsx`.

---

## Fase 1 — `ComprobanteNuevoPage` refactor

### 1.1 Identidad del documento
- Reemplazar [ComprobanteNuevoPage.jsx:712-717](frontend/src/pages/ComprobanteNuevoPage.jsx#L712-L717) por `<DocumentTypeSwitcher>` con opciones [Factura, Boleta]. Tabs grandes, color distintivo.
- `h1` reactivo: `Nueva ${tipo === '01' ? 'Factura' : 'Boleta'}`.
- Header gana borde-color o accent stripe del color del tipo activo.
- Eliminar el botón "Emitir" duplicado del header ([:696-700](frontend/src/pages/ComprobanteNuevoPage.jsx#L696)) — queda solo "Vista previa".

### 1.2 Bloque Cliente (sale del collapse)
- Promover el bloque "Cliente guardado" (hoy en [:864-925](frontend/src/pages/ComprobanteNuevoPage.jsx#L864) bajo collapse "Otros") al **primer** card visible del formulario.
- Reemplazar input+select por un único `<EntityCombobox kind="client">`:
  - Cada opción: `razón_social` (bold) + `tipo_doc·numero_documento` (mono, gris) + última fecha de operación (si existe).
  - Sin match → opción "+ Crear cliente: <query>" que abre modal Nuevo Cliente.
  - Selección → autocompleta los campos `razon_social/numero_documento/direccion/email/telefono` y muestra un chip-preview.
- Lookup ApísPeru por DNI/RUC se mantiene como botón atajo a la derecha del documento.
- Validaciones in-line:
  - DNI: longitud 8 numérica.
  - RUC: longitud 11 numérica + dígito verificador.
  - Para `tipo_comprobante='01'` exigir RUC.
- Eliminar el bloque collapse "Otros · Opciones" — sus campos restantes (teléfono, enviar correo) van al card principal con menos prominencia.

### 1.3 Tabla de detalle
- Reemplazar el `CustomSelect` de producto por `<EntityCombobox kind="product">` por línea, con columnas `código | nombre`.
- Aplicar `<MoneyInput>` a `precio_unitario` y al "Total" (readonly). Eliminar la columna `Cantidad` numérica nativa: usar input mono con `text-align:right` y supresión de spinners.
- Alineación estricta:
  - `Código`, `Descripción`, `UM` → izquierda.
  - `Cantidad`, `Precio`, `Descuento`, `Total` → derecha.
- `Tab` desde `precio_unitario` de la última línea + foco vacío en siguiente → `addItem()` automático.
- `Enter` en cualquier celda numérica → mismo comportamiento.
- Confirmación al importar CSV cuando ya hay líneas con descripción no vacía: "Reemplazar N líneas o agregar al final?". Implementar en [ComprobanteNuevoPage.jsx:629-666](frontend/src/pages/ComprobanteNuevoPage.jsx#L629).

### 1.4 Adaptación dinámica por tipo
Crear helper `getVisibleFields(tipo_comprobante, tipo_operacion)` que devuelve qué campos mostrar:

| Campo | Factura | Boleta | Guía |
|-------|---------|--------|------|
| Tipo operación | sí | oculto (force `0101`) | n/a |
| % Detracción | sí (si op=1001) | oculto | n/a |
| Moneda | sí | sí (default PEN, oculto en boleta consumidor) | oculto |
| Forma pago / Vencimiento | sí | sí | oculto |
| Transportista | n/a | n/a | obligatorio si modalidad=público |
| Dirección destino | n/a | n/a | obligatorio |
| Cliente sin doc | no | sí (opcional, marca "Cliente varios") | n/a |

### 1.5 Aside-summary sticky con CTA Emitir
- Volver el aside `comprobante-builder-aside` ([:1029-1079](frontend/src/pages/ComprobanteNuevoPage.jsx#L1029-L1079)) `position: sticky; top: 16px;` para que viaje con el scroll.
- El botón "Emitir ahora" ([:1057](frontend/src/pages/ComprobanteNuevoPage.jsx#L1057)) abre `<ConfirmEmitDialog>` en lugar de ejecutar directo. Solo tras confirmación se llama `handleEmit()`.
- Mostrar lista de validaciones pendientes debajo del botón cuando el formulario es inválido (en lugar de toast genérico al click).

### 1.6 Toggle "Incluye IGV"
- Cuando se conmuta y hay precios ya digitados ([:367-377](frontend/src/pages/ComprobanteNuevoPage.jsx#L367)), pedir confirmación: "Esto va a reescribir 4 precios — ¿continuar?".
- Mostrar tooltip permanente al lado del toggle: "Si está activo, los precios ingresados ya contienen IGV. Si está apagado, son sin IGV (se calcula al emitir)."

---

## Fase 2 — `NotasPage` refactor

### 2.1 Combobox de comprobante afectado enriquecido
- En [NotasPage.jsx:93-96](frontend/src/pages/NotasPage.jsx#L93-L96), reemplazar el label plano por un combobox que muestre por opción:
  - `serie-correlativo` (mono)
  - `cliente.razon_social` (bold)
  - `fecha_emision` (es-PE)
  - `total_venta` (mono, derecha)
- Búsqueda por número o cliente.
- Filtrar también por moneda y rango de fecha.

### 2.2 Modo Anula total vs Ajuste parcial
- Toggle "¿Anula totalmente la operación?" → si sí, el monto de la NC = total del afectado.
- Si no, mostrar tabla de líneas del comprobante afectado con checkboxes para seleccionar qué líneas/montos ajustar.
- Esto requiere endpoint backend que devuelva los items del comprobante afectado (verificar si ya existe en `cotizacionesSvc.get(id)`).

### 2.3 Confirmación irreversible
- Reemplazar el botón "Emitir Nota" ([:210-213](frontend/src/pages/NotasPage.jsx#L210-L213)) por uno que abra `<ConfirmEmitDialog>` con:
  - Tipo: "Nota de Crédito" / "Nota de Débito"
  - Comprobante afectado
  - Monto a ajustar
  - Advertencia: "La nota se enviará a SUNAT y consumirá un correlativo. No se puede anular una nota."

### 2.4 Validaciones in-line
- "Comprobante afectado" requerido → mensaje bajo el combobox, no toast ([:73](frontend/src/pages/NotasPage.jsx#L73)).
- Idem motivo y descripción.

---

## Fase 3 — Listados Facturas / Boletas / Notas → componente unificado

### 3.1 Crear `<DocumentList tipo>` reutilizable
- Archivo nuevo: `frontend/src/components/documents/DocumentList.jsx`.
- Props: `tipo` (`'01'|'03'|'07'|'08'`), `endpoint`, `title`, `subtitle`.
- Internamente: filtros (rango fecha, cliente, serie, correlativo, estado, moneda), búsqueda, paginación virtual, acciones por fila contextuales.
- **Eliminar** [FacturasPage.jsx](frontend/src/pages/FacturasPage.jsx) y [BoletasPage.jsx](frontend/src/pages/BoletasPage.jsx) duplicados — ambos pasan a ser:
  ```jsx
  export default () => <DocumentList tipo="01" title="Facturas emitidas" />;
  ```

### 3.2 Acciones contextuales por fila
| Acción | Condición | Endpoint |
|--------|-----------|----------|
| Ver detalle | siempre | `/cotizaciones/:id` |
| Descargar PDF | `sunat_pdf_url` existe | `sunat_pdf_url` |
| Compartir (link público) | siempre | `cotizacionesSvc.share` |
| Enviar WhatsApp | cliente.whatsapp existe | `wa.me` con texto |
| Enviar correo | cliente.email existe | `mailto:` |
| Emitir Nota Crédito | estado `facturada` | abre modal de [NotasPage.jsx](frontend/src/pages/NotasPage.jsx) prefilled |
| Emitir Nota Débito | estado `facturada` | idem |
| Dar de baja | estado `facturada` | abre modal de [BajasPage.jsx](frontend/src/pages/BajasPage.jsx) prefilled |

### 3.3 Estado SUNAT confiable
- Reemplazar el `estadoBadge()` de [FacturasPage.jsx:10-15](frontend/src/pages/FacturasPage.jsx#L10-L15) por la función `getSunatStatus()` ya existente en [CotizacionesPage.jsx:66-72](frontend/src/pages/CotizacionesPage.jsx#L66-L72), que considera `sunat_xml_url` además de `sunat_error`. Promover esa función a `frontend/src/lib/utils/documentStatus.js` y reutilizar.

---

## Fase 4 — `GuiasPage` refactor

### 4.1 Combobox de cliente y transportista
- Hoy ([GuiasPage.jsx:103-111](frontend/src/pages/GuiasPage.jsx#L103-L111)) solo se vincula a una cotización existente. Añadir `<EntityCombobox kind="client">` para guías sin cotización previa.
- Añadir bloque transportista obligatorio cuando `modalidad_traslado='01'` (público): RUC transportista + nombre + placa vehículo + licencia conductor.

### 4.2 Botón "Buscar ubigeo" funcional
- Hoy en [GuiasPage.jsx:143,163](frontend/src/pages/GuiasPage.jsx#L143) son dead buttons. Implementar modal con buscador de ubigeo (datos cargados de un JSON `peru-ubigeos.json` en `frontend/public/`).

### 4.3 Reorganización por tabs en el modal
- Tabs: `[General] [Origen/Destino] [Bienes] [Transportista]`.
- Validar tab por tab antes de habilitar "Emitir".
- Mover el modal de form a página propia `/guias/nueva` por la complejidad creciente.

### 4.4 Acciones por fila
- Hoy solo hay "Ver" ([:362-367](frontend/src/pages/GuiasPage.jsx#L362-L367)). Añadir: PDF SUNAT, anular guía, reemitir.

---

## Fase 5 — Refactor cross-cutting

### 5.1 Promover utilitarios duplicados
- `getSunatStatus`, `formatCurrency`, `addDays`, `paymentDays`, `inputDateToday` están duplicados en `ComprobanteNuevoPage.jsx`, `CotizacionesPage.jsx`, `BajasPage.jsx`, `NotasPage.jsx`.
- Centralizar en `frontend/src/lib/utils/documents.js`.

### 5.2 Hook `useDocumentForm()`
- Encapsula el state-machine del formulario de emisión (cliente, items, totales, validación, payload de envío).
- Reutilizable entre Cotización y Comprobante para evitar la divergencia que ya empieza a notarse.

### 5.3 Tests E2E (Playwright)
- Suite: `frontend/tests/emision/`.
- Casos:
  - Crear factura → Tab navega cantidad → concepto → precio → nueva línea automática.
  - Emitir factura sin RUC → error in-line, botón Emitir deshabilitado.
  - Emitir factura → confirmación → éxito → navega a detalle.
  - Importar CSV con líneas existentes → confirma reemplazo.
  - Anular factura → confirmación irreversible → estado actualizado.
  - Crear nota de crédito desde listado de Facturas (acción contextual).

---

## Orden de ejecución recomendado

1. **Fase 0** (componentes base) — bloquea todo lo demás.
2. **Fase 1** (`ComprobanteNuevoPage`) — es el flujo crítico y más visible.
3. **Fase 3** (listados unificados) — paralelizable con Fase 2 si se asignan dos pares.
4. **Fase 2** (`NotasPage`) — depende de `ConfirmEmitDialog` y `EntityCombobox`.
5. **Fase 4** (`GuiasPage`) — la más independiente, puede ir al final.
6. **Fase 5** (cleanup + tests E2E) — al cerrar el ciclo.

Build verificable después de cada fase con `npm run build` y smoke manual del flujo correspondiente.

---

## Criterios de "listo"

- Crear factura en < 30s para un cliente recurrente con 3 líneas (medido).
- Tab navega el flujo completo cantidad → concepto → precio → nueva línea sin tocar mouse.
- Imposible emitir comprobante con monto cero, sin RUC válido (Factura), o sin descripción de línea.
- Emitir, anular y emitir nota requieren confirmación explícita.
- Listados de Facturas/Boletas comparten 100% del código.
- Tipo de doc visible en `h1` y header coloreado — no se puede confundir Factura con Boleta a primera vista.
- Total siempre visible junto al CTA Emitir mientras se hace scroll.
- 0 toasts genéricos para validaciones de campo.
- Suite Playwright pasa al 100%.
