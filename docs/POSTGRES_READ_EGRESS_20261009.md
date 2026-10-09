# Optimización de lecturas PostgreSQL — 9 de octubre de 2026

## Alcance y base

Rama `codex/postgres-read-egress`, creada en un worktree limpio desde
`0298d26ec08ccaec4bbabfacab788b8c1aed7b2e`, identidad productiva verificada al iniciar.
Se implementaron secuencialmente los tres bloques aprobados. La raíz histórica y
el worktree pendiente de PDFs se conservaron separados.

Cambios exclusivamente de backend: sin migraciones, cambios de Storage, frontend,
worker, correlativos, proveedores fiscales ni escrituras productivas.

## Cambios revisables

1. **Guías:** `crud/guias.py`. Una agregación para todas las pestañas y una
   proyección de los campos de `GuiaRemisionListResponse`. Cliente directo o de la
   cotización, sin cargar las entidades completas. Ocho consultas propias pasan a dos.
2. **Cotizaciones:** `crud/_quote_list_read.py`, `_cotizaciones_quotes.py` y
   `_cotizaciones_shared.py`. Selección escalar, cliente conforme al contrato,
   último documento derivado elegible mediante subconsulta correlacionada.
   Indicadores XML/CDR/aceptación calculados en SQL; numeración y estado de pago
   reutilizan las propiedades existentes sobre un objeto sin relaciones ORM.
   Listado simple: una consulta; paginado: dos. El detalle conserva su carga completa.
3. **Excel mensual:** `crud/reportes.py` y `routers/reportes.py`. Se reutilizan las
   agregaciones existentes de cobranza para obtener pagos y saldo neto en lote;
   cabecera de empresa limitada a nombre y RUC. Dos consultas propias sin importar
   el número de comprobantes. El servicio fiscal que valida pagos/notas no cambia.

Se conservan contratos, filtros, roles, paginación y botones/descargas existentes.
Por defecto se mantienen 15 elementos; máximo HTTP de cotizaciones 50 y de guías
100. La medición interna de cotizaciones con 100 filas no amplía el máximo HTTP.
Se añade tenant a los joins del cliente y del documento derivado: referencias
históricas mal formadas hacia otra empresa no revelan su información.

El Excel conserva `fecha_emision ASC`. Como en la consulta anterior, dos filas con
idéntica fecha/hora no tienen un desempate contractual. La comparación inicial con
100 timestamps idénticos detectó únicamente ese orden indeterminado; la medición
final usa timestamps distintos y verifica igualdad completa de las filas.

## Medición reproducible en PostgreSQL 17 local

100 cotizaciones, 100 facturas y 100 guías sintéticas. Los documentos contienen
campos pesados de 50 KB para hacer visible la transferencia innecesaria. Se comparó
el código de la revisión base contra el nuevo código sobre los mismos datos.
Resultados detallados en `POSTGRES_READ_EGRESS_BENCHMARK_20261009.json`.

| Operación | Consultas antes → después | Bytes de valores SQL antes → después | Mediana local antes → después |
|---|---:|---:|---:|
| Guías, 15 filas | 8 → 2 | 4.505.536 → 1.993 | 35,5 → 15,2 ms |
| Cotizaciones, 15 filas | 2 → 2 | 6.009.875 → 2.735 | 27,9 → 19,9 ms |
| Guías, 100 filas | 8 → 2 | 30.036.679 → 13.140 | 123,8 → 17,9 ms |
| Cotizaciones, 100 filas | 2 → 2 | 40.065.624 → 18.079 | 120,7 → 17,8 ms |
| Excel, 100 facturas | 502 → 2 | 40.037.693 → 11.864 | 946,2 → 139,4 ms |

Los bytes suman valores SQL decodificados, incluidas repeticiones causadas por
joins. No incluyen protocolo/TLS ni equivalen a GB facturados por Supabase. Los
tiempos son locales, tres repeticiones con caché, en una máquina compartida con
otras pruebas; no son un SLA. Los tiempos variaron entre ejecuciones (en una
anterior la página de 15 cotizaciones tuvo latencia similar antes/después),
mientras que los conteos y bytes de los resultados permanecieron iguales.
No se promete una reducción porcentual mensual ni una reducción universal de CPU.

Reproducción (solo admite host local y base desechable `inkora_read_*`):

```powershell
python scripts/benchmark_read_egress.py --url postgresql://postgres@127.0.0.1:55433/inkora_read_egress
$env:INKORA_READ_POSTGRES_URL = 'postgresql://postgres@127.0.0.1:55433/inkora_read_egress'
python -m pytest backend/test_read_egress.py -q
```

El benchmark y las pruebas PostgreSQL crean y eliminan exclusivamente un esquema
aleatorio propio; no consultan tablas de negocio del esquema público.

## Validación

- Guías: 43 pruebas iniciales de CRUD/router/equivalencia aprobadas.
- Cotizaciones: 18 pruebas existentes aprobadas y comparación de respuestas,
  contenidos/URLs vacíos o nulos, aceptación y selección de documento derivado.
- Reportes: 18 pruebas existentes aprobadas y Excel completo comparado celda a
  celda, incluidos importes, formatos y estilos.
- Pruebas nuevas: cubren presupuestos SQL durante serialización, roles,
  aislamiento, referencias cruzadas mal formadas, páginas vacías/finales,
  cliente heredado de cotización, pagos primarios/legacy, adelantos excluidos,
  notas rechazadas y de otros meses, límites de diciembre y precisión decimal.
- Batería final focalizada SQLite: **46 aprobadas** (28 nuevas + 18 cotizaciones).
- PostgreSQL real: **28 pruebas nuevas aprobadas** sobre esquemas sintéticos aislados.
- Procedimiento canónico: **1.605 pruebas backend**, **77 PostgreSQL** (10 GRE,
  2 cotizaciones/inventario, 59 worker/reintentos, 6 resumen), **65 frontend**,
  lint y build aprobados. **197 E2E aprobados** (27,1 minutos), incluida la
  navegación local real por cotizaciones/guías y las matrices de interfaz con API
  simulada. Ninguna de estas pruebas constituye homologación fiscal productiva.
- `git diff --check`: aprobado.
- Puerta final `release_guard.py check`: **bloqueada por cambios publicables sin
  commit**. El script canónico terminó con código 1 por esta condición; no se
  declara aprobado el paquete de publicación. No fallaron las suites anteriores.

Evidencia local: `read-egress-verification.log`, `read-egress-postgres-final.log`
y `read-egress-final-contracts.log`, en la raíz de este worktree (logs ignorados
por Git). La regresión general se inició antes de añadir tres casos de límites
mensuales, incluidos en las baterías focalizadas finales.
La simplificación final del COUNT de cotizaciones quedó cubierta por las 46
pruebas focalizadas, las 28 PostgreSQL y la medición final. Los servicios locales
de E2E se cerraron mediante el runner; PostgreSQL local quedó detenido como estaba
al iniciar, tras comprobar que no había otras conexiones.

## Entrega y publicación

Estado: implementación local, sin commit, integración ni despliegue.
La skill `inkora-p1-operator` exige dejar los cambios revisables sin hacer commits.
El procedimiento canónico requiere un commit candidato limpio para generar el
paquete; por tanto esa puerta queda para la fase de integración autorizada.

Antes de producción: revisión del diff, reconciliar nuevamente main/producción,
staging aislado para la lectura de saldos, aprobación de integración/publicación,
paquete canónico con una misma huella de API/worker/frontend y rollback de aplicación.
No se requiere rollback de datos ni migración.

Después de publicar: verificar identidad/salud API y worker; abrir guías y
cotizaciones con filtros y páginas; descargar Excel y comparar importes. No es
necesario emitir documentos reales. Comparar egress en periodos con actividad
semejante, considerando retraso del panel y otras fuentes de consumo. El consumo
acumulado del mes no disminuye retroactivamente.
