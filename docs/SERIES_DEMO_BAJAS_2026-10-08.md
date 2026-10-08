# Series y prueba de bajas exclusivamente demo — 8 de octubre de 2026

## Resultado

Emisión individual de una boleta y una factura, seguida de sus bajas por RC y
RA, comprobada contra Smart PSE demo con CDR código 0. El worker del candidato
terminó los dos trabajos como `succeeded` y los documentos locales como
`anulada`. Una ejecución posterior de los trabajos terminados no volvió a
enviar, firmar ni consultar fiscalmente esos documentos.

El usuario autorizó expresamente estas pruebas únicamente en demo. La empresa
688, RUC `20610027351`, se verificó activa y en `environment=demo` antes de
iniciar, inmediatamente antes de cada envío y después de finalizar. No se
cambió su ambiente ni se utilizó la empresa productiva 384.

## Registro de series

| Empresa del proveedor | Ambiente | Tipo | Serie exclusiva | Número usado | Siguiente número disponible |
| --- | --- | --- | --- | --- | --- |
| 688 | demo | 03, boleta | `BBAJ` | 1 | 2 |
| 688 | demo | 01, factura de control | `FBAJ` | 1 | 2 |

Las dos series estaban vacías antes de la prueba. Son un registro de uso en
Smart PSE demo y en una base local aislada; no se agregaron a la configuración
ni a los correlativos productivos de Inkora. `BBAJ` es la serie dedicada a
pruebas de boleta. `FBAJ` permite contrastar la baja de factura del mismo worker.

Reglas para continuar:

- Usar exclusivamente la empresa 688 verificada en demo y un runtime aislado
  con `FISCAL_ENV=beta`. Verificar además el ambiente del proveedor antes de enviar.
- No usar estas series en producción, ni alternar temporalmente el ambiente de
  una empresa productiva para probarlas.
- No reiniciar a 1 ni reutilizar documentos o lotes ya enviados. El número 2
  es el siguiente disponible, no una emisión pendiente ni programada.
- Mantener registro de cada documento, lote, ticket, intento y CDR. Antes de
  reservar otro número, contrastar este registro con el listado del proveedor.
- Una pérdida de respuesta después de intentar el envío exige consultar el mismo
  lote; no repetir el POST ni crear otro lote para la misma baja incierta.
- Las notas requieren documentar su propia serie y referencia antes de probarlas.
  Esta prueba externa no emitió notas de crédito ni débito.

## Identidades y resultados externos

| Operación | Nombre exacto | ID Smart PSE | Ticket | Resultado |
| --- | --- | --- | --- | --- |
| Boleta individual | `20610027351-03-BBAJ-00000001` | 454000 | — | CDR 0 |
| Baja de boleta | `20610027351-RC-20261008-00001` | 454001 | `1791474755053` | CDR 0 |
| Factura individual | `20610027351-01-FBAJ-00000001` | 454002 | — | CDR 0 |
| Baja de factura | `20610027351-RA-20261008-00001` | 454003 | `1791474797692` | CDR 0 |

Los lotes RC/RA tienen su propio correlativo diario; no son series de venta.
Se comprobaron `ReferenceID`, `DocumentReference/ID`, código 0 y RUC receptor
del CDR contra la identidad congelada. El panel confirmó los lotes aceptados,
en demo y con CDR disponible después de las consultas.

Se realizaron exactamente cuatro POST fiscales a `/api/cpe/procesar-demo`:
dos comprobantes individuales y dos lotes. El contador de firmas pasó de 3 a 7.
Las consultas, la recuperación del worker y la repetición posterior mantuvieron
ese contador en 7. No hubo reenvío de lotes, POST fiscal productivo, escritura
en bases remotas ni cambio de configuración de Inkora/Railway/Smart PSE.

## Hallazgo real y corrección del candidato

La consulta documentada por nombre de archivo devolvía HTTP 404 para ambos
lotes demo existentes. Consultar el ticket numérico también devolvió 404.
Al enviar `GET /api/cpe/consultar/{nombre_archivo}` con cuerpo JSON
`{"environment":"demo"}`, el proveedor respondió HTTP 200, `Procesado`, con
CDR de aceptación que correspondía al lote. Esto es evidencia observada del
contrato demo, no una deducción de que 404 autoriza reenviar.

El worker ahora incluye ese cuerpo únicamente al consultar bajas en demo.
Producción conserva su consulta actual. Se reprodujeron dos fallos locales
antes del cambio; cuatro casos RC/RA × demo/producción cubren la selección del
ambiente y un solo envío por lote. La regresión focalizada completa terminó
con **90 pruebas aprobadas**.

La recuperación real utilizó los mismos jobs y la misma SQLite persistente:
job local 1, boleta BBAJ-1, tres ejecuciones; job local 2, factura FBAJ-1, dos
ejecuciones. Las ejecuciones adicionales consultaron; no generaron nuevos
documentos ni lotes. La repetición después de `succeeded` no realizó llamadas
fiscales ni incrementó los intentos.

## Aislamiento y límites

La base SQLite contiene documentos y usuarios sintéticos. Las credenciales
reales se obtuvieron en memoria, sin guardarlas en SQLite, archivos o logs.
El transporte restringió host HTTPS, empresa, ambiente, identidades y rutas;
bloqueó redirects, reintentos HTTP y cualquier POST fiscal sin sufijo demo.
Los marcadores exclusivos se persistieron con `fsync` antes de cada POST.
Las lecturas de variables de Railway no ejecutaron ni modificaron sus servicios.

La emisión individual se probó mediante el servicio compartido de facturación
y las bajas mediante la cola y el worker reales del candidato, ejecutados
localmente. No fue una prueba desde el navegador ni un despliegue de staging.
No se ejercitó inventario real en los documentos externos: la reversión de stock,
las notas, los rechazos y la concurrencia conservan sus pruebas locales aisladas.

Los CDR demo recibidos contienen placeholders de certificado/firma beta;
no acreditan aceptación productiva ni una firma SUNAT productiva verificable.
Esta homologación demo acotada no sustituye la puerta de staging aislado de
`AGENTS.md` antes de publicar el cambio fiscal/de inventario.

## Evidencia conservada

Worktree: `codex/boletas-bajas-auto`, desde main remoto
`210ac3f7fe57675545e42e93d193c3fc634abf83`; candidato base
`7da1631df7e0f6acbb596cafc1d90a5da570f4cb` más la corrección demo descrita.
La raíz histórica no se utilizó para implementar ni publicar.

Artefactos locales, excluidos de Git, bajo `pruebas/demo-bajas-20261008/`:
`first-attempt.json`, `before-demo-consult-fix.json`, `worker-accepted.json`,
`result.json`, `consult-contract.json`, `consult-contract-environment.json`,
`idempotence.log`, `provider-postcheck.log`, SQLite aislada, XML de lotes,
CDR de documentos/lotes y cuatro marcadores `.send.marker`.
Harnesses locales: `pruebas/demo_bajas_20261008.py` y
`pruebas/demo_bajas_consult_probe.py`. Regresión: `pruebas/demo-void-regression.log`.

SHA256 de los CDR conservados:

| Identidad | SHA256 |
| --- | --- |
| BBAJ-1 | `b6b97e56718a5c2987bfb9707f986fc7c06454b1c0a2f961f8ca4425cd4ea421` |
| RC-20261008-00001 | `f00bbcbb1c63f5989bcfc86241caf44dfc01822bdf1551f1cce3dc1a6ba1cdcb` |
| FBAJ-1 | `5f8ed155c2e9a8e21305bf468113350b04f4674e462762f8d5a27d7c3a925ae6` |
| RA-20261008-00001 | `0d6624faf1b78d2b095621cfb1a2b5b32571cdeeb428df139526802587a9270f` |

Contrato público contrastado: [documentación de Smart PSE](https://smartpse.pe/documentacion).
El cuerpo `environment=demo` para consultas RC/RA se confirmó mediante la
prueba, aunque ese requisito no aparece en el ejemplo público de resúmenes.
