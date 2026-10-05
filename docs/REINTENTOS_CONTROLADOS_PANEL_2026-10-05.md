# Reintentos controlados del panel — 5 de octubre de 2026

Actualización de las 10:07 Lima: `PRUEBA_ERROR_DEMO_2074_2026-10-05.md`
documenta un reintento real del mismo FERR-1. Confirmó la forma negativa del
panel y permitió corregir el campo adicional `state`; 213 pruebas aprobaron.
Huella local vigente: `95c7a5e79745f8e898c404eba77075750bd0540289feec263cd844fe6cff5c28`.
La prueba real de fallo temporal continúa pendiente. El usuario decidió
observarla cuando ocurra naturalmente en producción; la preparación vigente y
el procedimiento están en `PREPARACION_CONTINGENCIA_2026-10-05.md`.

## Alcance y base

Bloque backend autorizado por el usuario para sustituir el límite provisional
de un reintento automático por factura. Se conserva el worktree aislado
`codex/contingency-send-phases`. El `main` remoto se comprobó nuevamente y sigue
en `c336060527eafc9f438633557d85c9a936e83313`; no se publicó este candidato.

No modifica series, correlativos, importes, firmas, esquema ni frontend.
Reutiliza los flags de contingencia, recuperación y reintento por empresa.

## Decisión del worker

1. Consultar primero. Un CDR verificable determina aceptación o rechazo.
2. Para considerar un POST, comprobar nuevamente empresa, ambiente congelado,
   permisos, plazo, ausencia de CDR y coincidencia exacta del XML firmado.
3. Reservar el intento bajo bloqueo del documento y lease vigente del job.
   Guardar UUID, secuencia y predecesor en documento, job y auditoría antes de HTTP.
4. Clasificar la respuesta del mismo POST:
   - HTTP 200, `Content-Type: application/json`, objeto `ok`/`message`,
     permitiendo sólo el campo adicional `state` con valor `error`,
     `ok` booleano falso y error temporal permitido: finalización temporal confirmada.
   - Respuesta perdida, HTTP de error, JSON incompleto o contradictorio, ticket,
     procesamiento o simple `ok=true`: continuar consultando, sin autorizar otro POST.
5. Sólo una finalización temporal confirmada permite un sucesor: 15 minutos
   después de la primera, 30 minutos después de las siguientes. El contador
   considera POSTs del panel, no consultas intermedias.
6. Antes del sucesor, repetir la consulta y todas las barreras. Si llega un CDR,
   completar el documento y actualizar Inkora sin reenviarlo.

El mensaje temporal por sí solo en la lista del panel no finaliza un intento.
La respuesta explícita del POST tampoco significa que SUNAT nunca recibió el XML
ni que rechazó fiscalmente la factura: el estado fiscal se decide con el CDR.

## Concurrencia y evidencia

- Auditoría de inicio y finalización por intento, conservada sin reemplazar entradas.
- Validación de la cadena completa y de las copias en documento/jobs. Un marcador
  antiguo, desconocido, incompleto o inconsistente conserva sólo la conciliación.
- Comparación del predecesor esperado dentro del bloqueo del documento.
- La finalización exige la misma reserva y el mismo UUID; una respuesta tardía
  no puede completar el intento de otra ejecución.
- El tiempo se comprueba nuevamente antes de autorizar HTTP. Adelantar el job
  no adelanta el permiso para reenviar.
- Se conserva la huella del cuerpo recibido y un mensaje sanitizado, sin guardar
  contraseñas ni el cuerpo HTTP completo en la auditoría.
- Las consultas y los POSTs se ejecutan sin mantener una transacción SQL abierta.
- El resultado del panel no abre ni cierra por sí solo el circuito de la API;
  se conserva cualquier caída de API observada independientemente.

## Pruebas y límite de habilitación

Las pruebas de este bloque son locales, con transportes simulados y PostgreSQL
aislado en loopback. Comprueban la secuencia 15/30, pérdida de respuesta posterior,
CDR antes del siguiente POST, ausencia de pausa indebida de otras empresas,
competencia entre dos jobs y resultados tardíos.

Resultados del bloque:

- Cliente y parser: 250 pruebas aprobadas.
- Historial y política de autorización: 60 aprobadas, incluida lectura fresca
  después de una modificación concurrente que deja obsoleta la copia ORM.
- Regresión de worker, cola y recuperación: 146 aprobadas.
- Secuencia completa de reintentos: 3 aprobadas.
- PostgreSQL: 13 aprobadas (3 de secuencia y 10 de barreras existentes).

Evidencias locales: `pruebas/panel-retry-state-final-20261005.log`,
`pruebas/panel-sequence-regression-offline-20261005.log` y
`pruebas/panel-retry-sequence-final-20261005.log`.

El código público del panel evidencia las claves `ok` y `message`. Todavía no se
ha observado una respuesta real del POST elegible con `ok=false` y fallo temporal
503. El parser implementa esa variante temporal como contrato pendiente de validar;
si el proveedor entrega otra forma, mantiene la conciliación.

Este bloque no acredita por sí solo la homologación externa ni habilita la
contingencia en producción. El usuario decidió comprobar la respuesta temporal
en el primer caso natural productivo, conservando el contrato estricto y la
conciliación cuando el resultado sea desconocido. No se necesitan más facturas
demo para preparar el código. Quedan la integración y publicación canónicas;
no se fuerzan fallos ni reenvíos de facturas aceptadas para fabricar ese escenario.

## Comprobación final del 5 de octubre, 09:34–09:38 Lima

La lectura actual del listado completo de empresa 688/demo encontró sólo
FCTG-1 y FCTG-2, ambas aceptadas con XML/CDR. Cero candidatas para reintento
temporal. Se verificó además la identidad del tenant 6 en transacción de sólo
lectura. No hubo POST fiscal, cambios remotos ni descargas de documentos.
Evidencia: `pruebas/demo688-candidates-readonly-20261005.json`.

La comprobación adicional ejecutó el worker y cliente de panel reales sobre
los XML/CDR demo conservados, reemplazando únicamente el transporte HTTP y
Storage. Los tres recorridos verifican respuesta perdida, fallo temporal
confirmado seguido de pérdida y dos fallos temporales confirmados seguidos
de CDR. Conservan el XML exacto, generan el PDF y empaquetan el CDR; actualizan
documento/cotización y consumen la cuota una sola vez. Son pruebas locales:
las respuestas temporales se simulan y no homologan el servidor del proveedor.

Los tres recorridos y los contratos operativos/publicación aprobaron 23 casos
en 16,12 s. Evidencia: `pruebas/contingency-final-replay-20261005.log` y
`pruebas/demo688-failure-replay-local-20261003/result-*.json`.

`scripts/verify_recovery.ps1` ahora incluye la nueva suite de secuencia en la
etapa PostgreSQL obligatoria; la excluye de la etapa general para evitar que
un resultado omitido por falta de PostgreSQL se confunda con su aprobación.
Su sintaxis PowerShell y `git diff --check` aprobaron.

La identidad local del candidato comprobado a las 09:38 era
`a6013e7afd2b4e65c8b3e31c917d3da1f0420e08834da9b4f9b4b7df0c916e88`,
382 archivos con modo `canonical-text-v1`. Funcionalidades, assets, cierre de
importaciones e inclusión del nuevo módulo aprobaron. No es un paquete ni un
manifiesto de entrega: el contenido sigue sin commit y conserva las puertas de
publicación. Evidencia: `pruebas/contingency-integrated-review-content-20261005.json`.
