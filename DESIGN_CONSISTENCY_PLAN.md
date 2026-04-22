# Plan — Consistencia de diseño Inkora & flujo implícito de cliente

> **Estado:** propuesta — pendiente de aprobación antes de ejecutar.
> **Origen:** feedback del usuario tras testear el combobox inteligente recién entregado (4 capturas).
> **Objetivo:** que todos los formularios de cotización/comprobante respeten la línea Inkora (sin selects ni calendarios nativos del SO) y que el guardado de cliente sea **implícito** al guardar la cotización, eliminando pasos manuales.

---

## Issues reportados

| # | Issue | Archivo(s) | Síntoma |
|---|---|---|---|
| 1 | Dropdown nativo `<select>` con fondo oscuro | `ClientCombobox.jsx:273`, `DocumentList.jsx:105,122` | El selector "Tipo doc." y filtros de DocumentList muestran lista negra del SO, rompe la paleta. |
| 2 | Calendarios nativos `<input type="date">` | `CotizacionesPage.jsx:722,1273,1277,1561,1566`, `DocumentList.jsx:93,99` | Calendario del SO no respeta el diseño tipográfico mono / borde índigo. |
| 3 | Botón "+ Registrar cliente" innecesario | `ClientCombobox.jsx:391-405` | El usuario espera que el cliente se registre/actualice automáticamente al hacer "Guardar cotización". |
| 4 | Email y teléfono obligatorios | `ClientCombobox.jsx:230-232` | "A veces no se sabe" — debe ser opcional. (Backend ya los acepta `Optional`.) |
| 5 | "Buscar cliente guardado" redundante en comprobante | `ComprobanteNuevoPage.jsx:748-770` | Los inputs RUC y razón social ya hacen búsqueda en tiempo real — sobra el CustomSelect adicional. |

---

## Auditoría adicional — otras inconsistencias detectadas

Mientras buscaba los issues anteriores encontré:

- **`DocumentList.jsx`** mezcla 4 controles nativos (2 selects + 2 dates) en la barra de filtros — las facturas/boletas listadas heredan ese diseño feo.
- **`CotizacionesPage.jsx`** filtros de tabla (líneas 1273, 1277, 1561, 1566) también usan `<input type="date">`.
- **Páginas SUNAT auxiliares** (`PercepcionesPage`, `RetencionesPage`, `ResumenDiarioPage`, `ReversionesPage`) usan dates nativos. Decisión sugerida: **fuera de scope** para esta iteración (son herramientas internas de bajo tráfico) — anotar y dejar para una pasada futura.

---

## Decisiones de diseño antes de implementar

1. **Una sola fuente de cliente**: el `ClientCombobox` será el único punto de captura de cliente (en cotización **y** comprobante). Eliminamos el bloque manual + select duplicado de `ComprobanteNuevoPage`.
2. **Implícito > explícito**: el cliente se crea/actualiza dentro del orquestador `upsertCliente()` que ya existe — solo hay que dejar de exigir el click intermedio.
3. **Validación mínima**: solo `tipo_documento`, `numero_documento` y `razon_social` son requeridos. Email y teléfono → opcionales con aviso suave ("Sin correo registrado") pero no bloquean el guardado.
4. **Componentes ya disponibles** que reutilizaremos:
   - `frontend/src/components/ui/CustomSelect.jsx` — dropdown Inkora con sombra `4px 4px 0px rgba(99,102,241,0.35)`.
   - `frontend/src/components/ui/DatePicker.jsx` — calendario propio con la misma estética.

---

## Fases

### Fase 1 — `ClientCombobox` v5 (auto-save + opcionales + CustomSelect)

Archivo: `frontend/src/components/ui/ClientCombobox.jsx`

- [ ] Reemplazar el `<select>` nativo de `tipo_documento` (línea 273) por `<CustomSelect compact options={DOC_TYPES} ...>`.
- [ ] En `validate()` (líneas 226-235) eliminar las dos comprobaciones obligatorias de `email` y `telefono`. Mantener formato de email **solo si el usuario escribió algo** (`if (form.email.trim() && !regex) errs.email = ...`).
- [ ] Quitar el asterisco rojo `*` de las labels de Email y Teléfono (líneas 339, 354).
- [ ] **Eliminar** el botón "+ Registrar cliente" y el bloque envolvente `hasNewData &&` (líneas 391-405). Eliminar también `handleRegister`, `registering`, `onRegisterNew` prop, e import de `Loader2` si queda huérfano.
- [ ] Mantener `onFormChange(form, { isDirty, isNew, id })` — es la fuente de verdad para que el padre dispare `upsertCliente` al guardar.
- [ ] Sustituir el aviso "Cliente no encontrado — completa y regístralo" por algo más sutil: `"Nuevo cliente — se registrará al guardar la cotización"` (mismo estilo que badge `EDITADO`).

### Fase 2 — `CotizacionesPage` (consumir la nueva API)

Archivo: `frontend/src/pages/CotizacionesPage.jsx`

- [ ] Quitar el prop `onRegisterNew` y la función `handleClientUpdated` (ya no se invocan).
- [ ] Confirmar que `handleSubmit` ya hace `upsertCliente({ id, isNew, isDirty, form })` — agregar guard: si `isNew && !razon_social.trim()` mostrar toast "Falta nombre del cliente" en lugar del botón.
- [ ] **Reemplazar** `<input type="date">` de `fecha_vencimiento` (línea 722) por `<DatePicker value={fechaVenc} onChange={setFechaVenc} disabled={condicion === 'contado'} />`.
- [ ] **Reemplazar** los 4 `<input type="date" className="input-compact">` de los filtros (líneas 1273, 1277, 1561, 1566) por `<DatePicker compact ...>` (revisar si `DatePicker` necesita prop `compact`; si no, agregarlo en Fase 5).
- [ ] Limpiar import de `Loader2` o cualquier símbolo huérfano.

### Fase 3 — `ComprobanteNuevoPage` (unificar con ClientCombobox)

Archivo: `frontend/src/pages/ComprobanteNuevoPage.jsx`

- [ ] **Eliminar** el bloque `Buscar cliente guardado` (líneas 748-770) — el CustomSelect entero.
- [ ] **Reemplazar** el sub-formulario manual de cliente (líneas 772-824: tipo doc, número, razón social, email, teléfono, switch correo) por una sola integración del `<ClientCombobox>` ya rediseñado en Fase 1.
  - Pasar `clients={clientes}`, `value={form.cliente_id}`, `onChange={(id) => setRootField('cliente_id', id)}`, `onFormChange={handleClientFormChange}`.
  - Mantener fuera del combobox solo el switch "Enviar correo al emitir" (lógica de comprobante, no del cliente).
- [ ] Adaptar `handleEmitConfirmed` para que llame `await upsertCliente(...)` antes de armar el payload (similar a `CotizacionesPage.handleSubmit`). Ya hay scaffolding parcial — eliminar el path antiguo de `applyExistingClient` + lookup manual y dejar que el combobox lo absorba.
- [ ] Eliminar funciones huérfanas: `applyExistingClient`, `clienteOptions`, `customerDocOptions`, `setClienteField`, `handleLookupDocument` si ya no se usan tras absorber al combobox.

### Fase 4 — `DocumentList` (filtros con estilo Inkora)

Archivo: `frontend/src/components/documents/DocumentList.jsx`

- [ ] Reemplazar los 2 `<input type="date">` (líneas 93, 99) por `<DatePicker compact ...>`.
- [ ] Reemplazar los 2 `<select>` (líneas 105 "Estado", 122 "Moneda") por `<CustomSelect compact options=[...]>`.
- [ ] Quitar los styles inline de `select` que pretendían parecer Inkora (líneas 109, 126).

### Fase 5 — Pulido de `DatePicker` / `CustomSelect` para variante compacta (si hace falta)

- [ ] Verificar que `DatePicker` acepta o necesita prop `compact` para encajar en `input-compact` (height 36px). Si no, agregarlo replicando la lógica de `CustomSelect.compact`.
- [ ] Smoke visual: que los filtros nuevos no rompan el grid de la barra (gap, alineación).

### Fase 6 — Validación final

- [ ] `npm run build` limpio.
- [ ] Smoke flow:
  1. Crear cotización con **cliente nuevo** sin email ni teléfono → debe guardarse y aparecer en el catálogo de clientes con `email=null, telefono=null`.
  2. Crear cotización con cliente existente → editar email → debe actualizar el registro tras guardar (badge `EDITADO` visible).
  3. Crear comprobante (factura) usando solo el `ClientCombobox` (sin "Buscar cliente guardado").
  4. Filtrar facturas en `DocumentList` con DatePicker + CustomSelect → debe filtrar igual que antes.
  5. Filtros de cotizaciones con DatePicker → idem.
- [ ] Confirmar visualmente que **ningún** dropdown ni calendario muestra el chrome del SO.

---

## Fuera de scope (anotar para próxima iteración)

- Páginas SUNAT auxiliares (`PercepcionesPage`, `RetencionesPage`, `ResumenDiarioPage`, `ReversionesPage`) — bajo tráfico, posponer.
- Refactor de `<input className="input">` genérico a un `<TextField>` componente — es cosmética, no bloquea launch.

---

## Riesgos & rollback

- **Riesgo bajo**: cambios concentrados en UI + un orquestador que ya existe (`upsertCliente`). El backend no se toca.
- **Riesgo medio**: absorber el sub-formulario de comprobante dentro de `ClientCombobox` puede romper layouts (`comprobante-field-grid--client`). Mitigación: aplicar Fase 3 al final, después de validar Fases 1-2 en cotizaciones.
- **Rollback**: cada fase es un commit independiente y reversible con `git revert`.

---

## Solicitud de aprobación

¿Apruebas el alcance y el orden de fases? Si quieres ajustar algo (sacar la Fase 4, añadir las páginas SUNAT, posponer la integración de comprobante, etc.) dímelo antes de ejecutar.
