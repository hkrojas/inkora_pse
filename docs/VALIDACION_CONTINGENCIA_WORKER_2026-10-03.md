# Validación del worker de contingencia — 3 de octubre de 2026

Actualización del 5 de octubre: `REINTENTOS_CONTROLADOS_PANEL_2026-10-05.md`
documenta la nueva cadena de reintentos tras fallo confirmado, las comprobaciones
actuales y su huella local. Sustituye el límite de una tentativa descrito abajo.
Las pruebas externas con un fallo temporal elegible siguen pendientes.

## Alcance

Continuación de pruebas autorizada por el usuario. Worktree aislado
`codex/contingency-send-phases`; main remoto verificado sin retroceso en
`c336060527eafc9f438633557d85c9a936e83313`. La raíz histórica no se modifica.
Sólo facturas tipo 01. Este documento no es un recibo de despliegue.

## Corrección encontrada durante las pruebas

El worker confundía un resultado incierto del POST del panel con una caída de
la API fiscal. Un 422, una sesión vencida o una respuesta perdida del panel
podían abrir el circuito compartido y retrasar facturas de otras empresas.

Se eliminó esa inferencia en `backend/services/emission_queue_service.py`.
Se conserva la señal de fallo de API cuando se observó independientemente
antes de intentar el panel. El marcador durable, la consulta posterior y la
prohibición de repetir un POST incierto siguen operativos.

La regresión reprodujo nueve fallos antes del arreglo. La suite completa
`test_panel_retry_worker.py` pasó después: **64 casos en 63,82 segundos**.
Los 16 casos nuevos cruzan timeout/401/403/419/422/429/500/503 del panel con
API saludable o API 503, y comprueban el circuito y la programación de un
trabajo firmado de otra empresa. Evidencia: salida de herramienta de esta
sesión, ejecución 58094, código de salida 0; no se guardó un log separado.

Regresión de cola y contingencia: **82 casos en 74,97 segundos**.
Log: `pruebas/contingency-panel-circuit-regression-20261003.log`.
No se modificaron esquema, reservas concurrentes ni frontend.

## Reintento con pérdida de respuesta, en local

`pruebas/test_demo688_failure_replay.py` ejecuta el worker y cliente de panel
reales con los XML/CDR originales de FCTG-1. La base es SQLite desechable.
El estado de error HTTP 503 sin CDR, los transportes, la pérdida de respuesta,
la aparición posterior del CDR y las subidas de archivos son simulados.

Comprobaciones:

- Marcador y auditoría persistidos antes del único POST simulado, visibles
  desde otra sesión; sin transacción SQL abierta durante el transporte.
- La misma fila de error después de perder la respuesta no provoca otro POST.
- La API responde pendiente: el fallo del panel no abre un circuito API falso.
- Cuando aparece el CDR, se conserva el XML original y se actualiza la factura
  y su cotización. La cuota pasa de cero a uno y permanece en uno al consultar
  nuevamente desde otro trabajo.

Los dos replay locales terminaron con **2 casos aprobados en 8,42 segundos**.
Se fija el reloj fiscal de la prueba a la fecha del XML demo para conservar su
reproducibilidad; no se cambia el reloj ni la lógica fiscal de producción.
Evidencia: `pruebas/demo688-failure-replay-local-20261003/result.json`.

## PDF pendiente

Revisado visualmente el PDF local de FCTG-1 generado sin CDR. Una página,
identidad e importes correctos, QR visible y legible, sin elementos cortados
ni afirmación de aceptación por SUNAT. La extracción de texto corroboró
FCTG-00000001 y total 118,00. La correspondencia de los datos del QR con el
XML está cubierta por el replay. No se realizó una lectura con cámara del QR.
Archivo: `pruebas/demo688-reconciliation-local-20261003/pending.pdf`.

## Ejecución externa FCTG-2 y ajuste del ejecutor

El preflight de lectura comprobó empresa 688 activa en demo, tenant 6 y
ausencia de FCTG-2 en la base remota y el panel. La primera ejecución hizo
una firma real y ningún envío. El worker conservó XML y generó PDF; el fallo
de autenticación provocado localmente produjo `submission_phase=not_submitted`.

El ejecutor se detuvo al comprobar el estado de la tarea: su Session SQLAlchemy
tenía `autoflush=True`, a diferencia de `database.SessionLocal` y las fixtures,
que usan `autoflush=False`. El autoflush intermedio cambió el estado antes de
terminar el intento y el control de lease impidió el commit. Se corrige la
configuración del ejecutor; no se cambia el control de lease del producto.
La evidencia inicial se conserva y no se repite la firma.

### Resultado de la continuación: aprobado

La continuación utilizó el mismo SQLite, la misma identidad FCTG-2 y el mismo
XML firmado. Recuperó la reserva local vencida mediante el código real de
`emission_leases.recover`, con la configuración de sesión de producción.
Validó nuevamente la empresa demo y el registro firmado sin CDR antes del POST.

| Etapa | Evidencia |
|---|---|
| Antes de enviar | XML firmado válido, PDF de 18 143 bytes y QR; cuota cero |
| Primer intento sin POST fiscal | Fallo de autenticación inyectado localmente; fase `not_submitted` |
| Continuación | Mismo XML y fecha congelada; una sola llamada real a `/enviar-demo` |
| Respuesta del envío descartada | HTTP 200/estado 200 con CDR y sin XML; no se entregó al worker |
| Estado incierto | Worker mantuvo pendiente y cambió a `consult_fiscal_document` |
| Consulta independiente | CDR coincidente; tarea `succeeded`, factura y cotización facturadas, cuota uno |

Identificador del proveedor: **447120**. Firma y XML original:
`15f49035fce9290c93415f9d567b211de1abe7ee0c1779b8b531b042d9889221`.
CDR recuperado:
`363833f75979b761f123d6f0aef3b1aa288d261da7a6a0adf9b15cd26a8a364b`.

Firma inicial a las 21:34 y continuación terminada a las 21:41 del sábado
3 de octubre, hora de Lima. Hubo **una firma y un envío demo reales en total**.
El contador del proveedor pasó de uno a dos durante la firma inicial y se
mantuvo en dos durante la continuación. El contador interno `send_count=2`
incluye la tentativa detenida antes del POST; no representa dos envíos de red.

Evidencia en `pruebas/demo688-worker-live-20261003/`:
`result-original.json`, `resume-result.json` (`passed=true`), los dos marcadores
de operación, `signed.xml`, `cdr.xml`, `pending.pdf` y SQLite local conservada.
No borrar marcadores ni volver a emitir esta identidad.

El ejecutor usa worker, cliente CPE, validación y persistencia reales. Se
sustituyen únicamente las credenciales por una lectura en memoria, la subida
remota por archivos locales y la fábrica de sesiones por SQLite. Los fallos
de conexión son inyectados; se adelantó la disponibilidad de los trabajos y
comprobaciones locales para evitar esperar los intervalos de producción.
No valida el despliegue Railway ni sustituye las pruebas PostgreSQL previas.
No hubo escrituras en la base productiva ni cambios de configuración remota.

### Comandos de esta validación

Desde el worktree, usando el entorno Python 3.11 existente:

```text
python pruebas/pytest_offline.py test_panel_retry_worker.py -q
python pruebas/pytest_offline.py test_emission_queue.py test_fiscal_contingency_recovery.py -q
python pruebas/pytest_offline.py ../pruebas/test_demo688_reconciliation.py ../pruebas/test_demo688_failure_replay.py -q
```

Las operaciones externas de `demo688_worker_live.py --run` y
`--resume-not-submitted --run` ya se consumieron. Se documentan como evidencia,
no como instrucciones para repetirlas. El modo de continuación exige ausencia
del marcador de envío y rechaza la ejecución ahora que ese marcador existe.

## Límites de homologación

La pérdida de respuesta fabricada en el cliente no equivale a una caída de
SUNAT. No demuestra que un POST incierto haya terminado antes de otro intento.
El reintento del panel sigue limitado a una tentativa por documento elegible.
Permanece pendiente una prueba externa de error temporal explícito sin CDR
que el proveedor admita reenviar, y la garantía de repetición después de
resultados inciertos. El intento anterior desde `firmado` obtuvo 422 y no
satisface esa condición.

Las pruebas actuales no habilitan contingencia integral en producción. La
publicación requiere integrar el candidato revisado y cumplir las puertas
de `RELEASE_CANONICO.md`, incluida la validación aislada que corresponda.

### Cierre local posterior del 3 de octubre

La corrección de exposición de credenciales en logs de
`codex/redact-credential-logs` quedó integrada en este candidato. La revisión
encontró además handlers propios de Uvicorn fuera de la redacción original;
se corrigió la instalación para cubrirlos y conservar su configuración de
stream, niveles y propagación. Sus 31 pruebas pasaron; la ejecución conjunta
de logs y contratos aprobó 50 casos en 5,32 s. No se repitieron suites fiscales
externas ni comprobantes aceptados.

La lectura posterior del listado completo de empresa 688/demo encontró sólo
FCTG-1 y FCTG-2, ambas aceptadas con CDR: cero candidatos para el reintento
temporal pendiente. Una sesión y un listado; sin POST fiscal ni descargas.
Evidencia: `pruebas/demo688-eligible-candidates-readonly-20261004.json`.
La consulta al proveedor está preparada en
`CONSULTA_SMARTPSE_REINTENTO_SIN_CDR_2026-10-03.md`; no se envió.

Funcionalidades, assets e importaciones aprobaron sobre el contenido integrado,
381 archivos, modo `canonical-text-v1`, huella local:
`d996d0c3985c55ae98a5c6c675fbcaa3b67309181ca9caadcd48183e96ca13a3`.
Evidencia: `pruebas/contingency-integrated-review-content-20261003.json`.
Es una identificación del contenido sin commit, no un manifiesto o paquete
de publicación. `git diff --check` aprobó.

La publicación y la rotación de las credenciales previamente expuestas siguen
pendientes. No se modificaron producción, variables fiscales o secretos remotos.
