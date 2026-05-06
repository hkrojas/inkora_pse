# Plan de rediseño total — Inkora

> **Concepto rector:** *Press Room — Editorial Brutalism para operaciones de imprenta.*
> No es un SaaS genérico. Es una **sala de prensa** digital: precisión, tinta, papel, marcas
> de registro, folios y cifras en monoespaciada. El software refleja el oficio del cliente.

Este documento define la dirección visual y los tokens del sistema completo. Cubre
filosofía, identidad, tokens (color, tipografía, espaciado, sombras, movimiento),
especificación uniforme de **cada** componente, blueprints por página, accesibilidad,
responsive y plan de implementación por fases.

---

## 0. Diagnóstico del estado actual

**Problemas del diseño vigente:**
- Login con panel izquierdo denso de texto publicitario y panel derecho genérico
  → se siente "web de agencia" y desequilibrado.
- El logo violeta-azul es fuerte pero está **aislado**: no hay una lectura gráfica
  que conecte el producto con el negocio (imprenta) más allá del color.
- Componentes se pintaron por encima de Tailwind sin un token system duro, por eso
  la combobox, el date picker, los botones y los modales **no se sienten del mismo
  sistema**.
- La jerarquía tipográfica está presente pero es tímida: pocos pesos contrastados,
  poco uso de monoespaciada para cifras (y estamos en un software de **facturación**).
- Demasiados fondos suaves (azul grisáceo), poco contraste ink-on-paper, el ojo
  no sabe dónde pararse.

**Qué sí conservamos:**
- Paleta base del logo (azul #2563EB → violeta #7C3AED → púrpura #9333EA).
- Borders radius cero y sombras sólidas desplazadas que ya se estaban introduciendo
  en `app.css`. Vamos a llevarlo más lejos, no a retroceder.
- Nomenclatura de tokens semánticos (`--ink-primary`, `--bg-surface`, etc.).
- Esqueleto de layout con sidebar oscuro + contenido claro.

---

## 1. Filosofía de diseño

### 1.1. Lo que Inkora **sí** es
- **Herramienta de oficio**, no escaparate. Densidad antes que aire. Un operador
  factura 40 boletas al día; cada clic cuenta.
- **Papel e tinta**. El producto del usuario es el impreso. Usamos vocabulario
  gráfico de imprenta (marcas de corte, folios, registros de color, ledger rules,
  tipografía de taller) como **elementos funcionales**, no como decoración.
- **Editorial / Swiss / Bauhaus**: grilla visible, tipografía con tracking,
  números tabulares, uso deliberado del vacío en pocos sitios clave.
- **Brutalismo funcional**: border-radius 0, sombras sólidas desplazadas, bordes
  gruesos, estados muy evidentes. Nada se esconde tras humo.
- **Contraste severo ink/paper**: negro tinta sobre blanco papel como base;
  el color de marca es **acento raro**, no ruido de fondo.

### 1.2. Lo que Inkora **no** es (reglas duras)
- **NO gradientes en superficies grandes.** El gradiente del logo existe solo
  en el logo y en una única línea de tensión de 2 px en la parte superior de la
  app. No rellenamos cards, botones ni KPIs con gradiente.
- **NO botones redondeados**, NO pill-shapes. Todo `border-radius: 0`.
- **NO glassmorphism** difuso ni cards flotantes con blur de colores. Glass se
  limita al topbar sticky y al overlay de modales.
- **NO emojis en UI**. Iconos vectoriales Lucide o Phosphor, peso uniforme 1.5 px.
- **NO sombras soft de 40 px azules**. Las sombras son **offset sólido** (ej.
  `4px 4px 0 0 #0F172A`), no halo.
- **NO variaciones de color por gusto**. Solo la paleta definida. Los badges
  semánticos (éxito/warning/error/info) son los únicos portadores de color
  fuera del acento de marca.
- **NO "más de 3 tipografías" mezcladas**. 3 familias: display (Syne), grotesk
  (Space Grotesk), mono (JetBrains Mono). Body hereda del grotesk.
- **NO animaciones de aparición complicadas**. Fades cortos (120–180 ms) con
  desplazamientos de 4–8 px máximo.

### 1.3. Los 5 principios operativos
1. **Ledger first.** Cifras son protagonistas → siempre monoespaciada y
   alineadas a la derecha con separador de miles.
2. **Folio everywhere.** Todo documento tiene una matrícula visible y legible
   (F001-00123, B001-00088). El número es el rostro del documento.
3. **Marks of the press.** Marcas de corte en esquinas, lineas de registro
   sutiles, sellos de estado. El lenguaje gráfico de imprenta está embebido.
4. **High-contrast, low-chroma.** Paleta reducida: ink, paper, 1 acento y 4
   semánticos. Todo lo demás es grises calibrados.
5. **One chrome per role.** Botón primario tiene exactamente **un** aspecto,
   combobox tiene exactamente **uno**, modal tiene exactamente **uno**. Sin
   variantes ad-hoc por página.

---

## 2. Identidad y uso del logo

### 2.1. Versiones del logo
- **Isotipo (`/logo-icon.png`, `logo1.png`):** gota con monograma K en
  gradiente azul-violeta. Uso en sidebar, favicon, loading screens, esquina
  del login, avatar de marca en correos.
- **Logotipo completo (`logo.png`):** gota + wordmark "Inkora" en negro.
  Uso en login desktop, documentos PDF, correos, landing pública.
- **Wordmark solo** (tipografía Syne): cuando el isotipo ya está pintado
  al lado y no queremos duplicar.

### 2.2. Reglas del logo
- El gradiente del isotipo **solo vive en el isotipo**. Nunca lo extendemos
  a botones, fondos, títulos.
- Tamaño mínimo: 24 px de alto. Aislamiento: equivalente a media altura del
  isotipo a cada lado.
- En fondo oscuro (sidebar `--brand-950`): el isotipo va acompañado de un
  drop-shadow sutil `drop-shadow(0 0 8px rgba(99,102,241,.35))`.

### 2.3. La "línea de tensión"
Una línea de 2 px con el gradiente del logo corre a lo ancho de toda la app,
pegada al borde superior de la ventana:

```css
.app-tension-line {
  position: fixed; top: 0; left: 0; right: 0; height: 2px; z-index: 100;
  background: linear-gradient(90deg, #2563EB 0%, #7C3AED 50%, #D946EF 100%);
  background-size: 200% 200%;
  animation: tension-drift 8s ease-in-out infinite;
}
```

Es la única superposición del gradiente en la app. Funciona como firma
editorial y como status bar pasiva ("la prensa está operando").

---

## 3. Sistema de color

### 3.1. Filosofía de color
- **Ink & Paper** es el par base. Todo lo demás es acento medido.
- Paleta reducida: 1 tinta (negro azulado), 1 papel (blanco cálido), 1 acento
  de marca (el violeta/azul del logo), 4 semánticos (success/warning/error/info)
  y una escala de grises calibrada de 12 pasos (ink-950 → paper-50).

### 3.2. Tokens raíz — Modo claro (Paper)

```css
:root, [data-theme='light'] {
  /* === INK (tinta) — 12 pasos === */
  --ink-950: #0A0A12;   /* Titulares críticos, sidebar */
  --ink-900: #111118;   /* Headers display */
  --ink-800: #1A1A24;   /* Body text fuerte */
  --ink-700: #2A2A38;   /* Body default */
  --ink-600: #3F3F52;   /* Body secondary */
  --ink-500: #5E5E75;   /* Meta, tertiary */
  --ink-400: #8A8AA0;   /* Placeholder, disabled text */
  --ink-300: #B5B5C8;   /* Borders fuertes */
  --ink-200: #D4D4E0;   /* Borders default */
  --ink-100: #E8E8F0;   /* Borders sutiles, separators */
  --ink-50:  #F2F2F8;   /* Surface alt */
  --paper:   #FAFAF5;   /* Papel (fondo base, cálido) */

  /* === ACENTO DE MARCA (uso raro, solo highlight) === */
  --brand-600: #4F46E5;  /* Acento por defecto (índigo, no violeta puro) */
  --brand-700: #3730A3;  /* Acento pressed */
  --brand-500: #6366F1;  /* Acento hover / decorativo */
  --brand-100: #E0E7FF;  /* Tint muy suave para selection */
  --brand-50:  #EEF2FF;  /* Tint casi imperceptible */

  /* === GRADIENT (solo para logo y línea de tensión) === */
  --grad-press: linear-gradient(90deg, #2563EB, #7C3AED 60%, #D946EF);

  /* === SEMÁNTICOS (badges, alerts, estados) === */
  --sx-success:      #047857;
  --sx-success-bg:   #D1FAE5;
  --sx-success-edge: #6EE7B7;
  --sx-warning:      #B45309;
  --sx-warning-bg:   #FEF3C7;
  --sx-warning-edge: #FCD34D;
  --sx-error:        #B91C1C;
  --sx-error-bg:     #FEE2E2;
  --sx-error-edge:   #FCA5A5;
  --sx-info:         #0369A1;
  --sx-info-bg:      #E0F2FE;
  --sx-info-edge:    #7DD3FC;

  /* === SUPERFICIES (aliases funcionales) === */
  --bg-app:        var(--paper);
  --bg-surface:    #FFFFFF;       /* Card, modal body */
  --bg-surface-2:  var(--ink-50); /* Row hover, tabla zebra */
  --bg-input:      #F8FAFC;       /* Fondo de inputs en reposo */
  --bg-input-focus:#FFFFFF;       /* Input en focus = papel puro */
  --bg-inverse:    var(--ink-950);/* Sidebar, tooltips */

  /* === BORDERS === */
  --border-hair:   var(--ink-100); /* 1px separators */
  --border-rule:   var(--ink-200); /* borde default */
  --border-strong: var(--ink-300); /* hover / active */
  --border-ink:    var(--ink-900); /* outline brutalista (botón primario) */
  --border-brand:  var(--brand-600);

  /* === TEXTO === */
  --text-primary:   var(--ink-900);
  --text-secondary: var(--ink-600);
  --text-tertiary:  var(--ink-500);
  --text-muted:     var(--ink-400);
  --text-inverse:   #FFFFFF;
  --text-brand:     var(--brand-600);

  /* === SHADOWS (offset sólido, no halo) === */
  --shadow-brut-sm: 2px 2px 0 0 var(--ink-900);
  --shadow-brut-md: 4px 4px 0 0 var(--ink-900);
  --shadow-brut-lg: 6px 6px 0 0 var(--ink-900);
  --shadow-brut-brand: 4px 4px 0 0 var(--brand-600);
  --shadow-focus: 0 0 0 3px var(--brand-100), 0 0 0 4px var(--brand-600);
  --shadow-overlay: 0 10px 40px rgba(10,10,18,0.18);
}
```

### 3.3. Tokens raíz — Modo oscuro (Press Room)

```css
[data-theme='dark'] {
  --ink-950: #F5F5F0;   /* Invertido: ahora "tinta" es clara */
  --ink-900: #E8E8E5;
  --ink-800: #D6D6D2;
  --ink-700: #B8B8B5;
  --ink-600: #8F8F92;
  --ink-500: #6E6E78;
  --ink-400: #4E4E5A;
  --ink-300: #383842;
  --ink-200: #252530;
  --ink-100: #1C1C28;
  --ink-50:  #14141E;
  --paper:   #0B0B14;   /* Fondo: negro azulado profundo */

  --brand-600: #818CF8;  /* Lavender → más legible en oscuro */
  --brand-700: #A5B4FC;
  --brand-500: #6366F1;
  --brand-100: rgba(129,140,248,0.12);
  --brand-50:  rgba(129,140,248,0.06);

  --bg-app:        var(--paper);
  --bg-surface:    #14141E;
  --bg-surface-2:  #1C1C28;
  --bg-input:      #14141E;
  --bg-input-focus:#1C1C28;
  --bg-inverse:    #F5F5F0;

  --border-hair:   rgba(255,255,255,0.06);
  --border-rule:   rgba(255,255,255,0.12);
  --border-strong: rgba(255,255,255,0.22);
  --border-ink:    var(--ink-900);

  --shadow-brut-sm: 2px 2px 0 0 rgba(129,140,248,0.9);
  --shadow-brut-md: 4px 4px 0 0 rgba(129,140,248,0.9);
  --shadow-brut-lg: 6px 6px 0 0 rgba(129,140,248,0.9);
  --shadow-overlay: 0 10px 40px rgba(0,0,0,0.55);
}
```

### 3.4. Uso del color — mapa
| Rol | Claro | Oscuro | Notas |
|---|---|---|---|
| Fondo app | `#FAFAF5` papel cálido | `#0B0B14` press room | El papel cálido diferencia de blancos fríos tipo Notion |
| Superficie card | `#FFFFFF` | `#14141E` | Ligera elevación por contraste, no por sombra |
| Texto principal | `#111118` | `#E8E8E5` | AAA sobre papel y sobre oscuro |
| Texto meta | `#5E5E75` | `#8F8F92` | AA, para labels y timestamps |
| Acento de marca | `#4F46E5` índigo | `#818CF8` lavender | Solo para focus ring, links, highlight activo |
| Sidebar | `#0A0A12` | `#0A0A12` | Igual en ambos temas (press panel) |
| Success | `#047857` | `#6EE7B7` | Ingresos, "facturada" |
| Warning | `#B45309` | `#FCD34D` | Pendiente, días de mora medios |
| Error | `#B91C1C` | `#FCA5A5` | Vencida, anulada, crítico |
| Info | `#0369A1` | `#7DD3FC` | Notas informativas |

**Regla del acento:** en una pantalla completa, el acento de marca
(`--brand-600`) no puede ocupar más del **~5 %** del área visible. Si lo usas
en el botón primario, en un highlight activo y en el focus ring, ya llegaste
al máximo. Todo lo demás queda en ink/paper.

---

## 4. Sistema tipográfico

### 4.1. Familias
- **Syne** (display) — `--font-display`. Solo para el wordmark de marca,
  numerales enormes (KPIs del dashboard a ≥48 px) y titulares de login.
  Se usa poco, para que se note.
- **Space Grotesk** (grotesk / body) — `--font-body`. Títulos de sección,
  copy, formularios. El caballo de batalla.
- **JetBrains Mono** (mono) — `--font-mono`. Números, folios, series,
  RUC/DNI, montos, códigos, badges de estado, etiquetas uppercase tipo
  "CAPITAL PENDIENTE". Portador del lenguaje de taller.
- **Inter** es fallback de Space Grotesk (el proyecto ya la carga).

### 4.2. Escala tipográfica (modular base 16, ratio 1.25)

| Token | px | rem | line-height | Uso |
|---|---|---|---|---|
| `--fs-display-2xl` | 56 | 3.5 | 1.05 | KPI gigante dashboard, hero del login |
| `--fs-display-xl` | 44 | 2.75 | 1.1 | Login títulos |
| `--fs-display-lg` | 36 | 2.25 | 1.15 | Totales en modales transaccionales |
| `--fs-h1` | 28 | 1.75 | 1.2 | H1 de página (topbar title) |
| `--fs-h2` | 22 | 1.375 | 1.25 | H2 de sección |
| `--fs-h3` | 18 | 1.125 | 1.3 | Sub-sección, card title |
| `--fs-body-lg` | 16 | 1 | 1.5 | Body denso (detalle cotización) |
| `--fs-body` | 14 | 0.875 | 1.55 | Body default, inputs, celdas tabla |
| `--fs-sm` | 13 | 0.8125 | 1.5 | Body compacto |
| `--fs-xs` | 12 | 0.75 | 1.4 | Meta |
| `--fs-micro` | 10 | 0.625 | 1.3 | Labels mono uppercase |

### 4.3. Roles tipográficos — uso uniforme

```css
/* Wordmark (solo logo) */
.tx-brand { font-family: var(--font-display); font-weight: 700; letter-spacing: -0.02em; }

/* Titular de página */
.tx-page-title {
  font-family: var(--font-body); font-weight: 700;
  font-size: var(--fs-h1); letter-spacing: -0.02em; color: var(--text-primary);
}

/* Kicker (breadcrumb de página, en mono uppercase) */
.tx-kicker {
  font-family: var(--font-mono); font-weight: 700;
  font-size: var(--fs-micro); letter-spacing: 0.12em;
  text-transform: uppercase; color: var(--text-tertiary);
}

/* Label de formulario */
.tx-label {
  font-family: var(--font-mono); font-weight: 700;
  font-size: var(--fs-micro); letter-spacing: 0.1em;
  text-transform: uppercase; color: var(--text-secondary);
}

/* Cifra ledger (todos los montos) */
.tx-amount {
  font-family: var(--font-mono); font-weight: 600;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em; color: var(--text-primary);
  text-align: right;
}
.tx-amount--total {
  font-weight: 800; font-size: var(--fs-display-lg);
}

/* Folio (F001-00088) */
.tx-folio {
  font-family: var(--font-mono); font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.02em; color: var(--text-primary);
}

/* Copy body — default */
.tx-body { font-family: var(--font-body); font-size: var(--fs-body); color: var(--text-primary); }

/* Meta / timestamp */
.tx-meta { font-family: var(--font-mono); font-size: var(--fs-xs); color: var(--text-tertiary); }
```

### 4.4. Reglas tipográficas
- **Todos los montos** usan `tx-amount` (mono + tabular-nums + right-align).
  Excepción única: monto inline dentro de prosa, donde sí usamos grotesk.
- **Todos los folios y números de documento** (F001-00001, B001-000088,
  07 - DNI, RUC 20123456789) usan mono, sin mezcla.
- **Labels uppercase** sí, pero solo en mono con tracking 0.1–0.12em.
  Nunca uppercase en grotesk (eso es lo que grita "AI SaaS").
- **Cursivas prohibidas** excepto para palabras extranjeras en copy.
- **Los numerales de Syne en headline (Display)** son su razón de existir —
  exponerlos en el dashboard es lo que nos da carácter editorial.

---

## 5. Espaciado y grilla

### 5.1. Escala (base 4)
```
--sp-0: 0;      --sp-1: 4px;    --sp-2: 8px;    --sp-3: 12px;
--sp-4: 16px;   --sp-5: 20px;   --sp-6: 24px;   --sp-8: 32px;
--sp-10: 40px;  --sp-12: 48px;  --sp-16: 64px;  --sp-20: 80px;
--sp-24: 96px;  --sp-32: 128px;
```

### 5.2. Grilla de página
- Sidebar fijo **280 px** (desktop ≥ lg). Colapsable a 72 px.
- Contenido: `max-width: 1440px` centrado, padding horizontal 32 px en
  desktop, 20 px en tablet, 16 px en móvil.
- Grilla interna: **12 columnas**, gap 24 px.
- **Línea de grilla sutil de fondo** (tech-grid 32 px, `rgba(99,102,241,0.035)`)
  en el body. Es un guiño a las hojas de guía de taller.

### 5.3. Densidad
- Los contenidos de negocio (tabla cotizaciones, lista de clientes) usan
  densidad **media**: fila 48 px, padding celda 12×16. No 64 px tipo
  Shopify — eso malgasta pantalla para un usuario pro.
- Formularios: campos de 44 px de alto, gap vertical 16 px entre filas.
- Dashboard: KPI tiles de 160 px de alto mínimo.

---

## 6. Bordes, trazos, sombras, radios

### 6.1. Border radius → **0 en todos los componentes.**
Excepciones autorizadas únicas:
- Círculos puros: avatares, checkboxes (`4px` sí aquí por legibilidad),
  radio dots (`full`).
- Nada más. Ni botones, ni inputs, ni badges, ni cards, ni modales.

### 6.2. Trazos
- **Hairline:** `1px solid var(--border-hair)` — separadores internos.
- **Rule:** `1px solid var(--border-rule)` — borde default de cards/inputs.
- **Strong:** `1.5px solid var(--border-strong)` — hover states.
- **Ink:** `1.5px solid var(--border-ink)` — outline brutalista para botón
  primario y contenedores "stamped".

### 6.3. Sombras (offset sólido)
Solo estos:
- `--shadow-brut-sm` → `2px 2px 0 0 ink-900` — chips elevados, acciones menores.
- `--shadow-brut-md` → `4px 4px 0 0 ink-900` — hover de botón primario, card
  activa.
- `--shadow-brut-lg` → `6px 6px 0 0 ink-900` — modales, toasts.
- `--shadow-brut-brand` → `4px 4px 0 0 brand-600` — hover de CTA crítico
  (Emitir factura, Registrar pago).
- `--shadow-focus` → ring de accesibilidad (3px brand-100 + 1px brand-600).
- `--shadow-overlay` → única sombra "soft" permitida, solo para overlays.

### 6.4. Marcas de imprenta (decorativos funcionales)
Elementos gráficos únicos del sistema:

```css
/* Marcas de corte en esquinas de contenedores clave (login, modal detalle) */
.crop-mark {
  position: absolute; width: 12px; height: 12px;
  border: 1px solid var(--ink-900);
}
.crop-mark--tl { top: -1px; left: -1px; border-right: none; border-bottom: none; }
.crop-mark--tr { top: -1px; right: -1px; border-left: none; border-bottom: none; }
.crop-mark--bl { bottom: -1px; left: -1px; border-right: none; border-top: none; }
.crop-mark--br { bottom: -1px; right: -1px; border-left: none; border-top: none; }

/* Registro de color (punto en caja con cruz) — usado como "status live" */
.registration-mark {
  width: 14px; height: 14px; position: relative; display: inline-block;
}
.registration-mark::before, .registration-mark::after {
  content: ''; position: absolute; background: currentColor;
}
.registration-mark::before { left: 50%; top: 0; bottom: 0; width: 1px; }
.registration-mark::after { top: 50%; left: 0; right: 0; height: 1px; }

/* Ledger rules (reglas horizontales sutiles como papel contable) */
.ledger-row { border-bottom: 1px dashed var(--border-hair); }

/* Folio stamp (usado en headers de detalle de documento) */
.folio-stamp {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 6px 12px;
  border: 1.5px solid var(--ink-900);
  font-family: var(--font-mono); font-weight: 700;
  font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
  background: var(--paper);
}
```

---

## 7. Movimiento

### 7.1. Curvas
- `--ease-out: cubic-bezier(0.16, 1, 0.3, 1)` — default, todo lo que entra.
- `--ease-in: cubic-bezier(0.4, 0, 1, 1)` — todo lo que sale.
- `--ease-press: cubic-bezier(0.4, 0, 0.2, 1)` — botón pressed.
- **NO spring bounce.** Queda infantil. Todo recto y rápido.

### 7.2. Duraciones
- **Instant (80 ms):** estados hover de botones/links.
- **Fast (120 ms):** input focus, toggles.
- **Base (180 ms):** entrada de toasts, reveal de filas.
- **Slow (260 ms):** modales, drawers.
- Nada > 320 ms.

### 7.3. Desplazamientos permitidos
- Hover de botón brutalista: `translate(-4px, -4px)` + shadow aparece.
- Entrada de modal: `opacity 0 → 1` + `translateY(8px → 0)`.
- Entrada de página: `opacity 0 → 1` + `translateY(4px → 0)` (ya existe).
- `prefers-reduced-motion`: deshabilitamos todo salvo cambios de opacidad.

---

## 8. Iconografía

- **Librería única:** Lucide (ya está) o Phosphor Regular. **No mezclamos.**
  Recomiendo quedarnos con Lucide para evitar migrar imports.
- **Peso de trazo:** 1.5 px fijo. No Fill, no Duotone.
- **Tamaños canónicos:** 14 / 16 / 18 / 20 / 24 px. Stop. Otros tamaños
  se escalan por CSS pero la caja siempre es uno de estos.
- **Color:** heredado del texto (`currentColor`). Solo los semánticos
  (check verde, alert naranja) pintan.
- **Iconos propios de imprenta** (opcional, fase 2): marcas de registro,
  roller, plancha offset, guía de corte. Diseñar 6–8 íconos custom con el
  mismo stroke 1.5 px para módulos de imprenta específicos (Guía de remisión,
  PDF Designer).

---

## 9. Componentes — especificación uniforme

Regla maestra: **un solo chrome por rol**. No hay "botón primario variante B".
Si una página necesita algo distinto, hay que discutir el sistema, no hackearlo.

### 9.1. Botones

| Variante | Cuándo | Alto | Chrome |
|---|---|---|---|
| `btn-primary` | Acción principal única por vista | 44 px | Bg ink-950, texto paper, mono 11/700/tracking 0.1em uppercase, border 1.5px ink-950. Hover: `translate(-4px,-4px)` + `shadow-brut-md` brand. |
| `btn-secondary` | Acciones secundarias | 40 px | Bg paper, texto ink-900, border 1.5px ink-300, mono 11/600. Hover: border ink-900 + `shadow-brut-sm`. |
| `btn-ghost` | Acciones terciarias / cancelar | 36 px | Transparente, texto ink-600, grotesk 13/500. Hover: bg ink-50. |
| `btn-danger` | Anular, eliminar | 40 px | Bg paper, border 1.5px error, texto error, mono 11/700 uppercase. Hover: bg error, texto paper. |
| `btn-icon` | Solo ícono (cerrar, más opciones) | 36×36 px | Cuadrado, transparente, border 1px ink-200. Hover: border ink-900. |
| `btn-cta-press` | **Único por página** — emitir, registrar pago, imprimir | 48 px | Igual al primary pero con shadow brand por defecto en estado base (`shadow-brut-brand`). Se ve "armado" al entrar a la vista. |

**Estados compartidos:**
- Focus: `shadow-focus` (ring brand).
- Disabled: `opacity 0.45`, cursor not-allowed, sin hover.
- Loading: reemplaza el label por spinner mono + texto "PROCESANDO". El
  ancho del botón **no cambia** (reservamos el espacio con `min-width`).

**Iconos en botones:** gap 8 px, tamaño 16 px (botón 40/44) o 18 px (botón 48).
Primary arranca con ícono a la **derecha** (flecha/chevron) para sensación
de "avanzar". Los demás a la izquierda.

### 9.2. Inputs de texto

```
Alto: 44 px (compact: 36 px)
Border: 1.5px var(--border-rule); focus → ink-900 + ring brand
Radius: 0
Bg: var(--bg-input) en reposo; var(--bg-input-focus) en focus
Padding: 10px 14px
Placeholder: ink-400, font-body
Font: grotesk 14/400
Error: border var(--sx-error); abajo mensaje mono 11 rojo
Disabled: bg ink-50, texto ink-400
Prefijo/sufijo (S/, %, KGM): mono, ink-500, padding extra 40 px, dentro
  de una "caja inscrita" con `border-left: 1px ink-200`
Corners: opcionalmente marcas de corte en estados de focus para reforzar foco
```

Todos los campos numéricos (cantidades, precios, pesos) usan **input mono + tabular-nums + text-right**.

### 9.3. Textarea
Idéntico al input pero `min-height: 96 px`, resize vertical permitido.

### 9.4. Custom Select

Reemplaza 100 % al `<select>` nativo. Ya existe `CustomSelect.jsx`, hay que
alinearlo a este chrome:

```
Trigger: caja igual que input.
  Icono derecho: chevron 16px, stroke 1.5, rotado 180deg en open.
Dropdown: render via portal, overlay.
  Ancho: igual al trigger.
  Border: 1.5px ink-900 (más fuerte que el input → marca contexto abierto).
  Shadow: shadow-brut-md.
  Max-height: 260 px, scroll interno.
  Item: 40 px alto, padding 10 14, grotesk 14.
    Hover: bg ink-50 + borde izquierdo 2px brand-600.
    Selected: bg brand-50 + borde izquierdo 2px brand-600 + ícono check mono a la derecha.
  Buscador (searchable): sticky top, 40 px, border-bottom hairline.
  Footer action (p.ej. "+ Crear nuevo"): bg ink-50 separator, texto brand,
    mono 11 uppercase.
  Empty state: mono 12 ink-400 centrado, 48 px.
```

### 9.5. Combobox (Cliente, Producto)

Son **Select searchable con render personalizado** pero debe verse
exactamente como un Custom Select; solo cambia el renderItem:

- **ClientCombobox:** cada item muestra `RUC/DNI mono` + `Razón social grotesk`.
- **ProductCombobox:** cada item muestra `código mono` + `descripción grotesk`
  + precio alineado derecha tipo `tx-amount`.

Atajos:
- `↑ ↓` navega, `Enter` selecciona, `Esc` cierra.
- Al escribir, se auto-filtra; si no hay match, aparece una acción "+ Crear
  cliente con este RUC" en el footer (ya previsto en `CustomSelect`).

### 9.6. DatePicker

Ya existe; hay que reestilizarlo:

```
Trigger: idéntico a input. Muestra dd/mm/aaaa en mono + ícono calendario 16 px derecha.
Popover (portal):
  Card: 320 px, bg paper, border 1.5px ink-900, shadow-brut-md.
  Header: mes + año en grotesk 16/700 centrado; flechas ◀ ▶ mono 14,
    botón "Hoy" a la derecha en mono 11 uppercase.
  Weekdays: Lu Ma Mi Ju Vi Sa Do en mono 10 uppercase ink-500.
  Día: celda 40×40, mono 13, tabular-nums.
    Hover: bg ink-50.
    Today: cuadro con border-ink, sin rellenar.
    Selected: bg ink-900, texto paper. Esquina inferior derecha: marca de
      registro 6 px brand.
    Día fuera de mes: ink-300.
    Fin de semana: ink-600 (legible pero diferenciado).
  Footer: año navigator (año anterior / año siguiente), ambos mono.
```

Cobranza / Reportes necesitan **rango**: mismo popover con dos columnas
mes + mes consecutivos y selección de inicio/fin. Fuera del rango inicial,
los días quedan con una línea de registro debajo (underline).

### 9.7. Checkbox

- 18×18 px, border 1.5 px ink-900, bg paper, radius 2 px (única excepción,
  por legibilidad).
- Checked: bg ink-900, check mark blanco con stroke 2 px.
- Hover: border brand-600.
- Disabled: bg ink-50.
- Label a la derecha, gap 10 px, grotesk 13.

### 9.8. Radio

- 18×18 px, círculo, border 1.5 px ink-900, bg paper.
- Selected: dot interior 8 px ink-900.

### 9.9. Toggle (switch)

- 40×22 px, forma **rectangular** (no pill), border 1.5 px ink-900, bg paper.
- Thumb: cuadrado 14×14, ink-900.
- On: bg ink-900, thumb paper (invierte), transición 120 ms.
- Uppercase label ON / OFF en mono 9 dentro del track.

### 9.10. Badge / Chip / Tag

Tres variantes. **Ninguna redondeada.**

```
.badge-status  — estado de documento (PENDIENTE, FACTURADA, ANULADA)
  mono 10 / 700 / uppercase / tracking 0.1em
  padding 4 10 / border 1px / bg semantic-bg / texto semantic
  PENDIENTE → warning | FACTURADA → success | ANULADA → error | BORRADOR → info

.badge-aging  — antigüedad de deuda
  mono 10 / tabular-nums / muestra "12d" "45d"
  Escala: 0–7d ink-300 (neutro) | 8–30d warning | 31–60d warning+ | 60+ error
  Con registration-mark animada a la derecha en 60+d

.chip-tech   — info técnica (ENVIADA A SUNAT, QR OK, TIPO CAMBIO)
  mono 10 / bg ink-50 / border hair / icono 12
  solo ink colors, sin color semántico
```

### 9.11. Modal

```
Overlay:
  bg rgba(10,10,18, 0.55) + backdrop-filter: blur(4px)
  No gradientes de colores ni glass irisado.
Container:
  max-width por variante:
    modal-sm 420 px (confirmaciones)
    modal-md 640 px (formularios cortos)
    modal-lg 920 px (detalle con ledger)
    modal-xl 1120 px (cotización/factura en edición)
  bg paper, border 1.5 px ink-900, shadow-brut-lg.
  Marcas de corte en las 4 esquinas (12 px, 1 px ink-900).
Header:
  padding 20 24, border-bottom 1 px hair.
  Layout: [kicker mono] + [título grotesk 20/700] + [close btn-icon]
  Folio stamp opcional a la derecha (cuando aplica).
Body:
  padding 24, overflow-y auto, grilla interna.
Footer:
  padding 16 24, border-top 1 px hair, acciones alineadas derecha,
  gap 12 px. Primary a la derecha, ghost "Cancelar" a la izquierda.
Animación: fade + translateY(8 → 0), 180 ms ease-out.
```

### 9.12. Drawer (panel lateral)

Uso: filtros avanzados, detalle lateral sin salir de la lista.
- Ancho 440 px (md) / 100 % (móvil).
- Entra desde la derecha, 220 ms.
- Mismo chrome brutalist que el modal pero solo una cara con borde izquierdo
  1.5 px ink-900.

### 9.13. Toast

```
Contenedor fijo top-right, stack vertical gap 8 px.
Toast:
  bg paper, border 1.5 px semantic-edge, shadow-brut-md, padding 14 16.
  Icono 18 semantic.
  Título grotesk 14/700.
  Descripción grotesk 13/400 ink-600.
  Barra inferior de 2 px semantic que decrece como timer (4 s por defecto).
  Botón close 14 px ink-400.
Entrada: translateX(16 → 0) + fade, 180 ms.
```

### 9.14. Alert banner (inline)

- Horizontal, full-width, sticky en la parte superior de la sección.
- Border-left 4 px semantic, bg semantic-bg, texto semantic.
- Icono izquierdo, botón dismiss derecho.
- Mono 11 uppercase en su "prefijo" (`ERROR · SUNAT · 15:22`).

### 9.15. Tabla / Data grid

El componente más importante para este negocio. Patrón único:

```
Encabezado:
  sticky top 0, bg paper, border-bottom 2 px ink-900.
  Labels en mono 10 / 700 / uppercase / tracking 0.1em / ink-500.
  Sort arrow en mono 10.
  Columna de cifras → text-align right.
Fila:
  alto 48 px, border-bottom 1 px hair.
  Hover: bg ink-50 + revela acciones inline a la derecha.
  Seleccionada: bg brand-50 + border-left 2 px brand.
Celdas:
  grotesk 14, cifras en mono tabular.
  Truncate con ellipsis + tooltip en hover.
Zebra: no por defecto (ya tenemos hairlines). Activar solo en Reportes
  donde hay listas largas homogéneas.
Paginación:
  Footer sticky, bg paper, border-top 1 hair, padding 12 20.
  Controles mono 11 uppercase: "PÁG. 2 / 14"  [◀] [▶]  "MOSTRAR: 25 ▾".
Empty state:
  48 px vertical, mono + ilustración monocroma simple (marca de registro
  gigante 64 px brand con texto abajo).
```

Acciones por fila:
- Iconos 16 px ink-400 → ink-900 en hover.
- En reposo solo se ven los 2 primeros (ver, editar). En hover de fila
  aparece el resto deslizando desde la derecha.

### 9.16. Card / KPI tile

```
.card base:
  bg surface, border 1 px rule, radius 0, padding 20 24.
  Sin sombra en reposo. Hover opcional: shadow-brut-sm.
.card--outline (énfasis):
  border 1.5 px ink-900, shadow-brut-sm.
.metric-card (dashboard KPI):
  160 px alto min.
  Layout vertical: label mono top + valor display 44 px centro +
  sparkline o note abajo.
  Variante por semántica: solo cambia el color del valor y del sparkline.
  Brand variant solo para 1 KPI "hero" (el total vendido del día).
```

### 9.17. Tabs

```
Contenedor: border-bottom 1 px rule.
Tab:
  mono 11 / 700 / uppercase / tracking 0.1em.
  padding 14 20.
  Inactivo: ink-500.
  Hover: ink-900.
  Activo: ink-900 + border-bottom 2 px ink-900 (no brand).
Contador opcional a la derecha: mono 11 ink-500, sin pill.
```

No usamos tabs con fondo pintado. La regla de subrayado gruesa es la firma.

### 9.18. Tooltip

- bg inverse (ink-950 en claro, paper en oscuro), radius 0, padding 6 10.
- mono 11 / 600 / tracking 0.05em, texto inverse.
- Arrow 6 px inverse.
- Delay 300 ms abrir, 80 ms cerrar.

### 9.19. Empty state

- Ilustración monocroma simple: marca de registro grande o gota vacía.
- Título grotesk 18/700.
- Texto secondary 14.
- CTA primario o ghost abajo.
- No usar imágenes stock, no usar ilustraciones de colores.

### 9.20. Spinner / skeleton

- Spinner: cuadrado 16/20/24 rotando (no círculo). Border 2 px con 3 lados
  transparent, 1 lado current. Se lee "barra girando".
- Skeleton: bloques rectangulares `bg-ink-100` con shimmer horizontal
  sutil. No rounded.

### 9.21. Pagination (standalone)

- Ya cubierto en tabla; cuando es standalone (cards de cotizaciones) usa el
  mismo patrón mono.

### 9.22. Sidebar (nav)

```
Ancho: 280 px (expanded) / 72 px (collapsed).
bg: var(--bg-inverse) = ink-950 (en claro y oscuro).
Header (logo): 72 px, border-bottom 1 px rgba(white, .07).
  isotipo 32 px + wordmark Syne 22/700 blanco.
  Debajo kicker mono 10 uppercase: "IMPRENTAS · CORE" rgba(white,.45).
Grupos:
  label del grupo: mono 10 uppercase tracking 0.14em rgba(white, .35),
  padding 14 24 8.
Item:
  alto 44 px, padding horizontal 20 px (4 px de indent por ícono).
  Inactivo: texto rgba(white, .65), ícono rgba(white, .55).
  Hover: bg rgba(white, .05), texto blanco puro.
  Activo:
    bg rgba(white, .08),
    border-left 3 px con el gradiente --grad-press (la ÚNICA vez que el
    gradiente aparece fuera del logo / línea de tensión),
    texto blanco, ícono blanco.
Collapsed (72 px):
  solo íconos centrados 20 px, tooltip portal al hover.
Footer:
  bloque de usuario: avatar iniciales 36×36 cuadrado bg rgba(white,.08),
  nombre grotesk 13 blanco, rol mono 10 uppercase rgba(white,.45),
  dropdown hacia arriba con: Perfil · Cambiar password · Theme toggle · Logout.
```

### 9.23. Topbar

```
Sticky top 0, alto 72 px, bg paper 92 % + backdrop-blur 12 px.
Border-bottom 1 px rule.
Left:
  Breadcrumb kicker mono 10 uppercase → página.
  H1 tx-page-title + sub-kicker tx-meta.
Right:
  Reloj (hora mono 15/700 + fecha mono 10).
  Chip de tipo de cambio SUNAT (ya existe, respetamos).
  Badge SUNAT sync (ya existe).
  Botones acción contextuales (secundario/ghost).
  Avatar user (link a perfil).
Micro-detalle: la línea de tensión del gradiente va pegada arriba del topbar
  (2 px altura, full width, z-index 100).
```

### 9.24. Formularios (composición)

Reglas duras:
- Grid de 2 columnas en desktop, 1 en móvil. Columnas de 12 pueden partirse
  6/6, 4/8, etc.
- Cada campo ocupa una "fila lógica" con label arriba + input + helper/error.
- Grupo de campos con `fieldset.form-section` con `legend` en mono 11
  uppercase + border-top 1 hair arriba.
- Botones del formulario siempre en el **footer fijo** del modal / de la
  card, no flotando en el body.
- Autosave vs guardar explícito se marca con badge mono "AUTOGUARDADO · 10:02".

---

## 10. Blueprints por página

### 10.1. Login (PRIORIDAD ALTA — dolor actual)

**Problema actual:** mitad izquierda con texto largo, logo repetido dos veces,
copy publicitario ("La imprenta moderna empieza aquí") que no corresponde
a un login B2B donde ya sabes lo que vendes.

**Propuesta:**
```
Layout: 45 / 55 (izquierda = press panel / derecha = login).
La base es `bg-inverse` (ink-950) a la izquierda con `tech-grid`.

IZQUIERDA (bg ink-950):
  Header pegado arriba:
    [isotipo 40 px + wordmark Syne 28/700 blanco]
  Centro (mid-section, alineado vertical al medio):
    Kicker mono 10 uppercase brand-500: "CORE · OPERATIVO"
    Título grotesk 44 / 300 blanco, 2 líneas MÁXIMO:
      "Facturación de
       alto rendimiento."
    (El "alto rendimiento" va en 44/800 blanco. Contraste de pesos editorial.)
    Debajo, bloque de 2 stats con border-top rgba(white,.08) pt 24:
      LATENCIA_EMISIÓN     UPTIME_SUNAT
      3.2s                 99.2%
      ambos en mono 32, mini kicker mono 10 rgba(white,.45) arriba.
  Footer:
    Dot verde animado + "GATEWAY SUNAT CONECTADO" mono 10 uppercase.
    Versión a la derecha: mono 10 brand-500 "v2.4.0".
  Decorativo:
    Marcas de corte en las 4 esquinas (rgba(white, .20), 1 px, 16 px).

DERECHA (bg paper):
  En top-right absoluto: theme-toggle (btn-icon).
  Card central max-width 420 px, sin border (vive en el papel).
  Elementos dentro:
    kicker mono 10 uppercase ink-500: "ACCESO"
    H1 grotesk 28/700 ink-900: "Iniciar sesión"
    Tagline tx-meta ink-500: una sola línea — "Ingresa a tu panel Inkora"
    (divider 24 px de aire)
    Campo email (label mono 10 + input)
    Campo password (con toggle eye btn-icon a la derecha)
    Row: checkbox "Mantener sesión" (ink-900 grotesk 13) + link ghost "¿No puedes ingresar?"
    btn-cta-press full-width 48 px: "ENTRAR A INKORA →"
    (divider sutil hair)
    Footnote mono 10 uppercase center: "v2.4.0 · INKORA · LIMA"

Interacciones:
  - Focus del email → campo se vuelve paper puro con ring brand y en el
    label aparece una registration-mark a la izquierda (guiño visual).
  - Submit loading → botón a "PROCESANDO…" en mono con spinner cuadrado.
  - Error → alert banner en la parte superior del card (no toast).
  - Auto-focus en email al cargar.
```

### 10.2. Dashboard

```
Topbar:
  Kicker "CENTRO DE MANDO" + H1 "Dashboard" + kicker fecha.
  Right: chip tipo cambio + badge SUNAT + reloj.

Hero row (3 tiles):
  Tile A — "Vendido hoy" (BRAND ACENT, único que usa color de marca)
    display-2xl 56 Syne ink-900. "S/ 12,480.00"
    sparkline mono abajo.
    Kicker mono: "VS. AYER +12.4%".
  Tile B — "Pendiente de cobro" (warning)
  Tile C — "Vencida > 30d" (error, con registration-mark animada si > 0)

Row 2 (4 KPIs secundarios):
  Cotizaciones abiertas · Facturas hoy · Boletas hoy · Clientes nuevos mes.
  Todos en mismo formato metric-card, variant brand o neutral.

Row 3:
  Left 8/12: "Vencidas" — tabla densa de 8 filas con acciones reveal en hover.
  Right 4/12: "Últimos eventos SUNAT" — feed tipo ledger, mono 12,
    cada entry con timestamp + folio + estado semántico.

Fondo del dashboard: tech-grid visible al 3 %.

NO se usa glass blur, NO se usan gradientes de cards, NO pill badges.
```

### 10.3. Cotizaciones (listado)

```
Topbar: H1 "Cotizaciones" + chip contador mono "142 ABIERTAS · 38 FACTURADAS".
Actions topbar right: btn-secondary "EXPORTAR" + btn-primary "+ NUEVA COTIZACIÓN".

Filtro row sticky:
  Búsqueda (input con ícono lupa) 1/3.
  CustomSelect "Estado" | CustomSelect "Cliente" | DatePicker "Rango".
  Reset ghost "LIMPIAR FILTROS".

Tabla:
  Columnas: FOLIO (mono) · FECHA (mono) · CLIENTE (grotesk) ·
    ITEMS (#, mono) · MONEDA · TOTAL (tx-amount right) · ESTADO (badge) ·
    acciones reveal.
  Fila alt para "FACTURADA" con border-left 2 px success.
  Hover: reveal [ver, editar, duplicar, PDF, compartir WhatsApp].

Paginación sticky footer mono.
```

### 10.4. Cotización detalle (wide modal / page)

Este es el documento rey. Modal-xl (1120 px):
```
Header:
  folio-stamp "C001-00128" arriba izquierda.
  Título "Cotización para [Razón Social]" grotesk 22.
  Estado badge en su esquina.
  Close btn-icon.
Metadatos (2 col grid):
  Fecha, Moneda, Vendedor, Vencimiento — todos como tx-meta.
Ledger (items):
  Tabla editable spreadsheet-like:
    CANT · PRODUCTO · P. UNIT · DESC% · IGV · SUB · TOTAL.
    Celda en focus → bg paper + box-shadow inset 2 px ink-900.
    Última fila "+ AGREGAR ÍTEM" ghost full-width con icon plus.
Liquidación (sticky bottom-right):
  Block anchored:
    SUBTOTAL · DESC · IGV · TOTAL (total en display-lg 36 mono 800 right).
Acciones footer:
  [ghost CANCELAR] [secondary GUARDAR BORRADOR] [primary EMITIR →].

Si ya está facturada:
  La tabla es read-only; badge FACTURADA arriba; aparece botón "VER FACTURA →"
  que abre la factura vinculada en drawer lateral.
```

### 10.5. Comprobante nuevo (factura / boleta)

```
Wizard en 3 pasos con stepper mono-styled (no círculos rellenos, son cuadros
numerados con conector gruesa ink-900):
  [01] EMISOR → [02] RECEPTOR + ITEMS → [03] CONFIRMAR + EMITIR.

Paso 1 mínimo (suele autollenarse con datos del tenant).
Paso 2 idéntico al detalle de cotización (ledger spreadsheet).
Paso 3:
  Preview del documento estilo "overprint":
    bg paper, fuente mono, ledger rules dashed, folio-stamp.
    Se ve literalmente como un impreso antes de emitir.
  Abajo: alert banner info "Al emitir, el documento se envía a SUNAT
  y no puede editarse."
  btn-cta-press "EMITIR A SUNAT →".
```

### 10.6. Facturas / Boletas / Notas / Percepciones / Retenciones / Bajas / Reversiones

Todas comparten el **mismo patrón de listado** que Cotizaciones. Cambia:
- Topbar kicker + título.
- Columnas específicas del tipo.
- Estados posibles (envío SUNAT, aceptada, rechazada, anulada).

**Uniformidad:** no se inventa layout nuevo por página. Si necesita algo
propio, se agrega **una columna extra** o **una acción extra**, no un chrome
diferente.

### 10.7. Cobranza

```
Hero:
  Metric gigante — "S/ 48,720.00 POR COBRAR" display-2xl Syne ink-900.
  Sub: "EN 38 FACTURAS · PROMEDIO 12 DÍAS DE MORA" tx-meta.

Vista principal: tabla con aging badges:
  CLIENTE · FOLIO · EMITIDA · VENCE · DÍAS MORA (aging) · SALDO · [ACCIONES].
  Ordenada por defecto por días de mora DESC.
  Hover reveal: btn-icon "REGISTRAR PAGO" + btn-icon "NOTIFICAR WHATSAPP".

Modal de registrar pago:
  modal-md.
  Campos: Monto (mono tabular right) · Fecha · Medio de pago (CustomSelect
    con íconos mono) · Referencia · Nota.
  Footer primary "REGISTRAR".
```

### 10.8. Clientes

```
Layout de tabla + drawer lateral:
  Lista a la izquierda (tabla).
  Seleccionar un cliente → abre drawer 440 px con ficha + tabs
  (General · Documentos · Cobranza · Notas internas).
Tabs mono uppercase. Ficha con folio-stamp en cabecera con el RUC/DNI.
En General: campos read-only en fondo ink-50 cuando vienen de SUNAT
(lookup RUC) y campos editables en paper.
```

### 10.9. Productos

Similar a Clientes pero con foto de producto miniatura 64×64 cuadrada,
border 1 px rule, sin radius. El drawer de ficha muestra histograma de
ventas (barras mono sin color).

### 10.10. Guías de remisión

```
Lista:
  Columnas: SERIE · EMISIÓN · ORIGEN → DESTINO · ESTADO · BULTOS/KG.
  El campo origen→destino es gráfico: mini ruta con 2 puntos ink-900 y
  línea dashed. Registration-mark en medio.

Detalle (modal-lg):
  Split 50/50 ORIGEN | DESTINO.
  Izquierda bg paper, derecha bg ink-50 (para distinguir cognitivamente).
  Campos con sufijos físicos: 12.5 KGM · 0.8 M3.
  Todo el bloque de magnitudes en mono right-aligned.
  Botón CTA "EMITIR GUÍA →" en footer.
```

### 10.11. Resumen diario / Reversiones / Bajas

Usar el mismo listado que cotizaciones, con una barra de herramientas
superior específica (ej. "Generar resumen del día X", "Anular documentos
seleccionados") que abre modal de confirmación con **preview del envío
SUNAT** en fuente mono tipo terminal.

### 10.12. Configuración

```
Layout interno: tabs horizontales (chrome § 9.17):
  GENERAL · EMPRESA · FACTURACIÓN · SERIES · IMPUESTOS · USUARIOS · INTEGRACIONES · APARIENCIA.

Cada tab: formulario con secciones (fieldset) y botones fijos en el footer
de la página, no repartidos por sección.

Datos read-only:
  Se muestran como "folio-stamp" o caja bloqueada bg ink-50, nunca como
  input active.
  Ej.: RUC, email de acceso, rol.

Banner de permisos insuficientes (rol vendedor viendo tab admin):
  alert banner dark (bg ink-900 + texto paper) en mono uppercase con
  registration-mark roja.
```

### 10.13. Cambio de contraseña

Modal-sm con solo 3 campos (actual, nueva, confirmar). Indicador de
fortaleza: 4 cuadros monoespaciados que se rellenan (no barra de colores).

### 10.14. Superadmin

Panel técnico estilo "dev console":
- Fondo tech-grid más marcado (6 %).
- Listas de tenants con mono heavy.
- Chips de estado "CONFIGURADO · PENDIENTE · NO CARGADO" tal como ya se
  definió en `nuevo_diseño.md`.
- Alertas en cajas oscuras bg-ink-900 + texto paper.

### 10.15. PDF Designer

Preservar el preview tipo WYSIWYG en canvas claro 1:1. La toolbar lateral
izquierda usa el chrome de sidebar oscuro (bg ink-950) con el mismo patrón
de items mono + ícono. Las opciones (fuente, color, logo) respetan los
tokens del sistema; NO permitimos importar colores arbitrarios para el PDF
salvo que sea el logo del cliente.

---

## 11. Accesibilidad y contraste

- **Contraste AA+:** todo el body text cumple ≥ 4.5:1. Verificado:
  `ink-900 #111118` sobre `paper #FAFAF5` → 17.9:1. `brand-600 #4F46E5`
  sobre paper → 6.8:1 ✓.
- **Focus visible OBLIGATORIO** en todo elemento interactivo. `:focus-visible`
  usa el `shadow-focus` (ring ink + ring brand). Nunca `outline: none`
  sin reemplazo.
- **Target size:** botones/inputs ≥ 44×44 px en formularios. Íconos
  interactivos mínimos 36×36 px.
- **Color no es único portador de información:** los estados de documento
  tienen **texto** ("FACTURADA") y **borde** además del color. Las aging
  badges llevan el número de días, no solo el color.
- **`prefers-reduced-motion`:** ya manejado en base. Respetamos.
- **Roles ARIA** en modales (`dialog`), toasts (`status/alert`), tabs,
  comboboxes (`combobox` + `listbox`).

---

## 12. Responsive

### 12.1. Breakpoints
```
sm  ≥ 640  — teléfono horizontal
md  ≥ 768  — tablet
lg  ≥ 1024 — desktop (primer breakpoint donde sidebar aparece fija)
xl  ≥ 1280
2xl ≥ 1536
```

### 12.2. Comportamiento clave
- **< lg:** sidebar se convierte en drawer lateral que se abre con botón
  hamburguesa en topbar. La línea de tensión se queda arriba.
- **Tablas anchas:** en < md se convierten a "cards stacked" con el mismo
  orden de información pero en vertical. El folio y el total quedan en la
  esquina superior derecha de cada card.
- **Modales:** en < md ocupan 100 % de pantalla con safe-area insets. El
  footer de acciones se fija abajo con botones full-width apilados.
- **Login:** < md colapsa a vertical — press panel arriba compacto (96 px)
  con isotipo + línea de estado SUNAT en una sola fila, y form abajo.

---

## 13. Tokens extra — efectos y utilidades

### 13.1. Utilidades nuevas a agregar

```css
.u-tabular      { font-variant-numeric: tabular-nums; }
.u-mono-caps    { font-family: var(--font-mono); text-transform: uppercase; letter-spacing: 0.1em; }
.u-ledger-rule  { border-top: 1px dashed var(--border-hair); }
.u-noise        { /* opcional, 2-3% grain sobre paper para feel editorial */ }
.u-tension-line { /* linea del gradiente animada */ }
```

### 13.2. Noise (opcional, feature flag)

Una textura muy sutil (2–3 %) tipo grano sobre el `paper`. Da sensación
editorial/impresa. Se activa con `data-theme-print="true"` en `<html>` y
se puede toggle desde Configuración > Apariencia. Por defecto: **off**
(no queremos que sienta "retro" si no se quiere).

---

## 14. Plan de implementación por fases

### Fase 0 — Diseño base (1–2 días)
- [ ] Actualizar `tailwind.config.js`: eliminar los `borderRadius.md/lg/xl/2xl`
      (dejar solo `xs` y `full` para avatars); ampliar tokens de `ink`.
- [ ] Actualizar `app.css`: nuevos CSS vars (sección 3), nuevas utilidades
      (sección 13).
- [ ] Agregar fuente JetBrains Mono y Syne vía Google Fonts (Syne ya en
      `font-brand`).

### Fase 1 — Componentes base uniformes (2–3 días)
- [ ] Rehacer `btn-*` (primary/secondary/ghost/danger/icon/cta-press).
- [ ] Rehacer `.input`, `.select`, `.textarea`.
- [ ] Rehacer `CustomSelect`, `ClientCombobox`, `ProductCombobox` al nuevo chrome.
- [ ] Rehacer `DatePicker` al nuevo chrome.
- [ ] Rehacer `Badge` (status / aging / tech).
- [ ] Rehacer `Modal`, `Toast`.
- [ ] Introducir `.folio-stamp`, `.crop-mark`, `.registration-mark`, `.ledger-row`.

### Fase 2 — Shell (1 día)
- [ ] Sidebar (nuevo chrome press room con grad-press en item activo).
- [ ] Topbar (kicker + H1 + reloj + chips).
- [ ] Línea de tensión 2 px con `--grad-press`.

### Fase 3 — Login (0.5 día)
- [ ] Login 45/55, press panel izquierda, card minimal derecha.
- [ ] Bloque de stats "LATENCIA_EMISIÓN / UPTIME_SUNAT" (los valores pueden
      ser read-only o vivir de `/health`).

### Fase 4 — Dashboard (1 día)
- [ ] Hero row 3 tiles.
- [ ] KPIs secundarios.
- [ ] Tabla de vencidas con hover-reveal.
- [ ] Feed de eventos SUNAT.

### Fase 5 — Documentos transaccionales (2 días)
- [ ] Cotizaciones listado.
- [ ] Cotización detalle (modal-xl con ledger spreadsheet).
- [ ] Comprobante nuevo (wizard 3 pasos + preview overprint).
- [ ] Facturas / Boletas / Notas (listados con patrón uniforme).

### Fase 6 — Cobranza y Guías (1 día)
- [ ] Cobranza con aging badges y modal de pago.
- [ ] Guías con split origen/destino.

### Fase 7 — Catálogo y Configuración (1 día)
- [ ] Clientes (tabla + drawer).
- [ ] Productos (tabla + drawer).
- [ ] Configuración (tabs + formularios).
- [ ] Superadmin.

### Fase 8 — Pulido (0.5 día)
- [ ] Empty states de todas las vistas.
- [ ] Skeletons.
- [ ] Audit de contraste (par por par).
- [ ] Testing en móvil / tablet.
- [ ] Toggle de `u-noise` en Configuración > Apariencia.

**Total estimado:** ~9–10 días de front-end concentrado. Prioriza **Fase 0 → 3**
primero (base + login) para ver el nuevo lenguaje en menos de una semana,
después el resto se propaga rápido porque los componentes ya están listos.

---

## 15. Checklist de "no-ai-looking"

Antes de dar por bueno cualquier pantalla, pasar por esta lista:

- [ ] ¿Hay algún `border-radius > 4px`? → bórralo.
- [ ] ¿Hay algún gradiente fuera del logo y la línea de tensión? → bórralo.
- [ ] ¿Hay sombras con blur > 4 px y tinte de color? → cámbialas a offset sólido.
- [ ] ¿Hay algún botón con bg pastel y texto en color? → reemplázalo por ink/paper.
- [ ] ¿Hay labels en Title Case? → pásalos a `UPPERCASE mono tracking 0.1em`.
- [ ] ¿Hay cifras en grotesk? → pásalas a mono tabular.
- [ ] ¿Hay iconos en 2+ pesos distintos o librerías distintas? → normaliza a Lucide 1.5 px.
- [ ] ¿El acento de marca ocupa > 5 % de la pantalla? → reduce.
- [ ] ¿Hay algún `rounded-full` en algo que no sea avatar? → cuádralo.
- [ ] ¿Hay emoji? → reemplázalo por ícono Lucide.

---

## 16. Lo que queda fuera (explícito)

- **Ilustraciones 3D / glass / neon.** No.
- **Imágenes stock de personas trabajando.** No.
- **Dark mode "azul marino corporate".** No. Nuestro dark es **press room
  negro azulado profundo** (#0B0B14).
- **Animaciones de partículas, blobs, SVG orgánicos flotando.** No.
- **Tooltips con gradiente o glass.** No.

---

## 17. Inspiraciones declaradas

Para contextualizar el equipo de diseño/desarrollo cuando revise:
- **Linear** por la densidad y los atajos, pero con menos pastel y más tinta.
- **Vercel / v0** por el monospaciado y la precisión, pero con más vida editorial.
- **Swiss poster design** (Müller-Brockmann) por la grilla visible.
- **Peter Saville / Factory Records** por el brutalismo tipográfico.
- **Figma dev mode** por las marcas y los registros.
- **SUNAT / SOL** por razones funcionales (nuestros usuarios viven ahí) —
  pero ofreciendo el **contrario estético**: lo que ellos sufren en Java
  Applet del 2003, aquí se resuelve con editorial limpio.

---

## Apéndice A — Mapeo rápido de cambios en archivos

| Archivo | Acción |
|---|---|
| `frontend/tailwind.config.js` | Ampliar tokens `ink`, reducir `borderRadius`, registrar fuente JetBrains Mono |
| `frontend/src/app.css` | Reemplazar bloque `:root` y componentes `btn-*`, `.input`, `.select` con los de este plan |
| `frontend/src/index.html` | Agregar `<link>` de JetBrains Mono y Syne (ya hay Inter/Space Grotesk) |
| `frontend/src/components/ui/CustomSelect.jsx` | Re-skin (sin cambiar lógica) |
| `frontend/src/components/ui/DatePicker.jsx` | Re-skin |
| `frontend/src/components/ui/Modal.jsx` | Re-skin + crop-marks |
| `frontend/src/components/ui/Badge.jsx` | Re-skin aging + status + tech |
| `frontend/src/components/Sidebar.jsx` | Re-skin press room + línea activa gradient |
| `frontend/src/layouts/AppLayout.jsx` | Agregar línea de tensión 2 px top |
| `frontend/src/pages/Login.jsx` | Rehacer layout 45/55 + stats SUNAT |
| `frontend/src/pages/Dashboard.jsx` | Hero row + rework KPIs |
| `frontend/src/pages/CotizacionDetalle.jsx` | Ledger spreadsheet + liquidación sticky |
| `frontend/src/pages/CotizacionesPage.jsx` | Tabla con hover-reveal |
| `frontend/src/pages/ClientesPage.jsx` | Tabla + drawer |
| `frontend/src/pages/ProductosPage.jsx` | Tabla + drawer |
| `frontend/src/pages/ComprobanteNuevoPage.jsx` | Wizard 3 pasos |
| `frontend/src/pages/CobranzaPage.jsx` | Aging + hover-reveal |
| `frontend/src/pages/GuiasPage.jsx` + `GuiaDetalle.jsx` | Split origen/destino |
| `frontend/src/pages/ConfiguracionPage.jsx` | Tabs editoriales |
| `frontend/src/pages/SuperadminPage.jsx` | Dev console chrome |

## Apéndice B — Paleta compacta (copy-paste)

```
INK       #0A0A12  #111118  #1A1A24  #2A2A38  #3F3F52  #5E5E75
          #8A8AA0  #B5B5C8  #D4D4E0  #E8E8F0  #F2F2F8
PAPER     #FAFAF5
BRAND     #4F46E5  (hover #3730A3 / subtle #E0E7FF)
GRAD      #2563EB → #7C3AED → #D946EF   (logo + tension line only)
SUCCESS   #047857 on #D1FAE5
WARNING   #B45309 on #FEF3C7
ERROR     #B91C1C on #FEE2E2
INFO      #0369A1 on #E0F2FE
```

---

*Fin del plan. Firma: Inkora Press Room · v1.0 · 2026.*
