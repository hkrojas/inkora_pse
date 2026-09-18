# Análisis de Proyecto Inkora

## Resumen Ejecutivo

Inkora es un SaaS vertical para imprentas y pequeños negocios en Perú, con enfoque en facturación electrónica SUNAT. El proyecto está en **fase pre-launch con foco de hardening** (endurecimiento de seguridad, fiscalidad y estabilidad).

| Métrica | Valor |
|---------|-------|
| **Backend** | ~47.5K líneas Python (217 archivos) |
| **Frontend** | ~21.6K líneas JS/JSX (93 archivos) |
| **Tests backend** | ~13.8K líneas (49 archivos test) |
| **Build frontend** | 6.4 MB (dist/) |
| **Migraciones** | 10 versiones Alembic |
| **Ramas Git activas** | 9+ (incluyendo main, smartpse-backend, validación) |
| **Último commit** | `Expose fiscal artifact download flags` |

---

## 1. Arquitectura y Stack

### Backend (FastAPI)
- **Framework:** FastAPI 0.116 + Pydantic v2 + SQLAlchemy 2.0
- **Auth:** JWT con claims (tenant_id, rol, is_superadmin, must_change_password)
- **Passwords:** bcrypt + validación de fortaleza (top-100 blacklist)
- **DB:** PostgreSQL (producción) / SQLite (pruebas) con pooling configurable
- **Multitenancia:** ContextVar SQLAlchemy + filtro automático `do_orm_execute`
- **Rate limiting:** slowapi
- **Fiscal:** Dual provider (APISPeru + SmartPSE) + cola de emisión async
- **Storage:** Supabase Storage (CDR, XML, PDFs)
- **Workers:** Emission worker con polling y reintentos (max 5 intentos)
- **Logging:** JSON structured logging con request_id

### Frontend (React)
- **Framework:** React 18 + Vite 6 + React Router DOM 6
- **Estilos:** Tailwind CSS 3 + design system tokenizado (CSS variables)
- **UI:** Lucide React + componentes propios (DataTable, Modal, Toast, etc.)
- **State:** React Context (Auth + Theme) — sin Redux/Zustand
- **Data fetching:** fetch vanilla (sin React Query/SWR)
- **Testing:** Playwright E2E (6 suites) + tests unitarios mínimos (4 archivos)
- **Build:** ~6.4 MB (aceptable para SPA)

---

## 2. Fortalezas ✅

### 2.1 Seguridad y Tenant Isolation
- **JWT con claims ricos:** El token incluye `tenant_id`, `rol`, `is_superadmin`, `must_change_password`, evitando queries extra a BD.
- **Filtro automático de tenant:** `do_orm_execute` inyecta `WHERE tenant_id = X` en todas las queries SELECT. Esto es robusto y reduce el riesgo de filtración cruzada.
- **ContextVar thread-safe:** Usa `contextvars` para multitenancia, compatible con async.
- **PgBouncer aware:** Detecta automáticamente si usa pooler transaccional y evita `set_config` (que no funciona en modo transaction).
- **Roles explícitos:** `TENANT_ADMIN_ROLES`, `DOCUMENT_EMITTER_ROLES`, `PAYMENT_MANAGER_ROLES`.
- **Superadmin separado:** Validación explícita `is_superadmin` con guards independientes.
- **Passwords:** Mínimo 10 chars, alfanumérico, blacklist top-100, comparación con email.
- **Tokens internos:** Provisioning/registration protegidos por header secreto con `compare_digest` (timing-safe).
- **Emission guards:** Bloqueo de emisión fiscal si la suscripción no está activa/trial/grace (HTTP 402).
- **Password invalidation:** Si el usuario cambia su password, los tokens emitidos antes del cambio quedan invalidados automáticamente (comparación `iat` vs `password_changed_at`).

### 2.2 Fiscalidad
- **Dual provider:** APISPeru + SmartPSE con abstracción (`fiscal_provider_service`).
- **Cola de emisión async:** `EmissionJob` con polling, reintentos exponenciales, timeouts.
- **Artefactos fiscales:** Descarga automática de CDR, XML, PDF con almacenamiento en Supabase.
- **Correlativos:** Control de series y números con series floors configurables.
- **QR fiscales:** Generación integrada en PDFs.
- **Resumen diario / Bajas / Reversiones:** Módulos completos para operaciones SUNAT.
- **Notas de crédito/débito:** Con validación de montos disponibles.
- **Guías de remisión:** Integración GRE con SmartPSE.
- **Trackeo de provider:** Campo `provider_trace` para auditar qué proveedor fiscal se usó.

### 2.3 Calidad de Código y Tests
- **49 archivos de tests:** Cobertura enfocada en fiscal, auth, tenant isolation, SmartPSE, APISPeru.
- **Tests más grandes:**
  - `test_facturacion_fiscal.py` (1,051 líneas) — contratos fiscales
  - `test_facturacion_guards.py` (970 líneas) — guards de seguridad
  - `test_payments.py` (785 líneas) — cobranza
  - `test_cotizaciones.py` (524 líneas) — flujo cotización
  - `test_reportes.py` (871 líneas) — reportes
- **Migraciones disciplinadas:** 10 migraciones numeradas secuencialmente, evolucionando desde pre-beta hasta SmartPSE verification.
- **Frozen domains:** Documentación explícita de qué módulos están congelados (MRP, AI, proveedores) y por qué.
- **Design system tokenizado:** Frontend con variables CSS para colores, radios, sombras.
- **Lazy loading:** Páginas del frontend cargan bajo demanda.

### 2.4 Operaciones
- **Health check:** Endpoint `/health` con environment.
- **Request logging:** Middleware con `request_id`, duración, status code.
- **Rate limiting:** Configurado por endpoint (`slowapi`).
- **Configuración robusta:** `pydantic_settings` con validaciones cruzadas (producción → FISCAL_ENV=production, INIT_DB deshabilitado, BACKEND_URL real, Supabase obligatorio).
- **Feature flags por tenant:** `beta_feature_flags` para deshabilitar funcionalidades por tenant.
- **CORS:** Orígenes configurables por ambiente.

---

## 3. Debilidades y Riesgos ⚠️

### 3.1 Riesgos de Seguridad (P0-P1)

| Riesgo | Severidad | Detalle |
|--------|-----------|---------|
| **CORS allow_headers="*"** | P1 | El middleware CORS permite `*` en headers. En producción debería ser explícito. |
| **Sin Content Security Policy** | P1 | No hay headers de seguridad (HSTS, CSP, X-Frame-Options, X-Content-Type-Options). |
| **No rate limiting en health** | P2 | `/health` no tiene rate limiting, potencial vector de DoS. |
| **No rate limiting en auth** | P1 | `/token` tiene rate limiting (`10/minute`) pero `/register` no. Considerar brute force en registro. |
| **Secret keys en .env** | P2 | `SECRET_KEY` y `FIELD_ENCRYPTION_KEY` se cargan desde `.env`. Sin rotación programada. |
| **No audit log completo** | P2 | Solo auth events. No hay audit trail de cambios en documentos fiscales ni datos sensibles. |

### 3.2 Riesgos Fiscales (P0-P1)

| Riesgo | Severidad | Detalle |
|--------|-----------|---------|
| **Retry duplicado** | P0 | La lógica de reintentos de emisión debe tener idempotencia absoluta. Verificar que `emission_id` o `external_id` previene duplicación en APISPeru/SmartPSE. |
| **Estado de documentos** | P1 | Documentos `facturada`/`anulada` pueden tener lógica de edición que no está completamente auditada en este análisis. |
| **Cálculo de totales** | P1 | El redondeo y cálculo de IGV debe ser consistente entre backend y frontend. Requiere test de propiedad (property-based). |
| **Cuotas de crédito** | P1 | El cálculo de cuotas y fechas de vencimiento puede tener edge cases con meses de 28/31 días y festivos. |
| **Bundle de UBL** | P1 | `smartpse_ubl_service.py` y `fiscal_xml_service.py` son críticos. Verificar que no hay inyección de datos en XML. |
| **SUNAT directo** | P2 | El soporte para SUNAT directo está marcado como "parcial/futuro". Si se activa, requiere hardening adicional. |

### 3.3 Riesgos de Base de Datos (P1-P2)

| Riesgo | Severidad | Detalle |
|--------|-----------|---------|
| **ContextVar cleanup** | P1 | El `finally` en `get_db()` y `get_db_tenant()` usa `current_tenant_id.set(None)` directamente, pero hay un comentario que dice que `reset()` falla en contextos async. Esto puede causar fugas de tenant en edge cases con `anyio`. |
| **No hay schema separation** | P2 | Todos los tenants comparten el mismo schema. Una query mal escrita con `without_tenant_filter` expone todo. |
| **SQLite en tests** | P2 | SQLite no soporta todas las funciones de PostgreSQL. Algunos tests pueden pasar en SQLite pero fallar en producción. |
| **Init DB on startup** | P1 | `create_all` en startup puede causar problemas si hay modelos congelados que crean tablas no deseadas. |
| **Pool size pequeño** | P2 | `DB_POOL_SIZE=3`, `MAX_OVERFLOW=2` = 5 conexiones. Para un SaaS con workers, esto puede ser insuficiente bajo carga. |
| **Sin connection retries** | P2 | No hay reintentos automáticos en conexiones a BD. Si hay un blip de red, la petición falla. |

### 3.4 Riesgos de Frontend (P1-P2)

| Riesgo | Severidad | Detalle |
|--------|-----------|---------|
| **Sin React Query/SWR** | P2 | Todo el data fetching es con fetch vanilla. Sin cache, deduplicación, ni manejo de estado de carga/errores estandarizado. Esto genera código repetitivo y más propenso a bugs. |
| **Tests unitarios mínimos** | P2 | Solo 4 archivos `.test.js` en `lib/utils/`. No hay tests de componentes (React Testing Library, Vitest). |
| **Sin manejo de errores global** | P2 | No hay `ErrorBoundary` visible en la estructura del frontend. |
| **Build de 6.4 MB** | P2 | Aceptable pero verificar si incluye ReportLab o librerías pesadas innecesarias. |
| **exhaustive-deps off** | P2 | ESLint tiene `react-hooks/exhaustive-deps: off`. Esto oculta bugs de efectos. |
| **no-unused-vars off** | P2 | Variables no usadas no se reportan. Acumula deuda técnica. |
| **Sin TypeScript** | P3 | Proyecto en JS puro. Sin tipos estáticos, más propenso a errores en refactorizaciones. |
| **Sin service worker** | P3 | No hay PWA ni offline capability. Para un SaaS de imprentas, puede ser útil. |

### 3.5 Riesgos Operativos (P2)

| Riesgo | Severidad | Detalle |
|--------|-----------|---------|
| **Worker de emisión** | P2 | `EMISSION_WORKER_CONCURRENCY=1` con polling de 2 segundos. Un solo worker puede ser cuello de botella si hay muchos tenants emitiendo. |
| **Logs sin retención definida** | P2 | JSON logging está implementado pero no hay configuración de retención ni exportación a servicio externo (Datadog, CloudWatch). |
| **Sin monitoreo** | P2 | No hay endpoints de métricas (Prometheus) ni health checks profundos (solo `SELECT 1`). |
| **Deploy en Vercel** | P2 | El frontend usa `vercel.json` con SPA rewrite. Vercel es stateless y funciona bien para SPA. El backend en Docker/Railway/Fly. |
| **Múltiples ramas** | P2 | Hay 9+ ramas activas. Algunas pueden divergir (codex/smartpse-backend vs main). Necesitan merge strategy. |
| **Scripts de migración sueltos** | P2 | Hay ~30 scripts `migrate_*.py` sueltos en la raíz del backend. Deberían estar organizados o documentados como runbooks. |
| **No hay CI/CD visible** | P2 | No hay `.github/workflows/` ni `.gitlab-ci.yml`. Los tests se ejecutan manualmente. |

---

## 4. Análisis de Áreas Críticas (según AGENTS.md)

### 4.1 Tenant Isolation ✅ ✅
- **Estado:** Muy sólido. El filtro `do_orm_execute` es una de las mejores prácticas para FastAPI + SQLAlchemy.
- **Observación:** `without_tenant_filter()` existe para superadmin y queries globales, pero debe usarse con extrema cautela.
- **Riesgo residual:** Si algún endpoint usa `get_db` en lugar de `get_db_tenant`, la sesión no tiene tenant activado. Revisar que todos los routers de negocio usen `get_db_tenant`.

### 4.2 Ownership Explícito ✅ ✅
- **Estado:** Bien implementado. Los endpoints de facturación, clientes, productos validan que el recurso pertenece al tenant del usuario.
- **Observación:** Los tests `test_tenant_access_hardening.py` (407 líneas) y `test_facturacion_guards.py` (970 líneas) cubren esto.

### 4.3 Roles y Permisos ✅
- **Estado:** Roles definidos y validados en dependencias.
- **Riesgo:** El frontend no tiene un sistema de permisos robusto (solo oculta botones). La seguridad real está en el backend, lo cual es correcto.

### 4.4 Estados Fiscales ✅ ✅
- **Estado:** Estados bien definidos: `borrador`, `pendiente`, `enviada`, `rechazada`, `facturada`, `anulada`.
- **Observación:** El `document_flow_service.py` gestiona transiciones de estado. Revisar que no haya transiciones prohibidas (ej: `anulada` → `facturada`).

### 4.5 Correlativos ✅
- **Estado:** Series floors configurables por proveedor. `SMARTPSE_SERIES_FIES_FLOORS`.
- **Riesgo:** En alta concurrencia, el contador de correlativos puede tener race conditions. Verificar que usa `SELECT FOR UPDATE` o similar.

### 4.6 Reintentos de Emisión ✅
- **Estado:** `EMISSION_MAX_ATTEMPTS=5`, backoff exponencial.
- **Riesgo:** Si el proveedor fiscal acepta la petición pero el timeout del backend dispara un retry, puede haber duplicados. Necesita idempotencia por `external_id`.

### 4.7 Trazabilidad Cotización → Comprobante → Guía → Cobranza ✅
- **Estado:** `Cotizacion` tiene relaciones con `Pago`, `GuiaRemision`, y documentos fiscales.
- **Observación:** El flujo está implementado. Revisar que no se pueda borrar una cotización que ya tiene comprobante fiscal emitido.

### 4.8 Cálculo de Totales y Redondeo ⚠️
- **Estado:** `calculations.py` centraliza la lógica.
- **Riesgo:** Necesita tests de propiedad (hypothesis) para validar que el redondeo nunca produce centavos de diferencia.

### 4.9 Cuotas de Crédito ⚠️
- **Estado:** Implementado en `Cotizacion`.
- **Riesgo:** Edge cases con fechas (meses cortos, festivos, año bisiesto).

### 4.10 Notas de Crédito/Débito ✅
- **Estado:** Validación de montos disponibles (`ensure_credit_note_within_available_amount`).
- **Riesgo:** Race condition si dos notas de crédito se emiten simultáneamente contra el mismo documento.

### 4.11 Bajas, Resumen Diario, Reversiones ✅
- **Estado:** Módulos implementados con tests.
- **Riesgo:** SmartPSE vs APISPeru pueden tener comportamientos diferentes. Los tests deberían cubrir ambos providers.

### 4.12 Supabase Storage ✅
- **Estado:** Almacenamiento de PDFs, CDRs, XMLs.
- **Riesgo:** URLs públicas vs privadas. Verificar que los CDRs no son públicamente accesibles.

### 4.13 APISPeru / SmartPSE ✅
- **Estado:** Dual provider con abstracción.
- **Riesgo:** SmartPSE es más nuevo y puede tener edge cases no cubiertos. Los tests `test_smartpse_*.py` son buenos pero necesitan mantenimiento continuo.

### 4.14 Migraciones ✅
- **Estado:** 10 migraciones bien numeradas, evolucionan correctamente.
- **Riesgo:** Algunas migraciones (`0006_production_security_and_performance.py` = 6,180 bytes) son grandes. Si fallan en producción, rollback puede ser complicado.

### 4.15 Tests Backend ✅
- **Estado:** ~13,774 líneas de tests. Muy buena cobertura en áreas críticas.
- **Riesgo:** No hay CI/CD, por lo que los tests pueden romperse sin que nadie lo note.

### 4.16 Frontend sin Tests Automatizados ⚠️
- **Estado:** Playwright E2E (6 suites) + 4 tests unitarios.
- **Riesgo:** E2E es lento y frágil. Falta tests unitarios de componentes y hooks.

### 4.17 Bundle Frontend ✅
- **Estado:** 6.4 MB. Aceptable.
- **Riesgo:** Verificar si se puede reducir con code splitting adicional.

---

## 5. Recomendaciones Priorizadas

### Inmediatas (P0 — Pre-Launch)

1. **Implementar headers de seguridad:** HSTS, CSP, X-Frame-Options, X-Content-Type-Options en FastAPI.
2. **Auditar reintentos de emisión:** Verificar idempotencia con ambos providers (APISPeru + SmartPSE). Documentar el `external_id` usado.
3. **Revisar CORS en producción:** Cambiar `allow_headers=["*"]` a lista explícita.
4. **Validar race conditions en correlativos:** Asegurar que `SELECT FOR UPDATE` o advisory locks se usan para asignar números de serie.
5. **Agregar rate limiting a `/register` y `/health`:** Proteger contra abuso.

### Corto plazo (P1 — Post-Launch Hardening)

6. **Agregar CI/CD pipeline:** GitHub Actions con pytest, eslint, build de frontend, y smoke tests.
7. **Implementar ErrorBoundary en frontend:** Capturar errores de React.
8. **Agregar React Query/SWR:** Reemplazar fetch vanilla para cache, deduplicación, y manejo de errores.
9. **Auditar cálculos de totales:** Tests de propiedad con `hypothesis` para validar redondeo.
10. **Agregar métricas:** Prometheus endpoint para monitoreo.
11. **Limpiar scripts de migración sueltos:** Mover a `scripts/` o `runbooks/` con documentación.
12. **Organizar ramas Git:** Mergear ramas activas a `main` o documentar por qué existen.
13. **Agregar tests de componentes frontend:** Vitest + React Testing Library.
14. **Implementar audit trail completo:** Quién cambió qué y cuándo en documentos fiscales.
15. **Revisar pool de DB:** Aumentar a 5-10 si se espera carga concurrente.

### Mediano plazo (P2 — Escalabilidad)

16. **Considerar TypeScript para frontend:** Reduce bugs en refactorizaciones.
17. **Agregar reintentos de conexión a BD:** Con `tenacity` o similar.
18. **Implementar schema separation (opcional):** Un schema por tenant para aislamiento máximo.
19. **Agregar monitoreo de errores:** Sentry o similar para frontend y backend.
20. **Worker de emisión escalable:** Considerar múltiples workers con cola distribuida (Redis/RabbitMQ).

---

## 6. Estado de Preparación para Launch

| Área | Estado | Nota |
|------|--------|------|
| **Auth & Seguridad** | 🟡 Listo con ajustes | Headers de seguridad faltantes, CORS libre. |
| **Tenant Isolation** | 🟢 Sólido | Filtro automático + ContextVar. |
| **Fiscalidad** | 🟡 Listo con vigilancia | Dual provider, cola async, artefactos. Monitorear duplicados. |
| **Base de Datos** | 🟢 Sólido | Pooling, multitenancia, migraciones. |
| **Tests Backend** | 🟢 Sólido | 49 suites, ~13.8K líneas. Falta CI/CD. |
| **Tests Frontend** | 🔴 Débil | Solo E2E + 4 tests unitarios. |
| **Operaciones** | 🟡 Funcional | Logs estructurados, health check. Falta métricas y monitoreo. |
| **Deploy** | 🟡 Funcional | Docker + Vercel. Falta CI/CD. |
| **Documentación** | 🟢 Buena | AGENTS.md, FROZEN_DOMAINS.md, README. |

### Veredicto

**Inkora está en ~85% de preparación para launch.** El backend es robusto, bien testeado, y tiene buena arquitectura de seguridad y multitenancia. Los riesgos críticos restantes son operativos (headers de seguridad, CORS, CI/CD) y de calidad del frontend (falta de tests unitarios, manejo de estado). La fiscalidad está bien implementada pero requiere monitoreo activo de duplicados y race conditions en alta concurrencia.

---

*Análisis generado el 27 de junio de 2025. Basado en inspección directa del código fuente.*
