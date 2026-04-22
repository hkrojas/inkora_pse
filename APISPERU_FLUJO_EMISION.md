# Flujo de Emision ApisPeru

Fuente principal: `swagge.json`

Este documento resume el flujo operativo de ApisPeru segun el swagger local del proyecto. El objetivo es dejar claro:

- como se autentica el usuario
- como entra la empresa al flujo
- que endpoint se usa para cada tipo de documento
- que devuelve la API en cada caso
- que endpoints son de emision, cuales son de render y cuales son de consulta de estado

## 1. Flujo base

### 1.1 Login de usuario

Endpoint:

- `POST /auth/login`

Request esperado:

```json
{
  "username": "correo_o_usuario",
  "password": "clave"
}
```

Respuesta exitosa:

```json
{
  "token": "jwt_temporal_usuario"
}
```

Notas:

- El tag `user` indica que este token dura 24 horas.
- Este token sirve para administrar empresas y configuracion del usuario en ApisPeru.
- No debe asumirse que este es el token final de emision por empresa.

### 1.2 Empresas

Endpoints:

- `GET /companies`
- `POST /companies`
- `GET /companies/{companyId}`
- `PUT /companies/{companyId}`
- `DELETE /companies/{companyId}`

Notas relevantes del swagger:

- Antes de emitir, la empresa debe estar configurada correctamente.
- El swagger indica que cada empresa creada genera su propio token sin fecha de caducidad.
- El spec no deja claramente tipado en que respuesta exacta aparece ese token de empresa.

### 1.3 Bearer token para emision

El swagger define `bearerAuth` global.

Lectura operativa:

- primero se obtiene el token de usuario
- luego se configura o selecciona la empresa
- despues se emite usando el token de empresa

## 2. Configuracion de empresa

El schema `MyCompany` del swagger exige, como minimo, estos datos para el flujo completo por API:

- `ruc`
- `razon_social`
- `direccion`
- `certificado`
- `logo`
- `sol_user`
- `sol_pass`
- `plan`
- `environment`

Campos adicionales mencionados:

- `client_id`
- `client_secret`

Uso practico:

- si la empresa ya fue configurada manualmente en el portal de ApisPeru, Inkora no necesita replicar todo ese alta
- Inkora solo necesita guardar el token de empresa correcto y el RUC al que pertenece

## 3. Familias de documentos

### 3.1 Documentos con respuesta inmediata

Estos endpoints devuelven una respuesta directa de SUNAT en el mismo `send`.

#### Factura o boleta

- `POST /invoice/send`
- `POST /invoice/xml`
- `POST /invoice/pdf`

#### Nota de credito o debito

- `POST /note/send`
- `POST /note/xml`
- `POST /note/pdf`

#### Retencion

- `POST /retention/send`
- `POST /retention/xml`
- `POST /retention/pdf`

#### Percepcion

- `POST /perception/send`
- `POST /perception/xml`
- `POST /perception/pdf`

### 3.2 Documentos asincronos con ticket

Estos endpoints devuelven ticket en `send` y luego requieren consultar `status`.

#### Resumen diario de boletas

- `POST /summary/send`
- `POST /summary/xml`
- `POST /summary/pdf`
- `GET /summary/status`

#### Comunicacion de bajas

- `POST /voided/send`
- `POST /voided/xml`
- `POST /voided/pdf`
- `GET /voided/status`

#### Guia de remision

- `POST /despatch/send`
- `POST /despatch/xml`
- `POST /despatch/pdf`
- `GET /despatch/status`

#### Resumen de reversiones

- `POST /reversion/send`
- `POST /reversion/xml`
- `POST /reversion/pdf`
- `GET /reversion/status`

## 4. Que devuelve la API

## 4.1 Respuesta `DocumentResponse`

Se usa en:

- factura
- boleta
- nota de credito
- nota de debito
- retencion
- percepcion

Shape:

```json
{
  "xml": "contenido_o_referencia_xml",
  "hash": "resumen_firma_digital",
  "sunatResponse": {
    "success": true,
    "error": {
      "code": "string",
      "message": "string"
    },
    "cdrZip": "base64",
    "cdrResponse": {
      "accepted": true,
      "id": "string",
      "code": "string",
      "description": "string",
      "notes": ["string"]
    }
  }
}
```

Interpretacion:

- `xml`: XML firmado devuelto por la API
- `hash`: hash o resumen de la firma digital
- `sunatResponse.success`: si el envio fue aceptado
- `sunatResponse.error`: error de negocio o integracion si existe
- `sunatResponse.cdrZip`: CDR en base64
- `sunatResponse.cdrResponse`: respuesta interpretada de SUNAT

## 4.2 Respuesta `SummaryResponse`

Se usa en:

- resumen diario
- bajas
- guia de remision
- resumen de reversiones

Shape:

```json
{
  "xml": "contenido_o_referencia_xml",
  "hash": "resumen_firma_digital",
  "sunatResponse": {
    "success": true,
    "error": {
      "code": "string",
      "message": "string"
    },
    "ticket": "ticket_sunat"
  }
}
```

Interpretacion:

- `xml`: XML generado y firmado
- `hash`: hash de firma
- `sunatResponse.ticket`: ticket para consultar el estado despues

## 4.3 Respuesta `StatusResult`

Se usa en:

- `GET /summary/status`
- `GET /voided/status`
- `GET /despatch/status`
- `GET /reversion/status`

Shape:

```json
{
  "cdrZip": "base64",
  "cdrResponse": {
    "accepted": true,
    "id": "string",
    "code": "string",
    "description": "string",
    "notes": ["string"]
  },
  "success": true,
  "error": {
    "code": "string",
    "message": "string"
  },
  "code": "string"
}
```

Interpretacion:

- `success`: resultado de la consulta del ticket
- `cdrResponse`: respuesta final de SUNAT
- `cdrZip`: CDR si aplica
- `error`: error si la consulta falla
- `code`: codigo adicional del proveedor

## 4.4 Respuesta de validacion

Cuando el swagger documenta `400`, normalmente devuelve un arreglo de `ValidationResponse`:

```json
[
  {
    "message": "campo requerido",
    "field": "company.ruc"
  }
]
```

Interpretacion:

- es un error de validacion del payload
- no es necesariamente un error de autenticacion
- puede indicar estructura incompleta, campos invalidos o inconsistencia de datos

## 5. Flujo operativo por documento

## 5.1 Factura o boleta

Secuencia:

1. Preparar payload `Invoice`
2. Enviar a `POST /invoice/send`
3. Guardar:
   - `xml`
   - `hash`
   - `sunatResponse.success`
   - `sunatResponse.error`
   - `sunatResponse.cdrZip`
   - `sunatResponse.cdrResponse`
4. Si se necesita render separado:
   - `POST /invoice/xml`
   - `POST /invoice/pdf`

Resultado:

- respuesta final inmediata
- no requiere ticket ni consulta posterior de estado

## 5.2 Nota de credito o debito

Secuencia:

1. Preparar payload `Note`
2. Enviar a `POST /note/send`
3. Guardar lo mismo que en `DocumentResponse`
4. Si se requiere:
   - `POST /note/xml`
   - `POST /note/pdf`

Resultado:

- respuesta final inmediata

## 5.3 Resumen diario de boletas

Secuencia:

1. Preparar payload `Summary`
2. Enviar a `POST /summary/send`
3. Guardar:
   - `xml`
   - `hash`
   - `sunatResponse.ticket`
4. Consultar despues con `GET /summary/status?ticket=...`
5. Guardar:
   - `success`
   - `cdrZip`
   - `cdrResponse`
   - `error`

Resultado:

- el `send` no cierra el proceso
- el cierre real llega cuando se consulta el ticket

## 5.4 Comunicacion de bajas

Secuencia:

1. Preparar payload `Voided`
2. Enviar a `POST /voided/send`
3. Guardar ticket y metadata
4. Consultar `GET /voided/status?ticket=...`
5. Guardar respuesta final

Resultado:

- flujo asincrono con ticket

## 5.5 Guia de remision

Secuencia:

1. Preparar payload `Despatch`
2. Enviar a `POST /despatch/send`
3. Guardar ticket y metadata
4. Consultar `GET /despatch/status?ticket=...`
5. Guardar respuesta final
6. Si se necesita render:
   - `POST /despatch/xml`
   - `POST /despatch/pdf`

Resultado:

- flujo asincrono con ticket

Nota:

- el swagger menciona que para la nueva GRE puede requerirse `client_id` y `client_secret` configurados en la empresa

## 5.6 Retencion

Secuencia:

1. Preparar payload `Retention`
2. Enviar a `POST /retention/send`
3. Guardar `DocumentResponse`
4. Si se necesita render:
   - `POST /retention/xml`
   - `POST /retention/pdf`

Resultado:

- respuesta final inmediata

## 5.7 Percepcion

Secuencia:

1. Preparar payload `Perception`
2. Enviar a `POST /perception/send`
3. Guardar `DocumentResponse`
4. Si se necesita render:
   - `POST /perception/xml`
   - `POST /perception/pdf`

Resultado:

- respuesta final inmediata

## 5.8 Resumen de reversiones

Secuencia:

1. Preparar payload `Reversion`
2. Enviar a `POST /reversion/send`
3. Guardar ticket y metadata
4. Consultar `GET /reversion/status?ticket=...`
5. Guardar respuesta final

Resultado:

- flujo asincrono con ticket

## 6. Endpoints que no son emision

### 6.1 XML

Los endpoints `.../xml` generan o devuelven XML, pero no deben confundirse con emision.

### 6.2 PDF

Los endpoints `.../pdf` generan o devuelven PDF, pero no deben confundirse con emision.

### 6.3 QR

Endpoint:

- `POST /sale/qr`

Este endpoint no emite documentos. Solo genera la imagen QR de un comprobante ya definido con estos datos:

- `ruc`
- `tipo`
- `serie`
- `numero`
- `emision`
- `igv`
- `total`
- `clienteTipo`
- `clienteNumero`

## 7. Lo que Inkora deberia persistir

Para documentos con `DocumentResponse`:

- token de empresa usado
- endpoint usado
- payload enviado
- `xml`
- `hash`
- `sunatResponse.success`
- `sunatResponse.error.code`
- `sunatResponse.error.message`
- `sunatResponse.cdrZip`
- `sunatResponse.cdrResponse.accepted`
- `sunatResponse.cdrResponse.code`
- `sunatResponse.cdrResponse.description`
- `sunatResponse.cdrResponse.notes`

Para documentos con `SummaryResponse`:

- token de empresa usado
- endpoint usado
- payload enviado
- `xml`
- `hash`
- `sunatResponse.success`
- `sunatResponse.error.code`
- `sunatResponse.error.message`
- `sunatResponse.ticket`

Para `StatusResult`:

- ticket consultado
- fecha de consulta
- `success`
- `error.code`
- `error.message`
- `cdrZip`
- `cdrResponse.accepted`
- `cdrResponse.code`
- `cdrResponse.description`
- `cdrResponse.notes`

## 8. Conclusiones practicas para Inkora

1. No todos los documentos cierran en el `send`.
2. Factura, boleta, nota, retencion y percepcion tienen respuesta directa.
3. Resumen, baja, guia y reversion necesitan ticket y consulta posterior.
4. XML y PDF son endpoints auxiliares, no deben confundirse con el estado fiscal real.
5. El swagger no documenta un endpoint dedicado para validar el token de empresa.
6. El swagger tampoco deja claro en que respuesta exacta aparece el token de empresa al crearla, aunque si afirma que existe y no expira.

## 9. Mapa rapido

| Familia | Send | Respuesta send | Status posterior | Tipo final |
| --- | --- | --- | --- | --- |
| Factura/Boleta | `/invoice/send` | `DocumentResponse` | No | Inmediato |
| Nota credito/debito | `/note/send` | `DocumentResponse` | No | Inmediato |
| Resumen diario | `/summary/send` | `SummaryResponse` | `/summary/status` | Con ticket |
| Bajas | `/voided/send` | `SummaryResponse` | `/voided/status` | Con ticket |
| Guia remision | `/despatch/send` | `SummaryResponse` | `/despatch/status` | Con ticket |
| Retencion | `/retention/send` | `DocumentResponse` | No | Inmediato |
| Percepcion | `/perception/send` | `DocumentResponse` | No | Inmediato |
| Reversion | `/reversion/send` | `SummaryResponse` | `/reversion/status` | Con ticket |

## 10. Prueba real ejecutada desde este proyecto

Esta seccion documenta exactamente la prueba real que se hizo desde el proyecto local para emitir una factura en ApisPeru.

### 10.1 Aclaracion importante sobre el paso 1

En esta prueba no se hizo `POST /auth/login` contra ApisPeru.

Motivo:

- el backend actual no implementa login de usuario de ApisPeru
- la base de datos ya tenia guardado un token de empresa valido
- por eso la emision se hizo directamente con `Authorization: Bearer <token_empresa>`

En otras palabras:

- no se inicio sesion con usuario y contraseña de ApisPeru
- se uso el token de la unica empresa emisora que ya existia en la base

### 10.2 Empresa emisora usada

La base solo tenia una empresa con token ApisPeru disponible para emitir:

- emisor: `20606751509`
- razon social: `PAPELERIA GRAFICA Y PUBLICITARIA SAC.`

Ese token se leyo desde la tabla `tenants` y se uso para todas las llamadas de la prueba.

### 10.3 Como se usaron los RUC enviados en el mensaje

Los RUC enviados en el mensaje no se interpretan como empresas emisoras del sistema.

Se interpretan como posibles clientes/receptores para facturar desde la unica empresa emisora disponible.

RUC recibidos:

- `20191308868`
- `20341848955`
- `20499709944`

Para la prueba efectiva se uso como cliente:

- cliente: `20191308868`
- razon social resuelta por consulta documental: `ARCOR DE PERU S A`

### 10.4 Pasos exactos que se siguieron

1. Se cargaron las variables del archivo `backend/.env` para tener acceso a:
   - `DATABASE_URL`
   - `API_URL`
   - `DNIRUC_API_URL`
   - `DNIRUC_TOKEN`

2. Se consulto la base de datos del proyecto para obtener:
   - la unica empresa con `apisperu_token`
   - su `business_ruc`
   - su `business_name`
   - su direccion fiscal

3. Se valido el token de la empresa emisora con una llamada no destructiva a:
   - `POST /invoice/send`
   - payload vacio
   - bearer token de la empresa

4. Se consultaron por API documental los datos del emisor y del cliente usando:
   - `GET https://dniruc.apisperu.com/api/v1/ruc/{ruc}?token=...`

5. Se armo manualmente un payload de factura alineado al swagger, con estos campos principales:
   - `ublVersion`
   - `tipoOperacion`
   - `tipoDoc`
   - `serie`
   - `correlativo`
   - `fechaEmision`
   - `formaPago`
   - `tipoMoneda`
   - `client`
   - `company`
   - `mtoOperGravadas`
   - `mtoIGV`
   - `valorVenta`
   - `totalImpuestos`
   - `subTotal`
   - `mtoImpVenta`
   - `details`
   - `legends`

6. Se envio la factura a:
   - `POST /invoice/send`

7. Como respuesta, ApisPeru devolvio:
   - `status_code = 200`
   - `hash`
   - `xml`
   - `sunatResponse.success = true`
   - `sunatResponse.cdrResponse.code = "0"`
   - `sunatResponse.cdrResponse.description = "La Factura numero F001-75920954, ha sido aceptada"`

8. Luego se descargo el XML por endpoint auxiliar:
   - `POST /invoice/xml`

9. Luego se descargo el PDF por endpoint auxiliar:
   - `POST /invoice/pdf`

   Nota operativa:

   - con payload minimo el endpoint PDF devolvio error `500`
   - con el payload completo de la factura el endpoint PDF si respondio correctamente con `application/pdf`

10. Luego se genero el QR con:
    - `POST /sale/qr`

    Nota operativa:

    - ApisPeru devolvio el QR como `image/svg+xml`
    - por eso el archivo final utilizable se guardo como `.svg`

### 10.5 Datos de la factura emitida

- emisor: `20606751509`
- cliente: `20191308868`
- serie: `F001`
- correlativo: `75920954`
- tipo de comprobante: `01`
- moneda: `PEN`
- base gravada: `100.00`
- igv: `18.00`
- total: `118.00`
- descripcion del item: `SERVICIO DE PRUEBA PRINTFLOW`

### 10.6 Archivos generados

Todos los archivos quedaron en:

- `pruebas/apisperu_emision_20260411_102228`

Archivos principales:

- `F001-75920954.pdf`
- `F001-75920954.xml`
- `F001-75920954-cdr.zip`
- `F001-75920954-qr.svg`

Archivos auxiliares de trazabilidad:

- `invoice_request.json`
- `invoice_send_response.json`
- `invoice_xml_response_meta.json`
- `invoice_pdf_response_meta.json`
- `invoice_pdf_response_meta_full_payload.json`
- `qr_request.json`
- `qr_response_meta.json`
- `issuer_lookup.json`
- `client_lookup.json`

### 10.7 Conclusiones de esta prueba

1. La emision real si funciono usando el token de empresa ya guardado en la base.
2. Para esta prueba no hizo falta login de usuario/contraseña de ApisPeru.
3. Los RUC enviados por mensaje funcionaron como clientes para facturar desde la empresa emisora disponible.
4. El endpoint de PDF de ApisPeru fue sensible al payload: con payload minimo fallo y con payload completo funciono.
5. El QR no vino como PNG sino como SVG.

## 11. Bateria real de los demas documentos

Esta seccion documenta la bateria real que se ejecuto despues para probar los demas documentos disponibles del swagger usando la misma empresa emisora y el mismo entorno beta de ApisPeru.

### 11.1 Objetivo

El objetivo fue emitir y guardar evidencia local de:

- boleta
- nota de credito de boleta
- factura
- nota de debito de factura
- factura base para comunicacion de baja
- comunicacion de baja
- resumen diario
- guia de remision
- retencion
- percepcion
- resumen de reversiones

### 11.2 Datos base usados

- entorno del emisor en ApisPeru: `beta`
- emisor: `20606751509`
- razon social: `PAPELERIA GRAFICA Y PUBLICITARIA SAC.`
- DNI usado para boleta: `72758912`
- RUC usados como clientes o referencias:
  - `20191308868`
  - `20341848955`
  - `20499709944`

### 11.3 Primer intento de bateria

Primero se ejecuto una bateria completa guardada en:

- `pruebas/apisperu_bateria_20260411_103925`

En ese primer intento se uso una numeracion basada en timestamp, por ejemplo:

- `B001-1775921979`
- `F001-1775921981`
- `RA-20260411-1775921984`

Resultado:

- casi todos los `send` devolvieron `status_code = 200`
- pero ApisPeru respondio con `sunatResponse.success = false`
- el error repetido fue `0151`
- mensaje dominante: nombre de ZIP invalido

Ejemplos reales del rechazo:

- `20606751509-03-B001-1775921979.zip`
- `20606751509-01-F001-1775921981.zip`
- `20606751509-RA-20260411-1775921984.zip`

La conclusion tecnica de ese primer intento fue:

- los correlativos largos de 10 digitos no estaban siendo aceptados por la nomenclatura del proveedor
- antes de seguir habia que rehacer la bateria con correlativos cortos y series consistentes

### 11.4 Segundo intento corregido

Luego se rehizo la bateria completa con correlativos cortos y se guardo en:

- `pruebas/apisperu_bateria_retry_20260411_105451`

Correlativos usados en la bateria corregida:

- boleta: `B001-75921001`
- nota de credito boleta: `BB01-75921002`
- factura: `F001-75921003`
- nota de debito factura: `FF01-75921004`
- factura base para baja: `F001-75921005`
- baja: `RA-20260411-21001`
- resumen diario: `RC-20260411-21002`
- guia de remision: `T001-75921006`
- retencion: `R001-75921007`
- percepcion: `P001-75921008`
- reversion: `RR-20260411-21003`

### 11.5 Pasos exactos que se siguieron

1. Se leyo `backend/.env` para obtener:
   - `DATABASE_URL`
   - `DNIRUC_API_URL`
   - `DNIRUC_TOKEN`

2. Se consulto la tabla `tenants` para recuperar:
   - el `apisperu_token` del emisor
   - el `business_ruc`
   - la `apisperu_url`

3. Se consulto la API documental para obtener:
   - datos del emisor por RUC
   - datos del DNI `72758912`
   - datos de los RUC `20191308868`, `20341848955` y `20499709944`

4. Se armaron manualmente los payloads segun el swagger para cada documento.

5. Para documentos de respuesta inmediata se ejecuto este flujo:
   - `POST /invoice/xml` o `POST /note/xml` o equivalente
   - `POST /invoice/pdf` o `POST /note/pdf` o equivalente
   - `POST /invoice/send` o `POST /note/send` o equivalente

6. Para documentos asincronos se ejecuto este flujo:
   - `POST /summary/send` o `POST /voided/send` o `POST /reversion/send`
   - si hubo ticket, luego `GET /summary/status` o `GET /voided/status` o `GET /reversion/status`

7. Para boleta, factura y notas se genero QR con:
   - `POST /sale/qr`

8. En cada caso se guardo en disco:
   - payload enviado
   - respuesta cruda del proveedor
   - XML
   - PDF
   - QR cuando aplicaba
   - CDR zip cuando SUNAT acepto el documento

### 11.6 Resultado real del segundo intento

Documentos aceptados por ApisPeru/SUNAT en beta:

- boleta `B001-75921001`
- nota de credito `BB01-75921002`
- factura `F001-75921003`
- nota de debito `FF01-75921004`
- factura `F001-75921005`
- comunicacion de baja `RA-20260411-21001`
- retencion `R001-75921007`
- percepcion `P001-75921008`
- reversion `RR-20260411-21003`

Respuestas aceptadas mas importantes:

- boleta: `La Boleta numero B001-75921001, ha sido aceptada`
- nota de credito: `La Nota de Credito numero BB01-75921002, ha sido aceptada`
- factura: `La Factura numero F001-75921003, ha sido aceptada`
- nota de debito: `La Nota de Debito numero FF01-75921004, ha sido aceptada`
- baja: `La Comunicacion de baja RA-20260411-21001, ha sido aceptada`
- retencion: `El Comprobante numero R001-75921007 ha sido aceptado`
- percepcion: `El Comprobante numero P001-75921008 ha sido aceptado`
- reversion: `El Comprobante numero RR-20260411-21003 ha sido aceptado`

Documentos que no quedaron aceptados:

- resumen diario
- guia de remision

### 11.7 Resumen diario: bloqueo real encontrado

El resumen diario se probo dos veces:

- intento 1: `07_resumen_boleta`
- intento 2: `12_resumen_boleta_fix`

En ambos casos el proveedor devolvio:

- `status_code = 200`
- `sunatResponse.success = false`
- `code = 2992`

Mensaje:

- `El XML no contiene el tag de la tasa del tributo de la linea`

Hallazgo importante:

- incluso usando un payload pegado al ejemplo del swagger, el XML que genera ApisPeru para `summary` sale sin la tasa del tributo en el subtotal de impuestos
- por eso el rechazo parece venir del XML generado por el proveedor y no de la numeracion ni del orden del flujo local

### 11.8 Guia de remision: bloqueo real encontrado

La guia se probo tres veces:

- intento base: `08_guia_remision`
- variante privada: `13_guia_privada_fix`
- variante publica con `nroMtc`: `14_guia_publica_fix`

Resultado comun:

- `POST /despatch/xml` responde bien y genera XML
- `POST /despatch/pdf` responde bien y genera PDF
- `POST /despatch/send` devuelve `500`
- cuerpo: `Error al comunicarse con el servidor interno`

Hallazgo importante:

- el problema no fue solo la modalidad de traslado
- tampoco cambio al probar transporte privado y transporte publico
- por lo tanto, en esta bateria la guia quedo bloqueada por error interno del proveedor al momento del `send`

### 11.9 Archivos generados

Carpeta principal de la bateria corregida:

- `pruebas/apisperu_bateria_retry_20260411_105451`

Subcarpetas principales:

- `01_boleta_dni`
- `02_nota_credito_boleta`
- `03_factura`
- `04_nota_debito_factura`
- `05_factura_base_baja`
- `06_baja_factura`
- `07_resumen_boleta`
- `08_guia_remision`
- `09_retencion`
- `10_percepcion`
- `11_reversion`
- `12_resumen_boleta_fix`
- `13_guia_privada_fix`
- `14_guia_publica_fix`
- `lookups`

Archivos de resumen:

- `manifest_resumen_real.json`
- `manifest_complementario.json`

### 11.10 Conclusiones operativas de esta bateria

1. El token de empresa almacenado en la base si permite emitir varios tipos documentarios reales en beta.
2. El error `0151` del primer intento se resolvio usando correlativos cortos y nomenclatura compatible.
3. Los documentos que si quedaron efectivamente aceptados fueron:
   - boleta
   - nota de credito
   - factura
   - nota de debito
   - baja
   - retencion
   - percepcion
   - reversion
4. El resumen diario sigue bloqueado por un XML que ApisPeru genera sin la tasa del tributo, aun usando el ejemplo del swagger.
5. La guia de remision sigue bloqueada por `500` interno del proveedor en el `send`, aunque `xml` y `pdf` si se generan.

## 12. Verificacion integrada desde el backend

Fecha de verificacion:

- `2026-04-11`

Objetivo:

- comprobar que el backend de Inkora siga el flujo operativo ya validado manualmente
- ejecutar la prueba entrando por las rutas HTTP del backend, no solo por scripts directos al proveedor

Correccion aplicada antes de la prueba:

- `backend/tenant_access.py`: la consulta documental ahora prioriza `DNIRUC_TOKEN` antes que el token fiscal del tenant
- motivo: `dniruc.apisperu.com` y `facturacion.apisperu.com` no deben compartir por defecto el mismo token operativo

Evidencia local:

- `pruebas/backend_route_verification_20260411_141415/report.json`
- `pruebas/backend_route_verification_20260411_141415/factura_16.xml`
- `pruebas/backend_route_verification_20260411_141415/factura_16.pdf`
- `pruebas/backend_route_verification_20260411_141415/boleta_19.xml`
- `pruebas/backend_route_verification_20260411_141415/boleta_19.pdf`
- `pruebas/backend_route_verification_20260411_141415/nota_credito_17.xml`

### 12.1 Flujo ejecutado por rutas del backend

Secuencia real ejecutada:

1. `POST /superadmin/tenants/{tenant_id}/users`
2. `POST /token`
3. `GET /users/me/`
4. `POST /superadmin/validate/apisperu-token`
5. `GET /consultar-documento/20191308868`
6. `GET /consultar-documento/72758912`
7. `POST /clientes/`
8. `POST /cotizaciones/`
9. `POST /cotizaciones/{id}/facturar`
10. `POST /facturacion/xml`
11. `POST /facturacion/pdf`
12. `POST /notas/emitir`
13. `POST /guias-remision/`
14. `GET /guias-remision/{id}/etiqueta`
15. `POST /guias-remision/{id}/emitir`
16. `POST /bajas/anular`

Tenant usado en la prueba:

- `tenant_id = 7`
- emisor: `20606751509`
- razon social: `PAPELERIA GRAFICA Y PUBLICITARIA SAC.`

### 12.2 Resultado por paso

Pasos correctos desde backend:

- login del usuario temporal del tenant
- validacion del token fiscal del tenant
- consulta documental RUC
- consulta documental DNI
- alta de cliente con RUC
- alta de cliente con DNI
- creacion de cotizacion comercial
- emision de factura
- descarga de XML de factura
- descarga de PDF de factura
- emision de nota de credito
- descarga de XML de nota de credito
- creacion de guia de remision
- generacion de etiqueta de guia
- emision de boleta
- descarga de XML de boleta
- descarga de PDF de boleta
- emision de una segunda factura para probar baja

Pasos que fallaron en esta prueba integrada:

- descarga de PDF de nota de credito
- emision de guia de remision
- consulta final de comunicacion de baja

### 12.3 Detalle de fallos observados

#### PDF de nota de credito

Respuesta backend:

- `400`
- detalle: `ApisPeru devolvio 500 en /note/pdf: Error al comunicarse con el servidor interno`

Lectura:

- la nota si fue aceptada por SUNAT
- el fallo quedo solo en el endpoint auxiliar de PDF del proveedor
- no parece ser rechazo fiscal del documento

#### Guia de remision

Respuesta backend:

- `400`
- detalle: `ApisPeru devolvio 500 en /despatch/send: Error al comunicarse con el servidor interno`

Lectura:

- el backend si arma la guia y la etiqueta localmente
- el bloqueo aparece en el `send` del proveedor
- coincide con la bateria manual previa, donde `despatch/send` tambien quedo bloqueado por error interno

#### Comunicacion de baja

Respuesta backend:

- `400`
- detalle: `ApisPeru devolvio 404 en /voided/status: Empresa no encontrada.`

Lectura:

- la emision de la factura base si fue aceptada
- el backend llego a la fase asincrona de ticket para baja
- el bloqueo ocurre al consultar el estado final del ticket en el proveedor
- este punto debe revisarse otra vez contra el payload de baja y el comportamiento real del sandbox

### 12.4 Conclusiones de esta verificacion integrada

1. El backend ya sigue correctamente el flujo base para autenticacion local, consulta documental, alta de clientes, cotizacion y emision de factura/boleta.
2. La separacion entre token documental y token fiscal era un fallo real del backend y ya fue corregido.
3. Factura y boleta quedaron emitidas y descargadas correctamente por rutas del backend.
4. La nota de credito tambien quedo emitida correctamente; solo fallo el PDF auxiliar del proveedor.
5. La guia de remision sigue bloqueada por error interno del proveedor en `despatch/send`, igual que en la prueba manual.
6. La comunicacion de baja todavia no queda cerrada desde backend porque el proveedor responde `404` al consultar `voided/status`.

## 13. Revalidacion de documentos restantes

Despues de la verificacion integrada del backend, se hizo una revalidacion adicional para los tipos documentarios que faltaban:

- nota de debito
- retencion
- percepcion
- reversion
- resumen diario de boletas
- guia de remision

Esta revalidacion se ejecuto directamente contra ApisPeru reutilizando el token fiscal real del tenant y payloads base previamente aceptados, ajustando numeracion y fechas para evitar duplicados.

Evidencia generada:

- carpeta: `pruebas/apisperu_revalidacion_20260411_144908`
- manifiesto principal: `pruebas/apisperu_revalidacion_20260411_144908/manifest.json`

### 13.1 Resultado de pruebas automatizadas del backend

Se agrego una matriz automatizada para validar que el backend enruta correctamente cada familia documentaria y que distingue flujos sincronos y asincronos:

- archivo: `backend/test_apisperu_documentos_matrix.py`
- comando ejecutado: `python -m pytest test_apisperu_documentos_matrix.py -q`
- resultado: `11 passed`

Tambien se corrio la bateria combinada de pruebas criticas relacionadas:

- `python -m pytest test_facturacion_guards.py test_facturacion_fiscal.py test_guias.py test_apisperu_token_validation.py test_tenant_access_hardening.py test_apisperu_documentos_matrix.py -q`
- resultado: `87 passed`

Estas pruebas confirman la logica interna del backend, pero no sustituyen la validacion real contra el proveedor.

### 13.2 Resultado real contra ApisPeru

#### Documentos aceptados correctamente

- factura base de referencia: aceptada
- nota de debito: aceptada
- retencion: aceptada
- percepcion: aceptada
- boleta base de referencia: aceptada

#### Documentos que no cerraron satisfactoriamente

- reversion
- resumen diario de boletas
- guia de remision

### 13.3 Detalle de los documentos que fallaron

#### Reversion

Comportamiento observado:

- `send` respondio `200`
- se recibio ticket asincrono
- al consultar el estado final, ApisPeru respondio `404`
- mensaje: `Empresa no encontrada.`

Lectura:

- el backend y el flujo de ticket si avanzan
- el cierre del proceso falla del lado del proveedor o por una condicion no documentada del sandbox para este tipo

#### Resumen diario de boletas

Comportamiento observado:

- `send` respondio `200`
- el proveedor devolvio error funcional `2992`
- mensaje principal: falta la tasa del tributo de linea para codigo `1000`

Lectura:

- este no parece ser un error de transporte
- apunta a que el payload usado para resumen diario todavia no incluye una estructura tributaria exacta a la que espera ApisPeru para ese XML
- aqui si hay trabajo pendiente de payload o mapeo

#### Guia de remision

Comportamiento observado:

- el endpoint `despatch/send` respondio `500`
- no devolvio una respuesta funcional util para cerrar el flujo

Lectura:

- coincide con las verificaciones previas
- la guia sigue sin quedar operativa extremo a extremo en sandbox
- el bloqueo actual sigue estando en el proveedor

### 13.4 Conclusiones actuales

Estado real hasta este punto:

- factura: funciona
- boleta: funciona
- nota de credito: funciona, con incidencia puntual en PDF del proveedor
- nota de debito: funciona
- retencion: funciona
- percepcion: funciona
- comunicacion de baja: no cierra satisfactoriamente
- reversion: no cierra satisfactoriamente
- resumen diario: no funciona correctamente todavia
- guia de remision: no funciona correctamente todavia

Por lo tanto, no es correcto afirmar que todos los documentos disponibles ya devuelven un proceso satisfactorio. El backend ya cubre y prueba el flujo interno para todos, pero la validacion real contra ApisPeru todavia deja incidencias abiertas en baja, reversion, resumen diario y guia.

## 14. Correccion inicial de incidencias asincronas

Despues del analisis de los flujos que no pasaban, se identificaron dos fallos reales en backend para documentos asincronos:

- el polling de `status` se hacia solo con `ticket`
- el polling se hacia en un solo intento, sin reintento cuando SUNAT aun no registraba el ticket

### 14.1 Archivos corregidos

- `backend/services/facturacion_service.py`
- `backend/test_apisperu_documentos_matrix.py`

### 14.2 Correcciones aplicadas

1. En `summary/status`, `voided/status`, `reversion/status` y `despatch/status` ahora se envia tambien el parametro `ruc`.
2. El polling asincrono ahora reintenta cuando el proveedor devuelve respuestas temporales como ticket no encontrado o en proceso.
3. El payload interno de guia privada fue alineado mejor con el esquema del swagger:
   - `vehiculo`
   - `choferes`
   - ya no se reutiliza la estructura de `transportista` para traslado privado
4. El payload de resumen ahora sale mas explicito con montos tributarios en cero para campos opcionales del esquema.

### 14.3 Verificacion despues de la correccion

Pruebas automáticas:

- `python -m pytest test_apisperu_documentos_matrix.py -q` → `12 passed`
- `python -m pytest test_guias.py test_facturacion_guards.py -q` → `47 passed`

Validacion real contra ApisPeru despues del fix asincrono:

- comunicacion de baja: ahora responde correctamente al consultar `voided/status` con `ruc`
- reversion: ahora responde correctamente al consultar `reversion/status` con `ruc`

Conclusión actualizada:

- baja: corregido en backend
- reversion: corregido en backend
- resumen diario: sigue fallando con `2992` por estructura/XML esperado por el proveedor
- guia de remision: sigue fallando con `500` en `despatch/send`

## 15. Acotacion final de los dos pendientes

Despues de corregir el polling asincrono, se hicieron pruebas dirigidas adicionales sobre los dos casos que aun no cierran:

- `summary/send`
- `despatch/send`

### 15.1 Guia de remision

Hallazgo real:

- `despatch/send` sigue respondiendo `500`
- `despatch/xml` responde `200` y genera XML valido
- `despatch/pdf` responde `200` y genera PDF valido

Lectura tecnica:

- el backend si construye un payload aceptable para el proveedor
- la falla ya no apunta a estructura base del JSON
- el bloqueo esta concentrado en la etapa de envio SUNAT del proveedor o en la configuracion interna que ApisPeru usa para esa empresa al enviar la GRE

Por eso se mejoro el backend para reportar un diagnostico mas util cuando ocurra este caso:

- si `despatch/send` falla pero `despatch/xml` funciona, el mensaje ahora indica que el payload si genera XML y que el fallo parece estar en el envio del proveedor

### 15.2 Resumen diario

Se probaron variantes reales con:

- `estado = 1`
- `estado = 3`
- `clienteNro = 72758912`
- `clienteNro = 00000000`

Resultado:

- todas las variantes devolvieron el mismo error `2992`
- ApisPeru genero el XML del resumen sin el nodo `<cbc:Percent>` dentro del tributo `1000`

Lectura tecnica:

- el problema ya no depende de si el resumen es de alta o baja
- tampoco depende del DNI real vs `00000000`
- el proveedor esta renderizando el XML sin la tasa tributaria esperada para IGV

Por eso se mejoro el backend para reportar ese diagnostico de forma explicita:

- cuando `summary/send` devuelve `2992` y el XML sale sin `<cbc:Percent>`, el backend ahora lo informa directamente en el error

### 15.3 Estado real despues de esta ronda

Documentos ya corregidos y verificados:

- factura
- boleta
- nota de credito
- nota de debito
- retencion
- percepcion
- comunicacion de baja
- reversion

Documentos aun abiertos:

- resumen diario
- guia de remision
