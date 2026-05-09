# VALIDATION DATA CLEANUP RESULTS - Inkora PSE

## 1. Datos generales

- Fecha/hora de ejecucion: 2026-05-08 20:35 America/Lima.
- Repo: `hkrojas/inkora_pse`.
- Branch local: `validation/post-deploy`.
- Base remota validada antes de ejecutar: `inkora_pse/main` en `f3b3219 Record validation data cleanup dry run`.
- Supabase project: `inkora_pse` (`wiezwkosiuczpnbnvmef`).
- Backend Railway URL: `https://inkorapse-production.up.railway.app`.
- Autorizacion recibida: `Autorizo borrar tenants temporales 2, 3 y 4`.

## 2. Resultado ejecutivo

- Estado: `PASS`.
- Limpieza real ejecutada para `tenant_id IN (2, 3, 4)`.
- No se modifico backend, frontend, `.env`, secretos ni reglas fiscales.
- La ejecucion uso transaccion SQL y validaciones previas.
- No se ejecuto `TRUNCATE`.
- No se ejecuto `UPDATE`.
- Se ejecutaron `DELETE` solo para datos asociados a tenants temporales `2`, `3` y `4`.

## 3. Backup / resguardo previo

Backup logico reciente confirmado antes de borrar:

- Archivo: `C:\Users\HP\Desktop\inkora_backups\inkora_pse_pre_indexes_20260508-165311.dump`
- Tamano: `338573` bytes.
- LastWriteTime local: `2026-05-08 16:53:46`.
- SHA256 documentado previamente: `408A3A0A8AA0698306086A9B7F03C7E09DEEAC2FD7F56DD9E1CE4943C9893AF6`.

Nota: Supabase Free Plan no tiene PITR gestionado; la limpieza se ejecuto con respaldo logico manual disponible.

## 4. Dry-run previo

Se ejecuto nuevamente dry-run `SELECT` antes de borrar.

Resultado:

- Tenants encontrados: `3`.
- Usuarios validation encontrados: `3`.
- `fiscal_risk`: `0`.
- `active_jobs`: `0`.

Conteos no cero del dry-run:

| Tenant | Tabla | Filas |
| --- | --- | ---: |
| `2` | `audit_logs_by_validation_users` | 1 |
| `2` | `subscriptions` | 1 |
| `3` | `subscriptions` | 1 |
| `4` | `audit_logs_by_validation_users` | 8 |
| `4` | `clientes` | 1 |
| `4` | `cotizacion_items` | 1 |
| `4` | `cotizaciones` | 1 |
| `4` | `productos` | 1 |
| `4` | `subscriptions` | 1 |

El dry-run coincidio con el plan documentado. No aparecieron documentos fiscales reales, pagos reales, jobs activos ni datos MRP/frozen.

## 5. Limpieza ejecutada

La limpieza se ejecuto con una transaccion SQL.

Guardas previas dentro de la transaccion:

- `3` tenants con nombre `Inkora Validation ...` y RUC esperados.
- `3` usuarios validation `@inkora.test`.
- `1` cliente temporal.
- `1` producto temporal.
- `1` cotizacion temporal.
- `1` item de cotizacion temporal.
- `3` subscriptions temporales.
- `9` audit logs asociados a usuarios temporales.
- `0` documentos fiscales reales.
- `0` jobs fiscales activos.
- `0` pagos.
- `0` guias.
- `0` MRP/frozen.

Filas eliminadas por tabla:

| Tabla | Filas eliminadas |
| --- | ---: |
| `audit_logs` | 9 |
| `guia_remision_items` | 0 |
| `cotizacion_items` | 1 |
| `ordenes_produccion_detalle` | 0 |
| `alertas_inventario` | 0 |
| `ordenes_produccion` | 0 |
| `recetas_bom` | 0 |
| `proveedores` | 0 |
| `insumos` | 0 |
| `pagos` | 0 |
| `document_emission_jobs` | 0 |
| `guias_remision` | 0 |
| `resumenes_diarios` | 0 |
| `reversiones_fiscales` | 0 |
| `retenciones_fiscales` | 0 |
| `percepciones_fiscales` | 0 |
| `subscription_payments` | 0 |
| `usage_limits` | 0 |
| `subscriptions` | 3 |
| `cotizaciones` | 1 |
| `clientes` | 1 |
| `productos` | 1 |
| `users` | 3 |
| `tenants` | 3 |

La transaccion finalizo con `COMMIT`.

## 6. Verificacion posterior

Verificacion SQL posterior a la limpieza:

| Check | Filas |
| --- | ---: |
| `tenants_2_3_4` | 0 |
| `validation_users` | 0 |
| `clientes` | 0 |
| `productos` | 0 |
| `cotizaciones` | 0 |
| `cotizacion_items` | 0 |
| `pagos` | 0 |
| `document_emission_jobs` | 0 |
| `guias_remision` | 0 |
| `subscriptions` | 0 |
| `subscription_payments` | 0 |
| `usage_limits` | 0 |
| `insumos` | 0 |
| `recetas_bom` | 0 |
| `proveedores` | 0 |
| `ordenes_produccion` | 0 |
| `alertas_inventario` | 0 |
| `audit_logs_by_validation_users` | 0 |

Resultado esperado cumplido:

- Tenants `2`, `3` y `4` ya no existen.
- Usuarios `validation` / `inkora.test` ya no existen.
- Clientes/productos/cotizaciones temporales ya no existen.
- `document_emission_jobs` para esos tenants = `0`.
- Datos MRP/frozen para esos tenants = `0`.

## 7. Health Railway

Comando:

```powershell
curl.exe -i https://inkorapse-production.up.railway.app/health
```

Resultado:

- `HTTP/1.1 200 OK`.
- Fecha header: `Sat, 09 May 2026 01:35:14 GMT`.
- `X-Railway-Request-Id`: `ldm3DCsCTOeiz56-ozsQ6Q`.
- `X-Request-Id`: `83b2aaee-0690-4c81-b6f9-af2c8739d03e`.

Body:

```json
{"status":"ok","environment":"staging"}
```

## 8. Riesgos remanentes

- Supabase sigue sin PITR gestionado si el proyecto permanece en Free Plan.
- El dump logico manual existe, pero no reemplaza PITR para operacion con clientes reales.
- Railway sigue reportando `environment: "staging"`.
- La limpieza borro usuarios de validacion; tokens emitidos antes de la limpieza podrian existir hasta expirar, pero ya no corresponden a usuarios presentes en DB.

## 9. Comandos y herramientas usados

- `git status --short --branch`.
- `git log -1 --oneline`.
- `Get-ChildItem` / `Get-FileHash` sobre el dump logico local.
- `psql` via Supabase Session Pooler IPv4.
- Dry-run SQL con solo `SELECT`.
- Limpieza SQL transaccional con `DELETE` limitado a tenants `2`, `3` y `4`.
- Verificacion SQL post-cleanup con solo `SELECT`.
- `curl.exe -i https://inkorapse-production.up.railway.app/health`.

No se escribieron secretos en este documento.
