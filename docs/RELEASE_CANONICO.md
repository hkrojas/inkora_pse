# Entregas de Inkora: fuente única y control de regresiones

## Causa del incidente

La corrección de series se publicó desde un árbol divergente. El commit no identificaba los cambios locales: se enviaron archivos anteriores de interfaz y API junto con el arreglo. `_release_guides_prod` contenía funcionalidades recuperables, pero también versiones anteriores a los controles actuales de GRE, contingencia y paginación. Ni copiar esa carpeta completa ni publicar la raíz sin comparar resolvía el problema.

La única fuente para nuevas entregas es la raíz que contiene este documento, `backend`, `frontend`, `contracts` y `scripts`. Las carpetas `_release_*`, `_push_*`, `tmp`, fixtures, copias y respaldos nunca son fuentes de publicación.

## Puertas obligatorias

1. Registrar `git rev-parse HEAD`, estado local y alcance. No hacer reset, clean ni descartar cambios ajenos. Un commit solo NO acredita qué se publicó.
2. Comparar funcionalidad y contratos contra `contracts/operational_routes.json`. Incluye método y ruta; cambiar PUT por PATCH no es compatible por tener un nombre parecido. `backend/test_release_guard.py` falla si desaparece cualquier contrato aprobado.
3. Revisar cambios de `contracts/release_assets.json`: favicon y fuentes están fijados por SHA256. Una actualización intencional exige evidencia visual y revisión, no regeneración ciega del baseline.
4. Ejecutar `./scripts/verify_recovery.ps1 -RequirePostgres -PythonPath <python-del-entorno-de-pruebas>`. Las variables `INKORA_GRE_POSTGRES_URL` y `INKORA_QUOTE_POSTGRES_URL` deben identificar dos bases **locales, exclusivas y desechables**, con prefijos `inkora_gre_` e `inkora_quote_`. Sus fixtures eliminan tablas exclusivamente en esas bases. Nunca usar producción/staging de usuarios. El modo sin PostgreSQL sirve para desarrollo, NO para aprobar concurrencia.
   - La misma verificación ejecuta Playwright mediante `scripts/run_e2e_local.py`: crea una SQLite temporal, una contraseña aleatoria, inicia API y Vite únicamente en `127.0.0.1:8000/5173` y elimina sesión/base al terminar. La configuración no admite URLs remotas ni un bypass de producción.
   - El workflow `release-gate.yml` instala `backend/requirements-test.txt` y Chromium, y ejecuta estas puertas reproducibles sin PostgreSQL en cada PR y push a `main`. La protección de la rama debe exigir que ese check termine correctamente. PostgreSQL real y la revisión visual continúan siendo puertas manuales obligatorias antes de producción.
5. Revisar navegador con datos sintéticos, controles, permisos, PDF y errores de consola. No usar comprobantes reales para probar escritura, baja o reenvío.
6. Verificar esquema remoto y Storage mediante lectura. No ejecutar migraciones por rutina: esta recuperación reutiliza tablas/columnas ya existentes. Si falta algo, detener publicación y preparar un bloque de migración separado.
7. Ejecutar `python scripts/release_guard.py check` desde un commit candidato. El comando se bloquea si cualquier archivo publicable está modificado o sin seguimiento: la revisión registrada nunca vuelve a describir contenido local distinto. Revisar la huella y preparar un destino NUEVO bajo `tmp` mediante `package --approved-sha256 <huella> --destination tmp/<entrega>`. El empaquetador usa una lista positiva de runtime, incluye `requirements-lock.txt` y excluye credenciales, scripts administrativos/destructivos, seeds, pruebas, auxiliares y fixtures.
   - Los manifiestos nuevos declaran `hash_mode: canonical-text-v1`. Los archivos UTF-8 se identifican después de normalizar CRLF/CR a LF; los binarios continúan comparándose byte por byte. Así, un checkout Windows y uno Linux producen la misma identidad lógica sin ocultar cambios de contenido.
   - Los manifiestos históricos que no incluyen `hash_mode` se verifican como `raw-v1`, preservando su huella y contrato originales para rollback. No se les aplican retroactivamente los marcadores funcionales actuales y nunca se debe editar un manifiesto antiguo para convertirlo al formato nuevo.
8. Ejecutar `verify --destination tmp/<entrega>` inmediatamente antes de cada publicación. No modificar ese paquete; cualquier cambio obliga a otra huella y otra validación. No utilizar scripts históricos de empaquetado con listas parciales.
9. Publicar API compatible y worker desde el mismo contenido; verificar arranque, OpenAPI y salud. **La API compila desde raíz; el worker conserva `rootDirectory=backend` y compila mediante el Dockerfile backend incluido en la misma huella.** Para el worker ejecutar `project_worker_release.py <paquete> tmp/<proyeccion-worker>`: verifica el manifiesto, copia únicamente el backend y genera en la raíz del bundle los adaptadores `Dockerfile` y `railway.json` verificados. Publicar ese directorio completo con `railway deployment up ... --path-as-root`; no publicar directamente la subcarpeta `backend`. El start command, ambiente y variables del worker continúan siendo los configurados en Railway. Publicar frontend desde el paquete completo primero sin promoción automática y promoverlo cuando esté READY. No modificar variables fiscales como parte del deploy.
   - Los Dockerfiles de API y worker instalan el mismo `backend/requirements-lock.txt`; por eso resuelven versiones idénticas en Python 3.11. `backend/requirements.txt` se conserva como puente para desarrollo, pero no debe dependerse de la detección Railpack para producción. Las dependencias directas se documentan en `backend/requirements.in` y cualquier actualización exige regenerar y probar el lock.
10. Comparar `/health.delivery.content_sha256` del API con `/release.json` del frontend y con el manifiesto. Registrar IDs Railway API/worker y Vercel, hora, huella, revisión y resultados. La vieja variable `INKORA_RELEASE_ID` puede estar obsoleta: no sustituye la huella del contenido.
11. Validar en producción por lectura: cotizaciones, facturas, boletas, inventario, configuración, acciones y descargas autenticadas. Las acciones visibles no autorizan pruebas de emisión real. Revisión acotada de logs debe indicarse como tal, no como observación de 24 horas.

## Rollback

Guardar los IDs de la entrega anterior antes de promover. Revertir aplicación mediante los despliegues anteriores compatibles, nunca restaurar correlativos, facturas, inventario ni CDR para deshacer un deploy. Un rollback de datos no revierte documentos aceptados por SUNAT. Si API y frontend dejan de ser compatibles, detener promoción; no ocultar controles para disimular rutas ausentes.

## Límites del control

Las pruebas de contratos detectan pérdidas de rutas, no demuestran por sí mismas su comportamiento. Las huellas demuestran identidad, no ausencia de bugs. Por eso se necesitan pruebas de dominio, seguridad, PostgreSQL y navegador. No hay homologación fiscal real si solo se usaron respuestas simuladas. La automatización no impide que un operador la omita: el procedimiento de publicación debe exigir estas puertas y revisar cualquier modificación a sus baselines.

Los recibos de idempotencia de carga masiva se conservan en auditoría (`inventory_bulk`): no purgarlos como logs descartables, pues previenen aplicar de nuevo una operación repetida.

El baseline de producción comprende 223 operaciones. No incluye cinco contratos disponibles exclusivamente en modo local/test (PATCH/DELETE users e invocaciones fiscales `*-legacy`); exigirlos en producción sería reactivar rutas deliberadamente retiradas. Los tests de `test_legacy_frozen_gating.py` verifican esa separación.
