# Continuación de contingencia: recuperación de evidencia y firma

Estado vigente del 5 de octubre: `PREPARACION_CONTINGENCIA_2026-10-05.md`.
El usuario decidió observar el fallo temporal real cuando ocurra en producción.
Los reintentos posteriores a una respuesta temporal confirmada ahora usan el
historial durable descrito en `REINTENTOS_CONTROLADOS_PANEL_2026-10-05.md`.
Este informe conserva el cierre anterior y sus límites; no acredita un despliegue.

Validación posterior del 3 de octubre: `VALIDACION_CONTINGENCIA_WORKER_2026-10-03.md`.
Incluye FCTG-2 real demo con worker local, conservación de PDF/XML/QR,
recuperación tras respuesta perdida y corrección del falso circuito compartido
por errores del panel. Los límites de reenvío externo sin CDR siguen explícitos.

Actualización posterior: el bloque opt-in de reintento del registro existente
mediante el panel está descrito en `REINTENTO_PANEL_SMARTPSE_2026-10-02.md`.
Permite una tentativa durable por documento elegible, conserva CDR-first y
requiere homologación aislada antes de habilitarse. Este informe conserva las
pruebas y límites del bloque anterior; no implica publicación del nuevo reintento.

Estado: implementación del alcance seguro cerrada en `codex/contingency-send-phases`;
validación local documentada abajo. No publicada; el reenvío incierto productivo
continúa pendiente de homologación y no se declara contingencia completa habilitada.
Base remota comprobada: `c336060527eafc9f438633557d85c9a936e83313`.

## Alcance implementado

Se mantiene el alcance inicial de facturas tipo 01. No se amplía la firma y el
envío separados a boletas, notas o guías. Los documentos inciertos se concilian
sin crear otro correlativo ni asumir que HTTP 404 demuestra ausencia en SUNAT.

- Fases persistidas antes del envío: trabajo nuevo, posible envío y prueba local
  de que el intento no llegó al POST. La recuperación de reservas vencidas usa
  el mismo criterio en Python y PostgreSQL. Los trabajos históricos no reciben
  retroactivamente una fase segura.
- Recuperación de XML firmado desde el panel aunque todavía no exista CDR,
  únicamente cuando el proveedor declara que existe firma. Se valida firma,
  identidad, ambiente, receptor e importes antes de conservarlo y preparar PDF/QR.
  El estado sigue pendiente; no se aplican efectos de aceptación.
  El recurso público oficial del panel `Index-BT5ZRjeW.js` utiliza
  `has_signed_xml` para habilitar la descarga XML y `has_cdr` para la del CDR,
  independientemente. Esa lectura confirma los campos del contrato de interfaz;
  no constituye una prueba real de caída de SUNAT.
- El XML firmado conservado es inmutable. Las respuestas de envío y consulta
  deben coincidir exactamente con sus bytes. Una respuesta discordante mantiene
  conciliación. La persistencia también verifica esta condición bajo bloqueo.
- Consulta de artefactos existentes en el panel ante 404, HTTP 5xx o transporte
  tipado de la API, sólo para empresas incorporadas y ambiente original comprobado.
  Un fallo del panel no oculta el error original de transporte de la API.
  Recuperar artefactos por panel tampoco demuestra que la API se haya recuperado;
  su fallo temporal se conserva para coordinar la pausa de los demás trabajos.
- Firma temporal con reintentos espaciados hasta el plazo fiscal, sin abandono
  automático al quinto intento. Los errores de validación detienen ese trabajo.
- Circuito de firma `cpe:sign` independiente del circuito de envío `cpe`. Se usa
  la tabla existente: no requiere migración. Cada circuito coordina una sola
  comprobación de recuperación entre empresas y réplicas, con esperas de 15/30
  minutos. Recuperar un servicio no adelanta trabajos pausados por el otro.
- Vencimiento con una alerta de auditoría; se detienen nuevos intentos de envío
  o firma. Las consultas de trabajos ya enviados continúan.

## Límite pendiente de homologación externa

La prueba real de repetir exactamente FDEM-1 en `/enviar-demo` conservó registro,
XML y contador de firmas y devolvió un CDR nuevo de aceptación. No acredita por
sí sola el caso productivo en que se pierde la respuesta del primer envío.

La matriz real posterior de seis reenvíos confirmó éxito secuencial y detectó
un error `estado: 500` en uno de dos envíos simultáneos; el panel conservó XML y
CDR aceptados. Detalle y límites en `PRUEBA_REENVIOS_DEMO_2026-10-02.md`.

Por eso no se habilita un reenvío automático de un estado incierto, ni se declara
la contingencia completa habilitada. Si el proveedor no genera CDR, el trabajo
permanece en consulta y requiere resolver el contrato de retransmisión.

Consulta técnica preparada para Smart PSE:

> Si `/api/cpe/enviar` pierde la respuesta, ¿podemos repetir exactamente el mismo
> XML firmado y nombre? ¿Qué devuelve si ya fue aceptado, sigue procesándose o
> todavía no llegó a SUNAT? ¿El reenvío conserva el mismo registro y evita una
> nueva firma o cobro?

Enviar esa consulta requiere la respuesta a la autorización solicitada al usuario.
No se envió una comunicación externa como parte de esta implementación.

## Producción

La API y el frontend continúan declarando huella
`6651223d6efe4fb396668efe4fc59d9c90418fdf7394429d29b7da92f3ad8f25`
y base `9152c3fac714e06a97708b0879807c1eb4b1d331`, verificadas por lectura.
El recibo de recuperación CDR del 2 de octubre describe la configuración desplegada.
Este bloque no cambia credenciales, flags, datos, correlativos ni despliegues.

## Verificación

Las pruebas de backend bloquean conexiones externas y utilizan datos sintéticos.
PostgreSQL usa exclusivamente una base local desechable en loopback.

- PostgreSQL 17: 39 pruebas aprobadas, incluidas diez empresas y una sola prueba
  de recuperación simultánea en cada servicio; JSON malformado no interrumpe
  la actualización compartida de la cola. La primera ejecución detectó una
  incompatibilidad de sintaxis del CAST JSONB generado por SQLAlchemy; se corrigió
  mediante `->` y la ejecución final pasó completa. Servidor detenido al terminar.
- Cierre de PostgreSQL real: otras 10 pruebas de guías/remisiones/migraciones
  locales y dos de cotizaciones/inventario aprobadas en bases desechables
  independientes. Total PostgreSQL del bloque: 51 casos. Servidor local detenido.
- Frontend: 54 pruebas, lint, build y presupuesto de bundle aprobados. No hay
  cambios de interfaz en este bloque.
- Recorridos completos locales: **133 pruebas Playwright aprobadas en 6,2
  minutos**, con API y navegador aislados, SQLite temporal y datos sintéticos.
  Incluyen comprobantes, acciones, notas, guías, cuotas, permisos, búsqueda y
  paginación. Evidencia: `pruebas/contingency-e2e-final.log`.
- Backend: 1.057 pruebas aprobadas en 397,63 segundos con Python 3.11. Esa
  ejecución precede al último ajuste que conserva el diagnóstico API cuando el
  panel recupera evidencia; dicho ajuste se verifica después con suites focalizadas.
- Ajuste final: 79 pruebas de XML inmutable y conciliación por panel aprobadas
  en 56,62 segundos; otras 12 pruebas del worker aprobadas en 17,63 segundos
  cubren 503/timeout/conexión/404 con aceptación, pendiente y rechazo. Se corrigió
  además la propagación del resultado parcial en la excepción de rechazo.
  La revisión cruzada de los agentes cerró sin más hallazgos P1 en este alcance.
- Evidencia: `pruebas/contingency-postgres-final.log`,
  `pruebas/contingency-backend-full.log`,
  `pruebas/contingency-frontend-test.log`, `pruebas/contingency-frontend-lint.log`
  y `pruebas/contingency-frontend-build.log`, `pruebas/contingency-final-evidence.log`
  y `pruebas/contingency-final-circuit.log`, `pruebas/contingency-gre-postgres.log`
  y `pruebas/contingency-quote-postgres.log`.

La revisión final acotada no encontró otro P1 implementable en el alcance seguro:
el HTTP 200/estado 500 sin CDR mantiene conciliación, el XML validado evita nuevas
firmas, la clave del job impide encolados canónicos duplicados y el bloqueo del
documento evita aplicar dos veces una aceptación.

Los validadores canónicos de funcionalidades, identidad visual y cierre de imports
aprobaron. Huella del contenido local revisado (381 archivos de runtime):
`24ae26017f93198058a0b8b925b12011286c8c274e658e9d36094aebc9f3f99e`.
Es una identificación de contenido sin commit, no un manifiesto de publicación ni
una autorización de despliegue. Evidencia: `pruebas/contingency-review-content.json`.

`git diff --check` terminó sin errores. Los conteos de suites focalizadas no se
suman como si fueran casos distintos de la regresión: parte de su cobertura se repite.
Esto no constituye un recibo de despliegue ni homologación productiva. No se hizo
commit, integración, empaquetado canónico ni publicación. Las puertas de publicación
restantes se mantienen en `RELEASE_CANONICO.md`; no se declara aprobado staging.

## Estado de cierre para la siguiente decisión

| Capacidad | Estado |
|---|---|
| Firmar y conservar XML; entregar PDF/QR pendiente | Implementada y probada localmente |
| Coordinar pausas entre empresas y efectuar un primer envío seguro | Implementada y probada localmente |
| Recuperar XML/CDR y actualizar aceptación o rechazo sin duplicar efectos | Implementada y probada localmente |
| Evitar envíos simultáneos y reintentos de historia desconocida | Implementada y probada localmente |
| Reenviar automáticamente si el primer envío fue incierto y no aparece CDR | Pendiente de confirmar contrato Smart PSE; bloqueado |
| Integración y despliegue de estos cambios | No realizados |

No se requiere seguir agregando funciones al bloque seguro para cerrarlo. La
contingencia integral depende del caso de retransmisión pendiente: una factura
que SUNAT nunca aceptó no se resuelve únicamente consultando. Se necesita una
respuesta del proveedor sobre el mecanismo de reenvío de esa misma identidad
antes de implementar/habilitar esa política en producción. Los seis reenvíos
demo sobre una factura previamente aceptada no acreditan ese escenario.
