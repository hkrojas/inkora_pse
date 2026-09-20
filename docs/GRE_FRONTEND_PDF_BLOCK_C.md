# GRE remitente — cierre del bloque C (frontend y PDF)

Fecha de verificación: 2026-09-18.

## Frontend

- Entrada desde Facturas, Boletas, detalle del comprobante y sección Guías.
- Selector buscable y paginado contra backend para documentos `01` y `03`; conserva compatibilidad con enlaces antiguos `factura_id`.
- Contexto, conciliación y creación usan los endpoints neutrales de comprobantes.
- Formulario dinámico para privado, público con GRE 31, público con vehículo/conductor por acuerdo y M1/L público o privado.
- M1/L exige placa y oculta conductor. Transporte público sin registro no solicita datos ficticios de vehículo/conductor.
- Tipo de documento del conductor, unidad KGM/TNE, observaciones y confirmación auditada del acuerdo.
- Los cambios de escenario limpian datos incompatibles previa confirmación.
- El detalle distingue el escenario y muestra observaciones, identidad del conductor y evidencia del acuerdo.

## PDF

- Identifica correctamente factura o boleta relacionada.
- Presenta el escenario de transporte, fecha de entrega, observaciones y campos condicionales.
- M1/L muestra solo el vehículo y no inventa conductor.
- Conserva marca de agua en borradores/pendientes y QR únicamente cuando existe CDR válido.
- La muestra renderizada se revisó visualmente sin recortes, solapamientos ni campos contradictorios.

## Verificación

- ESLint: aprobado.
- Build Vite de producción: aprobado.
- Pruebas frontend Node: `34 passed`.
- Contratos frontend/backend y dominio focalizado: `17 passed`.
- PDF y Guías focalizado: `21 passed`.
- Playwright aislado: `7 passed`, incluyendo factura, boleta, despacho parcial,
  privado, público con GRE 31, M1/L sin conductor, evidencia Smart PSE,
  configuración protegida y viewport móvil.
- La tarjeta de evidencia ya no muestra "CDR pendiente" cuando existe CDR;
  comunica que XML firmado y CDR definitivo están disponibles.

La homologación Smart PSE demo y el despliegue permanecen en bloques posteriores. Ninguna llamada fiscal real se ejecutó durante este bloque.
