# Organización local de Inkora — 2026-09-18

## Alcance y límite

Primer bloque de organización autorizado: inventario, respaldo verificable y reducción de ruido local. No se modifica la aplicación, el despliegue, la configuración fiscal ni los datos. No se ejecutan publicaciones, migraciones, commits, staging, eliminaciones, movimientos ni poda de worktrees. Se aplica la skill `inkora-p1-operator`: un bloque separado, sin modificar el núcleo fiscal/cobranza.

La fuente canónica es `C:/Users/HP/Desktop/inkora_smartpse`. No usar la ruta histórica `mi_proyecto_cotizaciones` ni una copia auxiliar como fuente de entrega. La organización no sustituye las puertas de publicación de [RELEASE_CANONICO.md](RELEASE_CANONICO.md).

## Punto de recuperación

- Rama: `codex/smartpse-backend`.
- HEAD: `640528c4aac2f97e01b4c648aca34582e51c2c84`.
- Índice sin cambios preparados al iniciar. No se han preparado commits.
- Estado inicial, antes de las exclusiones: 126 archivos registrados modificados, 29 eliminados y 122 entradas sin registrar (algunas son carpetas, no archivos individuales).
- Huella del contenido de aplicación: `1755dc0ee9a6e22395b991f51e185b0c2437826c42ff94326643abab01a74a73`, 366 archivos.
- Paquete local conservado: `tmp/actions-consistency-20260918`; proyección worker: `tmp/actions-consistency-worker-20260918`.

La huella coincide con la entrega registrada en [CIERRE_ACCIONES_DOCUMENTALES_2026-09-18.md](CIERRE_ACCIONES_DOCUMENTALES_2026-09-18.md). Es una comprobación local; en este bloque no se consultan ni modifican Vercel, Railway o Supabase. Los resultados remotos del informe anterior no son nuevas verificaciones realizadas aquí.

## Mapa del espacio de trabajo

| Ubicación | Uso y tratamiento |
|---|---|
| `backend/`, `frontend/` | Código canónico. Cambios existentes conservados y visibles en Git. |
| `backend/alembic/versions/` | Migraciones, incluidas revisiones aún sin registrar. No ejecutar, renumerar ni ocultar. |
| `contracts/`, `scripts/` | Contratos y herramientas reproducibles. Conservar visibles; revisar antes de consolidar. |
| `docs/`, `.impeccable/`, `logo/` | Documentación y referencias de diseño. No tratarlas como basura. |
| `supabase/` | Recursos de proyecto pendientes de clasificación. No tocar servicios remotos. |
| `tmp/` | Paquetes inmutables, evidencias y temporales. Conservar; no publicar desde una copia arbitraria ni borrar en bloque. |
| `output/`, `frontend/output/` | Resultados generados. Conservar en disco, excluir del estado de Git raíz. |
| `.codex/`, `.codex-remote-attachments/`, `frontend/.vercel/` | Estado local de herramientas. Conservar, no incorporar a fuente. |
| `backups/` | Respaldos locales privados, ya ignorados. No subir al repositorio ni a paquetes. |
| `.env*`, bases locales, dependencias | No mover, mostrar secretos ni incorporar a esta entrega. |

### Worktrees anidados: no son temporales descartables

| Carpeta | Revisión observada | Referencia |
|---|---|---|
| `_release_guides_prod` | `a7b514c91bd98c4114953529471c4045ef85e520` | HEAD separado |
| `_push_main_sync` | `7b7da5d7bebda4a7a75683af59874492be0c065b` | `codex/push-pdf-header-sync` |
| `_push_quote_footer_main` | `b6346ebd9d4632179d746fbf0c16dd603379116c` | `codex/quote-footer-layout` |

Se conservan donde están, con sus estados independientes. Las exclusiones del repositorio raíz no eliminan sus archivos ni ocultan sus cambios al ejecutar `git -C <carpeta> status`. Antes de retirarlos en otra etapa, revisar sus diferencias y respaldar su contenido propio. El inventario conserva también el listado de otros worktrees; las entradas marcadas como podables no se podaron.

## Respaldo y comprobación

Directorio: `backups/organization-20260918`.

- `sources.zip`: 632 archivos actuales seleccionados de código/documentación/configuración y copias HEAD de los 29 archivos ya eliminados. No restaura esos archivos en el árbol de trabajo.
- `inventory.json`: rutas, clasificación, pertenencia a Git, tamaños, SHA256 por archivo y huella del ZIP.
- Dentro del ZIP, `metadata/`: estado Git inicial, diferencias del índice, referencias Git, listado de worktrees, estado de los tres worktrees anidados y manifiesto de aplicación.
- `git-info-exclude.before`: copia del archivo de exclusiones antes de este bloque.

El respaldo contiene 133 archivos actuales no registrados en Git, según la selección del inventario. Esta cifra no equivale a las 122 entradas de `git status`, que agrupa carpetas. Las categorías del inventario incluyen entradas eliminadas.

Comandos de verificación local desde la raíz, sin publicaciones:

```powershell
backend/venv/Scripts/python.exe scripts/workspace_inventory.py verify --destination backups/organization-20260918
backend/venv/Scripts/python.exe scripts/release_guard.py check
backend/venv/Scripts/python.exe scripts/release_guard.py verify --destination tmp/actions-consistency-20260918
git diff --cached --stat
```

El script de inventario rechaza destinos existentes y exige una huella de aplicación conocida al crear un nuevo respaldo. Comprueba que los archivos, el índice, el estado Git y el contenido de aplicación no cambien durante la copia.

**Límites:** no es un respaldo de producción, una copia completa del repositorio Git ni un respaldo del contenido de los demás worktrees. Omite dependencias, resultados generados, bases de datos y archivos de credenciales identificados por nombre/extensión; no realiza un análisis exhaustivo de secretos dentro del código. Tratarlo como privado. La documentación añadida después del snapshot no está dentro de ese snapshot.

Para una recuperación futura: verificar primero el ZIP, extraer en una carpeta nueva, comparar `current/` con la raíz y recuperar únicamente los archivos aprobados. `deleted-at-head/` contiene versiones históricas, no archivos que deban restaurarse automáticamente. No extraer sobre la raíz en bloque ni restaurar datos fiscales. Las exclusiones locales pueden recuperarse desde `git-info-exclude.before`, tras comprobar que nadie haya agregado reglas posteriores.

## Exclusiones locales, no cambios de despliegue

Solo se amplía `.git/info/exclude` con rutas exactas para los tres worktrees anidados, `tmp/`, resultados generados, estado local Codex/Vercel, `_browser_screen.png` y `backend/pytest_bootstrap.db`. No se modifica `.gitignore`, `.dockerignore`, Railway, Vercel ni el empaquetador.

Las exclusiones no afectan archivos ya registrados y no sustituyen la lista permitida de archivos del empaquetador. No significa que sea seguro desplegar manualmente cualquier carpeta. Tampoco convierten el árbol de trabajo en un árbol limpio.

## Consolidación pendiente: sin mezclar ni perder funciones

1. Revisar las 29 eliminaciones documentales registradas y decidir, archivo por archivo, si fueron intencionales, reemplazadas o requieren recuperación. El inventario conserva los nombres y las copias HEAD.
2. Clasificar cambios de aplicación y sus dependencias: base de modelos/migraciones; emisión/contingencia/despachos; recuperación operativa; interfaz; pruebas y contratos. No repartir un archivo compartido entre bloques sin revisar sus diferencias.
3. Preparar propuestas de commits explícitos y revisables, sin `git add .`, sin commits automáticos y sin publicar como parte de la organización. Los servicios y migraciones sin registrar son avances reales, no temporales.
4. Solo tras consolidar y validar la raíz, considerar archivar worktrees auxiliares en un bloque autorizado, con respaldo propio. No retirar paquetes necesarios para trazabilidad o rollback.

El riesgo principal pendiente es la divergencia entre HEAD y los avances locales. Quitar ruido visual ayuda, pero no resuelve por sí solo el origen del incidente: publicar contenido divergente sin verificar la entrega completa. La defensa sigue siendo fuente canónica, manifiesto, contratos, pruebas y comparación de la misma entrega entre componentes.

## Verificación de cierre de este bloque

- Verificador del respaldo: correcto, 632 archivos actuales y 29 copias históricas; SHA256 y CRC del ZIP válidos.
- Comparación independiente contra el inventario: todos los archivos originales conservan su contenido y las eliminaciones preexistentes permanecen sin cambios.
- `release_guard.py check` y `verify`: correctos; raíz y paquete conservan la huella indicada y los mismos 366 archivos.
- HEAD conservado e índice sin cambios preparados.
- `git check-ignore`: las rutas auxiliares quedan excluidas; migración `0022`, servicio de despachos, formulario GRE, contrato operativo, inventariador y este documento continúan visibles.
- Estado posterior: 126 modificados y 29 eliminados registrados, sin variación; 112 entradas sin registrar tras las exclusiones y la incorporación de este documento. No se presenta este estado como limpio.
- No se ejecutó la regresión funcional de la aplicación: este bloque no cambia su contenido. Las comprobaciones realizadas son de integridad y organización, no homologación ni auditoría remota nueva.
