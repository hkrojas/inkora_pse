# Plan de Concurrencia — Facturación Simultánea

## Diagnóstico

Cuando varios usuarios del mismo tenant facturan al mismo tiempo, existen race conditions reales que pueden causar errores 500, documentos duplicados, o estados inconsistentes.

---

## Hallazgos Detallados

### 1. Correlativo Duplicado (CRÍTICO)

**Archivos:** `crud/_base.py:70-76`, `crud/cotizaciones.py:209`, `crud/cotizaciones.py:379-385`, `crud/guias.py:63-69`

**Qué pasa:** `_next_correlativo_for_series()` usa `SELECT ... FOR UPDATE` sobre la fila con el mayor correlativo. Pero cuando dos transacciones compiten por la misma serie (ej. `F001`):

```
TX-A: Lock row con correlativo=5 → calcula 6
TX-B: Espera el lock...
TX-A: INSERT correlativo=6, COMMIT → libera lock
TX-B: Adquiere lock en row 5 (¡no ve la row 6 nueva!) → calcula 6
TX-B: INSERT correlativo=6 → IntegrityError (UNIQUE constraint)
```

Bajo `READ COMMITTED` (default de PostgreSQL), `FOR UPDATE` re-evalúa la fila bloqueada pero **no re-ejecuta la query completa** para encontrar el nuevo máximo.

**Impacto:** El segundo usuario recibe un error 500 no manejado. La `UniqueConstraint` en `(tenant_id, serie, correlativo)` previene corrupción de datos, pero la experiencia es mala.

**Aplica a:** Facturas (`F001`/`B001`), Notas de crédito/débito (`FF01`/`BB01`), Guías, y cotizaciones (`COT`).

### 2. Facturación Duplicada de la Misma Cotización (PROTEGIDO ✓)

**Archivos:** `crud/cotizaciones.py:192-206`

`create_fiscal_document_from_quote` ya hace `SELECT ... FOR UPDATE` en la cotización origen (línea 192-195) y DESPUÉS verifica si ya existe un fiscal document (línea 202-206). Dos requests sobre la **misma** cotización se serializan correctamente. **No requiere cambios.**

### 3. Anulación Concurrente (ALTO)

**Archivos:** `crud/cotizaciones.py:335-363`

**Qué pasa:** `anular_cotizacion()` lee el documento y su cotización origen SIN lock. Dos escenarios problemáticos:

- **Anular + Facturar simultáneo:** Usuario A anula el fiscal_document existente (poniendo la cotización en `pendiente`). Simultáneamente, Usuario B emite un nuevo fiscal_document. Si B comitea primero, A sobrescribe el estado de la cotización a `pendiente` cuando ya tiene un nuevo fiscal vigente.

- **Doble anulación:** Dos requests anulan el mismo documento. Ambos pasan el check, ambos actualizan la cotización origen. No hay consecuencia grave pero es procesamiento innecesario.

### 4. Cuota de Documentos — TOCTOU (ALTO)

**Archivos:** `routers/facturacion.py:139`, `crud/cotizaciones.py:304-311`

**Qué pasa:** `check_document_limit()` se verifica en el router (línea 139), pero `documents_used` se incrementa mucho después — solo cuando SUNAT responde OK (línea 309-311). Dos requests concurrentes ambos pasan el check con `documents_used=99/100`, ambos emiten, y el contador termina en 101.

### 5. Notas de Crédito/Débito sobre el Mismo Comprobante (MEDIO)

**Archivos:** `routers/facturacion.py:251`, `crud/cotizaciones.py:366-420`

El check de estado en `routers/facturacion.py:251` no bloquea el documento afectado con `FOR UPDATE`. Dos requests pueden emitir dos notas de crédito contra la misma factura. Además de la race de correlativo (hallazgo #1), se permite duplicar notas que deberían ser únicas.

---

## Plan de Solución

### Fase A — Retry con Backoff en Correlativo (Prioridad 1)

**Objetivo:** Convertir el `IntegrityError` silencioso en un retry transparente.

**Cambio en:** `crud/_base.py` y cada función que usa `_next_correlativo_for_series`

```python
# crud/_base.py — NUEVO
MAX_CORRELATIVO_RETRIES = 3

def _next_correlativo_for_series(db: Session, tenant_id: int, serie: str) -> int:
    """Obtiene siguiente correlativo. Debe llamarse dentro de una transacción
    que haga INSERT + COMMIT antes de liberar el lock."""
    last_doc = db.query(models.Cotizacion).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.serie == serie,
    ).order_by(models.Cotizacion.correlativo.desc()).with_for_update().first()
    ultimo_correlativo = last_doc.correlativo if last_doc else 0
    return ultimo_correlativo + 1
```

**Wrapping function en cada punto de creación** (`create_fiscal_document_from_quote`, `crear_nota_credito_debito`, `create_cotizacion`, `crear_guia`):

```python
from sqlalchemy.exc import IntegrityError
import time

def create_fiscal_document_from_quote(db, quote, usuario_id, tipo_comprobante):
    for attempt in range(MAX_CORRELATIVO_RETRIES):
        try:
            return _create_fiscal_document_from_quote_inner(
                db, quote, usuario_id, tipo_comprobante,
            )
        except IntegrityError as e:
            db.rollback()
            if "uq_cotizaciones_tenant_serie_correlativo" not in str(e):
                raise
            if attempt == MAX_CORRELATIVO_RETRIES - 1:
                raise ValueError(
                    "No se pudo asignar un número correlativo. "
                    "Intente nuevamente."
                ) from e
            time.sleep(0.05 * (attempt + 1))  # 50ms, 100ms, 150ms
    # unreachable
```

**Por qué retry y no advisory lock:** El retry es más simple, no requiere cambios de infraestructura, y el caso de colisión es infrecuente (requiere dos facturas en la misma serie dentro de ~100ms). La `UniqueConstraint` ya garantiza la integridad; solo falta manejar el error elegantemente.

### Fase B — Lock en Anulación (Prioridad 2)

**Cambio en:** `crud/cotizaciones.py` → `anular_cotizacion()`

```python
def anular_cotizacion(db, cotizacion_id, tenant_id=None):
    query = db.query(models.Cotizacion).filter(
        models.Cotizacion.id == cotizacion_id
    )
    if tenant_id is not None:
        query = query.filter(models.Cotizacion.tenant_id == tenant_id)
    
    # FOR UPDATE para serializar con facturación y otras anulaciones
    db_cot = query.with_for_update().first()
    if not db_cot:
        return None
    
    # Validar que no esté ya anulada
    if db_cot.estado == DOCUMENT_STATUS_VOIDED:
        return db_cot  # Idempotente
    
    # ... resto igual, pero también lock en source_quote si existe
    if db_cot.source_quote_id:
        source_quote = db.query(models.Cotizacion).filter(
            models.Cotizacion.id == db_cot.source_quote_id,
            models.Cotizacion.tenant_id == db_cot.tenant_id,
        ).with_for_update().first()
        # ... evaluar si revertir a pendiente
```

**Esto serializa:** anulación vs. anulación, y anulación vs. nueva facturación (porque `create_fiscal_document_from_quote` ya hace `FOR UPDATE` en la cotización origen).

### Fase C — Cuota Atómica (Prioridad 2)

**Cambio en:** `crud/cotizaciones.py` → `guardar_respuesta_sunat()`

Reemplazar el read-increment-write con un UPDATE atómico:

```python
from sqlalchemy import update

if data_sunat.get("success") and not was_issued and db_cot.document_kind == DOCUMENT_KIND_FISCAL_DOCUMENT:
    db.execute(
        update(models.Subscription)
        .where(models.Subscription.tenant_id == db_cot.tenant_id)
        .values(documents_used=models.Subscription.documents_used + 1)
    )
```

Y mover el `check_document_limit` al momento de **crear** el fiscal document (dentro de la misma transacción), no en el router:

```python
# En create_fiscal_document_from_quote, después del FOR UPDATE en la cotización:
sub = get_subscription_by_tenant(db, quote.tenant_id)
if sub and sub.documents_limit and (sub.documents_used or 0) >= sub.documents_limit:
    raise ValueError("Límite de documentos alcanzado para este período.")
```

Al estar dentro de la transacción que tiene el lock en la cotización, se serializa naturalmente.

### Fase D — Protección en Notas (Prioridad 3)

**Cambio en:** `crud/cotizaciones.py` → `crear_nota_credito_debito()`

Agregar `FOR UPDATE` al documento afectado antes de crear la nota:

```python
def crear_nota_credito_debito(db, doc_afectado, usuario_id, tipo_nota, cod_motivo, descripcion_motivo):
    # Re-lock el documento afectado para serializar notas concurrentes
    doc_afectado = db.query(models.Cotizacion).filter(
        models.Cotizacion.id == doc_afectado.id,
        models.Cotizacion.tenant_id == doc_afectado.tenant_id,
    ).with_for_update().first()
    
    if doc_afectado.estado != DOCUMENT_STATUS_ISSUED:
        raise ValueError("El documento debe estar facturado para emitir una nota.")
    
    # ... resto con el retry de correlativo de Fase A
```

### Fase E — Constraint Adicional (Opcional, Prioridad 4)

Agregar constraint en BD para prevenir duplicados lógicos a nivel de modelo:

```sql
-- Máximo un fiscal_document activo por cotización
CREATE UNIQUE INDEX uq_one_active_fiscal_per_quote
ON cotizaciones (tenant_id, source_quote_id)
WHERE document_kind = 'fiscal_document' AND estado != 'anulada';
```

Esto es un **partial unique index** de PostgreSQL. Es una red de seguridad — si todo lo anterior funciona, nunca se dispara. Pero previene corrupción si algún edge case escapa la lógica.

**Nota:** No se puede crear vía `metadata.create_all`. Requiere ejecución SQL manual o un script de migración.

---

## Resumen de Cambios por Archivo

| Archivo | Cambio | Fase |
|---------|--------|------|
| `crud/_base.py` | Documentar contrato de `_next_correlativo_for_series` | A |
| `crud/cotizaciones.py` → `create_cotizacion` | Wrap con retry en IntegrityError | A |
| `crud/cotizaciones.py` → `create_fiscal_document_from_quote` | Wrap con retry + mover check_document_limit dentro | A, C |
| `crud/cotizaciones.py` → `crear_nota_credito_debito` | FOR UPDATE en doc_afectado + retry | A, D |
| `crud/cotizaciones.py` → `anular_cotizacion` | FOR UPDATE en documento + cotización origen | B |
| `crud/cotizaciones.py` → `guardar_respuesta_sunat` | UPDATE atómico en documents_used | C |
| `crud/guias.py` → `crear_guia` | Wrap con retry en IntegrityError | A |
| `routers/facturacion.py` | Eliminar `check_document_limit` del router (movido a crud) | C |
| Migración SQL | Partial unique index | E |

---

## Estado de Implementación

### Contexto SUNAT: Series por Empresa

Las imprentas pueden tener una o más series de facturación (`F001`, `F002`, `B001`, etc.) asignadas por SUNAT. La colisión de correlativo **solo ocurre dentro de la misma serie del mismo tenant**. Si una imprenta usa `F001` y `F002`, dos trabajadores facturando en series distintas nunca colisionan. Sin embargo, la mayoría de MYPEs trabaja con una sola serie — el riesgo es real.

### Fases A-D: IMPLEMENTADAS ✅

| Fase | Estado | Ubicación | Verificado |
|------|--------|-----------|------------|
| A — Retry correlativo (fiscal) | ✅ | `_base.py:36-66`, `cotizaciones.py:196-211` | wrapper `_retry_on_correlativo_conflict` con 3 retries + backoff 50/100/150ms |
| A — Retry correlativo (notas) | ✅ | `cotizaciones.py:428-445` | mismo wrapper |
| A — Retry correlativo (guías) | ✅ | `guias.py:40-43` | mismo wrapper |
| B — Lock en anulación | ✅ | `cotizaciones.py:395` + `409` | `with_for_update()` en documento + source_quote |
| B — Idempotencia anulación | ✅ | `cotizaciones.py:400-401` | retorna si ya está anulada |
| C — Cuota atómica | ✅ | `cotizaciones.py:350-358` | `UPDATE ... SET documents_used = documents_used + 1` |
| C — Check dentro de TX | ✅ | `cotizaciones.py:240-247` | verifica cuota post-FOR UPDATE |
| C — Removido del router | ✅ | `routers/facturacion.py` | `check_document_limit` eliminado |
| D — Lock en notas | ✅ | `cotizaciones.py:458-461` | FOR UPDATE en doc_afectado |
| D — Validación estado post-lock | ✅ | `cotizaciones.py:463-467` | verifica `facturada` después del lock |

### Pendiente

| Item | Estado | Riesgo | Detalle |
|------|--------|--------|---------|
| A — Retry correlativo (cotizaciones serie `COT`) | ⚠️ FALTA | Bajo | `create_cotizacion` (`cotizaciones.py:138-178`) usa `with_for_update` + commit directo sin el wrapper `_retry_on_correlativo_conflict`. Mismo patrón vulnerable, pero menor criticidad que facturación. |
| E — Partial unique index en PostgreSQL | 🔲 Opcional | Bajo | Red de seguridad a nivel BD. No urgente — las Fases A-D ya cubren todos los escenarios. |

---

## Qué NO Cambiar

- **Isolation level global:** Subir a `SERIALIZABLE` causaría retries masivos en queries no relacionadas. Locks puntuales son suficientes.
- **Advisory locks de PostgreSQL:** Agregan complejidad innecesaria cuando el retry con unique constraint es igual de efectivo.
- **Emission queue job claiming:** Ya usa `FOR UPDATE SKIP LOCKED`. El recovery por timeout es aceptable.
- **`create_fiscal_document_from_quote` lock en cotización:** Ya está correcto. No duplicar lógica.

---

## Orden de Implementación Recomendado

1. **Fase A** — Retry de correlativo (~1h). Elimina el error 500 más probable.
2. **Fase B** — Lock en anulación (~30min). Previene estados inconsistentes.
3. **Fase C** — Cuota atómica (~30min). Cierra el bypass de límite.
4. **Fase D** — Lock en notas (~20min). Igual patrón que B.
5. **Fase E** — Constraint parcial (migración manual en staging/prod).

## Testing

Cada fase debe incluir un test que simule concurrencia. Ejemplo para Fase A:

```python
import threading

def test_concurrent_fiscal_creation(db_session):
    """Dos usuarios facturan cotizaciones distintas al mismo tiempo.
    Ambos deben obtener correlativos distintos sin error."""
    tenant = make_tenant(db_session, "CONC")
    user1 = make_user(db_session, tenant, email="u1@test.com")
    user2 = make_user(db_session, tenant, email="u2@test.com")
    quote1 = make_quote_via_crud(db_session, tenant, user1)
    quote2 = make_quote_via_crud(db_session, tenant, user2)
    
    results = [None, None]
    errors = [None, None]
    
    def facturar(idx, quote, user):
        try:
            results[idx] = crud.create_fiscal_document_from_quote(
                db_session, quote, user.id, "01"
            )
        except Exception as e:
            errors[idx] = e
    
    t1 = threading.Thread(target=facturar, args=(0, quote1, user1))
    t2 = threading.Thread(target=facturar, args=(1, quote2, user2))
    t1.start(); t2.start()
    t1.join(); t2.join()
    
    assert errors[0] is None and errors[1] is None
    assert results[0].correlativo != results[1].correlativo
```

**Nota:** Los tests con SQLite no reproducen `FOR UPDATE` fielmente. Para validar las fixes de concurrencia, ejecutar tests contra PostgreSQL (staging) o usar `pytest-postgresql`.
