# Auditoría de boletas y resumen diario — 5 de octubre de 2026

## Resultado

**Amarillo para la emisión individual de boletas; rojo para considerar el resumen diario un circuito fiscal completo.** Hay una base funcional de emisión individual con verificación de XML/CDR, pero existen defectos reproducibles en el resumen y validaciones incompletas de identidad/plazos. Las pruebas locales no acreditan homologación ni aceptación de boletas reales en producción.

Base revisada: `c0ae8b3bd029d055d4911437393933dc16213990`, main remoto actualizado, PR 36. Worktree limpio `C:/Users/HP/.codex/worktrees/boletas-worker/inkora_smartpse`, rama `codex/boletas-worker`. No se modificó código de aplicación, configuración, cola ni datos productivos. Este documento es el único archivo añadido.

## Explicación simple de la obligación

El resumen diario es un envío que informa boletas y sus notas de una misma fecha. No es otra venta ni otra boleta. La normativa permite informar boletas individualmente en lugar del resumen: para SEE del contribuyente, la RS 114-2019 modifica los artículos 7.3 y 12 de la RS 097-2012. El envío individual tiene un plazo de cinco días calendario contados desde el siguiente al de emisión; vencido ese plazo, corresponde el resumen en su plazo aplicable. El resumen se envía el día de emisión o hasta el séptimo día calendario siguiente. Para SEE-OSE también existe la alternativa individual, con sus condiciones propias.

Por tanto, una boleta correctamente informada individualmente no requiere un resumen adicional para informar esa misma emisión. El resumen sigue siendo relevante cuando se usa el envío agrupado y para la baja de numeración de boletas no otorgadas, según las condiciones y plazos normativos. Para revertir una venta cuya boleta ya se entregó, corresponde evaluar la nota de crédito y su motivo, no una baja indiscriminada.

Fuentes oficiales consultadas:

- [RS 114-2019/SUNAT](https://www.sunat.gob.pe/legislacion/superin/2019/114-2019.pdf): artículos 2.1, 2.3, 2.5, 2.7 y 4.3. Algunas páginas generales de orientación mantienen la descripción tradicional del envío por resumen; la resolución contempla expresamente la alternativa individual.
- [Resumen diario — SUNAT](https://orientacion.sunat.gob.pe/04-resumen-diario-boleta-de-venta-electronica): plazo del resumen.
- [Boleta de venta electrónica — SUNAT](https://cpe.sunat.gob.pe/tipos_de_comprobantes/boleta): identificación del adquirente cuando lo solicita o cuando el total supera S/700, con la excepción normativa indicada para determinados no domiciliados.
- [Catálogo 19 — SUNAT, página 8](https://www.sunat.gob.pe/legislacion/superin/2017/anexosV-318-2017.pdf): 1 adicionar, 2 modificar, 3 anulado.

## Alcance revisado

Se revisaron rutas de emisión/listado/resumen, construcción de XML, normalización de respuesta Smart PSE, persistencia del resumen, acciones del worker, recuperación de leases, validación de clientes, flags fiscales, páginas Boletas/Resumen Diario y aceptación del origen de guías.

El flujo normal de boleta usa XML tipo `03` y el mismo envío individual `/invoice/send` que las facturas. `_enviar_a_smartpse` exige la verificación posterior de XML y CDR para ese envío. La empresa emisora se deriva del usuario; los listados y las modificaciones de resumen se filtran por tenant. Las rutas sensibles tienen permisos de emisor y guard de habilitación/suscripción. El resumen está deshabilitado por defecto mediante `daily_summary`; no se comprobó el valor real de ese flag en cada empresa productiva.

La contingencia nueva y la recuperación por panel documentadas para facturas no se amplían automáticamente a boletas. Estas conservan su flujo anterior de emisión/consulta y las protecciones de recuperación de ejecución incierta.

## Hallazgos

| Prioridad | Hallazgo | Evidencia | Riesgo | Recomendación |
|---|---|---|---|---|
| P1 | El resumen puede marcarse enviado y exitoso sin CDR, o con un CDR que contiene rechazo | `services/smartpse_response.py:266-329` no valida CDR para RC; `crud/resumenes.py:71-106` persiste éxito de transporte. Reproducción SQLite: sin CDR y CDR código 2335 producen `sent`, `success=true`. | Confundir envío con aceptación fiscal; esa marca también es usada como evidencia de origen por `sale_dispatch_service.py:141`. | Verificar identidad y código del CDR del lote; diferenciar recibido, pendiente, aceptado y rechazado. |
| P1 | Los tickets de resumen no tienen un circuito posterior de consulta | `services/facturacion_service.py:2093` envía con `poll_async=False`. Sólo hay rutas GET de listado y POST de envío; no hay acción de resumen en `models/emission_jobs.py`. | Un ticket puede quedarse pendiente indefinidamente dentro de Inkora, aunque el proveedor ya tenga resultado. | Diseñar una consulta persistente de ticket, sin reenviar el resumen para consultar. |
| P1 | El formulario invierte modificar/anular | `frontend/src/pages/ResumenDiarioPage.jsx:24`: 2 = Baja, 3 = Corrección. El XML copia el código a `ConditionCode` en `smartpse_ubl_service.py:443`. Catálogo 19: 2 modificar, 3 anulado. | Una corrección puede solicitar una anulación; una baja puede solicitar modificación. | Corregir etiquetas en un bloque frontend separado y verificar los tres estados. |
| P1 | El resumen admite documentos y montos manuales sin contrastarlos con comprobantes de la empresa | `routers/facturacion.py:1916-1928` construye/persiste directamente el payload. Reproducción: B999-999999 se valida y almacena con cero comprobantes en la base. | Informar una numeración inexistente, montos diferentes o duplicados. La empresa emisora sí deriva del usuario; no se observó una lectura cruzada de tenants en esta ruta. | Construir detalles desde documentos del tenant autenticado y validar fecha, estado, importes, elegibilidad y duplicados. |
| P1 | La prevalidación de boleta no contempla la identificación por importe | `routers/facturacion.py:839-900` exige longitud mínima 8 para todos, sin regla de S/700. Reproducción: cliente genérico tipo 0, número 00000000, total S/800 pasa. | Datos insuficientes en ventas que requieren identificación; también se bloquean documentos extranjeros cortos aunque el schema admite 3-15 caracteres. | Validar por tipo de documento, importe y excepciones aplicables; definir consumidor final de forma explícita. |
| P1 | El XML de resumen no cubre todo lo admitido por el schema | `services/smartpse_ubl_service.py:422-451` sólo escribe operación gravada/IGV; no serializa referencia de notas ni importes exonerados/inafectos admitidos. Reproducción: nota con referencia y exoneración pierde esos campos. | Resúmenes incorrectos o rechazados para notas y operaciones distintas de las gravadas simples. | Limitar explícitamente el contrato soportado o completar XML con pruebas normativas. |
| P1 | No hay cierre automático ni control local del vencimiento para boletas/resúmenes | Resumen manual en `ResumenDiarioPage.jsx:217-238`; `facturacion.py:659` sólo impide fecha futura. El schema de resumen no contrasta antigüedad ni fecha real de sus documentos. | Depender de rechazo del proveedor después de que venció el plazo, sin una ruta de resumen completa para recuperar. | Diseñar alertas y elegibilidad por plazo; automatizar sólo después de definir la estrategia individual/lote con el proveedor. |
| P2 | Fecha diaria del formulario usa UTC y correlativo por segundo | `ResumenDiarioPage.jsx:58-65`; el modelo de resumen no tiene unicidad por empresa/correlativo. | Fecha adelantada respecto de Lima después de las 19:00; colisiones o doble envío manual. | Usar fecha fiscal de Lima y reserva/idempotencia de lote en backend. |

## Cambio mínimo sugerido

Primero cerrar **la aceptación y consulta del resumen** en un bloque backend aislado: CDR verificable, estados explícitos y conciliación de ticket sin duplicar envíos. No habilitar masivamente `daily_summary` mientras estos hallazgos estén abiertos. Esto es una recomendación, no un cambio aplicado al flag productivo.

Después, separar la corrección de etiquetas del frontend y la revisión de identidad/plazos de emisión. No añadir generación automática del cierre diario antes de definir qué boletas requieren lote y confirmar el comportamiento del proveedor. Cualquier modificación del worker debe coordinarse con el chat `Backend`, encargado actual de worker/contingencia y monitoreo; no se enviaron mensajes a ese chat.

## Archivos que tocaría el primer bloque

- `backend/services/smartpse_response.py`: evidencia del CDR de resumen.
- `backend/crud/resumenes.py`: estados y persistencia verificable.
- `backend/routers/facturacion.py`: consulta del resumen con tenant/ownership.
- Pruebas focalizadas del resumen, rechazo, respuesta ambigua y ownership.
- Si se aprueba consulta mediante cola: contrato/modelo/servicio de emission jobs, con revisión previa del responsable del worker. Cambios de esquema, si fueran necesarios, en bloque separado.

## Tests/comandos ejecutados

Desde el backend del worktree, con `ENVIRONMENT=test`, `DATABASE_URL=sqlite://` y clave sintética, usando el intérprete existente como dependencia:

```powershell
& 'C:/Users/HP/Desktop/inkora_smartpse/backend/venv/Scripts/python.exe' -m pytest -q test_apisperu_documentos_matrix.py test_facturacion_comprobante_builder.py test_facturacion_guards.py test_fiscal_submission_leases.py test_smartpse_response_normalization.py test_emission_queue.py test_beta_feature_flags.py test_apisperu_payload_contracts.py
```

Resultado: **160 passed in 35.53s**. Proveedor simulado y SQLite aislada. Además se ejecutaron las cinco reproducciones descritas, mediante Python por entrada estándar, sin archivos de implementación ni servicios externos. Todas confirmaron los comportamientos indicados. Las pruebas existentes pasan porque no cubren esos casos de resumen.

No se ejecutó emisión SUNAT/Smart PSE, consultas fiscales pagadas, migraciones, cambios de variables, reencolados ni despliegues. No se auditó cada boleta histórica productiva, no se recorrió el navegador en esta revisión y no se hicieron pruebas PostgreSQL de concurrencia. No se declara el módulo completo listo para producción.

## Recomendación

Mantener la emisión individual como estrategia a verificar con evidencia fiscal real ya existente, y corregir primero el circuito de resumen antes de depender de él para cumplimiento, bajas o recuperación de boletas vencidas. No implementar en este pedido de auditoría.
