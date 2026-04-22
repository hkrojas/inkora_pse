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
