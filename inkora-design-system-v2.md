# Inkora Design System v2.0 — Guía Completa para Codex

> Sistema de diseño para la plataforma de facturación electrónica **Inkora**, orientada a imprentas y MYPES del sector gráfico en Perú.
> Estilo visual: **Raw Aesthetics** con fundamentos de **psicología cognitiva**.
> Temas: **Light Mode** (principal) + **Dark Mode** (alternativo).

---

## 1. Identidad de Marca

### Nombre
- **Marca:** Inkora
- **Descriptor:** Sistema de facturación para imprentas
- **Variantes:** Inkora · Inkora ERP · Inkora Facturación · Inkora Print

### Personalidad
- Moderno pero confiable · Simple pero profesional · Tecnológico pero cercano
- Premium pero accesible para MYPES · **Raw** — honesto, directo, sin adornos

### Tono visual — Raw Aesthetics
- Líneas gruesas, bordes definidos, tipografía con peso
- Mucho espacio en blanco (light) o espacio oscuro (dark)
- Jerarquía clara con contraste fuerte
- Componentes consistentes con personalidad industrial
- Guiños sutiles al mundo gráfico/imprenta

### Filosofía
> "Cada elemento visual tiene un propósito psicológico. No decoramos — persuadimos."

---

## 2. Psicología Cognitiva Aplicada

### Sesgos integrados en el diseño

| Sesgo | Qué hace | Dónde se aplica |
|-------|----------|-----------------|
| **Halo Effect** | Diseño limpio = percepción de calidad (50ms — Google Research) | Toda la interfaz, login |
| **Social Proof** | "Otros confían, yo también" | Contadores, avatares, testimonios |
| **Loss Aversion** | Perder duele 2x más que ganar | CTAs: "Acceder a MIS facturas" |
| **Endowment Effect** | Sentir propiedad antes de tener | "Tu dashboard te espera" + preview |
| **Commitment & Consistency** | Micro-compromisos → compromisos mayores | Checkbox pre-marcado |
| **Cognitive Fluency** | Fácil = confiable | Máximo 2 campos en login |
| **Anchoring** | Primer número ancla percepción | Métricas grandes: 99.2%, 3.2s, 1,247 |
| **Mere Exposure** | Consistencia = familiaridad = confianza | Mismos patrones en toda la app |

### Reglas
1. Nunca más de 2 sesgos en un mismo componente
2. Priorizar claridad sobre persuasión
3. Social proof debe ser real — nunca inventar números
4. Loss aversion solo en CTAs principales
5. Trust signals (SUNAT activa, cifrado) siempre visibles en contextos fiscales

---

## 3. Tipografía

### Google Fonts Import
```
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Space+Mono:wght@400;700&family=Space+Grotesk:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');
```

### Roles tipográficos

| Fuente | Rol | Uso |
|--------|-----|-----|
| **Syne** (800) | Brand / Display | Logo "inkora", títulos hero, números de impacto |
| **Space Mono** (400, 700) | Labels / Datos | Labels uppercase, series de comprobantes, RUC, montos, códigos SUNAT, badges, botones |
| **Space Grotesk** (300-700) | Headings UI | Títulos de secciones, nombres de páginas, headings de tarjetas |
| **Inter** (300-700) | Body / UI | Texto corrido, descripciones, navegación, tablas |

### Escala tipográfica

| Elemento | Fuente | Tamaño | Peso | Line Height | Letter Spacing |
|----------|--------|--------|------|-------------|----------------|
| Brand / Hero | Syne | 48-72px | 800 | 0.85 | -0.02em |
| Display Number | Syne | 28-36px | 800 | 1.0 | -0.01em |
| Page Title (H1) | Space Grotesk | 24px | 700 | 1.2 | -0.02em |
| Section Title (H2) | Space Grotesk | 20px | 600 | 1.2 | -0.01em |
| Card Title (H3) | Space Grotesk | 16px | 600 | 1.3 | 0 |
| Body | Inter | 14px | 400 | 1.5 | 0 |
| Body Small | Inter | 13px | 400 | 1.5 | 0 |
| Label | Space Mono | 9-10px | 700 | 1.2 | 1.5-2px |
| Caption | Inter | 12px | 400 | 1.4 | 0 |
| Monospace Data | Space Mono | 14px | 400 | 1.4 | 0 |
| Button | Space Mono | 11px | 700 | 1.0 | 2px |
| Badge / Tag | Space Mono | 9px | 700 | 1.0 | 1px |

### Reglas tipográficas
- Labels de formularios: **siempre** Space Mono, uppercase, letter-spacing 1.5px
- Números financieros: Space Mono para alineación tabular
- Series de comprobantes (`F001-00001234`): Space Mono
- Texto de interfaz: Inter
- Títulos de páginas: Space Grotesk
- Logo y hero: Syne
- **Nunca** mezclar más de 2 fuentes en un mismo componente
- **Nunca** usar Syne para texto corrido

---

## 4. Paleta de Colores

### 4.1 Colores de marca

| Nombre | Hex | Uso |
|--------|-----|-----|
| Ink Navy | `#0B0B14` | Fondo dark theme, textos máximo contraste |
| Inkora Blue | `#2563EB` | Primario light theme, botones, links |
| Inkora Violet | `#7C3AED` | Acento dark theme |
| Inkora Indigo | `#6366F1` | Primario dark theme (inicio gradiente) |
| Inkora Lavender | `#818CF8` | Primario dark theme (fin gradiente), links dark |
| Inkora Lilac | `#C084FC` | Acento gradiente brand dark |

### 4.2 Gradientes de marca
```css
--gradient-brand-light: linear-gradient(135deg, #2563EB, #7C3AED);
--gradient-brand-dark: linear-gradient(135deg, #6366F1, #818CF8);
--gradient-brand-accent: linear-gradient(135deg, #818CF8, #C084FC);
```
Usar solo en: botón CTA principal (dark), logo, login, avatar de iniciales.
**Nunca** como fondo de secciones completas. **Nunca** en más de 1 elemento por vista.

### 4.3 Colores funcionales

| Estado | Color | Hex | Background | Hex BG |
|--------|-------|-----|------------|--------|
| Éxito | Verde | `#059669` | Verde claro | `#D1FAE5` |
| Advertencia | Ámbar | `#D97706` | Ámbar claro | `#FEF3C7` |
| Error | Rojo | `#DC2626` | Rojo claro | `#FEE2E2` |
| Info | Cyan | `#0891B2` | Cyan claro | `#CFFAFE` |

### 4.4 Neutros — Light Theme

| Nombre | Hex | Uso |
|--------|-----|-----|
| Papel | `#FAFAF7` | Fondo principal (tono cálido) |
| Superficie | `#FFFFFF` | Tarjetas, modales, dropdowns |
| Muted | `#F8F7F4` | Fondos secundarios, hover |
| Borde sutil | `#E8E5DF` | Bordes de tarjetas |
| Borde fuerte | `#D4D0C8` | Bordes de inputs activos |
| Texto principal | `#1A1A1A` | Títulos, contenido |
| Texto secundario | `#666666` | Descripciones, labels |
| Texto terciario | `#999999` | Hints, placeholders |
| Línea Raw | `#1A1A1A` | Líneas decorativas Raw |

### 4.5 Neutros — Dark Theme

| Nombre | Hex | Uso |
|--------|-----|-----|
| Fondo | `#0B0B14` | Fondo principal |
| Superficie | `#1A1A2E` | Tarjetas, modales |
| Elevado | `#252540` | Dropdowns, tooltips |
| Borde sutil | `rgba(255,255,255,0.06)` | Bordes de tarjetas |
| Borde fuerte | `rgba(255,255,255,0.12)` | Bordes de inputs |
| Texto principal | `#E2E8F0` | Títulos, contenido |
| Texto secundario | `rgba(255,255,255,0.4)` | Descripciones |
| Texto terciario | `rgba(255,255,255,0.2)` | Hints |
| Glow Blue | `radial-gradient(circle, rgba(37,99,235,0.12), transparent 70%)` | Aurora decorativo |
| Glow Violet | `radial-gradient(circle, rgba(124,58,237,0.08), transparent 70%)` | Aurora decorativo |

### 4.6 Distribución — Regla 70-20-10

| % | Light Theme | Dark Theme |
|---|-------------|------------|
| 70% | Blancos cálidos (#FAFAF7, #FFF) | Oscuros (#0B0B14, #1A1A2E) |
| 20% | Azul (#2563EB) + Negro Raw (#1A1A1A) | Indigo/Lavender (#6366F1, #818CF8) |
| 10% | Violeta + funcionales | Glows aurora + funcionales |

### Reglas de color
- Nunca más de 3 colores en una misma tarjeta
- Contraste mínimo 4.5:1 (WCAG AA)
- Violeta solo acento, nunca acción principal en light
- Funcionales solo para estados
- En dark, usar `rgba()` para bordes y textos secundarios

---

## 5. CSS Variables

```css
/* ===== LIGHT THEME ===== */
:root, [data-theme="light"] {
  /* Marca */
  --ink-navy: #0B0B14;
  --inkora-blue: #2563EB;
  --inkora-violet: #7C3AED;
  --inkora-gradient: linear-gradient(135deg, #2563EB, #7C3AED);

  /* Fondos */
  --bg-primary: #FAFAF7;
  --bg-surface: #FFFFFF;
  --bg-muted: #F8F7F4;
  --bg-elevated: #FFFFFF;

  /* Bordes */
  --border-subtle: #E8E5DF;
  --border-strong: #D4D0C8;
  --border-raw: #1A1A1A;

  /* Texto */
  --text-primary: #1A1A1A;
  --text-secondary: #666666;
  --text-tertiary: #999999;
  --text-brand: #2563EB;

  /* Funcionales */
  --color-success: #059669;
  --color-success-bg: #D1FAE5;
  --color-warning: #D97706;
  --color-warning-bg: #FEF3C7;
  --color-error: #DC2626;
  --color-error-bg: #FEE2E2;
  --color-info: #0891B2;
  --color-info-bg: #CFFAFE;

  /* Sombras */
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
  --shadow-lg: 0 8px 30px rgba(0,0,0,0.12);
  --shadow-focus: 0 0 0 3px rgba(37,99,235,0.12);
  --shadow-hover: 0 4px 24px rgba(37,99,235,0.08);

  /* Radios */
  --radius-xs: 4px;
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;

  /* Tipografía */
  --font-brand: 'Syne', sans-serif;
  --font-heading: 'Space Grotesk', sans-serif;
  --font-body: 'Inter', sans-serif;
  --font-mono: 'Space Mono', monospace;

  /* Transiciones */
  --transition-fast: 150ms ease;
  --transition-normal: 200ms ease;
  --transition-slow: 300ms ease;

  /* Espaciado */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
}

/* ===== DARK THEME ===== */
[data-theme="dark"] {
  --bg-primary: #0B0B14;
  --bg-surface: #1A1A2E;
  --bg-muted: rgba(255,255,255,0.03);
  --bg-elevated: #252540;

  --border-subtle: rgba(255,255,255,0.06);
  --border-strong: rgba(255,255,255,0.12);
  --border-raw: rgba(255,255,255,0.15);

  --text-primary: #E2E8F0;
  --text-secondary: rgba(255,255,255,0.4);
  --text-tertiary: rgba(255,255,255,0.2);
  --text-brand: #818CF8;

  --inkora-gradient: linear-gradient(135deg, #6366F1, #818CF8);

  --shadow-sm: 0 1px 3px rgba(0,0,0,0.3);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.4);
  --shadow-lg: 0 8px 30px rgba(0,0,0,0.5);
  --shadow-focus: 0 0 0 3px rgba(129,140,248,0.2);
  --shadow-hover: 0 4px 24px rgba(129,140,248,0.1);

  --color-success-bg: rgba(5,150,105,0.15);
  --color-warning-bg: rgba(217,119,6,0.15);
  --color-error-bg: rgba(220,38,38,0.15);
  --color-info-bg: rgba(8,145,178,0.15);
}
```

---

## 6. Elementos Raw Aesthetics

### 6.1 Líneas decorativas (firma visual)
Las 3 líneas decrecientes bajo el logo son la firma visual de Inkora.

```css
.raw-lines { display: flex; flex-direction: column; gap: 4px; margin-top: 12px; }
.raw-lines div:nth-child(1) { width: 100%; height: 2px; background: var(--border-raw); }
.raw-lines div:nth-child(2) { width: 65%; height: 2px; background: var(--border-raw); }
.raw-lines div:nth-child(3) { width: 40%; height: 2px; background: var(--border-raw); }
```
**Uso:** Login, header del dashboard, footer. **Nunca** en cada página.

### 6.2 Bordes Raw
```css
.raw-border { border: 2px solid var(--border-raw); }
/* Light: #1A1A1A (negro sólido) | Dark: rgba(255,255,255,0.15) */
```
**Uso:** Tarjetas principales, login form, cards de acción. **Nunca** en todos los elementos.

### 6.3 Labels Raw
```css
.raw-label {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text-secondary);
}
```

### 6.4 Aurora Glows (solo Dark Theme)
```css
.aurora-glow-blue {
  position: absolute; width: 400px; height: 400px; border-radius: 50%;
  background: radial-gradient(circle, rgba(37,99,235,0.12), transparent 70%);
  filter: blur(80px); pointer-events: none;
}
.aurora-glow-violet {
  position: absolute; width: 300px; height: 300px; border-radius: 50%;
  background: radial-gradient(circle, rgba(124,58,237,0.08), transparent 70%);
  filter: blur(60px); pointer-events: none;
}
```
**Uso:** Login dark, dashboard dark, detrás de modales. **Nunca** en light theme. Máximo 2 por vista.

---

## 7. Botones

### 7.1 Primario
```css
.btn-primary {
  width: 100%; padding: 14px 24px;
  background: #1A1A1A; color: #FFFFFF; border: none;
  font-family: var(--font-mono); font-size: 11px; font-weight: 700;
  letter-spacing: 2px; text-transform: uppercase;
  cursor: pointer; transition: all var(--transition-fast); border-radius: 2px;
}
.btn-primary:hover { background: var(--inkora-blue); box-shadow: 0 4px 16px rgba(37,99,235,0.2); }
.btn-primary:active { transform: translateY(1px); }

[data-theme="dark"] .btn-primary { background: var(--inkora-gradient); }
[data-theme="dark"] .btn-primary:hover { box-shadow: 0 4px 24px rgba(99,102,241,0.3); transform: translateY(-1px); }
```

### 7.2 Secundario
```css
.btn-secondary {
  width: 100%; padding: 12px 24px;
  background: transparent; border: 2px solid var(--border-raw);
  font-family: var(--font-mono); font-size: 10px; font-weight: 700;
  letter-spacing: 1px; text-transform: uppercase;
  cursor: pointer; transition: all var(--transition-fast);
  color: var(--text-primary); border-radius: 2px;
}
.btn-secondary:hover { background: var(--text-primary); color: var(--bg-surface); }
```

### 7.3 Ghost
```css
.btn-ghost {
  padding: 8px 16px; background: transparent; border: none;
  font-family: var(--font-body); font-size: 13px; font-weight: 500;
  color: var(--text-brand); cursor: pointer;
}
.btn-ghost:hover { color: var(--inkora-violet); }
```

### 7.4 FAB (Floating Action Button)
```css
.btn-fab {
  width: 48px; height: 48px; border-radius: 50%;
  background: var(--text-primary); color: var(--bg-surface);
  border: none; display: flex; align-items: center; justify-content: center;
  box-shadow: var(--shadow-md); transition: all var(--transition-normal);
}
.btn-fab:hover { background: var(--inkora-blue); box-shadow: var(--shadow-lg); transform: translateY(-2px); }
```

### Reglas de botones
- Primario: 1 por vista. Uppercase monospace. border-radius: 2px (Raw).
- Secundario: Acciones alternativas (Clave SOL, cancelar, exportar).
- Ghost: Links funcionales.
- FAB: Solo para "Nueva factura".
- **Nunca** gradiente en botones light. **Nunca** más de 2 botones juntos sin separador.

---

## 8. Inputs y Formularios

### 8.1 Input Raw (login)
```css
.input-raw {
  width: 100%; border: none; border-bottom: 2px solid var(--border-raw);
  padding: 10px 0; font-family: var(--font-mono); font-size: 14px;
  background: transparent; color: var(--text-primary); outline: none;
  transition: border-color var(--transition-normal);
}
.input-raw:focus { border-color: var(--text-brand); }
.input-raw::placeholder { color: var(--text-tertiary); font-family: var(--font-body); font-size: 13px; }
```

### 8.2 Input Estándar (formularios internos)
```css
.input-standard {
  width: 100%; padding: 10px 14px;
  border: 1.5px solid var(--border-strong); border-radius: var(--radius-sm);
  font-family: var(--font-body); font-size: 14px;
  background: var(--bg-surface); color: var(--text-primary); outline: none;
  transition: all var(--transition-normal);
}
.input-standard:focus { border-color: var(--text-brand); box-shadow: var(--shadow-focus); }
.input-standard:hover:not(:focus) { border-color: var(--text-secondary); }
```

### 8.3 Label
```css
.form-label {
  font-family: var(--font-mono); font-size: 9px; font-weight: 700;
  letter-spacing: 1.5px; text-transform: uppercase;
  color: var(--text-primary); display: block; margin-bottom: 6px;
}
```

### Reglas
- Login: `input-raw` (underline). Internos: `input-standard`.
- Labels: siempre Space Mono uppercase.
- Error: borde rojo + mensaje Inter 12px.
- **Nunca** inputs sin label visible.

---

## 9. Tarjetas (Cards)

### 9.1 Card Raw (énfasis)
```css
.card-raw {
  background: var(--bg-surface); border: 2px solid var(--border-raw);
  border-radius: var(--radius-xs); padding: 24px; position: relative;
}
.card-raw::before {
  content: attr(data-label); position: absolute; top: -11px; left: 20px;
  background: var(--text-primary); color: var(--bg-surface);
  font-family: var(--font-mono); font-size: 9px; font-weight: 700;
  padding: 3px 10px; letter-spacing: 2px; text-transform: uppercase;
}
```

### 9.2 Card Estándar
```css
.card-standard {
  background: var(--bg-surface); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); padding: 20px;
  transition: all var(--transition-normal);
}
.card-standard:hover { box-shadow: var(--shadow-hover); border-color: var(--border-strong); }
```

### 9.3 Card Stat
```css
.card-stat {
  background: var(--bg-surface); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); padding: 16px 20px;
}
.card-stat .value {
  font-family: var(--font-mono); font-size: 28px; font-weight: 700;
  color: var(--text-primary); line-height: 1;
}
.card-stat .label {
  font-family: var(--font-mono); font-size: 9px; letter-spacing: 1.5px;
  text-transform: uppercase; color: var(--text-secondary); margin-top: 4px;
}
.card-stat .trend { font-family: var(--font-body); font-size: 12px; margin-top: 8px; }
.card-stat .trend.up { color: var(--color-success); }
.card-stat .trend.down { color: var(--color-error); }
```

### 9.4 Card Social Proof
```css
.card-social-proof {
  padding: 14px 16px; background: var(--bg-muted);
  border-left: 3px solid var(--text-brand);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
}
.card-social-proof .counter {
  font-family: var(--font-mono); font-size: 26px; font-weight: 700; color: var(--text-brand);
}
```

### 9.5 Card Testimonial
```css
.card-testimonial {
  padding: 12px 14px; border: 1.5px solid var(--border-subtle); border-radius: var(--radius-md);
}
.card-testimonial .stars { color: #F59E0B; font-size: 11px; margin-bottom: 4px; }
.card-testimonial p { font-family: var(--font-body); font-size: 11px; color: var(--text-secondary); line-height: 1.6; font-style: italic; }
.card-testimonial .author { font-family: var(--font-mono); font-size: 10px; color: var(--text-brand); margin-top: 5px; font-weight: 700; }
```

### Reglas
- `card-raw`: Solo máxima importancia (login, nueva factura).
- `card-standard`: Uso general.
- `card-stat`: Métricas numéricas. Máximo 4 en fila.
- Dark theme: cards con `var(--bg-surface)` y bordes `rgba`.

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
