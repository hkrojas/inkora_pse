# GRE remitente — cierre del bloque B (backend y XML)

Fecha de verificación: 2026-09-18.

## Alcance implementado

- Origen neutral para facturas `01` y boletas `03`, conservando los endpoints de factura como adaptadores restringidos a `01`.
- Evidencia persistente de aceptación del origen y vínculo con resumen diario cuando la boleta fue aceptada mediante resumen.
- Endpoints neutrales de contexto, guías vinculadas, conciliación histórica y creación desde comprobante.
- Matriz única de transporte para privado, público con GRE 31, público con vehículo/conductor acordados y M1/L público o privado.
- La excepción pública con vehículo/conductor auditados ya no exige GRE 31 al confirmar salida.
- M1/L conserva placa y fecha en el payload/XML y no exige conductor.
- Referencia XML `03` con denominación `BOLETA DE VENTA`.
- Tipo de documento del conductor validado contra los códigos admitidos del catálogo 06 para este alcance.
- Observaciones y fechas GRE normalizadas al horario UTC-05:00 de Perú sin depender de `tzdata` del sistema operativo.
- GRE 31 acepta como trazabilidad de bienes una factura `01` o boleta `03`, manteniéndola separada de la GRE 09.

## Verificación

- Suite completa backend: `539 passed, 5 skipped`.
- Concurrencia PostgreSQL real y obligatoria: `4 passed` sobre PostgreSQL 17 aislado.
- Suite focalizada final de Guías, router y Smart PSE simulado: `32 passed`.
- No se llamó a Smart PSE ni se emitieron documentos reales.
- No se modificó frontend en este bloque.

## Pendiente para el siguiente bloque

- Conectar el frontend a los endpoints neutrales y habilitar selección de boletas.
- Aplicar la misma matriz dinámica en el formulario, incluida confirmación explícita del acuerdo con el transportista.
- Adaptar el PDF para boleta, observaciones y campos condicionales.
- Ejecutar pruebas de navegador aisladas; la homologación demo de Smart PSE continúa separada y no debe interpretarse como aceptación fiscal real.
