# Asistente de guías y consultas

La guía de venta conserva tres pasos: venta/cantidades, transporte y revisión.
Continuar y volver no escriben datos. En la revisión se puede guardar un borrador
o emitir con confirmación explícita. Emitir utiliza la misma cola y validación
fiscal del detalle; no confirma la salida física. Si falla el encolado después de
guardar, se abre el borrador existente para consultar su estado. Un reintento del
mismo guardado conserva su clave de idempotencia durante la sesión del formulario.

El destinatario de una guía de venta proviene del comprobante. Las consultas no
reescriben ese cliente ni sus datos históricos. En la guía transportista se pueden
consultar los RUC del remitente y destinatario; el documento del destinatario sigue
siendo RUC, conforme a su contrato actual.

Las consultas son opcionales y requieren pulsar su botón:

- DNI/RUC reutiliza `/consultar-documento/{numero}` y su credencial por empresa.
- Placa utiliza Factiliza `GET /placa/info/{placa}`. Solo muestra marca, modelo y
  color; no acredita autorización de circulación.
- Licencia utiliza Factiliza `GET /licencia/info/{dni}`. Completa el número y
  muestra categoría, estado y vencimiento devueltos. No inventa una licencia a
  partir del DNI ni sustituye la validación fiscal.

Placa/licencia requieren `FACTILIZA_API_URL` y `FACTILIZA_API_TOKEN` exclusivamente
en backend. Los endpoints requieren empresa activa y rol administrador/operador,
limitan a 20 solicitudes por minuto por origen/endpoint y no almacenan resultados.
Las respuestas exitosas declaran `Cache-Control: no-store`. Los errores externos
no exponen texto del proveedor ni credenciales. La entrada manual permanece
disponible; respuestas tardías o de otra identidad no sobrescriben campos.

No hay migraciones ni cambios de inventario, correlativos o estados fiscales.
Las pruebas de proveedor y emisión usan respuestas simuladas, además de la
regresión local PostgreSQL y el check de publicación requerido `verify`.

Referencias del proveedor:
[placa](https://docs.factiliza.com/api-consulta/endpoint/placa) y
[licencia](https://docs.factiliza.com/api-consulta/endpoint/licencia-conducir).
