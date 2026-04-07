# TASKS.md

This file is the execution checklist for the current PrintFlow phase.

The project is being narrowed to a **single launch plan**. The goal is to make the backend safe, maintainable, and ready for a small paid beta before expanding into inventory, MRP, advanced production, AI, or multi-plan pricing.

---

# Execution rules

- Do **not** expand frozen domains unless explicitly instructed.
- Do **not** add public multi-plan logic right now.
- Do **not** prioritize frontend framework migration.
- Prefer backend safety and launch-scope correctness over new features.
- Finish each phase with a clear checkpoint before starting the next one.

---

# Launch-scope product

The current commercial target is a **single-price launch plan** with this flow:

1. Customers
2. Product/service catalog
3. Quotations
4. Invoicing (invoice / receipt / notes)
5. Shipping guides
6. Shipping labels
7. Basic collections
8. Simple dashboard
9. Monthly Excel report
10. Superadmin / billing control

---

# Phase 0 — Scope freeze and feature classification

## Goal
Stop uncontrolled expansion and explicitly separate launch scope from frozen scope.

## Tasks
- [ ] Define and document the **launch-scope modules** in repo docs.
- [ ] Define and document the **frozen modules** in repo docs.
- [ ] Mark non-launch endpoints clearly in comments and internal docs.
- [ ] Ensure agent instructions match the single-plan strategy.
- [ ] Create a short release definition for the launch product.

## Launch-scope modules
- auth
- tenants
- customers
- products/services catalog
- quotations
- invoicing
- shipping guides
- shipping labels
- basic collections
- simple dashboard
- monthly Excel export
- superadmin / subscription control

## Frozen modules for now
- suppliers expansion
- insumos/raw-material inventory
- BOM / recetas
- production orders
- advanced inventory alerts
- advanced analytics
- AI endpoints

## Exit criteria
- [ ] Team/agent docs clearly reflect the reduced product scope.
- [ ] No new task is started outside launch scope without explicit approval.

---

# Phase 1 — Security and configuration hardening

## Goal
Remove the most dangerous operational risks before deeper refactoring.

## Tasks
- [ ] Remove hardcoded secrets/tokens from code.
- [ ] Rotate any exposed real token that has already been committed.
- [ ] Require critical env vars in non-local environments.
- [ ] Fail fast when required secrets are missing.
- [ ] Centralize environment loading.
- [ ] Separate local/dev/staging/prod config behavior.
- [ ] Review CORS and make it environment-driven.
- [ ] Add structured logging basics.
- [ ] Define backup requirements for DB and uploaded assets.
- [ ] Stop relying on unsafe defaults for JWT/API credentials.

## Specific code targets
- `backend/config.py`
- `backend/main.py`
- any service using external API tokens

## Exit criteria
- [ ] No real secrets are hardcoded in the repository.
- [ ] App can run locally through `.env` only.
- [ ] Production startup fails if critical secrets are missing.

---

# Phase 2 — Backend modularization

## Goal
Break down the oversized entrypoint and separate responsibilities.

## Tasks
- [ ] Reduce `backend/main.py` to an application composition layer.
- [ ] Create router modules:
  - [ ] `routers/auth.py`
  - [ ] `routers/tenants.py`
  - [ ] `routers/clientes.py`
  - [ ] `routers/productos.py`
  - [ ] `routers/cotizaciones.py`
  - [ ] `routers/facturacion.py`
  - [ ] `routers/guias.py`
  - [ ] `routers/pagos.py`
  - [ ] `routers/superadmin.py`
- [ ] Move business logic out of route handlers.
- [ ] Keep external API calls in service layer, not in routers.
- [ ] Split `crud.py` by domain when practical or introduce repository modules.
- [ ] Keep imports clean and acyclic.

## Optional structure target
- `routers/`
- `services/`
- `repositories/`
- `schemas/`
- `models/`
- `core/` or `config/`

## Exit criteria
- [ ] `main.py` no longer contains business-heavy route definitions.
- [ ] Launch-scope domains live in separate router files.
- [ ] Business logic is easier to navigate by domain.

---

# Phase 3 — Tenant isolation and role hardening

## Goal
Make tenant safety explicit and robust.

## Tasks
- [ ] Review the current automatic tenant filter and document exactly where it applies.
- [ ] Add explicit tenant checks in critical update/delete/read operations.
- [ ] Introduce helper functions for resource ownership validation.
- [ ] Review every launch-scope CRUD path for tenant leakage risk.
- [ ] Harden role checks:
  - [ ] superadmin
  - [ ] admin
  - [ ] operador
  - [ ] vendedor
- [ ] Define who can:
  - [ ] issue documents
  - [ ] void documents
  - [ ] update tenant settings
  - [ ] register payments
  - [ ] access superadmin endpoints
- [ ] Add tests for tenant isolation and forbidden access.

## Exit criteria
- [ ] Sensitive resources are tenant-safe by explicit logic, not only by assumption.
- [ ] Role-sensitive actions return clear forbidden errors when appropriate.

---

# Phase 4 — Document model correction

## Goal
Reduce the risk of mixing quotation logic and fiscal document logic.

## Current concern
The current backend uses quotation-like entities for multiple business meanings. This must be clarified.

## Tasks
- [ ] Decide target approach:
  - [ ] full separation of `Quotation` and `FiscalDocument`
  - [ ] transitional separation with explicit `document_kind`
- [ ] Add stable internal order identity for launch workflow.
- [ ] Ensure traceability between:
  - [ ] quotation
  - [ ] internal order/reference
  - [ ] fiscal document
  - [ ] shipping guide
  - [ ] payment status
- [ ] Prevent silent mutation of business meaning.
- [ ] Make status transitions explicit and documented.
- [ ] Review note/void flows against the new model.

## Preferred result
Quotations and fiscal documents are clearly distinguishable in behavior and traceability, even if a transitional schema is used initially.

## Exit criteria
- [ ] The document lifecycle is understandable and consistent.
- [ ] A quotation can be traced to its downstream fiscal and shipping artifacts cleanly.

---

# Phase 5 — Superadmin and SaaS billing domain

## Goal
Build the internal operational layer required to run PrintFlow as a SaaS.

## Tasks
- [ ] Introduce backend domain for subscription/access control.
- [ ] Add fields or models for:
  - [ ] plan code
  - [ ] subscription status
  - [ ] billing start date
  - [ ] billing due date
  - [ ] grace period
  - [ ] founder/current price
  - [ ] max users
  - [ ] max documents
  - [ ] onboarding status
  - [ ] internal notes
- [ ] Add SaaS payment record model separate from customer collection payments.
- [ ] Build internal endpoints for:
  - [ ] tenant listing
  - [ ] activate tenant
  - [ ] suspend tenant
  - [ ] extend access
  - [ ] register SaaS payment
  - [ ] set founder pricing
- [ ] Enforce suspended tenant access behavior.
- [ ] Keep this separate from tenant business payments.

## Exit criteria
- [ ] The team can control access and billing without spreadsheets/memory.
- [ ] SaaS subscription payments are not mixed with quotation/customer payments.

---

# Phase 6 — Launch workflow polish

## Goal
Make the single-plan product excellent in its core workflow.

## Customers
- [ ] Enrich customer model for launch scope:
  - [ ] phone
  - [ ] WhatsApp
  - [ ] email
  - [ ] contact name
  - [ ] delivery data
  - [ ] payment condition
  - [ ] notes
- [ ] Evaluate whether multiple addresses are needed now or in the next subphase.
- [ ] Improve search and quick retrieval.

## Catalog
- [ ] Keep product/service catalog simple and reusable.
- [ ] Ensure products are easy to use in quotations.
- [ ] Add duplicate/favorite flows if low-cost.

## Quotations
- [ ] Improve quotation creation UX at API/domain level.
- [ ] Support manual items cleanly.
- [ ] Ensure calculations are correct and consistent.
- [ ] Support quotation states clearly.
- [ ] Support shareable quotation PDFs.
- [ ] Support converting approved quotation into fiscal flow.
- [ ] Add internal order/reference id.

## Invoicing
- [ ] Harden pre-validation before issuing any fiscal document.
- [ ] Clarify fiscal status transitions.
- [ ] Improve duplicate emission protection.
- [ ] Improve retry/failure recording for external fiscal API.
- [ ] Ensure XML/PDF/CDR retrieval flows are robust.

## Shipping guides and labels
- [ ] Stabilize guide creation and validation.
- [ ] Stabilize guide emission flow.
- [ ] Generate shipping labels from guide data.
- [ ] Make the flow naturally follow invoice/dispatch use cases.

## Basic collections
- [ ] Clarify partial vs paid vs pending state.
- [ ] Store amount paid and balance clearly.
- [ ] Add overdue visibility and aging.

## Dashboard and report
- [ ] Keep dashboard intentionally simple.
- [ ] Ensure monthly Excel export is accountant-usable.

## Exit criteria
- [ ] Core flow works cleanly for a real pilot customer.
- [ ] The product already feels better than spreadsheet + basic e-invoicing + manual guide/label work.

---

# Phase 7 — Tests and launch reliability

## Goal
Make the backend trustworthy enough for a small paid beta.

## Tasks
- [ ] Add auth tests.
- [ ] Add tenant isolation tests.
- [ ] Add quotation creation tests.
- [ ] Add quotation-to-document flow tests.
- [ ] Add invoice/receipt state guard tests.
- [ ] Add guide emission flow tests.
- [ ] Add payment partial/full settlement tests.
- [ ] Add duplicate emission tests.
- [ ] Add external API failure/retry tests.
- [ ] Add regression tests for fiscal math that already exists.
- [ ] Add basic CI test execution if not present.

## Exit criteria
- [ ] Launch-scope workflows are covered by meaningful automated tests.
- [ ] Critical regressions are less likely to slip into beta.

---

# Phase 8 — Onboarding acceleration

## Goal
Reduce onboarding friction for real customers.

## Tasks
- [ ] Add import flow for customers from Excel/CSV if feasible.
- [ ] Add import flow for products from Excel/CSV if feasible.
- [ ] Define onboarding checklist in backend/admin model.
- [ ] Track tenant onboarding completion state.
- [ ] Prepare seeded demo/test tenant data for faster validation.
- [ ] Add internal notes/support metadata for each tenant.

## Exit criteria
- [ ] New customers can be onboarded without excessive manual setup time.

---

# Phase 9 — Closed paid beta

## Goal
Validate the single-plan launch product with a small number of paying launch customers.

## Tasks
- [ ] Select first pilot tenants.
- [ ] Use founder pricing / single-plan pricing.
- [ ] Run onboarding manually and observe every step.
- [ ] Track support issues.
- [ ] Track failure points in the workflow.
- [ ] Track retention signals and actual usage.
- [ ] Freeze expansion requests unless they affect launch reliability.

## Metrics to watch
- active paying tenants
- churn / early cancellation
- onboarding completion rate
- documents issued successfully
- guide + label usage
- support load per tenant
- monthly report usefulness feedback

## Exit criteria
- [ ] At least a small set of real users can operate the launch workflow reliably.
- [ ] The team has enough evidence to decide what the next product layer should be.

---

# Phase 10 — Only after launch stability

## Goal
Revisit frozen domains only after the launch base is stable.

## Candidate later domains
- suppliers expansion
- inventory / insumos
- BOM recipes
- production orders
- outsourcing workflow
- advanced analytics
- AI parsing / smart assistants
- plan differentiation / add-ons

## Rule
Do not enter this phase until the single-plan launch product is stable, paid, and supportable.

---

# What success looks like

The current phase succeeds if:
- backend architecture is safer and more modular
- tenant and billing control are operational
- launch workflow is strong
- first customers can pay and use it
- the team is not drowning in hidden complexity

That is the goal.