# Validación local del worker por eventos

Fecha: 2026-09-23. Rama `codex/worker-events-postgres`, desde `c66a3d5`.

## Entorno y límites de la evidencia

- PostgreSQL 17 real, cluster nuevo en loopback, puerto 55439, bases exclusivas y desechables. Ninguna conexión a Supabase/Railway de producción durante implementación o pruebas.
- Windows; regresión completa en el entorno local Python 3.13.3. Verificación adicional de worker/fiscalidad en Python 3.11.15 con `requirements-test.txt` y el lock de producción: 107 paquetes consistentes, comprobados mediante `uv pip check`.
- Todos los proveedores fiscales y artefactos externos de las pruebas están simulados. No se emitieron comprobantes productivos ni consumieron correlativos reales.
- La métrica SQL del benchmark cuenta sentencias de aplicación, no tráfico de red ni cargos Supabase. Su latencia corresponde al entorno local con proveedor simulado y capacidad libre.
- Staging aislado, observación de 24 horas, migración remota y verificación del paquete publicado siguen pendientes. Este informe no acredita preparación para producción.

## Pruebas completadas

| Puerta | Resultado |
|---|---|
| Regresión backend, incluidos contratos operativos y de publicación | 754 aprobadas |
| PostgreSQL GRE, traslados y migración 0024 | 10 aprobadas |
| PostgreSQL cotizaciones e inventario | 2 aprobadas |
| Frontend Node | 48 aprobadas |
| ESLint | aprobado |
| Vite build | aprobado |
| Navegador Chromium, runner local aislado | 59 aprobadas |
| Worker + fiscalidad focalizada en Python 3.11 | 69 aprobadas antes de tres casos adicionales de fencing |
| Suite final del worker en Python 3.11 (incluye éxito fiscal, tenant suspendido, token duplicado, rollback fallido, prioridad del piloto y drenaje inmediato en poll) | 29 aprobadas |

La suite PostgreSQL del worker verifica la migración 0025 (upgrade/downgrade/upgrade preservando trabajos), señales sólo después de commit, silencio al renovar, competencia entre reservas con topes globales/por empresa, reintentos futuros y allowlist, desconexión/reconexión, caídas antes/después de iniciar, fencing y evidencia tardía, ausencia de reservas sobrantes, renovación durante apagado y fallback sin listener.

La suite de configuración rechaza modo incorrecto, límites inválidos, allowlist mal formada, escucha transaccional, TLS remoto desactivado y otra base por nombre. La escucha comprueba adicionalmente la identidad real de la base mediante desafío.

## Benchmark

Ejecución de 30 minutos completada satisfactoriamente; resultado reproducible en `worker-benchmark-local.json` y comando en `WORKER_POSTGRES_EVENTS.md`.

| Medición local (Python 3.13.3, PostgreSQL 17) | Resultado |
|---|---:|
| Ventana real de reposo | 1.800 segundos |
| Patrón anterior, polling cada 2 segundos | 958 sentencias |
| Worker por eventos, todas las empresas habilitadas | 93 sentencias |
| Reducción de sentencias de aplicación | **90,29 %** |
| Carga posterior: 1.000 trabajos, 20 empresas, cuatro procesos | 8,07 segundos |
| Intentos por trabajo sintético | 1 |
| Máximo observado de reservas en curso | 4 |
| p95 de 30 trabajos individuales con cupo disponible | 0,326 segundos |

Se alcanzaron los dos objetivos locales: al menos 90 % menos consultas en reposo y p95 inferior a 2 segundos con capacidad disponible. La comprobación por lectura durante el reposo mostró cero sesiones `idle in transaction` y un listener dedicado. No se extrapola este porcentaje a GB de egress ni a latencia de Smart PSE/SUNAT reales.

Homologación adicional de carga en Python 3.11: `worker-benchmark-python311.json`.

- 1.000 trabajos, 20 empresas, cuatro procesos: 7,05 segundos; un intento por trabajo.
- Máximo observado: cuatro trabajos en curso; las muestras verificaron como máximo uno por empresa. La prueba de reservas concurrentes comprueba adicionalmente esos límites dentro de PostgreSQL.
- 30 pruebas individuales con capacidad disponible: p95 de 0,203 segundos, medido desde antes de insertar hasta confirmar finalización simulada.
- La calibración inicial de 60 segundos registra 32 sentencias previas frente a 6 nuevas, incluyendo arranque y verificación de conexión. No se usa esa ventana corta para acreditar el objetivo de 30 minutos.

## Revisión y entrega

Cambios organizados como migración aditiva, coordinación/ejecución, configuración y pruebas/documentación. Sin cambios de frontend ni contratos de API, cálculo de totales, correlativos o reglas de cobranza.

`RELEASE_CANONICO.md` exige un commit candidato y un árbol de publicación limpio antes de congelar la huella. El paquete que se prepare debe comprobarse en staging con la misma identidad para API, worker y frontend.

Rollback operativo documentado: nuevo ejecutor en `poll`, conservando leases y esquema 0025. No reintroducir un worker antiguo junto con el nuevo.
