# Continuación de contingencia: conservación de evidencia

## Alcance y diagnóstico

Continuación autorizada por el usuario el 3 de octubre. Se conserva el worktree
`codex/contingency-send-phases`, basado en el main remoto
`c336060527eafc9f438633557d85c9a936e83313`, verificado antes de continuar.
La raíz histórica no se utiliza para implementar ni publicar.

La revisión focal identificó dos riesgos en la conciliación:

1. Un XML firmado recibido y validado desde la API podía descartarse al sustituir
   la respuesta por una lectura pendiente del panel. A su vez, el cliente del
   panel descartaba un CDR recuperado si la descarga separada del XML daba 404.
2. Una consulta tardía pendiente podía sobrescribir el estado de un documento
   que otra consulta ya había rechazado con un CDR coincidente. Esto podía volver
   a habilitar la entrega del XML y dejar la tarea reintentando innecesariamente.

Ambos riesgos pertenecen al flujo aprobado de contingencia y actualización de
estados; no requieren migraciones ni modificaciones de frontend.

## Conservación de XML y CDR

- Conservar el primer XML que superó la validación de firma, identidad, receptor
  e importes, aunque la lectura posterior del panel no tenga XML o falle.
- Si el panel devuelve otro XML, mantener los bytes originales y dejar la
  conciliación pendiente. Un XML diferente nunca autoriza aceptar el documento.
- Conservar el CDR descargado aunque el recurso XML del panel no esté disponible.
  Sólo reconciliar como aceptado cuando se disponga también del XML válido.
- Una consulta pendiente puede generar el PDF con XML validado, pero no declara
  aceptación SUNAT ni consume la cuota de documentos aceptados.

La conservación cubre también respuestas de error de consulta que contienen XML.
El indicador de fallo de transporte se mantiene; conservar evidencia no prueba
que SUNAT o el servicio de envío se hayan recuperado. Las pruebas incluyen
respuesta API 404/500/503, panel pendiente, timeout del panel y XML discordante.

## Resultados fiscales que llegan fuera de orden

La comprobación de un rechazo almacenado exige un CDR legible de esa empresa y
ese comprobante. Una etiqueta `rejected`, un texto de error o un CDR ajeno no
bastan. La relectura del documento bajo bloqueo debe ocurrir antes de guardar
la respuesta tardía y nuevamente después de cualquier commit intermedio.

La aceptación ya acreditada mantiene su protección anterior. Un CDR recibido que
contradiga otro resultado fiscal confirmado requiere conciliación del conflicto;
no debe desaparecer como si fuera una simple respuesta pendiente.

El conflicto queda registrado con identidad y huellas de ambos CDR en auditoría
y en el resultado del trabajo, con un error explícito de conciliación. No se
consume cuota ni se reemplaza automáticamente el CDR que estaba confirmado.

La protección se aplica también inmediatamente antes de escribir un rechazo nuevo:
una aceptación guardada por otro trabajo durante el procesamiento del PDF conserva
su estado, XML, CDR y cuota. Un rechazo entrante sin RUC del emisor confirmado
permanece en conciliación.

Los cierres por resultado ya confirmado conservan la señal interna de caída de la
API. Se registra antes de adquirir el bloqueo del documento porque actualizar
el circuito hace commit. La misma consulta fallida se registra una sola vez,
incluso si después aparece un CDR contradictorio del panel.

## Validación

Pruebas focalizadas del bloque, sin envíos fiscales externos:

| Alcance | Resultado | Evidencia en `pruebas/` |
|---|---:|---|
| Cliente panel y reintento | 152 aprobadas | `panel-evidence-preservation-client.log` |
| Conciliación y servicio de facturación | 69 aprobadas | `contingency-evidence-service-final.log` |
| Worker, incluidos 14 casos nuevos | 48 aprobadas | `rejection-terminal-worker-final.log` |
| Regresión de cola | 27 aprobadas | `contingency-evidence-queue-final.log` |
| PostgreSQL local, tres escenarios entre sesiones | 3 aprobadas | `contingency-evidence-postgres-final.log` |

Son 296 casos de las cuatro suites y tres casos PostgreSQL. Una regresión
intermedia de worker y contingencia dio además 99 aprobadas; no se suman como
pruebas nuevas ni se usa esa ejecución intermedia para sustituir los casos finales.

PostgreSQL se ejecutó en `127.0.0.1:55439`, base desechable
`inkora_worker_panel_20261002`, y se detuvo al finalizar. Los escenarios verifican
que otra sesión pueda confirmar rechazo o aceptación mientras la consulta está en
vuelo, sin mantener una transacción SQL durante la petición externa simulada.

Controles de funcionalidades, assets e importaciones aprobados y diff sin errores
de espacios. Huella local revisada (381 archivos, `canonical-text-v1`):
`3e89efb4cbd096d42cde80ea5f20bc9b728b9aad786a0e2bf1d44e9a2c147240`.
Evidencia: `pruebas/contingency-evidence-review-content.json`.
Es una revisión del árbol local sin commit; no es un paquete de despliegue.

La lectura de cierre confirmó main remoto sin cambios y respuestas HTTP 200 de
`/health` y `/release.json`, ambas con huella productiva
`6651223d6efe4fb396668efe4fc59d9c90418fdf7394429d29b7da92f3ad8f25` y base
`9152c3fac714e06a97708b0879807c1eb4b1d331`. No se cambió producción.

## Límite externo que permanece

El historial oficial de Smart PSE fue consultado por lectura. Contiene eventos y
fechas, pero las respuestas observadas no vinculan un evento a un identificador
de solicitud. No habilita por sí solo reenvíos repetidos después de un POST de
resultado incierto. Ver `docs/REINTENTO_PANEL_SMARTPSE_2026-10-02.md`.

Este bloque sigue siendo local. No activa contingencia, cambia credenciales o
flags remotos, emite documentos, consume correlativos ni despliega servicios.
La validación demo de un reintento por panel sin CDR y con ambiente aislado sigue
pendiente; no se declara contingencia productiva completa.
