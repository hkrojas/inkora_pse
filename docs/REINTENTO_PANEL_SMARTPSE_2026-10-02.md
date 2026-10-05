# Reintento del documento existente mediante el panel Smart PSE

Actualización del 5 de octubre: `REINTENTOS_CONTROLADOS_PANEL_2026-10-05.md`
reemplaza el límite local de un intento por una cadena de intentos separados
por 15/30 minutos, exclusivamente tras una respuesta temporal explícita del
mismo POST. Las respuestas inciertas siguen en conciliación. El contrato
negativo aún requiere comprobación real antes de habilitarlo en producción.

Validación posterior: `VALIDACION_CONTINGENCIA_WORKER_2026-10-03.md` documenta
la corrección que impide atribuir fallos del panel a la API fiscal, 64 pruebas
del worker y el recorrido real demo de FCTG-2. La empresa demo separada 688 ya
está comprobada; el límite externo restante es obtener el caso elegible sin CDR,
no la ausencia de una empresa demo. Las secciones siguientes conservan la
evidencia histórica de este bloque.

## Alcance

Bloque backend local solicitado tras comprobar que repetir el XML productivo de
FA01-230 en `/api/cpe/enviar` devuelve 1033 sin XML/CDR y deja el panel en error
aunque conserva su CDR original. Base remota comprobada al iniciar:
`c336060527eafc9f438633557d85c9a936e83313`.

Se continúa el worktree `codex/contingency-send-phases`; la raíz histórica no se
usa para implementar ni publicar. No se amplía a boletas, notas o guías.

## Contrato observado del panel

El 3 de octubre de 2026 por lectura:

- El recurso oficial `https://panel.smartpse.pe/build/assets/Index-BT5ZRjeW.js`
  ejecuta `axios.post(route('client.documents.retry', document.id))` sin datos
  de factura en el cuerpo. La interfaz interpreta `ok` y `message` y recarga la lista.
- El mapa de rutas de `https://panel.smartpse.pe/login` identifica
  `client.documents.retry` como POST `panel/documentos/{document}/reintentar`.
- El botón se muestra para `error`/`rechazado` con `has_signed_xml`; excluye guías.
- Los registros incluyen `state`, `error_message`, `has_cdr`, `has_signed_xml`,
  identidad, empresa y ambiente. No incluyen un identificador del último intento
  ni fecha de conclusión que permita demostrar que un POST incierto terminó.

Es una ruta interna autenticada, no un contrato de API pública homologado. El
código del navegador no prueba la implementación del servidor ni su selección
del ambiente fiscal. Inkora aplica controles más restrictivos que el botón.

## Comportamiento implementado

1. Consultar y recuperar CDR antes de considerar cualquier POST.
2. Si existe CDR, validar su identidad y resultado. Una aceptación ya acreditada
   no se sustituye por el error de un intento posterior.
3. Para un error temporal explícito sin CDR, comprobar empresa, ambiente congelado,
   identidad, XML firmado original y permisos actuales del emisor.
4. Reservar la comprobación compartida del servicio y el documento. Persistir un
   marcador durable antes del POST, sin conservar transacción SQL durante HTTP.
5. Ejecutar una sola operación contra el registro existente. No generar ni firmar
   otro XML, modificar su numeración o llamar a `/api/cpe/enviar` como alternativa.
6. Conciliar después mediante XML/CDR. `ok=true` no acredita aceptación SUNAT.

### Límite de repetición del bloque original (sustituido el 5 de octubre)

En este bloque se admite **como máximo un intento automático por documento**
mediante esta ruta. Si el POST pierde la respuesta o no aporta un CDR verificable,
el worker conserva la conciliación, sin repetir automáticamente ese POST.

La misma etiqueta `error` que se leyó antes del envío no demuestra que un intento
nuevo concluyó. Permitir más intentos requiere evidencia causal del proveedor o
una política de reintento homologada. Este límite no debe presentarse como una
solución completa a cualquier duración de caída de SUNAT.

### Historial verificado el 3 de octubre

Se verificó por lectura la ruta oficial del panel
`GET /panel/documentos/{document}/historial` y se consultaron exclusivamente los
documentos identificados FDEM-1 (demo) y FA01-230 (producción). No hubo POST fiscal
ni cambios de configuración. El historial devuelve `id`, `document_id`, `event`,
`sunat_code`, `message`, `extra` y `created_at`.

En FDEM-1 hay nueve eventos; la prueba simultánea anterior produjo un evento
`error` con `[HTTP] Unauthorized` y otro `aceptado`, ambos a las 01:18:04 UTC.
`extra` es nulo en estos eventos. No existe en las respuestas observadas un
identificador de solicitud ni correlación entre inicio y conclusión del intento.
El identificador del evento no demuestra por sí solo qué POST terminó ni excluye
otro intento concurrente. No se usa ese historial para autorizar un segundo POST.

FA01-230 conserva en su historial la aceptación original y el error posterior de
la prueba autorizada. Esto refuerza la necesidad de conservar la evidencia fiscal
válida aunque la etiqueta actual del panel sea `error`.

Evidencias sin credenciales: `pruebas/panel-history-readonly-20261003.json` y
`pruebas/panel-history-extra-shape-20261003.json`. La ruta se investigó en una
lectura puntual; no se agrega sondeo periódico de historiales al worker.

## Habilitación

`SMARTPSE_PANEL_RETRY_TENANT_IDS` es una lista explícita de empresas, vacía por
defecto. La recuperación de CDR habilitada por sí sola no autoriza el nuevo POST.
El worker también exige incorporación actual a contingencia y recuperación,
snapshot compatible y ambiente original válido. Deshabilitar reenvíos debe dejar
operativa la recuperación de evidencias.

No se cambian flags remotos, secretos, esquema, frontend o despliegues en este
bloque. El alcance de habilitación corresponde al worker; no se solicita que el
usuario final gestione la caída de SUNAT.

## Validación real disponible y límite demo

La lectura de la empresa 384 encontró 19 facturas demo: todas tienen CDR. FDEM-1
está en `error` con mensaje `[HTTP] Unauthorized`, pero conserva XML firmado y
CDR. Es un caso para comprobar que el conector **no** reenvía.

La empresa compartida sigue configurada en producción. La nueva ruta del panel
no contiene `-demo` ni un parámetro de ambiente en su llamada de navegador; no
se presume que usar el ID de un documento demo fuerce SUNAT beta. No se modifica
la configuración productiva para fabricar una factura fallida.

La homologación de un POST real sin CDR sigue requiriendo un entorno demo
aislado o confirmación verificable del enrutamiento y un documento elegible.
Las pruebas locales usan datos sintéticos y transporte simulado sin red externa.

## Resultados

- Cliente del panel: **152 pruebas aprobadas**, incluyendo autenticación, CSRF,
  aislamiento, XML discordante, revalidación del registro, CDR existente, permisos
  explícitos, sesión vencida, límites, concurrencia y timeout sin repetición.
  Evidencia: `pruebas/panel-retry-client-final.log`.
- Comprobación demo real de sólo lectura: el método nuevo recuperó el CDR original
  de FDEM-1/registro 444951 y no invocó el callback de envío ni hizo POST fiscal.
  El transporte de la prueba prohibía cualquier POST fiscal, como segunda barrera.
  Evidencia: `pruebas/panel-retry-demo-20261003/existing-cdr-guard.json`.
- Worker: **34 pruebas aprobadas**. Cubren consulta previa, POST único, posterior
  aceptación por CDR, respuesta perdida, CDR ajeno/rechazado, permisos, empresa
  cambiada durante prefetch, runtime beta bloqueando producción, plazo vencido,
  circuito compartido y marcadores de otros jobs/auditoría. Evidencia:
  `pruebas/panel-retry-worker-final.log`.
- PostgreSQL real local: **46 casos únicos aprobados**, incluidos siete nuevos
  de reserva concurrente, auditoría durable, lease vencida y cambios de usuario,
  tenant, suscripción o empresa del proveedor después de reservar el circuito.
  En el primer pase combinado, 45 pasaron y uno falló por el formato del DSN del
  runner (`postgresql+psycopg2` no admitido por la conexión psycopg2 directa).
  Corregido a `postgresql`, pasó ese caso y se volvieron a ejecutar los siete
  nuevos contra el código final: **8/8**. No hubo fallo productivo ni se cambió el
  código de negocio para resolver el DSN. Evidencias:
  `pruebas/panel-retry-postgres-initial.log` y `pruebas/panel-retry-postgres-final.log`.
  Clúster exclusivo loopback detenido al finalizar.
- La revisión cruzada corrigió dos riesgos: cambio de empresa Smart PSE durante
  las lecturas y ausencia inicial de comprobación del runtime fiscal antes del
  POST. Ambos están cubiertos por pruebas focalizadas.
- Regresión pertinente: **212 pruebas aprobadas** en 122,23 s, cubriendo cola,
  contingencia, conciliación, XML inmutable, fases, leases y contratos de rutas.
  Evidencia: `pruebas/panel-retry-regression.log`. En conjunto son **398 pruebas
  de backend** (152 cliente + 34 worker + 212 regresión) y **46 casos PostgreSQL**.
- Controles de funcionalidades, assets e importaciones completos, sintaxis del
  runner PowerShell válida y `git diff --check` limpio. El runner canónico incluye
  ahora el archivo PostgreSQL nuevo en su fase dedicada.
- Huella local revisada, **no manifiesto de despliegue**:
  `96040bdcc64d942a8c61a342e26533527424101434c98bc00b1cc87c3743a9ea`,
  381 archivos publicables. Evidencia: `pruebas/panel-retry-review-content.json`.
  No se creó paquete, commit, PR ni publicación.
- No se repitieron frontend/Playwright: este bloque no modifica interfaz, rutas
  de navegador ni plantillas PDF. Los resultados del cierre anterior no sustituyen
  las puertas requeridas cuando se prepare una nueva publicación.

### Comandos focalizados

Usar Python 3.11 y el runner local `pruebas/pytest_offline.py`, que bloquea red
externa, con estos argumentos pytest:

```text
test_smartpse_panel_client.py test_smartpse_panel_retry.py -q
test_panel_retry_worker.py -q
test_emission_queue.py test_fiscal_contingency_recovery.py test_smartpse_panel_reconciliation.py test_frozen_sale_xml.py test_release_guard.py test_fiscal_submission_leases.py test_fiscal_submission_state.py -q
test_panel_retry_postgres.py test_emission_worker_postgres.py -q
```

La última línea requiere exclusivamente una base desechable local con prefijo
`inkora_worker_`, `INKORA_WORKER_POSTGRES_URL=postgresql://postgres@127.0.0.1:55439/inkora_worker_panel_20261002`
e `INKORA_REQUIRE_POSTGRES_TESTS=1`. Sus fixtures recrean tablas; jamás usar una
base que contenga información del usuario.

## Producción

Continuación local posterior, con conservación de evidencia y estados terminales:
`docs/CONTINGENCIA_CONSERVACION_EVIDENCIA_2026-10-03.md`. Su huella de revisión
sustituye a la huella local anterior; ninguna de las dos corresponde a una
publicación productiva de este bloque.

Este bloque no está desplegado y el reintento por panel no está activado.
La aceptación de FA01-230 permanece respaldada por su CDR original; el estado
`error` del registro en Smart PSE documentado en la prueba anterior no se corrige
con un reenvío adicional.
