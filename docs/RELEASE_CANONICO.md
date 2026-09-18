# Entregas de Inkora: fuente única y control de regresiones

## Causa del incidente

La corrección de series se publicó desde un árbol divergente. El commit no identificaba los cambios locales: se enviaron archivos anteriores de interfaz y API junto con el arreglo. `_release_guides_prod` contenía funcionalidades recuperables, pero también versiones anteriores a los controles actuales de GRE, contingencia y paginación. Ni copiar esa carpeta completa ni publicar la raíz sin comparar resolvía el problema.

La única fuente para nuevas entregas es la raíz que contiene este documento, `backend`, `frontend`, `contracts` y `scripts`. Las carpetas `_release_*`, `_push_*`, `tmp`, fixtures, copias y respaldos nunca son fuentes de publicación.

## Puertas obligatorias

1. Registrar `git rev-parse HEAD`, estado local y alcance. No hacer reset, clean ni descartar cambios ajenos. Un commit solo NO acredita qué se publicó.
2. Comparar funcionalidad y contratos contra `contracts/operational_routes.json`. Incluye método y ruta; cambiar PUT por PATCH no es compatible por tener un nombre parecido. `backend/test_release_guard.py` falla si desaparece cualquier contrato aprobado.
3. Revisar cambios de `contracts/release_assets.json`: favicon y fuentes están fijados por SHA256. Una actualización intencional exige evidencia visual y revisión, no regeneración ciega del baseline.
4. Ejecutar `./scripts/verify_recovery.ps1 -RequirePostgres`. Las variables `INKORA_GRE_POSTGRES_URL` y `INKORA_QUOTE_POSTGRES_URL` deben identificar dos bases **locales, exclusivas y desechables**, con prefijos `inkora_gre_` e `inkora_quote_`. Sus fixtures eliminan tablas exclusivamente en esas bases. Nunca usar producción/staging de usuarios. El modo sin PostgreSQL sirve para desarrollo, NO para aprobar concurrencia.
5. Revisar navegador con datos sintéticos, controles, permisos, PDF y errores de consola. No usar comprobantes reales para probar escritura, baja o reenvío.
6. Verificar esquema remoto y Storage mediante lectura. No ejecutar migraciones por rutina: esta recuperación reutiliza tablas/columnas ya existentes. Si falta algo, detener publicación y preparar un bloque de migración separado.
7. Ejecutar `backend/venv/Scripts/python.exe scripts/release_guard.py check`. Revisar la huella y preparar un destino NUEVO bajo `tmp` mediante `package --approved-sha256 <huella> --destination tmp/<entrega>`. El empaquetador incluye solo archivos de aplicación, excluye credenciales, auxiliares y fixtures, y comprueba backend/frontend de la misma entrega.
   - Los manifiestos nuevos declaran `hash_mode: canonical-text-v1`. Los archivos UTF-8 se identifican después de normalizar CRLF/CR a LF; los binarios continúan comparándose byte por byte. Así, un checkout Windows y uno Linux producen la misma identidad lógica sin ocultar cambios de contenido.
   - Los manifiestos históricos que no incluyen `hash_mode` se verifican como `raw-v1`, preservando su huella original. No editar un manifiesto antiguo para convertirlo al formato nuevo.
8. Ejecutar `verify --destination tmp/<entrega>` inmediatamente antes de cada publicación. No modificar ese paquete; cualquier cambio obliga a otra huella y otra validación. No utilizar scripts históricos de empaquetado con listas parciales.
9. Publicar API compatible y worker desde el mismo contenido; verificar arranque, OpenAPI y salud. **La API compila desde raíz con Dockerfile; el worker mantiene rootDirectory=backend y RAILPACK.** Para el worker ejecutar `project_worker_release.py <paquete> tmp/<proyeccion-worker>`: verifica el manifiesto y copia únicamente backend, con hashes idénticos y el mismo release.json. No enviar el Dockerfile de raíz al contexto backend (COPY backend fallaría). Publicar frontend desde el paquete completo primero sin promoción automática y promoverlo cuando esté READY. No modificar variables fiscales como parte del deploy.
10. Comparar `/health.delivery.content_sha256` del API con `/release.json` del frontend y con el manifiesto. Registrar IDs Railway API/worker y Vercel, hora, huella, revisión y resultados. La vieja variable `INKORA_RELEASE_ID` puede estar obsoleta: no sustituye la huella del contenido.
11. Validar en producción por lectura: cotizaciones, facturas, boletas, inventario, configuración, acciones y descargas autenticadas. Las acciones visibles no autorizan pruebas de emisión real. Revisión acotada de logs debe indicarse como tal, no como observación de 24 horas.

## Rollback

Guardar los IDs de la entrega anterior antes de promover. Revertir aplicación mediante los despliegues anteriores compatibles, nunca restaurar correlativos, facturas, inventario ni CDR para deshacer un deploy. Un rollback de datos no revierte documentos aceptados por SUNAT. Si API y frontend dejan de ser compatibles, detener promoción; no ocultar controles para disimular rutas ausentes.

## Límites del control

Las pruebas de contratos detectan pérdidas de rutas, no demuestran por sí mismas su comportamiento. Las huellas demuestran identidad, no ausencia de bugs. Por eso se necesitan pruebas de dominio, seguridad, PostgreSQL y navegador. No hay homologación fiscal real si solo se usaron respuestas simuladas. La automatización no impide que un operador la omita: el procedimiento de publicación debe exigir estas puertas y revisar cualquier modificación a sus baselines.

Los recibos de idempotencia de carga masiva se conservan en auditoría (`inventory_bulk`): no purgarlos como logs descartables, pues previenen aplicar de nuevo una operación repetida.

El baseline de producción comprende 223 operaciones. No incluye cinco contratos disponibles exclusivamente en modo local/test (PATCH/DELETE users e invocaciones fiscales `*-legacy`); exigirlos en producción sería reactivar rutas deliberadamente retiradas. Los tests de `test_legacy_frozen_gating.py` verifican esa separación.
