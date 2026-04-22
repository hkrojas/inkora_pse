# Inkora â€” QWEN Context

## Project Overview

**Inkora** is a vertical SaaS for print shops in Peru. It helps them manage customers, create quotations, issue electronic invoices/receipts via SUNAT, generate shipping guides and labels, track basic collections, and export monthly Excel reports for accountants.

### Current Phase
The project is focused on a **single-plan launch product** â€” not a full ERP. The core workflow is:

**Customer â†’ Quotation â†’ Invoice/Receipt â†’ Shipping Guide â†’ Shipping Label â†’ Basic Collection â†’ Monthly Report**

### Current Status
The backend has already been partially refactored into a modular structure with routers, services, models, schemas, and crud packages. The frontend is a React + Vite + Tailwind CSS SPA.

---

## Tech Stack

### Backend
- **Python** with **FastAPI**
- **SQLAlchemy** ORM
- **PostgreSQL** (via psycopg2-binary)
- **Pydantic** + **pydantic-settings** for validation and config
- **python-jose** + **bcrypt** + **passlib** for auth
- **reportlab** + **qrcode** for PDF generation
- **openpyxl** for Excel export
- **Supabase** client for storage
- **Apisperu API** integration for SUNAT electronic invoicing
- **pytest** for testing

### Frontend
- **React 18**
- **React Router v6**
- **Tailwind CSS v3**
- **Vite**
- **Lucide React** icons

---

## Directory Structure

```
mi_proyecto_cotizaciones/
â”œâ”€â”€ backend/
â”‚   â”œâ”€â”€ main.py                     # Thin app composition layer
â”‚   â”œâ”€â”€ config.py                   # Pydantic settings (env-based)
â”‚   â”œâ”€â”€ database.py                 # SQLAlchemy engine/session + tenant context
â”‚   â”œâ”€â”€ security.py                 # Password hashing, JWT, role checks
â”‚   â”œâ”€â”€ access_control.py           # Tenant access guards
â”‚   â”œâ”€â”€ tenant_access.py            # Tenant context helpers
â”‚   â”œâ”€â”€ logging_utils.py            # Structured logging
â”‚   â”œâ”€â”€ supabase_client.py          # Supabase storage client
â”‚   â”œâ”€â”€ routers/                    # HTTP endpoint routers (by domain)
â”‚   â”‚   â”œâ”€â”€ auth.py
â”‚   â”‚   â”œâ”€â”€ tenants.py
â”‚   â”‚   â”œâ”€â”€ clientes.py
â”‚   â”‚   â”œâ”€â”€ productos.py
â”‚   â”‚   â”œâ”€â”€ cotizaciones.py
â”‚   â”‚   â”œâ”€â”€ facturacion.py
â”‚   â”‚   â”œâ”€â”€ guias.py
â”‚   â”‚   â”œâ”€â”€ pagos.py
â”‚   â”‚   â”œâ”€â”€ reportes.py
â”‚   â”‚   â”œâ”€â”€ dashboard.py
â”‚   â”‚   â”œâ”€â”€ superadmin.py
â”‚   â”‚   â””â”€â”€ legacy_frozen.py        # Frozen/deprecated endpoints
â”‚   â”œâ”€â”€ services/                   # Business logic layer
â”‚   â”‚   â”œâ”€â”€ facturacion_service.py  # SUNAT fiscal emission
â”‚   â”‚   â”œâ”€â”€ document_flow_service.py
â”‚   â”‚   â”œâ”€â”€ pdf_generator.py
â”‚   â”‚   â”œâ”€â”€ comunicacion_service.py
â”‚   â”‚   â”œâ”€â”€ subscription_service.py
â”‚   â”‚   â”œâ”€â”€ sunat_service.py
â”‚   â”‚   â””â”€â”€ ai_service.py           # Gemini integration (frozen)
â”‚   â”œâ”€â”€ models/                     # SQLAlchemy persistence models
â”‚   â”‚   â”œâ”€â”€ tenants.py              # Tenant, User, Subscription, AuditLog
â”‚   â”‚   â”œâ”€â”€ clientes.py             # Cliente
â”‚   â”‚   â”œâ”€â”€ productos.py            # Producto
â”‚   â”‚   â”œâ”€â”€ cotizaciones.py         # Cotizacion, CotizacionItem
â”‚   â”‚   â”œâ”€â”€ guias.py                # GuiaRemision, GuiaRemisionItem
â”‚   â”‚   â”œâ”€â”€ pagos.py                # Pago
â”‚   â”‚   â””â”€â”€ frozen.py               # Insumo, RecetaBOM, Proveedor, etc.
â”‚   â”œâ”€â”€ schemas/                    # Pydantic API contracts
â”‚   â”‚   â”œâ”€â”€ auth.py
â”‚   â”‚   â”œâ”€â”€ tenants.py
â”‚   â”‚   â”œâ”€â”€ clientes.py
â”‚   â”‚   â”œâ”€â”€ productos.py
â”‚   â”‚   â”œâ”€â”€ cotizaciones.py
â”‚   â”‚   â”œâ”€â”€ guias.py
â”‚   â”‚   â”œâ”€â”€ subscriptions.py
â”‚   â”‚   â”œâ”€â”€ onboarding.py
â”‚   â”‚   â””â”€â”€ ai.py
â”‚   â”œâ”€â”€ crud/                       # Data access layer (by domain)
â”‚   â”‚   â”œâ”€â”€ auth.py
â”‚   â”‚   â”œâ”€â”€ tenants.py
â”‚   â”‚   â”œâ”€â”€ clientes.py
â”‚   â”‚   â”œâ”€â”€ productos.py
â”‚   â”‚   â”œâ”€â”€ cotizaciones.py
â”‚   â”‚   â”œâ”€â”€ guias.py
â”‚   â”‚   â”œâ”€â”€ pagos.py
â”‚   â”‚   â””â”€â”€ reportes.py
â”‚   â”œâ”€â”€ conftest.py                 # pytest fixtures
â”‚   â””â”€â”€ requirements.txt
â”œâ”€â”€ frontend/
â”‚   â”œâ”€â”€ src/
â”‚   â”œâ”€â”€ static/
â”‚   â”œâ”€â”€ package.json
â”‚   â”œâ”€â”€ tailwind.config.js
â”‚   â””â”€â”€ vite.config.js
â”œâ”€â”€ ROADMAP.md                      # Strategic roadmap
â”œâ”€â”€ TASKS.md                        # Execution checklist
â”œâ”€â”€ BACKEND_REFACTOR_PLAN.md        # File-by-file refactor plan
â””â”€â”€ AGENTS.md                       # Agent coding instructions
```

---

## Building and Running

### Backend

```bash
cd backend

# Create virtual environment (first time)
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Set up .env file (copy from example and fill in values)
cp .env.example .env

# Run development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies (first time)
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

### Testing

```bash
cd backend
pytest
```

### Local Start Script
A `start_local.bat` file is provided for Windows to start both backend and frontend together.

---

## Development Conventions

### Architecture Rules
1. **`main.py` must stay thin** â€” only app composition, middleware, and router mounting
2. **Separate responsibilities** â€” routers (HTTP), services (business logic), crud (data access), models (persistence), schemas (API contracts)
3. **Explicit tenant safety** â€” critical CRUD operations must validate tenant ownership explicitly
4. **No hardcoded secrets** â€” all secrets come from `.env` via `pydantic-settings`
5. **Fail fast on missing config** â€” `DATABASE_URL` and `SECRET_KEY` are mandatory

### Launch-Scope Domains (Active)
- auth, tenants, customers, products/services catalog
- quotations, invoicing, shipping guides, shipping labels
- basic collections, simple dashboard, monthly Excel export
- superadmin / subscription control

### Frozen Domains (Do Not Expand)
- suppliers (Proveedores)
- raw materials / insumos
- BOM / recetas (MRP)
- production orders
- advanced inventory alerts
- advanced analytics
- AI / Gemini parsing

Frozen endpoints live in `routers/legacy_frozen.py` and are marked as `deprecated=True`.

### Document Lifecycle
- **Quotation â‰  Fiscal Document** â€” they are separate concepts
- Traceability: quotation â†’ internal order â†’ fiscal document â†’ shipping guide â†’ payment
- Do not silently mutate business meaning between document types

### Testing Priorities
- auth and tenant isolation
- quotation creation and conversion to fiscal documents
- invoice/receipt emission state guards
- shipping guide emission flow
- payment partial/full balance logic
- duplicate emission protection
- external API failure/retry handling

---

## Key Configuration

### Environment Variables (`.env`)

| Variable | Purpose |
|----------|---------|
| `ENVIRONMENT` | `development`, `staging`, `production` |
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | JWT signing secret (required) |
| `API_TOKEN` | Apisperu facturacion API token |
| `DNIRUC_TOKEN` | Apisperu DNI/RUC lookup token |
| `SUPABASE_URL` / `SUPABASE_KEY` | Supabase storage for uploaded assets |
| `INTERNAL_PROVISIONING_TOKEN` | Internal onboarding token |
| `GEMINI_API_KEY` | Gemini AI key (frozen) |

---

## Strategic Context

The project is intentionally narrowing scope. Success is defined as:
- Stable, safe backend for real paying tenants
- Reliable launch workflow (customer â†’ quote â†’ invoice â†’ guide â†’ label â†’ payment)
- Internal superadmin controls for tenant/billing management
- Code modular enough to keep evolving safely

**Not** prioritized right now: multi-plan packaging, advanced inventory, MRP, production planning, AI features, frontend redesign.

See `AGENTS.md`, `ROADMAP.md`, `TASKS.md`, and `BACKEND_REFACTOR_PLAN.md` for detailed strategic guidance.

## Qwen Added Memories
- El usuario quiere explicarme el negocio más adelante. Pendiente de escuchar la explicación antes de dar más consejos de pricing o planes.
