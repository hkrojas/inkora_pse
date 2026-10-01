# Integración de recuperación fiscal y QR GRE

## Alcance autorizado

El usuario solicitó integrar la corrección del QR de guías con la recuperación
fiscal y desplegar, comprobando el funcionamiento. Se integra en
`codex/fiscal-contingency-recovery`, desde `inkora_pse/main` en
`acc2730cd0ba2186c44ac5c0af18d3022149937a`. Se preserva la raíz histórica.

Se revisaron y aplicaron exclusivamente cinco archivos de `codex/gre-cdr-qr`:
`guide_pdf_service.py`, `gre_qr_service.py`, `test_guide_pdf_service.py`,
`test_gre_qr_service.py` y `GRE_QR_CDR_2026-10-01.md`. Ambas ramas parten del mismo
commit; los archivos del QR no se solapan con el cambio previo de facturas.

Los informes `FISCAL_CONTINGENCY_RECOVERY.md` y `GRE_QR_CDR_2026-10-01.md`
documentan las verificaciones individuales previas. Este bloque autoriza
registrar los commits necesarios para el candidato y el empaquetado canónico;
la integración no introduce emisión o reenvío de guías.

## Producción anterior registrada

Comprobación del 01/10/2026 mediante lectura:

- Railway proyecto `truthful-flexibility`, ID `a0e3fddd-4e31-48ee-ac32-89bc295249c4`.
- Ambiente production `c5f4f5f8-c12b-417d-b0e3-a551464552ad`.
- API servicio `37eb9bee-4140-45e6-a518-e082d09589e9`, despliegue SUCCESS
  `0ba3789d-a332-49c0-9bd4-c5ad9967d17a`.
- Worker servicio `17a2668a-d2dc-4f77-a13e-b651ba1adbe5`, despliegue SUCCESS
  `586b94dc-81eb-4769-be03-e7686eb12537`.
- API y frontend comparten base `fa6308fcb2de3ed6af31c23abcd01387e2e7a550`
  y huella `e0d499040a1208305fa297b98955c2cd70198f62dcd085df6baad7433b7edd83`.
- El árbol de `main` coincide con esa base publicada.
- Railway solo declara el ambiente production. No existe staging de Inkora en
  ese proyecto. El proyecto Supabase accesible por el conector corresponde a
  otro producto y no sirve como staging de Inkora.

## Validación y publicación

La validación conjunta utiliza un venv nuevo de Python 3.11.15 con
`requirements-lock.txt` y `requirements-test.txt`, tres bases PostgreSQL 17
locales desechables y la suite canónica. HTTP externo al proveedor queda
bloqueado durante las pruebas locales; el navegador usa la API local aislada.

La autorización para desplegar está recibida. Queda pendiente resolver la
condición de staging aislado de AGENTS.md, regla 12, y la homologación de los
endpoints separados de firma/envío de Smart PSE. Ningún resultado simulado
acredita esa homologación. El flujo nuevo conserva el enrolamiento por empresa
desactivado por defecto.

Conservar los despliegues anteriores para rollback de aplicación, sin restaurar
documentos o correlativos. Los trabajos del nuevo flujo requieren drenaje o
retención antes de volver al worker anterior, como detalla el informe fiscal.
