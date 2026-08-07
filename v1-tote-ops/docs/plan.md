# Plan: Tote-Ops

**Version:** 1.0
**Date:** 2026-03-15
**Status:** Approved — ready for development

---

## Task Status Legend
- [ ] Not started
- [~] In progress
- [x] Complete

---

## Task 1: Project skeleton
**Status:** [x]

**Files:**
- `app/__init__.py` — create (empty)
- `app/main.py` — create
- `app/config.py` — create
- `requirements.txt` — create
- `Procfile` — create

**Functions to implement:**
- `app/main.py`: FastAPI app instantiation, `SessionMiddleware` registration, all routers registered (stubs acceptable in this task), Jinja2 `templates` directory mounted
- `app/config.py`: `Settings` class — loads `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_STORAGE_BUCKET`, `APP_PASSWORD`, `SESSION_SECRET_KEY`, `INVOICE_RECIPIENT_EMAIL` from `os.environ`; also defines constants `TOTE_RATE=5`, `FOLLOWUP_DAYS_THRESHOLD=60`, `UPCOMING_PICKUP_DAYS=14`, `SESSION_EXPIRY_DAYS=30`, `PDF_SIGNED_URL_EXPIRY_SECONDS=3600`

**`requirements.txt` contents:**
```
fastapi
uvicorn[standard]
gunicorn
sqlalchemy
alembic
psycopg2-binary
supabase
python-multipart
jinja2
python-dotenv
pytest
httpx
```

**`Procfile`:**
```
web: gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker
```

**Acceptance criteria:**
- [x] `uvicorn app.main:app --reload` starts without errors
- [x] All env vars loaded from `.env` via `python-dotenv` in development
- [x] `Settings` raises `KeyError` with missing var name if any required env var is absent — no silent defaults (EH-01, CQ-04)
- [x] No env var values hardcoded anywhere (SEC-01)
- [x] `SessionMiddleware` registered with `secret_key=settings.SESSION_SECRET_KEY`
- [x] No function exceeds 50 lines (CQ-01)

**Tests required:**
- `test_config` → `loads all required env vars from environment`
- `test_config` → `raises KeyError on missing required env var`

**Depends on:** None

---

## Task 2: Database setup
**Status:** [x]

**Files:**
- `app/database.py` — create
- `alembic.ini` — create (via `alembic init migrations`)
- `migrations/env.py` — modify to inject `DATABASE_URL` from env

**Functions to implement:**
- `get_engine() -> Engine` — creates SQLAlchemy engine from `settings.DATABASE_URL`
- `get_session_factory(engine: Engine) -> sessionmaker` — returns bound sessionmaker
- `get_db() -> Generator[Session, None, None]` — FastAPI dependency, yields session, closes in `finally` block

**Acceptance criteria:**
- [ ] `get_db()` closes session in `finally` — no leaked connections (EH-01)
- [ ] `DATABASE_URL` from `settings` — not hardcoded (SEC-01)
- [ ] Alembic `env.py` imports `Base.metadata` from `app.models` for autogenerate support
- [ ] `alembic.ini` `sqlalchemy.url` set to placeholder — actual URL injected via env in `migrations/env.py` (SEC-01)
- [ ] `get_db` is a generator function using `yield` — not a context manager

**Tests required:**
- `test_database` → `get_db yields a session and closes on exit`
- `test_database` → `raises on invalid DATABASE_URL format`

**Depends on:** Task 1

---

## Task 3: SQLAlchemy models
**Status:** [x]

**Files:**
- `app/models/__init__.py` — create (exports `Base`, imports all models so Alembic sees them)
- `app/models/supplier.py` — create
- `app/models/pickup.py` — create
- `app/models/gradeout.py` — create
- `app/models/invoice.py` — create
- `app/models/lead.py` — create

**Functions to implement (class definitions):**

`Supplier`: all columns per `docs/data-model.md`. `is_deleted=False`, `created_at/updated_at` via `server_default=func.now()`.

`Pickup`: all columns. `status` as `Column(Enum('contacted','confirmed','completed','cancelled', name='pickup_status'))`. Relationship to `Supplier`.

`Gradeout`: all columns. `UniqueConstraint('pickup_id')`. FK to `pickups.id` and `suppliers.id`. Relationships to `Pickup` and `Supplier`.

`Invoice`: all columns. `UniqueConstraint('month')`. `total_revenue` as `Column(Numeric(10,2))`.

`Lead`: all columns. `outreach_status` as `Column(Enum('research','contacted','responded','not_interested','active_supplier', name='lead_status'), default='research')`.

**Acceptance criteria:**
- [ ] All PKs use `Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)`
- [ ] `UNIQUE` constraint on `gradeouts.pickup_id` enforced at DB level (not just application level)
- [ ] `UNIQUE` constraint on `invoices.month` enforced at DB level
- [ ] `updated_at` uses `onupdate=func.now()` on all models with that column
- [ ] `Base` exported from `app/models/__init__.py` — single source (CQ-03)
- [ ] All model files under 200 lines (CQ-02)
- [ ] No circular imports between model files

**Tests required:**
- `test_models` → `Supplier instantiates with required fields`
- `test_models` → `Gradeout raises IntegrityError on duplicate pickup_id`

**Depends on:** Task 2

---

## Task 4: Initial Alembic migration
**Status:** [x]

**Files:**
- `migrations/versions/0001_initial_schema.py` — create (generated, then verified)

**Functions to implement:**
- `upgrade()` — creates all 5 tables with correct columns, types, constraints, indexes
- `downgrade()` — drops all 5 tables in reverse dependency order

**Indexes to include:**
- `suppliers`: `idx_suppliers_is_deleted`
- `pickups`: `idx_pickups_supplier_id`, `idx_pickups_status`
- `gradeouts`: `idx_gradeouts_supplier_id`, `idx_gradeouts_date_received`
- `invoices`: `idx_invoices_month`
- `leads`: `idx_leads_outreach_status`

**Acceptance criteria:**
- [ ] `alembic upgrade head` runs without errors against Supabase PostgreSQL
- [ ] `alembic downgrade base` runs without errors
- [ ] All UNIQUE constraints in migration match model definitions
- [ ] Migration file contains no credentials (SEC-01)
- [ ] `alembic.ini` is NOT in `.env` — URL injected only via `migrations/env.py`

**Tests required:**
- Manual: `alembic upgrade head` → verify tables in Supabase dashboard

**Depends on:** Task 3

---

## Task 5: Auth middleware + login routes + login template
**Status:** [x]

**Files:**
- `app/auth.py` — create
- `app/routers/auth.py` — create
- `app/templates/login.html` — create
**Specialist:** @ui-tote-ops

**Functions to implement:**
- `require_auth(request: Request) -> None` — checks `request.session.get("authenticated")` and parses `request.session.get("expires_at")`. Raises `RedirectResponse("/login", status_code=302)` if not authenticated or expired.
- `set_session(request: Request) -> None` — sets `session["authenticated"] = True`, `session["expires_at"] = (datetime.utcnow() + timedelta(days=SESSION_EXPIRY_DAYS)).isoformat()`
- `clear_session(request: Request) -> None` — calls `request.session.clear()`
- `GET /login` — renders `login.html`; redirects to `/` if already authenticated
- `POST /login` — reads `password` from form data; compares to `settings.APP_PASSWORD`; calls `set_session` and redirects to `/` on success; re-renders `login.html` with `error="Incorrect password"` on failure
- `POST /logout` — calls `clear_session`, returns `RedirectResponse("/login")`

**Acceptance criteria:**
- [ ] `APP_PASSWORD` compared from `settings` — never hardcoded (SEC-01)
- [ ] Wrong password: error message "Incorrect password" — does not indicate whether user/password was wrong specifically (SEC-05)
- [ ] Session cookie is HTTP-only (Starlette SessionMiddleware default — verify in code)
- [ ] `require_auth` checks both `authenticated` flag AND `expires_at` timestamp
- [ ] Expired session clears session data and redirects to `/login`
- [ ] Login template: centered card, Inter font, password field, blue submit button, error message area (@ui-tote-ops)
- [ ] `SESSION_EXPIRY_DAYS` from config — not hardcoded (CQ-04)

**Tests required:**
- `test_auth` → `POST /login with correct password sets session and redirects to /`
- `test_auth` → `POST /login with wrong password returns 200 with error message`
- `test_auth` → `GET / without session redirects to /login`
- `test_auth` → `GET / with expired session redirects to /login`
- `test_auth` → `POST /logout clears session and redirects to /login`

**Depends on:** Task 1

---

## Task 6: Base HTML template
**Status:** [x]

**Files:**
- `app/templates/base.html` — create
**Specialist:** @ui-tote-ops

**What it must include:**
- `<head>`: Tailwind CSS CDN, HTMX CDN, Inter Google Font CDN, meta viewport tag
- Fixed left sidebar (240px desktop): ToteOps logo block, 6 nav items (Dashboard, Suppliers, Pickups, Gradeouts, Invoices, Leads), user footer with "Logout" POST form
- Mobile top bar (hidden desktop, visible ≤768px): hamburger button + "ToteOps" text
- Sidebar collapses off-screen on ≤768px, toggled by hamburger — vanilla JS only (≤50 lines)
- `{% block content %}{% endblock %}` in `<main>` area
- Active nav item determined by `request.url.path` — `eff6ff` background, `2563eb` text
- Toast container `#toast-container` fixed top-right for HTMX toast notifications

**Acceptance criteria:**
- [ ] Tailwind via CDN — no build step, no config file (CQ-04)
- [ ] HTMX via CDN
- [ ] Sidebar collapses at ≤768px (iPad breakpoint)
- [ ] Active nav detection uses `request.url.path.startswith("/route")`
- [ ] All nav tap targets ≥44px height
- [ ] Logout uses `<form method="post" action="/logout">` — not a link
- [ ] Sidebar JS ≤50 lines, no external JS libraries (CQ-01)

**Tests required:**
- Manual: verify at 768px viewport using Playwright screenshot

**Depends on:** Task 5

---

## Task 7: Dashboard page
**Status:** [x]

**Files:**
- `app/routers/dashboard.py` — create
- `app/services/dashboard_service.py` — create
- `app/templates/dashboard.html` — create
**Specialist:** @ui-tote-ops

**Functions to implement:**
- `get_monthly_stats(db: Session, year: int, month: int) -> dict` — returns `{"total_usable_totes": int, "revenue": float}` from gradeouts in that month
- `get_active_supplier_count(db: Session) -> int` — count of non-deleted suppliers
- `get_upcoming_pickups_count(db: Session) -> int` — pickups with status in `(contacted, confirmed)` and `pickup_date` ≤ today + `UPCOMING_PICKUP_DAYS`
- `get_needs_followup_suppliers(db: Session) -> list[dict]` — suppliers with ≥1 completed pickup where most recent `pickup.pickup_date` < today - `FOLLOWUP_DAYS_THRESHOLD`; excludes soft-deleted
- `get_upcoming_pickups(db: Session) -> list[dict]` — pickups with status in `(contacted, confirmed)`, `pickup_date` ≤ today + `UPCOMING_PICKUP_DAYS`, sorted by `pickup_date` asc
- `GET /` route — calls all 5 service functions, passes results to `dashboard.html`

**Acceptance criteria:**
- [ ] All queries use SQLAlchemy ORM — no string-concatenated SQL (SEC-03)
- [ ] `get_needs_followup_suppliers` excludes suppliers with zero completed pickups
- [ ] `get_needs_followup_suppliers` excludes soft-deleted suppliers
- [ ] Revenue = `total_usable_totes * settings.TOTE_RATE` — not `* 5` inline (CQ-04)
- [ ] `FOLLOWUP_DAYS_THRESHOLD` and `UPCOMING_PICKUP_DAYS` from config (CQ-04)
- [ ] Each service function ≤50 lines (CQ-01)
- [ ] 4 stat cards + 2 panels match design system (@ui-tote-ops)
- [ ] "Send Email" button on follow-up rows generates mailto: link via `build_followup_mailto()`

**Tests required:**
- `test_dashboard` → `get_needs_followup_suppliers returns supplier with last pickup >60 days ago`
- `test_dashboard` → `get_needs_followup_suppliers excludes supplier with no completed pickups`
- `test_dashboard` → `get_monthly_stats returns correct revenue for current month`

**Depends on:** Task 6, Task 4

---

## Task 8: Suppliers — list + CRUD
**Status:** [x]

**Files:**
- `app/routers/suppliers.py` — create
- `app/services/supplier_service.py` — create
- `app/templates/suppliers/list.html` — create
- `app/templates/suppliers/_row.html` — create
**Specialist:** @ui-tote-ops

**Functions to implement:**
- `get_suppliers(db: Session, search: str | None = None, filter_by: str | None = None) -> list[Supplier]` — returns non-deleted suppliers; `filter_by` values: `needs_followup`, `hazmat`
- `create_supplier(db: Session, data: dict) -> Supplier` — validates `company_name` and `location` not empty; creates and returns record
- `update_supplier(db: Session, supplier_id: UUID, data: dict) -> Supplier` — updates fields; raises `NotFoundError` if not found
- `soft_delete_supplier(db: Session, supplier_id: UUID) -> None` — sets `is_deleted=True`, `deleted_at=now()`; raises `NotFoundError` if not found
- Routes: `GET /suppliers`, `POST /suppliers`, `GET /suppliers/search` (HTMX), `PUT /suppliers/{id}`, `DELETE /suppliers/{id}`

**Acceptance criteria:**
- [ ] Search uses `ilike(f"%{search}%")` — not string concatenation in query (SEC-03)
- [ ] `create_supplier` raises `ValueError("company_name is required")` if empty; route returns 422 (SEC-02, EH-05)
- [ ] `location` same validation as `company_name`
- [ ] Soft delete does not delete or modify linked pickups or gradeouts
- [ ] `GET /suppliers/search` returns `_row.html` fragment (HTMX), not full page
- [ ] `bol_email` field disabled in template when `bol_same_as_primary` is checked
- [ ] All inputs validated at route boundary before service call (SEC-02)
- [ ] Each service function ≤50 lines (CQ-01); each file ≤300 lines (CQ-02)

**Tests required:**
- `test_suppliers` → `create_supplier saves record with required fields`
- `test_suppliers` → `create_supplier raises ValueError when company_name is empty`
- `test_suppliers` → `soft_delete_supplier sets is_deleted True and preserves linked pickups`
- `test_suppliers` → `get_suppliers excludes soft-deleted records`
- `test_suppliers` → `get_suppliers returns only hazmat suppliers when filter is hazmat`

**Depends on:** Task 7

---

## Task 9: Supplier detail page
**Status:** [x]

**Files:**
- `app/templates/suppliers/detail.html` — create
- `app/routers/suppliers.py` — modify (add `GET /suppliers/{id}`)
- `app/services/supplier_service.py` — modify (add detail query + mailto builder)
**Specialist:** @ui-tote-ops

**Functions to implement:**
- `get_supplier_by_id(db: Session, supplier_id: UUID) -> Supplier` — raises `NotFoundError` if not found or `is_deleted=True`
- `get_supplier_recent_pickups(db: Session, supplier_id: UUID, limit: int = 5) -> list[Pickup]` — sorted by `created_at` desc
- `build_followup_mailto(supplier: Supplier, days_since_pickup: int | None) -> str` — builds URL-encoded `mailto:` string; fallback `contact_name="there"` if missing; omits days line if `days_since_pickup` is None
- `GET /suppliers/{id}` — calls all three functions, renders `detail.html`

**Acceptance criteria:**
- [ ] `get_supplier_by_id` raises `NotFoundError` (custom error class) if not found or soft-deleted; route returns 404 (EH-05)
- [ ] `build_followup_mailto` encodes subject and body with `urllib.parse.quote` (SEC-02)
- [ ] mailto: link opens mail client with pre-filled To, Subject, Body
- [ ] Edit form pre-fills all current supplier values
- [ ] Delete confirmation modal shown before soft delete executes
- [ ] Detail page shows last 5 pickups

**Tests required:**
- `test_suppliers` → `build_followup_mailto returns correctly encoded mailto URL`
- `test_suppliers` → `build_followup_mailto uses "there" when contact_name is missing`
- `test_suppliers` → `GET /suppliers/{id} returns 404 for soft-deleted supplier`

**Depends on:** Task 8

---

## Task 10: Pickups — list + CRUD
**Status:** [x]

**Files:**
- `app/routers/pickups.py` — create
- `app/services/pickup_service.py` — create
- `app/templates/pickups/list.html` — create
- `app/templates/pickups/_row.html` — create
**Specialist:** @ui-tote-ops

**Functions to implement:**
- `get_pickups(db: Session, status: str | None = None, supplier_id: UUID | None = None) -> list[Pickup]`
- `create_pickup(db: Session, data: dict) -> Pickup` — validates `supplier_id` exists and is not deleted; pre-fills `is_hazmat` from supplier
- `update_pickup(db: Session, pickup_id: UUID, data: dict) -> Pickup`
- `update_pickup_status(db: Session, pickup_id: UUID, status: str) -> Pickup` — validates status is valid enum value; raises `ValueError` if not
- `delete_pickup(db: Session, pickup_id: UUID) -> None` — raises `ConflictError` if gradeout linked
- Routes: `GET /pickups`, `POST /pickups`, `PATCH /pickups/{id}`, `PATCH /pickups/{id}/status` (HTMX), `DELETE /pickups/{id}`

**Acceptance criteria:**
- [ ] Status validated against `('contacted','confirmed','completed','cancelled')` — returns 422 on invalid (SEC-02)
- [ ] `is_hazmat` pre-fills from `supplier.is_hazmat` on create
- [ ] `PATCH /pickups/{id}/status` returns HTMX `_row.html` fragment
- [ ] When status=`completed`: HTMX response includes toast "Pickup complete — upload the gradeout?" with link `/gradeouts/new?pickup_id={id}`
- [ ] `delete_pickup` raises `ConflictError` with message if gradeout linked; route returns 409 (EH-05)
- [ ] Supplier dropdown shows non-deleted suppliers only
- [ ] Each service function ≤50 lines (CQ-01)

**Tests required:**
- `test_pickups` → `create_pickup saves with status contacted by default`
- `test_pickups` → `update_pickup_status raises ValueError on invalid status`
- `test_pickups` → `delete_pickup raises ConflictError when gradeout is linked`
- `test_pickups` → `PATCH status to completed returns fragment with gradeout upload link`

**Depends on:** Task 8

---

## Task 11: Supabase Storage helper
**Status:** [x]

**Files:**
- `app/storage.py` — create

**Functions to implement:**
- `get_storage_client() -> StorageClient` — initializes `supabase.create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY).storage`
- `upload_pdf(file_bytes: bytes, supplier_id: str, gradeout_id: str, filename: str) -> str` — uploads to `{SUPABASE_STORAGE_BUCKET}/{supplier_id}/{gradeout_id}.pdf`; returns storage path; raises `StorageError` on failure
- `get_signed_url(storage_path: str, expires_in_seconds: int = PDF_SIGNED_URL_EXPIRY_SECONDS) -> str` — generates signed URL; raises `StorageError` if path not found
- `delete_file(storage_path: str) -> None` — deletes from storage; logs warning if not found but does not raise

**Acceptance criteria:**
- [ ] `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_STORAGE_BUCKET` all from `settings` (SEC-01)
- [ ] `upload_pdf` raises `StorageError` with `{"operation": "upload_pdf", "supplier_id": ..., "filename": ...}` context on failure (EH-01, EH-02)
- [ ] `StorageError` is a custom error class extending `Exception` (EH-05)
- [ ] `get_signed_url` raises `StorageError` if path not found (EH-01)
- [ ] `delete_file` logs warning on missing file but does not raise — idempotent delete (EH-01)
- [ ] Each function ≤50 lines (CQ-01)

**Tests required:**
- `test_storage` → `upload_pdf returns correct storage path on success` (mock supabase client)
- `test_storage` → `upload_pdf raises StorageError on client failure`
- `test_storage` → `get_signed_url returns URL string on success`
- `test_storage` → `delete_file logs warning instead of raising when file not found`

**Depends on:** Task 1

---

## Task 12: Gradeouts — list + new form + PDF upload
**Status:** [x]

**Files:**
- `app/routers/gradeouts.py` — create
- `app/services/gradeout_service.py` — create
- `app/templates/gradeouts/list.html` — create
- `app/templates/gradeouts/new.html` — create
**Specialist:** @ui-tote-ops

**Functions to implement:**
- `get_gradeouts(db: Session, supplier_id: UUID | None = None, month: date | None = None) -> list[Gradeout]`
- `get_pickups_without_gradeout(db: Session) -> list[Pickup]` — pickups with no linked gradeout, status in `(contacted, confirmed, completed)`
- `create_gradeout(db: Session, data: dict, pdf_path: str | None = None) -> Gradeout` — sets `supplier_id` from `pickup.supplier_id`; within single transaction: creates gradeout + calls `_complete_pickup()`
- `_complete_pickup(db: Session, pickup_id: UUID, pickup_date: date) -> None` — sets `pickup.status='completed'`, `pickup.pickup_date=pickup_date`; private helper, called only from `create_gradeout`
- `delete_gradeout(db: Session, gradeout_id: UUID) -> str | None` — deletes record, returns `pdf_storage_path` if present (caller handles Storage deletion)
- Routes: `GET /gradeouts`, `GET /gradeouts/new`, `POST /gradeouts`, `GET /gradeouts/{id}`, `DELETE /gradeouts/{id}`

**Acceptance criteria:**
- [ ] PDF upload optional — `POST /gradeouts` accepts form with no file (ASSUMPTION-03)
- [ ] PDF stored via `storage.upload_pdf()` only — never `open()` to local filesystem (ASSUMPTION-03)
- [ ] `supplier_id` set from `pickup.supplier_id` in service — never from request data (SEC-02)
- [ ] All tote counts validated ≥ 0 at route boundary (SEC-02)
- [ ] Warning shown in template if `total_usable > good_washable + good_cage` — not a hard block
- [ ] `create_gradeout` and `_complete_pickup` execute in same SQLAlchemy transaction (EH-01)
- [ ] `get_pickups_without_gradeout` uses LEFT JOIN or subquery — not Python-side filtering (CQ-08)
- [ ] `?pickup_id=` query param pre-selects pickup in dropdown

**Tests required:**
- `test_gradeouts` → `create_gradeout sets supplier_id from pickup supplier_id`
- `test_gradeouts` → `create_gradeout sets linked pickup status to completed`
- `test_gradeouts` → `create_gradeout succeeds with no PDF file`
- `test_gradeouts` → `POST /gradeouts returns 422 when tote_275_total_usable is negative`

**Depends on:** Task 10, Task 11

---

## Task 13: Invoices — generation + preview + mailto
**Status:** [x]

**Files:**
- `app/routers/invoices.py` — create
- `app/services/invoice_service.py` — create
- `app/templates/invoices/list.html` — create
- `app/templates/invoices/preview.html` — create
**Specialist:** @ui-tote-ops

**Functions to implement:**
- `get_invoices(db: Session) -> list[Invoice]` — sorted by month descending
- `get_invoice_by_month(db: Session, month: date) -> Invoice | None`
- `generate_invoice_preview(db: Session, month: date) -> dict` — queries gradeouts where `date_received` in that month; returns `{"rows": list[dict], "totals": dict}`; raises `ValueError(f"No gradeouts found for {month.strftime('%B %Y')}")` if empty
- `save_invoice(db: Session, month: date, preview_data: dict) -> Invoice` — creates record; raises `ConflictError` if invoice for month exists
- `mark_invoice_sent(db: Session, invoice_id: UUID) -> Invoice` — sets `sent_at = datetime.utcnow()`
- `build_invoice_mailto(invoice: Invoice, rows: list[dict]) -> str` — builds URL-encoded mailto: with `settings.INVOICE_RECIPIENT_EMAIL`, subject, plain-text body
- Routes: `GET /invoices`, `POST /invoices/generate`, `POST /invoices`, `PATCH /invoices/{id}/sent`

**Acceptance criteria:**
- [ ] `INVOICE_RECIPIENT_EMAIL` from `settings` — not hardcoded (SEC-01, CQ-04)
- [ ] One invoice per month — `save_invoice` raises `ConflictError` if exists; `POST /invoices/generate` returns existing preview (no duplicate)
- [ ] `generate_invoice_preview` raises `ValueError` if no gradeouts — route shows error, no invoice created
- [ ] Revenue per row = `(totes_275_total_usable + totes_330_total_usable) * settings.TOTE_RATE` (CQ-04)
- [ ] `build_invoice_mailto` encodes subject and body with `urllib.parse.quote` (SEC-02)
- [ ] Each service function ≤50 lines (CQ-01)

**Tests required:**
- `test_invoices` → `generate_invoice_preview returns correct totals for month`
- `test_invoices` → `generate_invoice_preview raises ValueError when no gradeouts exist`
- `test_invoices` → `save_invoice raises ConflictError when invoice for month already exists`
- `test_invoices` → `build_invoice_mailto returns correctly encoded mailto URL`
- `test_invoices` → `mark_invoice_sent sets sent_at timestamp`

**Depends on:** Task 12

---

## Task 14: Leads — list + CRUD + convert to supplier
**Status:** [x]

**Files:**
- `app/routers/leads.py` — create
- `app/services/lead_service.py` — create
- `app/templates/leads/list.html` — create
- `app/templates/leads/_row.html` — create
**Specialist:** @ui-tote-ops

**Functions to implement:**
- `get_leads(db: Session, status: str | None = None) -> list[Lead]`
- `create_lead(db: Session, data: dict) -> Lead` — `company_name` required; raises `ValueError` if empty
- `update_lead(db: Session, lead_id: UUID, data: dict) -> Lead`
- `update_lead_status(db: Session, lead_id: UUID, status: str) -> tuple[Lead, bool]` — returns `(lead, should_prompt_convert)` where `should_prompt_convert = (status == 'active_supplier')`
- `delete_lead(db: Session, lead_id: UUID) -> None`
- `build_supplier_prefill(lead: Lead) -> dict` — maps `company_name`, `location`, `contact_name`, `contact_phone`, `contact_email` to supplier form field names
- Routes: `GET /leads`, `POST /leads`, `PATCH /leads/{id}`, `PATCH /leads/{id}/status` (HTMX), `DELETE /leads/{id}`

**Acceptance criteria:**
- [ ] `PATCH /leads/{id}/status` returns HTMX `_row.html` fragment
- [ ] When `active_supplier`: HTMX response includes convert modal with pre-filled supplier form fields
- [ ] Convert modal POSTs to `/suppliers` — creates supplier; does NOT delete or modify lead
- [ ] `build_supplier_prefill` maps all 5 contact fields — no data lost (CQ-06)
- [ ] Status validated against enum — returns 422 on invalid (SEC-02)
- [ ] Each service function ≤50 lines (CQ-01)

**Tests required:**
- `test_leads` → `create_lead raises ValueError when company_name is empty`
- `test_leads` → `update_lead_status returns should_prompt_convert True when set to active_supplier`
- `test_leads` → `update_lead_status returns should_prompt_convert False for all other statuses`
- `test_leads` → `build_supplier_prefill maps all contact fields correctly`

**Depends on:** Task 8

---

## Task 15: Tests
**Status:** [x]

**Files:**
- `tests/conftest.py` — create
- `tests/test_auth.py` — create (consolidate from Task 5)
- `tests/test_suppliers.py` — create (consolidate from Tasks 8, 9)
- `tests/test_pickups.py` — create (consolidate from Task 10)
- `tests/test_gradeouts.py` — create (consolidate from Task 12)
- `tests/test_invoices.py` — create (consolidate from Task 13)
- `tests/test_leads.py` — create (consolidate from Task 14)

**Functions to implement:**
- `conftest.py`:
  - `test_db` fixture — SQLite in-memory engine + `Base.metadata.create_all()` + session; scope=`function`
  - `test_client` fixture — FastAPI `TestClient` with `get_db` dependency overridden to use `test_db`
  - `authenticated_client` fixture — `test_client` with session cookie pre-set

**Acceptance criteria:**
- [ ] All tests use `test_db` fixture — no real Supabase/PostgreSQL calls (TS-03)
- [ ] Supabase Storage calls mocked in gradeout tests — `storage.upload_pdf` patched (TS-03)
- [ ] All test names follow `[function/route] [does X] when [condition]` (TS-02)
- [ ] Each test uses `beforeEach`-equivalent (`test_db` fixture is function-scoped — fresh DB per test) (TS-05)
- [ ] Auth tests cover all 5 cases from Task 5 (TS-04)
- [ ] All data write operations have ≥1 happy path + ≥1 error case (TS-01)
- [ ] `pytest tests/` runs all tests from project root

**Tests required:** All tests specified in Tasks 1–14.

**Depends on:** Tasks 1–14

---

## Task 16: Render deployment
**Status:** [x]

**Files:**
- `Procfile` — verify (from Task 1)
- `.env.example` — verify all vars present

**Steps:**
1. Create GitHub repo, push all project files (verify `.gitignore` excludes `CLAUDE.md`, `manifest.md`, `.env`, etc.)
2. Create Render Web Service — connect GitHub repo, set runtime to Python 3.11
3. Set env vars in Render dashboard: `DATABASE_URL` (from Supabase Settings → Database → Connection string), `SUPABASE_URL`, `SUPABASE_KEY` (from Supabase Settings → API), `SUPABASE_STORAGE_BUCKET=gradeout-pdfs`, `APP_PASSWORD`, `SESSION_SECRET_KEY` (generate: `python -c "import secrets; print(secrets.token_hex(32))"`), `INVOICE_RECIPIENT_EMAIL`
4. In Supabase dashboard: create Storage bucket named `gradeout-pdfs` (set to private)
5. Run `alembic upgrade head` via Render shell (or add as pre-deploy command)
6. Verify app loads and login works

**Acceptance criteria:**
- [ ] App accessible via Render URL
- [ ] Login works with `APP_PASSWORD`
- [ ] Dashboard loads without errors
- [ ] PDF upload stores file in Supabase Storage (test with dummy file)
- [ ] No env vars in source code or Render build logs (SEC-01)
- [ ] `.env` not committed — confirmed in `.gitignore` (SEC-07)
- [ ] `CLAUDE.md` and `manifest.md` not committed (SEC-07)

**Depends on:** Task 15

---

## Task 17: AppSettings model + migration
**Status:** [x]

**Files:**
- `app/models/app_settings.py` — create
- `app/models/__init__.py` — modify (add AppSettings import)
- `migrations/versions/0002_add_app_settings.py` — create

**Functions to implement:**
- `AppSettings` model class: `key String(64) PRIMARY KEY`, `value String(512) NOT NULL`. No UUID — key is natural PK.

**Acceptance criteria:**
- [ ] `AppSettings` imported in `app/models/__init__.py` alongside existing models
- [ ] Migration creates `app_settings` table with `key` as string PK, `value` NOT NULL
- [ ] `alembic upgrade head` runs without errors against Supabase PostgreSQL
- [ ] `alembic downgrade` removes `app_settings` table cleanly
- [ ] No UUID column — no `id` field (CQ-03)
- [ ] Migration file contains no credentials (SEC-01)

**Tests required:**
- `test_growth` → `AppSettings instantiates with key and value`
- `test_growth` → `duplicate key raises IntegrityError`

**Depends on:** Task 4

---

## Task 18: Growth Planning — service, router, template, nav
**Status:** [x]

**Files:**
- `app/services/growth_service.py` — create
- `app/routers/growth.py` — create
- `app/templates/growth/index.html` — create
- `app/main.py` — modify (register growth router)
- `app/templates/base.html` — modify (add Growth Planning as 6th nav item)
- `tests/test_growth.py` — create
**Specialist:** @ui-tote-ops

**Functions to implement:**
- `get_avg_shipments_per_supplier(db: Session) -> float` — count gradeouts per active (non-deleted, `is_active=True`) supplier over last 12 months, return average rounded to 1 decimal; returns `0.0` if no data
- `get_avg_totes_per_shipment(db: Session) -> float` — average of `(totes_275_total_usable + totes_330_total_usable)` per gradeout, all time, rounded to 1 decimal; returns `0.0` if no gradeouts
- `get_setting(db: Session, key: str) -> str | None` — returns value or `None` if key absent
- `set_setting(db: Session, key: str, value: str) -> None` — upsert: update if exists, insert if not
- `GET /growth` — calls `get_active_supplier_count` (import from `dashboard_service`), `get_avg_shipments_per_supplier`, `get_avg_totes_per_shipment`, `get_setting(db, "growth_target")`; passes all to `growth/index.html`
- `POST /growth/target` — reads `target` from form data; validates `target >= 0`; calls `set_setting(db, "growth_target", str(target))`; returns `RedirectResponse("/growth")`

**Template — `growth/index.html`:**
- Extends `base.html`
- **Section 1 — Target:** displays saved target as currency; edit button reveals inline input + save form; empty state "No target set yet" when `growth_target` is `None`
- **Section 2 — Sliders:** 4 rows, each with: label, `<input type="range">`, companion `<input type="number">`, unit label. Defaults injected via Jinja2 as inline JS variables.
- **Vanilla JS** (embedded, ≤60 lines): bidirectional slider ↔ text sync; recalculation on input — moving Suppliers recalculates Shipments, moving any other recalculates Suppliers; clamps slider to max, shows actual value in text input; shows `"—"` in dependent field when Totes=0 or Revenue/Tote=0

**Acceptance criteria:**
- [ ] Target saves to `app_settings` and reloads correctly on next visit (CQ-04)
- [ ] Target `< 0` rejected at route boundary — returns 422 (SEC-02)
- [ ] Page loads with DB-derived defaults for all 4 sliders
- [ ] Moving Suppliers slider recalculates Shipments/Supplier in real time
- [ ] Moving Shipments, Totes, or Revenue/Tote recalculates Suppliers in real time
- [ ] Slider and companion text input stay in sync — changing either updates the other
- [ ] No target set → empty state shown in Section 1
- [ ] Totes=0 or Revenue/Tote=0 → dependent field shows "—", no JS error (EH-01)
- [ ] Calculated value exceeding slider max → slider clamps, text input shows actual value
- [ ] Growth Planning is 6th nav item in `base.html`, active state matches existing nav pattern
- [ ] All DB queries use ORM — no raw SQL (SEC-03)
- [ ] Each service function ≤50 lines (CQ-01)
- [ ] JS ≤60 lines, no external JS libraries (CQ-01)
- [ ] `get_active_supplier_count` imported from `dashboard_service` — not duplicated (CQ-03)

**Tests required:**
- `test_growth` → `get_avg_shipments_per_supplier returns correct average for active suppliers in last 12 months`
- `test_growth` → `get_avg_shipments_per_supplier returns 0.0 when no gradeouts exist`
- `test_growth` → `get_avg_totes_per_shipment returns correct average across all gradeouts`
- `test_growth` → `get_avg_totes_per_shipment returns 0.0 when no gradeouts exist`
- `test_growth` → `set_setting creates new key when absent`
- `test_growth` → `set_setting updates existing key without creating duplicate`
- `test_growth` → `POST /growth/target saves value and redirects to /growth`
- `test_growth` → `POST /growth/target returns 422 when target is negative`

**Depends on:** Task 17, Task 6, Task 7

---

## Task 19: Dashboard — washable/cage display update
**Status:** [x]

**Files:**
- `app/services/dashboard_service.py` — modify
- `app/templates/dashboard.html` — modify
**Specialist:** @ui-tote-ops

**Functions to implement:**
- Update `get_followup_suppliers` — replace `avg_275`, `avg_330` with `avg_275_washable`, `avg_275_cage`, `avg_330_washable`, `avg_330_cage` (4 separate `func.avg()` calls on the respective columns)

**Acceptance criteria:**
- [ ] Recent Gradeouts table: "275 Usable" / "330 Usable" columns replaced with "275 W/C" / "330 W/C" — each cell shows `{washable} / {cage}`
- [ ] Follow-Up panel: "275/330 Avg" column replaced with "275 W/C Avg" and "330 W/C Avg" — each cell shows `{avg_washable}w {avg_cage}c`
- [ ] Revenue column unchanged — still computed from total_usable
- [ ] "Totes" stat card unchanged
- [ ] `get_followup_suppliers` returns 4 avg values — no Python-side calculation (CQ-08)
- [ ] Each service function ≤50 lines (CQ-01)
- [ ] Template renders correctly at 768px iPad viewport (@ui-tote-ops)

**Tests required:**
- `test_dashboard` → `get_followup_suppliers returns avg_275_washable and avg_275_cage separately`

**Depends on:** Task 7

---

## Task 20: Suppliers list — remove Contact column + washable/cage averages
**Status:** [x]

**Files:**
- `app/services/supplier_service.py` — modify
- `app/templates/suppliers/list.html` — modify
- `app/templates/suppliers/_row.html` — modify
**Specialist:** @ui-tote-ops

**Functions to implement:**
- Update `get_supplier_gradeout_stats` — replace `avg_275`, `avg_330` with `avg_275_washable`, `avg_275_cage`, `avg_330_washable`, `avg_330_cage`

**Acceptance criteria:**
- [ ] Contact column (`contact_name` + `phone`) removed from `_row.html` and `list.html` thead
- [ ] "275/330 Avg" column replaced with "275 W/C Avg" and "330 W/C Avg" — shows `{avg_washable}w {avg_cage}c`
- [ ] `list.html` thead column count matches `_row.html` column count exactly
- [ ] HTMX search (`GET /suppliers/search`) still returns correct `_row.html` fragments
- [ ] Detail page contact info unchanged
- [ ] Each service function ≤50 lines (CQ-01)
- [ ] Template renders correctly at 768px iPad viewport (@ui-tote-ops)

**Tests required:**
- `test_suppliers` → `get_supplier_gradeout_stats returns avg_275_washable and avg_275_cage separately`

**Depends on:** Task 8

---

## Task 21: Migration — last_pickup_date rename + action stage columns
**Status:** [x]

**Files:**
- `migrations/versions/0006_supplier_action_stage.py` — create

**Functions to implement:**
- `upgrade()` — renames `last_contacted_date` → `last_pickup_date`; adds `last_action_stage VARCHAR(32)` nullable; adds `last_action_date DATE` nullable
- `downgrade()` — reverses all three changes

**Acceptance criteria:**
- [ ] `alembic upgrade head` runs without errors against Supabase PostgreSQL
- [ ] `alembic downgrade` reverses cleanly
- [ ] Migration contains no credentials (SEC-01)
- [ ] Column rename uses `op.alter_column` — no data loss

**Tests required:**
- Manual: `alembic upgrade head` → verify columns in Supabase dashboard

**Depends on:** Task 4

---

## Task 22: Supplier model — add action stage fields
**Status:** [x]

**Files:**
- `app/models/supplier.py` — modify

**Functions to implement:**
- Rename `last_contacted_date` → `last_pickup_date = Column(Date)`
- Add `last_action_stage = Column(String(32))`
- Add `last_action_date = Column(Date)`

**Acceptance criteria:**
- [ ] `last_pickup_date` replaces `last_contacted_date` — no other model changes
- [ ] Both new columns nullable with no default
- [ ] Model file remains ≤200 lines (CQ-02)

**Tests required:**
- `test_suppliers` → `Supplier model accepts last_action_stage and last_action_date`

**Depends on:** Task 21

---

## Task 23: Service updates — action stage + gradeout auto-reset
**Status:** [x]

**Files:**
- `app/services/supplier_service.py` — modify
- `app/services/gradeout_service.py` — modify

**Functions to implement:**

`supplier_service.py`:
- `set_supplier_action_stage(db: Session, supplier_id: str, stage: str | None) -> None` — if stage is empty string or None: sets `last_action_stage=None`, `last_action_date=None`; otherwise sets `last_action_stage=stage`, `last_action_date=date.today()`; commits; raises `NotFoundError` if supplier not found or deleted

`gradeout_service.py` — update `create_gradeout`:
- After gradeout commit: fetch supplier, set `supplier.last_pickup_date = gradeout.date_received`, `supplier.last_action_stage = None`, `supplier.last_action_date = None`; commit in same transaction

**Acceptance criteria:**
- [ ] `set_supplier_action_stage` with empty/None stage clears both fields to null
- [ ] `set_supplier_action_stage` with valid stage sets stage + `date.today()` — never user-supplied date (SEC-02)
- [ ] `create_gradeout` resets action stage and sets last_pickup_date in same transaction as gradeout save (EH-01)
- [ ] `set_supplier_action_stage` raises `NotFoundError` for missing/deleted supplier (EH-05)
- [ ] Each function ≤50 lines (CQ-01)

**Tests required:**
- `test_suppliers` → `set_supplier_action_stage sets stage and today's date`
- `test_suppliers` → `set_supplier_action_stage with empty string clears both fields to null`
- `test_suppliers` → `set_supplier_action_stage raises NotFoundError for missing supplier`
- `test_gradeouts` → `create_gradeout sets supplier last_pickup_date to gradeout date_received`
- `test_gradeouts` → `create_gradeout resets supplier last_action_stage to null`

**Depends on:** Task 22

---

## Task 24: Router — PATCH /suppliers/{id}/action-stage
**Status:** [x]

**Files:**
- `app/routers/suppliers.py` — modify

**Functions to implement:**
- `PATCH /suppliers/{supplier_id}/action-stage` — reads `last_action_stage` from form data; calls `set_supplier_action_stage(db, supplier_id, stage)`; returns `HTMLResponse("")`; raises 404 on `NotFoundError`

**Acceptance criteria:**
- [ ] Returns `HTMLResponse("")` — HTMX `hx-swap="none"` pattern
- [ ] Invalid/unknown stage value accepted — no enum enforcement (values fixed in dropdown)
- [ ] Raises HTTP 404 if supplier not found (EH-05)
- [ ] Route requires auth (SEC-01)

**Tests required:**
- `test_suppliers` → `PATCH /suppliers/{id}/action-stage sets stage and returns 200`
- `test_suppliers` → `PATCH /suppliers/{id}/action-stage with empty value clears stage`

**Depends on:** Task 23

---

## Task 25: Templates — Last Action column in all 3 locations
**Status:** [x]

**Files:**
- `app/templates/dashboard.html` — modify
- `app/templates/suppliers/_row.html` — modify
- `app/templates/suppliers/list.html` — modify
- `app/templates/suppliers/detail.html` — modify
**Specialist:** @ui-tote-ops

**What to implement:**

Stage dropdown (all 3 locations) — HTMX `hx-patch` on `change`, `hx-swap="none"`, `name="last_action_stage"`. Options: `""` → "—", `followed_up` → "Followed Up", `responded_no` → "Responded No", `pickup_confirmed` → "Pickup Confirmed", `maybe` → "Maybe — Follow Up Later". Selected option reflects current `supplier.last_action_stage`. Date shown beneath as `{last_action_date}` or blank if null.

*dashboard.html* — Follow-Up panel: add "Last Action" column after Supplier — stage dropdown + date beneath.

*suppliers/_row.html*: add "Last Action" column — stage dropdown + date beneath. (Contact column already removed in Task 20.)

*suppliers/list.html*: add "Last Action" `<th>` to thead to match `_row.html`.

*suppliers/detail.html*: add "Last Action" row to Contact card — stage dropdown + date; add "Last Pickup" row showing `supplier.last_pickup_date`.

**Acceptance criteria:**
- [ ] Stage dropdown present and functional in all 3 locations
- [ ] HTMX `hx-patch` fires on dropdown `change` — no button required
- [ ] Selected option reflects current `last_action_stage` on page load
- [ ] Date shown beneath dropdown when set; blank when null
- [ ] `list.html` thead column count matches `_row.html` exactly
- [ ] Dashboard follow-up panel renders without horizontal scroll at 768px viewport (@ui-tote-ops)
- [ ] `last_pickup_date` shown correctly on detail page — no reference to `last_contacted_date` remains
- [ ] Template renders correctly at 768px iPad viewport (@ui-tote-ops)

**Tests required:**
- Manual: verify dropdown updates without page reload at 768px viewport (Playwright)

**Depends on:** Task 24, Task 20

---

## Task 26: Pillow dependency + invoice image generation
**Status:** [x]

**Files:**
- `requirements.txt` — modify (add `Pillow>=10.1.0`)
- `app/services/invoice_service.py` — modify (add `generate_invoice_image()`)
- `app/routers/invoices.py` — modify (add `GET /invoices/{id}/image` route)

**Functions to implement:**
- `generate_invoice_image(db, invoice_id: str) -> bytes` — fetches invoice from DB, queries gradeouts for that month (same logic as `generate_invoice_preview`), draws PNG table with columns: Supplier, Address, Date, Usable Totes, Revenue + totals row using Pillow. Uses `ImageFont.load_default(size=16)`. Returns PNG bytes — no file written to disk.
- `GET /invoices/{invoice_id}/image` — calls `generate_invoice_image()`, returns `Response(content=bytes, media_type="image/png")`. 404 if invoice not found, 422 if no gradeouts for that month.

**Acceptance criteria:**
- [ ] PNG contains correct columns: Supplier, Address, Date, Usable Totes, Revenue
- [ ] Totals row at bottom clearly separated
- [ ] Route returns 404 if invoice not found
- [ ] Route returns 422 if no gradeouts found for that month
- [ ] `Pillow>=10.1.0` added to `requirements.txt`
- [ ] No file written to disk — bytes returned directly in memory (SEC-01)
- [ ] Route protected with `require_auth` (SEC-01)

**Tests required:**
- `GET /invoices/{id}/image` → `happy path: returns 200 and content-type image/png`
- `GET /invoices/{id}/image` → `error: 404 when invoice id not found`

**Depends on:** Task 25

---

## Task 27: Invoice service — per-gradeout rows, city/state, overwrite, delete, toggle sent
**Status:** [x]

**Files:**
- `app/services/invoice_service.py` — modify

**Functions to implement:**
- `generate_invoice_preview(db, month)` — update existing: each row is now one gradeout (not aggregated by supplier); add `date` field (`g.date_received`); add `city_state` field using same split logic as `suppliers/_row.html`: if `location.split(',')` has ≥2 parts → `parts[-2].strip() + ', ' + parts[-1].strip()`, else full `location` string
- `overwrite_invoice(db, month, preview_data) -> Invoice` — deletes existing invoice for that month (hard delete), then calls `save_invoice()`; raises `NotFoundError` if no existing invoice
- `delete_invoice(db, invoice_id: str)` — hard deletes invoice by id; raises `NotFoundError` if not found
- `toggle_invoice_sent(db, invoice_id: str) -> Invoice` — if `sent_at` is None → sets to `datetime.now(timezone.utc)` (tzinfo stripped); if `sent_at` is set → sets to None; raises `NotFoundError` if not found

**Acceptance criteria:**
- [ ] Preview rows: one entry per gradeout ordered by `date_received` asc
- [ ] `city_state` falls back to full `location` string if no comma present
- [ ] `overwrite_invoice` deletes old record before creating new — no duplicate month constraint violation
- [ ] `toggle_invoice_sent` correctly flips in both directions
- [ ] All DB writes use ORM — no raw SQL (SEC-03)
- [ ] All mutations committed and refreshed before return (EH-01)

**Tests required:**
- `generate_invoice_preview` → `returns one row per gradeout with date and city_state fields`
- `generate_invoice_preview` → `city_state falls back to full location when no comma`
- `overwrite_invoice` → `deletes old and creates new invoice for same month`
- `delete_invoice` → `happy path: invoice removed from DB`
- `delete_invoice` → `error: raises NotFoundError when id not found`
- `toggle_invoice_sent` → `sets sent_at when currently None`
- `toggle_invoice_sent` → `clears sent_at when currently set`

**Depends on:** Task 26

---

## Task 28: Router — preview modal route, overwrite, delete, updated toggle sent
**Status:** [x]

**Files:**
- `app/routers/invoices.py` — modify

**Functions to implement:**
- `GET /invoices/preview?month=YYYY-MM` — calls `generate_invoice_preview()`; calls `get_invoice_by_month()` to pass `existing_invoice` bool into context; returns `invoices/_preview_modal.html` HTML fragment (HTMX partial, not full page)
- `POST /invoices/generate-or-confirm` (form: `month`) — calls `generate_invoice_preview()`; if no existing invoice → calls `save_invoice()` + returns `HTMLResponse("")` with `HX-Redirect: /invoices`; if existing invoice exists → returns `invoices/_overwrite_confirm.html` fragment with month in context
- `POST /invoices/overwrite` (form: `month`) — calls `overwrite_invoice()`; returns `HTMLResponse("")` with `HX-Redirect: /invoices`
- `DELETE /invoices/{invoice_id}` — calls `delete_invoice()`; returns `HTMLResponse("")` with `HX-Redirect: /invoices`
- `PATCH /invoices/{invoice_id}/sent` — replace existing implementation: calls `toggle_invoice_sent()` instead of `mark_invoice_sent()`; returns `HTMLResponse("")` with `HX-Redirect: /invoices`
- Remove `POST /invoices` (old save route — no longer needed)

**Acceptance criteria:**
- [ ] `GET /invoices/preview` returns HTML fragment not full page — no `{% extends %}` in partial
- [ ] `POST /invoices/generate-or-confirm` returns overwrite confirmation fragment (not redirect) when invoice exists
- [ ] `POST /invoices/overwrite` returns `HX-Redirect` on success (CONSTRAINT-09)
- [ ] `DELETE /invoices/{id}` returns `HX-Redirect` on success (CONSTRAINT-09)
- [ ] `PATCH /invoices/{id}/sent` toggles in both directions and returns `HX-Redirect`
- [ ] All routes protected with `require_auth` (SEC-01)
- [ ] Invalid month format returns 422 with user-facing error message

**Tests required:**
- `GET /invoices/preview` → `returns 200 HTML fragment`
- `POST /invoices/generate-or-confirm` → `saves and returns HX-Redirect when no existing invoice`
- `POST /invoices/generate-or-confirm` → `returns overwrite confirm fragment when invoice exists`
- `POST /invoices/overwrite` → `overwrites and returns HX-Redirect`
- `DELETE /invoices/{id}` → `deletes and returns HX-Redirect; 404 if not found`

**Depends on:** Task 27

---

## Task 29: Invoice list template — full rework
**Status:** [x]

**Files:**
- `app/templates/invoices/list.html` — modify
**Specialist:** @ui-tote-ops

**Changes:**
- Add **Created** column to table header and rows — displays `inv.generated_at.strftime('%b %d, %Y')`
- Rename top form button: "Generate Preview" → "Generate"
- Replace top form action (was POST to `/invoices/generate`) with HTMX: `hx-get="/invoices/preview"` with month as query param, `hx-target="#modal-container"`, `hx-swap="innerHTML"`
- Remove **Status** column from `<thead>` and all rows
- Replace per-row action buttons with four actions:
  - **Preview** — `hx-get="/invoices/preview?month={{ inv.month.strftime('%Y-%m') }}"` `hx-target="#modal-container"` `hx-swap="innerHTML"`
  - **Send** — `<button onclick="sendInvoice('{{ inv.id }}')">`
  - **Delete** — `hx-delete="/invoices/{{ inv.id }}"` `hx-confirm="Delete invoice for {{ inv.month.strftime('%B %Y') }}?"` `hx-target="body"` `hx-swap="none"`
  - **Sent toggle** — CSS animated toggle switch (checkbox + label pattern); `hx-patch="/invoices/{{ inv.id }}/sent"` `hx-trigger="change"` `hx-swap="none"`; checked when `inv.sent_at is not None`; label text "Sent" / "Not sent"
- Add `<div id="modal-container"></div>` at bottom of page (empty HTMX target)
- Add `<script>` block with `sendInvoice(invoiceId)` function: fetches `/invoices/{invoiceId}/image`, creates `File` object (`invoice-{month}.png`, `image/png`), calls `navigator.share({ files: [file], title: 'Invoice' })`; if `navigator.share` not available or share fails → `alert('Web Share not supported — use a compatible browser or device')`

**Acceptance criteria:**
- [ ] Created date column visible in table
- [ ] Generate button opens modal via HTMX — no full page navigation
- [ ] Status column absent from thead and all rows
- [ ] Sent toggle animates and persists state; shows correct state on page load
- [ ] Send button triggers `navigator.share()` with PNG file
- [ ] Delete shows confirm dialog before firing
- [ ] All buttons meet 44px min-height touch target
- [ ] Renders correctly at 768px viewport (iPad) — no horizontal scroll
- [ ] `navigator.share` fallback alert shown if API unavailable

**Tests required:** Manual verification at 768px viewport

**Depends on:** Task 28

---

## Task 30: Preview modal partial template
**Status:** [x]

**Files:**
- `app/templates/invoices/_preview_modal.html` — create
**Specialist:** @ui-tote-ops

**What to render:**
- Full-screen overlay modal (same CSS pattern as `suppliers/list.html` create modal)
- Header: "Invoice Preview — {month.strftime('%B %Y')}"
- Table: one row per gradeout — Supplier, Address (city_state), Date (`row.date.strftime('%b %d, %Y')`), Usable Totes (`row.total_usable`), Revenue (`$row.revenue`)
- Totals row in `<tfoot>`: gradeout count, total usable, total revenue
- Two buttons:
  - **Generate** — `hx-post="/invoices/generate-or-confirm"` `hx-target="#modal-container"` `hx-swap="innerHTML"` with hidden `<input name="month" value="{{ month.strftime('%Y-%m') }}">`
  - **Back to Invoices** — `onclick="document.getElementById('modal-container').innerHTML=''"` (clears modal)
- No `{% extends "base.html" %}` — this is an HTML fragment only

**Acceptance criteria:**
- [ ] No `{% extends %}` tag — partial only
- [ ] One row per gradeout in correct column order
- [ ] Date formatted as `%b %d, %Y`
- [ ] Totals row shows gradeout count, total usable, total revenue
- [ ] Generate fires HTMX POST — no full page reload
- [ ] Back to Invoices closes modal without page reload
- [ ] Renders correctly at 768px viewport

**Depends on:** Task 29

---

## Task 31: Overwrite confirmation partial template
**Status:** [x]

**Files:**
- `app/templates/invoices/_overwrite_confirm.html` — create
**Specialist:** @ui-tote-ops

**What to render:**
- Replaces modal content (HTMX swap into `#modal-container`)
- Full-screen overlay (same CSS pattern)
- Message: "An invoice for **{month.strftime('%B %Y')}** already exists. Overwrite it completely? This cannot be undone."
- Two buttons:
  - **Yes, Overwrite** — `hx-post="/invoices/overwrite"` `hx-target="#modal-container"` with hidden `<input name="month">`
  - **Cancel** — `onclick="document.getElementById('modal-container').innerHTML=''"` closes modal
- No `{% extends "base.html" %}` — fragment only

**Acceptance criteria:**
- [ ] Month name shown in confirmation message
- [ ] Yes Overwrite fires HTMX POST and redirects on success
- [ ] Cancel closes without action or page reload
- [ ] Both buttons meet 44px touch target
- [ ] No `{% extends %}` tag

**Depends on:** Task 30

---

## Task 32: Tests — invoice improvements
**Status:** [x]

**Files:**
- `tests/test_invoices.py` — modify (extend existing)

**Tests required:**
- `generate_invoice_preview` → `returns one row per gradeout with date and city_state fields`
- `generate_invoice_preview` → `city_state falls back to full location string when no comma`
- `overwrite_invoice` → `deletes old invoice and creates new for same month`
- `delete_invoice` → `happy path: invoice removed from DB`
- `delete_invoice` → `error: raises NotFoundError when id not found`
- `toggle_invoice_sent` → `sets sent_at when currently None`
- `toggle_invoice_sent` → `clears sent_at when currently set`
- `GET /invoices/preview` → `returns 200 with HTML content`
- `POST /invoices/generate-or-confirm` → `saves invoice and returns HX-Redirect when no existing`
- `POST /invoices/generate-or-confirm` → `returns overwrite confirm HTML when invoice exists for month`
- `POST /invoices/overwrite` → `overwrites existing invoice and returns HX-Redirect`
- `DELETE /invoices/{id}` → `deletes invoice and returns HX-Redirect`
- `DELETE /invoices/{id}` → `error: 404 when id not found`
- `GET /invoices/{id}/image` → `returns 200 with content-type image/png`
- `GET /invoices/{id}/image` → `error: 404 when invoice not found`

**Depends on:** Task 31

---

## Task 33: Pickup model + Alembic migration
**Status:** [x]

**Files:**
- `app/models/pickup.py` — create
- `app/models/gradeout.py` — modify
- `app/models/supplier.py` — modify
- `app/models/__init__.py` — modify
- `migrations/versions/0007_add_pickups.py` — create

**Functions to implement:**
- `Pickup` model: `id String(36) PK default uuid4`, `supplier_id String(36) FK→suppliers.id NOT NULL`, `created_at DateTime server_default=func.now()`, `status String(16) NOT NULL default 'confirmed'`; `supplier = relationship("Supplier", back_populates="pickups")`
- `Gradeout`: add `pickup_id = Column(String(36), ForeignKey("pickups.id"), nullable=True)`; add `pickup = relationship("Pickup")`
- `Supplier`: add `pickups = relationship("Pickup", back_populates="supplier")`
- Migration `upgrade()`: create `pickups` table first, then `op.add_column("gradeouts", pickup_id FK nullable)`
- Migration `downgrade()`: drop `pickup_id` from gradeouts, drop `pickups` table

**Acceptance criteria:**
- [ ] `Pickup` imported in `app/models/__init__.py` alongside existing models
- [ ] `alembic upgrade head` runs without errors against Supabase PostgreSQL
- [ ] `alembic downgrade` reverses cleanly
- [ ] `gradeouts.pickup_id` is nullable — existing gradeouts with no linked pickup are valid (EH-01)
- [ ] Migration contains no credentials (SEC-01)
- [ ] `Pickup.supplier` and `Supplier.pickups` relationships defined in both directions

**Tests required:**
- `test_models` → `Pickup instantiates with supplier_id and status defaults to confirmed`
- `test_models` → `Gradeout accepts nullable pickup_id`

**Depends on:** Task 32

---

## Task 34: Pickup service + router
**Status:** [x]

**Files:**
- `app/services/pickup_service.py` — create
- `app/routers/pickups.py` — create
- `app/main.py` — modify (register pickup router)

**Functions to implement (service):**
- `create_pickup(db: Session, supplier_id: str) -> Pickup` — validates supplier exists and `is_deleted=False`; creates Pickup with `status="confirmed"`; raises `ValueError("Supplier not found")` if not found or deleted
- `get_confirmed_pickups_for_supplier(db: Session, supplier_id: str) -> list[Pickup]` — returns pickups where `supplier_id=supplier_id` and `status="confirmed"`
- `get_all_confirmed_pickups(db: Session) -> list[dict]` — returns all `status="confirmed"` pickups across all suppliers; each dict: `{"id": str, "supplier_name": str, "created_at": datetime}`; joined via relationship; ordered by `created_at` desc
- `get_confirmed_pickup_count(db: Session) -> int` — count of all `status="confirmed"` pickups
- `cancel_pickup(db: Session, pickup_id: str) -> None` — sets `status="cancelled"`; raises `NotFoundError` if not found; raises `ValueError("Cannot cancel a completed pickup")` if `status="completed"`

**Functions to implement (router):**
- `POST /pickups` — reads `supplier_id` from form; calls `create_pickup`; returns `RedirectResponse(f"/suppliers/{supplier_id}", 303)` on success; 422 on `ValueError` (SEC-02)
- `DELETE /pickups/{pickup_id}` — calls `cancel_pickup`; returns `HTMLResponse("")` with `HX-Redirect: /` header on success; 404 on `NotFoundError`; 422 on `ValueError` (CONSTRAINT-09)

**Acceptance criteria:**
- [ ] Pickup router registered in `app/main.py`
- [ ] `create_pickup` raises `ValueError` if supplier is soft-deleted or not found (EH-05)
- [ ] `cancel_pickup` raises `NotFoundError` if pickup not found (EH-05)
- [ ] `cancel_pickup` raises `ValueError` if pickup `status="completed"` — completed pickups cannot be cancelled (EH-01)
- [ ] All DB queries use ORM — no raw SQL (SEC-03)
- [ ] Each service function ≤ 50 lines (CQ-01)
- [ ] Both routes protected with `require_auth` (SEC-01)

**Tests required:**
- `test_pickups` → `create_pickup creates pickup with status confirmed for valid supplier`
- `test_pickups` → `create_pickup raises ValueError when supplier not found`
- `test_pickups` → `create_pickup raises ValueError when supplier is soft-deleted`
- `test_pickups` → `get_confirmed_pickups_for_supplier returns only confirmed pickups`
- `test_pickups` → `get_confirmed_pickup_count returns correct count`
- `test_pickups` → `cancel_pickup sets status to cancelled`
- `test_pickups` → `cancel_pickup raises NotFoundError when pickup id not found`
- `test_pickups` → `cancel_pickup raises ValueError when pickup is already completed`
- `test_pickups` → `DELETE /pickups/{id} returns 200 with HX-Redirect on success`
- `test_pickups` → `DELETE /pickups/{id} returns 404 when pickup not found`

**Depends on:** Task 33

---

## Task 35: Supplier detail — Confirm Pickup button + confirmed count
**Status:** [x]

**Files:**
- `app/routers/suppliers.py` — modify
- `app/templates/suppliers/detail.html` — modify
**Specialist:** @ui-tote-ops

**Functions to implement:**
- In `GET /suppliers/{id}`: import `get_confirmed_pickups_for_supplier` from `pickup_service`; add `confirmed_pickup_count = len(get_confirmed_pickups_for_supplier(db, str(supplier.id)))` to template context

**Template changes:**
- Add "Confirm Pickup" button in detail page header: `<form method="post" action="/pickups">` with hidden `<input name="supplier_id" value="{{ supplier.id }}">` and blue submit button "Confirm Pickup" (min-height 44px)
- Below button (shown only when `confirmed_pickup_count > 0`): `"{{ confirmed_pickup_count }} pickup(s) confirmed — awaiting gradeout"`
- Zero state: no count text shown

**Acceptance criteria:**
- [ ] "Confirm Pickup" form POSTs to `/pickups` with `supplier_id`
- [ ] After POST, page redirects to supplier detail with updated count
- [ ] Count shows only `confirmed` pickups — not completed or cancelled
- [ ] Zero confirmed pickups → count text not shown
- [ ] Button min-height 44px touch target (@ui-tote-ops)
- [ ] Renders correctly at 768px iPad viewport (@ui-tote-ops)

**Tests required:**
- `test_suppliers` → `GET /suppliers/{id} passes confirmed_pickup_count in template context`
- `test_pickups` → `POST /pickups redirects to supplier detail page on success`

**Depends on:** Task 34

---

## Task 36: Gradeout service + router + template — pickup linking
**Status:** [x]

**Files:**
- `app/services/gradeout_service.py` — modify
- `app/routers/gradeouts.py` — modify
- `app/templates/gradeouts/new.html` — modify
**Specialist:** @ui-tote-ops

**Functions to implement:**
- Add `_complete_pickup(db: Session, pickup_id: str) -> None` — private helper; sets `pickup.status = "completed"`; raises `ValueError("Pickup not found")` if not found; does NOT commit (caller commits)
- Modify `create_gradeout(db, data)`:
  - Extract `pickup_id = (data.get("pickup_id") or "").strip() or None`
  - Call `get_confirmed_pickups_for_supplier(db, supplier_id)` (import from `pickup_service`)
  - 0 confirmed: `pickup_id` stays `None`, proceed normally
  - 1 confirmed and no `pickup_id` provided: auto-set `pickup_id = str(confirmed[0].id)`
  - 2+ confirmed and no `pickup_id`: raise `ValueError("Select which pickup this gradeout belongs to")`
  - If `pickup_id` set: assign `gradeout.pickup_id = pickup_id`; call `_complete_pickup(db, pickup_id)` before `db.commit()`

**Router changes (`GET /gradeouts/new`):**
- Build `confirmed_pickups_by_supplier: dict[str, list[dict]]` — keys are `str(supplier.id)`, values are `[{"id": str(p.id), "label": f"Confirmed {p.created_at.strftime('%b %d')}"}]` for each confirmed pickup
- Pass to template context as `confirmed_pickups_by_supplier`

**Template changes (`new.html`):**
- Add `<script>const confirmedPickupsBySupplierId = {{ confirmed_pickups_by_supplier | tojson }};</script>`
- On supplier `<select>` `change` (vanilla JS, ≤50 lines total including any existing JS):
  - 0 pickups for selected supplier: hide `#pickup-field` div
  - 1 pickup: show `#pickup-field` with "1 pickup confirmed — auto-linking" text and hidden `<input name="pickup_id" value="{id}">`
  - 2+ pickups: show `#pickup-field` with required `<select name="pickup_id">` with one option per pickup
- Run same logic on page load for initially-selected supplier (if any)

**Acceptance criteria:**
- [ ] 0 confirmed pickups: gradeout saves normally, no pickup field shown, `pickup_id=None` in DB
- [ ] 1 confirmed pickup: auto-linked silently; pickup `status="completed"` in same DB transaction as gradeout save (EH-01)
- [ ] 2+ confirmed pickups: required `<select>` shown; returns 422 if submitted without selection (SEC-02)
- [ ] `_complete_pickup` does not commit — `create_gradeout` commits all changes in one transaction (EH-01)
- [ ] `gradeout.pickup_id` is `None` when no pickup is linked
- [ ] All 4 original `test_gradeouts` tests pass unchanged
- [ ] Renders correctly at 768px iPad viewport (@ui-tote-ops)

**Tests required:**
- `test_gradeouts` → `create_gradeout auto-links single confirmed pickup and marks it completed`
- `test_gradeouts` → `create_gradeout raises ValueError when multiple confirmed pickups exist and no pickup_id provided`
- `test_gradeouts` → `create_gradeout succeeds with pickup_id None when no confirmed pickups exist`
- `test_gradeouts` → `create_gradeout sets gradeout pickup_id when pickup is linked`

**Depends on:** Task 35

---

## Task 37: Dashboard service — confirmed pickup count + revenue chart data
**Status:** [x]

**Files:**
- `app/services/dashboard_service.py` — modify

**Functions to implement:**
- `get_confirmed_pickup_count(db: Session) -> int` — `db.query(Pickup).filter(Pickup.status == "confirmed").count()`; returns 0 if no pickups
- `get_all_confirmed_pickups(db: Session) -> list[dict]` — query all `status="confirmed"` pickups with supplier loaded via relationship; returns `[{"id": str, "supplier_name": str, "created_at": datetime}]` ordered by `created_at` desc
- `get_revenue_chart_data(db: Session) -> dict` — fetches all gradeout `(date_received, totes_275_total_usable, totes_330_total_usable)`; groups Python-side (no SQL date functions — SQLite-compatible); returns:
  `{"monthly": [{"label": "Apr 2025", "revenue": 150.0}, ...], "annual": [{"label": "2022", "revenue": 500.0}, ...]}` — 12 monthly entries oldest→newest, 5 annual entries oldest→newest; periods with no gradeouts included with `revenue: 0.0`; revenue = `(usable_275 + usable_330) * settings.TOTE_RATE` (CQ-04)

**Acceptance criteria:**
- [ ] `get_confirmed_pickup_count` returns 0 when no confirmed pickups exist
- [ ] `get_all_confirmed_pickups` returns `supplier_name` from relationship — not supplier_id
- [ ] `get_revenue_chart_data` always returns exactly 12 monthly entries and exactly 5 annual entries
- [ ] Periods with no gradeouts appear with `revenue: 0.0` — not omitted
- [ ] Revenue uses `settings.TOTE_RATE` — not hardcoded `5` (CQ-04)
- [ ] Date grouping done in Python — no PostgreSQL-specific SQL functions (TS-03)
- [ ] All queries use ORM — no raw SQL (SEC-03)
- [ ] Each function ≤ 50 lines (CQ-01)

**Tests required:**
- `test_dashboard` → `get_confirmed_pickup_count returns correct count of confirmed pickups`
- `test_dashboard` → `get_confirmed_pickup_count returns 0 when no pickups exist`
- `test_dashboard` → `get_revenue_chart_data returns exactly 12 monthly entries`
- `test_dashboard` → `get_revenue_chart_data returns exactly 5 annual entries`
- `test_dashboard` → `get_revenue_chart_data returns 0.0 revenue for periods with no gradeouts`

**Depends on:** Task 34

---

## Task 38: Dashboard router + template — stat cards, pickups modal, revenue chart
**Status:** [x]

**Files:**
- `app/routers/dashboard.py` — modify
- `app/templates/dashboard.html` — modify
**Specialist:** @ui-tote-ops

**Router changes:**
- `GET /`: call `get_confirmed_pickup_count`, `get_all_confirmed_pickups`, `get_revenue_chart_data`; pass to template as `confirmed_pickup_count`, `confirmed_pickups`, `chart_data`

**Template changes:**
1. **"Totes" card → "Pickups Confirmed":** label = "Pickups Confirmed"; value = `confirmed_pickup_count`; not period-scoped; card wrapped in `<button onclick="document.getElementById('pickups-modal').style.display='flex'" style="...cursor:pointer; width:100%; text-align:left;">` — same visual card style
2. **"Suppliers" card:** wrap in `<a href="/suppliers" style="text-decoration:none; color:inherit; display:block;">`
3. **"Gradeouts" card:** same pattern, `href="/gradeouts"`
4. **Pickups modal:** full-screen overlay (same CSS pattern as existing modals); header "Confirmed Pickups" + ✕ close button; table: Supplier / Date Confirmed / Action; each row: `supplier_name`, `created_at.strftime('%b %d, %Y')`, Cancel button (`hx-delete="/pickups/{{ p.id }}" hx-confirm="Cancel this pickup?" hx-target="body" hx-swap="none"`); empty state "No confirmed pickups" when list is empty
5. **Revenue chart:** full-width card between stat cards and bottom panels; header bar "Revenue Trend" + collapse arrow — entire bar is `onclick` toggle for `display` of `#chart-body`; collapsed by default (`display:none`); inside: Time pill toggle (Monthly | Annual) + Value pill toggle (Per Period | Cumulative); `<canvas id="revenue-chart">`; Chart.js from CDN (`https://cdn.jsdelivr.net/npm/chart.js`); `<script>` injects `const chartData = {{ chart_data | tojson }};`; vanilla JS ≤ 60 lines handles collapse toggle, pill toggle state, Chart.js init and re-render on toggle

**Acceptance criteria:**
- [ ] "Pickups Confirmed" shows `confirmed_pickup_count`; not affected by period toggle
- [ ] Clicking card opens modal; modal lists all confirmed pickups with supplier name + date
- [ ] Cancel in modal sends DELETE; page reloads showing updated count
- [ ] Empty state shown in modal when no confirmed pickups
- [ ] Suppliers card → `/suppliers`; Gradeouts card → `/gradeouts` on click
- [ ] Chart section collapsed by default; tap header toggles open/close without page reload
- [ ] Monthly: 12 bars; Annual: 5 bars; $0 periods render as 0-height bar (not omitted)
- [ ] Per Period and Cumulative toggles switch values without reload
- [ ] Chart.js from CDN (CQ-04); JS ≤ 60 lines (CQ-01)
- [ ] Renders correctly at 768px iPad viewport (@ui-tote-ops)

**Tests required:**
- `test_dashboard` → `GET / passes confirmed_pickup_count in template context`
- `test_dashboard` → `GET / passes chart_data with monthly and annual keys to template`

**Depends on:** Task 37

---

## Task 39: Suppliers tab — action stage filter + active toggle + Status column rename
**Status:** [x]

**Files:**
- `app/services/supplier_service.py` — modify
- `app/routers/suppliers.py` — modify
- `app/templates/suppliers/list.html` — modify
**Specialist:** @ui-tote-ops

**Service changes:**
- Replace `filter_by: str | None = None` with `action_stage: str | None = None, active_only: bool = True` in `get_suppliers` signature
- Remove `if filter_by == "hazmat"` and `if filter_by == "needs_followup"` branches entirely
- Add: `if action_stage: query = query.filter(Supplier.last_action_stage == action_stage)`
- Add: `if active_only: query = query.filter(Supplier.is_active == True)`  # noqa: E712

**Router changes:**
- `GET /suppliers`: read `action_stage: str | None = Query(None)` and `active_only: bool = Query(True)` params; pass to `get_suppliers`; pass back to template for UI state
- `GET /suppliers/search`: forward `action_stage` and `active_only` from request query string to `get_suppliers`

**Template changes (`list.html`):**
- Replace filter `<select>` options: `""` → "All Suppliers", `"followed_up"` → "Followed Up", `"responded_no"` → "Responded No", `"pickup_confirmed"` → "Pickup Confirmed", `"maybe"` → "Maybe"; HTMX `hx-get="/suppliers/search"` `hx-trigger="change"` `hx-include="[name='q'], [name='active_only']"`
- Add hidden `<input name="active_only" value="{{ 'true' if active_only else 'false' }}">` so HTMX carries toggle state
- Add Active/Show All toggle as pill-style links: `<a href="?active_only=true">Active Only</a>` and `<a href="?active_only=false">Show All</a>`; highlight current state (blue pill = active); full page reload on toggle
- Update search `<input>` `hx-include` to include `[name='action_stage'], [name='active_only']`
- Rename `<th>` "Hazmat" → "Status"

**Acceptance criteria:**
- [ ] Filter dropdown: All Suppliers / Followed Up / Responded No / Pickup Confirmed / Maybe
- [ ] Stage filter works via HTMX — no full page reload
- [ ] `active_only=True` is default on page load — `is_active=False` suppliers excluded
- [ ] Show All toggle includes inactive suppliers; Inactive badge visible on their rows
- [ ] Search + stage filter + `active_only` all sent together on every HTMX request
- [ ] "Status" in `<thead>`; `_row.html` cell logic unchanged
- [ ] `list.html` thead column count matches `_row.html` exactly (CQ-06)
- [ ] All queries use ORM — no raw SQL (SEC-03)

**Tests required:**
- `test_suppliers` → `get_suppliers filters by action_stage correctly`
- `test_suppliers` → `get_suppliers excludes inactive suppliers when active_only is True`
- `test_suppliers` → `get_suppliers includes inactive suppliers when active_only is False`
- *(Replace existing `test_get_suppliers_returns_only_hazmat_suppliers_when_filter_is_hazmat` with `get_suppliers filters by action_stage correctly`)*

**Depends on:** Task 32

---

## Task 40: Tests — all new coverage
**Status:** [x]

**Files:**
- `tests/test_pickups.py` — create
- `tests/test_gradeouts.py` — modify (4 new pickup-linking tests)
- `tests/test_dashboard.py` — modify (5 service + 2 route tests)
- `tests/test_suppliers.py` — modify (replace hazmat test + 3 new active_only tests)

**Acceptance criteria:**
- [ ] `pytest tests/` passes with 0 failures
- [ ] `test_pickups.py` contains all 12 tests specified in Tasks 34–35
- [ ] `test_gradeouts.py` contains 4 new pickup-linking tests from Task 36; all original tests pass
- [ ] `test_dashboard.py` contains 7 new tests from Tasks 37–38; all original tests pass
- [ ] `test_suppliers.py` hazmat filter test replaced; 3 new `active_only` tests added; all other existing tests pass
- [ ] All fixtures function-scoped SQLite in-memory — no real DB calls (TS-03)
- [ ] All test names follow `[function] [does X] when [condition]` (TS-02)

**Tests required:** All tests listed in Tasks 33–39.

**Depends on:** Tasks 33–39
