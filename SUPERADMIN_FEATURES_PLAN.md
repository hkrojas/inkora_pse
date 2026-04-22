# SUPERADMIN FEATURES PLAN

Plan de mejoras para el panel de superadmin. Hoy el panel cubre tenants, suscripciones SaaS, pagos SaaS y notas de piloto, pero le falta visibilidad por usuario, límites accionables y guardrails de cobranza.

---

## Estado actual (qué ya existe)

- `/superadmin/tenants` — listar/crear/editar/borrar tenants
- `/superadmin/tenants/{id}/users` — crear usuario por tenant (no listar por tenant)
- `/superadmin/usuarios` — listar todos los usuarios (sin filtros, sin métricas)
- `/superadmin/tenants/{id}/subscription` — activar / suspender / extender / pricing
- `/superadmin/tenants/{id}/payments` — registrar y listar pagos SaaS
- `/superadmin/beta/resumen` — resumen consolidado de tenants piloto
- `/superadmin/tenants/{id}/actividad` — métricas de uso del tenant
- `/superadmin/audit-logs` — bitácora global

**Brechas claras:**
1. No hay visión por **usuario** dentro del tenant: ni email visible en panel, ni cuántos documentos emite cada uno.
2. No existe un mecanismo para **limitar** la emisión por usuario.
3. La suspensión por impago es manual: no hay bloqueo automático cuando vence el ciclo SaaS.
4. No hay soporte de "ver como usuario" (impersonación) para diagnosticar problemas reportados.
5. Sin notificaciones cuando un tenant se acerca al límite o entra en mora.

---

## Fase 1 — Visibilidad por usuario (la base que falta)

### 1.1 Endpoint: `GET /superadmin/tenants/{tenant_id}/users-detail`

Devuelve la lista de usuarios del tenant **con métricas de emisión por usuario**:

```json
[
  {
    "id": 12,
    "email": "ventas@grafica.pe",
    "nombre_completo": "María Torres",
    "rol": "operador",
    "is_active": true,
    "last_login_at": "2026-04-19T14:33:21Z",
    "created_at": "2026-02-01T10:00:00Z",
    "metrics": {
      "cotizaciones_total": 142,
      "cotizaciones_mes_actual": 23,
      "facturas_total": 58,
      "facturas_mes_actual": 11,
      "boletas_total": 87,
      "boletas_mes_actual": 14,
      "notas_credito_total": 3,
      "notas_debito_total": 0,
      "guias_total": 41,
      "guias_mes_actual": 9,
      "ultimo_documento_at": "2026-04-19T13:10:00Z"
    },
    "limits": {
      "facturas_mes": 50,
      "boletas_mes": 100,
      "guias_mes": null
    }
  }
]
```

**Cambios de modelo:**
- Agregar `User.last_login_at: DateTime | null` (actualizado en `routers/auth.py` al loguear).
- Agregar `User.is_active: Boolean default true` (independiente de `Tenant.is_active`).

**Cambios de CRUD:**
- Nuevo `crud/superadmin.py::get_tenant_users_with_metrics(db, tenant_id)` que hace 5–6 queries `COUNT()` agrupadas por `usuario_id` y `document_kind` sobre `cotizaciones` + `guias_remision`.

### 1.2 Frontend — Sub-pestaña "Usuarios" en el detalle de tenant

En `SuperadminPage.jsx`, dentro del modal/drawer de detalle de tenant, agregar una pestaña **Usuarios** con tabla:

| Email | Nombre | Rol | Último login | Cot. | Fact. | Bol. | Guías | Límites | Acciones |
|---|---|---|---|---|---|---|---|---|---|
| ventas@grafica.pe | María Torres | operador | hace 2 h | 142 | 58 | 87 | 41 | F:50 / B:100 | Editar · Bloquear · Reset |

Columnas con tooltip "(mes actual / total)". Acciones por usuario:
- **Editar** — cambia rol, nombre, email
- **Bloquear / Activar** — toggle `is_active` (sin borrar)
- **Resetear contraseña** — genera password temporal de 12 chars, la muestra una vez
- **Ver actividad** — timeline de los últimos 50 documentos del usuario

---

## Fase 2 — Límites por usuario y por tenant

### 2.1 Modelo de límites

Nueva tabla `usage_limits`:

```python
class UsageLimit(Base):
    __tablename__ = "usage_limits"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # null => límite a nivel tenant
    document_kind = Column(String, nullable=False)  # 'fiscal_invoice' | 'fiscal_boleta' | 'guia' | 'nota_credito' | 'nota_debito'
    period = Column(String, default="month")  # 'month' | 'day' | 'total'
    max_count = Column(Integer, nullable=False)
    notify_at_pct = Column(Integer, default=80)  # alertar al alcanzar X% del límite
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
```

> **Regla explícita:** `document_kind = 'quotation'` **NO** acepta límites. La capa de validación lo rechaza con 400. Las cotizaciones siempre son ilimitadas porque son la entrada del funnel — limitar cotizaciones limita el negocio del cliente.

### 2.2 Endpoints

- `GET /superadmin/tenants/{tenant_id}/limits` — lista límites del tenant (a nivel tenant + a nivel cada usuario)
- `PUT /superadmin/tenants/{tenant_id}/limits` — bulk upsert de límites
- `DELETE /superadmin/limits/{limit_id}` — quitar un límite
- `GET /superadmin/tenants/{tenant_id}/limits/usage` — devuelve `{ limit_id, used, max, pct, would_block }` por cada límite

### 2.3 Enforcement (el guardrail real)

En `services/facturacion_service.py` y en el flujo de creación de guías, antes de emitir:

```python
def check_emission_quota(db, user, document_kind):
    if document_kind == "quotation":
        return  # nunca limitada
    limits = get_active_limits(db, user.tenant_id, user.id, document_kind)
    for limit in limits:
        used = count_documents_in_period(db, limit)
        if used >= limit.max_count:
            raise QuotaExceededError(limit, used)
```

`QuotaExceededError` se mapea a HTTP 402 Payment Required con payload `{ "code": "QUOTA_EXCEEDED", "limit_kind": "...", "max": N, "used": N, "contact": "..." }`.

### 2.4 Frontend del límite

En la pestaña Usuarios (Fase 1.2) y en la pestaña Tenant del superadmin:

- Botón "Configurar límites" abre modal con grid:
  - Filas: Factura · Boleta · Guía · Nota Crédito · Nota Débito
  - Columnas: Mensual · Diario · Total
  - Inputs numéricos vacíos = sin límite
  - Toggle "Notificarme al 80% del límite"
- Al guardar, validar que ningún campo `quotation` esté presente (defensa en profundidad).

En el tenant (sidebar): badge `45/50 facturas este mes` cuando >70%, color rojo si >95%.

---

## Fase 3 — Bloqueo automático por impago

### 3.1 Concepto

Hoy `Subscription.billing_due_at` y `grace_until` existen pero no bloquean nada — la suspensión es manual con `/suspend`. Convertir en regla automática.

### 3.2 Estado fiscal vs estado SaaS

Distinguir dos niveles de bloqueo:

| Estado SaaS | Acceso al sistema | Emisión fiscal | Cotizaciones |
|---|---|---|---|
| `active` | OK | OK | OK |
| `grace` (1–7 días post `billing_due_at`) | OK con banner | OK con banner | OK |
| `payment_required` (>7 días post vencimiento) | OK | **BLOQUEADO** | OK |
| `suspended` | **BLOQUEADO** | BLOQUEADO | BLOQUEADO |

> Razonamiento: cortar la emisión fiscal es la presión correcta para el cobro (ahí está su flujo de caja). Cortar cotizaciones rompe la operación interna del cliente y daña la relación. Cortar el login pierde adopción y dificulta la recuperación.

### 3.3 Implementación

**Cron / job diario** (`services/subscription_service.py::run_billing_check`):
- Marcar `payment_required` cuando `billing_due_at + 7d < now`.
- Marcar `suspended` cuando `billing_due_at + 30d < now`.
- Reactivar a `active` cuando llega un `SubscriptionPayment` que cubra el monto pendiente.

**Middleware/dependency** `require_emission_allowed`:
- Aplicado a `/cotizaciones/{id}/emit-fiscal-document`, `/notas/*`, `/guias/*` (pero NO a `POST /cotizaciones`).
- Si `subscription.status in ("payment_required", "suspended")` → HTTP 402 con detalle.

### 3.4 UI cliente final (banner)

En el frontend del **tenant** (no superadmin), mostrar banner según estado:

- `grace` (amarillo): "Tu pago vence el {fecha}. Regulariza para seguir emitiendo."
- `payment_required` (rojo): "Emisión bloqueada por pago pendiente. Contacta soporte."
- `suspended` (rojo full-screen): pantalla de bloqueo con instrucciones de pago.

### 3.5 UI superadmin

En la lista de tenants, columna "Estado SaaS" con chips de color. Filtros rápidos: `Todos / Activos / En gracia / Mora / Suspendidos`. Acción "Forzar reactivación" si registra pago manual.

---

## Fase 4 — Otras funciones que el panel necesita

### 4.1 Impersonación segura ("Ver como tenant")

Endpoint `POST /superadmin/tenants/{tenant_id}/impersonate` → devuelve un JWT corto (15 min) con `tenant_id` del cliente y un claim `impersonated_by: superadmin_user_id`.

- En el frontend, banner persistente rojo: "Operando como TENANT X — Salir".
- Toda acción durante impersonación se audita con `entity_type='impersonation'` en `audit_logs`.
- Restricciones: no puede cambiar contraseñas, no puede borrar datos, no puede emitir documentos fiscales reales.

Justifica casos de soporte tipo "no veo mi cotización" sin pedir credenciales al cliente.

### 4.2 Alertas y notificaciones

Tabla `superadmin_alerts`:
- Tipo: `quota_warning`, `payment_overdue`, `apisperu_token_expiring`, `emission_failure_spike`
- Estado: `pending` / `seen` / `dismissed`
- Tenant relacionado

Generadas por jobs:
- 80% de cualquier límite → alerta
- 3 días antes de `billing_due_at` → alerta
- 5+ emisiones fallidas en 1 hora en un tenant → alerta

UI: campana en topbar del superadmin con conteo de pendientes.

### 4.3 Health check de credenciales ApisPeru por tenant

Job semanal que llama `validate_apisperu_token` por cada tenant con token guardado. Resultado se guarda en `Tenant.apisperu_token_status` + `apisperu_token_checked_at`. Si falla, alerta automática.

Razón: hoy se descubre cuando el cliente intenta emitir y falla.

### 4.4 Logs de errores de emisión por tenant

Endpoint `GET /superadmin/tenants/{tenant_id}/emission-errors?limit=50` — devuelve los últimos errores de `DocumentEmissionJob` con `status='failed'`, agrupados por código de error.

Útil para diagnosticar problemas recurrentes (ej. tenant siempre falla por dirección mal formateada).

### 4.5 Métricas de engagement

En `/superadmin/tenants-detail`, agregar:
- `dau_last_7d` — usuarios distintos que loguearon en los últimos 7 días
- `documents_last_30d` — total de documentos emitidos
- `inactive_users` — usuarios que no loguean hace >30 días

Permite identificar tenants que están dejando de usar antes de que cancelen.

### 4.6 Acciones masivas

En la lista de tenants, checkbox por fila + barra de acciones masivas:
- "Suspender N tenants seleccionados"
- "Enviar mensaje a N tenants" (email + WhatsApp link)
- "Exportar a CSV"

Solo para suscripciones, no para datos operativos del tenant.

### 4.7 Modo mantenimiento global

Toggle `system_settings.maintenance_mode = true` que devuelve 503 con mensaje configurable a todos los endpoints excepto `/auth/me` y `/health`. El superadmin sigue operativo.

Para deploys que requieren bajar la app (migraciones grandes, cambio de credenciales SUNAT).

### 4.8 Exportar datos del tenant (compliance)

Endpoint `POST /superadmin/tenants/{tenant_id}/export` — genera ZIP con CSVs de clientes, productos, cotizaciones, facturas, guías, pagos. Útil para:
- Onboarding (importar a la competencia se vuelve doloroso)
- Cancelación (entregar al cliente sus datos como deber legal)
- Migraciones internas

### 4.9 Cupones / descuentos

Tabla `discount_codes` con `code`, `pct_off`, `valid_until`, `applied_to_tenant_id`. Permite aplicar descuento al `current_price` de la suscripción sin perder el `founder_price` original.

### 4.10 Vista de costo por tenant (interno)

Métrica acumulada por tenant:
- Llamadas a ApisPeru (boletas + facturas + guías + consultas DNI/RUC)
- Storage en Supabase (PDFs almacenados, MB)
- Costo estimado mensual (configurable: $0.X por emisión)

Permite ver márgenes reales por cliente. No se muestra al cliente, solo al superadmin.

---

## Priorización sugerida

| # | Fase | Esfuerzo | Valor | Cuándo |
|---|---|---|---|---|
| 1 | Fase 1 — Visibilidad por usuario | M | Alto | Inmediato (lo pidió el usuario) |
| 2 | Fase 3 — Bloqueo por impago | M | Alto | Antes de tener >10 clientes pagando |
| 3 | Fase 2 — Límites por usuario | M | Medio | Cuando aparezca el primer abuso |
| 4 | Fase 4.1 — Impersonación | S | Alto | Segundo ciclo de soporte |
| 5 | Fase 4.2 — Alertas | S | Medio | Junto con Fase 3 |
| 6 | Fase 4.3 — Health ApisPeru | S | Alto | Inmediato (barato y previene fuegos) |
| 7 | Fase 4.4 — Errores de emisión | S | Medio | Junto con 4.3 |
| 8 | Fase 4.5 — Engagement | S | Medio | Cuando el portafolio crezca |
| 9 | Fase 4.6 — Acciones masivas | S | Bajo | Cuando >30 tenants |
| 10 | Fase 4.7 — Mantenimiento | XS | Medio | Antes del primer deploy con downtime |
| 11 | Fase 4.8 — Export compliance | S | Medio | Antes del primer churn formal |
| 12 | Fase 4.9 — Cupones | M | Bajo | Cuando se haga campaña de adquisición |
| 13 | Fase 4.10 — Costo por tenant | S | Medio | Al cerrar primer trimestre con clientes |

---

## Notas de diseño

- **Cotizaciones nunca se limitan ni se bloquean.** Es la entrada del funnel del cliente — bloquearlas rompe su operación y daña la relación. La presión de cobro va sobre la emisión fiscal (factura/boleta/guía), que es donde está su valor cobrable.
- **Reset de contraseña genera password temporal visible una sola vez.** No permitir al superadmin "ver" passwords (no existen en plano), solo regenerar.
- **Toda acción del superadmin sobre un tenant queda en `audit_logs`** con `entity_type='tenant'` o `entity_type='user'` y `details` JSON con el cambio.
- **Los límites son soft por defecto:** primer mes solo notifican, segundo mes bloquean. Configurable por límite.
- **Cuando se bloquea emisión por impago, la respuesta HTTP debe incluir el contacto y monto** para que el cliente pueda regularizar sin escribir soporte.
