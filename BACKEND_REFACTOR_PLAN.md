# BACKEND_REFACTOR_PLAN.md

This file translates the current Inkora strategy into a **file-by-file backend refactor plan**.

It is based on the current backend state and the current product decision:
- **single launch plan only for now**
- **backend first**
- **launch workflow only**
- **frozen advanced domains** until the base is solid

The goal is not to rewrite everything from scratch.
The goal is to **stabilize, modularize, and narrow** the backend so it is safe for real paying tenants.

---

# 1. Current backend diagnosis

The current backend already contains:
- auth
- tenant model
- customer CRUD
- product CRUD
- quotations
- fiscal document emission
- payment tracking
- shipping guides
- providers
- BOM / production order logic
- analytics
- AI endpoints

This means the project has strong domain ambition, but too much scope is mixed into the same backend stage.

The launch product does **not** need the whole current backend surface.
The launch product needs a stable base around:
- customers
- catalog
- quotations
- invoices/receipts/notes
- guides
- labels
- collections
- monthly report
- superadmin billing/access control

---

# 2. Launch-scope code map

## Keep active and improve now
- `backend/main.py` → only as temporary composition layer, then reduce heavily
- `backend/config.py`
- `backend/database.py`
- `backend/security.py`
- `backend/models.py`
- `backend/schemas.py`
- `backend/crud.py` → split gradually
- `backend/facturacion_service.py`
- `backend/pdf_generator.py`
- `backend/comunicacion_service.py`

## Freeze for now (do not expand)
- AI-related logic
- advanced analytics
- BOM/inventory expansion
- production order depth
- supplier domain depth

If these files or endpoints are touched, it should be only to:
- isolate them
- decouple them
- hide them from launch scope
- avoid breakage

---

# 3. Refactor principles

## Principle A — Do not keep growing `main.py`
Current `main.py` is too large and mixes route declarations with product growth history.
It must move toward a thin app assembly file.

## Principle B — Make launch domains first-class
Launch domains must become explicit modules:
- auth
- tenants
- customers
- products
- quotations
- invoicing
- guides
- payments
- superadmin

## Principle C — Do not deepen wrong abstractions
The current design blurs quotation and fiscal document behavior.
Do not add more business logic that assumes this is harmless forever.

## Principle D — Make tenant safety explicit
Do not trust implicit filtering alone for critical access.
Critical paths must validate tenant ownership clearly.

## Principle E — Separate tenant SaaS billing from tenant business collections
Those are different domains and must not share the same mental model.

---

# 4. File-by-file plan

---

## `backend/config.py`

### Current role
Environment settings and external API configuration.

### Problems
- risky defaults
- secrets can end up embedded too easily
- insufficient environment strictness

### Refactor goals
- make config production-safe
- fail fast on missing secrets
- remove dangerous defaults
- prepare env separation cleanly

### Tasks
- remove all real token defaults
- require env-based values for:
  - database URL
  - JWT secret
  - API tokens
  - Gemini key if used
- keep local-only defaults minimal and clearly marked
- add helper flags like:
  - `ENVIRONMENT`
  - `IS_PRODUCTION`
- make CORS origins configurable from env, not hardcoded in app bootstrap

### Desired result
Config becomes deterministic and safe.

---

## `backend/database.py`

### Current role
Engine/session setup and tenant filter injection.

### Problems
- good intent, but safety depends too much on context assumptions
- writes rely on manual correctness elsewhere
- no explicit migration strategy here

### Refactor goals
- preserve tenant context mechanism
- make tenant behavior easier to reason about
- prepare migration-friendly evolution

### Tasks
- document how tenant context is expected to be set/reset
- verify no background or async edge path can leak tenant context unexpectedly
- introduce helper utilities for explicit tenant-safe queries where appropriate
- stop relying on runtime `create_all` elsewhere as schema strategy

### Desired result
Tenant filtering is still useful, but the system no longer depends on it blindly.

---

## `backend/security.py`

### Current role
Password hashing, JWT creation, token decoding, current user resolution.

### Problems
- user resolution also mutates tenant context implicitly
- role model is still too loose for launch-grade operation

### Refactor goals
- keep auth simple and stable
- make role/tenant effects explicit

### Tasks
- keep password and JWT logic here
- clarify user resolution + tenant context behavior
- define role constants or enums centrally
- prepare permission helpers such as:
  - `require_admin`
  - `require_superadmin`
  - `require_document_emitter`
- ensure suspended tenants cannot use protected business endpoints

### Desired result
Authentication stays simple, authorization becomes clearer.

---

## `backend/models.py`

### Current role
Persistence models for all domains.

### Problems
- too many product stages mixed in one file
- quotation/fiscal-document meaning is blurred
- SaaS billing domain is missing
- launch and frozen domains are all mixed together

### Refactor goals
- preserve existing value where possible
- improve document modeling
- add SaaS subscription domain
- reduce conceptual confusion

### Tasks

#### A. Tenant / SaaS operation
Extend tenant-side operational models with either direct fields or related subscription model.

Preferred direction:
- add `Subscription` model or equivalent domain with:
  - `tenant_id`
  - `plan_code`
  - `status`
  - `billing_started_at`
  - `billing_due_at`
  - `grace_until`
  - `current_price`
  - `founder_price`
  - `max_users`
  - `max_documents`
  - `notes_internal`
  - `onboarding_status`

Add separate `SubscriptionPayment` model:
- `tenant_id`
- `amount`
- `currency`
- `method`
- `reference`
- `paid_at`
- `validated_by_user_id`
- `notes`

#### B. Customer model
For launch scope, enrich customer record with fields that matter operationally:
- `whatsapp`
- `contact_name`
- `payment_condition`
- `delivery_reference`
- `notes`

If multiple addresses are not modeled yet, plan for either:
- separate address table later
- or temporary explicit fields:
  - `fiscal_address`
  - `delivery_address`

#### C. Quotations vs documents
Current model uses `Cotizacion` for too many meanings.

Two acceptable directions:

**Preferred direction**
Introduce a separate `FiscalDocument` model and keep quotation as quotation.

**Transitional direction**
Keep current table but add explicit fields such as:
- `document_kind`
- `source_quote_id`
- `internal_order_number`

Do not keep deepening the assumption that one record can quietly shift business meaning.

#### D. Frozen domains
Do not remove BOM/production models immediately if they are already used in code,
but do not expand them either.

### Desired result
Models reflect the launch product more clearly and prepare for internal SaaS operations.

---

## `backend/schemas.py`

### Current role
API contract layer.

### Problems
- launch scope and frozen scope are mixed
- some schemas reflect transitional/legacy coupling
- customer schemas still need launch-oriented enrichment

### Refactor goals
- align API contracts with launch workflow
- reduce ambiguity in document lifecycle
- prepare admin/subscription schemas

### Tasks
- add launch customer fields:
  - whatsapp
  - contact_name
  - payment_condition
  - delivery_reference
  - notes
- add internal order/reference support to quotation/document schemas
- add schemas for subscription/admin operations:
  - tenant summary response
  - activate/suspend request
  - founder pricing update
  - SaaS payment create/response
- separate launch schemas mentally and structurally from frozen-domain schemas where practical
- keep forward compatibility, but do not overdesign public plan schemas yet

### Desired result
Schemas become aligned to the launch product and internal SaaS operations.

---

## `backend/crud.py`

### Current role
Large persistence + business helper file across many domains.

### Problems
- too much domain logic mixed in one place
- tenant assumptions are not explicit enough in all operations
- launch scope and frozen scope are mixed heavily

### Refactor goals
- split by domain gradually
- harden tenant-safe access
- keep launch CRUD paths very clear

### Recommended split target
Over time move toward files like:
- `repositories/users.py`
- `repositories/tenants.py`
- `repositories/clientes.py`
- `repositories/productos.py`
- `repositories/cotizaciones.py`
- `repositories/facturacion.py`
- `repositories/guias.py`
- `repositories/pagos.py`
- `repositories/subscriptions.py`

### Immediate tasks
- make update/delete/read operations explicitly tenant-safe
- extract launch-scope CRUD first
- keep production/BOM CRUD isolated and frozen
- avoid adding more business rules into generic CRUD helpers when they belong in services

### Desired result
CRUD no longer acts as a giant mixed domain bucket.

---

## `backend/facturacion_service.py`

### Current role
Fiscal payload generation, SUNAT/API integration, rules like detracciones and anticipos.

### What is good
This file contains real domain value and should be preserved.

### Problems
- it still mixes some transport concerns, payload shaping, and business assumptions tightly
- it depends on current user business data structure that may evolve
- document identity assumptions may stay too coupled to current quotation model

### Refactor goals
- preserve fiscal know-how
- isolate external API transport cleanly
- make document inputs clearer
- keep idempotency and state guards strong

### Tasks
- separate payload-building helpers from transport layer if helpful
- introduce explicit data contract for what a fiscal emission needs
- improve error taxonomy:
  - validation error
  - external API error
  - timeout
  - duplicate emission risk
- prepare cleaner integration boundary with whichever document model survives
- keep/reinforce state guards and duplicate protection

### Desired result
This becomes a robust fiscal service layer, not an overgrown helper module.

---

## `backend/pdf_generator.py`

### Current role
PDF creation for quotations/documents.

### Refactor goals
- keep it narrow and reusable
- avoid coupling PDF generation too hard to mutable business meaning

### Tasks
- ensure quotation PDF generation is stable
- if needed, prepare separate generators/templates for:
  - quotations
  - labels
  - internal printable docs
- do not overengineer styling right now

### Desired result
Reliable PDF outputs for launch workflow.

---

## `backend/comunicacion_service.py`

### Current role
Link/message generation for WhatsApp or email sharing.

### Refactor goals
- keep this simple
- use it as delivery helper, not as a giant messaging subsystem

### Tasks
- preserve WhatsApp/email helper behavior
- keep launch-scope message generation focused on quotation/document sharing
- do not turn this into a notification platform yet

### Desired result
Useful communication helpers without scope creep.

---

## `backend/main.py`

### Current role
Everything.

### Refactor goal
Stop being everything.

### Final target
`main.py` should only:
- create app
- configure middleware
- mount static assets if still needed
- include routers
- maybe register startup hooks

### Tasks
- remove direct heavy route definitions progressively
- move route groups to routers
- remove inline request/response classes defined in `main.py`
- keep startup/bootstrap logic minimal

### Desired result
A thin entrypoint that no longer defines the system architecture by accident.

---

# 5. New folder structure target

A pragmatic target structure:

```text
backend/
  main.py
  config.py
  database.py
  security.py

  routers/
    auth.py
    tenants.py
    clientes.py
    productos.py
    cotizaciones.py
    facturacion.py
    guias.py
    pagos.py
    superadmin.py

  services/
    facturacion_service.py
    pdf_service.py
    comunicacion_service.py
    subscription_service.py
    tenant_access_service.py

  repositories/
    users.py
    tenants.py
    clientes.py
    productos.py
    cotizaciones.py
    guias.py
    pagos.py
    subscriptions.py

  models/
    # optional later split if desired

  schemas/
    # optional later split if desired
