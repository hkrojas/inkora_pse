# Base productiva reconstruida — 18/09/2026

## Resultado

**AMARILLO para Git; VERDE para la identidad del código desplegado.**

La entrega que opera en producción está identificada y preservada, pero no está representada por un único commit. No se debe hacer `checkout`, `reset`, rebase ni despliegue desde `main` hasta consolidar esta base en una rama nueva y verificarla.

Este análisis fue local y de solo lectura sobre aplicación e historial. No consultó ni modificó Vercel, Railway, Supabase, Smart PSE, series, correlativos, credenciales o datos.

## Base comprobada

| Elemento | Evidencia |
|---|---|
| Raíz canónica | `C:/Users/HP/Desktop/inkora_smartpse` |
| Rama de trabajo | `codex/smartpse-backend` |
| HEAD de la raíz | `640528c4aac2f97e01b4c648aca34582e51c2c84` |
| `main` local | `8ff4b7f954f8b637b338267d42f5d72540b1bf48` |
| `main` remoto observado | `a7b514c91bd98c4114953529471c4045ef85e520` |
| Ancestro entre HEAD y `main` remoto | `653e229dc9087753192fe1bebf6b95dc64dc5e97` |
| Divergencia HEAD / `main` remoto | 14 commits exclusivos del HEAD y 228 exclusivos de `main` remoto |
| Paquete productivo preservado | `tmp/actions-consistency-20260918`, 366 archivos |
| Huella del contenido | `1755dc0ee9a6e22395b991f51e185b0c2437826c42ff94326643abab01a74a73` |
| Respaldo local | `backups/organization-20260918`, verificado |

Los identificadores remotos de la última entrega constan en [CIERRE_ACCIONES_DOCUMENTALES_2026-09-18.md](CIERRE_ACCIONES_DOCUMENTALES_2026-09-18.md). No se volvieron a consultar en este bloque.

## Qué significan los cambios que aparecen en Git

### Contra el HEAD actual

De las entradas que Git presenta como modificadas o nuevas, **164 pertenecen al paquete productivo exacto**:

- 101 archivos productivos registrados, modificados respecto al HEAD.
- 63 archivos productivos sin registrar respecto al HEAD.
- 202 archivos del paquete no aparecen modificados respecto al HEAD.

Por tanto, “sin registrar” no significa “experimental” ni “descartable”. Parte del backend, frontend y las migraciones que producción necesita todavía no está en el historial de esta rama.

Fuera del paquete hay 116 entradas del estado de Git: 29 eliminadas, 25 modificadas y 62 nuevas. Comprenden principalmente pruebas, contratos, scripts y documentación. No se ejecutan en producción, pero varias explican o validan el código desplegado; tampoco deben borrarse en bloque.

### Contra `main` remoto

| Relación de los 366 archivos productivos | Cantidad |
|---|---:|
| Idénticos a `main` remoto | 238 |
| Presentes, pero con contenido diferente | 94 |
| Ausentes de `main` remoto | 34 |
| Total que debe preservarse al consolidar sobre `main` | **128** |

De los 34 archivos productivos ausentes de `main`, solo `0007_quote_wallet_selection.py` aparece en algún otro commit local. Los otros **33 no tienen historial en ninguno de los refs locales inspeccionados**. Su única fuente completa comprobada es el árbol actual y el paquete/respaldo verificados.

## Mapa funcional reconstruido

Las categorías se basan en código, migraciones, pruebas e informes existentes; varios archivos compartidos participan en más de un bloque y no deben separarse mecánicamente.

| Bloque | Qué incorpora | Estado respecto a producción | Evidencia principal |
|---|---|---|---|
| Base proveniente de `main` | Inventario comercial, precios a cuatro decimales, facturación/boletas, notas y mejoras de interfaz previas | 238 archivos idénticos; es el punto de partida, no la entrega completa | Historial hasta `a7b514c` |
| Base fiscal Smart PSE | Trazabilidad del proveedor, verificación, serie por empresa, precisión, historial de intentos y contingencia | Desplegado; repartido entre migraciones, modelos, worker y servicios | Revisiones `0008`–`0020`, suites Smart PSE/emisión |
| Recuperación operativa | Edición y PDF de cotizaciones, inventario, configuración, Superadmin, acceso público, almacenamiento y seguridad | Desplegado y documentado; no es únicamente trabajo de Guías | [RECUPERACION_VERSION_2026-09-18.md](RECUPERACION_VERSION_2026-09-18.md) |
| Guías de venta | Despachos parciales, reservas, factura/boleta, GRE 09/31, transporte privado/público/M1-L, XML, PDF y conciliación | Desplegado; últimas migraciones `0021` y `0022` presentes en Supabase según el informe de entrega | `sale_dispatch_service.py`, `gre_ubl_service.py`, `guide_pdf_service.py`, formularios GRE y documentos `GRE_*` |
| Acciones documentales | Menú común, reenvío condicionado, recuperación de artefactos, seguimiento del worker, paginación fiscal y estados excluyentes | Es la corrección desplegada después de la recuperación/Guías; también debe conservarse | [CIERRE_ACCIONES_DOCUMENTALES_2026-09-18.md](CIERRE_ACCIONES_DOCUMENTALES_2026-09-18.md) |
| Catálogo/landing/acceso público | Catálogo aislado, landing, consulta pública y solicitudes de acceso | Parte del contenido productivo actual; algunos servicios no existen en `main` remoto | Migración `0018`, routers/servicios de catálogo y acceso |
| Soporte de calidad | Contratos de rutas/activos, guard de entrega, pruebas PostgreSQL y frontend, runbooks | No todo se empaqueta en runtime, pero evita repetir la regresión | `contracts/`, `scripts/`, pruebas y [RELEASE_CANONICO.md](RELEASE_CANONICO.md) |

### Archivos productivos ausentes de `main` remoto

**Migraciones:**

- `0007_quote_wallet_selection.py`
- `0009_widen_unit_price_precision.py`
- `0010_smartpse_provider_verification.py`
- `0017_merge_fiscal_inventory_heads.py`
- `0018_catalog_domain_foundation.py`
- `0019_emission_attempt_history.py`
- `0020_tenant_fiscal_contingency.py`
- `0021_sale_dispatch_guides.py`
- `0022_gre_sales_documents.py`

**Backend:** catálogo, reglas y PDF/XML de Guías, reservas de despacho, acciones fiscales, presentación fiscal y huella de entrega (`models/catalog.py`, routers/servicios de catálogo, `document_actions_service.py`, `fiscal_presentation_service.py`, `gre_ubl_service.py`, `guide_pdf_service.py`, `release_identity.py` y `sale_dispatch_service.py`).

**Frontend:** acciones fiscales y menú compartido, seguimiento de trabajos, filtros fiscales y formularios de GRE remitente/transportista (`FiscalDocumentActions`, `ActionMenu`, `useFiscalTracking`, utilidades relacionadas y `GuiaNuevaPage`/`GuiaTransportistaNuevaPage`).

La lista completa y las huellas individuales están preservadas en `backups/organization-20260918/inventory.json` y en el manifiesto del paquete.

## Hallazgos

| Prioridad | Hallazgo | Riesgo | Tratamiento recomendado |
|---|---|---|---|
| P0 organizativo | Ningún commit reproduce producción | Un checkout o despliegue desde una rama borra funciones activas | Crear una rama local de baseline desde `main` remoto y materializar exactamente el paquete verificado |
| P0 organizativo | 33 archivos productivos sin historial recuperable en refs locales | Se perderían con `git clean`, cambio de worktree o copia parcial | Mantener árbol, paquete y respaldo; registrarlos en el baseline |
| P1 | El HEAD y `main` remoto tienen historias muy divergentes | Rebase/merge directo produciría conflictos difíciles de atribuir | No reconciliar por commits antiguos; usar comparación de contenido con el paquete como autoridad |
| P1 | Migraciones desplegadas siguen sin registrar en la rama actual | Una entrega futura podría omitirlas aunque la base remota ya esté en `0022` | Incluir la cadena exacta en el baseline y ejecutar validación Alembic local/aislada antes de publicar otra entrega |
| P1 | Código productivo y pruebas/contratos están separados por el empaquetador | Consolidar solo runtime dejaría una base difícil de verificar | Crear un segundo commit de soporte validado, enlazado al mismo baseline |
| P2 | 29 documentos registrados figuran eliminados | Se puede perder historia de decisiones o restaurar planes obsoletos indiscriminadamente | Revisar contra documentos sustitutos; conservar copia HEAD hasta decidir uno por uno |

## Consolidación propuesta

No conviene reconstruir docenas de commits “por memoria”. La opción reproducible es:

1. Crear una **rama local nueva** desde `refs/remotes/inkora_pse/main` en otro worktree, sin tocar esta raíz.
2. Materializar en ella los 366 archivos del paquete inmutable y comprobar que genera exactamente la misma huella.
3. Crear un primer commit denominado conceptualmente **baseline productivo 2026-09-18**. Este commit debe representar lo que ya está desplegado; no una funcionalidad nueva.
4. Incorporar en un segundo commit pruebas, contratos, scripts y documentación que validan ese baseline. Revisar las 29 eliminaciones antes de decidir si se registran.
5. Ejecutar guard, regresión backend/frontend y PostgreSQL aislado. Comparar el paquete resultante archivo por archivo con la entrega productiva.
6. Recién después, integrar nuevos cambios de Guías u otros módulos como commits separados sobre esa base.

Crear esta rama y sus commits **no requiere ni autoriza un despliegue**. No debe promoverse ni fusionarse a `main` hasta una revisión explícita. El árbol actual se mantiene intacto como fuente de comparación y recuperación.

## Archivos que tocaría el siguiente bloque

- Un worktree nuevo fuera de la raíz actual.
- Los 366 archivos del paquete, copiados con sus rutas exactas en ese worktree.
- `contracts/`, `scripts/`, pruebas y documentos aprobados en un commit separado.
- Ningún archivo, variable o dato remoto.

## Verificaciones de este diagnóstico

```powershell
backend/venv/Scripts/python.exe scripts/workspace_inventory.py verify --destination backups/organization-20260918
backend/venv/Scripts/python.exe scripts/release_guard.py check
backend/venv/Scripts/python.exe scripts/release_guard.py verify --destination tmp/actions-consistency-20260918
git rev-list --left-right --count HEAD...refs/remotes/inkora_pse/main
git diff --cached --stat
```

Resultados: respaldo correcto; raíz y paquete con huella idéntica; 366 archivos; HEAD conservado; índice vacío. No se ejecutaron pruebas funcionales nuevas porque este bloque no modifica la aplicación. Los resultados históricos citados pertenecen a los informes de cada entrega y no se presentan como una nueva ejecución.

## Recomendación

**Implementar el baseline local en el siguiente bloque, sin desplegar.** No trabajar directamente sobre el `main` local actual ni sustituir la raíz con el `main` remoto. `main` aporta la base común, pero el paquete productivo es la autoridad de contenido hasta que exista un commit verificado que lo reproduzca.

## Estado de construcción local

Se creó el worktree aislado `C:/Users/HP/Desktop/inkora_production_baseline_20260918` con la rama `codex/production-baseline-20260918`, partiendo de `a7b514c91bd98c4114953529471c4045ef85e520`. No altera la rama ni los archivos de la raíz original.

El contenido actual y respaldado fue materializado allí. Los 632 archivos del snapshot coinciden individualmente por SHA256. El guard ejecutado desde el nuevo worktree reconoce 366 archivos de aplicación y reproduce exactamente la huella productiva `1755dc0ee9a6e22395b991f51e185b0c2437826c42ff94326643abab01a74a73`.

El índice del nuevo worktree está vacío. Frente a `main` remoto, el candidato todavía muestra 129 modificaciones, 238 eliminaciones y 89 rutas nuevas. Esta amplitud es esperable porque `main` contiene una línea divergente; no debe ejecutarse `git add .`.

Las 238 eliminaciones se descomponen en 173 archivos auxiliares del frontend, 40 documentos, 9 pruebas, 9 migraciones alternativas, 5 archivos raíz/auxiliares y 2 archivos backend. Los únicos elementos de ejecución que merecen revisión explícita antes de preparar el commit son:

- Las nueve migraciones alternativas de `main` (`0007_smartpse_company_management` a `0014_access_requests`), incompatibles nominalmente con la cadena productiva actual. La base productiva conserva su propia cadena hasta `0022_gre_sales_documents`.
- `backend/services/fiscal_clock.py`, deliberadamente no incorporado durante la recuperación porque las diferencias de fecha fiscal requerían un bloque específico.
- `backend/scripts/audit_smartpse_emission_evidence.py`, herramienta auxiliar y no parte del paquete de ejecución.

No se ha creado commit ni staging. `backend/test_release_guard.py`: 5 pruebas aprobadas desde el nuevo worktree. El siguiente control debe revisar esas exclusiones y clasificar los 89 archivos nuevos entre runtime y soporte antes de proponer dos listas explícitas para staging.

## Control posterior de organización

El runtime productivo fue preparado selectivamente en el índice del worktree aislado, sin crear commit: 94 modificaciones, 34 altas y 10 eliminaciones, para 138 cambios al desactivar la detección de renombres. Ningún archivo de soporte entró en ese staging.

Se recuperaron seis pruebas útiles de `main` fuera del índice. La ejecución focalizada backend produjo 6 aprobaciones y 3 fallas. Dos fallas revelan riesgos P1 del contenido productivo actual —terminación del worker ante ciertos errores SQLAlchemy y ausencia de una segunda validación de service-role en el cliente de Storage—. La tercera corresponde a un contrato antiguo de readiness que efectuaba escritura y borrado; debe rediseñarse antes de adoptarlo.

La organización se detuvo en el diagnóstico: no se cambió el código operativo, no se creó commit y no se desplegó. La consolidación futura debe corregir y validar cada P1 en su propio bloque antes de incorporar las pruebas recuperadas al conjunto de soporte.
