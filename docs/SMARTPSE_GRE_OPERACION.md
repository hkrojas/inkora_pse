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

La revisión esperada para esta entrega es `0022_gre_sales_documents`. Además de
las columnas GRE incorporadas previamente, deben existir los campos de origen
01/03, evidencia de aceptación, observaciones y acuerdo de transporte.

Columnas base esperadas:

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

La documentacion vigente de Smart PSE indica que una GRE queda pendiente al
enviarse y debe conciliarse mediante:

```http
GET /api/cpe/consultar/{nombre_archivo}
```

Para GRE 09 y 31 se deben reenviar los cuatro campos OAuth/SOL:

- `client_id_sunat`
- `client_secret_sunat`
- `sol_user`
- `sol_password`

Inkora los envia en el cuerpo JSON de la consulta para no exponer secretos en
la URL. Este detalle de transporte debe confirmarse con una ejecucion demo: la
documentacion publica exige los campos "en el request", pero no publica un
ejemplo completo de la consulta GRE.

Cuando las cuatro credenciales se envían, Inkora añade también `environment`
con el ambiente congelado de la guía (`demo` o `produccion`). El worker vuelve a
validar que ese ambiente coincida con la empresa antes de llamar al proveedor.

En `procesar-demo` los cuatro campos son opcionales segun Smart PSE. Inkora los
omite solo si el tenant esta configurado expresamente en `demo`; en produccion
siguen siendo obligatorios. Un ticket, HTTP 200 o XML firmado no equivalen a
aceptacion: solo el CDR definitivo permite marcar la guia como aceptada.

### Preflight histórico Papeleria Grafica - 15/09/2026

La comprobacion de solo lectura contra la base configurada encontro:

- tenant presente, pero `smartpse_environment = produccion`;
- credenciales CPE presentes;
- las cuatro credenciales GRE ausentes;
- `SMARTPSE_API_TOKEN` de gestion ausente en el runtime local;
- base remota en Alembic `0018_access_requests`, sin las tablas de despacho de
  `0021_sale_dispatch_guides`.

Resultado: **no se realizo ninguna emision ni consulta externa**. Para probar
Papeleria Grafica sin riesgo se requiere una empresa Smart PSE configurada en
`demo`, credenciales CPE demo almacenadas y una base aislada migrada hasta
`0021`. No debe cambiarse a demo la empresa productiva existente como atajo.

Este resultado es una evidencia histórica y no describe necesariamente el
estado actual del despliegue. El preflight queda disponible como comando
repetible y de solo lectura:

```powershell
cd C:\Users\HP\Desktop\inkora_smartpse\backend
python preflight_smartpse_gre_demo.py --tenant-id 5
```

El comando devuelve codigo `0` unicamente cuando tenant, runtime, host,
credenciales CPE y esquema permiten una homologacion demo. Devuelve codigo `2`
ante cualquier bloqueo. Nunca llama al proveedor, no modifica la base y no
imprime secretos ni el RUC completo.

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

- Confirmar en demo que Smart PSE acepta las cuatro credenciales GRE en cuerpo
  JSON durante `GET /consultar/{nombre_archivo}`.
- Confirmar con Smart PSE la inconsistencia de su documentación pública sobre
  si las cuatro credenciales son opcionales o exigibles en `procesar-demo`.
- Obtener evidencia de homologación demo. Una falla conocida del ambiente demo
  se documenta como limitación del proveedor, no como aceptación.
- Validar comportamiento GRE en producción únicamente con autorización nueva y
  un traslado real; nunca mediante un comprobante ficticio.
