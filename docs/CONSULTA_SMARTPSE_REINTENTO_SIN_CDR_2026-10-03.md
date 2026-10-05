# Consulta para homologar reintento sin CDR

Borrador técnico preparado para Smart PSE. No se envió una comunicación externa.

Estamos validando la contingencia de facturas tipo 01. La empresa 688 está
configurada exclusivamente en demo. Las pruebas FCTG-1 y FCTG-2 comprobaron
firma sin CDR, primer envío del mismo XML y recuperación independiente del
CDR después de descartar la respuesta del envío. Ambas están aceptadas en demo.
No necesitamos reenviar esos documentos aceptados para probar el caso pendiente.

Necesitamos un escenario beta controlado con un documento existente que tenga:

- XML firmado original disponible y numeración fija;
- estado `error` con una causa temporal concreta de transporte/SUNAT;
- ausencia de CDR y de ticket en procesamiento.

La interfaz del panel realiza `POST /panel/documentos/{document}/reintentar`.
Un intento sobre un documento que sólo estaba `firmado` recibió HTTP 422;
no se considera equivalente al escenario de error temporal.

Por favor indiquen:

1. ¿Existe una ruta API pública y soportada que reintente el registro existente
   con su XML original? Si sólo existe el panel, ¿garantiza usar el ambiente demo
   del documento y conservar identidad, XML y contador de firmas?
2. ¿Cómo podemos provocar o recibir el escenario beta temporal sin CDR anterior
   para ejecutar la prueba? Necesitamos un resultado controlado del servidor;
   perder la respuesta únicamente en nuestro cliente no reproduce ese caso.
3. Si perdemos la respuesta del reintento, ¿qué evidencia permite comprobar que
   terminó y repetirlo? ¿Existe una clave idempotente, identificador de intento,
   consulta de estado causal o garantía expresa de repetición de la misma operación?

La implementación actual consulta el CDR primero, reserva un intento durable,
ejecuta como máximo un POST y después consulta. Un error histórico sin cambios
no autoriza otro POST. Para superar ese límite necesitamos el contrato anterior.

No incluir tokens, contraseñas, credenciales SOL ni archivos de certificado en
la comunicación. El RUC y las evidencias públicas de los documentos demo se
pueden aportar por el canal oficial que Smart PSE indique.
