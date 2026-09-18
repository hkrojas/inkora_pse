# Runbook de staging PostgreSQL

Este procedimiento prepara y verifica **staging**. No debe ejecutarse contra producción.

## 1. Condiciones previas

- Ventana de mantenimiento abierta.
- `ENVIRONMENT=staging` confirmado.
- `DATABASE_URL` revisada sin imprimir usuario, contraseña ni host completo en tickets o chats.
- Acceso de restauración probado por el responsable de infraestructura.
- Worker fiscal detenido o sin tráfico durante la migración.
- `INIT_DB_ON_STARTUP=false`.
- Proyecto Supabase y entorno Railway exclusivos de staging; no se permite
  duplicar producción conservando su `DATABASE_URL` o credenciales fiscales.
- Una misma `RELEASE_ID` inmutable para backend, worker y frontend.

## 2. Backup y punto de retorno

1. Crear snapshot administrado de PostgreSQL.
2. Registrar su identificador y hora en Lima.
3. Confirmar que pertenece al proyecto de staging.
4. Definir para esta ejecución:

```bash
export STAGING_DEPLOY_CONFIRMATION=INKORA_STAGING
export STAGING_BACKUP_ID=<identificador-del-snapshot>
export STAGING_TARGET_ID=<project-ref-o-identificador-real-de-staging>
export RELEASE_ID=<git-sha-o-huella-inmutable>
```

Si existe acceso seguro a la URL de producción, definir `PRODUCTION_DATABASE_URL`; el script abortará si coincide con `DATABASE_URL`.

## 3. Preflight sin escrituras

Desde `backend/`:

```bash
python run_launch_migrations.py --dry-run --strict
python migrate_beta_integrity.py --dry-run
python -m alembic -c alembic.ini heads
python -m alembic -c alembic.ini current
```

Criterios para continuar:

- La cadena launch no tiene scripts faltantes.
- Integridad no reporta bloqueantes.
- `alembic heads` devuelve una sola cabeza.
- La cabeza esperada para esta entrega es `0022_gre_sales_documents`.

## 4. Bootstrap Alembic excepcional

Este paso se usa **solo** cuando la base existente fue construida con los scripts launch, pasó integridad y todavía no tiene tabla/revisión Alembic.

```bash
python run_launch_migrations.py --strict
python migrate_beta_integrity.py --dry-run
python migrate_beta_integrity.py --apply
python migrate_beta_integrity.py --dry-run
python -m alembic -c alembic.ini stamp 0001_prebeta_baseline
python -m alembic -c alembic.ini current
```

No ejecutar `stamp` si `alembic current` ya muestra una revisión. Nunca usarlo para ocultar una migración fallida.

## 5. Aplicación en staging

Con una revisión Alembic válida:

```bash
python run_launch_migrations.py --strict
python migrate_beta_integrity.py --dry-run
python migrate_beta_integrity.py --apply
python migrate_beta_integrity.py --dry-run
python -m alembic -c alembic.ini upgrade head
python -m alembic -c alembic.ini current
python -m alembic -c alembic.ini heads
```

Antes de aplicar `0022_gre_sales_documents` en el staging compartido, ejecutar
la homologación PostgreSQL en una base aislada cuyo nombre empiece con
`inkora_gre_`:

```bash
export INKORA_TEST_POSTGRES_URL=postgresql://<usuario>:<clave>@<host>:<puerto>/inkora_gre_test
export INKORA_REQUIRE_POSTGRES_TESTS=1
python -m pytest test_sale_dispatch_postgres.py -q
```

La suite se niega a destruir datos si el host no es local o si el nombre de la
base no tiene el prefijo `inkora_gre_`. `INKORA_REQUIRE_POSTGRES_TESTS=1`
convierte la ausencia de conexión en error; no permite omitir estos casos en la
homologación.

Alternativamente, `bash deploy_staging.sh` ejecuta esta secuencia y se niega a continuar sin confirmación de staging, snapshot y revisión Alembic previa.

## 6. Verificación posterior

```bash
python -m pytest test_fiscal_contingency.py test_emission_queue.py test_migrate_beta_integrity.py -q
```

Verificar además:

- `alembic current` coincide con `alembic heads`.
- La tabla `document_emission_attempts` existe.
- Las tablas `sale_dispatches`, `sale_dispatch_lines` y
  `guide_external_references` existen.
- `sale_dispatches` conserva tipo de origen `01/03`, resumen diario y evidencia
  de aceptación; las guías conservan observaciones y auditoría del acuerdo de
  transporte.
- `guia_remision_items.cantidad` es `NUMERIC(18,4)`.
- Las facturas y boletas históricas tipo `01/03` quedan con
  `dispatch_reconciliation_status='required'`; los demás documentos quedan en
  `not_required`.
- `tenants` contiene `fiscal_contingency_mode`, `fiscal_contingency_reason` y `fiscal_contingency_started_at`.
- El endpoint de consulta de contingencia responde únicamente a Superadmin.
- Activar contingencia en un tenant de prueba retiene jobs simulados, sin llamar SUNAT/PSE.
- Desactivar libera únicamente `contingency_pending`; `pending_confirmation` permanece aislado.
- Logs sin secretos, errores 5xx ni reintentos duplicados.

## 7. Go / no-go

**GO** solamente si:

- Backup identificado y restaurable.
- Dry-run final sin acciones pendientes ni bloqueantes.
- Una sola cabeza Alembic y revisión actual en la cabeza.
- Suites fiscal, cola e integridad verdes.
- Smoke frontend de contingencia verde.

**NO-GO** si falta cualquiera de esas condiciones, si aparecen referencias entre tenants, notas ambiguas, pagos sin enlace determinista o más de una cabeza Alembic.

## 8. Rollback

1. Detener backend y worker de staging.
2. Conservar logs y revisión Alembic observada; no ejecutar `stamp`, `downgrade` ni scripts manuales improvisados.
3. Restaurar el snapshot indicado por `STAGING_BACKUP_ID` en una instancia o rama de recuperación.
4. Validar conteos de tenants, documentos, pagos y jobs antes de redirigir tráfico.
5. Volver a desplegar la versión anterior del backend y frontend.
6. Ejecutar pruebas de lectura y mantener la emisión fiscal deshabilitada hasta confirmar consistencia.

Las revisiones `0019`, `0020`, `0021` y `0022` crean estructuras nuevas; el rollback
recomendado es restaurar snapshot y código anterior, no borrar columnas,
reservas ni historial de intentos manualmente. Restaurar la base no revierte
documentos que ya hayan sido aceptados por Smart PSE/SUNAT; esos documentos se
concilian antes de reabrir la emisión.
