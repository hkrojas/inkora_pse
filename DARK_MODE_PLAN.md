# Plan — Modo oscuro vanguardista "Inkora Nocturne"

> **Estado:** propuesta — pendiente de aprobación.
> **Objetivo:** diseñar un dark mode con identidad propia (no la inversión clásica blanco→negro), coherente con el lenguaje Inkora (mono-typography, brutalismo geométrico de bordes 0px, acento índigo/violeta) y que se sienta moderno, pulcro y técnico.

---

## Diagnóstico del estado actual

`app.css` ya define un selector `[data-theme='dark']` (líneas 102-134) con tokens básicos (fondo `#0B0B14`, superficie `#1A1A2E`, primario `#818CF8`). Pero:

- **No hay toggle UI** — el usuario nunca lo activa.
- **No hay JS** que aplique `data-theme` ni persista preferencia.
- Tokens definidos solo cubren ~20 variables; cientos de componentes hardcodean colores blancos (`#fff`, `#F8FAFC`, `#E2E8F0`) en estilos inline (ClientCombobox, ProductLineCell, DatePicker, CustomSelect, Modal, etc.).
- Las `box-shadow` brutalist `4px 4px 0px rgba(99,102,241,1)` se ven mal sobre fondo oscuro (necesitan glow, no offset sólido).
- Background grid `linear-gradient(rgba(99,102,241,0.035)...)` es muy débil sobre superficie clara — sobre dark debe levantarse a `~0.06` para mantener legibilidad.

---

## Concepto de diseño — "Nocturne"

No queremos un "modo noche" oficinista. Queremos algo que se sienta como un **estudio de impresión a media luz**: superficies estratificadas con profundidad, acentos que brillan suavemente (no neón chillón), tipografía mono que respira en el negro.

### Principios

1. **Profundidad estratificada, no plana.** Cuatro niveles de "negro" — desde el lienzo (`#08070D`) hasta superficies elevadas (`#1F1B33`). El ojo percibe jerarquía sin necesidad de bordes pesados.
2. **Glow en lugar de drop-shadow sólido.** En light mode usamos `4px 4px 0px #6366F1` (sello brutalist). En dark, el offset sólido se ve sucio — lo reemplazamos por glow `0 0 24px rgba(129,140,248,0.35)` cuando hay hover/focus, manteniendo el offset solo en estados activos.
3. **Acento índigo luminoso.** El primario se mueve de `#2563EB` (azul) a `#A5B4FC` (lavanda luminosa) — más saturada y brillante para atravesar el fondo oscuro sin quemar.
4. **Glassmorphism selectivo.** Solo el header del sidebar y los modales usan `backdrop-filter: blur(20px)` con superficie semitransparente. Cards normales se mantienen sólidas (legibilidad > efectismo).
5. **Bordes "hairline" iluminados.** En light usamos `1.5px solid #E2E8F0`. En dark cambiamos a `1px solid rgba(255,255,255,0.08)` + `box-shadow: inset 0 1px 0 rgba(255,255,255,0.04)` — simula que el objeto está iluminado desde arriba.
6. **Grid de fondo sutilmente animado.** Mantenemos la grid 32px pero con un gradiente cónico que rota ultra-lento (60s) en background-position — apenas perceptible, da sensación de "vivo" sin distraer.
7. **Transición de tema con cross-fade.** Al togglear: `transition: background 350ms, color 250ms, border-color 250ms` aplicado a `*` por 400ms (clase `.theme-transitioning`), luego se remueve para que las animaciones normales no sufran.

### Paleta propuesta (tokens "Nocturne")

```css
[data-theme='dark'] {
  /* Lienzo y superficies (4 niveles) */
  --bg-canvas:        #08070D;   /* fondo absoluto */
  --bg-primary:       #0E0C18;   /* body background */
  --bg-surface-low:   #14111F;   /* secciones recesivas */
  --bg-surface:       #1A1628;   /* cards, modales */
  --bg-surface-high:  #221C36;   /* hover states */
  --bg-surface-glass: rgba(26,22,40,0.72);  /* sidebar/modal con blur */

  /* Acento índigo luminoso */
  --ink-primary:           #A5B4FC;   /* lavanda luminosa (era #2563EB) */
  --ink-primary-glow:      rgba(165,180,252,0.45);
  --ink-primary-container: rgba(165,180,252,0.10);
  --ink-secondary:         #C4B5FD;   /* violeta suave */
  --ink-accent-cyan:       #67E8F9;   /* acento alterno para alertas info */

  /* Texto con jerarquía generosa */
  --text-primary:    #F4F3FF;        /* casi blanco con tinte lavanda */
  --text-secondary:  rgba(244,243,255,0.62);
  --text-tertiary:   rgba(244,243,255,0.38);
  --text-quaternary: rgba(244,243,255,0.22);

  /* Bordes "hairline iluminados" */
  --border-subtle:   rgba(255,255,255,0.06);
  --border-strong:   rgba(255,255,255,0.12);
  --border-brand:    rgba(165,180,252,0.35);
  --border-edge-top: inset 0 1px 0 rgba(255,255,255,0.04);

  /* Sombras = glow */
  --shadow-sm:    0 0 12px rgba(0,0,0,0.45);
  --shadow-md:    0 4px 24px rgba(0,0,0,0.55);
  --shadow-lg:    0 8px 40px rgba(0,0,0,0.65);
  --shadow-glow-sm: 0 0 16px rgba(165,180,252,0.20);
  --shadow-glow-md: 0 0 28px rgba(165,180,252,0.32);
  --shadow-glow-lg: 0 0 48px rgba(165,180,252,0.40);
  --shadow-focus:   0 0 0 3px rgba(165,180,252,0.30), 0 0 24px rgba(165,180,252,0.20);

  /* Estados semánticos atenuados (no fluo) */
  --color-success:    #4ADE80;
  --color-success-bg: rgba(74,222,128,0.10);
  --color-warning:    #FBBF24;
  --color-warning-bg: rgba(251,191,36,0.10);
  --color-error:      #F87171;
  --color-error-bg:   rgba(248,113,113,0.10);

  /* Gradiente Nocturne */
  --inkora-gradient: linear-gradient(135deg, #6366F1 0%, #A78BFA 50%, #67E8F9 100%);
  --inkora-gradient-mesh:
    radial-gradient(at 20% 0%, rgba(99,102,241,0.18) 0px, transparent 50%),
    radial-gradient(at 80% 100%, rgba(167,139,250,0.18) 0px, transparent 50%);
}
```

---

## Fases

### Fase 1 — Tokens y base global (CSS)

**Archivo:** `frontend/src/app.css`

- [ ] **Reemplazar** el bloque `[data-theme='dark']` actual (líneas 102-134) por la paleta Nocturne completa de arriba.
- [ ] Agregar al `:root` light mode los tokens nuevos que faltan en ambos temas (`--bg-canvas`, `--shadow-glow-*`, `--border-edge-top`) con valores neutros para que no rompan light.
- [ ] Aumentar la grid de fondo en dark a `rgba(99,102,241,0.06)` para que no desaparezca.
- [ ] Añadir `html.theme-transitioning *, html.theme-transitioning *::before, html.theme-transitioning *::after { transition: background-color 350ms ease, color 250ms ease, border-color 250ms ease, box-shadow 250ms ease !important; }`
- [ ] Agregar `@media (prefers-color-scheme: dark)` que aplique `data-theme='dark'` solo si **no** hay preferencia manual guardada (lo gestiona el JS).

### Fase 2 — Theme controller (JS + Context)

**Archivos nuevos:**
- `frontend/src/context/ThemeContext.jsx` — provee `{ theme: 'light'|'dark'|'system', resolvedTheme, setTheme }`.
- `frontend/src/lib/utils/theme.js` — helpers (`applyTheme`, `getStoredTheme`, `getSystemTheme`).

Comportamiento:
- Lee de `localStorage.theme` ('light' | 'dark' | 'system'). Default: `'system'`.
- Aplica `document.documentElement.dataset.theme = resolvedTheme`.
- Suscribe a `matchMedia('(prefers-color-scheme: dark)')` y reacciona.
- Antes del primer render, inyecta un script bloqueante en `index.html` para evitar FOUC (Flash of Unstyled Content):
  ```html
  <script>
    (function(){
      var t = localStorage.getItem('theme') || 'system';
      var m = window.matchMedia('(prefers-color-scheme: dark)').matches;
      var r = t === 'system' ? (m ? 'dark' : 'light') : t;
      document.documentElement.dataset.theme = r;
    })();
  </script>
  ```
- En `App.jsx` envolver con `<ThemeProvider>`.

### Fase 3 — Toggle UI vanguardista

**Archivo:** nuevo `frontend/src/components/ui/ThemeToggle.jsx`. Ubicación: en el footer del `Sidebar.jsx`.

Diseño:
- **No** un switch convencional. Pill con tres pestañas: `[ ☀ ]  [ ◐ ]  [ ☾ ]` (light / system / dark).
- Indicador deslizante con `position: absolute` y `transform: translateX()` animado (`cubic-bezier(0.34,1.56,0.64,1)` — overshoot juguetón).
- Color del indicador toma el `--inkora-gradient` actual del tema → siempre se siente vivo.
- Hover en cada icono → leve glow `box-shadow: 0 0 12px var(--ink-primary-glow)`.
- Persistencia + accesibilidad: `aria-label`, `role="radiogroup"`, navegable con flechas.

Variante secundaria (atajo): `Ctrl+Shift+D` toggle rápido entre light/dark (sin pasar por system).

### Fase 4 — Migrar estilos hardcoded a tokens

Esto es el trabajo grueso. Los componentes con estilos inline blancos `#fff`/`#F8FAFC`/`#E2E8F0` rompen sobre dark.

**Componentes prioritarios** (orden por visibilidad):
1. [ ] `ClientCombobox.jsx` — inputs, dropdown portal, badges
2. [ ] `ProductLineCell.jsx` — inputs Código/Descripción, dropdown
3. [ ] `CustomSelect.jsx` — trigger button, dropdown
4. [ ] `DatePicker.jsx` — trigger, calendario
5. [ ] `Modal.jsx` — overlay + caja
6. [ ] `Sidebar.jsx` — fondo, items
7. [ ] `Toast.jsx` — fondo, bordes
8. [ ] `Badge.jsx` — variantes
9. [ ] `EmptyState.jsx`
10. [ ] `Spinner.jsx`
11. [ ] `Tables` y `cards` específicos de páginas (CotizacionesPage, DocumentList, ComprobanteNuevoPage)

**Patrón de migración**:
```jsx
// ❌ Antes
style={{ background: '#fff', border: '1.5px solid #E2E8F0', color: '#0F172A' }}

// ✅ Después
style={{
  background: 'var(--bg-surface)',
  border: '1px solid var(--border-subtle)',
  boxShadow: 'var(--border-edge-top)',
  color: 'var(--text-primary)',
}}
```

Para los inputs activos en light usábamos `border: '1.5px solid #C7D2FE'` — en dark mapearemos a `var(--border-brand)` + `box-shadow: var(--shadow-glow-sm)`.

### Fase 5 — Refinamientos vanguardistas (lo que distingue Nocturne del dark genérico)

- [ ] **Backdrop mesh sutil**: en `body::before` agregar el `--inkora-gradient-mesh` con `opacity: 0.6` solo en dark, posición fija, `pointer-events: none`. Da una atmósfera sin tapar contenido.
- [ ] **Glow en focus de inputs**: cualquier `:focus` dentro de `.input` aplica `--shadow-focus`.
- [ ] **Botones primarios con sheen**: `.btn-primary` en dark tiene `background: linear-gradient(135deg, #6366F1, #A78BFA)` con `box-shadow: var(--shadow-glow-md)` en hover (en lugar del 4x4 offset).
- [ ] **Selección de texto**: `::selection { background: rgba(165,180,252,0.30); color: #fff; }` (ya existe lógica similar en light).
- [ ] **Scrollbar custom**: track invisible, thumb `var(--border-strong)`, hover `var(--ink-primary)`.
- [ ] **Estados activos de tablas**: row hover en dark = `background: rgba(165,180,252,0.04)` (no la inversión del light).
- [ ] **Iconos de Lucide**: en dark, `color: var(--text-secondary)` por defecto (en light van más oscuros).
- [ ] **PDF preview**: el iframe del PDF mantiene fondo blanco (los PDFs son blancos por naturaleza); agregar marco oscuro `padding: 12px; background: var(--bg-surface-low);` para que no "queme".

### Fase 6 — QA visual sistemático

Checklist por pantalla, validando ambos temas:

- [ ] Login / Register
- [ ] Dashboard
- [ ] Cotizaciones (lista + crear/editar)
- [ ] Comprobantes (lista + crear/editar + detalle)
- [ ] Guías (lista + crear/editar + detalle)
- [ ] Clientes (lista + modal)
- [ ] Productos (lista + modal)
- [ ] Pagos
- [ ] Reportes
- [ ] Configuración / Superadmin
- [ ] PDF preview
- [ ] Modales de confirmación (anular, eliminar)
- [ ] Toast en cada variante (success, error, warn, info)
- [ ] Estados de carga (Spinner, EmptyState)

Para cada pantalla revisar:
- Contraste WCAG AA (texto sobre fondo)
- Estados hover/focus/disabled
- Bordes visibles pero no agresivos
- Sin "flashes" blancos al togglear

### Fase 7 — Build limpio y verificación final

- [ ] `npm run build` sin errores ni warnings nuevos.
- [ ] Smoke en navegador: togglear ~10 veces; no debe haber FOUC ni saltos de layout.
- [ ] Lighthouse en dark: contraste ≥ 4.5:1 en texto, ≥ 3:1 en UI.
- [ ] Probar en navegador con `prefers-color-scheme: dark` activo (DevTools → Rendering).

---

## Decisiones que necesito confirmar antes de ejecutar

1. **¿Mantenemos `system` como default**, o forzamos light hasta que el usuario opte? (Sugiero `system` — moderno y respetuoso.)
2. **¿Toggle visible en sidebar siempre, o solo en submenu de perfil?** (Sugiero footer del sidebar — siempre 1 click.)
3. **¿Atajo `Ctrl+Shift+D`?** (Inofensivo, lo agregaría.)
4. **¿Migración de estilos inline ahora o gradual?** Hay ~30 componentes con colores hardcoded. Opciones:
   - **(A) Big-bang**: una sola PR grande migrando todo. Tarda ~1 día completo, pero deja todo limpio.
   - **(B) Por fases**: priorizar los 5 componentes más visibles ahora; el resto se migra en sprints futuros. Riesgo: en el interín hay pantallas con look mixto si el usuario activa dark.
   - Mi recomendación: **(A) Big-bang** — el dark mode no debe lanzarse "a medias" porque las pantallas rotas matan la percepción de calidad.
5. **¿PDFs y plantillas de email se quedan en light** siempre? (Sí — son documentos impresos/enviados, no UI.)

---

## Estimación

| Fase | Esfuerzo |
|------|----------|
| 1. Tokens + base CSS | ~1h |
| 2. Theme controller (JS) | ~1h |
| 3. Toggle UI | ~1.5h |
| 4. Migración de hardcoded styles | ~5-7h ⚠ |
| 5. Refinamientos vanguardistas | ~2h |
| 6. QA visual | ~2h |
| 7. Build + smoke final | ~30min |
| **Total** | **~12-15h** |

La Fase 4 es el grueso. Si decides B (gradual) bajamos a ~5-6h iniciales, pero queda deuda visible.

---

## Riesgos

- **FOUC**: si el script bloqueante en `index.html` se omite, hay flash blanco al cargar. **Mitigación**: incluirlo desde Fase 2.
- **Componentes inline imposibles de migrar limpiamente**: algunos usan colores conditional (ej. `color: error ? '#DC2626' : '#0F172A'`). Hay que reescribirlos a tokens semánticos (`var(--color-error)` / `var(--text-primary)`).
- **PDFs / preview iframes**: el `<iframe>` del PDF no hereda tema; mostrar marco contextual.
- **Imágenes/logos**: si el logo Inkora es PNG con fondo blanco, en dark se ve mal. **Mitigación**: usar SVG o tener variante dark del logo.
- **Confirmar legibilidad de gradientes en texto**: `background-clip: text` con gradientes claros sobre dark es legible; sobre light a veces no.

---

## Solicitud de aprobación

¿Apruebas el concepto Nocturne y el alcance de fases? Si hay algo del concepto que prefieres distinto (más conservador, más radical, o paleta diferente), dímelo y reescribo antes de tocar código.
