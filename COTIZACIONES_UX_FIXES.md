# Plan de mejoras UX — Cotizaciones v2

> Sigue al `COTIZACIONES_REFACTOR_PLAN.md` ya ejecutado. Aquí sólo se listan los problemas de **diseño, usabilidad y jerarquía visual** detectados tras revisar la pantalla en funcionamiento y los feedbacks del usuario.

---

## 1. Problemas reportados por el usuario

| # | Área | Problema observado |3. Elaboras un plan md

|---|------|--------------------|
| 1 | Selector de cliente | El combobox muestra sólo la razón social. No hay señal de si el cliente ya existe, cuántas operaciones tiene o si es recién creado. El botón "Nuevo Cliente" pasa desapercibido (texto pequeño arriba a la derecha del label). |
| 2 | Selector de producto | Hay que hacer scroll en una lista plana, no se ve el `codigo_interno`, no hay búsqueda tipada, el placeholder "Desde catálogo..." no comunica su función. |
| 3 | Fondo y jerarquía | Demasiado blanco. Secciones (cliente, detalle, observaciones) se diluyen con el fondo de la app. En pantallas con brillo alto se pierde todo el contraste. |
| 4 | Tab bar | Texto muy pequeño (11px), padding ajustado, la barra se "esconde" contra el header de la app. |
| 5 | Acciones del Historial | Sólo hay 2 iconos (Emitir · Ver). El usuario pide iconos **separados** para Ver, Duplicar, Descargar PDF, Enviar WhatsApp, Enviar correo, Enviar WhatsApp+correo, Eliminar. |

## 2. Problemas adicionales detectados durante la revisión

| # | Área | Problema |
|---|------|---------|
| 6 | Footer del formulario | "Limpiar formulario" y "Guardar cotización" tienen el mismo peso visual (ambos son `btn-secondary`/`btn-primary` al mismo nivel). El botón destructivo-leve queda demasiado cerca del CTA principal. |
| 7 | Panel de totales | Flota suelto debajo de la tabla, sin borde ni contenedor. No es claro que es un bloque resumen: parece parte de la última fila. |
| 8 | Observaciones | Textarea de 2 filas ocupa todo el ancho con mucho padding; rara vez se usa, pero visualmente compite con el detalle. |
| 9 | Tabla de detalle — columna "Producto" y "Descripción" | Duplicación confusa: si eliges un producto, se copia a "Descripción" y la columna "Producto" queda vacía (value=""). Después de elegir ya no hay forma visible de saber qué producto estaba asociado a esa línea. |
| 10 | Historial — estado del comprobante vinculado | Cuando la cotización está facturada se muestra el número (F001-...) pero no el estado (ACEPTADO / RECHAZADO / PENDIENTE SUNAT). El `getSunatStatus` ya existe, pero sólo se usa en el tab Emitidas. |
| 11 | Historial — sin duplicar | No existe acción para duplicar una cotización anterior (caso frecuente: cliente pide la misma proforma con variación de precio). |
| 12 | Historial — sin enlace público | El modelo tiene `uuid_publico` (para `compartir`) pero no se expone como copiar-link ni como QR. |
| 13 | Modal Nuevo Cliente | Se abre sobre el formulario pero al crear el cliente el `clienteId` no se auto-selecciona (el usuario tiene que volver al combobox y buscarlo). |
| 14 | Avanzado (unidad / afectación) | El toggle está "oculto" en la esquina superior derecha en tipografía mono 10px. Usuarios de boleta doméstica suelen no activarlo nunca; usuarios de exonerado / servicio no lo encuentran. |
| 15 | Empty state Historial | El botón del empty state dice "+ Nueva cotización" pero no explica qué se va a crear ni cómo seguir. |
| 16 | Tab Emitidas — fila seleccionada | Al seleccionar una fila aparece la toolbar (Nota Crédito / Débito / Anular) pero no hay indicación visual clara de selección (fondo tenue en la fila). |
| 17 | Fecha vencimiento | Aparece y desaparece según condición de pago causando saltos del layout. Debería quedar fija (deshabilitada en "contado"). |
| 18 | Columna "Cant." | `<input type="number">` con step="any" muestra flechitas de incremento del navegador que rompen la estética mono/spreadsheet. |

---

## 3. Propuesta UX

### 3.1 Selector de cliente — combobox enriquecido

**Cambios:**
- Reemplazar `CustomSelect` plano por un **`ClientCombobox`** dedicado.
- Cada opción muestra: `razón_social` (bold) + `documento` (mono, tenue) + badge si es cliente nuevo (< 7 días) o frecuente (≥ 3 cotizaciones).
- Búsqueda interna por nombre o documento (match case-insensitive).
- Cuando el texto del input no coincide con ningún cliente existente, al final de la lista aparece una opción **"+ Crear cliente: <texto>"** que dispara el modal de Nuevo Cliente con el nombre pre-rellenado.
- Al crear el cliente desde el modal, **auto-seleccionarlo** en el combobox.
- Debajo del combobox, cuando hay cliente seleccionado, mostrar un pequeño chip-preview: `RUC 20XXXXXXXX · Av. La Marina 1234 · 📞 999-999-999`. Si faltan datos, enlazar "completar ficha".

### 3.2 Selector de producto — con código y búsqueda

**Cambios:**
- En la columna "Producto / Servicio" de la tabla, usar el mismo patrón combobox tipeable.
- Cada opción de la lista muestra **2 columnas**: `codigo_interno` (mono, 11px, color tenue) | `nombre`. Si el producto no tiene código, se muestra `—`.
- Búsqueda por código o nombre.
- Al seleccionar, la celda "Producto" muestra `CODIGO · Nombre` (truncado) en lugar de quedar vacía, para que siga siendo visible la fuente del ítem.
- Añadir una opción final **"+ Usar descripción libre"** que deja el campo vacío y pone el foco en "Descripción" (el caso actual de servicios ad-hoc).

### 3.3 Jerarquía visual y fondos

**Cambios globales:**
- Fondo del contenedor de la página: `#F5F7FA` (ya existe como `--surface-muted`?) en vez de `#fff`. La tarjeta interna queda en blanco, con sombra suave. Genera separación inmediata entre "lienzo" y "hoja de trabajo".
- Cada sección del formulario con **backgrounds diferenciados**:
  - Sección cliente/moneda/condición → `#FFFFFF` (fondo claro, es la entrada de datos)
  - Sección líneas de detalle → `#F8FAFC` (ya está, mantener)
  - Sección observaciones → **colapsable** por defecto, aparece como una fila `+ Añadir observaciones` (estilo link); se expande al click. Elimina 100px de espacio en blanco desaprovechado.
  - Panel de totales → **caja flotante** con borde `1px solid #CBD5E1`, fondo `#FFFFFF`, sombra suave. Mover a columna derecha **debajo** de la tabla (no dentro del bloque gris), para que se lea como "resumen del bloque detalle".
- Separadores horizontales más visibles: reemplazar `border-bottom: 1px solid #E2E8F0` entre secciones por una banda de 1px con `linear-gradient` del color de acento tenue, para que el ojo identifique el corte.

### 3.4 Tab bar más prominente

**Cambios:**
- Tipografía: `13px` (antes 11px), `font-weight: 700`, **sin uppercase** o con letterspacing reducido.
- Padding `14px 24px` (antes `8px 20px`).
- Borde inferior activo **3px solid** (antes 2px) y color más saturado.
- Añadir **icono** al lado del label: `Plus` para crear, `History` para historial, `Receipt` para emitidas. Ya están importados los iconos necesarios.
- Separador vertical (`1px` gris) entre tabs para clarificar "grupos" de acciones.
- Contador (ej. "Historial (12)") como badge gris pill al lado, no en el mismo texto.

### 3.5 Historial — acciones separadas

Reemplazar la botonera actual (`Emitir` + `Ver`) por un grid de iconos con tooltip individual:

| Icono | Acción | Condición |
|-------|--------|-----------|
| `Eye` | Ver detalle | siempre |
| `Copy` | Duplicar cotización | siempre |
| `Download` | Descargar PDF | `sunat_xml_url` o cotización guardada |
| `Share2` | Copiar enlace público | siempre (usa `uuid_publico`) |
| `MessageCircle` (o `Phone`) | Enviar por WhatsApp | cliente tiene `whatsapp` o `telefono` |
| `Mail` | Enviar por correo | cliente tiene `email` |
| `Send` | WhatsApp + correo (combo) | cliente tiene ambos |
| `Receipt` | Emitir factura/boleta | `!hasLinked` |
| `Trash2` | Eliminar cotización | `!hasLinked` y `estado != 'anulada'` |

**Implementación visual:**
- Agrupar en 2 clusters separados por un divisor vertical: *consultar / compartir* (izquierda) y *procesar / destructivo* (derecha).
- Tamaño de icono 14px dentro de un botón de 28x28 (suficiente touch target, no inflado).
- Colores por intención: `Eye` neutro, `Download/Share/Message/Mail` accent azul, `Receipt` primary indigo, `Trash` danger sólo al hover.
- Si son demasiados iconos para móvil: en viewport < 768px, colapsar en un menú `⋯` que despliega la lista completa.

**Backend necesario:**
- Duplicar → endpoint `POST /cotizaciones/{id}/duplicar` (crea copia con nuevo `internal_order_number`, mismos items, mismo cliente). *Si no existe aún, implementarlo en el backend.*
- Eliminar → endpoint `DELETE /cotizaciones/{id}` restringido a estado `pendiente` y sin `linked_fiscal_document`. *Si no existe, implementarlo.*
- WhatsApp/Correo: reutilizar `getWhatsAppLink` (ya existe) y añadir `getEmailLink` equivalente (`mailto:` con asunto y cuerpo). El envío "real" queda fuera de alcance de este plan (lanzar cliente externo de correo/WhatsApp es suficiente para v2).
- Enlace público: reutilizar `svc.share(id)` que ya existe en `services/cotizaciones.js` línea 8 para copiar al clipboard.

### 3.6 Formulario — mejoras puntuales

- Footer: mover "Limpiar formulario" a un link discreto (`text-slate-500 hover:text-red-500`) a la izquierda. El CTA "Guardar cotización" queda solo a la derecha, con más peso.
- Observaciones: colapsable como se explicó en 3.3.
- Avanzado (unidad / afectación): promover a **toggle switch** con label claro, al nivel del encabezado de la tabla, no escondido a la derecha. Persistir preferencia en `localStorage`.
- Fecha vencimiento: siempre visible, `disabled` cuando condición = contado (evita salto de layout).
- Inputs numéricos: añadir `appearance: none` + `-moz-appearance: textfield` + reglas para ocultar spinners nativos, coherente con el resto de la estética mono.

### 3.7 Tab Emitidas — mejoras puntuales

- Fila seleccionada: background `#EEF2FF` + borde izquierdo 3px `#4F46E5` (consistente con estado activo de otros paneles de la app).
- Toolbar contextual: cuando no hay selección, mostrar mensaje placeholder `"Selecciona un comprobante para emitir nota o anular"` en lugar de iconos deshabilitados silenciosos.

---

## 4. Tareas concretas (orden de implementación)

1. **Base visual** (tab bar + fondos + separadores) — cambios globales en `CotizacionesPage.jsx` y clases utilitarias de `app.css` si hiciera falta. Test visual: comparar con screenshot de referencia.
2. **Footer formulario + observaciones colapsables + fecha vencimiento siempre visible + avanzado toggle** — contenidos en `NuevaCotizacionForm`.
3. **`ClientCombobox`** (componente nuevo en `src/components/ui/`) — usa `CustomSelect` como base pero acepta `renderOption`/`renderPreview` y `onCreateNew`. Integrar en `NuevaCotizacionForm`. Añadir auto-selección tras `handleNuevoCliente`.
4. **`ProductCombobox`** (componente nuevo) — mismo patrón, columna de código. Integrar en la tabla de detalle. Guardar el `codigo_interno` o `id` del producto seleccionado en el state del item (nuevo campo `item.producto_id` opcional) para poder mostrar `CODIGO · Nombre` truncado.
5. **Historial — acciones separadas** — refactor del bloque de iconos en la columna "Acciones". Añadir helpers `getEmailLink`, `copyShareLink`, y las llamadas a `svc.duplicar`/`svc.remove` (añadir a `services/cotizaciones.js` cuando los endpoints backend estén).
6. **Backend: duplicar y eliminar cotización** — routers/crud nuevos, con tests en `test_cotizaciones.py` (crear, duplicar, verificar que la copia tiene nuevo `internal_order_number` y los mismos items; eliminar sólo si `estado == pendiente` y `linked_fiscal_document` es null).
7. **Historial — badge SUNAT** — mostrar `getSunatStatus(item)` también cuando `hasLinked`, como pequeña pill al lado del número del comprobante.
8. **Tab Emitidas — selección visible + placeholder de toolbar**.
9. **QA manual**: flujo completo crear cliente desde combobox → cotización → duplicar → emitir → compartir → ver historial con badge SUNAT.
10. **Build + smoke test**: `npm run build`, `npm run dev`, recorrer rutas `/cotizaciones` y `/cotizaciones/:id` sin errores en consola.

---

## 5. Fuera de alcance (posterior)

- Envío real de correo (requiere SMTP backend).
- Plantillas de mensajes de WhatsApp personalizables por tenant.
- Vista móvil optimizada (responsive profundo).
- Import masivo de cotizaciones desde CSV.
- Reemplazo del componente `CustomSelect` por una librería (Combobox de Headless UI / Radix).

---

## 6. Criterios de "listo"

- ✅ Al abrir `/cotizaciones/nueva`, un usuario nuevo identifica en < 5s cómo añadir un cliente que no existe.
- ✅ Al buscar un producto por código (ej. "P-001") aparece de inmediato en la lista.
- ✅ La tab bar es legible desde 1m de distancia en pantalla 14" con brillo medio.
- ✅ En Historial, cada acción tiene su propio icono y tooltip; no hay acciones "combinadas".
- ✅ Duplicar una cotización toma 1 click y lleva al formulario con todos los campos pre-rellenados.
- ✅ El panel de totales se percibe como bloque resumen, no como extensión de la tabla.
- ✅ `npm run build` sin warnings nuevos.
