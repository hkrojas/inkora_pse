# REVISION TECNICA DEL PROYECTO INKORA

Fecha de revision: 2026-05-01  
Proyecto: Inkora  
Ruta local: `c:\Users\HP\Desktop\mi_proyecto_cotizaciones`

Este documento resume el estado actual del proyecto, su arquitectura, APIs, modulos, funciones principales, integraciones y puntos de cuidado. Esta escrito como referencia tecnica para continuar el desarrollo sin perder contexto.

---

## 1. Resumen general

Inkora es una aplicacion SaaS vertical para imprentas en Peru. El objetivo actual no es construir un ERP completo, sino estabilizar un producto de lanzamiento con un solo plan comercial.

El flujo principal del producto es:

- Gestionar clientes.
- Gestionar productos y servicios reutilizables.
- Crear cotizaciones.
- Convertir cotizaciones en facturas o boletas electronicas.
- Emitir notas de credito/debito.
- Emitir guias de remision.
- Generar etiquetas de despacho.
- Controlar cobranza basica.
- Exportar reportes mensuales.
- Administrar tenants, usuarios, credenciales fiscales y limites desde superadmin.

El sistema esta dividido en:

- Backend FastAPI en Python.
- Frontend React con Vite.
- Base de datos SQLAlchemy, con PostgreSQL en entorno real y SQLite en pruebas.
- Integracion fiscal via APISPeru y soporte directo parcial para SUNAT.
- Storage de archivos con Supabase Storage.

---

## 2. Stack tecnico

### Backend

- Python 3.11.
- FastAPI.
- Uvicorn.
- SQLAlchemy ORM.
- Pydantic v2.
- pydantic-settings.
- JWT con `python-jose`.
- Hash de passwords con `passlib` + `bcrypt`.
- Rate limiting con `slowapi`.
- PDF con `reportlab` y `svglib`.
- Excel con `openpyxl`.
- XML fiscal con `xmltodict`, `signxml` y servicios propios.
- QR con `qrcode[pil]`.
- Supabase Storage para archivos.
- Requests HTTP hacia APIs externas.

### Frontend

- React 18.
- Vite 6.
- React Router DOM 6.
- Tailwind CSS 3.
- CSS global personalizado.
- Lucide React para iconos.
- JavaScript/JSX, no TypeScript.
- ESLint 9.

### Infraestructura local

- Backend local esperado en `http://localhost:8000`.
- Frontend Vite en `http://localhost:5173`.
- Proxy Vite configurado para `/api -> http://localhost:8000`, aunque el frontend actualmente usa `VITE_API_URL` o fallback directo a `http://localhost:8000`.

---

## 3. Estructura principal del proyecto

```text
backend/
  main.py
  config.py
  database.py
  security.py
  api_dependencies.py
  access_control.py
  tenant_access.py
  routers/
  services/
  crud/
  schemas/
  models/
  requirements.txt
  Dockerfile

frontend/
  package.json
  vite.config.js
  src/
    App.jsx
    main.jsx
    pages/
    services/
    components/
    context/
    layouts/
    lib/utils/
    styles/
  static/
```

---

## 4. Backend: composicion de la app

Archivo principal: `backend/main.py`

La app se crea con `create_app()`.

Componentes registrados:

- `FastAPI(title="Sistema Cotizaciones SUNAT")`.
- `GZipMiddleware` con `minimum_size=1000`.
- `CORSMiddleware`.
- Rate limiter global `slowapi`.
- Middleware de logging/request tracking.
- Startup ping de base de datos.
- Registro de routers funcionales.
- Registro de router `legacy_frozen` solo para dominios congelados/no launch scope.

Routers incluidos:

- `auth.router`
- `tenants.router`
- `clientes.router`
- `productos.router`
- `cotizaciones.router`
- `pagos.router`
- `reportes.router`
- `facturacion.router`
- `guias.router`
- `superadmin.router`
- `dashboard.router`
- `sunat.router`
- `legacy_frozen.router`

---

## 5. Configuracion y seguridad

Archivo principal: `backend/config.py`

Configuracion importante:

- `DATABASE_URL`: obligatoria.
- `SECRET_KEY`: obligatoria.
- `ENVIRONMENT`: controla modo test/development/staging/production.
- `FISCAL_ENV`: solo debe ser `beta` o `production`.
- `INIT_DB_ON_STARTUP`: prohibido en production.
- `APISPERU_URL`: URL base para APISPeru.
- `API_TOKEN` / `DNIRUC_TOKEN`: tokens globales legacy/fallback.
- `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_STORAGE_BUCKET`: storage.
- `MAX_LOGO_UPLOAD_BYTES`: limite de logo, actualmente 2 MB.

Seguridad:

- JWT incluye email, tenant, rol, superadmin, flags de cambio de password, `iat` y `exp`.
- Password minimo 10 caracteres, al menos letra y numero, no passwords comunes.
- Passwords se invalidan si `password_changed_at` es posterior al `iat` del token.
- Roles principales: `superadmin`, `admin`, `operador`, `vendedor`.
- Superadmin puede operar transversalmente.
- Tenant suspendido bloquea accesos sensibles.
- Registro publico protegido por `X-Internal-Provisioning-Token` cuando aplica.

Tenant isolation:

- Existe ContextVar `current_tenant_id`.
- SQLAlchemy aplica filtro automatico por tenant.
- Funciones criticas deben validar ownership explicitamente.

---

## 6. Modelos de base de datos

### Tenant

Modelo: `backend/models/tenants.py`

Campos principales:

- `id`
- `created_at`
- `is_active`
- `business_name`
- `business_ruc`
- `business_address`
- `business_phone`
- `logo_filename`
- `primary_color`
- `pdf_note_1`
- `pdf_note_1_color`
- `pdf_note_2`
- `bank_accounts`
- `apisperu_token`
- `apisperu_url`
- `apisperu_token_status`
- `apisperu_token_checked_at`
- `sunat_gre_client_id`
- `sunat_gre_client_secret`
- `plan_type`
- `plan_start_date`
- `plan_end_date`
- `invoice_limit`
- `invoices_used`
- `sunat_usuario_sol`
- `sunat_clave_sol`
- `sunat_cert_password`
- `sunat_cert_url`

Relaciones:

- usuarios
- clientes
- productos
- cotizaciones
- guias de remision
- pagos
- subscription
- subscription_payments
- emission_jobs
- resumenes diarios
- reversiones fiscales
- retenciones fiscales
- percepciones fiscales

### User

Campos principales:

- `id`
- `email`
- `hashed_password`
- `nombre_completo`
- `rol`
- `is_superadmin`
- `is_active`
- `last_login_at`
- `must_change_password`
- `password_changed_at`
- `tenant_id`

Tambien conserva campos legacy de empresa en usuario, pero el criterio actual es usar datos del tenant como fuente principal.

### Cliente

Modelo: `backend/models/clientes.py`

Campos principales:

- `tipo_documento`
- `numero_documento`
- `razon_social`
- `nombre_comercial`
- `direccion`
- `ubigeo`
- `email`
- `telefono`
- `whatsapp`
- `contacto`
- `condicion_pago`
- `direccion_entrega`
- `observaciones`
- `tenant_id`

### Producto

Modelo: `backend/models/productos.py`

Campos principales:

- `codigo_interno`
- `nombre`
- `descripcion`
- `precio_unitario`
- `valor_unitario`
- `moneda`
- `unidad_medida`
- `tipo_afectacion_igv`
- `tenant_id`

Validaciones agregadas/revisadas:

- Codigo SKU interno con longitud razonable.
- Unidad de medida SUNAT.
- Tipo de afectacion IGV SUNAT.
- Moneda.
- Precio con IGV incluido o valor base segun modo de registro.
- Producto/servicio reutilizable para cotizaciones, facturas, boletas y guias.

### Cotizacion

Modelo: `backend/models/cotizaciones.py`

Campos principales:

- `serie`
- `correlativo`
- `fecha_emision`
- `fecha_vencimiento`
- `moneda`
- `estado`
- `uuid_publico`
- `document_kind`
- `internal_order_number`
- `source_quote_id`
- `tenant_id`
- `cliente_id`
- `usuario_id`
- `total_gravada`
- `total_exonerada`
- `total_inafecta`
- `total_igv`
- `total_venta`
- `tipo_comprobante`
- `sunat_xml_url`
- `sunat_pdf_url`
- `sunat_cdr_url`
- `sunat_error`
- `sunat_xml_content`
- `sunat_hash`
- `sunat_qr_payload`
- `sunat_qr_svg`
- `tipo_de_cambio`
- `sujeta_detraccion`
- `porcentaje_detraccion`
- `monto_detraccion`
- `cuenta_banco_nacion`
- `anticipos_deducidos`
- `total_anticipos`
- `nota_referencia_id`
- `nota_motivo_codigo`
- `nota_motivo_descripcion`
- `observaciones`
- `condicion_pago`
- `cuotas_pago`
- `monto_pagado`
- `saldo_pendiente`

### CotizacionItem

Campos principales:

- `cotizacion_id`
- `producto_id`
- `codigo_producto`
- `descripcion`
- `cantidad`
- `precio_unitario`
- `valor_unitario`
- `total_base_igv`
- `total_igv`
- `total_item`
- `unidad_medida`
- `tipo_afectacion_igv`

### Pago

Modelo: `backend/models/pagos.py`

Campos principales:

- `tenant_id`
- `cotizacion_id`
- `source_quote_id`
- `fiscal_document_id`
- `internal_order_number`
- `monto_pagado`
- `metodo_pago`
- `fecha_pago`
- `referencia_operacion`
- `tipo`

### GuiaRemision

Modelo: `backend/models/guias.py`

Campos principales:

- `serie`
- `correlativo`
- `fecha_emision`
- `fecha_traslado`
- `estado`
- `tenant_id`
- `cotizacion_id`
- `cliente_id`
- `source_quote_id`
- `fiscal_document_id`
- `internal_order_number`
- `usuario_id`
- `motivo_traslado`
- `descripcion_motivo`
- `peso_bruto_total`
- `unidad_medida_peso`
- `numero_bultos`
- `modalidad_traslado`
- datos de transportista
- datos de conductor
- datos de vehiculo
- punto de partida
- punto de llegada
- URLs fiscales SUNAT/APISPeru

### Documentos fiscales adicionales

Modelos agregados o estabilizados:

- `ResumenDiario`
- `ReversionFiscal`
- `RetencionFiscal`
- `PercepcionFiscal`
- `DocumentEmissionJob`

Estos modelos guardan:

- tenant
- usuario
- serie/correlativo cuando aplica
- fecha de emision o generacion
- estado
- ticket
- hash
- payload enviado
- respuesta del proveedor
- error SUNAT/APISPeru
- status code del proveedor

### Modelos congelados

Existen modelos de dominios no prioritarios:

- proveedores
- insumos
- recetas BOM
- ordenes de produccion
- alertas de inventario

Estos estan en scope congelado y no deben ampliarse salvo que se pida explicitamente.

---

## 7. Servicios backend principales

### `services/calculations.py`

Funciones clave:

- `to_decimal`
- `redondear`
- `redondear_extendido`
- `calcular_item`
- `sumarizar_cotizacion`
- `get_line_totals_v3`
- `calculate_cotizacion_totals_v3`

Responsabilidad:

- Calcular bases imponibles.
- Calcular IGV.
- Calcular totales por item.
- Mantener redondeo consistente.

### `services/facturacion_service.py`

Funciones clave:

- `numero_a_letras`
- `obtener_tipo_documento_codigo`
- `_extract_token_company_ruc`
- `_get_api_base_url`
- `_build_company_payload`
- `_build_client_payload`
- `_construir_items_payload`
- `_resolve_tipo_operacion`
- `_build_payment_terms`
- `_aplicar_detraccion`
- `_aplicar_anticipos`
- `_provider_request_headers`
- `_raise_for_provider_http_error`

Responsabilidad:

- Construir payloads compatibles con APISPeru.
- Resolver empresa emisora.
- Resolver cliente.
- Construir items.
- Preparar cuotas cuando condicion de pago es credito.
- Preparar detracciones y anticipos.
- Manejar errores del proveedor fiscal.
- Adjuntar links, QR y artefactos de respuesta.

### `services/fiscal_provider_service.py`

Funciones clave:

- `has_any_direct_sunat_credentials`
- `has_complete_direct_sunat_credentials`
- `has_apisperu_credentials`
- `can_use_direct_sunat`
- `direct_sunat_block_reason`

Responsabilidad:

- Determinar si el tenant puede emitir por APISPeru.
- Determinar si tiene credenciales SUNAT directas.
- Evitar usar canales incompletos.

### `services/document_flow_service.py`

Funciones clave:

- `build_internal_order_number`
- `get_document_kind_for_note`
- `is_quote_document`
- `is_fiscal_document`
- `is_note_document`
- `is_fiscal_family_document`
- `resolve_source_quote_id`
- `calculate_payment_status`

Responsabilidad:

- Mantener trazabilidad cotizacion -> documento fiscal -> guia -> cobranza.
- Resolver orden interna.
- Resolver estado de pago.

### `services/emission_queue_service.py`

Funciones clave:

- `enqueue_fiscal_document_job`
- `enqueue_note_job`
- `enqueue_void_document_job`
- `enqueue_guide_job`
- `process_emission_job`
- `process_next_available_job`
- `run_worker_loop`

Responsabilidad:

- Manejar emision asincrona.
- Registrar jobs.
- Reintentar errores retryables.
- Evitar duplicados con idempotency key.

### `services/pdf_generator.py`

Funciones clave:

- `monto_a_letras`
- `obtener_etiqueta_tipo_doc`
- `_resolve_quote_company_data`
- `_resolve_company_data`
- `_build_qr_content`
- `_load_logo`
- `_build_logo_block`
- `_build_observation_paragraphs`
- `_build_footer_contact_text`
- `_build_quote_pdf_buffer`

Responsabilidad:

- Generar PDFs comerciales.
- Usar logo, datos de empresa, telefono, cuentas bancarias y billeteras.
- Generar QR cuando aplica.
- Usar observaciones configurables.

### `services/storage_service.py`

Funciones clave:

- `build_storage_path`
- `build_private_storage_reference`
- `parse_private_storage_reference`
- `create_signed_storage_url`
- `resolve_storage_download_url`
- `upload_to_storage`

Responsabilidad:

- Subir archivos a Supabase Storage.
- Generar referencias privadas.
- Generar URLs publicas para logos.
- Resolver URLs firmadas.

### `services/import_service.py`

Funciones clave:

- `parse_clientes`
- `parse_productos`

Responsabilidad:

- Leer CSV/Excel.
- Normalizar filas.
- Validar campos.
- Preparar importacion masiva.

### `services/bank_account_validation.py`

Funcion principal:

- `validate_and_normalize_bank_accounts`

Responsabilidad:

- Validar cuentas bancarias y billeteras.
- Normalizar banco, tipo de cuenta, moneda, cuenta, CCI, titular, telefono.
- Evitar datos de cobro invalidos en PDFs.

### `services/phone_validation.py`

Funciones clave:

- `digits_only`
- `normalize_peru_mobile`
- `validate_optional_peru_mobile`
- `normalize_and_validate_optional_peru_mobile`

Responsabilidad:

- Validar celulares peruanos.
- Usado en clientes y tenant.

### `services/subscription_service.py`

Funciones clave:

- `activate_tenant`
- `suspend_tenant`
- `extend_access`
- `set_founder_pricing`
- `register_saas_payment`
- `get_subscription_status`
- `update_subscription_general`

Responsabilidad:

- Control SaaS interno.
- Activacion/suspension de tenants.
- Precio founder.
- Pagos SaaS.
- Estados de suscripcion.

### `services/sunat_exchange_rate_service.py`

Funcion principal:

- `get_exchange_rate`

Responsabilidad:

- Obtener tipo de cambio SUNAT.
- Cachear respuesta.
- Responder al frontend para mostrar compra/venta.

---

## 8. APIs backend por modulo

### Auth

| Metodo | Ruta | Funcion | Uso |
| --- | --- | --- | --- |
| POST | `/token` | `login_for_access_token` | Login OAuth2 password y emision JWT |
| POST | `/register` | `register_user` | Registro protegido por token interno |
| GET | `/users/me/` | `read_users_me` | Usuario autenticado |
| POST | `/users/me/change-password` | `change_password` | Cambio de password |
| PUT | `/users/profile` | `update_user_profile` | Actualizar perfil |

### Tenant y configuracion

| Metodo | Ruta | Funcion | Uso |
| --- | --- | --- | --- |
| GET | `/tenant/` | `get_my_tenant` | Datos de empresa actual |
| PUT | `/tenant/` | `update_my_tenant` | Razon social, domicilio fiscal, telefono, color, notas PDF, cuentas |
| GET | `/tenant/subscription-status` | `get_my_subscription_status` | Estado SaaS publico |
| POST | `/tenants/` | `create_tenant` | Crear tenant por provisioning |
| GET | `/onboarding/estado` | `get_onboarding_estado` | Checklist de onboarding |
| GET | `/users/` | `list_tenant_users` | Usuarios del tenant |
| POST | `/users/` | `create_tenant_user` | Crear usuario local |
| POST | `/users/{user_id}/reset-password` | `admin_reset_user_password` | Reset de password |
| POST | `/users/upload-logo` | `upload_logo` | Subir logo de empresa |

Notas recientes de Configuracion:

- Se agrego edicion de razon social y domicilio fiscal desde frontend.
- El RUC sigue bloqueado para tenant porque cambia identidad fiscal.
- Logo acepta PNG, JPG, JPEG y WEBP.
- Limite de logo: 2 MB.
- Logo se sube a Supabase Storage y se guarda en `tenant.logo_filename`.

### Clientes

| Metodo | Ruta | Funcion | Uso |
| --- | --- | --- | --- |
| GET | `/consultar-documento/{numero}` | `consultar_documento` | Buscar DNI/RUC |
| GET | `/consultar-ruc/{numero}` | `consultar_ruc_legacy` | Alias legacy |
| GET | `/clientes/` | `read_clientes` | Listar clientes |
| GET | `/clientes/count` | `count_clientes` | Conteo |
| GET | `/clientes/plantilla-importacion` | `descargar_plantilla_clientes` | Descargar plantilla |
| POST | `/clientes/importar` | `importar_clientes` | Importacion masiva |
| GET | `/clientes/{cliente_id}` | `read_cliente` | Obtener cliente |
| POST | `/clientes/` | `create_cliente` | Crear cliente |
| PUT | `/clientes/{cliente_id}` | `update_cliente` | Actualizar completo |
| PATCH | `/clientes/{cliente_id}` | `patch_cliente` | Actualizar parcial |
| DELETE | `/clientes/{cliente_id}` | `delete_cliente` | Eliminar |

### Productos

| Metodo | Ruta | Funcion | Uso |
| --- | --- | --- | --- |
| GET | `/productos/` | `read_productos` | Listar productos/servicios |
| GET | `/productos/count` | `count_productos` | Conteo |
| GET | `/productos/plantilla-importacion` | `descargar_plantilla_productos` | Plantilla |
| POST | `/productos/importar` | `importar_productos` | Importacion masiva |
| GET | `/productos/codigo-sugerido` | `codigo_sugerido` | SKU sugerido |
| GET | `/productos/{producto_id}` | `read_producto` | Obtener producto |
| POST | `/productos/` | `create_producto` | Crear producto |
| PUT | `/productos/{producto_id}` | `update_producto` | Actualizar |
| DELETE | `/productos/{producto_id}` | `delete_producto` | Eliminar |

Notas recientes:

- Se revisaron campos contra uso fiscal.
- El formulario distingue producto/servicio.
- Maneja unidad de medida SUNAT.
- Maneja tipo de afectacion IGV.
- Maneja moneda.
- Maneja precio con IGV incluido y valor base.
- Genera codigo SKU.

### Cotizaciones

| Metodo | Ruta | Funcion | Uso |
| --- | --- | --- | --- |
| GET | `/cotizaciones/` | `read_cotizaciones` | Listado paginado |
| POST | `/cotizaciones/` | `create_cotizacion` | Crear cotizacion |
| POST | `/cotizaciones/{id}/duplicar` | `duplicar_cotizacion` | Duplicar |
| GET | `/cotizaciones/{id}` | `read_cotizacion` | Detalle |
| DELETE | `/cotizaciones/{id}` | `delete_cotizacion` | Eliminar |
| GET | `/public/cotizaciones/{uuid}/pdf` | `descargar_pdf_publico` | PDF publico compartido |
| GET | `/cotizaciones/{id}/pdf` | `descargar_pdf_interno` | PDF interno |
| GET | `/cotizaciones/{id}/compartir` | `compartir_cotizacion` | Link compartible |

Notas recientes:

- El limite visual estandar se bajo a 15 items por lista.
- Se corrigieron columnas vacias que desplazaban tablas.
- Se optimizo carga inicial para no pedir 100 cotizaciones.
- Se mantiene trazabilidad con `internal_order_number`.

### Pagos y cobranza

| Metodo | Ruta | Funcion | Uso |
| --- | --- | --- | --- |
| POST | `/cotizaciones/{id}/pagos` | `registrar_adelanto_pago` | Registrar pago |
| GET | `/cotizaciones/{id}/pagos` | `listar_pagos` | Historial de pagos |
| GET | `/cobranza/resumen` | `cobranza_resumen` | KPIs de cobranza |
| GET | `/cobranza/vencidas` | `cobranza_vencidas` | Documentos vencidos/por vencer |

Notas recientes:

- Se reviso comunicacion backend/frontend.
- Se usa para documentos en seguimiento activo.
- Permite saldo pendiente, mora y filtros.

### Facturacion y documentos fiscales

| Metodo | Ruta | Funcion | Uso |
| --- | --- | --- | --- |
| POST | `/cotizaciones/{id}/facturar` | `emitir_comprobante` | Emitir factura/boleta desde cotizacion |
| GET | `/facturas-emitidas/` | `list_facturas_emitidas` | Listar facturas/boletas/documentos |
| POST | `/notas/emitir` | `emitir_nota` | Nota credito/debito |
| GET | `/notas/` | `list_notas` | Listado de notas |
| POST | `/bajas/anular` | `anular_documento` | Comunicacion de baja |
| POST | `/facturacion/{tipo_archivo}` | `recuperar_archivo_api` | Recuperar XML/PDF/CDR |

Notas recientes:

- Nuevo comprobante soporta contado/credito.
- Si se selecciona credito, se agregan cuotas.
- Las cuotas se preparan para APISPeru en terminos de pago.
- Facturas y boletas se listan con limite estandar de 15.
- Tablas corregidas para evitar primera columna vacia.

### Guias de remision

| Metodo | Ruta | Funcion | Uso |
| --- | --- | --- | --- |
| POST | `/guias-remision/` | `crear_guia_remision` | Crear guia |
| GET | `/guias-remision/` | `listar_guias_remision` | Listar guias |
| GET | `/guias-remision/{id}` | `obtener_guia_remision` | Detalle |
| GET | `/guias-remision/{id}/etiqueta` | `obtener_etiqueta_guia` | Etiqueta imprimible |
| POST | `/guias-remision/{id}/emitir` | `emitir_guia_remision_endpoint` | Emitir guia |

Notas recientes:

- Se reviso conectividad frontend/backend.
- Se aplica estandar de listas de 15.
- Se mantiene relacion con cliente, cotizacion, documento fiscal y orden interna.

### Retenciones

| Metodo | Ruta | Funcion | Uso |
| --- | --- | --- | --- |
| GET | `/retenciones/` | `list_retenciones` | Listar retenciones |
| POST | `/retenciones/emitir` | `emitir_retencion` | Emitir retencion APISPeru |
| POST | `/retenciones/emitir-legacy` | `emitir_retencion_legacy` | Ruta legacy oculta |

Notas recientes:

- Se agrego modelo `RetencionFiscal`.
- Se agrego schema y CRUD.
- Se agrego payload APISPeru `/retention/send`.
- Se agrego frontend `RetencionesPage`.
- Lista limitada a 15.

### Percepciones

| Metodo | Ruta | Funcion | Uso |
| --- | --- | --- | --- |
| GET | `/percepciones/` | `list_percepciones` | Listar percepciones |
| POST | `/percepciones/emitir` | `emitir_percepcion` | Emitir percepcion APISPeru |
| POST | `/percepciones/emitir-legacy` | `emitir_percepcion_legacy` | Ruta legacy oculta |

Notas recientes:

- Se agrego modelo `PercepcionFiscal`.
- Se agrego schema y CRUD.
- Se agrego payload APISPeru `/perception/send`.
- Se agrego frontend `PercepcionesPage`.
- Lista limitada a 15.

### Resumen diario

| Metodo | Ruta | Funcion | Uso |
| --- | --- | --- | --- |
| GET | `/resumen-diario/` | `list_resumenes_diarios` | Listar resumenes |
| POST | `/resumen-diario/enviar` | `enviar_resumen_diario` | Enviar resumen |

Notas:

- Orientado al consolidado de boletas del dia.
- Flujo asincrono con ticket SUNAT/APISPeru.
- Lista limitada a 15 cuando hay registros.

### Reversiones

| Metodo | Ruta | Funcion | Uso |
| --- | --- | --- | --- |
| GET | `/reversiones/` | `list_reversiones` | Listar reversiones |
| POST | `/reversiones/enviar` | `enviar_reversion` | Enviar reversion |
| POST | `/reversiones/enviar-legacy` | `enviar_reversion_legacy` | Ruta legacy oculta |

Notas:

- Usado para correccion/reversion de comunicaciones.
- Lista limitada a 15.

### Emission jobs

| Metodo | Ruta | Funcion | Uso |
| --- | --- | --- | --- |
| GET | `/emission-jobs/{job_id}` | `get_emission_job_endpoint` | Consultar job |
| GET | `/emission-jobs` | `list_emission_jobs_endpoint` | Listar jobs |

Uso:

- Seguimiento asincrono de emisiones.
- Estado de tickets y reintentos.

### Dashboard

| Metodo | Ruta | Funcion | Uso |
| --- | --- | --- | --- |
| GET | `/analytics/dashboard` | `read_dashboard_stats` | KPIs generales |

El dashboard frontend tambien consulta:

- `/cotizaciones/?limit=4`
- `/cobranza/resumen`
- `/cobranza/vencidas?limit=4`

### Reportes

| Metodo | Ruta | Funcion | Uso |
| --- | --- | --- | --- |
| GET | `/reporte/mensual` | `reporte_mensual_excel` | Excel mensual |

### SUNAT auxiliar

| Metodo | Ruta | Funcion | Uso |
| --- | --- | --- | --- |
| GET | `/sunat/exchange-rate` | `read_sunat_exchange_rate` | Tipo de cambio SUNAT |

### Superadmin

| Metodo | Ruta | Uso |
| --- | --- | --- |
| POST | `/superadmin/validate/apisperu-token` | Validar token APISPeru |
| POST | `/superadmin/tenants` | Crear tenant |
| GET | `/superadmin/tenants` | Listar tenants |
| PATCH | `/superadmin/tenants/{tenant_id}` | Actualizar tenant |
| DELETE | `/superadmin/tenants/{tenant_id}` | Eliminar tenant si no tiene datos relacionados |
| POST | `/superadmin/tenants/{tenant_id}/users` | Crear usuario en tenant |
| GET | `/superadmin/usuarios` | Listar usuarios |
| PATCH | `/users/{user_id}` | Actualizar usuario legacy/global |
| DELETE | `/users/{user_id}` | Eliminar usuario |
| GET | `/superadmin/audit-logs` | Auditoria |
| GET | `/superadmin/tenants/{tenant_id}/subscription` | Suscripcion |
| POST | `/superadmin/tenants/{tenant_id}/activate` | Activar tenant |
| POST | `/superadmin/tenants/{tenant_id}/suspend` | Suspender tenant |
| POST | `/superadmin/tenants/{tenant_id}/extend-access` | Extender acceso |
| PUT | `/superadmin/tenants/{tenant_id}/founder-pricing` | Precio founder |
| PATCH | `/superadmin/tenants/{tenant_id}/subscription` | Actualizar suscripcion |
| POST | `/superadmin/tenants/{tenant_id}/payments` | Registrar pago SaaS |
| GET | `/superadmin/tenants/{tenant_id}/payments` | Listar pagos SaaS |
| GET | `/superadmin/tenants-detail` | Tenants con detalle |
| GET | `/superadmin/beta/resumen` | Resumen beta |
| GET | `/superadmin/tenants/{tenant_id}/actividad` | Actividad tenant |
| PATCH | `/superadmin/tenants/{tenant_id}/notas` | Notas internas |
| GET | `/superadmin/tenants/{tenant_id}/users-detail` | Usuarios detalle |
| PATCH | `/superadmin/users/{user_id}/toggle-active` | Activar/desactivar usuario |
| POST | `/superadmin/users/{user_id}/reset-password` | Reset password |
| GET | `/superadmin/tenants/{tenant_id}/emission-errors` | Errores de emision |
| POST | `/superadmin/tenants/{tenant_id}/check-token-health` | Health token tenant |
| POST | `/superadmin/check-all-tokens` | Health tokens global |
| GET | `/superadmin/tenants/{tenant_id}/limits` | Limites |
| PUT | `/superadmin/tenants/{tenant_id}/limits` | Upsert limites |
| DELETE | `/superadmin/limits/{limit_id}` | Eliminar limite |

### Legacy frozen

El router `legacy_frozen.py` contiene endpoints de proveedores, insumos, BOM, produccion, alertas e IA. Estan congelados para el lanzamiento actual.

---

## 9. Frontend: rutas principales

Archivo: `frontend/src/App.jsx`

| Ruta | Pagina | Uso |
| --- | --- | --- |
| `/login` | `Login` | Acceso |
| `/dashboard` | `Dashboard` | Inicio operativo |
| `/clientes` | `ClientesPage` | Clientes |
| `/productos` | `ProductosPage` | Catalogo |
| `/cotizaciones` | `CotizacionesPage` | Historial cotizaciones |
| `/cotizaciones/:id` | `CotizacionDetalle` | Detalle |
| `/cobranza` | `CobranzaPage` | Seguimiento de pagos |
| `/guias` | `GuiasPage` | Guias |
| `/guias/:id` | `GuiaDetalle` | Detalle guia |
| `/configuracion` | `ConfiguracionPage` | Perfil, fiscal, cuenta, seguridad, apariencia |
| `/cambiar-password` | redirect | Redirige a configuracion seguridad |
| `/diseno-pdf` | `PdfDesignerPage` | Diseno PDF |
| `/superadmin` | `SuperadminPage` | Panel interno |
| `/comprobantes/nuevo` | `ComprobanteNuevoPage` | Emision central |
| `/facturas` | `FacturasPage` | Comprobantes tipo 01 |
| `/boletas` | `BoletasPage` | Comprobantes tipo 03 |
| `/notas` | `NotasPage` | Notas credito/debito |
| `/retenciones` | `RetencionesPage` | Retenciones |
| `/percepciones` | `PercepcionesPage` | Percepciones |
| `/resumen-diario` | `ResumenDiarioPage` | Resumen diario |
| `/bajas` | `BajasPage` | Comunicacion de bajas |
| `/reversiones` | `ReversionesPage` | Reversiones |

---

## 10. Frontend: servicios API

Todas las llamadas pasan por `frontend/src/lib/utils/api.js`.

### `api.js`

Funciones:

- `api.get`
- `api.post`
- `api.put`
- `api.patch`
- `api.delete`
- `api.postForm`
- `api.blob`

Comportamiento:

- Usa `BASE_URL`.
- Agrega `Authorization: Bearer <token>` si existe token.
- JSON por defecto.
- Detecta `FormData` y no fuerza `Content-Type`.
- Timeout por defecto: 12 segundos.
- Si recibe 401 borra token y manda a `/login`.
- Si recibe 403 por usuario bloqueado o tenant suspendido tambien termina sesion.

### `clientes.js`

- `clientes.list(params)`
- `clientes.get(id)`
- `clientes.lookupDocument(numero)`
- `clientes.create(data)`
- `clientes.update(id, data)`
- `clientes.remove(id)`

### `productos.js`

- `productos.list(params)`
- `productos.get(id)`
- `productos.create(data)`
- `productos.update(id, data)`
- `productos.remove(id)`
- `productos.generateCode()`

### `cotizaciones.js`

- `cotizaciones.list(params = '?limit=15')`
- `cotizaciones.get(id)`
- `cotizaciones.create(data)`
- `cotizaciones.duplicar(id)`
- `cotizaciones.pdf(id)`
- `cotizaciones.share(id)`
- `cotizaciones.facturar(id, payload)`
- `cotizaciones.pagos(id)`
- `cotizaciones.addPago(id, data)`
- `cotizaciones.notas(payload)`
- `cotizaciones.anular(payload)`
- `cotizaciones.remove(id)`

### `guias.js`

- `guias.list(params = { limit: 15 })`
- `guias.get(id)`
- `guias.create(data)`

### `cobranza.js`

- `cobranza.resumen()`
- `cobranza.vencidas(params = '?scope=active&limit=50')`

Nota: debe alinearse con el nuevo estandar de 15 si se usa como lista visible general. Algunos bloques del dashboard usan limites menores.

### `dashboard.js`

- `dashboard.stats()`
- `dashboard.cobranzaResumen()`
- `dashboard.cobranzaVencidas(params = '?limit=4')`
- `dashboard.reporteMensual()`
- `dashboard.recentDocuments()`
- `dashboard.pendingInvoices()`

Incluye retry simple para varias consultas.

### `sunat.js`

- `sunat.exchangeRate()`

### `tenant.js`

- `tenant.get()`
- `tenant.update(data)`
- `tenant.uploadLogo(formData)`
- `tenant.onboarding()`
- `tenant.subscriptionStatus()`

### `superadmin.js`

Funciones agrupadas:

- tenants
- usuarios
- health de tokens
- errores de emision
- limites
- suscripciones
- pagos SaaS
- auditoria

---

## 11. Frontend: utilidades importantes

### `config.js`

Define:

```js
export const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

### `bankAccountValidation.js`

Valida:

- Banco.
- Tipo de cuenta.
- Moneda.
- Numero de cuenta.
- CCI.
- Billetera digital.
- Numero asociado.

### `paymentMethods.js`

Construye, normaliza y serializa:

- Cuentas bancarias.
- Billeteras digitales.

### `peruPhoneValidation.js`

Valida celular peruano:

- Solo digitos.
- 9 digitos.
- Debe iniciar en 9.

### `sunatCatalogs.js`

Contiene catalogos usados por formularios:

- Unidades de medida.
- Tipos de afectacion IGV.
- Catalogos fiscales auxiliares.

### `fiscalClientValidation.js`

Valida clientes segun documento:

- RUC para factura.
- DNI/RUC u otros permitidos para boleta segun reglas aplicadas.

### `documents.js`

Funciones utilitarias para documentos y estados.

### `format.js`

Formateo de:

- Monedas.
- Fechas.
- Numeros.
- Estados.

---

## 12. Modulos funcionales actuales

### Dashboard

Estado:

- Conectado a backend.
- Muestra KPIs generales.
- Consulta cobranza.
- Consulta documentos recientes.
- Usa retry en el servicio frontend.

Pendiente recomendado:

- Reducir dependencias cruzadas si el dashboard crece.
- Mantener consultas livianas.

### Clientes

Estado:

- CRUD conectado.
- Consulta DNI/RUC.
- Importacion por plantilla.
- Validaciones de documento.
- Enriquecimiento con contacto, email, whatsapp, condicion de pago y direccion de entrega.

### Productos

Estado:

- CRUD conectado.
- SKU sugerido.
- Importacion por plantilla.
- Validacion frontend/backend reforzada.
- Compatible con cotizaciones, facturas, boletas y guias.
- Incluye producto/servicio, unidad SUNAT, tipo afectacion, moneda y precio.

### Cotizaciones

Estado:

- CRUD conectado.
- PDF interno.
- PDF publico compartible.
- Duplicado.
- Conversion a comprobante.
- Pagos asociados.
- Lista optimizada a 15 items por defecto.
- Corregida columna vacia en tabla.

### Nuevo comprobante

Estado:

- Emision central.
- Documento tipo factura/boleta.
- Cliente obligatorio segun tipo.
- Lineas obligatorias.
- Forma de pago contado/credito.
- Si es credito se gestionan cuotas.
- Totales visibles en resumen lateral.
- Validaciones antes de emitir.

### Facturas

Estado:

- Conectada a `/facturas-emitidas/`.
- Tipo 01.
- Tarjetas de resumen.
- Filtros.
- Lista limitada a 15.
- Tabla corregida para evitar columna vacia.

### Boletas

Estado:

- Conectada a `/facturas-emitidas/` filtrando tipo 03.
- Lista limitada a 15.
- Tabla corregida para evitar columna vacia.
- Control de pendientes/aceptadas/observadas.

### Guias

Estado:

- Conectada a backend.
- Lista limitada a 15.
- Soporta detalle y etiqueta.
- Preparada para emision fiscal GRE.

### Notas credito/debito

Estado:

- Conectadas a `/notas/`.
- Emision por `/notas/emitir`.
- Tipos 07 y 08.
- Ajustes sobre documentos aceptados.

### Cobranza

Estado:

- Conectada a `/cobranza/resumen`.
- Conectada a `/cobranza/vencidas`.
- Muestra total por cobrar, vencidos, cobrado mes y seguimiento.
- Muestra documentos con mora.

### Resumen diario

Estado:

- Conectado a `/resumen-diario/`.
- Envio por `/resumen-diario/enviar`.
- Maneja tickets asincronos.
- Vista lista para cuando existan resumenes.

### Bajas

Estado:

- Comunicacion de baja por `/bajas/anular`.
- Vista lista documentos a anular.
- Lista estandar 15.

### Reversiones

Estado:

- Conectado a `/reversiones/`.
- Envio por `/reversiones/enviar`.
- Lista estandar 15.

### Retenciones

Estado:

- Modelo, schema, CRUD, endpoints y pagina agregados.
- Payload APISPeru `retention/send`.
- Lista estandar 15.
- Valida contrato con tests.

### Percepciones

Estado:

- Modelo, schema, CRUD, endpoints y pagina agregados.
- Payload APISPeru `perception/send`.
- Lista estandar 15.
- Valida contrato con tests.

### Configuracion

Estado:

- Conectada a `/tenant/`.
- Lee tenant actual.
- Actualiza datos permitidos por `PUT /tenant/`.
- Permite editar razon social y domicilio fiscal.
- Mantiene RUC bloqueado para tenant.
- Permite telefono.
- Permite cuentas bancarias y billeteras digitales.
- Permite subir logo por `/users/upload-logo`.
- Muestra estado de token APISPeru, credenciales SOL y certificado.
- Tiene tabs de empresa, fiscal, cuenta, seguridad y apariencia.
- Cambio de password integrado.
- Tema visual integrado.

Campos bloqueados por criterio fiscal:

- RUC del emisor.
- Token APISPeru.
- Credenciales SOL.
- Certificado.

Motivo:

- Cambiar RUC o credenciales cambia la identidad fiscal del emisor.
- Debe hacerlo superadmin con revalidacion de token/certificado.

### Superadmin

Estado:

- Administra tenants.
- Administra usuarios.
- Valida token APISPeru.
- Gestiona suscripciones.
- Gestiona pagos SaaS.
- Gestiona limits.
- Gestiona health de tokens.
- Gestiona errores de emision.

---

## 13. Integraciones externas

### APISPeru

Uso:

- Emision de facturas.
- Emision de boletas.
- Emision de notas.
- Comunicacion de baja.
- Guias de remision.
- Retenciones.
- Percepciones.
- Resumen diario.
- Reversiones.
- Consulta RUC/DNI segun token.

Datos importantes:

- El token idealmente debe estar en el tenant.
- El RUC del token debe coincidir con `tenant.business_ruc`.
- El frontend nunca debe exponer tokens.
- El backend guarda payload y respuesta del proveedor para auditoria.

### SUNAT

Uso:

- Tipo de cambio.
- Reglas fiscales de documentos.
- Credenciales SOL/certificado para flujos directos o futuros.
- Catalogos de unidades, afectacion IGV y documentos.

### Supabase Storage

Uso:

- Logos publicos.
- PDFs/XML/CDR privados o firmados.

Riesgo:

- Si Supabase no esta configurado, la subida de logo o archivos fiscales fallara.

---

## 14. Reglas de negocio importantes

### Lista estandar de documentos

Por rendimiento y usabilidad, cualquier lista visible de documentos debe cargar 15 items por defecto.

Aplica a:

- Cotizaciones.
- Facturas.
- Boletas.
- Guias.
- Notas.
- Resumen diario.
- Bajas.
- Reversiones.
- Retenciones.
- Percepciones.

### Cotizacion no es factura

Regla:

- Una cotizacion es documento comercial.
- Un comprobante fiscal es otro documento.
- Debe mantenerse trazabilidad, no mezclar significados.

Campos de trazabilidad:

- `document_kind`
- `source_quote_id`
- `internal_order_number`
- `fiscal_document_id` cuando aplica.

### Credito y cuotas

Si forma de pago es credito:

- Deben existir cuotas.
- Cada cuota debe tener monto y fecha.
- El total de cuotas debe cuadrar con el total del comprobante.
- El payload fiscal debe incluir condiciones de pago requeridas por APISPeru/SUNAT.

### Datos de empresa

Editable por tenant:

- Razon social.
- Domicilio fiscal.
- Telefono.
- Logo.
- Datos de cobro.
- Notas PDF.
- Color primario.

No editable por tenant:

- RUC.
- Token APISPeru.
- Credenciales SOL.
- Certificado.

### Productos

Reglas:

- Nombre obligatorio.
- Precio obligatorio.
- Unidad SUNAT.
- Tipo afectacion IGV.
- Codigo SKU opcional/generable, pero recomendado.
- Producto/servicio debe ser reutilizable en documentos.

### Cobranza

Reglas:

- Pago parcial reduce saldo.
- Pago total deja saldo en cero.
- Documento vencido entra a seguimiento.
- No mezclar cobranza del cliente final con pagos SaaS del tenant.

---

## 15. Estado de pruebas

Backend tiene suite pytest.

Pruebas relevantes existentes o tocadas:

- `test_auth.py`
- `test_tenant_access_hardening.py`
- `test_cotizaciones.py`
- `test_facturacion_fiscal.py`
- `test_facturacion_guards.py`
- `test_guias.py`
- `test_guias_router.py`
- `test_payments.py`
- `test_document_flow_transition.py`
- `test_emission_queue.py`
- `test_pdf_generator.py`
- `test_apisperu_documentos_matrix.py`
- `test_apisperu_payload_contracts.py`
- `test_facturacion_comprobante_builder.py`
- `test_productos_pricing.py`
- `test_phone_validation.py`

Comandos:

```bash
cd backend
python -m pytest -v
```

Frontend no tiene suite automatizada de UI.

Verificacion frontend:

```bash
cd frontend
npm run lint
npm run build
```

Estado reciente verificado:

- `npm run lint` OK.
- `npm run build` OK.
- Warning persistente: bundle JS mayor a 500 kB.

---

## 16. Comandos de ejecucion

Backend:

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm run dev
```

Build frontend:

```bash
cd frontend
npm run build
```

Lint frontend:

```bash
cd frontend
npm run lint
```

Tests backend:

```bash
cd backend
python -m pytest -v
```

---

## 17. Riesgos y pendientes tecnicos

### Bundle frontend grande

Vite advierte que el chunk JS supera 500 kB.

Recomendacion:

- Aplicar code splitting por rutas.
- Cargar paginas fiscales y superadmin con `React.lazy`.
- Separar componentes pesados.

### Frontend sin tests automatizados

Riesgo:

- Cambios visuales o formularios pueden romperse sin deteccion automatica.

Recomendacion:

- Agregar Vitest para utilidades.
- Agregar Playwright para flujos criticos.

### Legacy congelado todavia registrado

Riesgo:

- Endpoints no launch scope siguen disponibles.

Recomendacion:

- Mantenerlos aislados.
- No expandirlos.
- Considerar esconderlos por configuracion en produccion si no son necesarios.

### APISPeru real

Riesgo:

- No todos los flujos deben probarse contra APISPeru real porque pueden generar operaciones fiscales.

Recomendacion:

- Usar mocks/contract tests para payloads.
- Solo hacer pruebas reales en beta controlada.

### Migraciones

Hay multiples scripts `migrate_*.py`.

Riesgo:

- Sin herramienta formal tipo Alembic, el orden de migracion puede ser fragil.

Recomendacion:

- Normalizar migraciones antes de beta pagada.

### Datos legacy en User

El modelo `User` mantiene datos de empresa legacy.

Riesgo:

- Duplicidad con Tenant.

Recomendacion:

- Tenant debe ser fuente oficial.
- Evitar nuevos usos de campos legacy de empresa en User.

---

## 18. Prioridades recomendadas

Orden sugerido:

1. Consolidar migraciones.
2. Revisar que todas las listas documentales usen `limit=15`.
3. Agregar code splitting en frontend.
4. Agregar pruebas e2e para emision central.
5. Agregar pruebas e2e para configuracion fiscal y logo.
6. Revisar permisos por rol en cada endpoint fiscal.
7. Revisar tenant ownership explicito en endpoints sensibles.
8. Documentar variables `.env` obligatorias.
9. Agregar estado visual para errores de Supabase Storage.
10. Separar completamente dominios frozen del flujo launch.

---

## 19. Estado actual por cumplimiento de lanzamiento

| Area | Estado |
| --- | --- |
| Auth | Funcional y con pruebas |
| Tenant isolation | Implementado, seguir reforzando ownership explicito |
| Clientes | Funcional |
| Productos | Funcional y validado para uso fiscal basico |
| Cotizaciones | Funcional y optimizado a 15 |
| Facturas | Funcional como listado y emision desde cotizacion/comprobante |
| Boletas | Funcional como listado y emision desde cotizacion/comprobante |
| Guias | Funcional con emision/etiqueta |
| Notas | Funcional |
| Cobranza | Funcional basica |
| Resumen diario | Estructura funcional |
| Bajas | Estructura funcional |
| Reversiones | Estructura funcional |
| Retenciones | Agregado y conectado |
| Percepciones | Agregado y conectado |
| Configuracion | Perfil, fiscal, cuenta, seguridad, apariencia y logo |
| Superadmin | Amplio, requiere seguir endureciendo |
| Reporte mensual | Endpoint disponible |
| Frontend tests | Pendiente |
| Migraciones formales | Pendiente |

---

## 20. Conclusion

Inkora ya tiene un flujo launch-scope bastante completo:

- Login y tenant.
- Clientes.
- Productos.
- Cotizaciones.
- Emision de comprobantes.
- Guias.
- Cobranza.
- Configuracion.
- Superadmin.
- Documentos fiscales complementarios.

El foco tecnico siguiente no deberia ser agregar mas modulos, sino endurecer:

- exactitud fiscal,
- pruebas,
- migraciones,
- permisos,
- tenant isolation,
- rendimiento frontend,
- confiabilidad de APISPeru/SUNAT,
- trazabilidad documental.

La prioridad del proyecto debe seguir siendo: correcto, seguro por tenant, fiscalmente confiable y mantenible.
