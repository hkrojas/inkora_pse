# Plan de Diseño Responsivo — Inkora Frontend

Plan integral para que el frontend de Inkora sea 100% usable en móviles (≥360 px) y tablets (≥768 px), sin perder la experiencia de escritorio actual.

---

## 1. Auditoría del estado actual

### 1.1 Qué ya es responsivo (parcial)
- **Topbar** — tiene media queries a `900px` y `640px` que reducen tipografía, ocultan el breadcrumb/kicker en móvil y reflujan el reloj/chip SUNAT ([app.css:629-775](frontend/src/app.css#L629-L775)).
- **Login** — `.lp-grid` colapsa a una columna a `860px` y oculta `.lp-brand` ([app.css:2801-2803](frontend/src/app.css#L2801-L2803)).
- **Formularios genéricos** — `.form-grid--2` y `.form-grid--3` caen a 1 columna a `768px` ([app.css:2113-2115](frontend/src/app.css#L2113-L2115)).
- **Comprobante nuevo** — dos media queries (`1100px`, `760px`) reorganizan el constructor ([app.css:3875](frontend/src/app.css#L3875), [app.css:3893](frontend/src/app.css#L3893)).
- **Utilidades Tailwind-like** — `md:grid-cols-*` y `lg:grid-cols-*` definidas manualmente ([app.css:2659-2672](frontend/src/app.css#L2659-L2672)).

### 1.2 Problemas críticos en móvil
1. **Sidebar fija de 248 px** ([app.css:781-794](frontend/src/app.css#L781-L794)) — en pantallas <768 px consume ~70% del ancho. No existe patrón de drawer/hamburguesa.
2. **Sin botón de menú móvil** — [AppLayout.jsx](frontend/src/layouts/AppLayout.jsx) no tiene toggle para abrir/cerrar sidebar en móvil.
3. **Tablas `.ink-table`** — 20 páginas usan tablas con 5-9 columnas ([FacturasPage.jsx:64-122](frontend/src/pages/FacturasPage.jsx#L64-L122), [BoletasPage.jsx:64-122](frontend/src/pages/BoletasPage.jsx#L64-L122), [CotizacionesPage.jsx](frontend/src/pages/CotizacionesPage.jsx), etc.). No hay wrapper con scroll horizontal ni vista de tarjetas móvil.
4. **Modales con `maxWidth` fijo** ([Modal.jsx:24-29](frontend/src/components/ui/Modal.jsx#L24-L29)) — `sm: 440px`, `md: 640px`, `lg: 800px`, `xl: 960px`. Con `width: 100%` y `padding: 24px` del backdrop funcionan, pero el contenido interno (grids, tabs, tablas) no adapta.
5. **`.page-header` en flex row con `justify-content: space-between`** ([app.css:1192-1197](frontend/src/app.css#L1192-L1197)) — el botón de acción se pega al título sin margen cuando el texto es largo.
6. **Topbar reloj + chip SUNAT** — en móvil sigue ocupando ~60% del alto de la topbar.
7. **Targets táctiles** — varios botones/links tienen `padding: 4px 10px, fontSize: 12` (ver [FacturasPage.jsx:108-109](frontend/src/pages/FacturasPage.jsx#L108-L109)) — por debajo del mínimo de 44×44 px recomendado por WCAG 2.5.5.
8. **Dashboard KPIs** — presumiblemente grid de 4 columnas, sin verificación explícita en media queries móviles.
9. **CotizacionDetalle / GuiaDetalle / ComprobanteNuevo** — layouts multi-columna complejos; solo el último tiene cuidado móvil.
10. **No hay viewport meta verificado** — revisar `<meta name="viewport" ...>` en [index.html](frontend/index.html).

---

## 2. Estrategia de breakpoints

Adoptar **mobile-first** con tres breakpoints canónicos, coherentes con lo ya definido:

| Token | Valor  | Dispositivo objetivo                  | Uso                                                |
|-------|--------|---------------------------------------|----------------------------------------------------|
| `sm`  | 640 px | móvil landscape / phablet             | Ajustes finos (ej. `flex-direction`)               |
| `md`  | 768 px | tablet vertical                       | Aparece sidebar + layouts 2-col                    |
| `lg`  | 1024 px| tablet landscape / desktop pequeño    | Layouts 3-4 col, sidebar completa                  |

**Regla**: "móvil" = `<768 px`. A partir de ese ancho se considera desktop y aparece la sidebar persistente.

Consolidar los breakpoints actuales (860, 900, 1100) hacia los canónicos cuando sea posible, salvo en casos específicos (p. ej. `comprobante-builder` a 1100 px donde hay justificación de contenido).

---

## 3. Arquitectura móvil: Sidebar → Drawer

### 3.1 Comportamiento deseado

- **≥768 px**: sidebar sticky actual (248 px / 60 px al colapsar).
- **<768 px**:
  - Sidebar oculta por defecto (`transform: translateX(-100%)`).
  - Topbar muestra **botón hamburguesa** a la izquierda del breadcrumb.
  - Al tocar hamburguesa → sidebar se desliza desde la izquierda con overlay oscuro sobre el contenido.
  - Tocar el overlay o un item del menú cierra el drawer.
  - Usar `position: fixed` + `z-index: 100`, overlay con `rgba(13,11,30,0.6)` y `backdrop-filter: blur(4px)`.

### 3.2 Cambios concretos

**[Sidebar.jsx](frontend/src/components/Sidebar.jsx)**:
- Añadir prop `mobileOpen` + `onMobileClose`.
- En móvil, renderizar también un overlay con `createPortal` para cerrar al tap fuera.
- Cerrar drawer automáticamente al cambiar `location.pathname` (escuchar con `useEffect`).
- En móvil, forzar modo expandido (ignorar `collapsed`) — no tiene sentido mostrar solo iconos en un drawer.

**[AppLayout.jsx](frontend/src/layouts/AppLayout.jsx)**:
- Añadir estado `const [sidebarMobileOpen, setSidebarMobileOpen] = useState(false)`.
- Insertar botón `<Menu />` (lucide) visible solo en `<768px` dentro de `.topbar-main`.
- Pasar props a `<Sidebar mobileOpen={...} onMobileClose={...} />`.

**app.css — nueva sección `@media (max-width: 767px)`**:
```css
.sidebar-shell {
  position: fixed;
  top: 0; left: 0; bottom: 0;
  transform: translateX(-100%);
  transition: transform 240ms var(--ease-out);
  z-index: 100;
  width: 280px; /* un poco más ancho en móvil para mejor touch */
}
.sidebar-shell.sidebar-mobile-open {
  transform: translateX(0);
  box-shadow: 8px 0 32px rgba(13,11,30,0.35);
}
.sidebar-mobile-overlay {
  position: fixed; inset: 0;
  background: rgba(13,11,30,0.6);
  backdrop-filter: blur(4px);
  z-index: 90;
}
.sidebar-mobile-trigger {
  display: inline-flex; /* oculto en >=768 */
}
```

---

## 4. Topbar móvil

### 4.1 Problemas actuales
- `SunatExchangeRate` ([AppLayout.jsx:9-83](frontend/src/layouts/AppLayout.jsx#L9-L83)) y `SystemClock` consumen mucho espacio vertical en móvil pese a los media queries existentes.
- `topbar-breadcrumb` y `topbar-kicker` ya se ocultan en `<640px` — bien.

### 4.2 Ajustes
- En `<768px`: mostrar solo **hamburguesa + título + reloj compacto (hora, sin fecha)**. Ocultar `sunat-badge` "SUNAT Sync" y mover el `sunat-rate-chip` a un segundo renglón colapsable o ocultarlo por completo; alternativa: mostrarlo solo bajo demanda tocando un icono `$`.
- Reducir `topbar-title` a 16 px en móvil.
- Forzar `topbar-shell` a una sola fila con alineación centrada vertical.

---

## 5. Tablas → Cards apilables en móvil

**Decisión**: patrón **dual**:
- En `≥768 px`: `.ink-table` tradicional (actual).
- En `<768 px`: convertir cada fila en una **tarjeta apilada** (stack layout) con etiquetas embebidas (data-label pattern) o con componentes dedicados.

### 5.1 Opción elegida: CSS `data-label` con pseudo-elementos
Más simple, un solo render. Añadir `data-label` a cada `<td>` y usar CSS:
```css
@media (max-width: 767px) {
  .ink-table, .ink-table thead, .ink-table tbody,
  .ink-table tr, .ink-table td { display: block; width: 100%; }
  .ink-table thead { display: none; }
  .ink-table tr {
    border-bottom: 1px solid var(--border-subtle);
    padding: 12px 14px;
  }
  .ink-table td {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 6px 0;
    border: none;
  }
  .ink-table td::before {
    content: attr(data-label);
    font-family: var(--font-mono);
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-tertiary);
    flex-shrink: 0;
  }
}
```

### 5.2 Cambios por archivo
Páginas a modificar (añadir `data-label="..."` a cada `<td>`):
- [FacturasPage.jsx](frontend/src/pages/FacturasPage.jsx)
- [BoletasPage.jsx](frontend/src/pages/BoletasPage.jsx)
- [CotizacionesPage.jsx](frontend/src/pages/CotizacionesPage.jsx)
- [ClientesPage.jsx](frontend/src/pages/ClientesPage.jsx)
- [ProductosPage.jsx](frontend/src/pages/ProductosPage.jsx)
- [CobranzaPage.jsx](frontend/src/pages/CobranzaPage.jsx)
- [GuiasPage.jsx](frontend/src/pages/GuiasPage.jsx)
- [NotasPage.jsx](frontend/src/pages/NotasPage.jsx)
- [RetencionesPage.jsx](frontend/src/pages/RetencionesPage.jsx)
- [PercepcionesPage.jsx](frontend/src/pages/PercepcionesPage.jsx)
- [ResumenDiarioPage.jsx](frontend/src/pages/ResumenDiarioPage.jsx)
- [BajasPage.jsx](frontend/src/pages/BajasPage.jsx)
- [ReversionesPage.jsx](frontend/src/pages/ReversionesPage.jsx)
- [SuperadminPage.jsx](frontend/src/pages/SuperadminPage.jsx)

### 5.3 Alternativa — scroll horizontal
Para tablas con columnas irreducibles (p. ej. reportes financieros), envolver en `<div className="ink-table-scroll">` con `overflow-x: auto` + gradiente en los bordes para indicar scroll. Aplicar solo a casos justificados.

---

## 6. Modales

Ya ocupan `width: 100%` con padding 24 px. Ajustes:

- **[Modal.jsx](frontend/src/components/ui/Modal.jsx:33-46)** — reducir el padding del backdrop a `12px` en móvil (vía media query en app.css, no inline style) para maximizar el área útil.
- **Body `padding: 24px`** ([Modal.jsx:115](frontend/src/components/ui/Modal.jsx#L115)) — bajar a 16 px en móvil.
- **`maxHeight: 90vh`** — mantener, pero verificar que el header no se oculte en teclados desplegados (iOS). Usar `max-height: 100dvh` (dynamic viewport) cuando esté disponible.
- Convertir estilos inline a clases CSS (`.modal-backdrop`, `.modal-panel`, `.modal-header`, `.modal-body`) para poder aplicar media queries sin refactor mayor. Opcional pero recomendado.

---

## 7. Formularios y layouts complejos

### 7.1 Grids genéricos
`.form-grid--2` y `.form-grid--3` ya colapsan a `768px` — OK.

### 7.2 Verificar grids Tailwind-like
Muchas páginas usan `md:grid-cols-2`, `lg:grid-cols-3`. Auditar que no haya `grid-cols-3` sin prefijo (aplicaría en móvil). Si existe, envolver con `grid-cols-1 md:grid-cols-3`.

Comando de búsqueda: `grep -n "grid-cols-[234]" frontend/src/pages/*.jsx` (excluir los que tengan `md:`/`lg:` prefix).

### 7.3 Páginas con layouts propios a revisar
- **[Dashboard.jsx](frontend/src/pages/Dashboard.jsx)** — grid de KPIs (4 col) debe ser `grid-cols-2` en móvil (dos KPIs por fila conservan legibilidad) y `grid-cols-1` en `<400px` muy estrecho.
- **[CotizacionDetalle.jsx](frontend/src/pages/CotizacionDetalle.jsx)** — cabecera con totales + acciones. Stack vertical en móvil.
- **[GuiaDetalle.jsx](frontend/src/pages/GuiaDetalle.jsx)** — igual.
- **[ComprobanteNuevoPage.jsx](frontend/src/pages/ComprobanteNuevoPage.jsx)** — ya tiene cuidado móvil a 760/1100 px; validar tras cambios globales.
- **[ConfiguracionPage.jsx](frontend/src/pages/ConfiguracionPage.jsx)** — tabs/secciones probablemente en grid.
- **[SuperadminPage.jsx](frontend/src/pages/SuperadminPage.jsx)** — revisar formularios fiscales complejos.

### 7.4 `.page-header` responsivo
```css
@media (max-width: 640px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
  }
  .page-header .btn-primary,
  .page-header .page-actions { width: 100%; justify-content: center; }
  .page-title { font-size: 20px; }
  .page-subtitle { font-size: 13px; }
}
```

---

## 8. Targets táctiles y tipografía

Seguir WCAG 2.5.5 (mínimo 44×44 px para targets interactivos):

- Auditar botones con `padding: 4px 10px, fontSize: 12` — subir a `padding: 10px 14px, fontSize: 13` en móvil.
- Links con iconos (p. ej. "Ver PDF" en [FacturasPage.jsx:104-113](frontend/src/pages/FacturasPage.jsx#L104-L113)) — aumentar área clicable.
- `input`, `select`, `textarea` — mínimo 44 px de alto en móvil; usar `font-size: 16px` para evitar zoom automático en iOS.
- Iconos de cerrar modal, reintentar, etc. — `min-width/height: 40px`.

**Acción**: revisar `.btn-primary`, `.btn-ghost`, `.btn-secondary` y añadir overrides móviles a su CSS base.

---

## 9. Viewport y CSS base

### 9.1 [index.html](frontend/index.html)
Confirmar la presencia de:
```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
```

### 9.2 Safe areas (iOS notch)
Añadir soporte para `env(safe-area-inset-*)` en:
- `.sidebar-shell` — `padding-top: max(20px, env(safe-area-inset-top))`
- `.topbar-shell` — `padding-left: max(24px, env(safe-area-inset-left))`
- Drawer móvil — `padding-bottom: env(safe-area-inset-bottom)`

### 9.3 Scroll containment
El `.app-content-shell` tiene `overflow-y: auto` — OK. En móvil con drawer abierto, aplicar `overflow: hidden` al `<body>` (ya se hace en `Modal.jsx`; replicar en `Sidebar` drawer).

---

## 10. Accesibilidad y UX móvil

- **Focus visible** — verificar que el botón hamburguesa tenga `outline` claro en `:focus-visible`.
- **ARIA** — `aria-expanded`, `aria-controls="sidebar-nav"` en el botón hamburguesa.
- **Escape** — cerrar drawer con tecla ESC (igual que `Modal.jsx`).
- **Trap focus** — cuando el drawer está abierto en móvil, atrapar foco dentro. (Opcional para la primera iteración.)
- **Prefer reduced motion** — ya existe `@media (prefers-reduced-motion: reduce)` en [app.css:178](frontend/src/app.css#L178); añadir las nuevas transiciones (drawer, cards) al set desactivado.

---

## 11. Página por página — checklist

| Página                   | Cambios principales                                                                  |
|--------------------------|--------------------------------------------------------------------------------------|
| `Dashboard`              | KPI grid 4→2→1 col, VencidaRow stack vertical, sparklines con `max-width:100%`       |
| `ClientesPage`           | Tabla → cards con `data-label`, search full-width, botón `+` fijo/flotante opcional  |
| `ProductosPage`          | Igual que Clientes                                                                   |
| `CotizacionesPage`       | Tabla → cards, modal "Nueva cotización" con grid 1-col en items                      |
| `CotizacionDetalle`      | Totales + acciones en stack, tabla de items → cards, botones emisión full-width      |
| `CobranzaPage`           | Tabla vencidas → cards, filtros (fecha, cliente) en accordion                        |
| `GuiasPage` / `GuiaDetalle` | Tabla → cards, mapa/dirección en full-width                                       |
| `FacturasPage`           | Ya auditada arriba — aplicar `data-label` y botones más grandes                      |
| `BoletasPage`            | Igual que Facturas                                                                   |
| `NotasPage`              | Tabla → cards, referencia documento en stack                                         |
| `Retenciones/Percepciones/ResumenDiario/Bajas/Reversiones` | Tabla → cards, formularios de emisión full-width                |
| `ComprobanteNuevoPage`   | Ya tiene 760 px; validar tras migrar Modal y `.page-header`                           |
| `ConfiguracionPage`      | Tabs horizontales → scroll-x en móvil, formularios grid-cols-1                       |
| `SuperadminPage`         | Tablas tenants → cards, formularios fiscales en stack                                |
| `Login`                  | Ya responsivo; verificar que los inputs cumplan 44 px                                |

---

## 12. Fases de implementación

### Fase 1 — Infraestructura (1-2 días)
- Viewport meta + safe areas.
- Botón hamburguesa en `AppLayout`.
- Drawer móvil en `Sidebar` + overlay + cierre automático.
- Ajustes globales de `.page-header`, `.page-title`, botones base en móvil.
- Media queries de tabla genérica (patrón `data-label`).

### Fase 2 — Migración de tablas (2-3 días)
- Añadir `data-label` a todas las tablas listadas en §5.2.
- QA visual en cada página.

### Fase 3 — Layouts específicos (2-3 días)
- Dashboard (KPIs + VencidaRow).
- CotizacionDetalle, GuiaDetalle (cabeceras + acciones).
- ConfiguracionPage, SuperadminPage (tabs + formularios).

### Fase 4 — Modales y formularios (1 día)
- Migrar estilos inline de `Modal.jsx` a clases.
- Media queries para padding y altura.
- Auditar todos los modales de páginas individuales.

### Fase 5 — Pulido y accesibilidad (1-2 días)
- Targets táctiles ≥44 px.
- Tipografía inputs 16 px.
- Focus-visible, ARIA, ESC.
- Prueba con `prefers-reduced-motion`.
- Pruebas reales en Chrome DevTools (iPhone SE 375×667, Pixel 7 412×915, iPad 768×1024).

**Total estimado**: 7-10 días de trabajo dedicado.

---

## 13. Criterios de aceptación

- [ ] Todas las páginas son usables sin scroll horizontal involuntario a 375 px de ancho.
- [ ] Sidebar accesible vía hamburguesa en `<768 px` y se cierra al navegar.
- [ ] Todas las tablas presentan vista apilada legible en móvil.
- [ ] Todos los modales ocupan ≥90% del ancho en móvil sin contenido cortado.
- [ ] Todos los botones/links interactivos miden ≥44×44 px en móvil.
- [ ] Inputs no disparan zoom automático en iOS (font-size ≥16 px).
- [ ] Sin errores de layout a breakpoints 375, 414, 768, 1024, 1280, 1440 px.
- [ ] `prefers-reduced-motion` desactiva animaciones nuevas.

---

## 14. Riesgos y consideraciones

- **Tablas con scroll horizontal vs cards**: en páginas de reporte contable puede ser más útil scroll horizontal. Decidir caso por caso en Fase 2.
- **CustomSelect / otros componentes custom**: verificar que los dropdowns se posicionen correctamente en drawer/modal móvil. Puede requerir portalizarlos.
- **Impresión PDF / vista previa**: los PDFs de SUNAT se abren en nueva pestaña — no se ven afectados, pero verificar que el link "Ver PDF" sea accesible.
- **Tests visuales**: no hay tests frontend; la QA será manual. Considerar usar Playwright en el futuro.
