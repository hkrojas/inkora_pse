
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
