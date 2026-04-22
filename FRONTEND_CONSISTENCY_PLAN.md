# Plan de Consistencia Frontend — PrintFlow

Auditoría completa del frontend vs. sistema de diseño "Industrial / Command Center" (`logo/nuevo.md`).

**Total de hallazgos:** 45+ inconsistencias agrupadas en 10 categorías.
**Sistema de referencia:**
- Tipografía: `var(--font-body)` Inter + `var(--font-mono)` JetBrains Mono
- Paleta: brand-500 `#6366F1`, brand-600 `#4F46E5`, slate-900 `#0F172A`
- **Border-radius = 0 en todo** (excepto dots circulares)
- Botones primary: `bg-slate-900` + hover con `translate(-4px,-4px)` + `4px 4px 0 rgba(99,102,241,1)`
- Inputs/selects: `color-scheme: light`, focus `inset 0 0 0 1px #4F46E5`

---

## Categorías de hallazgos

### 1. Border-radius incorrecto (contradice spec `border-radius: 0`)

| Archivo | Línea | Problema | Fix |
|---|---|---|---|
| [src/app.css](frontend/src/app.css#L277) | 277 | `.btn-ghost` tiene `border-radius: var(--radius-md)` | `border-radius: 0` |
| [src/app.css](frontend/src/app.css#L299) | 299 | `.btn-danger` tiene `border-radius: var(--radius-md)` | `border-radius: 0` |
| [src/app.css](frontend/src/app.css#L834) | 834 | `.ink-card` tiene `border-radius: var(--radius-xl)` | `border-radius: 0` |
| [src/app.css](frontend/src/app.css#L1332) | 1332 | `.ink-inline-alert` tiene `border-radius: 10px` | `border-radius: 0` |
| [src/app.css](frontend/src/app.css#L1585) | 1585 | `.toast-item` tiene `border-radius: var(--radius-md)` | `border-radius: 0` |
| [src/app.css](frontend/src/app.css#L1645) | 1645 | `.trust-bar` tiene `border-radius: 8px` | `border-radius: 0` |
| [src/pages/CotizacionesPage.jsx](frontend/src/pages/CotizacionesPage.jsx#L394) | 394 | Botón `rounded-full` en tabla | Usar `ink-row-btn` |
| [src/pages/GuiasPage.jsx](frontend/src/pages/GuiasPage.jsx#L356) | 356 | Botón `rounded-full` en tabla | Usar `ink-row-btn` |
| [src/pages/ConfiguracionPage.jsx](frontend/src/pages/ConfiguracionPage.jsx#L121) | 121 | `<img className="rounded">` en logo | Remover `rounded` |
| [src/pages/SuperadminPage.jsx](frontend/src/pages/SuperadminPage.jsx#L242) | 242 | `rounded-[var(--radius-md)]` | Remover / cuadrado |

---

### 2. Variables CSS inexistentes

`--bg-muted` se usa en 3 archivos pero NO está definida en `app.css`. Los hovers no aplican.

| Archivo | Línea | Uso |
|---|---|---|
| [src/pages/CotizacionesPage.jsx](frontend/src/pages/CotizacionesPage.jsx#L394) | 394 | `hover:bg-[var(--bg-muted)]` |
| [src/pages/GuiasPage.jsx](frontend/src/pages/GuiasPage.jsx#L356) | 356 | `hover:bg-[var(--bg-muted)]` |
| [src/pages/SuperadminPage.jsx](frontend/src/pages/SuperadminPage.jsx#L242) | 242 | `bg-[var(--bg-muted)]` |

**Fix:** reemplazar por `var(--bg-surface-low)` (línea 42 de app.css) o `#F1F5F9`.

También `font-mono-label` usado en [CotizacionesPage:372-381](frontend/src/pages/CotizacionesPage.jsx#L372) no existe como clase Tailwind ni en app.css.

**Fix:** reemplazar por `style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700 }}`.

---

### 3. `<select>` nativos pendientes de migrar a `CustomSelect`

| Archivo | Línea | Contexto |
|---|---|---|
| [src/pages/CotizacionDetalle.jsx](frontend/src/pages/CotizacionDetalle.jsx#L43) | 43 | Método de pago |
| [src/pages/CotizacionDetalle.jsx](frontend/src/pages/CotizacionDetalle.jsx#L54) | 54 | Tipo de pago |
| [src/pages/SuperadminPage.jsx](frontend/src/pages/SuperadminPage.jsx#L688) | 688 | Rol de usuario |

**Fix:** importar `CustomSelect` de `components/ui/CustomSelect` y reemplazar.

---

### 4. Inline styles masivos que deberían ser clases reutilizables

| Archivo | Rango | Problema |
|---|---|---|
| [src/pages/CotizacionesPage.jsx](frontend/src/pages/CotizacionesPage.jsx#L87-L256) | 87-256 | Form completo con `style={{...}}` repetido |
| [src/pages/ConfiguracionPage.jsx](frontend/src/pages/ConfiguracionPage.jsx#L73-L276) | 73-276 | Página completa inline |
| [src/pages/GuiasPage.jsx](frontend/src/pages/GuiasPage.jsx#L53-L166) | 53-166 | Form de nueva guía inline |

**Fix:** extraer a clases `.modal-form`, `.modal-section`, `.config-tabs`, `.config-section` en `app.css`.

---

### 5. Colores hardcodeados fuera de paleta

| Archivo | Línea | Uso |
|---|---|---|
| [src/pages/ProductosPage.jsx](frontend/src/pages/ProductosPage.jsx#L214) | 214-221 | `dotColors`, `umColors` con hex ad-hoc |
| [src/pages/CobranzaPage.jsx](frontend/src/pages/CobranzaPage.jsx#L19) | 19-21 | `agingDot()` hex hardcoded |
| [src/pages/Dashboard.jsx](frontend/src/pages/Dashboard.jsx#L193) | 193 | `style={{ color: '#F59E0B' }}` |
| [src/pages/CobranzaPage.jsx](frontend/src/pages/CobranzaPage.jsx#L91) | 91,123 | `rgba(254,242,242,...)` inline |

**Fix:** usar variables `var(--color-warning)`, `var(--color-error)`, `var(--text-tertiary)`, o crear clases `.ink-table-row--overdue`.

---

### 6. Márgenes negativos / modal-footer duplicado

[ClientesPage:104](frontend/src/pages/ClientesPage.jsx#L104), [ProductosPage:92](frontend/src/pages/ProductosPage.jsx#L92), [GuiasPage](frontend/src/pages/GuiasPage.jsx) y [CotizacionesPage](frontend/src/pages/CotizacionesPage.jsx) usan `style={{ margin: '16px -24px -24px', borderRadius: 0 }}` sobre `.modal-footer`. La clase ya existe en [app.css:1476](frontend/src/app.css#L1476) — el inline style es redundante.

**Fix:** mover el reset de margen a la clase `.modal-footer` y eliminar inline.

---

### 7. Spacing inconsistente

`padding: '20px 24px'` vs `'24px'` vs `'14px 16px'` mezclados sin criterio en GuiasPage y CotizacionesPage.

**Fix:** definir tokens semánticos `.modal-section { padding: 20px 24px }`, `.modal-body { padding: 24px }`, `.toolbar { padding: 14px 16px }`.

---

### 8. Componentes UI — estado de adherencia

| Componente | Estado | Nota |
|---|---|---|
| [Modal.jsx](frontend/src/components/ui/Modal.jsx) | OK | `borderRadius: 0`, sombra offset correcta |
| [CustomSelect.jsx](frontend/src/components/ui/CustomSelect.jsx) | OK | Nuevo, ya alineado |
| [Badge.jsx](frontend/src/components/ui/Badge.jsx) | OK | Clases mapeadas |
| [EmptyState.jsx](frontend/src/components/ui/EmptyState.jsx) | OK | — |
| [Spinner.jsx](frontend/src/components/ui/Spinner.jsx) | OK | — |
| [Sidebar.jsx](frontend/src/components/Sidebar.jsx) | OK | — |
| [AppLayout.jsx](frontend/src/layouts/AppLayout.jsx) | OK | — |
| [Toast.jsx](frontend/src/components/ui/Toast.jsx) | ⚠️ | `.toast-item` tiene `border-radius` en CSS |

---

## Orden de ejecución recomendado

### Fase 1 — Fixes globales en `app.css` (15 min)
1. Reemplazar `border-radius: var(--radius-*)` por `0` en: `.btn-ghost`, `.btn-danger`, `.ink-card`, `.ink-inline-alert`, `.toast-item`, `.trust-bar`
2. Añadir variable `--bg-muted: #F1F5F9` (alias de `--bg-surface-low`) para los archivos que la usan
3. Añadir `.modal-footer { margin: 16px -24px -24px; border-radius: 0; }` definitivo

### Fase 2 — Migración a CustomSelect (15 min)
1. [CotizacionDetalle.jsx:43,54](frontend/src/pages/CotizacionDetalle.jsx#L43) — 2 selects
2. [SuperadminPage.jsx:688](frontend/src/pages/SuperadminPage.jsx#L688) — 1 select

### Fase 3 — Fix de clases rotas (10 min)
1. Reemplazar `rounded-full` → `ink-row-btn` en CotizacionesPage:394 y GuiasPage:356
2. Remover `className="rounded"` en ConfiguracionPage:121
3. Reemplazar `font-mono-label` por estilos inline correctos en CotizacionesPage

### Fase 4 — Colores hardcodeados (20 min)
1. ProductosPage: extraer `dotColors`/`umColors` a constantes con variables CSS
2. CobranzaPage: `agingDot()` → variables
3. Dashboard:193 → `var(--color-warning)`

### Fase 5 — Inline styles → clases (45 min, opcional)
1. Crear `.modal-form`, `.modal-section`, `.config-tabs` en `app.css`
2. Refactor CotizacionesPage, GuiasPage, ConfiguracionPage

---

## Archivos en orden de prioridad

1. **[src/app.css](frontend/src/app.css)** — base del sistema, los fixes aquí se propagan
2. **[src/pages/CotizacionesPage.jsx](frontend/src/pages/CotizacionesPage.jsx)** — rounded-full + --bg-muted + inline
3. **[src/pages/GuiasPage.jsx](frontend/src/pages/GuiasPage.jsx)** — rounded-full + inline
4. **[src/pages/ConfiguracionPage.jsx](frontend/src/pages/ConfiguracionPage.jsx)** — inline masivo
5. **[src/pages/CotizacionDetalle.jsx](frontend/src/pages/CotizacionDetalle.jsx)** — selects nativos
6. **[src/pages/SuperadminPage.jsx](frontend/src/pages/SuperadminPage.jsx)** — selects + --bg-muted
7. **[src/pages/ProductosPage.jsx](frontend/src/pages/ProductosPage.jsx)** — colores
8. **[src/pages/CobranzaPage.jsx](frontend/src/pages/CobranzaPage.jsx)** — colores + inline
9. **[src/pages/Dashboard.jsx](frontend/src/pages/Dashboard.jsx)** — color hardcoded

---

## Resumen por severidad

| Severidad | Cantidad | Ejemplo |
|---|---|---|
| **CRÍTICO** | 4 | Variables CSS inexistentes, botones redondos en UI cuadrada, selects sin estilo |
| **ALTO** | 12 | `border-radius` en componentes principales, inline styles masivos |
| **MEDIO** | 15 | Colores hardcodeados, spacing inconsistente |
| **BAJO** | 14 | Mantenibilidad, código duplicado |

Tiempo total estimado de ejecución: **~2h** para todas las fases.
