# Smart PSE GRE - Operacion Backend

## Alcance

Este runbook aplica solo a `inkora_smartpse` y al flujo backend de guias de remision electronicas con Smart PSE.

APISPeru queda como codigo legacy tecnico. El backend no debe hacer fallback automatico a APISPeru cuando falten credenciales Smart PSE o SUNAT GRE.

## Configuracion Segura

Generar una llave Fernet para cifrar secretos:

```powershell
cd C:\Users\HP\Desktop\inkora_smartpse\backend
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Guardar el valor solo en `.env` o en el gestor de secretos del entorno:

```env
FIELD_ENCRYPTION_KEY=<llave-fernet>
```

No guardar esta llave en archivos tracked. `.env.example` y `.env.staging.example` deben contener solo placeholders.

## Migracion

Aplicar migraciones:

```powershell
cd C:\Users\HP\Desktop\inkora_smartpse\backend
alembic upgrade head
```

Columnas esperadas:

- `tenants.smartpse_gre_sol_username`
- `tenants.smartpse_gre_sol_password_enc`
- `tenants.smartpse_gre_client_id`
- `tenants.smartpse_gre_client_secret_enc`
- `tenants.smartpse_gre_status`
- `tenants.smartpse_gre_checked_at`
- `guias_remision.sunat_xml_content`
- `guias_remision.sunat_hash`
- `guias_remision.sunat_ticket`
- `guias_remision.provider_response`

## Endpoints Superadmin

Guardar o rotar credenciales SUNAT GRE:

```http
PUT /superadmin/tenants/{tenant_id}/smartpse/gre-credentials
```

Payload:

```json
{
  "sol_username": "USUARIO_SOL_CORTO",
  "sol_password": "CLAVE_SOL",
  "client_id": "CLIENT_ID_SUNAT",
  "client_secret": "CLIENT_SECRET_SUNAT"
}
```

Validar credenciales SUNAT GRE:

```http
POST /superadmin/tenants/{tenant_id}/smartpse/gre-credentials/check
```

Respuesta esperada:

```json
{
  "valid": true,
  "message": "Credenciales GRE aceptadas.",
  "provider_status_code": 200,
  "provider_detail": "ok"
}
```

Las respuestas de tenant/superadmin solo deben exponer:

- `has_smartpse_gre_credentials`
- `smartpse_gre_status`
- `smartpse_gre_checked_at`

Nunca deben exponer clave SOL, client secret ni valores descifrados.

## Emision GRE

Emitir por endpoint normal de Inkora:

```http
POST /guias-remision/{guia_id}/emitir?mode=sync
```

En demo, Smart PSE puede devolver:

- `success: true`
- `pending: true`
- `ticket` presente
- `hash` presente
- XML firmado presente

Cuando `pending=true`, la guia debe quedar:

```text
estado = pendiente_smartpse
```

No debe marcarse como `emitida` sin CDR o aceptacion final.

## Consulta de Ticket

La documentacion publica de Smart PSE muestra `GET /api/cpe/consultar/{nombre_archivo}` para resumenes `RC/RA/RR`.

Con la evidencia actual en demo, ese endpoint no cierra GRE:

- sin credenciales GRE, Smart PSE exige `client_id_sunat`, `client_secret_sunat`, `sol_user`, `sol_password`;
- con credenciales GRE en la consulta, Smart PSE puede responder `estado=404` / `Resource not found`;
- por eso Inkora no debe hacer polling automatico de GRE con `/consultar`.

## Evidencia en BD

Para una guia enviada a Smart PSE demo y pendiente, revisar:

- `guias_remision.estado = 'pendiente_smartpse'`
- `sunat_hash` lleno
- `sunat_ticket` lleno
- `sunat_xml_content` lleno
- `provider_response` lleno
- `sunat_cdr_url` vacio si no hay CDR

## Verificacion Offline

```powershell
cd C:\Users\HP\Desktop\inkora_smartpse\backend
python -m pytest test_smartpse_client.py test_smartpse_ubl_contracts.py test_smartpse_response_normalization.py test_smartpse_facturacion_service.py test_smartpse_superadmin.py test_smartpse_gre_backend.py test_guias.py test_guias_router.py test_emission_queue.py test_facturacion_guards.py test_tenant_access_hardening.py -q
python -m pytest test_alembic_baseline.py -q
python -m compileall -q services routers schemas models crud
```

## Pendientes Separados

- Agregar UI superadmin para cargar y rotar credenciales GRE.
- Mostrar estado `pendiente_smartpse` en la pantalla de guias.
- Definir flujo operativo para actualizar CDR cuando Smart PSE entregue cierre GRE verificable.
- Validar comportamiento GRE en produccion antes de marcar guias como aceptadas automaticamente.
