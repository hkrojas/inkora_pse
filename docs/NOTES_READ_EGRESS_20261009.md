# Optimización del listado de notas — 9 de octubre de 2026

## Alcance

Bloque adicional autorizado con «Continua», posterior a las optimizaciones de
guías, cotizaciones y Excel mensual. Se limita a `GET /notas/page` en la rama
`codex/postgres-read-egress`, sobre la base
`0298d26ec08ccaec4bbabfacab788b8c1aed7b2e`.

- `backend/routers/facturacion.py`: una consulta agregada de conteos y una de página.
- `backend/crud/_note_list_read.py`: proyección de campos del contrato público y
  construcción de la respuesta sin entidades ni relaciones cargadas automáticamente.
- `backend/test_note_list_read.py`: equivalencia, aislamiento y presupuesto de consultas.
- `scripts/benchmark_note_list.py`: comparación reproducible con el código base.

Las ocho consultas propias del listado se reducen a dos, incluyendo la
serialización. Autenticación y dependencias se contabilizan aparte. La subconsulta
que selecciona los IDs de la página forma parte del segundo SQL: no agrega un
viaje a PostgreSQL. Limita los joins y la verificación de XML a las filas solicitadas.

Se conservan filtros, pestañas, estados, orden descendente, 15 elementos por
defecto, máximo 100 y contrato `{items, total, skip, limit, counts}`. Cliente,
cotización origen y comprobante referenciado se unen también por empresa. Las
referencias corruptas que apunten a otra empresa devuelven relaciones nulas.

XML, CDR, QR y respuesta completa del proveedor no viajan en los resultados SQL.
PostgreSQL sí lee el contenido necesario para calcular los indicadores. La regla
de disponibilidad del XML conserva la comparación exacta de SHA-256, junto con
la compatibilidad existente para documentos aceptados con CDR. No se sustituye
por una simple comprobación de existencia del hash.

No se modifican emisión, correlativos, reintentos, pagos, detalle, descarga,
listado simple legacy, worker, frontend, Storage ni esquema de datos.

## Pruebas

- **75 pruebas SQLite aprobadas**, incluyendo las 19 nuevas y 56 de regresión:
  notas, páginas fiscales, acciones/recuperación, aislamiento tenant y contratos
  operativos del frontend.
- **19 pruebas aprobadas sobre PostgreSQL 17 local**, en un esquema aislado de la
  base desechable `inkora_read_egress`.
- Comparación completa del JSON anterior y nuevo: pestañas, páginas vacías/finales,
  XML Unicode, hash válido e inválido, valores vacíos/nulos, contenido y URLs,
  rechazo, anulación y pendiente de confirmación.
- Pruebas HTTP: filtros, límites, errores de fecha y dos SELECT incluso durante
  la serialización. Prueba adicional de referencias hacia otra empresa.
- Benchmark: igualdad completa para páginas de 15 y 100 notas.

Comandos desde `backend` con el entorno Python de pruebas:

```powershell
python -m pytest test_note_list_read.py test_notes_v2.py test_fiscal_page_endpoints.py test_document_actions_consistency.py test_document_actions_recovery.py test_tenant_access_hardening.py test_operational_frontend_contracts.py test_pagination_read_pages.py -q
$env:INKORA_READ_POSTGRES_URL='postgresql://postgres@127.0.0.1:55433/inkora_read_egress'
python -m pytest test_note_list_read.py -q
```

## Medición local

100 notas sintéticas con XML de 100 KB UTF-8, CDR de 50 KB, QR de 50 KB y respuesta
del proveedor de aproximadamente 50 KB, además de sus referencias. Son datos
deliberadamente pesados: no representan el tamaño medio medido en producción.
Tres repeticiones locales, sin red hacia Supabase ni documentos reales.

| Página | Consultas antes → después | Bytes de valores SQL antes → después | Mediana de aplicación antes → después |
|---|---:|---:|---:|
| 15 notas | 8 → 2 | 11.262.947 → 6.539 | 64,7 → 53,1 ms |
| 100 notas | 8 → 2 | 75.086.201 → 43.498 | 372,9 → 116,1 ms |

El tamaño de valores devueltos baja más del 99,9 % en esta prueba. No es una
estimación del ahorro mensual de Supabase ni una medición de bytes facturables.
La medición de aplicación incluye consulta, transferencia local y serialización.

**Coste a observar:** la ejecución dentro de PostgreSQL subió de 2,2 a 13,3 ms
para 15 notas y de 2,8 a 71,8 ms para 100. El cálculo del hash y de indicadores se
realiza ahora en PostgreSQL; se ahorra transferencia a cambio de trabajo local
en la base. `EXPLAIN ANALYZE` no incluye toda la transferencia/serialización del
resultado. No se promete reducción de CPU. Las duraciones locales varían y no
constituyen un SLA productivo.

La primera versión de la consulta evaluaba las expresiones antes de paginar.
Se corrigió antes de la entrega: el plan de la página de 15 termina con 15 filas
y aplica el límite de IDs antes de proyectar contenido y referencias. Los planes
y cifras finales están en `NOTES_READ_BENCHMARK_20261009.json`.

Reproducción desde la raíz del worktree:

```powershell
$env:PYTHONPATH='backend;scripts'
python scripts/benchmark_note_list.py --url postgresql://postgres@127.0.0.1:55433/inkora_read_egress
```

El script solo acepta una base local `inkora_read_*`; crea y elimina únicamente
su propio esquema aleatorio.

## Estado de entrega

Implementación local para revisión, sin commit, integración ni despliegue.
Antes de integrar este bloque deberán ejecutarse los controles canónicos sobre
el conjunto final; los controles completos del bloque anterior no certifican
automáticamente este cambio posterior. La publicación necesita autorización
explícita y el procedimiento de `docs/RELEASE_CANONICO.md`.

Tras publicar, verificar el listado sin emitir documentos, observar latencia/CPU
y comparar el egress durante actividad equivalente. El panel tiene retraso y el
consumo incluye otras fuentes. Quedan para bloques posteriores la proyección de
datos de autenticación y el listado de resúmenes diarios.
