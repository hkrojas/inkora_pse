# Plan de Diseño Unificado — Inkora

> Objetivo: dar vida al frontend con micro-interacciones coherentes, animaciones suaves y unificación visual — **respetando paleta y tipografía actuales** (Forest `#1C2D1C` + Lime `#8DC63F` + Orange `#E8A23A`, fuente Plus Jakarta Sans).

---

## 1. Diagnóstico — Qué está roto hoy

Auditoría del código actual revela tres causas raíz de la sensación "estática y desordenada":

### 1.1 El Spinner traiciona la marca
[Spinner.jsx:36-65](frontend/src/components/ui/Spinner.jsx#L36) usa **estilos inline con `borderRadius: 0`** — esquinas en pico cuando el sistema usa radios de 11–20px. Colores hardcodeados (`rgba(0,0,0,0.06)`) en vez de tokens. Resultado: una caja blanca genérica que parece de otra app.

### 1.2 Cero animaciones más allá del propio spinner
Solo existe un keyframe (`spinner-bar-slide`). No hay:
- Transiciones de entrada para listas (productos, cotizaciones)
- Hover states animados en filas/cards
- Animación de cambio de ruta
- Skeleton loaders (todo es "spinner ciego")
- Estados de focus animados en inputs
- Feedback de press en botones
- Animaciones de modal/drawer
- Stagger en aparición de elementos

### 1.3 Estilos inline rompen la coherencia
Componentes mezclan tokens con valores literales. Ej. en Spinner: `padding: '32px 48px'`, `gap: '20px'`. Si mañana cambia la escala de espaciado, hay que tocar JS además del CSS.

---

## 2. Principios Rectores

1. **No reinventar la marca** — paleta, tipografía y radios actuales se mantienen.
2. **Animar la información, no los adornos** — cada animación responde a un cambio de estado real (carga, hover, focus, navegación).
3. **Duración corta, easing suave** — usar los `--ease-*` ya definidos. Nunca animaciones >500ms en interacciones, nunca <120ms (se pierden).
4. **Respetar `prefers-reduced-motion`** — ya está cubierto en [tokens.css:316](frontend/src/styles/tokens.css#L316), nuevas animaciones deben caer dentro de esa regla.
5. **Tokens, no literales** — toda nueva sombra, color, radio o duración pasa por una variable CSS.

---

## 3. Sistema de Animación — Tokens nuevos

Agregar a [tokens.css](frontend/src/styles/tokens.css) en la sección `:root`:

```css
/* === Duraciones === */
--duration-instant: 80ms;    /* feedback de press */
--duration-fast: 150ms;      /* hover, focus */
--duration-base: 220ms;      /* la mayoría de transiciones */
--duration-slow: 360ms;      /* modales, page transitions */
--duration-deliberate: 520ms; /* hero, splash */

/* === Combinaciones canónicas === */
--motion-press: transform var(--duration-instant) var(--ease-press);
--motion-hover: all var(--duration-fast) var(--ease-out);
--motion-fade: opacity var(--duration-base) var(--ease-out);
--motion-slide: transform var(--duration-base) var(--ease-out),
                opacity var(--duration-base) var(--ease-out);
--motion-spring: transform var(--duration-base) var(--ease-spring);
```

Eliminar `borderRadius: 0` de Spinner. Usar `var(--radius-lg)`.

---

## 4. Inventario de Animaciones a Crear

### 4.1 `@keyframes` globales (en `globals.css`)

| Nombre | Propósito | Duración | Easing |
|---|---|---|---|
| `fade-in` | Entrada genérica | base | ease-out |
| `fade-in-up` | Entrada de cards/items con leve subida | base | ease-out |
| `fade-in-down` | Entrada de notificaciones desde arriba | base | ease-out |
| `slide-in-right` | Drawers laterales | slow | ease-out |
| `slide-out-right` | Cierre de drawers | base | ease-in |
| `scale-in` | Modales (95% → 100% con fade) | slow | ease-spring |
| `pulse-soft` | Indicador de "live"/online | 2s loop | ease-in-out |
| `shimmer` | Skeleton loaders | 1.6s loop | linear |
| `stagger-fade` | Lista que aparece secuencial | base | ease-out |
| `bar-progress` | Reemplazo del `spinner-bar-slide` actual con curva mejor | 1.4s loop | ease-in-out |

### 4.2 Micro-interacciones por componente

| Componente | Estado | Animación |
|---|---|---|
| Botón primario | hover | `transform: translateY(-1px)`, sombra aumenta |
| Botón primario | active/press | `transform: scale(0.97)` con `--duration-instant` |
| Botón primario | loading | spinner inline, label oculto suavemente |
| Card / fila lista | hover | `box-shadow: var(--shadow-card)`, `translateY(-2px)` |
| Input | focus | borde anima a `--color-primary`, `box-shadow: var(--shadow-focus)` |
| Tab activo | switch | underline animado con `transform-origin` |
| Sidebar item | hover | fondo aparece con fade, indicador izquierdo crece |
| Sidebar item | active | indicador lime se desliza desde arriba |
| Toast | enter | `slide-in-right` + scale 95→100 |
| Toast | exit | fade + slide-out |
| Modal | open | overlay fade, panel `scale-in` (spring) |
| Dropdown | open | fade-in-down con `transform-origin: top` |
| Checkbox/radio | check | rebote suave del check con spring |
| Tabla row | delete | colapsa altura + fade |
| Empty state | mount | ilustración fade-in-up con stagger |

---

## 5. Loading States — Reemplazo del Spinner

El spinner actual no es contextual: aparece igual cargando lista vs creando cotización vs validando login. Plan:

### 5.1 Skeleton loaders por contexto

Crear `frontend/src/components/ui/Skeleton.jsx` con variantes:
- `<SkeletonRow />` — fila de tabla (productos, cotizaciones)
- `<SkeletonCard />` — card de dashboard
- `<SkeletonForm />` — formulario completo (nueva cotización)
- `<SkeletonText lines={3} />` — bloques de texto

Todos usan animación `shimmer` con gradient: `linear-gradient(90deg, var(--color-surface-soft) 0%, var(--color-surface-muted) 50%, var(--color-surface-soft) 100%)`.

### 5.2 Spinner refinado para casos genuinos

Cuando NO se puede skeleton (ej. acción transitoria como guardado), el `<Spinner size="lg">`:
- Card con `var(--radius-lg)` (no más esquinas en pico)
- Borde `var(--color-border)`
- Sombra `var(--shadow-card)`
- Indicator dot pulsante en lime sobre el label
- Barra de progreso con gradiente `var(--grad-press)` (forest → lime → orange)
- Sustituir estilos inline por clase `.spinner-panel` en globals.css

### 5.3 Inline spinner para botones

Cuando un botón está procesando: el texto se oculta con `--motion-fade`, aparece spinner inline en su lugar. Botón mantiene su ancho (no se contrae) usando `min-width` calculado.

---

## 6. Transiciones de Ruta

Hoy el cambio de ruta es instantáneo y abrupto. Plan:

1. Envolver `<Routes>` en wrapper con `key={location.pathname}`.
2. Aplicar `fade-in-up` (200ms, ease-out) al contenido entrante.
3. Mantener sidebar y topbar fijos — solo el contenido principal anima.
4. Para navegación dentro de la misma sección (ej. lista → detalle), usar `slide-in-right` para sugerir profundidad.

Implementación con CSS puro (no instalar `framer-motion` para no engrosar el bundle de 611 KB que ya hay que reducir).

---

## 7. Consistencia Estructural

### 7.1 Eliminar estilos inline de componentes UI

Auditoría:
- [Spinner.jsx](frontend/src/components/ui/Spinner.jsx) — ~15 propiedades inline → mover a `.spinner-panel` en globals.css
- Verificar otros componentes en `components/ui/` con misma metodología

### 7.2 Escala de espaciado canónica

Definir si no existen ya:
```css
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
--space-10: 40px;
--space-12: 48px;
```

Reemplazar literales en JSX y CSS. Esto resuelve los espaciados desordenados visibles en los tabs ("+ Nueva cotización | Historial | Emitidas SUNAT") donde íconos y texto no respiran consistentemente.

### 7.3 Header de página estandarizado

Todas las páginas deben usar el mismo patrón visual:
```
[Título grande]
[Subtítulo gris]
[Acción primaria a la derecha]
─────────────────────  (línea sutil)
[Contenido]
```

Esto ya parece estar en Productos pero NO en Cotizaciones (la lista de tabs aparece pegada al contenido sin jerarquía).

---

## 8. Mapa de Implementación por Fases

### Fase 1 — Fundamentos (impacto inmediato)
- [ ] Agregar tokens de duración y motion canónicos en `tokens.css`
- [ ] Crear `@keyframes` globales en `globals.css`
- [ ] Refactor de `Spinner.jsx`: eliminar inline styles, aplicar tokens
- [ ] Actualizar barra de progreso del spinner con gradiente de marca
- [ ] Verificar que `prefers-reduced-motion` cubre todo lo nuevo

### Fase 2 — Loading states contextuales
- [ ] Crear `Skeleton.jsx` con variantes Row/Card/Form/Text
- [ ] Aplicar skeletons en: ProductosPage, CotizacionesPage, Dashboard
- [ ] Inline spinner en `<Button>` (estado loading)

### Fase 3 — Micro-interacciones de UI
- [ ] Hover/press en botones (todos los variantes)
- [ ] Hover en filas de listas (productos, cotizaciones, clientes)
- [ ] Focus animado en inputs/selects
- [ ] Sidebar items: hover + indicador active animado
- [ ] Tabs: underline animado al cambiar

### Fase 4 — Transiciones globales
- [ ] Wrapper de page-transition con CSS keyframes
- [ ] Modal/dialog open/close con scale-in y overlay fade
- [ ] Toast/notification slide-in-right
- [ ] Dropdown con fade-in-down

### Fase 5 — Pulido de páginas específicas
- [ ] CotizacionesPage: ordenar la barra de tabs (íconos + texto alineados)
- [ ] Header de página unificado (título + subtítulo + acción + separador)
- [ ] Stagger en aparición de tarjetas de Dashboard
- [ ] Empty states con ilustración + animación de entrada

### Fase 6 — Limpieza
- [ ] Auditoría: ningún componente UI con `style={{...}}` que no sea dinámico
- [ ] Reemplazar literales de espaciado/radio/sombra por tokens
- [ ] Confirmar que `dist/assets/index.css` no creció >15% post-cambios

---

## 9. Métricas de Éxito

| Métrica | Antes | Objetivo |
|---|---|---|
| Estilos inline en componentes UI | ~50+ | <10 (solo dinámicos) |
| Estados con feedback animado | 1 (spinner) | 20+ |
| Loading skeletons | 0 | 4 variantes |
| Animación en cambio de ruta | No | Sí |
| Bundle CSS gzipped | ~12 KB | <16 KB (no más de +33%) |
| Lighthouse "Avoid non-composited animations" | — | 100 |
| Lighthouse "Performance" | actual | sin regresión |

---

## 10. Reglas de Animación — Cheat sheet para futuras features

```
✓ Toda animación ≥80ms y ≤520ms
✓ Hover/focus: usar --ease-out
✓ Press/click: usar --ease-press, --duration-instant
✓ Modal/drawer: usar --ease-spring si es entrada
✓ Animar solo: opacity, transform, filter, backdrop-filter, color, border-color, box-shadow
✗ NUNCA animar: width, height, top, left, margin (causan reflow)
✓ Si necesitas animar tamaño: usar transform: scale() con transform-origin
✓ stagger entre items: 30-60ms de delay incremental, máximo 8 items animados
✗ No agregar animaciones decorativas sin propósito (rotaciones eternas, parallax)
```

---

## 11. Decisiones Pendientes

1. **¿Instalar `framer-motion`?** Recomendación: **no**. CSS puro + `<CSSTransition>` (de `react-transition-group`, ya muy ligero) cubre todos los casos. `framer-motion` añade ~30 KB gzipped, peso que ahora mismo no podemos justificar dado el bundle de 611 KB ya identificado como problema en el plan de optimización backend.

2. **¿Skeleton vs spinner por defecto?** Skeleton siempre que se conozca la forma del contenido futuro. Spinner solo para acciones cuyo resultado no muestra contenido (ej. guardar, cerrar sesión).

3. **¿Animar la sidebar al colapsar?** Sí, con transform + opacity en items. Width del contenedor anima con `--duration-base`, los labels desaparecen con `--motion-fade` 50ms antes para evitar squish visual.

---

## Anexo — Archivos que se tocan

| Archivo | Cambios |
|---|---|
| [tokens.css](frontend/src/styles/tokens.css) | + tokens de duración y motion |
| [globals.css](frontend/src/styles/globals.css) | + keyframes globales, + clase `.spinner-panel`, + clases de transición |
| [Spinner.jsx](frontend/src/components/ui/Spinner.jsx) | refactor completo: inline → clases |
| `components/ui/Skeleton.jsx` | **nuevo** |
| `components/ui/PageTransition.jsx` | **nuevo** |
| Páginas (`Dashboard`, `Cotizaciones`, `Productos`, `Clientes`) | aplicar skeletons + page-transition |
| `Sidebar.jsx` | hover + indicador active animado |

Estimado total: ~12-15 archivos modificados, 2-3 archivos nuevos, ~600 líneas de CSS adicionales (gzipped: +3-4 KB).
