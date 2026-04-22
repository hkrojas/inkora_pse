# ROADMAP.md

This roadmap describes the current strategic execution path for Inkora.

The immediate objective is **not** to finish the full ERP vision. The objective is to build a **solid, safe, and sellable backend foundation** for a **single-plan launch product**.

---

# Roadmap principle

We are intentionally narrowing the product.

We are **not** optimizing for maximum feature count.
We are optimizing for:
- backend solidity
- tenant safety
- fiscal reliability
- operational control
- a clear launch workflow that real print shops will pay for

The current commercial target is a **single-price launch plan**.

---

# Product we are actually launching first

The launch product is centered on this workflow:

**Customer → Quotation → Invoice/Receipt → Shipping Guide → Shipping Label → Basic Collection → Monthly Report**

This is the product to stabilize and validate first.

---

# Milestone 1 — Scope reset

## Goal
Turn Inkora from “expanding ERP vision” into a controlled launch product.

## Strategic outcome
- one launch plan
- one clearly defined launch workflow
- frozen non-essential domains
- reduced complexity pressure on the codebase

## What changes in this milestone
- public multi-plan thinking is postponed
- AI is not a launch pillar
- advanced inventory/production is postponed
- backend decisions are made in favor of reliability, not breadth

## Success criteria
- the team has one product definition, not many competing product definitions
- launch-scope and frozen-scope are clearly documented

---

# Milestone 2 — Backend safety foundation

## Goal
Make the backend safe enough to keep evolving without hidden operational landmines.

## Strategic focus
- configuration hardening
- secret hygiene
- safer startup behavior
- logging and operational sanity
- movement away from fragile runtime assumptions

## Why this matters
If secrets, env config, or startup behavior are sloppy, the entire SaaS will remain fragile no matter how many features are added.

## Success criteria
- no hardcoded live secrets
- production-sensitive config is environment-based
- launch environments are predictable

---

# Milestone 3 — Architectural cleanup

## Goal
Make the backend understandable, modular, and maintainable.

## Strategic focus
- reduce `main.py`
- split routers by domain
- isolate business logic into services
- reduce accidental coupling between modules

## Why this matters
The backend already contains more business scope than the launch product needs. Without modularization, every future change becomes riskier.

## Success criteria
- entrypoint is thin
- launch-scope domains are separated cleanly
- backend changes can be made without spelunking one huge file

---

# Milestone 4 — Tenant and permission reliability

## Goal
Make multi-tenant access safe and explicit.

## Strategic focus
- explicit tenant-safe operations
- role-based access clarity
- preventing cross-tenant leakage
- ensuring suspension/activation behavior is enforceable

## Why this matters
A SaaS serving multiple businesses cannot tolerate ambiguous tenant boundaries.

## Success criteria
- tenant isolation is trustworthy
- roles are predictable
- sensitive actions are clearly protected

---

# Milestone 5 — Document lifecycle correction

## Goal
Fix the most dangerous domain ambiguity before it gets entrenched.

## Strategic focus
- clarify quotation vs fiscal document behavior
- improve traceability across the flow
- reduce silent mutation of business meaning
- define clearer document lifecycle and transitions

## Why this matters
If quotations, invoices, notes, and related records are modeled ambiguously, future scaling becomes painful and error-prone.

## Success criteria
- the team can explain the document lifecycle clearly
- traceability from quotation to dispatch is clean enough for real operations

---

# Milestone 6 — Superadmin and SaaS operations

## Goal
Build the internal operating layer needed to run Inkora as a real SaaS.

## Strategic focus
- tenant activation/suspension
- founder pricing support
- due dates and subscription state
- SaaS payment registration
- onboarding tracking

## Why this matters
Without an internal control plane, billing and access become a manual mess as soon as customers start paying.

## Success criteria
- access can be controlled from the system, not from memory/spreadsheets
- SaaS payments are tracked separately from tenant customer collections

---

# Milestone 7 — Launch workflow excellence

## Goal
Perfect the single-plan launch workflow.

## Strategic focus
- customer records that are useful in real print-shop operations
- fast, reusable quotations
- robust document emission
- shipping guide + label flow
- basic payment tracking
- accountant-friendly reporting

## Why this matters
This is the workflow customers will pay for. It must feel complete enough to replace scattered manual work.

## Success criteria
- a real print shop can operate the core flow inside Inkora
- the workflow already beats spreadsheet + generic invoicing + manual guide/label work

---

# Milestone 8 — Reliability and test coverage

## Goal
Make the launch workflow trustworthy enough for paid users.

## Strategic focus
- auth tests
- tenant isolation tests
- fiscal state tests
- shipping flow tests
- payment tracking tests
- duplicate prevention
- external API failure handling

## Why this matters
The cost of a bug is much higher once fiscal documents and tenant data are involved.

## Success criteria
- launch-critical flows are covered by meaningful tests
- regressions are less likely during beta

---

# Milestone 9 — Onboarding readiness

## Goal
Make it possible to onboard real customers without exhausting the team.

## Strategic focus
- customer/product imports if feasible
- onboarding status tracking
- support metadata
- initial tenant setup helpers

## Why this matters
Even a strong product can fail if customer setup is too slow or painful.

## Success criteria
- onboarding becomes repeatable
- first customers can be activated with less friction

---

# Milestone 10 — Closed paid beta

## Goal
Validate the single-plan launch product with real customers.

## Strategic focus
- real usage observation
- support pattern learning
- founder pricing execution
- workflow validation under real-world conditions

## Success criteria
- paying users complete the core workflow reliably
- retention and support signals begin to emerge
- the team has evidence for what should be built next

---

# What is intentionally deferred

The following areas are not roadmap priorities until after the launch base is stable:
- advanced inventory logic
- BOM / MRP as active product scope
- deeper production tracking
- outsourcing workflow depth
- AI as a product pillar
- advanced analytics
- public multi-plan packaging
- premium feature gating
- frontend framework migration

These may exist in code already, but they are **not current roadmap drivers**.

---

# How to decide whether something belongs on the roadmap now

A task belongs **now** if it improves one of these:
- launch workflow reliability
- tenant safety
- fiscal correctness
- backend maintainability
- internal SaaS operations
- onboarding readiness

A task belongs **later** if it mainly adds:
- breadth
- sophistication
- optional intelligence
- advanced operations not needed for launch validation

---

# Definition of roadmap success

This roadmap succeeds when:
- Inkora has a stable backend core
- the team can operate tenants and billing internally
- the product supports a clean launch workflow
- early customers can pay and use it reliably
- the codebase is in a healthier position for future expansion

That is the focus of the current stage.
