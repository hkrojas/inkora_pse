# Frozen Domains — PrintFlow Backend

Este documento describe el estado de los dominios congelados en `routers/legacy_frozen.py`.
Un dominio "congelado" existe en el código y tiene modelos/datos, pero **no forma parte del launch
scope comercial actual** y no debe expandirse sin instrucción explícita del product owner.

---

## Reglas generales

- Todos los endpoints congelados tienen `deprecated=True` en OpenAPI.
- El tag OpenAPI es `frozen-non-launch` para distinguirlos de los endpoints de launch.
- No agregar nuevos endpoints a `legacy_frozen.py` sin instrucción explícita.
- Si un dominio se decide activar como feature de launch o premium, moverlo a su propio
  router dedicado (ej: `routers/mrp.py`, `routers/ai.py`).

---

## Dominios congelados

### 1. Proveedores / Talleres externos
**Modelos:** `Proveedor`
**Endpoints:** `GET/POST /proveedores/`, `PUT/DELETE /proveedores/{id}`

Estado actual: catálogo simple de talleres tercerizados. Los datos existen en producción para
tenants que los cargaron antes del re-enfoque del producto.

Riesgo de acoplamiento: bajo. Es un CRUD independiente sin FK hacia el flujo de launch.

Para activar: crear `routers/proveedores.py`, mover los 4 endpoints, remover `deprecated=True`.

---

### 2. Insumos / Materia prima
**Modelos:** `Insumo`
**Endpoints:** `GET/POST /insumos/`, `PUT/DELETE /insumos/{id}`

Estado actual: inventario de insumos/materia prima. Ligado al módulo MRP (BOM + órdenes).
No tiene valor standalone sin el resto del módulo MRP.

Riesgo de acoplamiento: medio. `Insumo` es referenciado por `RecetaBOM` y `AlertaInventario`.

Para activar: activar junto con BOM y órdenes de producción como módulo MRP completo.

---

### 3. BOM / Recetas (Lista de Materiales)
**Modelos:** `RecetaBOM`
**Endpoints:** `GET/POST /productos/{producto_id}/bom`

Estado actual: lista de materiales por producto (MRP ligero). Los endpoints usan el prefijo
`/productos/` del launch scope — acoplamiento de namespace conocido.

Riesgo de acoplamiento: medio-alto.
- Los endpoints viven bajo `/productos/{id}/` (launch scope namespace).
- `crud.get_recetas_producto` ahora requiere `tenant_id` y hace JOIN con `Producto`
  para evitar lectura cruzada entre tenants (corregido en Fase 10).

Para activar: crear `routers/mrp.py` con prefijo `/mrp/`, mover los endpoints a
`/mrp/productos/{id}/bom` para desacoplar el namespace.

---

### 4. Órdenes de Producción
**Modelos:** `OrdenProduccion`
**Endpoints:**
  - `GET /ordenes-produccion`
  - `PATCH /ordenes-produccion/{id}/status`
  - `POST /cotizaciones/{cotizacion_id}/orden-produccion`

Estado actual: motor MRP ligero. Genera una orden de trabajo calculando requerimientos de
material según la BOM del producto. El endpoint de generación está bajo `/cotizaciones/`
(acoplamiento de namespace conocido y documentado).

Riesgo de acoplamiento: alto.
- El endpoint `POST /cotizaciones/{id}/orden-produccion` usa el prefijo `/cotizaciones/`
  del launch scope. Si el módulo MRP se activa, este endpoint debe moverse a `/mrp/`.
- La tarea de fondo `_check_stock_background` crea su propia sesión DB — dependencia
  interna al módulo MRP.

Para activar: crear `routers/mrp.py`, mover los 3 endpoints, resolver el acoplamiento
de namespace `/cotizaciones/`.

---

### 5. Alertas de Inventario
**Modelos:** `AlertaInventario`
**Endpoints:** `GET /alertas/inventario`

Estado actual: alertas de quiebre de stock generadas automáticamente por el motor MRP
(vía `crud.verificar_stock_y_generar_alertas` en background). No tiene valor standalone
sin el módulo MRP activo.

Riesgo de acoplamiento: bajo (solo lectura, sin side-effects).

Para activar: activar junto con el módulo MRP completo.

---

### 6. AI — Parsing con Gemini
**Modelos:** ninguno (stateless)
**Endpoints:**
  - `POST /ai/cotizar-texto`
  - `POST /ai/leer-factura-proveedor`

Estado actual: integración con Gemini para extraer ítems cotizables de texto libre y
datos de facturas de proveedor (PDF/imagen). Requiere `GEMINI_API_KEY` configurado.
No genera datos persistentes.

Riesgo de acoplamiento: muy bajo. Es completamente stateless y no depende de otros
dominios congelados.

Para activar: crear `routers/ai.py`, mover los 2 endpoints, remover `deprecated=True`.
Considerar: rate limiting, quota management, y pricing del feature premium.

---

## Dominio promovido al launch scope (Fase 10)

### Dashboard
**Endpoint:** `GET /analytics/dashboard`
**Router:** `routers/dashboard.py`

Movido de `legacy_frozen.py` a su propio router en la Fase 10 porque el dashboard es
un feature explícito del launch product, no un dominio congelado. Utiliza únicamente
modelos del launch scope (`Cotizacion`, `Pago`, `Producto`) más un campo de órdenes
de producción que devuelve 0.00 si el módulo MRP no está activo.

---

## Resumen de riesgos por dominio

| Dominio            | Acoplamiento | Activar junto con     | Esfuerzo estimado |
|--------------------|-------------|----------------------|-------------------|
| Proveedores        | Bajo         | Solo                  | 1-2h              |
| Insumos            | Medio        | BOM + Órdenes (MRP)  | con MRP           |
| BOM / Recetas      | Medio-alto   | MRP completo          | con MRP           |
| Órdenes producción | Alto         | MRP completo          | con MRP           |
| Alertas inventario | Bajo         | MRP completo          | con MRP           |
| AI (Gemini)        | Muy bajo     | Solo (feature premium)| 2-4h              |
