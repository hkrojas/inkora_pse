# Plan de rediseño — Prototipo Inkora → App actual

> Aplicar el diseño exacto del prototipo `inkora_prototipo_funcional (2).html` a la app React real, **sin emojis** (todos los emojis y glifos ASCII se reemplazan por íconos de `lucide-react`), e inferir el diseño de las secciones que el prototipo deja como placeholder (Notas Cred/Deb, Resumen diario, Bajas, Reversiones, Retenciones, Percepciones, Cobranza, Seguridad).

---

## 1. Diagnóstico rápido

### Lo que ya está alineado
- Tokens de color: `--color-primary #8DC63F`, `--color-sidebar-dark #102b16`, fondo `#eef1f4`. Coinciden con el prototipo.
- Tipografía: Plus Jakarta Sans ya cargada en `app.css`.
- Sidebar (`Sidebar.jsx`): ya usa el gradiente verde oscuro, ítems activos con barra lima, scroll interno y user-card. Solo hay que ajustar etiquetas/orden.
- Topbar (`AppLayout.jsx`): ya tiene título + subtítulo + buscador + pill SUNAT + íconos + botón "Añadir".

### Lo que hay que reescribir
- Todas las páginas usan estilos Tailwind ad-hoc; el prototipo usa **un sistema de clases reutilizable** (`panel`, `metric`, `stat`, `attention`, `module-tab`, `summary-strip`, `records-card`, `line-table`, `summary-card`, `client-row`, `settings-*`). La forma más rápida y consistente de portarlo es:
  1. Crear un CSS de componentes que **replique 1:1** las clases del prototipo en `frontend/src/styles/`.
  2. Refactorizar el JSX de cada página para usar esa misma marcación.

### Reemplazo de emojis → íconos Lucide
Los glifos del prototipo se reemplazan así (los unicode shapes `▦ ♙ ◫ ▣ ▤ ▱` de la sidebar **ya** están reemplazados por íconos Lucide en el app actual; lo que toca es eliminar los emojis del cuerpo de cada página):

| Prototipo | Lucide | Uso típico |
| --- | --- | --- |
| 💳 / 💵 | `CreditCard`, `Wallet` | Pagos, cobranzas |
| 📄 / 📋 / 🧾 | `FileText`, `Receipt` | Documentos, facturas |
| 📩 / ✉️ | `Mail`, `Send` | Correos, recordatorios |
| 📦 | `Package` | Productos, despacho |
| 🚚 | `Truck` | Guías de remisión |
| 🛡 | `ShieldCheck` | SUNAT, seguridad |
| 📅 | `CalendarDays` | Filtros de fecha |
| ☼ ◔ ▣ | `Sun`, `Moon`, `Monitor` | Selector de tema |
| ☀ 🏢 👤 🎨 | `Sun`, `Building2`, `User`, `Palette` | Mosaicos de configuración |
| 🔥 | `Flame` | Más usados |
| ✓ ⊗ ⊙ ↪ ⏱ | `CheckCircle2`, `XCircle`, `Slash`, `Send`, `Clock3` | Estados de comprobante |
| ☰ ⇩ ↗ | `Filter`, `Download`, `Upload`, `ArrowUpRight` | Toolbar |
| 👁 ✈ | `Eye`, `Send` | Vista previa, emitir |
| ＋ × ⌫ | `Plus`, `X`, `Trash2` | CRUD inline |
| ⌕ | `Search` | Búsqueda |
| ⚙ ⌘ ☾ | `Settings`, `KeyRound`, `Moon` | Sidebar (ya hecho) |

> Regla: cualquier emoji que aparezca en el prototipo se traduce a `<Icon size={14|16} />` con el color del contexto (`text-[var(--color-text-muted)]` por defecto). Nunca se inserta el carácter Unicode del emoji.

---

## 2. Arquitectura de la migración

### 2.1 Nuevo archivo: `frontend/src/styles/inkora-prototipo.css`
Contendrá las clases del prototipo, mapeadas a tokens existentes:

| Clase del prototipo | Mapeo a tokens |
| --- | --- |
| `--bg #eef1f4` | `var(--color-bg)` ✓ |
| `--panel #fff` | `var(--color-surface)` ✓ |
| `--green-500 #8cc63f` | `var(--color-primary)` ✓ |
| `--green-700 #1f5b31` | nuevo: `--green-700: #1f5b31` |
| `--green-900 #112b16` | `var(--color-sidebar-dark)` ✓ |
| `--green-50 #f0fbe8` | `var(--color-primary-soft)` ≈ |
| `--orange-50` | `var(--color-warning-soft)` ✓ |
| `--red-50` | `var(--color-danger-soft)` ✓ |
| `--blue-50 #eff6ff` | nuevo `--blue-soft` |
| `--shadow #...07` | `var(--shadow-card)` ✓ |
| `--radius 18px` | usar 18px directo (radio específico del proto) |

Bloques de CSS a portar (copia 1:1 desde `inkora_prototipo_funcional (2).html` líneas 282–1334), ajustando variables a los tokens:

1. **Layout**: `.app`, `.content`, `.page`, `@keyframes rise`, `.page-head`, `.eyebrow`.
2. **Botones de página**: `.btn`, `.btn.primary`, `.btn.dark`.
3. **Paneles base**: `.panel`, `.panel-header`, `.panel-body`.
4. **Dashboard**: `.attention`, `.attention-card`, `.metrics-grid`, `.metric`, `.dashboard-grid`, `.side-stack`, `.quick-actions`, `.todo-list`, `.todo`, `.aging`, `.aging-row`, `.bar`, `.sunat-grid`, `.sunat-box`.
5. **Tablas compartidas**: `.data-table`, `.table-wrap`, `.status` (ok/pending/bad/neutral/blue/purple), `.table-footer`, `.pagination`, `.page-btn`.
6. **Clientes**: `.stats-row`, `.stat`, `.toolbar`, `.search-box`, `.segments-row`, `.segments`, `.segment`, `.client-list`, `.client-row`, `.list-head`, `.client-avatar`, `.pill`, `.contact-block`, `.commercial`, `.activity-block`, `.actions-col`, `.edit-btn`, `.more-btn`.
7. **Drawer**: `.overlay`, `.drawer`, `.drawer-header`, `.drawer-body`, `.drawer-footer`, `.drawer-icon`, `.close-drawer`.
8. **Forms**: `.form-section`, `.section-label`, `.form-grid`, `.span-2…12`, `.field`, `.field.full`, `.control`, `.control-with-button`, `.inline-btn`, `.field-help`, `.btn-lg`, `.optional`, `.req`.
9. **Listados (Facturas/Boletas/Productos/Guías)**: `.module-tabs`, `.module-tab`, `.count-badge`, `.filter-card`, `.filter-card.products`, `.filter-card.guides`, `.filter-field`, `.filter-control`, `.summary-strip`, `.summary-items`, `.summary-item`, `.summary-icon`, `.records-card`, `.records-head`, `.record-action`, `.view-btn`.
10. **Productos**: `.product-title`, `.product-icon` (variantes green/teal/orange/purple/yellow/pink).
11. **Cotización builder**: `.quote-tabs`, `.tab`, `.builder`, `.client-result`, `.line-table`, `.line-head`, `.line-row`, `.product-input`, `.code-chip`, `.trash-btn`, `.line-footer`, `.link-btn`, `.toggle-chip`, `.switch`, `.note-blocks`, `.note-row`, `.color-pill`, `.summary-card`, `.summary-header`, `.summary-body`, `.total-line`, `.grand-total`, `.summary-actions`, `.side-btn`, `.hint-card`.
12. **Crear comprobante**: `.doc-type-row`, `.doc-selector`, `.small-pill`, `.comprobante-grid`, `.top-form-grid`, `.lines-summary-grid`, `.info-strip`, `.info-box`.
13. **Modal preview**: `.modal-overlay`, `.preview-modal`, `.preview-header`, `.preview-close`, `.preview-body`, `.pdf-paper`, `.pdf-top`, `.pdf-logo`, `.pdf-title`, `.pdf-line`, `.pdf-info`, `.pdf-table`, `.pdf-bottom`, `.pdf-total-row`.
14. **Configuración** (línea 1834+ del prototipo): `.settings-overview`, `.settings-overview-copy`, `.settings-overview-actions`, `.settings-meta-grid`, `.settings-metric`, `.settings-metric-top`, `.settings-metric-icon`, `.tiny-link`, `.settings-tabs`, `.settings-tab-btn`, `.settings-view`, `.settings-grid`, `.settings-section-stack`, `.settings-hero-card`, `.settings-hero-grid`, `.identity-showcase`, `.identity-logo`, `.settings-side-note`, `.settings-kpi-badge`, `.settings-side-list`, `.info-grid`, `.info-card`, `.split-config`, `.form-card`, `.settings-form-grid-2`, `.config-field`, `.input-control`, `.select-control`, `.helper`, `.bank-item`, `.bank-item-head`, `.transfer-grid`, `.bank-mini-grid`, `.badge-soft` (ok/warn/neutral), `.link-danger`, `.settings-info-rail`, `.settings-rail-card`, `.metric-line`, `.credential-status-grid`, `.status-tile`, `.status-pill`, `.fiscal-grid`, `.credential-list`, `.credential-item`, `.notice-card`, `.emission-flow`, `.emission-step`, `.account-overview`, `.account-card`, `.account-head`, `.account-avatar`, `.account-role`, `.account-grid`, `.account-side`, `.section-kicker`, `.appearance-layout`, `.appearance-card`, `.theme-options`, `.theme-btn`, `.divider`, `.texture-row`, `.checkbox`, `.appearance-preview`, `.preview-mock`, `.preview-mock-topbar`, `.preview-mock-body`, `.preview-sidebar`, `.preview-content`, `.preview-line`, `.preview-card`.
15. **Responsive**: bloques `@media (max-width: 1240px)` y `@media (max-width: 920px)`.

> Importante: las clases de Configuración no aparecen en los selectores extraídos del prototipo (faltan en el `<style>`). Hay que **definirlas en el CSS nuevo** copiando las que están en el `<style>` del archivo y extrapolando con los mismos tokens (colores neutrales, paneles, info-grid, etc.) — es lo que el prototipo deja "implícito" en su HTML.

### 2.2 Importar el CSS nuevo
- Añadir `@import './styles/inkora-prototipo.css';` a `frontend/src/app.css`, **después** de `tokens.css` y `globals.css`, para que sus reglas ganen especificidad sin romper componentes ya estilizados.
- Mantener `globals.css` (lo usan otras vistas no rediseñadas todavía como Login y SuperadminPage).

---

## 3. Refactor por página

Patrón general por página:
1. Reemplazar el wrapper Tailwind por la marcación del prototipo (`<section class="page-head">`, `<article class="panel">`, etc.).
2. Sustituir cada emoji por `<LucideIcon size={...} />` con clase `text-[var(--color-...)]`.
3. Mantener los hooks/servicios actuales (no se toca lógica de fetch ni estado de auth).

### 3.1 Dashboard — `Dashboard.jsx`
Estructura objetivo (líneas 1393–1498 del prototipo):
- `page-head` con eyebrow "Centro operativo", h2 "Resumen operativo", botón pill con `<CalendarDays />` + mes actual.
- `<section class="attention">` — banner verde oscuro con 4 tarjetas pequeñas (pagos sin conciliar, rechazados SUNAT, cuentas vencidas, cotizaciones pendientes). Datos: ya están en `dashboard.stats()` y `cobranzaResumen()`.
- `metrics-grid` (4 métricas): Ventas emitidas, Cobrado, Pendiente por cobrar, Estado SUNAT.
- `dashboard-grid` izquierda: panel "Actividad reciente" con `data-table` (Documento / Cliente / Fecha / Total / Estado) + `quick-actions` (3 botones: Crear factura, Registrar cobro, Enviar recordatorio).
- `dashboard-grid` derecha (`side-stack`): panel "Pendientes urgentes" con `todo-list` + panel "Cuentas por cobrar" con `aging` (3 barras: por vencer / 1-15 / +60).
- Panel inferior "Seguimiento de cobranza" con tabla (Cliente / Documento / Monto / Vencimiento / Días atraso / Estado / Acción).
- Quitar todos los emojis: el `📅` del header → `<CalendarDays />`; en `todo-list` los iconos `💳 📄 📩` → `<CreditCard /> <FileText /> <Mail />` con fondo `panel-soft`.

### 3.2 Clientes — `ClientesPage.jsx`
Estructura objetivo (líneas 1500–1546):
- `page-head` con eyebrow "Directorio comercial", botones `Importar / Exportar / + Nuevo cliente` (íconos `Upload`, `Download`, `Plus`).
- `stats-row` con 4 stats: Activos / Con crédito / Con deuda / Datos incompletos (ya tenemos esos KPIs; si no, calcularlos en el mismo componente).
- Panel principal: `toolbar` con `search-box` (icono `Search`) + acciones (`Filtrar`, `Columnas`, `+ Nuevo cliente`).
- `segments-row`: chips ("Todos", "Empresas", "Personas", "Con deuda", "Datos incompletos") + sort-text.
- `client-list`: cabecera + filas estilo prototipo (avatar coloreado por inicial, name-line con pill empresa/persona, contact-block, commercial pills, activity-block, actions-col).
- Drawer "Nuevo / Editar cliente" con tres secciones (`Identidad fiscal`, `Contacto`, `Condiciones comerciales`) — íconos en section-label vienen de Lucide (`Receipt`, `Mail`, `Briefcase`).

### 3.3 Cotizaciones — `CotizacionesPage.jsx` y `CotizacionDetalle.jsx`
Estructura objetivo (líneas 1548–1620):
- Tabs `quote-tabs`: "Nueva cotización" / "Historial" / "Emitidas SUNAT" (`Plus`, `RotateCcw`, `Receipt`).
- `builder` grid (1fr / 360px):
  - Columna izquierda: panel "Cliente y condiciones" con form-grid 12 columnas y `client-result` cuando hay cliente seleccionado; panel "Líneas de detalle" con `line-table` editable; panel "Observaciones del PDF" con `note-blocks`.
  - Columna derecha (sticky): `summary-card` con totales + `summary-actions` (Vista previa / Guardar borrador / Guardar) + `hint-card` verde oscuro debajo.
- "Historial" debe usar `records-card` + `data-table` con columnas Serie/Cliente/Fecha/Total/Estado/Acción.

### 3.4 Facturas / Boletas — `FacturasPage.jsx`, `BoletasPage.jsx`, `DocumentList.jsx`
Estructura objetivo (líneas 1622–1662 + el `renderComprobantesTable` JS):
- `page-head` con título y botones `Exportar` / `+ Nueva factura|boleta` (links a `/comprobantes/nuevo`).
- `module-tabs`: Todas / Borradores / Emitidas / Pendientes / Rechazadas / Anuladas con `count-badge`.
- `filter-card` con search + Estado + Cobranza/SUNAT + Moneda + Desde + Hasta + botón Filtros.
- `summary-strip` con métricas claves (Por cobrar / Vencidas / Aceptadas SUNAT) — boletas: Emitidas hoy / Aceptadas SUNAT / Por cobrar.
- `records-card` con `data-table` (Serie-Número, Cliente+RUC, Emisión, Vencimiento (sólo factura), Total, SUNAT, Cobranza/Pago, Acción).
- Refactorizar `DocumentList.jsx` para que acepte un `variant` ("factura"|"boleta") y produzca este layout. Mantener la lógica de fetch + filtros existente.

### 3.5 Guías — `GuiasPage.jsx` y `GuiaDetalle.jsx`
Estructura objetivo (líneas 1664–1705):
- `page-head` + `module-tabs` (Todas / Pendientes / En tránsito / Emitidas / Anuladas).
- `filter-card.guides` con 6 columnas (search, estado, motivo, desde, hasta, origen/destino).
- `summary-strip` con 4 mosaicos: Pendientes (`Package`), En tránsito (`Truck`), Emitidas hoy (`CheckCircle2`), Emitidas mes (`FileText`).
- `records-card` con tabla (Número, Fecha traslado, Cliente/destinatario, Origen, Destino, Comprobante relacionado, Estado, Acción).
- Detalle: usar el mismo `comprobante-grid` (cliente + lines-summary-grid).

### 3.6 Productos — `ProductosPage.jsx`
Estructura objetivo (líneas 1707–1744):
- `page-head` con eyebrow "Catálogo reusable" + botones `Exportar` / `+ Nuevo producto`.
- `module-tabs`: Todos / Productos / Servicios / Activos / Inactivos / Más usados.
- `filter-card.products`: search + Tipo + Categoría + Estado + U.M. + Filtros.
- `metrics-grid` con 4 métricas (productos activos, servicios activos, más usados, precio actualizado). Los iconos derecha (`◈ ▣ 🔥 ✓`) → `Package`, `Wrench`, `Flame`, `BadgeCheck`.
- `records-card` con `data-table` (Producto/Servicio + product-title con product-icon coloreado, Tipo, SKU, Categoría, U.M., Precio, Estado, Acción). Asignación de color del icono por hash del SKU para mantener consistencia.
- Drawer "Nuevo / Editar producto" con 3 secciones (Información, Precio y unidad, Control interno). Iconos section-label desde Lucide (`Package`, `DollarSign`, `Settings`).

### 3.7 Crear comprobante — `ComprobanteNuevoPage.jsx`
Estructura objetivo (líneas 1746–1824):
- `page-head` con link "← Volver al listado" y h2 "Crear comprobante".
- `doc-type-row`: `doc-selector` (Factura / Boleta) + small-pills CPE y Contingencia.
- `top-form-grid` (1fr / 0.78fr): panel "Datos del comprobante" (form-grid 12) + panel "Datos del cliente".
- `lines-summary-grid`: panel "Líneas del comprobante" con cabecera de acciones (Subir CSV, + Agregar línea) + `line-table` editable (col `#`, código, producto, unidad, cant., p. unitario, total, eliminar). `info-strip` debajo.
- Aside `summary-card` sticky: pills (tipo doc + serie + N° líneas), totales (Subtotal, IGV, Total), `summary-actions` (Vista previa, Emitir factura/boleta) + `info-box` "Sin cliente seleccionado".

### 3.8 Configuración — `ConfiguracionPage.jsx`
Estructura objetivo (líneas 1834–2110):
- `settings-overview` (header con eyebrow + h3 + texto + acciones Restablecer / Guardar cambios).
- `settings-meta-grid` con 4 mosaicos (Empresa / SUNAT / Cuenta / Apariencia) — íconos Lucide (`Building2`, `Sun`, `User`, `Palette`).
- `settings-tabs` 4 botones: Perfil de Empresa / Config. Fiscal / Mi Cuenta / Apariencia.
- **Tab Perfil**: hero card con identity-showcase, info-grid (Razón social / RUC / Dirección / Teléfono); `split-config` con form-card "Contacto comercial" + form-card "Datos para la transferencia" (lista `bank-item` con cabecera y `transfer-grid`); rail derecho con 3 `settings-rail-card` (Impacto, Uso en documentos, Recomendación UX).
- **Tab Config. Fiscal**: `credential-status-grid` (3 status-tiles: ApisPeru / Credenciales SOL / Certificado PFX); `fiscal-grid` con panel `credential-list` + `notice-card` y rail con "Prioridad actual" + `emission-flow` (3 steps).
- **Tab Mi Cuenta**: `account-overview` con `account-card` + `account-side` (rail con metric-line: Perfil/Último acceso/Tenant + rail Notas).
- **Tab Apariencia**: `appearance-layout` con `appearance-card` (selector de tema 3 botones + textura toggle + appearance-preview) + rail "Estado visual" + `preview-mock` (mini-mock visual).

### 3.9 Cobranza — `CobranzaPage.jsx` (inferido)
Patrón inferido: bandeja operativa (igual a Facturas).
- `page-head`: "Cobranza" + acciones `Exportar`, `+ Registrar pago` (`Plus`).
- `summary-strip` con 4 métricas: Por cobrar mes, Vencidas, Cobrado mes, Tasa de recupero (`Wallet`, `AlertTriangle`, `CheckCircle2`, `TrendingUp`).
- `module-tabs`: Todos / Por vencer / Vencidos / Pagados parcial / Pagados.
- `filter-card`: search (cliente o documento) + Cliente + Estado + Antigüedad + Desde + Hasta.
- `records-card` con `data-table`: Cliente, Documento, Total, Saldo, Vencimiento, Días atraso, Estado, Acción (`Recordar`, `Conciliar`, `Ver`).

### 3.10 Notas Cred/Deb — `NotasPage.jsx` (inferido)
Patrón: similar a Crear comprobante, pero requiere documento referenciado.
- `page-head` + `module-tabs` (Todas / Crédito / Débito / Pendientes / Aceptadas / Rechazadas).
- `filter-card`: search + Tipo (Crédito|Débito) + Motivo (SUNAT 07/08) + Documento ref. + Desde/Hasta.
- `summary-strip`: Notas emitidas mes, Crédito acumulado, Débito acumulado, Pendientes SUNAT.
- `records-card` con tabla: Serie-Número, Tipo (NC/ND), Doc. afectado, Cliente, Motivo, Total, SUNAT, Acción.
- Botón "+ Nueva nota" lleva a un wizard idéntico al `comprobante-grid` con un panel extra arriba "Documento a corregir" (search por serie+correlativo + chip motivo) — reutiliza `top-form-grid` y `lines-summary-grid`.

### 3.11 Resumen diario — `ResumenDiarioPage.jsx` (inferido)
Patrón: bitácora SUNAT diaria.
- `page-head` con selector de día (`DatePicker`) + botón `Reenviar resumen` (`RefreshCw`).
- `metrics-grid` (4): Boletas incluidas, Total emitido, Estado SUNAT (Operativo/Pendiente), Última generación.
- `panel` "Detalle del resumen" con `data-table`: Serie-Número, Cliente, Total, Estado, Motivo (anulación/baja), Acción.
- `info-strip` con texto explicativo del flujo y un botón `link-btn` "Cómo se genera el resumen ↗".

### 3.12 Bajas / Reversiones — `BajasPage.jsx`, `ReversionesPage.jsx` (inferido)
Mismo patrón (Comunicación de baja vs. Reversión de boleta):
- `page-head` con título + botón `+ Nueva baja|reversión`.
- `module-tabs`: Todas / Pendientes / Aceptadas / Rechazadas.
- `filter-card`: search + tipo doc afectado + estado + desde/hasta.
- `summary-strip`: Total mes / Aceptadas SUNAT / Pendientes / Rechazadas.
- `records-card` con tabla: Número de comunicación, Doc. afectado, Tipo, Motivo, Fecha generación, Estado SUNAT, Acción.
- Drawer "Nueva baja|reversión" con form-grid (Doc. afectado, Motivo SUNAT cat. 1–6, Observaciones, Confirmar emisión).

### 3.13 Retenciones / Percepciones — `RetencionesPage.jsx`, `PercepcionesPage.jsx` (inferido)
Mismo patrón (régimen tributario):
- `page-head` + acciones `Exportar` / `+ Nueva retención|percepción`.
- `module-tabs`: Todas / Emitidas / Pendientes / Anuladas.
- `summary-strip`: Total emitido mes (`Wallet`), Importe retenido/percibido (`Coins`), Aceptadas SUNAT (`ShieldCheck`), Pendientes (`Clock3`).
- `filter-card`: search + Cliente / Proveedor + Régimen (Agente / Sujeto) + Desde/Hasta.
- `records-card` con tabla: Serie-Número, Cliente, Documento(s) referenciado(s), Importe retenido/percibido, Total, SUNAT, Acción.

### 3.14 Seguridad — `ChangePasswordPage.jsx` (placeholder en proto)
Patrón inferido reutilizando `account-card` + `settings-rail-card`:
- `page-head` con eyebrow "Acceso y credenciales" + h2 "Seguridad".
- `account-overview` (1.4fr / 1fr):
  - `account-card` con form para cambiar contraseña (Password actual / Nuevo / Confirmar) + botón primary `Guardar cambios`.
  - `account-side` con 2 rail-cards: "Sesión actual" (último acceso, IP, dispositivo, tenant) + "Recomendaciones" (texto: usar contraseña fuerte, activar 2FA en el futuro).
- `panel` "Actividad reciente de inicio de sesión" con `data-table` (Fecha / IP / Dispositivo / Resultado).

---

## 4. Modificaciones específicas a archivos existentes

| Archivo | Cambio |
| --- | --- |
| `frontend/src/styles/inkora-prototipo.css` | **Crear**: porting completo del CSS del prototipo (sección 2.1). |
| `frontend/src/app.css` | Añadir `@import './styles/inkora-prototipo.css';` después de los imports existentes. |
| `frontend/src/styles/tokens.css` | Añadir variables faltantes: `--green-700: #1f5b31`, `--green-850: #14331a`, `--blue-soft: #eff6ff`, `--purple-soft: #f5f3ff`, `--orange-warm: #f59e0b`. |
| `frontend/src/components/Sidebar.jsx` | Solo agregar a `GROUPS` los ítems faltantes y verificar que el orden sea idéntico al prototipo. Quitar emoji ☾ del toggle dark mode (ya usa `Moon/Sun`). |
| `frontend/src/layouts/AppLayout.jsx` | Quitar texto "Buscar en Inkora..." con caracter `Search` en azul; renombrar botón "Anadir" → "Añadir" con tilde. Sin más cambios. |
| `frontend/src/pages/Dashboard.jsx` | Reescribir JSX al patrón 3.1, manteniendo los hooks de carga. |
| `frontend/src/pages/ClientesPage.jsx` | Reescribir lista al patrón 3.2 + drawer con `form-grid`/`span-N`. |
| `frontend/src/pages/CotizacionesPage.jsx` | Reescribir builder al patrón 3.3. Como es un archivo grande (2628 líneas), partir en sub-componentes: `CotizacionBuilder`, `LineTable`, `NoteBlocks`, `SummaryCard`. |
| `frontend/src/pages/CotizacionDetalle.jsx` | Aplicar `panel` + `pdf-paper` para vista previa. |
| `frontend/src/components/documents/DocumentList.jsx` | Reescribir al patrón 3.4, parametrizando textos y `summary-strip` por tipo. |
| `frontend/src/pages/FacturasPage.jsx`, `BoletasPage.jsx` | Pasarle al componente las métricas y label correctos. |
| `frontend/src/pages/GuiasPage.jsx`, `GuiaDetalle.jsx` | Reescribir al patrón 3.5. |
| `frontend/src/pages/ProductosPage.jsx` | Reescribir al patrón 3.6. |
| `frontend/src/pages/ComprobanteNuevoPage.jsx` | Reescribir al patrón 3.7 (top-form-grid + lines-summary-grid + summary-card). |
| `frontend/src/pages/ConfiguracionPage.jsx` | Reescribir al patrón 3.8 (tabs internos `Perfil / Fiscal / Mi cuenta / Apariencia`). |
| `frontend/src/pages/CobranzaPage.jsx` | Reescribir al patrón 3.9. |
| `frontend/src/pages/NotasPage.jsx` | Reescribir al patrón 3.10. |
| `frontend/src/pages/ResumenDiarioPage.jsx` | Reescribir al patrón 3.11. |
| `frontend/src/pages/BajasPage.jsx`, `ReversionesPage.jsx` | Reescribir al patrón 3.12. |
| `frontend/src/pages/RetencionesPage.jsx`, `PercepcionesPage.jsx` | Reescribir al patrón 3.13. |
| `frontend/src/pages/ChangePasswordPage.jsx` | Aplicar patrón 3.14. |
| `frontend/src/components/ui/Drawer.jsx` | Asegurar que use `.drawer` / `.drawer-header` / `.drawer-body` / `.drawer-footer` del nuevo CSS para que tenga la silueta del prototipo (esquinas 26px, separación 14px del borde). |
| `frontend/src/components/ui/Modal.jsx` | Verificar que pueda renderizar el modal estilo `preview-modal` para vista previa de comprobante (ya existe `FiscalDocPreview`; se le envuelve en este shell). |

---

## 5. Convenciones para evitar emojis

- **Sidebar y topbar**: ya usan Lucide; no tocar.
- **Status pills (`status.ok/pending/bad/neutral/blue/purple`)**: pueden llevar opcionalmente `<CheckCircle2 size={11} />`, `<Clock3 size={11} />`, `<XCircle size={11} />`, `<MinusCircle size={11} />` antes del texto. El prototipo a veces los pone, a veces no — preferir **no incluir icono** dentro del status pill para dejar la lectura limpia (consistente con el estilo serio que pidió el usuario).
- **Botones (`btn`, `btn-lg`, `view-btn`, `edit-btn`)**: cuando lleven icono, va a la izquierda con `size={14}` y `strokeWidth={2}`.
- **Section labels en drawers (`section-label`)**: mantener el icono Lucide a la izquierda + texto. Color `var(--color-text-muted)`.
- **Métricas (`summary-icon`)**: el círculo lleva un icono Lucide en lugar del emoji.
- **Texto de ayuda (`field-help`, `info-strip`, `notice-card`)**: el `ⓘ` del prototipo se reemplaza por `<Info size={14} />`.

---

## 6. Orden de ejecución sugerido

1. **CSS base**:
   1. Añadir variables faltantes a `tokens.css`.
   2. Crear `styles/inkora-prototipo.css` con todas las clases.
   3. Importar desde `app.css`.
2. **Layout** (sidebar + topbar): pequeñas correcciones (orden de menú, tilde).
3. **Dashboard**: pieza más visible, valida tokens y patrones generales.
4. **Clientes** y **Productos**: validan `stats-row`, `module-tabs`, `records-card`, drawers.
5. **Facturas** + **Boletas** + `DocumentList.jsx`: patrón compartido.
6. **Guías**: variante con 6 columnas de filtros.
7. **Cotizaciones** (builder + historial): es la pieza más grande; refactorizar en sub-componentes mientras se aplica el diseño.
8. **Crear comprobante**: usa lo aprendido en Cotizaciones.
9. **Cobranza, Notas, Resumen, Bajas, Reversiones, Retenciones, Percepciones, Seguridad**: patrones derivados, en bloque al final.
10. **Configuración**: rediseño grande, hacerlo después del builder de Cotizaciones porque comparte muchos componentes (form-cards, rail-cards).
11. **QA visual**: comparar lado a lado con `inkora_prototipo_funcional (2).html` abierto en navegador, verificar que todas las clases respetan el spacing exacto (radios 18/22 px, gaps 12/14/16, sombras `--shadow-card`), y que **ningún emoji** queda en el árbol React.

---

## 7. Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Conflicto de clases con `globals.css` (ya define `.btn`, `.panel`, `.toolbar`, `.summary-strip`, etc.). | El nuevo CSS se importa después y sus reglas deben usar selectores específicos del prototipo (`.app .panel`, etc.). Donde colisionen, **eliminar la regla obsoleta** de `globals.css`. Hacer `grep` de `\.panel\b`, `\.btn\b`, `\.toolbar\b` antes de portar. |
| Pages como `CotizacionesPage.jsx` (2628 líneas) se vuelven imposibles de revisar en un solo PR. | Dividir en sub-componentes durante el refactor (`CotizacionForm`, `CotizacionLineTable`, `CotizacionSummary`, `CotizacionHistory`, `CotizacionPdfPreview`). |
| Drawer y Modal ya existen y los usan otras pantallas. | Ajustar los estilos de `Drawer.jsx` / `Modal.jsx` con clases que coincidan con el prototipo, sin romper su API. |
| Datos de SUNAT y emisión deben seguir funcionando. | Solo se reemplaza el JSX/markup. Toda llamada a `api`, `services/*`, hooks de auth queda intacta. Tests del backend no se tocan. |
| Modo oscuro debe seguir respetándose. | Las nuevas reglas usan tokens (`var(--color-...)`) — el dark theme las hereda automáticamente. Donde el prototipo hardcodea hex (`#fff`, `#102b16`), reemplazar por tokens. |
| Inferencias de páginas placeholder pueden no ajustarse 100% al modelo de datos. | Cada vista placeholder se construye encima de los servicios existentes (`bajas`, `reversiones`, `retenciones`, etc.) sin cambiarles la firma. Si falta alguna API, mostrar `EmptyState` con CTA hacia el flujo correspondiente. |

---

## 8. Definición de "hecho"

- [ ] `frontend/src/styles/inkora-prototipo.css` existe y contiene las clases de las 15 secciones del 2.1.
- [ ] `tokens.css` tiene las variables nuevas.
- [ ] Todas las páginas de la sección 3 renderizan con el mismo layout visual que el prototipo (verificación lado a lado).
- [ ] No queda **ningún** emoji literal (`grep -rE "[☀-➿]|[🀀-􏿿]" src/` devuelve vacío).
- [ ] Los íconos de Lucide están integrados con `size` y color por contexto.
- [ ] Modo claro y oscuro mantienen consistencia (paneles, sombras, contraste de texto).
- [ ] Tests existentes (`npm run build`) compilan sin warnings nuevos.
- [ ] Se verifica manualmente cada flujo: emitir factura, crear cotización, registrar cliente, configuración, vista previa PDF.
