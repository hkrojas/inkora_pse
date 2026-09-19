# Capas locales y orden de commits — 18/09/2026

## Propósito

Este documento fija el punto de separación entre el contenido que ya está en producción y los endurecimientos locales posteriores. Su objetivo es impedir que un `git add .`, una copia de carpeta o un despliegue desde un árbol divergente vuelva a mezclar versiones.

No autoriza publicar, fusionar ni modificar producción.

## Autoridades de comparación

- Worktree aislado: `C:/Users/HP/Desktop/inkora_production_baseline_20260918`.
- Rama local: `codex/production-baseline-20260918`.
- HEAD de partida: `a7b514c91bd98c4114953529471c4045ef85e520`.
- Paquete productivo histórico: `C:/Users/HP/Desktop/inkora_smartpse/tmp/actions-consistency-20260918`.
- Huella raw del paquete productivo: `1755dc0ee9a6e22395b991f51e185b0c2437826c42ff94326643abab01a74a73`.

## Capa 0 — baseline productivo preparado

Estado: **confirmado localmente en `792e3585f6566b2902090c404c98918e28687361`**.

- 94 modificaciones.
- 34 altas.
- 10 eliminaciones.
- 138 cambios con detección de renombres desactivada.
- 12 076 inserciones y 4 914 eliminaciones frente al `main` remoto de partida.
- Identificador del diff staged: `b3b1a7aedeed491388bdddaa104592d1a946a1ba`.
- Cero rutas staged fuera del manifiesto productivo.
- Las diez eliminaciones esperadas están presentes.
- Ninguna prueba, contrato o documento de soporte fue incorporado al índice.

Los 366 archivos del índice fueron comparados previamente con el paquete: 256 eran idénticos byte por byte y 110 diferían solo por saltos de línea. No se detectaron diferencias sustantivas. La huella canónica versionada resuelve esa variación para entregas futuras sin cambiar el paquete histórico.

## Capa 1 — resiliencia del worker

Estado: **confirmado localmente en `ce7c914500a8a5a32698b22dc6136fdbb20ab22c`**.

Archivos exclusivos:

- `backend/services/emission_queue_service.py`
- `backend/test_emission_worker_resilience.py`

Identificador del diff: `329318f74897408deaad8eff8f9467f553966a51`.

Alcance: recuperación frente a `SQLAlchemyError`, rollback protegido, espera y reintento sin terminar el proceso. Pruebas focalizadas del worker/cola: 26 aprobadas.

## Capa 2 — Storage y readiness

Estado: **confirmado localmente en `cc4c136a3dc245e9004d4774a989f4b55d928945`**.

Archivos exclusivos:

- `backend/config.py`
- `backend/supabase_client.py`
- `backend/services/storage_service.py`
- `backend/routers/ops.py`
- `backend/test_storage_service.py`

Identificador del diff: `cf1603546449367963420bd708cd82089cddcf10`.

Alcance: service-role obligatoria fuera de local y readiness de solo lectura para ambos buckets, con errores sanitizados. Regresión focalizada: 70 aprobadas.

## Capa 3 — guard de entrega

Estado: **confirmado localmente en `f4d95fbbe06da944bec6fa107987157a8b60f997`**.

| Archivo | SHA256 actual |
|---|---|
| `scripts/release_guard.py` | `c12b7732e4c44448ec5816599ec12d21f0f349191764ac62925667759bfbcf97` |
| `backend/test_release_guard.py` | `f753380d9511018caaac54222ba437e89e73806fda5a4358f1281484e568689c` |
| `docs/RELEASE_CANONICO.md` | `9ad24199a1ec18fe7d689a202b89453997bc7f613f2734b89d127509c521d08e` |

Alcance: manifiestos `canonical-text-v1`, compatibilidad `raw-v1` y preservación byte-exacta de binarios. Pruebas focalizadas: 9 aprobadas.

## Regresión acumulada

La ejecución conjunta de worker, cola, Storage, PDF, artefactos, uploads, recuperación documental y guard terminó con **105 pruebas aprobadas**.

No se ejecutaron migraciones, proveedores fiscales, Supabase remoto ni pruebas de escritura productiva.

## Capa 4 — soporte y referencias recuperadas

Estado: **incluido en el commit final de soporte de esta rama**.

Incluye pruebas y contratos de recuperación, configuración de desarrollo sin secretos, documentación operativa, herramientas locales, referencias de análisis y la eliminación de artefactos generados. La documentación histórica ausente fue restaurada antes de preparar esta capa; no se registrarán esas eliminaciones accidentales.

## Cambios de soporte todavía no consolidados

El soporte se prepara mediante una lista positiva y comprobación de secretos. Queda expresamente prohibido usar `git add .`, `git add -A` o preparar directorios completos en futuras recuperaciones.

Las 172 salidas `frontend/.svelte-kit/` permanecen eliminadas y su ignore forma parte de esta capa. También se mantienen ocho eliminaciones confirmadas de herramientas o pruebas sustituidas. Los demás documentos históricos fueron preservados desde el índice.

## Orden obligatorio de commits

1. **Baseline productivo 2026-09-18:** `792e3585f6566b2902090c404c98918e28687361`.
2. **Resiliencia del worker:** `ce7c914500a8a5a32698b22dc6136fdbb20ab22c`.
3. **Seguridad y readiness de Storage:** `cc4c136a3dc245e9004d4774a989f4b55d928945`.
4. **Guard canónico de entrega:** `f4d95fbbe06da944bec6fa107987157a8b60f997`.
5. **Soporte restante:** pruebas, contratos, scripts, `.gitignore` y documentos previamente clasificados; nunca junto al runtime.

Cada commit debe repetir sus pruebas focalizadas y comprobar que el siguiente conjunto no entró accidentalmente en staging.

## Estado final de las capas

Las cinco capas quedan confirmadas localmente y separadas. La validación final de soporte comprende 673 pruebas backend, 47 pruebas frontend, lint, build y guard canónico. No hubo push, merge o despliegue.

## Capa 5 preparada — CI y rollback verificable

Estado: **validada y preparada sin commit**.

Archivos exclusivos:

- `.github/workflows/release-gate.yml`
- `scripts/release_guard.py`
- `scripts/project_worker_release.py`
- `backend/test_release_guard.py`
- `docs/RELEASE_CANONICO.md`
- `docs/CAPAS_LOCALES_Y_ORDEN_DE_COMMITS_2026-09-18.md`

Alcance: puerta CI reproducible, regresión backend/frontend, proyección del worker con el mismo modo de hash y verificación de paquetes históricos `raw-v1` sin imponerles marcadores funcionales posteriores. La capa no cambia archivos de runtime empaquetados ni producción.

Validación: 676 pruebas backend, 47 pruebas frontend, lint, build, 13 pruebas focalizadas del guard, paquete canónico nuevo y verificación del paquete productivo histórico. Las pruebas PostgreSQL continúan como puerta separada con bases desechables.
