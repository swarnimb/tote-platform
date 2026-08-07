# Architecture: Tote-Ops

**Version:** 1.0
**Date:** 2026-03-15
**Status:** Approved

---

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Database | Supabase (PostgreSQL) |
| ORM | SQLAlchemy 2.0 (sync) + Alembic migrations |
| DB Driver | psycopg2-binary |
| Frontend | Jinja2 templates + Tailwind CSS (CDN) + HTMX (CDN) + Chart.js (CDN — dashboard revenue chart, Task 38) |
| File Storage | Supabase Storage |
| Auth | Starlette SessionMiddleware (signed cookie, 30-day expiry) |
| Deployment | Vercel (Python/WSGI) |
| PDF Extraction | None in V1 — manual entry (PDFs are scanned handwriting) |
| Email | mailto: links only — no SMTP in V1 |

---

## Key Architectural Decisions

### Sync SQLAlchemy (not async)
Single user, no concurrency requirement. Sync SQLAlchemy 2.0 is simpler and sufficient. Migrating to async later requires rewriting all DB queries — acceptable trade-off for a personal tool.

### HTML-First Responses (no JSON API)
All FastAPI routes return `TemplateResponse` (HTML) or HTML fragments (HTMX partials). No JSON API layer. Adding a mobile app later requires building a JSON API — not in scope.

### Session-Based Auth (signed cookie)
Starlette `SessionMiddleware` with `SESSION_SECRET_KEY`. Cookie stores `{"authenticated": true, "expires_at": ISO timestamp}`. 30-day expiry checked on every protected request.

### Supabase Storage for PDFs
Render filesystem is ephemeral — PDFs must be stored externally. Supabase Storage free tier (1GB) is sufficient. Path stored in DB; signed URLs generated on-demand (1-hour expiry).

---

## Project Structure

```
tote-ops/
├── app/
│   ├── main.py               # FastAPI app + middleware registration
│   ├── config.py             # Settings class — all env vars loaded here
│   ├── database.py           # SQLAlchemy engine, session factory, get_db dependency
│   ├── auth.py               # require_auth dependency, set/clear session helpers
│   ├── storage.py            # Supabase Storage: upload, signed URL, delete
│   ├── models/
│   │   ├── __init__.py       # Exports Base and all models
│   │   ├── supplier.py
│   │   ├── pickup.py
│   │   ├── gradeout.py
│   │   ├── invoice.py
│   │   ├── lead.py
│   │   └── app_settings.py   # Key-value store for app-level settings (e.g. growth_target)
│   ├── routers/
│   │   ├── auth.py           # GET/POST /login, POST /logout
│   │   ├── dashboard.py      # GET /
│   │   ├── suppliers.py      # Full CRUD + search partial
│   │   ├── pickups.py        # Full CRUD + HTMX status update
│   │   ├── gradeouts.py      # List + new form + PDF upload
│   │   ├── invoices.py       # List + generate + save + mailto
│   │   ├── leads.py          # Full CRUD + HTMX status + convert to supplier
│   │   └── growth.py         # GET /growth (render) + POST /growth/target (save target)
│   ├── services/
│   │   ├── supplier_service.py
│   │   ├── pickup_service.py
│   │   ├── gradeout_service.py
│   │   ├── invoice_service.py
│   │   ├── lead_service.py
│   │   ├── dashboard_service.py
│   │   └── growth_service.py  # Baseline stat queries + app_settings get/set
│   └── templates/
│       ├── base.html          # Sidebar layout, CDN links, mobile hamburger
│       ├── login.html
│       ├── dashboard.html
│       ├── suppliers/
│       │   ├── list.html
│       │   ├── detail.html
│       │   └── _row.html      # HTMX partial
│       ├── pickups/
│       │   ├── list.html
│       │   └── _row.html
│       ├── gradeouts/
│       │   ├── list.html
│       │   └── new.html
│       ├── invoices/
│       │   ├── list.html
│       │   └── preview.html
│       ├── leads/
│       │   ├── list.html
│       │   └── _row.html
│       └── growth/
│           └── index.html     # Target section + sliders, vanilla JS calculations
├── migrations/
│   ├── env.py                 # Alembic env — DATABASE_URL injected from env
│   └── versions/
│       ├── 0001_initial_schema.py
│       ├── 0002_gradeouts_remove_pickup_pdf.py
│       ├── 0003_gradeouts_single_junk.py
│       ├── 0004_drop_pickups_table.py
│       ├── 0005_supplier_followup_weeks_is_active.py
│       ├── 0006_supplier_action_stage.py  # rename last_contacted_date → last_pickup_date; add last_action_stage, last_action_date
│       ├── 0007_add_pickups.py            # create pickups table; add pickup_id nullable FK to gradeouts (Tasks 33–36)
│       ├── 0008_backfill_pickup_confirmed.py  # insert pickup rows for suppliers already marked pickup_confirmed
│       ├── 0009_add_app_settings.py      # app_settings table (Growth Planning) — renumbered from duplicate 0002
│       └── 0010_fix_backfill_pickup_dates.py  # set pickup created_at = supplier last_action_date for backfilled rows
├── tests/
│   ├── conftest.py            # Fixtures: test_db, test_client, authenticated_client
│   ├── test_auth.py
│   ├── test_suppliers.py
│   ├── test_pickups.py
│   ├── test_gradeouts.py
│   ├── test_invoices.py
│   ├── test_leads.py
│   └── test_growth.py
├── alembic.ini
├── requirements.txt
├── Procfile
└── .env.example
```

---

## Data Layer

See `docs/data-model.md` for full schema.

**Relationships:**
- `suppliers` → `pickups`: one-to-many (supplier has many pickups)
- `pickups` → `gradeouts`: one-to-one (UNIQUE on `gradeouts.pickup_id`)
- `suppliers` → `gradeouts`: one-to-many (denormalized FK — set automatically from pickup)
- `invoices`: standalone — computed from `gradeouts.date_received` at generation time

**Soft delete:** Suppliers only. `is_deleted=True`, `deleted_at=now()`. All other entities use hard delete.

**`app_settings` table:**
- `key` — `String(64)`, PRIMARY KEY (natural key — no UUID)
- `value` — `String(512)`, NOT NULL
- Generic key-value store for app-level configuration. Current keys: `growth_target` (float stored as string). Upserted via `growth_service.set_setting()`.

Index: none required — single-row lookups by PK.

---

## API Layer

See `docs/api-spec.md` for full route list (28 routes).

**Response patterns:**
- Standard routes: `TemplateResponse` — full page HTML
- HTMX partial routes: `HTMLResponse` — HTML fragment only (row, modal, toast)
- Redirects: `RedirectResponse` after successful mutations
- Errors: HTTP status + error message rendered in template or HTMX response

---

## Auth Flow

```
Request → SessionMiddleware (signs/reads cookie)
       → require_auth dependency
           → checks session["authenticated"] == True
           → checks session["expires_at"] > now()
           → if fail: RedirectResponse("/login")
       → Route handler
```

All routes except `GET /login`, `POST /login` include `require_auth` as a FastAPI dependency.

---

## File Upload Flow

```
POST /gradeouts (multipart/form-data)
  → validate form fields at route boundary
  → if file present:
      → storage.upload_pdf(file.read(), supplier_id, gradeout_id, file.filename)
      → returns storage_path string
  → gradeout_service.create_gradeout(db, data, pdf_path=storage_path or None)
      → within transaction: create gradeout + complete linked pickup
  → RedirectResponse("/gradeouts")
```

---

## HTMX Usage

| Interaction | Pattern |
|---|---|
| Supplier search | `GET /suppliers/search` → returns `_row.html` fragments |
| Pickup status update | `PATCH /pickups/{id}/status` → returns updated `_row.html` + optional toast |
| Lead status update | `PATCH /leads/{id}/status` → returns updated `_row.html` + optional convert modal |
| Invoice mark sent | `PATCH /invoices/{id}/sent` → returns updated row fragment |
| Form submissions | `hx-post` with `hx-target` and `hx-swap` — no full reload |
| Growth target save | `POST /growth/target` → standard form POST, `RedirectResponse` back to `GET /growth` |

Full page reloads retained for: all navigation, dashboard, initial page loads.

**Growth Planning slider pattern:** No HTMX on sliders. Jinja2 injects defaults and saved target as inline JS variables on page load. All four slider ↔ text input sync and cross-slider recalculation runs entirely in vanilla JS (≤60 lines, embedded in `growth/index.html`).

---

## Deployment

**Vercel (Python/WSGI):**
- Runtime: Python 3.11
- Start command (Procfile): `gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker`
- Environment variables set in Vercel dashboard (never in code)

**Supabase:**
- PostgreSQL database — connection via `DATABASE_URL`
- Storage bucket `gradeout-pdfs` — created manually in Supabase dashboard
- Migrations run manually via Vercel shell or local CLI: `alembic upgrade head`

**Required env vars:**
```
DATABASE_URL
SUPABASE_URL
SUPABASE_KEY
SUPABASE_STORAGE_BUCKET
APP_PASSWORD
SESSION_SECRET_KEY
INVOICE_RECIPIENT_EMAIL
```

---

## Config Constants (app/config.py)

| Constant | Value | Source |
|---|---|---|
| `TOTE_RATE` | `5` | Config constant (not env var — business rule) |
| `FOLLOWUP_DAYS_THRESHOLD` | `60` | Config constant |
| `UPCOMING_PICKUP_DAYS` | `14` | Config constant |
| `SESSION_EXPIRY_DAYS` | `30` | Config constant |
| `PDF_SIGNED_URL_EXPIRY_SECONDS` | `3600` | Config constant |
