# Preflight actualizado de la prueba de contingencia

Actualización posterior: el usuario autorizó ejecutar pruebas demo el mismo día.
Se creó FCTG-1 exclusivamente en empresa 688 demo y se verificó firma sin CDR,
primer envío y recuperación independiente. Ver
`docs/PRUEBA_DEMO_SIN_CDR_2026-10-03.md`. El listado vacío que sigue corresponde
al preflight anterior a esa prueba; no describe el estado posterior.

Fecha local: 3 de octubre de 2026 (Lima). Continuación autorizada por el usuario.

## Avance confirmado

El listado oficial `GET /api/v1/companies?environment=demo&per_page=100`
devolvió la empresa 688, RUC 20610027351, activa y en demo. Una consulta
PostgreSQL de solo lectura confirmó que corresponde al tenant 6 de Inkora,
con el mismo RUC, ID del proveedor y ambiente. Es distinta de la empresa
productiva 384 del tenant 5; no se cambió ninguna de sus configuraciones.

El listado del panel para empresa 688, demo y facturas devolvió cero documentos.
No existe un candidato sin CDR en esa empresa. La evidencia anterior de las
19 facturas demo con CDR corresponde a la empresa 384.

Evidencias saneadas:

- `pruebas/demo-companies-readonly-20261003.json`.
- `pruebas/demo-company688-readonly-20261003.json`.

Las verificaciones realizaron GET y autenticación del panel, sin POST fiscal,
escrituras en producción, descargas XML/CDR ni consumo de correlativos.

## Prueba externa pendiente

La empresa demo separada resuelve la identificación del emisor de prueba.
No demuestra por sí sola qué endpoint SUNAT usa el POST interno del panel.
Para validar el conector necesitamos:

1. Confirmación del proveedor o evidencia verificable de que
   `/panel/documentos/{id}/reintentar` usa beta para la empresa y documento demo.
2. Un documento de esa empresa con XML firmado, sin CDR ni ticket y con fallo
   temporal explícito de servicio; no un rechazo por datos o credenciales.
3. Ejecutar el mismo XML e identidad mediante un único intento reservado,
   conciliar el CDR y comprobar actualización de Inkora y cuota una sola vez.
4. Para permitir más intentos tras una respuesta perdida, contrato verificable
   de idempotencia o correlación de finalización. La etiqueta `error` sola no basta.

No se debe inventar un fallo del proveedor, borrar un CDR ni alterar un estado
remoto para fabricar el escenario. Crear una factura demo aceptada no verifica
el caso pendiente. La contingencia completa sigue sin desplegarse ni habilitarse.

## Consulta preparada para soporte (no enviada)

Asunto: Homologación de reintento de factura demo sin CDR — empresa 688

Estamos integrando la recuperación automática de facturas de Inkora. Tenemos
una empresa dedicada en demo, ID 688, actualmente sin facturas. Necesitamos
validar el mismo reintento que ofrece el panel cuando SUNAT no respondió:

- ¿`POST /panel/documentos/{id}/reintentar` selecciona SUNAT beta a partir del
  ambiente del documento o de la empresa? ¿Existe una ruta pública soportada
  para esta operación?
- ¿Pueden proporcionar un caso demo con XML firmado, sin CDR/ticket y con un
  fallo temporal de disponibilidad, sin usar datos productivos?
- ¿El reintento conserva el registro, XML, serie y número y evita otra firma?
- Si se pierde la respuesta HTTP, ¿cómo identificar que terminó ese intento y
  cuándo es seguro repetirlo? ¿Hay clave idempotente o ID de solicitud?
- ¿Cómo se consulta el resultado definitivo y se recupera el CDR de ese intento?

No se enviaron mensajes al proveedor. Se solicitó al usuario autorización y
contacto de soporte para enviar esta consulta concreta.
