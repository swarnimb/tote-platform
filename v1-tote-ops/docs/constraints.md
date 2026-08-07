# Constraints: Tote-Ops

> Active binding decisions only. Not history. Not rationale. Just what is locked.
> Updated when new binding decisions are made during development.
> Loaded by `@session-start` every session.

---

## Active Constraints

---

### CONSTRAINT-01: Sync SQLAlchemy only

**Decision:** SQLAlchemy 2.0 sync — no async SQLAlchemy, no `async def` database operations.

**What it means in practice:** All service functions and DB queries use synchronous SQLAlchemy session. No `await` in DB code. FastAPI routes that use `get_db` are synchronous.

**Who decided and when:** @cto, 2026-03-15

**What this closes off:** Migrating to async requires rewriting all DB queries. Acceptable for a personal tool — revisit only if concurrency becomes a real requirement.

---

### CONSTRAINT-02: HTML-first responses — no JSON API

**Decision:** All FastAPI routes return `TemplateResponse` (full HTML) or `HTMLResponse` (HTMX fragment). No JSON endpoints.

**What it means in practice:** No `return {"key": "value"}` from routes. No Pydantic response models for HTTP responses. HTMX partials return HTML strings only.

**Who decided and when:** @cto, 2026-03-15

**What this closes off:** A native mobile app or third-party integration would require adding a JSON API layer from scratch.

---

### CONSTRAINT-03: No local filesystem for file storage

**Decision:** Uploaded PDFs must be stored in Supabase Storage only — never written to the local filesystem.

**What it means in practice:** No `open(path, 'wb')` for PDF uploads. No `os.path` operations on uploaded files. Always use `storage.upload_pdf()` from `app/storage.py`. Render's filesystem is ephemeral — local writes are lost on redeploy.

**Who decided and when:** @cto, 2026-03-15 (ASSUMPTION-03 outcome)

**What this closes off:** Nothing — this is the only correct approach for Render deployment.

---

### CONSTRAINT-04: No SMTP email in V1

**Decision:** All email flows use `mailto:` links only — no SMTP, no email sending from the application server.

**What it means in practice:** Never import `smtplib`, `sendgrid`, `resend`, or any email-sending library. All "Send" buttons generate a `mailto:` href that opens the user's mail client. `build_followup_mailto()` and `build_invoice_mailto()` return URL-encoded mailto strings only.

**Who decided and when:** Builder + @cto, 2026-03-15

**What this closes off:** Switching to SMTP in V2 requires adding a new service and env vars — no existing code to undo.

---

### CONSTRAINT-05: No PDF auto-extraction in V1

**Decision:** No PDF text extraction logic. Gradeout data is entered manually via form.

**What it means in practice:** No `pdfplumber`, `pytesseract`, or AI Vision API imports. The `@pdf-extractor` skill is inactive for V1. PDFs are stored for reference only — they are not parsed.

**Who decided and when:** Builder, 2026-03-15 (ASSUMPTION-03: PDFs are scanned handwriting)

**What this closes off:** Nothing — V2 can add extraction by adding a `/gradeouts/extract` route that calls Claude Vision API and pre-fills the form. Storage infrastructure is already in place.

---

### CONSTRAINT-06: Supplier soft delete only

**Decision:** Suppliers use soft delete (`is_deleted=True`) — all other entities use hard delete.

**What it means in practice:** Never `db.delete(supplier)`. Always set `supplier.is_deleted = True`, `supplier.deleted_at = datetime.utcnow()`. All queries against suppliers must filter `Supplier.is_deleted == False` (enforced in `get_suppliers` and `get_supplier_by_id`).

**Who decided and when:** Builder, 2026-03-15

**What this closes off:** Nothing — hard delete can be added later for cleanup if needed.

---

### CONSTRAINT-07: All config values from settings — no inline magic numbers

**Decision:** Business constants (`TOTE_RATE`, `SESSION_EXPIRY_DAYS`, `PDF_SIGNED_URL_EXPIRY_SECONDS`) must be referenced from `app/config.py` — never hardcoded inline.

**What it means in practice:** No `* 5` for revenue — use `* settings.TOTE_RATE`. Changes to business rules require updating only `config.py`.

**Note (2026-03-16):** `FOLLOWUP_DAYS_THRESHOLD` was removed — follow-up threshold is now per-supplier (`followup_weeks` field on `Supplier`). `FOLLOWUP_WEEKS_DEFAULT = 4` lives in `supplier_service.py` as a module constant — acceptable because it is only used at supplier creation time, not as a business rule applied globally.

**Who decided and when:** @cto, 2026-03-15

**What this closes off:** Nothing — makes future changes to business rules trivial.

---

### CONSTRAINT-08: String(36) for all PK and FK columns

**Decision:** All primary key and foreign key columns use `Column(String(36), ...)` with `default=lambda: str(uuid.uuid4())` — not `UUID(as_uuid=True)` from `sqlalchemy.dialects.postgresql`.

**What it means in practice:** Every new model must use `String(36)` for its `id` column and all FK columns. Every new migration must use `sa.String(36)` for these columns. Do not import `UUID` from `sqlalchemy.dialects.postgresql` in any model file.

**Who decided and when:** @dev, 2026-03-15 (implementation discovery — `UUID(as_uuid=True)` breaks SQLite in-memory tests)

**What this closes off:** Nothing meaningful. UUIDs are still generated and unique. Storage cost difference is negligible at this scale.

---

### CONSTRAINT-09: HTMX mutation routes return HX-Redirect, not RedirectResponse

**Decision:** Any PUT or PATCH route that may be called from an HTMX form must detect the `HX-Request` header and return an `HTMLResponse("")` with an `HX-Redirect` header — not a `RedirectResponse`.

**What it means in practice:**
```python
if request.headers.get("HX-Request"):
    response = HTMLResponse("")
    response.headers["HX-Redirect"] = "/destination"
    return response
return RedirectResponse("/destination", status_code=303)
```
Applied to: `PUT /suppliers/{id}`, `PATCH /pickups/{id}`. Apply to all future mutation routes called via HTMX forms.

**Why:** HTMX follows 3xx redirects but places the response body into `hx-target`, not the full page. `HX-Redirect` tells HTMX to redirect the entire browser window — the correct behavior for form saves.

**Who decided and when:** @dev, 2026-03-15 (discovered during Task 9 implementation)

**What this closes off:** Nothing — this is additive. Non-HTMX form submissions still get the standard `RedirectResponse` fallback.

---

### CONSTRAINT-10: Dark mode via CSS `!important` overrides — not CSS variables

**Decision:** Dark mode is implemented by toggling `data-theme='dark'` on `<html>` and overriding colors with CSS `!important` rules in `base.html`. Do not refactor to CSS custom properties without a full plan to migrate all inline styles.

**What it means in practice:** New UI components added to any template will not automatically support dark mode — targeted CSS overrides must be added to the dark mode block in `base.html` if the component uses new background or text colors not already covered.

**Who decided and when:** Builder, 2026-03-16

**What this closes off:** Deep dark mode coverage without a CSS vars refactor. The current approach covers all structural colors. New components using background/text colors not already in the dark override block must add explicit overrides.

---

### CONSTRAINT-11: Table row hover via `.tbl-row` CSS class — not JS inline styles

**Decision:** All table data rows (`<tr>`) must use `class="tbl-row"` for hover highlighting — never `onmouseover`/`onmouseout` inline JS.

**What it means in practice:** The `.tbl-row` class is defined in `base.html` with both light and dark mode rules. Any new table added to any template must use this class on its data rows. Do not write `onmouseover="this.style.background=..."`.

**Why:** Inline style writes set via JS cannot be targeted by CSS attribute selectors like `[data-theme='dark']`, making dark mode overrides impossible without a full refactor.

**Who decided and when:** Builder, 2026-03-18 (fixed after dark mode hover regression)

**What this closes off:** Nothing — this pattern is strictly better and has no downsides.

---

### CONSTRAINT-12: No Jinja2 block tags inside HTML comments in partials

**Decision:** HTMX partial templates must not include `{% ... %}` block tag syntax anywhere — including inside HTML comments. Jinja2 parses block tags even within `<!-- -->` comment nodes.

**What it means in practice:** Do not write `<!-- no {% extends %} here -->` or any `{% tag %}` syntax in comments. Use plain English to describe what a template does not include. E.g., `<!-- HTMX partial — fragment only, no extends tag -->`.

**Who decided and when:** @dev, 2026-04-14 (discovered as TemplateSyntaxError during Task 30)

**What this closes off:** Nothing — this is a Jinja2 parser behavior, not a design trade-off.

---

## Summary Table

| # | Decision | Practical impact | Decided by | Date |
|---|---|---|---|---|
| 01 | Sync SQLAlchemy | No async DB code anywhere | @cto | 2026-03-15 |
| 02 | HTML-first responses | No JSON endpoints | @cto | 2026-03-15 |
| 03 | No local filesystem for files | All uploads → Supabase Storage | @cto | 2026-03-15 |
| 04 | No SMTP in V1 | All email = mailto: links | Builder | 2026-03-15 |
| 05 | No PDF extraction in V1 | Manual gradeout entry only | Builder | 2026-03-15 |
| 06 | Supplier soft delete | `is_deleted=True` not `db.delete()` | Builder | 2026-03-15 |
| 07 | Config constants for business rules | No magic numbers inline | @cto | 2026-03-15 |
| 08 | String(36) for all PKs/FKs | No `UUID(as_uuid=True)` in models | @dev | 2026-03-15 |
| 09 | HTMX mutation routes use HX-Redirect | Check `HX-Request` header on PUT/PATCH | @dev | 2026-03-15 |
| 10 | Dark mode via CSS `!important` overrides | New components need manual dark mode CSS | Builder | 2026-03-16 |
| 11 | Table row hover via `.tbl-row` class | No `onmouseover` inline JS on `<tr>` | Builder | 2026-03-18 |
| 12 | No Jinja2 block tags in HTML comments | Plain-text comments only in partials | @dev | 2026-04-14 |
