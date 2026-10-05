# Corrección de credenciales en logs

Actualización de integración: incorporada localmente en
`codex/contingency-send-phases` el 3 de octubre. La revisión añadió protección
para los handlers propios de Uvicorn, que no propagan al handler raíz.
`configure_logging` conserva sus streams, niveles y propagación y aplica el
formateador con redacción. La nueva prueba instala la configuración real de
Uvicorn antes de configurar Inkora; verifica access, excepciones y HTTPX por
root, configuración repetida sin duplicados y petición original intacta.
Resultado: 31 pruebas aprobadas en 0,40 s; conjunto con contratos: 50 aprobadas
en 5,32 s. Logs en `pruebas/logging-installation-final-20261003.log` y
`pruebas/contingency-integrated-logging-contracts-20261003.log`.
La corrección sigue sin publicarse y la rotación sigue pendiente. Las secciones
siguientes conservan el diagnóstico y evidencia del bloque de origen.

## Diagnóstico y alcance

El monitoreo detectó que httpx registró una URL con token APISPeru en producción.
El formateador usaba `record.getMessage()` y la excepción sin redacción. Este
bloque autorizado se aisló desde main remoto
`c336060527eafc9f438633557d85c9a936e83313` en `codex/redact-credential-logs`.
No incluye los cambios fiscales pendientes de la rama de contingencia.

## Cambio

- Ocultar valores de parámetros de consulta, incluso nombres codificados y
  rutas relativas, conservando la ruta y nombres de parámetros para diagnóstico.
- Ocultar credenciales en userinfo de URLs, cabeceras de autorización y cookies.
- Ocultar claves sensibles en mensajes, contexto anidado y excepciones,
  incluyendo aliases reales de Inkora como `token_acceso`, `client_secret_sunat`,
  `clave_sol` y `sunat_cert_password_enc`.
- Conservar el LogRecord original y la petición enviada; solo cambia la salida
  del formateador. Mantener eventos, job IDs, estados y trazas diagnósticas.

Archivos: `backend/logging_utils.py` y `backend/test_logging_utils.py`.

## Verificación

Desde backend, con Python 3.11:

```text
python -m pytest --noconftest test_logging_utils.py -q
```

30 casos aprobados, incluidos un cliente httpx real con MockTransport sin red,
URLs de token, cookies múltiples, Digest, contexto anidado, aliases de Inkora,
excepciones e idempotencia de redacción. La revisión independiente detectó
cookies parciales y aliases faltantes; ambos quedaron corregidos y probados.

Un primer comando desde la raíz con --noconftest no encontró el módulo local;
se corrigió el directorio de ejecución a backend. Una prueba de excepciones
contenía el secreto sintético literalmente en la línea de código del traceback;
se ajustó para modelar una respuesta recibida, sin secretos incrustados en código.

## Estado y límites

Corrección local, sin commit, integración ni despliegue. No cambió permisos,
estado fiscal, esquema, frontend ni credenciales remotas. No se repitieron suites
fiscales o navegador ajenas al cambio; las puertas canónicas de publicación
siguen pendientes antes de publicar.

La redacción no elimina logs históricos ni revoca el token expuesto. Su rotación
requiere emitir el reemplazo en APISPeru, actualizar su configuración y verificar
el servicio de forma coordinada. El incidente sigue abierto hasta desplegar la
corrección y completar la rotación. No es una garantía contra secretos sin etiqueta
en texto arbitrario ni contra otros handlers que no usen este formateador.
