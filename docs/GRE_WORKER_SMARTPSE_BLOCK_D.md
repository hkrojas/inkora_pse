# GRE remitente — Bloque D: worker y contrato Smart PSE

Fecha de verificación: 18/09/2026.

## Resultado

El circuito técnico queda preparado para enviar y conciliar GRE 09/31 sin
interpretar un HTTP 200, XML firmado o ticket como aceptación fiscal.

- La emisión usa `/api/cpe/procesar` o `/api/cpe/procesar-demo` según el ambiente
  congelado del documento.
- La consulta usa `GET /api/cpe/consultar/{nombre_archivo}` y nunca reenvía la
  GRE por la ruta de emisión.
- Cuando están configuradas, se envían `sol_user`, `sol_password`,
  `client_id_sunat`, `client_secret_sunat` y el `environment` correspondiente.
- Una respuesta con ticket y sin CDR conserva XML firmado, hash, respuesta y
  ticket, deja guía y trabajo en estado pendiente y mantiene la reserva activa.
- Solo un CDR válido, correspondiente al documento y con resultado aceptado,
  permite convertir la reserva en cobertura.
- Un resultado ambiguo, timeout o agotamiento de consultas no libera cantidades
  ni habilita un reenvío automático.

## Correcciones realizadas

1. La normalización reconoce el ticket sin CDR como resultado pendiente. Una
   respuesta aparentemente exitosa sin CDR ni indicador de espera sigue siendo
   inválida.
2. El ambiente se incluye con las credenciales GRE para evitar que Smart PSE
   resuelva implícitamente un ambiente distinto al congelado.
3. El worker conserva el ticket y el resumen del proveedor también en el
   trabajo `pending_confirmation`, no solo en la guía.
4. Se agregó una prueba del worker que demuestra que el resultado pendiente no
   ejecuta la transición de reserva a cantidad cubierta.

## Evidencia de pruebas

- Normalización, cliente, backend GRE, worker y dominio de despachos: 60 pruebas
  aprobadas.
- Cola, normalización y backend GRE después de la corrección de trazabilidad:
  39 pruebas aprobadas.
- Regresión backend completa: 541 aprobadas, 5 omitidas explícitamente y 12
  advertencias de deprecación FastAPI ya conocidas.
- Frontend: ESLint aprobado, 34 pruebas Node aprobadas y build Vite de producción
  generado correctamente. Permanecen avisos no bloqueantes por dos fuentes que
  se resuelven en runtime y la base Browserslist desactualizada.
- Playwright aislado con API y proveedor simulados: 7 escenarios aprobados para
  factura/boleta, matriz de transporte, emisión visual, credenciales y mobile.
- Alembic declara `0022_gre_sales_documents` como única revisión `head`.

Todas estas pruebas utilizan proveedor simulado. No se realizó ninguna llamada
a Smart PSE ni se cambió el ambiente de Papelería Gráfica.

## Contrato confirmado en documentación pública

- Autenticación CPE mediante `POST /api/auth/cpe/token`.
- Procesamiento en `/api/cpe/procesar` y variante demo
  `/api/cpe/procesar-demo`.
- Consulta por nombre de archivo en `/api/cpe/consultar/{nombre_archivo}`.
- Nombres GRE 09 y 31 con el RUC y la serie/número del documento.
- Las GRE requieren las cuatro credenciales SOL/OAuth en la solicitud.
- Un resultado pendiente debe consultarse hasta obtener resultado definitivo.

Fuente: https://smartpse.pe/documentacion

SUNAT exige obtener el CDR aceptado antes del inicio del traslado:
https://cpe.sunat.gob.pe/node/116

## Requiere confirmación de Smart PSE

- La ubicación exacta de las cuatro credenciales en la petición GET de consulta;
  Inkora usa cuerpo JSON porque la página pública no publica un ejemplo completo
  y así evita secretos en la URL.
- La documentación pública contiene mensajes contradictorios sobre si las
  credenciales GRE son opcionales en demo. Producción permanece estricta.
- La capacidad real del ambiente demo para producir una aceptación y un CDR de
  GRE. El fallo habitual reportado por el usuario no se contabiliza como prueba
  aprobada ni como rechazo fiscal real.

## Límite operativo

Este bloque valida el circuito técnico, no una homologación real. No se debe
habilitar un piloto productivo hasta contar con evidencia del proveedor o una
autorización separada para probar un traslado real. No existe fallback automático
a SUNAT directo ni a APISPeru.
