# Manifiestos de commits pendientes — 19/09/2026

## Estado y límites

- Rama local: `codex/production-baseline-20260918`.
- Base exacta: `3d5654dc5b65e0e87500fe35402046c8aa18a8e2`.
- El índice debe permanecer vacío hasta recibir autorización expresa.
- Estos manifiestos no autorizan commit, push, merge ni despliegue.
- Está prohibido sustituir las listas por `git add .` o `git add -A`.
- Cada candidato debe probarse en un worktree aislado creado desde el commit
  anterior; el árbol de trabajo actual contiene también las capas siguientes.

Las huellas de capa se calculan como SHA256 del texto UTF-8 formado por cada
ruta ordenada como aparece debajo, un tabulador y el SHA256 del contenido,
separando registros con LF.

## 1. Reproducibilidad, guard y E2E aislado

Mensaje sugerido: `test(release): make local verification reproducible`

Huella de capa:
`42b74f4f446ed556fe9b7c0e249160b230e6d746d218d627024aab2bb7d3b610`

Lista positiva:

```text
Dockerfile
backend/Dockerfile
backend/requirements.in
backend/requirements.txt
backend/requirements-lock.txt
backend/requirements-test.txt
backend/seed_demo_tenant.py
backend/test_dependency_lock.py
backend/test_release_guard.py
backend/test_seed_demo_tenant.py
frontend/e2e/fiscal-contingency.spec.js
frontend/e2e/landing.spec.js
frontend/e2e/smartpse-gre-visual.spec.js
frontend/index.html
frontend/playwright.config.js
frontend/src/app.css
frontend/src/styles/globals.css
frontend/src/styles/tokens.css
scripts/release_guard.py
scripts/run_e2e_local.py
scripts/verify_recovery.ps1
docs/RELEASE_CANONICO.md
docs/STAGING_POSTGRES_RUNBOOK.md
```

Validación requerida en el candidato aislado:

```powershell
python -m pip install -r backend/requirements-test.txt
python -m pip check
Push-Location backend
python -m pytest -q --ignore=test_sale_dispatch_postgres.py --ignore=test_cotizaciones_postgres.py --ignore=test_inventory_recovery_postgres.py
Pop-Location
Push-Location frontend
npm ci --ignore-scripts
npm test
npm run lint
npm run build
Pop-Location
python scripts/run_e2e_local.py
```

Las seis pruebas PostgreSQL se ejecutan después con las dos bases locales
desechables y los prefijos exigidos por el runbook.

## 2. Seguridad frontend y presupuesto de bundle

Mensaje sugerido: `fix(frontend): harden router and bundle gate`

Huella de capa:
`afa78fd404a8d37e2f5a28f1ce2e2ea55c3c5b7dbec86f96d555a97d4a9057c7`

Lista positiva:

```text
.github/workflows/release-gate.yml
frontend/e2e/auth.setup.js
frontend/e2e/helpers/auth.js
frontend/package-lock.json
frontend/package.json
frontend/src/App.jsx
frontend/scripts/check-bundle-size.mjs
```

Esta capa agrupa React Router 7, los parches del toolchain y el presupuesto de
bundle porque `package.json`, `package-lock.json` y el workflow son archivos
compartidos. Separarlos desde el estado final produciría commits intermedios
incompletos o exigiría reconstruir un lock histórico no conservado.

Validación requerida:

```powershell
Push-Location frontend
npm ci --ignore-scripts
npm audit
npm test
npm run lint
npm run build
npm run check:bundle
Pop-Location
python scripts/run_e2e_local.py
```

Resultado confirmado antes de preparar: 0 vulnerabilidades, 47 pruebas
frontend, lint, build, presupuesto aprobado y 53 pruebas E2E.

## 3. Lifespan FastAPI

Mensaje sugerido: `refactor(api): migrate startup ping to lifespan`

Huella de capa:
`e6d3eea136d846cd5f6bbeb3fca3cbaa38881124c48cbb3cd9894ca76a2c6ccb`

Lista positiva:

```text
backend/main.py
backend/test_main_lifespan.py
```

Validación requerida:

```powershell
Push-Location backend
python -m pytest test_main_lifespan.py test_legacy_frozen_gating.py -q -W error::DeprecationWarning
python -m pytest -q --ignore=test_sale_dispatch_postgres.py --ignore=test_cotizaciones_postgres.py --ignore=test_inventory_recovery_postgres.py
Pop-Location
python scripts/run_e2e_local.py
```

Resultado confirmado: 8 pruebas focalizadas, 689 pruebas backend y 53 E2E.

## 4. Evidencia final

Mensaje sugerido: `docs(release): record verified local layers`

Lista positiva:

```text
docs/CAPAS_LOCALES_Y_ORDEN_DE_COMMITS_2026-09-18.md
docs/MANIFIESTOS_COMMITS_PENDIENTES_2026-09-19.md
```

Antes de preparar cada commit:

1. Confirmar `git diff --cached --quiet`.
2. Comparar la lista positiva con `git status --short`.
3. Verificar la huella de la capa.
4. Preparar exclusivamente las rutas de esa capa.
5. Revisar `git diff --cached --check` y `git diff --cached --name-status`.
6. Ejecutar las pruebas en un worktree aislado del candidato.
7. No publicar mientras `scripts/release_guard.py check` no termine limpio sobre
   el commit candidato y el resto de capas esté fuera de ese worktree.

## Cobertura del árbol actual

Los cuatro manifiestos cubren todos los archivos modificados o nuevos del
árbol al momento de esta revisión. Ningún archivo se asigna a dos commits.
