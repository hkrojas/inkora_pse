# GRE remitente — preparación de publicación

Fecha de revisión: 18/09/2026.

## Estado

La implementación y sus pruebas locales están cerradas, pero la publicación a
staging está en **NO-GO** porque hoy no existe un destino remoto aislado.

No se modificó Vercel, Railway, Supabase, Papelería Gráfica ni Smart PSE.

## Evidencia del preflight

- El checkout local de Vercel está enlazado a `inkora-pse`; los despliegues
  listados pertenecen al ambiente `Production`.
- `VITE_API_URL` está configurada solo para `Development` y `Production`; no
  existe una variable `Preview` que identifique una API de staging.
- Railway contiene únicamente el entorno `production`, con los servicios
  `inkora_pse` e `inkora_pse_worker` activos.
- La configuración local de Supabase declara PostgreSQL 17, pero no existe un
  `project-ref` remoto de staging enlazado en `supabase/.temp`.
- Alembic tiene una única cabeza: `0022_gre_sales_documents`.

Crear un entorno Railway duplicando producción no es una solución segura:
podría heredar `DATABASE_URL`, credenciales Smart PSE/SUNAT y Storage de
producción. Tampoco se debe publicar un preview Vercel que apunte a la API
productiva para ejecutar pruebas de escritura.

## Barreras incorporadas

`backend/deploy_staging.sh` ahora exige:

- `ENVIRONMENT=staging` y `FISCAL_ENV=beta` mediante la configuración del
  runtime;
- confirmación explícita y snapshot restaurable;
- `STAGING_TARGET_ID` concreto y presente en la identidad de `DATABASE_URL`;
- `RELEASE_ID` común para API, worker y frontend;
- una única cabeza Alembic y coincidencia exacta con
  `0022_gre_sales_documents` antes y después de migrar;
- rechazo cuando `DATABASE_URL` coincide con la URL productiva conocida.

El script pasó validación sintáctica con Git Bash. El runbook y el archivo de
entorno de ejemplo fueron actualizados a `0022` y a orígenes factura/boleta.

## Requisitos para habilitar staging

1. Crear un proyecto PostgreSQL/Supabase separado y restaurable, con Storage
   privado separado.
2. Crear un entorno Railway `staging` desde configuración limpia, no desde una
   copia de secretos productivos; desplegar API y worker con la misma
   `RELEASE_ID`.
3. Crear un proyecto Vercel de staging o variables Preview que apunten
   exclusivamente a la API de staging.
4. Mantener feature flag `guides` solo para un tenant sintético y proveedor
   simulado. No cargar credenciales productivas.
5. Ejecutar migración, smoke de lectura/escritura, Playwright y verificación de
   logs; recién después evaluar la prueba demo Smart PSE por separado.

## Evidencia acumulada antes de publicar

- PostgreSQL 17 aislado: migración, restauración y concurrencia aprobadas.
- Backend: 541 pruebas aprobadas, 5 omitidas explícitamente.
- Frontend: ESLint, 34 pruebas Node y build Vite aprobados.
- Playwright aislado: 7 escenarios GRE aprobados.
- PDF GRE Inkora renderizado y revisado visualmente.
- Smart PSE: contrato técnico probado con simulación; homologación demo real
  pendiente y no presentada como aceptación.
