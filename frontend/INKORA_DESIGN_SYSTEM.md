# Inkora — Especificación de Diseño UI/UX

**Versión:** 1.0  
**Proyecto base revisado:** `hkrojas/facturacion-sunat`  
**Stack recomendado:** React + Vite + Tailwind CSS  
**Objetivo:** transformar la interfaz actual en un sistema visual moderno, consistente, intuitivo y preparado para modo claro/oscuro.

---

## 1. Diagnóstico del proyecto actual

### 1.1. Lo que ya existe

El proyecto ya tiene una base funcional correcta para crecer:

- Frontend con **React 18**, **Vite**, **React Router**, **React Hook Form**, **Lucide React**, **Heroicons**, `react-hot-toast`, `clsx`, `tailwind-merge` y **Tailwind CSS**.
- Rutas públicas:
  - `/login`
  - `/register`
- Rutas protegidas:
  - `/`
  - `/cotizaciones`
  - `/cotizaciones/nueva`
  - `/cotizaciones/editar/:id`
  - `/clientes`
  - `/productos`
  - `/configuracion`
- Componentes existentes:
  - `AuthLayout`
  - `Input`
  - `DashboardLayout`
  - `Sidebar`
  - `Card`
  - `ProtectedRoute`
  - `LoadingSpinner`
- Módulos principales:
  - Dashboard
  - Cotizaciones
  - Clientes
  - Productos
  - Configuración

### 1.2. Problemas visuales detectados

#### Problema 1: identidad inconsistente

Actualmente aparecen textos como **FacturaPro**, pero el producto que estamos diseñando es **Inkora**.

**Decisión:** todo el sistema debe migrar a una identidad única: **Inkora**.

Ejemplos de reemplazo:

| Actual | Nuevo |
|---|---|
| FacturaPro | Inkora |
| FacturaPro Enterprise | Inkora Cloud |
| Infraestructura de Facturación Segura SSL | Plataforma segura de facturación y gestión comercial |
| Control Total Fiscal | Control total de ventas, facturación y cobranza |

---

#### Problema 2: App.css conserva estilos base de Vite

El archivo `App.css` mantiene estilos de plantilla inicial como:

```css
#root {
  max-width: 1280px;
  margin: 0 auto;
  padding: 2rem;
  text-align: center;
}
```

Esto limita una aplicación SaaS real, porque centra todo el sistema y agrega padding global innecesario.

**Decisión:** eliminar esos estilos globales y mover el diseño a tokens reutilizables.

---

#### Problema 3: falta una escala visual unificada

El proyecto usa clases Tailwind directamente en cada componente, pero aún no hay una guía clara para:

- Colores
- Botones
- Inputs
- Tarjetas
- Estados
- Alertas
- Tablas
- Modo oscuro
- Microcopy
- Empty states
- Modales
- Layout responsive

**Decisión:** crear un sistema de diseño base para que todo componente nuevo siga las mismas reglas.

---

## 2. Principios de diseño de Inkora

Inkora debe sentirse como un sistema de facturación moderno para imprentas y negocios gráficos, no como un ERP pesado.

### 2.1. Principios principales

1. **Claridad antes que decoración**  
   Cada pantalla debe responder: qué estoy viendo, qué debo hacer y qué pasará después.

2. **Una acción primaria por pantalla**  
   Ejemplo: en Facturas, la acción principal es `+ Nueva factura`.

3. **Lenguaje humano, no robótico**  
   Evitar: `Error`, `Aceptar`, `No hay datos`.  
   Usar: `No se pudo emitir la factura`, `Emitir factura`, `Aún no tienes facturas`.

4. **Prevención de errores fiscales**  
   Antes de emitir comprobantes, el sistema debe advertir y confirmar.

5. **Operación rápida**  
   El usuario debe poder crear cliente, cotización, factura o guía sin sentirse perdido.

6. **Confianza visual**  
   La UI debe transmitir seguridad, orden, cumplimiento tributario y control operativo.

7. **Modo oscuro real**  
   No basta invertir colores. El modo oscuro debe mantener jerarquía, legibilidad y estados claros.

---

## 3. Personalidad visual

### 3.1. Concepto

Inkora debe sentirse:

- Profesional
- Rápido
- Confiable
- Moderno
- Fiscalmente seguro
- Fácil de aprender
- No intimidante

### 3.2. Referencias de estilo

La dirección visual combina:

- **QuickBooks / Xero:** dashboard claro, KPIs financieros y tarjetas.
- **Stripe:** estética premium, navegación limpia y estados bien definidos.
- **Qonto / fintech europea:** diseño confiable, espacios amplios, bordes suaves.
- **Zoho Invoice:** enfoque práctico para facturación y documentos.
- **Billin / Fatture in Cloud:** claridad para facturación electrónica.

---

## 4. Arquitectura visual de la aplicación

### 4.1. Layout principal

La aplicación debe usar una estructura base:

```txt
┌─────────────────────────────────────────────┐
│ Sidebar │ Header / Topbar                   │
│         ├───────────────────────────────────┤
│         │ Contenido principal               │
│         │ Cards, tablas, formularios        │
└─────────────────────────────────────────────┘
```

### 4.2. Sidebar

Debe ser fija en desktop y colapsable en móvil.

#### Menú recomendado

```txt
Principal
- Dashboard
- Clientes
- Cotizaciones
- Facturas
- Guías
- Cobranza
- Productos

Gestión
- Reportes
- Configuración
- Seguridad
```

#### Naming recomendado

| Actual | Recomendado |
|---|---|
| Resumen | Dashboard |
| Ventas y Doc. | Cotizaciones |
| Productos | Catálogo |
| Configuración | Configuración |
| Cerrar Sesión | Cerrar sesión |

---

## 5. Tokens de diseño

Los tokens son valores base que se reutilizan en todo el sistema.

---

## 6. Colores — modo claro

### 6.1. Paleta principal

```css
:root {
  --color-bg: #f5f7fb;
  --color-surface: #ffffff;
  --color-surface-soft: #f8fafc;
  --color-surface-muted: #f1f5f9;

  --color-text: #0f172a;
  --color-text-muted: #64748b;
  --color-text-soft: #94a3b8;

  --color-border: #e2e8f0;
  --color-border-strong: #cbd5e1;

  --color-primary: #2563eb;
  --color-primary-hover: #1d4ed8;
  --color-primary-soft: #dbeafe;
  --color-primary-text: #ffffff;

  --color-success: #16a34a;
  --color-success-soft: #dcfce7;
  --color-success-text: #166534;

  --color-warning: #d97706;
  --color-warning-soft: #fef3c7;
  --color-warning-text: #92400e;

  --color-danger: #dc2626;
  --color-danger-soft: #fee2e2;
  --color-danger-text: #991b1b;

  --color-purple: #7c3aed;
  --color-purple-soft: #ede9fe;
  --color-purple-text: #5b21b6;
}
```

### 6.2. Uso de colores

| Token | Uso |
|---|---|
| `primary` | Acción principal, enlaces, foco, navegación activa |
| `success` | Pagado, aceptado por SUNAT, operación correcta |
| `warning` | Pendiente, revisión, datos incompletos |
| `danger` | Error, anulación, vencido, acción destructiva |
| `purple` | Cotización aprobada, estado especial |
| `surface` | Cards, formularios, modales |
| `surface-soft` | Fondos secundarios y tablas |

---

## 7. Colores — modo oscuro

El modo oscuro debe ser elegante y operativo, no simplemente negro.

```css
.dark {
  --color-bg: #020617;
  --color-surface: #0f172a;
  --color-surface-soft: #111827;
  --color-surface-muted: #1e293b;

  --color-text: #f8fafc;
  --color-text-muted: #cbd5e1;
  --color-text-soft: #94a3b8;

  --color-border: #1e293b;
  --color-border-strong: #334155;

  --color-primary: #60a5fa;
  --color-primary-hover: #3b82f6;
  --color-primary-soft: rgba(37, 99, 235, 0.20);
  --color-primary-text: #020617;

  --color-success: #22c55e;
  --color-success-soft: rgba(34, 197, 94, 0.16);
  --color-success-text: #bbf7d0;

  --color-warning: #f59e0b;
  --color-warning-soft: rgba(245, 158, 11, 0.16);
  --color-warning-text: #fde68a;

  --color-danger: #f87171;
  --color-danger-soft: rgba(248, 113, 113, 0.16);
  --color-danger-text: #fecaca;

  --color-purple: #a78bfa;
  --color-purple-soft: rgba(167, 139, 250, 0.16);
  --color-purple-text: #ddd6fe;
}
```

### 7.1. Reglas para modo oscuro

- Evitar `#000000` como fondo general.
- Usar `#020617` como fondo base.
- Las tarjetas deben ser `#0f172a`.
- Los bordes deben ser sutiles: `#1e293b`.
- No usar sombras negras fuertes. En oscuro, preferir bordes y contraste.
- Los estados deben mantenerse reconocibles:
  - Pagado: verde suave
  - Vencido: rojo suave
  - Pendiente: amarillo suave
  - Enviado: azul suave

---

## 8. Tipografía

### 8.1. Fuente recomendada

Usar **Inter** o fallback del sistema.

```css
font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
```

### 8.2. Escala tipográfica

| Uso | Tamaño | Peso | Tracking | Ejemplo |
|---|---:|---:|---:|---|
| Display | 36-46px | 850 | -0.06em | Facturación |
| Título página | 28-34px | 850 | -0.05em | Crea una factura |
| Título tarjeta | 18-22px | 800 | -0.03em | Resumen de cobranza |
| Texto cuerpo | 15px | 400-500 | normal | Revisa tus ventas... |
| Label | 12-13px | 750-800 | 0.08em | RUC |
| Helper | 13px | 400-500 | normal | Este dato aparecerá en el PDF |
| Error | 13px | 700 | normal | El RUC no es válido |
| Botón | 14px | 800 | -0.01em | Emitir factura |

### 8.3. Ejemplo CSS

```css
.text-display {
  font-size: 2.5rem;
  line-height: 1.05;
  font-weight: 850;
  letter-spacing: -0.06em;
}

.text-page-title {
  font-size: 2rem;
  line-height: 1.12;
  font-weight: 850;
  letter-spacing: -0.05em;
}

.text-body {
  font-size: 0.9375rem;
  line-height: 1.65;
  color: var(--color-text-muted);
}
```

---

## 9. Espaciado

### 9.1. Escala

| Token | Valor | Uso |
|---|---:|---|
| `space-1` | 4px | separación mínima |
| `space-2` | 8px | ícono + texto |
| `space-3` | 12px | padding pequeño |
| `space-4` | 16px | padding base |
| `space-5` | 20px | separación entre grupos |
| `space-6` | 24px | padding de cards |
| `space-8` | 32px | separación de secciones |
| `space-10` | 40px | bloques grandes |
| `space-12` | 48px | pantallas principales |

### 9.2. Reglas

- Una card estándar usa `24px`.
- Una página usa `32px` en desktop y `16px` en móvil.
- Los formularios deben usar separación vertical de `16px` a `24px`.
- Las tablas deben usar `13px-16px` de padding por celda.

---

## 10. Bordes y radios

```css
--radius-sm: 10px;
--radius-md: 14px;
--radius-lg: 18px;
--radius-xl: 24px;
--radius-2xl: 32px;
```

| Componente | Radio |
|---|---:|
| Botón pequeño | 11px |
| Botón normal | 13-14px |
| Input | 14-16px |
| Card | 24-28px |
| Modal | 24px |
| Login card | 32px |
| Badge | 999px |

---

## 11. Sombras

### 11.1. Modo claro

```css
--shadow-soft: 0 8px 24px rgba(15, 23, 42, 0.06);
--shadow-card: 0 18px 45px rgba(15, 23, 42, 0.08);
--shadow-floating: 0 30px 80px rgba(15, 23, 42, 0.16);
--shadow-primary: 0 12px 24px rgba(37, 99, 235, 0.22);
```

### 11.2. Modo oscuro

```css
--shadow-soft: none;
--shadow-card: none;
--shadow-floating: 0 24px 70px rgba(0, 0, 0, 0.45);
--shadow-primary: 0 12px 24px rgba(96, 165, 250, 0.18);
```

En modo oscuro, el borde reemplaza gran parte de la sombra.

---

## 12. Botones

### 12.1. Principio

Cada botón debe indicar exactamente qué va a pasar.

Evitar:

```txt
Aceptar
OK
Continuar
Procesar
```

Preferir:

```txt
Emitir factura
Guardar borrador
Enviar por WhatsApp
Registrar pago
Anular comprobante
Descargar PDF
```

---

### 12.2. Variantes

#### Botón primario

Uso: acción principal de la pantalla.

```html
<button class="btn btn-primary">+ Nueva factura</button>
```

Texto recomendado:

- `+ Nueva factura`
- `Emitir comprobante`
- `Crear cotización`
- `Registrar pago`
- `Guardar cambios`

---

#### Botón secundario

Uso: acción útil, pero no principal.

```html
<button class="btn btn-secondary">Guardar borrador</button>
```

Texto recomendado:

- `Guardar borrador`
- `Vista previa`
- `Duplicar cotización`
- `Ver detalle`
- `Editar cliente`

---

#### Botón suave

Uso: acción contextual amable.

```html
<button class="btn btn-soft">Enviar por WhatsApp</button>
```

Texto recomendado:

- `Enviar por WhatsApp`
- `Enviar por correo`
- `Copiar enlace`
- `Recordar pago`

---

#### Botón fantasma

Uso: cancelar o cerrar sin enfatizar.

```html
<button class="btn btn-ghost">Cancelar</button>
```

Texto recomendado:

- `Cancelar`
- `Volver`
- `Cerrar`
- `Limpiar filtros`

---

#### Botón destructivo

Uso: anular, eliminar o cancelar documentos.

```html
<button class="btn btn-danger">Anular factura</button>
```

Texto recomendado:

- `Anular factura`
- `Eliminar cliente`
- `Cancelar guía`
- `Revocar acceso`

Debe estar acompañado de modal de confirmación.

---

### 12.3. Estados

| Estado | Ejemplo |
|---|---|
| Normal | `Emitir factura` |
| Hover | Subir 1px o cambiar tono |
| Loading | `Enviando...` + spinner |
| Disabled | `Sin cliente seleccionado` |
| Success | `Pago registrado` |
| Warning | `Revisar datos` |
| Danger | `Anular factura` |

---

### 12.4. CSS base

```css
.btn {
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  border-radius: 13px;
  border: 1px solid transparent;
  padding: 0 15px;
  font-size: 14px;
  font-weight: 800;
  letter-spacing: -0.01em;
  cursor: pointer;
  transition: 170ms ease;
  white-space: nowrap;
}

.btn:hover {
  transform: translateY(-1px);
}

.btn-primary {
  color: var(--color-primary-text);
  background: var(--color-primary);
  box-shadow: var(--shadow-primary);
}

.btn-primary:hover {
  background: var(--color-primary-hover);
}

.btn-secondary {
  color: var(--color-text);
  background: var(--color-surface);
  border-color: var(--color-border);
}

.btn-soft {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.btn-ghost {
  color: var(--color-text-muted);
  background: transparent;
}

.btn-danger {
  color: #fff;
  background: var(--color-danger);
}

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.52;
  transform: none;
  box-shadow: none;
}
```

---

## 13. Inputs y formularios

### 13.1. Estructura recomendada

```txt
Label
[ Input ]
Helper text / Error text
```

Ejemplo:

```txt
RUC
[ 20481234567 ]
Este dato se usará para emitir comprobantes electrónicos.
```

### 13.2. Labels

Los labels deben ser claros, cortos y específicos.

| Campo | Label recomendado |
|---|---|
| Cliente | Cliente |
| RUC | RUC |
| DNI | DNI |
| Razón social | Razón social |
| Dirección | Dirección fiscal |
| Teléfono | Teléfono |
| Email | Correo de facturación |
| Producto | Producto o servicio |
| Observación | Observaciones para el cliente |

---

### 13.3. Placeholders

El placeholder no reemplaza al label.

| Campo | Placeholder |
|---|---|
| Cliente | `Busca por RUC, DNI o razón social` |
| RUC | `Ej. 20481234567` |
| Email | `facturacion@cliente.com` |
| Producto | `Ej. Volantes A5 full color` |
| Observación | `Ej. Entrega estimada en 48 horas` |

---

### 13.4. Errores

Evitar culpar al usuario.

No usar:

```txt
RUC incorrecto.
Error de usuario.
Datos inválidos.
```

Usar:

```txt
El RUC debe tener 11 dígitos.
No encontramos este cliente. Puedes crearlo ahora.
La fecha de vencimiento no puede ser anterior a la fecha de emisión.
```

---

### 13.5. CSS base

```css
.form-field {
  display: grid;
  gap: 8px;
}

.form-label {
  font-size: 13px;
  font-weight: 800;
  color: var(--color-text);
}

.form-input {
  width: 100%;
  min-height: 44px;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  padding: 12px 13px;
  font-size: 14px;
  color: var(--color-text);
  background: var(--color-surface);
  outline: none;
  transition: 170ms ease;
}

.form-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.09);
}

.form-helper {
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.45;
}

.form-error {
  color: var(--color-danger);
  font-size: 13px;
  font-weight: 700;
}
```

---

## 14. Cards

### 14.1. Uso

Las cards se usan para agrupar:

- KPIs
- Formularios
- Tablas
- Accesos rápidos
- Alertas de sistema
- Resúmenes de cliente
- Resúmenes de factura

### 14.2. Card estándar

```css
.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 24px;
  padding: 24px;
  box-shadow: var(--shadow-soft);
}
```

### 14.3. Card de KPI

Debe tener:

- Label
- Valor
- Tendencia opcional
- Icono
- Estado o comparación

Ejemplo:

```txt
Ventas del mes
S/ 42,850.00
+12% vs mes anterior
```

Microcopy recomendado:

- `Ventas del mes`
- `Por cobrar`
- `Facturas vencidas`
- `Cotizaciones aprobadas`
- `Clientes activos`
- `Productos registrados`

---

## 15. Badges y estados

### 15.1. Estados de comprobante

| Estado interno | Texto visible | Color |
|---|---|---|
| `draft` | Borrador | Gris |
| `sent` | Enviada | Azul |
| `accepted` | Aceptada por SUNAT | Morado / Verde |
| `paid` | Pagada | Verde |
| `partial` | Pago parcial | Amarillo |
| `overdue` | Vencida | Rojo |
| `cancelled` | Anulada | Rojo / Gris |
| `rejected` | Rechazada | Rojo |

### 15.2. CSS base

```css
.badge {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border-radius: 999px;
  padding: 7px 10px;
  font-size: 12px;
  font-weight: 850;
}

.badge::before {
  content: "";
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: currentColor;
}

.badge-paid {
  color: var(--color-success-text);
  background: var(--color-success-soft);
}

.badge-draft {
  color: var(--color-text-muted);
  background: var(--color-surface-muted);
}

.badge-sent {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.badge-overdue {
  color: var(--color-danger-text);
  background: var(--color-danger-soft);
}

.badge-partial {
  color: var(--color-warning-text);
  background: var(--color-warning-soft);
}
```

---

## 16. Alertas

### 16.1. Tipos

| Tipo | Uso |
|---|---|
| Info | explicación o aviso neutro |
| Success | acción completada |
| Warning | falta algo o se requiere revisión |
| Danger | error o bloqueo |

### 16.2. Mensajes recomendados

#### Info

```txt
Factura guardada como borrador.
Puedes terminarla luego desde la sección de comprobantes.
```

#### Success

```txt
Comprobante aceptado.
SUNAT aceptó la factura. Ya puedes enviarla al cliente.
```

#### Warning

```txt
Falta método de pago.
Agrega una condición de pago para calcular correctamente la fecha de vencimiento.
```

#### Danger

```txt
No se pudo emitir la factura.
Revisa el RUC, la dirección fiscal y la conexión con el proveedor electrónico.
```

---

## 17. Toasts

### 17.1. Uso

Los toasts deben confirmar acciones sin interrumpir.

Ejemplos:

```txt
Cliente creado correctamente.
Cotización enviada por WhatsApp.
PDF descargado.
Factura guardada como borrador.
Pago registrado correctamente.
```

### 17.2. Reglas

- Duración: 3 a 5 segundos.
- No usar toasts para errores críticos que requieren decisión.
- Siempre que sea posible, agregar una acción:
  - `Ver`
  - `Abrir`
  - `Deshacer`

---

## 18. Tablas

### 18.1. Reglas

- Cabeceras en mayúsculas pequeñas.
- Filas con altura cómoda.
- Acción visible por fila.
- Estado con badge.
- Monto alineado a la derecha.
- No saturar con demasiadas columnas.

### 18.2. Tabla de facturas recomendada

Columnas:

```txt
Comprobante
Cliente
Estado
Emisión
Vence
Total
Acción
```

Ejemplo:

```txt
F001-000248 | Gráfica Norte SAC | Pagada | 20 abr | 22 abr | S/ 1,280.00 | Ver
```

### 18.3. Empty row

Si no hay datos:

```txt
Aún no hay movimientos recientes.
Crea una factura o convierte una cotización aprobada.
```

---

## 19. Empty states

### 19.1. Regla

Un empty state no debe decir solo “No hay datos”. Debe explicar qué falta y ofrecer una acción.

### 19.2. Ejemplos

#### Facturas

```txt
Aún no tienes facturas.
Crea tu primera factura electrónica usando un cliente registrado o una cotización aprobada.
[Crear primera factura]
```

#### Clientes

```txt
Aún no tienes clientes.
Registra tu primer cliente para emitir cotizaciones y comprobantes más rápido.
[Crear cliente]
```

#### Productos

```txt
Tu catálogo está vacío.
Agrega productos o servicios frecuentes para cotizar sin volver a escribirlos.
[Agregar producto]
```

#### Cobranza

```txt
No hay pagos pendientes.
Cuando una factura quede por cobrar, aparecerá aquí para darle seguimiento.
```

---

## 20. Modales

### 20.1. Cuándo usar modal

Usar modal solo para decisiones importantes:

- Anular factura
- Eliminar cliente
- Revocar acceso
- Emitir comprobante
- Cambiar configuración fiscal
- Confirmar envío a SUNAT

### 20.2. Modal destructivo

```txt
¿Anular esta factura?

Esta acción generará una comunicación de baja. La factura dejará de estar disponible como comprobante válido.

[Volver] [Sí, anular]
```

### 20.3. Modal de emisión

```txt
¿Emitir esta factura?

Revisaremos los datos del cliente, los productos y el total antes de enviarla a SUNAT.

[Revisar] [Emitir factura]
```

---

## 21. Login

### 21.1. Objetivo

El login debe transmitir seguridad sin parecer complejo.

### 21.2. Estructura

```txt
Panel visual izquierdo
- Logo
- Mensaje de valor
- Mini dashboard
- Estado del sistema

Formulario derecho
- Título
- Subtítulo
- Google/Microsoft opcional
- Email
- Contraseña
- Mantener sesión
- Recuperar acceso
- Entrar al dashboard
- Mensaje de seguridad
```

### 21.3. Textos recomendados

| Elemento | Texto |
|---|---|
| Título | Bienvenido de nuevo |
| Subtítulo | Ingresa al panel de tu imprenta para emitir comprobantes, revisar cobranza y continuar tus cotizaciones. |
| Email | Correo o usuario |
| Password | Contraseña |
| Remember | Mantener sesión en este equipo |
| Forgot | ¿Olvidaste tu contraseña? |
| CTA | Entrar al dashboard |
| Seguridad | Acceso protegido. Recomendado para cuentas con verificación en dos pasos y registro de actividad por usuario. |

---

## 22. Dashboard

### 22.1. Objetivo

El dashboard debe responder rápido:

- ¿Cuánto vendí?
- ¿Cuánto me deben?
- ¿Qué está vencido?
- ¿Qué debo hacer hoy?

### 22.2. KPIs recomendados

```txt
Ventas del mes
Por cobrar
Facturas vencidas
Cotizaciones aprobadas
Clientes activos
Productos registrados
```

### 22.3. Acciones rápidas

```txt
+ Nueva factura
+ Nueva cotización
Registrar pago
Crear cliente
```

### 22.4. Secciones

```txt
1. KPIs superiores
2. Gráfico de ventas / cobranza
3. Últimos documentos
4. Facturas vencidas
5. Acciones pendientes
6. Estado del sistema fiscal
```

### 22.5. Microcopy

```txt
Tu negocio al día.
Revisa tus ventas, comprobantes pendientes y pagos recibidos en un solo lugar.
```

---

## 23. Cotizaciones

### 23.1. Objetivo

Crear y convertir cotizaciones sin doble digitación.

### 23.2. Acciones

```txt
Crear cotización
Duplicar cotización
Enviar por WhatsApp
Convertir en factura
Marcar como aprobada
Marcar como rechazada
```

### 23.3. Estados

```txt
Borrador
Enviada
Aprobada
Rechazada
Vencida
Convertida en factura
```

### 23.4. Microcopy

```txt
Convierte esta cotización en factura.
Usaremos los datos del cliente y los productos aprobados para evitar doble digitación.
```

---

## 24. Facturas

### 24.1. Objetivo

Emitir comprobantes con seguridad fiscal.

### 24.2. Flujo ideal

```txt
Seleccionar cliente
Agregar productos
Revisar impuestos
Confirmar forma de pago
Vista previa
Emitir factura
Enviar a cliente
Registrar pago
```

### 24.3. Textos críticos

```txt
Antes de emitir, revisa los datos.
Una vez enviado a SUNAT, el comprobante no podrá editarse directamente.
```

```txt
No se pudo emitir la factura.
Revisa el RUC, la dirección fiscal y la conexión con el proveedor electrónico.
```

---

## 25. Guías

### 25.1. Objetivo

Generar guías de remisión sin olvidar datos obligatorios.

### 25.2. Campos mínimos

```txt
Motivo de traslado
Punto de partida
Punto de llegada
Transportista
Placa
Conductor
Productos trasladados
Fecha de traslado
```

### 25.3. Microcopy

```txt
Confirma dirección de salida, dirección de llegada, transportista y motivo de traslado.
```

---

## 26. Cobranza

### 26.1. Objetivo

Ayudar a cobrar sin perder seguimiento.

### 26.2. Estados

```txt
Pendiente
Pago parcial
Pagado
Vencido
En recordatorio
```

### 26.3. Acciones

```txt
Registrar pago
Enviar recordatorio
Ver comprobante
Marcar como incobrable
Descargar estado de cuenta
```

### 26.4. Microcopy

```txt
Pago pendiente de confirmación.
Registra el abono cuando el dinero figure en la cuenta bancaria de la empresa.
```

---

## 27. Modo oscuro

### 27.1. Estrategia técnica

Usar `class="dark"` en el elemento raíz.

Ejemplo:

```html
<html class="dark">
```

O en React:

```jsx
document.documentElement.classList.toggle('dark', isDarkMode);
```

### 27.2. Tailwind recomendado

En `tailwind.config.js`:

```js
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        inkora: {
          bg: 'var(--color-bg)',
          surface: 'var(--color-surface)',
          soft: 'var(--color-surface-soft)',
          text: 'var(--color-text)',
          muted: 'var(--color-text-muted)',
          border: 'var(--color-border)',
          primary: 'var(--color-primary)',
          success: 'var(--color-success)',
          warning: 'var(--color-warning)',
          danger: 'var(--color-danger)',
        }
      },
      borderRadius: {
        inkora: 'var(--radius-lg)'
      },
      boxShadow: {
        inkora: 'var(--shadow-card)'
      }
    }
  },
  plugins: [],
};
```

### 27.3. CSS global recomendado

Crear:

```txt
frontend/src/styles/tokens.css
```

Contenido base:

```css
:root {
  color-scheme: light;

  --color-bg: #f5f7fb;
  --color-surface: #ffffff;
  --color-surface-soft: #f8fafc;
  --color-surface-muted: #f1f5f9;
  --color-text: #0f172a;
  --color-text-muted: #64748b;
  --color-text-soft: #94a3b8;
  --color-border: #e2e8f0;
  --color-border-strong: #cbd5e1;

  --color-primary: #2563eb;
  --color-primary-hover: #1d4ed8;
  --color-primary-soft: #dbeafe;
  --color-primary-text: #ffffff;

  --color-success: #16a34a;
  --color-success-soft: #dcfce7;
  --color-success-text: #166534;

  --color-warning: #d97706;
  --color-warning-soft: #fef3c7;
  --color-warning-text: #92400e;

  --color-danger: #dc2626;
  --color-danger-soft: #fee2e2;
  --color-danger-text: #991b1b;

  --radius-sm: 10px;
  --radius-md: 14px;
  --radius-lg: 18px;
  --radius-xl: 24px;
  --radius-2xl: 32px;

  --shadow-soft: 0 8px 24px rgba(15, 23, 42, 0.06);
  --shadow-card: 0 18px 45px rgba(15, 23, 42, 0.08);
  --shadow-floating: 0 30px 80px rgba(15, 23, 42, 0.16);
}

.dark {
  color-scheme: dark;

  --color-bg: #020617;
  --color-surface: #0f172a;
  --color-surface-soft: #111827;
  --color-surface-muted: #1e293b;
  --color-text: #f8fafc;
  --color-text-muted: #cbd5e1;
  --color-text-soft: #94a3b8;
  --color-border: #1e293b;
  --color-border-strong: #334155;

  --color-primary: #60a5fa;
  --color-primary-hover: #3b82f6;
  --color-primary-soft: rgba(37, 99, 235, 0.20);
  --color-primary-text: #020617;

  --color-success: #22c55e;
  --color-success-soft: rgba(34, 197, 94, 0.16);
  --color-success-text: #bbf7d0;

  --color-warning: #f59e0b;
  --color-warning-soft: rgba(245, 158, 11, 0.16);
  --color-warning-text: #fde68a;

  --color-danger: #f87171;
  --color-danger-soft: rgba(248, 113, 113, 0.16);
  --color-danger-text: #fecaca;

  --shadow-soft: none;
  --shadow-card: none;
  --shadow-floating: 0 24px 70px rgba(0, 0, 0, 0.45);
}

body {
  margin: 0;
  min-height: 100vh;
  background: var(--color-bg);
  color: var(--color-text);
}
```

---

## 28. Refactor recomendado del proyecto

### 28.1. Nueva estructura

```txt
frontend/src/
  app/
    App.jsx
    routes.jsx

  components/
    ui/
      Button.jsx
      Input.jsx
      Select.jsx
      Textarea.jsx
      Badge.jsx
      Alert.jsx
      Card.jsx
      Modal.jsx
      Toast.jsx
      EmptyState.jsx
      Table.jsx
      ThemeToggle.jsx

    layout/
      AuthLayout.jsx
      DashboardLayout.jsx
      Sidebar.jsx
      Topbar.jsx

  features/
    auth/
      LoginPage.jsx
      RegisterPage.jsx

    dashboard/
      DashboardPage.jsx
      components/
        KpiCard.jsx
        RecentDocumentsTable.jsx
        PendingActions.jsx

    clientes/
      ClientesPage.jsx

    cotizaciones/
      CotizacionesPage.jsx
      CotizacionFormPage.jsx

    facturas/
      FacturasPage.jsx
      FacturaFormPage.jsx

    guias/
      GuiasPage.jsx

    cobranza/
      CobranzaPage.jsx

  styles/
    tokens.css
    globals.css

  utils/
    cn.js
    formatters.js
    apiUtils.js

  context/
    AuthContext.jsx
    ToastContext.jsx
    ThemeContext.jsx
```

---

### 28.2. Eliminar o reemplazar

Eliminar estilos de plantilla Vite en:

```txt
frontend/src/App.css
```

Reemplazar con:

```txt
frontend/src/styles/tokens.css
frontend/src/styles/globals.css
```

---

## 29. Componentes base recomendados

### 29.1. `Button.jsx`

```jsx
import { Loader2 } from 'lucide-react';
import { cn } from '../../utils/cn';

const variants = {
  primary: 'bg-[var(--color-primary)] text-[var(--color-primary-text)] hover:bg-[var(--color-primary-hover)] shadow-[var(--shadow-primary)]',
  secondary: 'bg-[var(--color-surface)] text-[var(--color-text)] border border-[var(--color-border)] hover:bg-[var(--color-surface-soft)]',
  soft: 'bg-[var(--color-primary-soft)] text-[var(--color-primary)] hover:opacity-90',
  ghost: 'bg-transparent text-[var(--color-text-muted)] hover:bg-[var(--color-surface-muted)]',
  danger: 'bg-[var(--color-danger)] text-white hover:opacity-90',
};

const sizes = {
  sm: 'h-34 px-3 text-xs rounded-xl',
  md: 'h-42 px-4 text-sm rounded-[13px]',
  lg: 'h-52 px-5 text-[15px] rounded-2xl',
};

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  className,
  disabled,
  ...props
}) {
  return (
    <button
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center justify-center gap-2 font-extrabold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed hover:-translate-y-px active:translate-y-0',
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}
```

---

### 29.2. `Badge.jsx`

```jsx
import { cn } from '../../utils/cn';

const variants = {
  draft: 'bg-[var(--color-surface-muted)] text-[var(--color-text-muted)]',
  sent: 'bg-[var(--color-primary-soft)] text-[var(--color-primary)]',
  accepted: 'bg-[var(--color-purple-soft)] text-[var(--color-purple-text)]',
  paid: 'bg-[var(--color-success-soft)] text-[var(--color-success-text)]',
  partial: 'bg-[var(--color-warning-soft)] text-[var(--color-warning-text)]',
  overdue: 'bg-[var(--color-danger-soft)] text-[var(--color-danger-text)]',
  cancelled: 'bg-[var(--color-danger-soft)] text-[var(--color-danger-text)]',
};

export default function Badge({ children, variant = 'draft', className }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-2 rounded-full px-2.5 py-1.5 text-xs font-black',
        'before:h-1.5 before:w-1.5 before:rounded-full before:bg-current',
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
```

---

### 29.3. `Card.jsx`

```jsx
import { cn } from '../../utils/cn';

export default function Card({ children, className }) {
  return (
    <section
      className={cn(
        'rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-soft)]',
        className
      )}
    >
      {children}
    </section>
  );
}
```

---

### 29.4. `EmptyState.jsx`

```jsx
import Button from './Button';

export default function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
}) {
  return (
    <div className="rounded-3xl border border-dashed border-[var(--color-border-strong)] bg-[var(--color-surface-soft)] px-6 py-10 text-center">
      <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-[var(--color-primary-soft)] text-[var(--color-primary)]">
        {icon}
      </div>

      <h3 className="mb-2 text-lg font-extrabold tracking-tight text-[var(--color-text)]">
        {title}
      </h3>

      <p className="mx-auto mb-5 max-w-md text-sm leading-6 text-[var(--color-text-muted)]">
        {description}
      </p>

      {actionLabel && (
        <Button onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
```

---

### 29.5. `ThemeToggle.jsx`

```jsx
import { Moon, Sun } from 'lucide-react';

export default function ThemeToggle({ theme, setTheme }) {
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
      aria-label={isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
    >
      {isDark ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}
```

---

## 30. Utilidad `cn`

Crear:

```txt
frontend/src/utils/cn.js
```

```js
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
```

---

## 31. Microcopy global

### 31.1. Botones

```txt
Crear cliente
Crear cotización
Emitir factura
Guardar borrador
Vista previa
Enviar por WhatsApp
Enviar por correo
Descargar PDF
Registrar pago
Anular comprobante
Duplicar
Editar
Ver detalle
```

### 31.2. Mensajes de éxito

```txt
Cliente creado correctamente.
Cambios guardados correctamente.
Cotización enviada por WhatsApp.
Factura guardada como borrador.
Comprobante aceptado por SUNAT.
Pago registrado correctamente.
PDF descargado.
```

### 31.3. Mensajes de error

```txt
No se pudo cargar la información.
No se pudo emitir la factura.
No encontramos este cliente.
El RUC debe tener 11 dígitos.
La fecha de vencimiento no puede ser anterior a la emisión.
Revisa tu conexión e inténtalo nuevamente.
```

### 31.4. Mensajes de prevención

```txt
Antes de emitir, revisa los datos del cliente.
Esta acción no se puede deshacer.
El comprobante no podrá editarse después de enviarlo a SUNAT.
Este cliente tiene facturas vencidas.
```

---

## 32. Accesibilidad

### 32.1. Reglas

- Todo botón debe tener texto claro o `aria-label`.
- Contraste mínimo:
  - Texto normal: 4.5:1
  - Texto grande: 3:1
- Inputs siempre con label visible.
- Errores debajo del campo.
- Estados no deben depender solo del color.
- Badges deben tener texto además de color.
- Modales deben poder cerrarse con Escape.
- Foco visible en botones, inputs y enlaces.

### 32.2. Focus ring

```css
:focus-visible {
  outline: 3px solid rgba(37, 99, 235, 0.35);
  outline-offset: 2px;
}
```

---

## 33. Responsive

### 33.1. Breakpoints

| Breakpoint | Uso |
|---|---|
| `< 640px` | móvil |
| `640px - 1024px` | tablet |
| `> 1024px` | desktop |

### 33.2. Reglas

- Sidebar oculta en móvil.
- Header móvil con botón de menú.
- Cards en una columna en móvil.
- Tablas con scroll horizontal en móvil.
- Botones principales pueden ocupar ancho completo en móvil.
- Formularios deben ser de una columna en móvil.

---

## 34. Animación y microinteracciones

### 34.1. Duración

```txt
150ms - 200ms: hover, focus, botones
250ms - 350ms: sidebar, modales
600ms - 900ms: gráficos o barras
```

### 34.2. Reglas

- No animar todo.
- Animar solo cambios que ayuden a entender.
- Respetar `prefers-reduced-motion`.

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation: none !important;
    transition: none !important;
    scroll-behavior: auto !important;
  }
}
```

---

## 35. Checklist de implementación

### Fase 1 — Limpieza

- [ ] Renombrar `FacturaPro` a `Inkora`.
- [ ] Eliminar estilos base de Vite en `App.css`.
- [ ] Crear `styles/tokens.css`.
- [ ] Crear `styles/globals.css`.
- [ ] Importar estilos globales en `main.jsx`.

### Fase 2 — Componentes base

- [ ] Crear `Button`.
- [ ] Crear `Input`.
- [ ] Crear `Card`.
- [ ] Crear `Badge`.
- [ ] Crear `Alert`.
- [ ] Crear `Modal`.
- [ ] Crear `EmptyState`.
- [ ] Crear `ThemeToggle`.

### Fase 3 — Layout

- [ ] Refactorizar `AuthLayout`.
- [ ] Refactorizar `DashboardLayout`.
- [ ] Refactorizar `Sidebar`.
- [ ] Crear `Topbar`.
- [ ] Implementar modo oscuro con `ThemeContext`.

### Fase 4 — Pantallas

- [ ] Refactorizar `LoginPage`.
- [ ] Refactorizar `DashboardPage`.
- [ ] Refactorizar `CotizacionesPage`.
- [ ] Refactorizar `ClientesPage`.
- [ ] Refactorizar `ProductosPage`.
- [ ] Crear `FacturasPage`.
- [ ] Crear `CobranzaPage`.
- [ ] Crear `GuiasPage`.

### Fase 5 — Microcopy y seguridad fiscal

- [ ] Reescribir mensajes de error.
- [ ] Reescribir empty states.
- [ ] Agregar modales de confirmación fiscal.
- [ ] Agregar estados de comprobante.
- [ ] Agregar alertas preventivas antes de emitir.

---

## 36. Prompt recomendado para Codex / Antigravity

```txt
Actúa como Senior Frontend Engineer y UX/UI Designer para un SaaS de facturación llamado Inkora.

Quiero que refactorices el frontend React + Vite + Tailwind siguiendo la especificación de diseño en `INKORA_DESIGN_SYSTEM.md`.

Objetivos:
1. Reemplazar la identidad visual antigua `FacturaPro` por `Inkora`.
2. Eliminar estilos base de Vite en `App.css`.
3. Crear tokens globales para modo claro y modo oscuro.
4. Implementar `darkMode: 'class'` en Tailwind.
5. Crear componentes UI reutilizables: Button, Input, Card, Badge, Alert, Modal, EmptyState, ThemeToggle.
6. Refactorizar AuthLayout, LoginPage, DashboardLayout, Sidebar y DashboardPage.
7. Mantener compatibilidad con React Router, AuthContext, ToastContext y apiUtils existentes.
8. Usar lenguaje claro orientado a facturación, cotizaciones, SUNAT, cobranza y clientes.
9. Priorizar accesibilidad, responsive design y consistencia visual.
10. No romper la lógica existente de autenticación ni llamadas API.

Entrega:
- Código ordenado por carpetas.
- Componentes reutilizables.
- Modo oscuro funcional.
- UI más moderna, intuitiva y profesional.
```

---

## 37. Resultado esperado

Al aplicar esta guía, Inkora debe sentirse como una plataforma moderna de facturación:

- Fácil de entender.
- Rápida para operar.
- Visualmente confiable.
- Preparada para modo oscuro.
- Con componentes reutilizables.
- Con textos claros y humanos.
- Con prevención de errores fiscales.
- Con dashboard útil para tomar decisiones.

La meta no es solo que “se vea bonito”, sino que el usuario pueda trabajar más rápido, equivocarse menos y confiar en el sistema.
