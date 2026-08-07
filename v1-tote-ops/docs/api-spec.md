# API Spec: Tote-Ops

**Version:** 1.0
**Date:** 2026-03-15

All routes are HTML-first (return TemplateResponse or HTMLResponse).
No JSON API. HTMX partial routes return HTML fragments only.
All routes except `/login` and `/logout` require auth (via `require_auth` dependency).

---

## Auth

### GET /login
Returns login page.
- **Response:** `login.html`
- **Auth:** Not required

### POST /login
Validates password, sets session.
- **Body:** `form: { password: str }`
- **Response:** `RedirectResponse("/")` on success; `login.html` with error on failure
- **Auth:** Not required
- **Session:** Sets `{"authenticated": true, "expires_at": ISO timestamp}`

### POST /logout
Clears session.
- **Response:** `RedirectResponse("/login")`
- **Auth:** Not required

---

## Dashboard

### GET /
Main dashboard.
- **Query params:** `period` (month | year, default: month)
- **Response:** `dashboard.html` with stat cards (scoped to period), follow-up list, recent gradeouts (last 30 days)
- **Auth:** Required

---

## Suppliers

### GET /suppliers
Supplier list page.
- **Query params:** `search` (string), `filter` (needs_followup | hazmat)
- **Response:** `suppliers/list.html`
- **Auth:** Required

### GET /suppliers/search
HTMX partial — live search results.
- **Query params:** `search` (string)
- **Response:** HTML fragment — one `_row.html` per matching supplier
- **Auth:** Required
- **HTMX:** Yes — returns fragment, not full page

### POST /suppliers
Create new supplier.
- **Body:** `form: { company_name, location, contact_name, phone, email, bol_email, bol_same_as_primary, industry, tote_types, average_quantity_275, average_quantity_330, working_hours, followup_weeks, is_hazmat, warnings, notes }`
- **Validation:** `company_name` and `location` required — returns 422 with field error if missing
- **Response:** `RedirectResponse("/suppliers")` on success; form with errors on failure
- **Auth:** Required

### GET /suppliers/{id}
Supplier detail page.
- **Response:** `suppliers/detail.html` with supplier data + last 5 pickups + mailto link
- **Error:** 404 if not found or soft-deleted
- **Auth:** Required

### PUT /suppliers/{id}
Update supplier.
- **Body:** Same as POST
- **Response:** `RedirectResponse("/suppliers/{id}")` on success
- **Error:** 404 if not found; 422 if validation fails
- **Auth:** Required

### POST /suppliers/{id}/followup-weeks
Update per-supplier follow-up timeline.
- **Body:** `form: { followup_weeks: int (1–10) }`
- **Response:** Empty 200 (HTMX inline — no page reload)
- **Error:** 404 if not found
- **Auth:** Required

### POST /suppliers/{id}/toggle-active
Toggle supplier active/inactive status.
- **Response:** `RedirectResponse("/suppliers/{id}")`
- **Behavior:** Flips `is_active`. Inactive suppliers are hidden from follow-up lists but remain visible in the supplier list with an Inactive badge.
- **Error:** 404 if not found
- **Auth:** Required

### DELETE /suppliers/{id}
Soft delete supplier.
- **Response:** `RedirectResponse("/suppliers")`
- **Behavior:** Sets `is_deleted=True`, `deleted_at=now()`. Does NOT delete linked pickups or gradeouts.
- **Auth:** Required

---

## Pickups

### GET /pickups
Pickup list page.
- **Query params:** `status` (contacted | confirmed | completed | cancelled), `supplier_id` (UUID)
- **Response:** `pickups/list.html`
- **Auth:** Required

### POST /pickups
Create pickup.
- **Body:** `form: { supplier_id, request_date, pickup_date, tote_275_count, tote_330_count, is_hazmat, status, notes }`
- **Validation:** `supplier_id` required and must exist (non-deleted). `status` must be valid enum value.
- **Response:** `RedirectResponse("/pickups")` on success
- **Auth:** Required

### PATCH /pickups/{id}
Full update pickup.
- **Body:** Same as POST
- **Response:** `RedirectResponse("/pickups")`
- **Error:** 404 if not found
- **Auth:** Required

### PATCH /pickups/{id}/status
HTMX inline status update.
- **Body:** `form: { status: str }`
- **Validation:** Status must be valid enum value — returns 422 if not
- **Response:** HTML fragment — updated `_row.html` + toast if status=`completed` ("Pickup complete — upload the gradeout?" with link to `/gradeouts/new?pickup_id={id}`)
- **HTMX:** Yes
- **Auth:** Required

### DELETE /pickups/{id}
Delete pickup.
- **Response:** `RedirectResponse("/pickups")`
- **Error:** 409 if pickup has a linked gradeout ("Cannot delete pickup with an existing gradeout")
- **Auth:** Required

---

## Gradeouts

### GET /gradeouts
Gradeout list page.
- **Query params:** `supplier_id` (UUID), `month` (YYYY-MM)
- **Response:** `gradeouts/list.html`
- **Auth:** Required

### GET /gradeouts/new
New gradeout form.
- **Query params:** `pickup_id` (UUID, optional — pre-selects pickup in dropdown)
- **Response:** `gradeouts/new.html` — pickup dropdown shows only pickups without existing gradeout
- **Auth:** Required

### POST /gradeouts
Create gradeout (multipart/form-data).
- **Body:** `form: { pickup_id, date_received, totes_275_good_washable, totes_275_good_cage, totes_275_total_usable, totes_275_junk, totes_330_good_washable, totes_330_good_cage, totes_330_total_usable, totes_330_junk, notes }` + optional `file: PDF`
- **Validation:** All tote counts ≥ 0. `pickup_id` required and must not already have a gradeout.
- **Behavior:** If PDF uploaded → `storage.upload_pdf()` → store path. Sets `supplier_id` from `pickup.supplier_id`. Within single transaction: creates gradeout + sets `pickup.status=completed`, `pickup.pickup_date=date_received`.
- **Response:** `RedirectResponse("/gradeouts")` on success
- **Auth:** Required

### GET /gradeouts/{id}
Gradeout detail (for viewing PDF link and all fields).
- **Response:** `gradeouts/detail.html` or modal fragment
- **Error:** 404 if not found
- **Auth:** Required

### DELETE /gradeouts/{id}
Delete gradeout and associated Storage file.
- **Response:** `RedirectResponse("/gradeouts")`
- **Behavior:** Deletes DB record + calls `storage.delete_file(pdf_storage_path)` if path exists
- **Auth:** Required

---

## Invoices

### GET /invoices
Invoice list page.
- **Response:** `invoices/list.html` — sorted by month descending
- **Auth:** Required

### POST /invoices/generate
Generate invoice preview (does NOT save).
- **Body:** `form: { month: YYYY-MM }`
- **Behavior:** Queries all gradeouts in that month. If invoice already exists for month, returns existing preview. If no gradeouts exist, returns error message.
- **Response:** `invoices/preview.html` with gradeout rows + totals
- **Error:** Renders error in page if no gradeouts for month
- **Auth:** Required

### POST /invoices
Save generated invoice.
- **Body:** `form: { month, gradeout_count, total_usable_275, total_usable_330, total_revenue }`
- **Behavior:** Creates invoice record. Raises 409 if invoice for month already exists.
- **Response:** `RedirectResponse("/invoices")`
- **Auth:** Required

### PATCH /invoices/{id}/sent
Mark invoice as sent (HTMX).
- **Behavior:** Sets `sent_at = now()`
- **Response:** HTML fragment — updated invoice row with sent timestamp
- **HTMX:** Yes
- **Auth:** Required

---

## Leads

### GET /leads
Lead list page.
- **Query params:** `status` (research | contacted | responded | not_interested | active_supplier)
- **Response:** `leads/list.html`
- **Auth:** Required

### POST /leads
Create lead.
- **Body:** `form: { company_name, location, industry, contact_name, contact_phone, contact_email, outreach_status, last_contact_date, potential_volume, notes }`
- **Validation:** `company_name` required — returns 422 if missing
- **Response:** `RedirectResponse("/leads")`
- **Auth:** Required

### PATCH /leads/{id}
Full update lead.
- **Body:** Same as POST
- **Response:** `RedirectResponse("/leads")`
- **Auth:** Required

### PATCH /leads/{id}/status
HTMX inline status update.
- **Body:** `form: { status: str }`
- **Validation:** Status must be valid enum value
- **Response:** HTML fragment — updated `_row.html`. If status=`active_supplier`: response also includes "Convert to Supplier?" modal pre-filled with lead contact data.
- **HTMX:** Yes
- **Auth:** Required

### DELETE /leads/{id}
Delete lead.
- **Response:** `RedirectResponse("/leads")`
- **Auth:** Required
