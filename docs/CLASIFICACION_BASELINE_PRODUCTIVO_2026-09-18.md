# Clasificación del baseline productivo — 18/09/2026

## Resultado

**VERDE para preparar el runtime; AMARILLO para consolidar el soporte.**

El worktree `C:/Users/HP/Desktop/inkora_production_baseline_20260918` reproduce el runtime de producción, pero no debe prepararse con `git add .`. Sus 456 cambios frente a `main` se dividen en dos capas independientes:

| Capa | Modificados | Nuevos | Eliminados | Total |
|---|---:|---:|---:|---:|
| Runtime productivo | 94 | 34 | 10 | **138** |
| Pruebas, contratos, documentos y auxiliares | 35 | 55 | 228 | **318** |

No existe ningún archivo en staging y no se creó commit.

## Capa 1 — Runtime productivo

La lista positiva de runtime es el manifiesto de `tmp/actions-consistency-20260918/release-manifest.json`: 366 archivos con SHA256 individual. De esos archivos, 128 cambian frente a `main`; los otros 238 ya son idénticos.

Para reproducir producción también deben permanecer ausentes estos diez archivos que sí existen en `main`:

1. `backend/alembic/versions/0007_smartpse_company_management.py`
2. `backend/alembic/versions/0008_client_snapshots.py`
3. `backend/alembic/versions/0009_quote_payment_methods.py`
4. `backend/alembic/versions/0010_quote_wallet_selection.py`
5. `backend/alembic/versions/0011_extended_unit_price_precision.py`
6. `backend/alembic/versions/0012_fiscal_provider_evidence.py`
7. `backend/alembic/versions/0013_inventory_enabled_by_default.py`
8. `backend/alembic/versions/0013_quote_quantity_precision.py`
9. `backend/alembic/versions/0014_access_requests.py`
10. `backend/services/fiscal_clock.py`

Las nueve migraciones pertenecen a la línea divergente de `main`. Reintroducirlas junto a la cadena productiva sin diseñar una conciliación podría crear revisiones paralelas o contradicciones. Con el conjunto productivo actual, Alembic informa una única cabeza: `0022_gre_sales_documents`.

`fiscal_clock.py` fue omitido deliberadamente en la recuperación porque implicaba cambiar la semántica de fechas fiscales. No debe entrar silenciosamente en el baseline; puede auditarse en un bloque fiscal posterior.

**Decisión recomendada:** conservar los 138 cambios como primer commit de baseline. No descartar ninguno individualmente mientras el objetivo sea reproducir producción.

## Capa 2 — Soporte que se conserva

### Modificados: conservar los 35

- `.gitignore`, configuración de staging y lock de dependencias.
- 27 pruebas backend modificadas.
- Dos pruebas frontend y el escenario visual GRE.
- Checklist beta y documentación operativa/XML de Smart PSE.

Estos archivos explican o validan el runtime. Deben ir en un commit posterior, no mezclados con el baseline ejecutable.

### Nuevos: conservar 45 y separar 10 referencias opcionales

Conservar como soporte operativo:

- 16 pruebas backend nuevas de recuperación, Guías, PostgreSQL, seguridad y guard.
- Seis fixtures/especificaciones E2E de recuperación, contingencia, Guías y acciones.
- `contracts/operational_routes.json` y `contracts/release_assets.json`.
- `scripts/project_worker_release.py`, `scripts/release_guard.py` y `scripts/verify_recovery.ps1`.
- `backend/audit_smartpse_documents.py` y `backend/preflight_smartpse_gre_demo.py`.
- Configuración local de Supabase sin secretos.
- Informes de recuperación, acciones documentales, GRE, staging y publicación canónica.

Mantener fuera del baseline operativo y decidir en un bloque documental:

- Tres informes de `.impeccable/critique/`.
- `ANALISIS_INKORA.md` y `CODEX_BACKEND_SCALABILITY_TASK .md`.
- Los cinco documentos `docs/pricing/`.
- `docs/MODULOS_PRODUCTO_INKORA.md`.
- `scripts/workspace_inventory.py`, útil para esta recuperación pero no requerido por el producto ni por el despliegue.

Estos diez archivos no son basura; simplemente no son requisito del baseline productivo.

## Eliminaciones de soporte

### Confirmadas: mantener eliminadas 172 salidas generadas

`frontend/.svelte-kit/` contiene 172 artefactos compilados de otro frontend. No son fuente de Inkora React/Vite y no deben estar versionados. La consolidación de soporte debe agregar `frontend/.svelte-kit/` a `.gitignore` para evitar que reaparezcan.

### Confirmadas por sustitución: mantener eliminados

- `backend/scripts/audit_smartpse_emission_evidence.py`: sustituido por las herramientas actuales de auditoría/preflight.
- `backend/test_fiscal_clock.py`: depende del servicio fiscal deliberadamente excluido.
- `frontend/e2e/beta-launch-scope.spec.js` y `frontend/src/lib/utils/betaLaunchScope.test.js`: validan un gating que la recuperación decidió no reincorporar.
- Los cuatro ejecutores históricos de `pruebas/`: sustituidos por `scripts/verify_recovery.ps1` y suites focalizadas.

### Recuperación recomendada antes del commit de soporte

Estas pruebas de `main` siguen cubriendo funciones vigentes y conviene restaurarlas en el worktree aislado, ejecutarlas y mantenerlas solo si pasan sin debilitar controles:

- `backend/test_document_lookup_normalization.py`
- `backend/test_emission_worker_resilience.py`
- `backend/test_storage_service.py`
- `backend/test_ubl21_calculation_contract.py`
- `frontend/e2e/beta-demo-smoke.spec.js`
- `frontend/e2e/landing.spec.js`

### Documentación histórica: no decidir en bloque

Hay 40 documentos eliminados frente a `main`, entre planes antiguos, resultados, diseños y notas de implementación. Git ya conserva su historia, pero algunos pueden contener decisiones todavía útiles. No deben restaurarse ni confirmarse todos juntos. Revisarlos contra `RELEASE_CANONICO.md`, `RECUPERACION_VERSION_2026-09-18.md` y los informes GRE; luego archivar o eliminar individualmente.

## Propuesta exacta de preparación

### Commit 1 — Baseline ejecutable

- Preparar exclusivamente las rutas presentes en el manifiesto productivo.
- Preparar además las diez eliminaciones runtime enumeradas.
- Verificar el árbol preparado contra la huella productiva antes del commit.
- No incluir documentos, pruebas externas al manifiesto ni limpieza generada.

Resultado esperado: 138 cambios efectivos frente a `main`, con runtime idéntico a producción.

### Commit 2 — Controles de calidad

- Los 35 soportes modificados.
- Los 45 soportes nuevos operativos.
- Las seis pruebas recomendadas, después de restaurarlas y ejecutarlas.
- La eliminación de `.svelte-kit/` y su regla de ignore.
- Sin resolver todavía los 40 documentos históricos ni las diez referencias opcionales.

La cifra final del segundo commit se recalculará tras ejecutar las pruebas restauradas.

## Verificaciones realizadas

- Runtime del worktree: 366 archivos, huella `1755dc0ee9a6e22395b991f51e185b0c2437826c42ff94326643abab01a74a73`.
- Respaldo: 632 archivos actuales y 29 copias HEAD, correcto.
- `backend/test_release_guard.py`: 5 aprobadas.
- Alembic: una sola cabeza, `0022_gre_sales_documents`.
- Índice del worktree: vacío.
- Ninguna consulta o modificación de Vercel, Railway, Supabase o Smart PSE.

## Siguiente bloque recomendado

Preparar solo el **Commit 1** en staging —sin crearlo todavía— y validar que el contenido staged reproduce exactamente la huella de producción. Esta operación es reversible en el worktree aislado y no afecta la raíz ni los despliegues.

## Resultado de la preparación local

El runtime quedó preparado en staging dentro del worktree aislado, sin commit:

- 94 modificaciones.
- 34 archivos nuevos.
- 10 eliminaciones.
- 138 cambios totales con detección de renombres desactivada.
- Cero archivos de soporte incorporados accidentalmente.

Git presenta dos pares como renombres por similitud de contenido (`0010_quote_wallet_selection` y `0011_extended_unit_price_precision` hacia revisiones de la cadena productiva). Sin detección de renombres, las diez eliminaciones y 34 altas permanecen explícitas.

La verificación desde el índice encontró 256 archivos idénticos byte por byte y 110 diferencias exclusivamente de saltos de línea. No existe ninguna diferencia sustantiva entre los 366 archivos staged y el paquete productivo. Esto revela que la huella anterior depende de la representación de fin de línea del worktree de Windows:

- Huella del paquete desplegado: `1755dc0ee9a6e22395b991f51e185b0c2437826c42ff94326643abab01a74a73`.
- Huella del contenido normalizado almacenado en el índice Git: `63041dbb3826a7b3967d0e159912f0b632a1c476724d35ab155fe6010bc47db2`.

No se modificó `.gitattributes` ni se reescribieron archivos para forzar una coincidencia artificial. Antes de convertir esta preparación en commit será necesario decidir, en un bloque separado, si el guard debe normalizar texto o si se fija una política de fin de línea. El staging actual es lógicamente equivalente a producción, pero no debe describirse como idéntico byte por byte después de la normalización de Git.

No se creó commit, push o despliegue. El árbol raíz original continúa fuera de este staging.

## Revisión de pruebas recuperables

Se restauraron en el worktree aislado, sin incorporarlas al staging del runtime, las seis pruebas de `main` que seguían cubriendo funciones vigentes:

- `backend/test_document_lookup_normalization.py`
- `backend/test_emission_worker_resilience.py`
- `backend/test_storage_service.py`
- `backend/test_ubl21_calculation_contract.py`
- `frontend/e2e/beta-demo-smoke.spec.js`
- `frontend/e2e/landing.spec.js`

Las cuatro pruebas backend se ejecutaron de forma focalizada. Resultado: **6 aprobadas y 3 fallidas**. Las aprobaciones confirman la normalización de búsqueda documental, el contrato de cálculos UBL y parte del comportamiento de Storage/worker. Las fallas no se ocultaron ni se corrigieron dentro de este bloque de organización:

1. **P1 — resiliencia del worker:** `run_worker_loop()` deja escapar un `SQLAlchemyError` durante la recuperación de trabajos vencidos, por lo que el proceso puede terminar ante una interrupción temporal de base de datos.
2. **P1 — defensa en profundidad de Storage:** la validación de configuración exige `SUPABASE_SERVICE_ROLE_KEY` al construir settings fuera de local, pero `get_supabase_client()` todavía permite caer a `SUPABASE_KEY` si la configuración es alterada o reutilizada después de arrancar.
3. **Contrato de readiness por rediseñar:** la prueba histórica esperaba listar, escribir, descargar y borrar un objeto. El runtime actual solo informa configuración. No debe recuperarse mecánicamente un probe destructivo; corresponde diseñar una comprobación remota segura y explícita, separando lectura de una prueba de escritura controlada.

Las dos pruebas E2E quedaron recuperadas para inspección posterior, pero no se ejecutaron porque los P1 anteriores deben registrarse primero y este bloque no autoriza cambios operativos.

También se añadió `frontend/.svelte-kit/` al `.gitignore` del worktree aislado. Esto evita que los 172 artefactos generados vuelvan a versionarse. La regla no fue incorporada al staging del runtime y no modifica el repositorio raíz.

El staging ejecutable continúa aislado: 138 cambios con detección de renombres desactivada, sin pruebas, contratos ni documentos mezclados. Estos hallazgos deben resolverse en bloques P1 independientes antes de preparar el soporte definitivo.

## Bloque P1 local — resiliencia del worker

El primer P1 se corrigió como una capa de trabajo **no staged** sobre el baseline preparado. `run_worker_loop()` ahora protege también la creación de la sesión, captura `SQLAlchemyError`, intenta rollback si corresponde, registra el fallo, espera el intervalo normal y vuelve al ciclo sin terminar el proceso. El cambio no captura errores de programación genéricos ni modifica el procesamiento fiscal de cada trabajo.

Se amplió `backend/test_emission_worker_resilience.py` para cubrir tanto el error durante la recuperación de trabajos como el fallo al crear la sesión. La suite focalizada de cola y configuración terminó con **26 pruebas aprobadas**.

El baseline productivo staged permanece en 138 cambios; este arreglo y su prueba continúan fuera del índice para que puedan revisarse como un bloque separado. No hubo commit ni despliegue.

## Bloque P1 local — clave privilegiada de Storage

El segundo P1 se corrigió también como capa **no staged**. `Settings.has_supabase_storage` exige ahora `SUPABASE_SERVICE_ROLE_KEY` en staging/producción y conserva el uso de `SUPABASE_KEY` únicamente como fallback local. `get_supabase_client()` repite esa validación antes de devolver incluso un cliente cacheado, evitando que una configuración inválida eluda el control después del arranque.

Se añadieron pruebas para el rechazo de una configuración remota con solo clave pública y para conservar el desarrollo local con clave pública. La regresión focalizada de Storage, artefactos fiscales, PDF, uploads por tenant y recuperación documental terminó con **67 pruebas aprobadas y una prueba de readiness deliberadamente excluida**. Esa prueba antigua efectúa escritura y borrado y será tratada en un bloque de diseño separado.

No se leyeron ni cambiaron secretos reales, variables remotas o buckets. No hubo commit ni despliegue.

## Bloque P2 local — readiness de Storage de solo lectura

`check_storage_ready()` valida ahora, para el bucket privado y el bucket de activos públicos, que el bucket pueda consultarse y que sus objetos puedan listarse con límite uno. No sube, descarga, sobrescribe ni elimina archivos. Los fallos se reducen al nombre de la excepción para evitar filtrar respuestas sensibles del proveedor.

`GET /ops/readiness` usa el resultado real de acceso en lugar de considerar saludable a Storage por estar solamente configurado. La prueba cubre acceso correcto, errores sanitizados y el caso configurado-pero-inaccesible. La regresión focalizada terminó con **70 pruebas aprobadas**.

El cambio continúa fuera del staging del baseline. No se consultaron servicios remotos y no hubo commit ni despliegue.

## Bloque organizativo local — huella canónica de entrega

El guard de entrega usa ahora manifiestos versionados. Las entregas nuevas declaran `hash_mode: canonical-text-v1`: normalizan CRLF y CR a LF únicamente cuando el archivo es UTF-8 sin bytes nulos; los binarios permanecen byte-exactos. El modo se incorpora a la huella global para que no pueda confundirse con el algoritmo anterior.

Los manifiestos históricos sin `hash_mode` continúan verificándose como `raw-v1`. El paquete productivo existente conserva y valida su huella `1755dc0ee9a6e22395b991f51e185b0c2437826c42ff94326643abab01a74a73`. El candidato local actual —que además contiene los arreglos P1 no desplegados— obtiene una huella canónica distinta y no debe confundirse con producción.

`backend/test_release_guard.py` cubre equivalencia LF/CRLF, preservación de diferencias binarias, cambios reales de texto, identidad del algoritmo y verificación de paquetes canónicos. Resultado: **9 pruebas aprobadas**. No se generó paquete nuevo, commit ni despliegue.
