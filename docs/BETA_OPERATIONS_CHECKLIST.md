# Inkora - Checklist Operativo Beta Pagada

Este checklist se usa antes de abrir Inkora a una beta pagada controlada.
El objetivo es separar claramente la beta operativa de la produccion fiscal, mantener la base de datos recuperable y evitar que modulos fuera del launch-scope queden expuestos.

## 1. Alcance De La Beta

| Item | Prioridad | Estado esperado | Responsable sugerido | Verificacion |
|---|---:|---|---|---|
| Beta controlada | P0 | Solo tenants piloto autorizados, con datos ficticios o consentimiento explicito | Founder / Ops | Lista de tenants beta aprobada |
| Produccion fiscal | P0 | Separada de beta; no activar `FISCAL_ENV=production` sin go fiscal explicito | Founder / Fiscal / Tech lead | Aprobacion escrita antes del cambio |
| Emision real | P0 | Desactivada hasta prueba controlada | Fiscal / Backend | Worker y credenciales revisadas |
| Datos reales | P0 | No cargar clientes reales hasta validar rollback, logs y soporte | Ops | Checklist firmado por responsable |

## 2. Variables De Entorno Finales

| Variable | Prioridad | Estado esperado | Responsable sugerido | Verificacion |
|---|---:|---|---|---|
| `ENVIRONMENT` | P0 | `staging` para beta controlada; `production` solo al pasar a produccion | DevOps | Revisar runtime |
| `APP_ENV` | P0 | Igual a `ENVIRONMENT` | DevOps | Revisar runtime |
| `FISCAL_ENV` | P0 | `beta` durante beta controlada | Tech lead | Revisar runtime |
| `DATABASE_URL` | P0 | Apunta a DB beta/staging autorizada; nunca hardcodeada | DevOps | URL redacted |
| `SECRET_KEY` | P0 | Fuerte, unico por entorno, fuera del repo | DevOps | Secret manager |
| `BACKEND_URL` | P0 | URL real del backend; no `localhost` en staging/production | DevOps | `/health` |
| `FRONTEND_URL` | P0 | URL real del frontend | DevOps | Navegador |
| `VITE_API_URL` | P0 | Apunta al backend correcto | Frontend / DevOps | Network tab / build env |
| `CORS_ALLOW_ORIGINS` | P0 | Solo dominios esperados | DevOps | OpenAPI/browser |
| APISPeru / SUNAT | P0 | Credenciales beta/sandbox hasta go fiscal | Fiscal / Backend | Secret manager |
| Supabase Storage | P0 | URL, key y bucket del entorno beta | DevOps | Smoke upload/download no fiscal |
| Worker flags | P0 | Worker controlado y monitoreado; no emision real accidental | Backend / Ops | Proceso worker y logs |

Regla: secretos reales, tokens, passwords, certificados, claves SOL, URLs firmadas y credenciales de proveedores no van al repo, no van en capturas y no se imprimen en reportes.

## 3. Seguridad

| Item | Prioridad | Estado esperado | Responsable sugerido | Verificacion |
|---|---:|---|---|---|
| Tenant isolation | P0 | Toda consulta critica filtra por tenant autenticado | Backend | Suite P0/P1 |
| Ownership explicito | P0 | Endpoints sensibles validan que el recurso pertenezca al tenant | Backend | Tests de hardening |
| Superadmin | P0 | Solo `is_superadmin=true`; no depender de `rol="superadmin"` | Backend / Frontend | Tests superadmin |
| Legacy frozen | P1 | No montado fuera de local/dev; no aparece en OpenAPI staging/production | Backend | `/openapi.json` |
| Legacy fiscal | P0 | Rutas legacy no aparecen o responden `410 Gone` | Backend | HTTP seguro |
| JWT | P0 | `SECRET_KEY` fuerte y rotacion planificada | DevOps | Secret manager |
| Password reset | P1 | Reset auditado, sin imprimir password en logs | Backend / Ops | Audit logs |
| Auditoria | P1 | Mutaciones superadmin criticas generan `AuditLog` | Backend / Ops | Tabla `audit_logs` |
| Logs seguros | P0 | Logs no imprimen tokens, passwords, certificados, XML firmado, payloads fiscales sensibles ni Authorization headers | Backend / Ops | Revision de logs |

## 4. Operacion Fiscal

| Item | Prioridad | Estado esperado | Responsable sugerido | Verificacion |
|---|---:|---|---|---|
| APISPeru beta | P0 | Credenciales y URLs de beta/sandbox | Fiscal / Backend | Config redacted |
| SUNAT directo | P1 | No activar salvo prueba especifica | Fiscal / Backend | Config redacted |
| Worker fiscal | P0 | Encendido solo con monitoreo y tenant autorizado | Backend / Ops | Logs worker |
| Retries | P0 | No duplican comprobantes; errores no retryable quedan terminales | Backend | Suite emission jobs |
| Notas credito/debito | P0 | Parciales, limite acumulado y revalidacion pre-emision | Backend / Fiscal | Suite fiscal |
| Bajas | P1 | Probar primero con datos ficticios | Fiscal | Runbook manual |
| Resumen diario | P1 | Probar con documentos ficticios antes de clientes reales | Fiscal | Runbook manual |
| Reversiones | P1 | Probar sin clientes reales | Fiscal | Runbook manual |
| Retenciones/percepciones | P1 | Mantener beta hasta validacion fiscal | Fiscal | Runbook manual |

No probar con clientes reales todavia: emision fiscal real, anulaciones reales, bajas reales, resumen diario real, reversiones reales, retenciones/percepciones reales y credenciales SOL/certificados productivos.

## 5. Base De Datos Y Migraciones

| Item | Prioridad | Estado esperado | Responsable sugerido | Verificacion |
|---|---:|---|---|---|
| Backup logico | P0 | Dump y TOC restaurables antes de cambios | DevOps | `pg_restore --list` |
| Integrity dry-run | P0 | Sin bloqueantes ni advertencias no justificadas | Backend / Ops | `python backend/migrate_beta_integrity.py --dry-run` |
| Integrity apply | P0 | Ejecutado solo con backup y autorizacion | Backend / Ops | Reporte apply |
| Alembic current | P0 | `0001_prebeta_baseline (head)` | Backend | `alembic current` |
| Alembic heads | P0 | `0001_prebeta_baseline (head)` | Backend | `alembic heads` |
| Rollback | P0 | Restauracion documentada y responsable asignado | DevOps | Ensayo en entorno aparte |
| Cambios futuros | P0 | Todo cambio de esquema posterior a `0001_prebeta_baseline` va por Alembic | Backend | Revision PR |

Regla: no crear nuevos `migrate_*.py` para cambios de esquema despues del baseline. Los scripts legacy quedan como bootstrap historico/pre-Alembic.

## 6. Frontend

| Item | Prioridad | Estado esperado | Responsable sugerido | Verificacion |
|---|---:|---|---|---|
| Lint | P1 | Sin errores | Frontend | `npm run lint` |
| Build | P0 | Sin errores y sin warning de chunk grande critico | Frontend | `npm run build` |
| URLs finales | P0 | Frontend apunta al backend final correcto | Frontend / DevOps | Network tab |
| Dominio / HTTPS | P0 | Dominio valido y certificado vigente | DevOps | Navegador |
| Dashboard | P1 | Copy honesto y sin saldos legacy como verdad | Frontend | Smoke manual/E2E |
| Lazy loading | P1 | Chunks cargan sin pantalla blanca | Frontend | Playwright smoke |
| Consola/network | P1 | Sin `console.error`, API 5xx ni requests a puertos incorrectos | Frontend / QA | Playwright smoke |

## 7. Post-Deploy Checks

| Check | Prioridad | Estado esperado | Responsable sugerido | Verificacion |
|---|---:|---|---|---|
| Backend health | P0 | `/health` responde 200 y entorno esperado | Ops | `GET /health` |
| OpenAPI | P0 | `/openapi.json` responde 200; sin `frozen-non-launch` fuera de local/dev | Backend / Ops | `GET /openapi.json` |
| Legacy fiscal | P0 | Legacy fiscal no aparece en OpenAPI o responde `410 Gone` | Backend | HTTP seguro |
| Login tenant | P0 | Tenant beta puede iniciar sesion | QA / Ops | UI |
| Dashboard | P0 | Carga sin pantalla blanca ni errores de red | QA / Ops | UI |
| Playwright smoke | P0 | Smoke E2E verde | QA / Frontend | `npx playwright test --project=chromium` |
| Logs post-deploy | P0 | Sin 500 nuevos, sin secretos impresos | Ops | Logs backend/worker |

## 8. Monitoreo Y Logs

| Item | Prioridad | Estado esperado | Responsable sugerido | Verificacion |
|---|---:|---|---|---|
| Backend logs | P0 | Errores 500 visibles y accionables | Ops | Log drain/plataforma |
| Worker logs | P0 | Jobs, retries, terminal failures y no-retryables visibles | Backend / Ops | Logs worker |
| APISPeru/SUNAT logs | P0 | Errores visibles sin payloads sensibles completos | Backend / Fiscal | Logs sanitizados |
| Audit logs | P1 | Acciones superadmin trazables | Ops | `audit_logs` |
| Storage logs | P1 | Fallos de upload/download visibles | Ops | Logs plataforma |
| Alertas | P1 | Alertas para 500, fallos worker y auth anomalies | Ops | Monitor |

## 9. Go / No-Go

| Criterio | Go | No-Go |
|---|---|---|
| Tenant piloto | Tenant beta aprobado, subscription activa y datos controlados | Tenant ambiguo, sin subscription o con datos reales no autorizados |
| Fiscal | `FISCAL_ENV=beta`, proveedor beta/sandbox y emision real bloqueada hasta prueba controlada | Credenciales productivas o worker sin monitoreo |
| DB | Backup validado, integrity limpio, Alembic baseline en head | Sin backup o dry-run con bloqueantes |
| Seguridad | Superadmin protegido, legacy frozen oculto, legacy fiscal `410` | Rutas frozen visibles en staging/production |
| Frontend | Lint/build/smoke verde | Pantalla blanca, chunks rotos, API incorrecta |
| Logs | Sin secretos ni payloads sensibles | Tokens/passwords/certificados en logs |
| Rollback | Responsable y procedimiento definido | Sin responsable o sin backup restaurable |

## 10. Rollback

1. Congelar acceso al tenant afectado.
2. Detener worker fiscal si hay riesgo de emision duplicada.
3. Conservar logs y artifacts del incidente.
4. Restaurar desde backup validado en entorno controlado.
5. Comparar `alembic current`, integridad y datos criticos.
6. Reabrir solo despues de smoke backend/frontend y aprobacion del responsable.

## 11. Responsables Sugeridos

| Area | Responsable |
|---|---|
| Go fiscal | Founder + responsable fiscal |
| DB / backups / rollback | DevOps |
| Backend / Alembic / integrity | Backend lead |
| Frontend / E2E | Frontend lead / QA |
| Monitoreo / logs | Ops |
| Superadmin / tenants | Ops + Backend |

## Recomendacion Final

Inkora puede pasar a beta pagada controlada si se mantiene la separacion entre beta operativa y produccion fiscal. El primer tenant debe operar con monitoreo activo, emision real bloqueada hasta prueba fiscal aprobada, backups validados y rollback listo.
