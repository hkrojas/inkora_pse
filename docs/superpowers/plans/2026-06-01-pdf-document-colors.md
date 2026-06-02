# PDF Document Colors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make PDF color customization discoverable from Configuracion and ensure tenant PDF accent color is consistently applied.

**Architecture:** Reuse the existing `/diseno-pdf` editor and tenant visual fields. Add a lightweight card to `ConfiguracionPage`, add backend hex validation, and replace the remaining hardcoded modern PDF strip color with `color_principal`.

**Tech Stack:** React 18, Vite, Tailwind/CSS, FastAPI, Pydantic v2, ReportLab, pytest, ESLint.

---

### Task 1: Backend Color Validation

**Files:**
- Modify: `backend/schemas/tenants.py`
- Test: `backend/test_tenant_pdf_colors.py`

- [ ] **Step 1: Add schema tests**

Create `backend/test_tenant_pdf_colors.py` with tests that instantiate `TenantAdminUpdate` and `TenantUpdate` using valid and invalid values:

```python
import pytest
from pydantic import ValidationError

from schemas.tenants import TenantAdminUpdate, TenantUpdate


@pytest.mark.parametrize("schema", [TenantAdminUpdate, TenantUpdate])
def test_tenant_pdf_colors_accept_hex(schema):
    payload = schema(primary_color="#8DC63F", pdf_note_1_color="#EF4444")

    assert payload.primary_color == "#8DC63F"
    assert payload.pdf_note_1_color == "#EF4444"


@pytest.mark.parametrize("schema", [TenantAdminUpdate, TenantUpdate])
@pytest.mark.parametrize("field", ["primary_color", "pdf_note_1_color"])
def test_tenant_pdf_colors_reject_invalid_values(schema, field):
    with pytest.raises(ValidationError):
        schema(**{field: "blue"})
```

- [ ] **Step 2: Run test to verify current behavior**

Run:

```powershell
cd C:\Users\HP\Desktop\inkora_pse_main_security\backend
& 'C:\Users\HP\Desktop\inkora_smartpse\backend\venv\Scripts\python.exe' -m pytest test_tenant_pdf_colors.py -q
```

Expected: invalid color test fails before validation is added.

- [ ] **Step 3: Implement validation**

In `backend/schemas/tenants.py`, add a helper that trims optional values and accepts only `#RRGGBB`, then register it as a `field_validator` for `primary_color` and `pdf_note_1_color` in both tenant update schemas.

- [ ] **Step 4: Verify backend test passes**

Run the same pytest command. Expected: all tests pass.

### Task 2: Configuracion Entry Point

**Files:**
- Modify: `frontend/src/pages/ConfiguracionPage.jsx`
- Modify: `frontend/src/styles/globals.css`
- Test: `frontend/src/lib/utils/betaLaunchScope.test.js` if it needs route/static updates

- [ ] **Step 1: Add PDF document card to Apariencia**

Pass `tenantData` into `AparienciaPanel`. Add a "Colores de documentos PDF" section with a preview using `tenantData.primary_color || "#004AAD"` and `tenantData.pdf_note_1_color || "#FF0000"`.

- [ ] **Step 2: Add navigation button**

Use `Link` from React Router to navigate to `/diseno-pdf`. The button text should be "Editar colores PDF".

- [ ] **Step 3: Style the card**

Add focused CSS classes for the document color card, preview strip, color swatches and footer action. Keep styles aligned with the existing settings cards and support dark mode.

- [ ] **Step 4: Run frontend lint/build**

Run:

```powershell
cd C:\Users\HP\Desktop\inkora_pse_main_security\frontend
npm run lint
npm run build
```

Expected: both pass.

### Task 3: PDF Accent Consistency

**Files:**
- Modify: `backend/services/pdf_generator.py`

- [ ] **Step 1: Replace hardcoded modern strip color**

Change `color_strip = colors.HexColor("#1747C8")` to use `color_principal`.

- [ ] **Step 2: Run targeted backend tests**

Run:

```powershell
cd C:\Users\HP\Desktop\inkora_pse_main_security\backend
& 'C:\Users\HP\Desktop\inkora_smartpse\backend\venv\Scripts\python.exe' -m pytest test_tenant_pdf_colors.py -q
```

Expected: tests pass and no schema regression.

### Task 4: Final Verification And Publish

**Files:**
- Commit only the files touched by this plan.

- [ ] **Step 1: Check diff and whitespace**

Run:

```powershell
git diff --check
git status --short
```

Expected: no whitespace errors, only intended files changed.

- [ ] **Step 2: Commit and push**

Run:

```powershell
git add docs/superpowers/specs/2026-06-01-pdf-document-colors-design.md docs/superpowers/plans/2026-06-01-pdf-document-colors.md backend/schemas/tenants.py backend/test_tenant_pdf_colors.py backend/services/pdf_generator.py frontend/src/pages/ConfiguracionPage.jsx frontend/src/styles/globals.css
git commit -m "Add PDF color customization entry point"
git push inkora_pse main
```

Expected: commit created and pushed to `inkora_pse/main`.
