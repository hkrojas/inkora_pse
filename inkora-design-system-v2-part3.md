
---

## 10. Trust Signals

### Trust Bar
```css
.trust-bar {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 12px; border-radius: var(--radius-sm);
}
.trust-bar--light { background: #EEF2FF; }
.trust-bar--light span { font-family: var(--font-body); font-size: 10px; color: #4338CA; }
.trust-bar--dark { background: rgba(129,140,248,0.06); border: 1px solid rgba(129,140,248,0.08); }
.trust-bar--dark span { font-family: var(--font-body); font-size: 10px; color: rgba(255,255,255,0.35); }

.trust-dot {
  width: 6px; height: 6px; border-radius: 50%; background: #22C55E;
  animation: trustPulse 2s infinite;
}
@keyframes trustPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(34,197,94,0.3); }
  50% { box-shadow: 0 0 0 5px rgba(34,197,94,0); }
}
```
**Contenido:** "SUNAT activa · Cifrado E2E · 99.2% aceptación"
**Ubicación:** Login, Dashboard top bar, Emisión de factura.

---

## 11. Badges y Estados

```css
.badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 8px; border-radius: 4px;
  font-family: var(--font-mono); font-size: 9px; font-weight: 700;
  letter-spacing: 0.5px; text-transform: uppercase;
}
.badge--success { background: var(--color-success-bg); color: var(--color-success); }
.badge--warning { background: var(--color-warning-bg); color: var(--color-warning); }
.badge--error   { background: var(--color-error-bg);   color: var(--color-error); }
.badge--info    { background: var(--color-info-bg);    color: var(--color-info); }
.badge--neutral { background: var(--bg-muted); color: var(--text-secondary); }
.badge--outline {
  background: transparent; border: 1.5px solid var(--border-raw);
  color: var(--text-primary); border-radius: 20px;
}
```

### Mapeo de estados SUNAT

| Estado | Badge | Color |
|--------|-------|-------|
| Aceptada | `badge--success` | Verde |
| Pendiente de envío | `badge--warning` | Ámbar |
| Rechazada | `badge--error` | Rojo |
| Anulada | `badge--error` | Rojo |
| Observada | `badge--warning` | Ámbar |
| Baja solicitada | `badge--info` | Cyan |
| Borrador | `badge--neutral` | Gris |

---

## 12. Tablas

```css
.table-inkora { width: 100%; border-collapse: collapse; font-family: var(--font-body); font-size: 13px; }

.table-inkora thead th {
  font-family: var(--font-mono); font-size: 9px; font-weight: 700;
  letter-spacing: 1.5px; text-transform: uppercase; color: var(--text-secondary);
  padding: 12px 16px; text-align: left; border-bottom: 2px solid var(--border-raw);
}

.table-inkora tbody td {
  padding: 12px 16px; border-bottom: 1px solid var(--border-subtle);
  color: var(--text-primary); vertical-align: middle;
}
.table-inkora tbody tr:hover { background: var(--bg-muted); }
.table-inkora .col-amount { text-align: right; font-family: var(--font-mono); font-size: 13px; }
.table-inkora .col-serie { font-family: var(--font-mono); font-size: 12px; color: var(--text-brand); font-weight: 500; }
```

### Reglas de tablas
- Headers: Space Mono uppercase
- Montos: Space Mono, alineados derecha
- Series: Space Mono, color brand
- Hover: fondo muted sutil
- **Nunca** bordes verticales. **Nunca** zebra striping. Máximo 20 filas/página.

---

## 13. Sidebar y Navegación

### Sidebar
```css
.sidebar {
  width: 240px; /* Colapsada: 64px */
  height: 100vh; background: var(--bg-surface);
  border-right: 1px solid var(--border-subtle);
  display: flex; flex-direction: column; padding: 16px 0;
  transition: width var(--transition-slow);
}
.sidebar-logo {
  padding: 8px 20px 16px; font-family: var(--font-brand);
  font-size: 24px; font-weight: 800; color: var(--text-primary);
}
.sidebar-logo em { font-style: normal; color: var(--text-brand); }

.sidebar-item {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 20px; font-family: var(--font-body);
  font-size: 13px; font-weight: 500; color: var(--text-secondary);
  cursor: pointer; transition: all var(--transition-fast);
  border-left: 3px solid transparent;
}
.sidebar-item:hover { background: var(--bg-muted); color: var(--text-primary); }
.sidebar-item.active {
  background: rgba(37,99,235,0.08); color: var(--text-brand);
  border-left-color: var(--text-brand); font-weight: 600;
}

[data-theme="dark"] .sidebar { background: var(--bg-primary); }
[data-theme="dark"] .sidebar-item.active {
  background: rgba(129,140,248,0.08); color: var(--text-brand);
  border-left-color: var(--text-brand);
}
```

### Top Bar
```css
.topbar {
  height: 56px; background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
  display: flex; align-items: center; justify-content: space-between; padding: 0 24px;
}
.topbar-breadcrumb {
  font-family: var(--font-mono); font-size: 10px;
  letter-spacing: 1px; text-transform: uppercase; color: var(--text-tertiary);
}
.topbar-breadcrumb .current { color: var(--text-primary); font-weight: 700; }
```

### Módulos de navegación

| Icono (Lucide) | Módulo | Ruta |
|----------------|--------|------|
| `LayoutDashboard` | Dashboard | `/dashboard` |
| `FileText` | Comprobantes | `/comprobantes` |
| `FilePlus` | Nueva Factura | `/comprobantes/nuevo` |
| `Users` | Clientes | `/clientes` |
| `Package` | Productos | `/productos` |
| `BarChart3` | Reportes | `/reportes` |
| `Settings` | Configuración | `/configuracion` |

---

## 14. Layout del Dashboard

### Estructura
```
┌──────────────────────────────────────────────────┐
│ Sidebar (240px)  │  Top Bar (56px)               │
│                  ├───────────────────────────────│
│  ink[ora.]       │  Dashboard > Resumen          │
│                  │                               │
│  📊 Dashboard    │  ┌─────┐ ┌─────┐ ┌─────┐ ┌──┐│
│  📄 Comprobantes │  │Stat │ │Stat │ │Stat │ │St││
│  ➕ Nueva        │  └─────┘ └─────┘ └─────┘ └──┘│
│  👥 Clientes     │                               │
│  📦 Productos    │  ┌──────────────┐ ┌─────────┐│
│  📈 Reportes     │  │  Chart       │ │ Recent  ││
│  ⚙️ Config       │  │              │ │ Activity││
│                  │  └──────────────┘ └─────────┘│
│  ──────          │                               │
│  ────            │  ┌──────────────────────────┐│
│  ───             │  │  Últimos comprobantes     ││
│                  │  │  (tabla)                  ││
└──────────────────────────────────────────────────┘
```

### Stat Cards del Dashboard

| Métrica | Valor ejemplo | Psicología |
|---------|---------------|------------|
| Facturas hoy | 847 | Anchoring — número grande primero |
| Tiempo emisión | 3.2s | Endowment — "tu velocidad" |
| Aceptación SUNAT | 99.2% | Trust — refuerza confianza |
| Errores hoy | 0 | Loss Aversion — "no has perdido nada" |

### Endowment Preview (Dark Theme)
```css
.preview-chart {
  display: flex; align-items: flex-end; gap: 3px; height: 32px; margin-top: 10px;
}
.preview-chart .bar {
  width: 100%; background: rgba(129,140,248,0.15);
  border-radius: 2px 2px 0 0; transition: height var(--transition-slow);
}
.preview-chart .bar.active { background: #818CF8; }
```

---

## 15. Pantalla de Login

### Estructura
Layout split asimétrico: **1.15fr (izquierda) + 1fr (derecha)**
- Izquierda: Brand + Social Proof + Testimonial
- Derecha: Formulario de acceso

### Elementos por tema

| Elemento | Light | Dark |
|----------|-------|------|
| Logo | Syne 64px, negro + azul | Syne 64px, blanco + gradiente lavender |
| Líneas Raw | 3 líneas negras decrecientes | 3 líneas blancas semitransparentes |
| Tagline | Space Mono 10px, gris | Space Mono 10px, blanco 30% |
| Social Proof | Card borde azul izquierdo | Card con preview dashboard |
| Contador | Space Mono 26px, azul | Space Mono 18px, blanco |
| Avatares | Círculos colores sólidos | Círculos colores sólidos |
| Testimonio | Card borde sutil + estrellas | Card borde rgba + estrellas |
| Form title | "Bienvenido de vuelta 👋" | "Bienvenido de vuelta 👋" |
| Inputs | Underline 2px negro | Underline 1.5px rgba blanco |
| CTA | Negro sólido → hover azul | Gradiente indigo → hover glow |
| CTA texto | "Acceder a mis facturas →" | "Acceder a mi dashboard →" |
| Alt button | Borde 2px negro | Borde 1px rgba blanco |
| Trust bar | Fondo azul claro | Fondo indigo 6% |
| Fondo | `#FAFAF7` (papel cálido) | `#0B0B14` + aurora glows |

### Formulario
- **Campo 1:** RUC — label Space Mono uppercase, input Space Mono 14px
- **Campo 2:** Contraseña — label Space Mono uppercase, input password
- **Checkbox:** "Recordar dispositivo" (pre-marcado — Commitment bias)
- **Link:** "¿Olvidaste tu clave?"
- **CTA primario:** Botón principal
- **Separador:** "o"
- **CTA secundario:** "Ingresar con Clave SOL"
- **Link registro:** "¿No tienes cuenta? Solicitar acceso →"
- **Trust bar:** Punto verde animado + texto

---

## 16. Animaciones y Transiciones

### Duraciones

| Tipo | Duración | Easing | Uso |
|------|----------|--------|-----|
| Micro-interacción | 150ms | ease | Hover botones, focus inputs |
| Transición UI | 200ms | ease | Cambio de estados |
| Animación entrada | 300ms | ease-out | Modales, dropdowns, toasts |
| Animación página | 400ms | ease-in-out | Transición entre vistas |

### Animaciones clave
```css
/* Entrada de tarjetas (stagger +50ms por card) */
@keyframes cardEnter {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Skeleton loading */
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
.skeleton {
  background: linear-gradient(90deg, var(--bg-muted) 25%, var(--border-subtle) 50%, var(--bg-muted) 75%);
  background-size: 200% 100%; animation: shimmer 1.5s infinite;
  border-radius: var(--radius-sm);
}

/* Toast entrada */
@keyframes toastEnter {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Modal entrada */
@keyframes modalEnter {
  from { opacity: 0; transform: scale(0.96) translateY(8px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}
```

### Reglas
- **Nunca** animaciones > 400ms
- **Nunca** bounce o elastic easing (no es Raw)
- **Siempre** ease o ease-out
- Skeleton loading para toda carga de datos
- Stagger 50ms entre elementos de lista
- Respetar `prefers-reduced-motion: reduce`

---

## 17. Componentes Adicionales

### Avatares
```css
.avatar {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-body); font-size: 12px; font-weight: 600; color: #fff;
}
.avatar--blue { background: #2563EB; }
.avatar--violet { background: #7C3AED; }
.avatar--green { background: #059669; }
.avatar--red { background: #DC2626; }
.avatar--amber { background: #D97706; }

.avatar-stack { display: flex; }
.avatar-stack .avatar { margin-left: -7px; border: 2px solid var(--bg-surface); }
.avatar-stack .avatar:first-child { margin-left: 0; }
```

### Toasts / Notificaciones
```css
.toast {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 16px; border-radius: var(--radius-md);
  font-family: var(--font-body); font-size: 13px;
  box-shadow: var(--shadow-lg); animation: toastEnter 300ms ease-out;
}
.toast--success { background: var(--color-success-bg); color: var(--color-success); border-left: 3px solid var(--color-success); }
.toast--error   { background: var(--color-error-bg);   color: var(--color-error);   border-left: 3px solid var(--color-error); }
.toast--warning { background: var(--color-warning-bg); color: var(--color-warning); border-left: 3px solid var(--color-warning); }
.toast--info    { background: var(--color-info-bg);    color: var(--color-info);    border-left: 3px solid var(--color-info); }
```

### Modales
```css
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.45);
  display: flex; align-items: center; justify-content: center;
}
.modal {
  background: var(--bg-surface); border-radius: var(--radius-lg);
  padding: 28px; max-width: 480px; width: 90%;
  box-shadow: var(--shadow-lg); animation: modalEnter 300ms ease-out;
}
.modal-title { font-family: var(--font-heading); font-size: 18px; font-weight: 600; color: var(--text-primary); }
.modal-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 20px; }
```

### Dropdowns
```css
.dropdown {
  background: var(--bg-surface); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); box-shadow: var(--shadow-md);
  padding: 4px; min-width: 200px;
}
.dropdown-item {
  padding: 8px 12px; font-family: var(--font-body); font-size: 13px;
  color: var(--text-primary); border-radius: var(--radius-xs); cursor: pointer;
}
.dropdown-item:hover { background: var(--bg-muted); }
.dropdown-item.active { background: rgba(37,99,235,0.08); color: var(--text-brand); font-weight: 500; }
```

### Separadores
```css
.divider { height: 1px; background: var(--border-subtle); margin: 16px 0; }
.divider-text { display: flex; align-items: center; gap: 12px; margin: 14px 0; }
.divider-text .line { flex: 1; height: 1px; background: var(--border-subtle); }
.divider-text span { font-family: var(--font-mono); font-size: 9px; color: var(--text-tertiary); }
.divider-raw { height: 2px; background: var(--border-raw); margin: 24px 0; }
```

### Checkbox
```css
.checkbox { display: flex; align-items: center; gap: 8px; }
.checkbox input[type="checkbox"] { width: 14px; height: 14px; accent-color: var(--text-brand); }
.checkbox label { font-family: var(--font-body); font-size: 11px; color: var(--text-secondary); }
```

### Tooltips
```css
.tooltip {
  background: var(--bg-elevated); color: var(--text-primary);
  font-family: var(--font-body); font-size: 12px;
  padding: 6px 10px; border-radius: var(--radius-sm);
  box-shadow: var(--shadow-md); max-width: 240px;
}
[data-theme="dark"] .tooltip { background: #252540; border: 1px solid rgba(255,255,255,0.08); }
```

---

## 18. Responsive Breakpoints

| Nombre | Valor | Comportamiento |
|--------|-------|----------------|
| Mobile | `< 640px` | Sidebar oculta, single column, login stacked |
| Tablet | `640px - 1024px` | Sidebar colapsada (64px), 2 columnas |
| Desktop | `> 1024px` | Sidebar expandida (240px), grid completo |

### Login responsive
- Desktop: Split 1.15fr + 1fr
- Tablet: Split 1fr + 1fr
- Mobile: Stack vertical (brand arriba, form abajo)

### Dashboard responsive
- Desktop: 4 stat cards en fila, chart + activity side by side
- Tablet: 2 stat cards por fila, chart full width
- Mobile: 1 stat card por fila, todo stacked

---

## 19. Iconografía — Lucide Icons

Estilo: línea fina (stroke-width: 1.5-2px). Tamaños: 20px (sidebar), 16px (inline), 24px (headers).

| Contexto | Icono |
|----------|-------|
| Dashboard | `LayoutDashboard` |
| Comprobantes | `FileText` |
| Nueva factura | `FilePlus` |
| Clientes | `Users` |
| Productos | `Package` |
| Reportes | `BarChart3` |
| Configuración | `Settings` |
| Buscar | `Search` |
| Notificaciones | `Bell` |
| Usuario | `User` |
| Cerrar sesión | `LogOut` |
| Éxito | `CheckCircle` |
| Error | `XCircle` |
| Advertencia | `AlertTriangle` |
| Info | `Info` |
| Editar | `Pencil` |
| Eliminar | `Trash2` |
| Descargar | `Download` |
| Imprimir | `Printer` |
| Enviar | `Send` |

---

## 20. Principios de Diseño

1. **Claridad sobre decoración** — Cada elemento visual tiene un propósito
2. **Una acción principal por pantalla** — No saturar con opciones
3. **El documento es el centro** — La factura/boleta siempre visible
4. **Feedback inmediato** — Toda acción tiene respuesta visual
5. **Lenguaje humano** — "Emitir factura", no "Gestión documental tributaria"
6. **Consistencia total** — Mismos patrones en toda la app
7. **Accesible** — Contraste WCAG AA, navegable por teclado
8. **Rápido** — Skeleton loading, optimistic UI, transiciones cortas
9. **Psicología invisible** — Los sesgos guían, nunca manipulan
10. **Raw con propósito** — La estética industrial refuerza confianza

---

## 21. Implementación

### Tecnologías recomendadas
- **CSS:** Tailwind CSS
- **Componentes:** Radix UI o Headless UI
- **Íconos:** Lucide React / Lucide Vue
- **Animaciones:** Framer Motion (React) o Vue Transition
- **Charts:** Recharts o Chart.js
- **Fonts:** Google Fonts CDN
- **Theme switching:** `data-theme` attribute en `<html>`

### Tailwind config
```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        'ink-navy': '#0B0B14',
        'inkora-blue': '#2563EB',
        'inkora-violet': '#7C3AED',
        'inkora-indigo': '#6366F1',
        'inkora-lavender': '#818CF8',
        'inkora-lilac': '#C084FC',
        'papel': '#FAFAF7',
        'muted': '#F8F7F4',
      },
      fontFamily: {
        brand: ['Syne', 'sans-serif'],
        heading: ['Space Grotesk', 'sans-serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['Space Mono', 'monospace'],
      },
      borderRadius: {
        'xs': '4px',
        'sm': '6px',
        'md': '8px',
        'lg': '12px',
        'xl': '16px',
      },
      boxShadow: {
        'inkora-sm': '0 1px 3px rgba(0,0,0,0.06)',
        'inkora-md': '0 4px 12px rgba(0,0,0,0.08)',
        'inkora-lg': '0 8px 30px rgba(0,0,0,0.12)',
        'inkora-focus': '0 0 0 3px rgba(37,99,235,0.12)',
        'inkora-hover': '0 4px 24px rgba(37,99,235,0.08)',
      },
    },
  },
}
```

---

*Inkora Design System v2.0 — Creado para Codex*
*Plataforma de facturación electrónica para imprentas y MYPES gráficas — Perú*
*Estilo: Raw Aesthetics + Psicología Cognitiva*
*Temas: Light (Halo + Social Proof + Loss Aversion) + Dark (Endowment + Commitment)*
