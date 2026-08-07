# PRD: Tote-Ops

**Version:** 1.0
**Date:** 2026-03-15
**Status:** Approved

## One-Line Description
Internal operations dashboard for a solo IBC tote sourcing contractor — manages suppliers, pickups, gradeouts, monthly invoices, and leads.

---

## F1 — Authentication

**What the user does:**
1. Opens the app → redirected to `/login` if no valid session
2. Enters password → POST `/login` → session cookie set → redirected to dashboard
3. Session expires after 30 days → redirected to `/login`
4. Logout link in sidebar footer clears session

**Acceptance criteria:**
- [ ] All routes except `/login` redirect to `/login` if no valid session cookie
- [ ] Password checked against `APP_PASSWORD` env var — not hardcoded (SEC-01)
- [ ] Session expires after 30 days
- [ ] Wrong password shows inline error: "Incorrect password"
- [ ] Session secret loaded from `SESSION_SECRET_KEY` env var (SEC-01)
- [ ] Login page matches design system (Inter, light, centered card)

---

## F2 — Dashboard

> **Revised 2026-03-30:** Tote columns in both dashboard panels changed from usable totals to washable/cage split; no other dashboard changes.

**What the user sees on load:**

**Period toggle (Month / Year):** Pill toggle in dashboard header. Defaults to current month. Switching to Year shows year-to-date totals. Period-scoped card labels append "YTD" in year view. Suppliers is the only card unaffected by the toggle (always all-time).

Row 1 — 4 stat cards:
1. **Revenue** — total usable totes × $5 (TOTE_RATE), scoped to selected period
2. **Suppliers** — count of non-deleted, active suppliers (not period-scoped)
3. **Gradeouts** — count of gradeouts in the selected period
4. **Totes** — total usable totes (275 + 330) in the selected period; label appends "YTD" in year view

Row 2 — 2 panels (stacked on iPad):

**Recent Gradeouts panel:**
- Shows gradeouts from last 30 days only
- Columns: Date, Supplier, 275 W/C, 330 W/C, Revenue
  - "275 W/C" cell shows `{totes_275_good_washable} / {totes_275_good_cage}`
  - "330 W/C" cell shows `{totes_330_good_washable} / {totes_330_good_cage}`
- "View all →" links to `/gradeouts`

**Needs Follow-Up panel:**
- Suppliers whose last gradeout date exceeds their individual `followup_weeks` threshold
- Suppliers with no gradeouts at all appear at the top (most overdue)
- Sorted by days past deadline descending
- Excludes soft-deleted and inactive (`is_active=false`) suppliers
- Columns: Supplier, Last Pickup, 275 W/C Avg, 330 W/C Avg
  - "275 W/C Avg" cell shows `{avg_275_washable}w {avg_275_cage}c`
  - "330 W/C Avg" cell shows `{avg_330_washable}w {avg_330_cage}c`
- "View all →" links to `/suppliers`

**Acceptance criteria:**
- [ ] All stat cards compute from live DB data
- [ ] Period toggle switches between month and YTD without full page navigation state loss
- [ ] Follow-up query excludes soft-deleted and inactive suppliers
- [ ] Follow-up sorted by days past per-supplier deadline, no-gradeout suppliers first
- [ ] Dashboard renders in single page render — no separate API calls
- [ ] Recent Gradeouts: each row shows `{washable} / {cage}` for both 275 and 330
- [ ] Follow-Up: each row shows `{avg_washable}w {avg_cage}c` for both 275 and 330
- [ ] Revenue column unaffected — computed from total_usable; "Totes" stat card unchanged

---

## F3 — Suppliers

> **Revised 2026-03-30:** Contact column removed from list (available on detail page); tote avg columns changed from usable totals to washable/cage split.

**List page (`/suppliers`):**
- Search: filters by `company_name` (case-insensitive, partial match, HTMX — no full reload)
- Filter pills: All / Needs Follow-Up / Hazmat
- Columns: Company, Location, 275 W/C Avg, 330 W/C Avg, Last Pickup, Last Action, Hazmat, Actions
  - "275 W/C Avg" cell shows `{avg_275_washable}w {avg_275_cage}c`
  - "330 W/C Avg" cell shows `{avg_330_washable}w {avg_330_cage}c`
  - Last Action column added via F10 (see F10 spec)
- "Add Supplier" button → modal
- Row click → detail page

**Detail page (`/suppliers/{id}`):**
- All supplier fields displayed
- Edit button → edit modal
- "Send Follow-Up Email" button → mailto: link
- Last 5 pickups for this supplier
- Delete button → confirmation modal → soft delete

**Fields:**
- `company_name` (required)
- `location` (required)
- `contact_name`
- `phone`
- `email`
- `bol_email` + `bol_same_as_primary` checkbox ("BOL email same as primary")
- `industry`
- `tote_types` (checkboxes: 275 / 330)
- `working_hours` (text)
- `followup_weeks` (integer 1–10, default 4) — per-supplier follow-up timeline
- `is_active` (boolean, default true) — inactive suppliers excluded from follow-up; shown with Inactive badge in list
- `is_hazmat` (boolean)
- `warnings` (text)
- `notes` (text)

**Detail page extras:**
- `followup_weeks` dropdown in contact card — updates inline via HTMX on change
- Set Inactive / Set Active toggle button in header — full page reload on change
- Avg Qty 275 / Avg Qty 330 computed from actual gradeout records (not manually entered)

**Follow-up list behavior:**
- Filter: last gradeout date > `followup_weeks * 7` days ago, OR no gradeouts ever
- Sort: most days past deadline first; no-gradeout suppliers always at top
- Excludes inactive and soft-deleted suppliers

**Acceptance criteria:**
- [ ] Search filters via HTMX — no full page reload
- [ ] Soft delete sets `is_deleted=true`, `deleted_at=now()` — record not deleted from DB
- [ ] Soft-deleted suppliers hidden from all list views and follow-up logic
- [ ] Inactive suppliers show Inactive badge in list; excluded from follow-up
- [ ] `followup_weeks` dropdown updates without page reload
- [ ] Avg Qty 275/330 on detail page computed from gradeout averages, not stored field
- [ ] All inputs validated at route boundary — empty `company_name` or `location` returns 422 (SEC-02)
- [ ] All DB queries use ORM — no raw SQL string concatenation (SEC-03)
- [ ] `bol_email` field hidden/disabled when `bol_same_as_primary` checked
- [ ] Contact column absent from list view — contact info on detail page only
- [ ] List shows washable/cage avg split for both 275 and 330
- [ ] `list.html` thead column count matches `_row.html` exactly

---

## F4 — Pickups

> **Revised 2026-04-16:** Original spec replaced. The original F4 (pickup dates, tote counts, separate /pickups page) was never implemented. New design is intentionally simpler — pickups are confirmation events only, managed through supplier detail and the gradeout form.

### Problem Statement
Pickups get confirmed with multiple suppliers before gradeouts are uploaded. There's no way to track how many are pending or link a gradeout to the right confirmed pickup event.

### User Story
As a contractor, I want to log when a pickup is confirmed with a supplier so I can track what's pending and link each gradeout to the right pickup.

### User Flow
1. User selects "Pickup Confirmed" in the Last Action dropdown (dashboard, suppliers list, or supplier detail) → confirmation modal appears → "Yes, record it" creates a pickup record (status: confirmed) instantly; "No, go back" resets the dropdown
2. Supplier detail page shows: "X pickup(s) confirmed, awaiting gradeout"
3. When uploading a gradeout for a supplier:
   - 0 confirmed pickups → gradeout saves normally with no pickup link
   - 1 confirmed pickup → auto-linked silently (no user action)
   - 2+ confirmed pickups → required dropdown: "Which pickup does this gradeout belong to?" (cannot submit without selecting)
4. On gradeout save → linked pickup (if any) transitions to `completed` in same DB transaction
5. User can cancel a confirmed pickup from the dashboard modal (see F11)

### Fields
- `id`, `supplier_id` (FK, non-deleted suppliers only), `created_at`, `status`: `confirmed` / `completed` / `cancelled`

### Business Logic
- No pickup date, no tote estimate fields — a pickup is a confirmation event only
- `confirmed → completed`: triggered automatically by gradeout save
- `confirmed → cancelled`: manual, via Cancel button in dashboard modal
- Only `confirmed` pickups count toward stat card total and supplier detail count
- One pickup ↔ one gradeout — a completed pickup cannot be re-linked

### Acceptance Criteria
- [x] Selecting "Pickup Confirmed" in Last Action dropdown (dashboard / suppliers list / supplier detail) shows confirmation modal → creates pickup with `status=confirmed`
- [x] Re-selecting "Pickup Confirmed" when already set triggers the modal again (logs another pickup)
- [ ] Supplier detail shows count of `confirmed` pickups (excludes completed and cancelled)
- [ ] Gradeout form: 0 confirmed → no pickup field shown; 1 confirmed → auto-linked; 2+ → required dropdown (SEC-02)
- [ ] Linked pickup transitions to `completed` in same DB transaction as gradeout save (EH-01)
- [ ] Cancelled and completed pickups excluded from all counts and dropdowns
- [ ] One pickup cannot be linked to more than one gradeout
- [ ] All DB queries use ORM — no raw SQL (SEC-03)

### Edge Cases
- 0 confirmed pickups when uploading gradeout → gradeout saves with no pickup link, no error
- All confirmed pickups cancelled before gradeout upload → treated as 0 confirmed case
- Pickup already `completed` → cannot be cancelled or re-linked

### Out of Scope
- Pickup date or tote count estimates on the pickup record
- Separate /pickups list page
- Status transitions beyond confirmed / completed / cancelled

---

## F5 — Gradeouts

**List page (`/gradeouts`):**
- Filter by supplier, month
- Columns: Supplier, Date Received, 275 Usable, 330 Usable, Total Usable, Revenue, PDF
- "Add Gradeout" → `/gradeouts/new`

**New gradeout page (`/gradeouts/new`):**
- Pickup dropdown (required): shows only pickups without an existing gradeout
- Pre-selects pickup if `?pickup_id=` param present
- PDF upload (optional) — stored in Supabase Storage
- Manual form for all tote count fields
- Submit → save, redirect to `/gradeouts`

**Fields:**
- `pickup_id` (FK, required — from dropdown)
- `supplier_id` (auto-set from `pickup.supplier_id` — not user-entered)
- `date_received` (date, required)
- `totes_275_good_washable`, `totes_275_good_cage`, `totes_275_total_usable`, `totes_275_junk` (integers ≥ 0)
- `totes_330_good_washable`, `totes_330_good_cage`, `totes_330_total_usable`, `totes_330_junk` (integers ≥ 0)
- `pdf_storage_path` (text, nullable — Supabase Storage path)
- `notes` (text)

**Revenue displayed:** `(totes_275_total_usable + totes_330_total_usable) × TOTE_RATE` — computed, not stored

**On gradeout save:**
- Linked pickup auto-transitions to `completed`
- `pickup.pickup_date` set to `gradeout.date_received`
- Both updates in same DB transaction

**Acceptance criteria:**
- [ ] PDF upload optional — form submits without file
- [ ] PDF stored in Supabase Storage only — never on local filesystem
- [ ] `supplier_id` set from pickup — never from user input (SEC-02)
- [ ] All tote counts validated as integers ≥ 0 (SEC-02)
- [ ] Warning (not hard block) if total_usable > good_washable + good_cage
- [ ] Pickup dropdown shows only pickups without an existing gradeout
- [ ] Pickup auto-completes within same DB transaction as gradeout save (EH-01)

---

## F6 — Invoices

**List page (`/invoices`):**
- Columns: Month, Gradeout Count, 275 Usable, 330 Usable, Total Revenue, Generated, Sent
- Sorted by month descending
- "Generate Invoice" → month selector modal

**Invoice generation flow:**
1. Select month (defaults to current month)
2. System queries all gradeouts where `date_received` in that month
3. If no gradeouts: error "No gradeouts found for [Month Year]" — no invoice created
4. If invoice already exists for month: show existing (no duplicate)
5. Preview: one row per gradeout (Supplier, Date, 275 Usable, 330 Usable, Revenue) + totals row
6. "Save Invoice" → creates invoice record
7. "Send Invoice" → mailto: pre-filled

**Stored invoice fields:**
`id`, `month` (first day of month), `gradeout_count`, `total_usable_275`, `total_usable_330`, `total_revenue`, `generated_at`, `sent_at`

**Invoice mailto: pre-fill:**
- To: `INVOICE_RECIPIENT_EMAIL` env var
- Subject: `Invoice — [Month Year]`
- Body: plain-text gradeout table + total revenue

**Acceptance criteria:**
- [ ] One invoice per calendar month — second generate returns existing
- [ ] `INVOICE_RECIPIENT_EMAIL` from env var — not hardcoded (SEC-01, CQ-04)
- [ ] `sent_at` set when "Send Invoice" clicked
- [ ] Zero gradeouts in month → error shown, no invoice created
- [ ] Revenue per row = `(275_usable + 330_usable) * TOTE_RATE`

---

## F7 — Leads

**List page (`/leads`):**
- Filter by `outreach_status`
- Columns: Company, Location, Industry, Contact, Status badge, Last Contact, Potential Volume
- "Add Lead" → modal
- Inline status update via HTMX dropdown

**Fields:**
- `company_name` (required)
- `location`, `industry`
- `contact_name`, `contact_phone`, `contact_email`
- `outreach_status`: research / contacted / responded / not_interested / active_supplier (default: research)
- `last_contact_date` (date)
- `potential_volume` (text)
- `notes` (text)

**Convert to supplier:**
- When status set to `active_supplier`: modal appears — "Convert to Supplier?"
- Pre-fills supplier form with: company_name, location, contact_name, contact_phone, contact_email from lead
- Submitting creates supplier record — lead record is NOT deleted

**Acceptance criteria:**
- [ ] Status update via HTMX — no full page reload
- [ ] `company_name` required — empty returns 422 (SEC-02)
- [ ] Setting `active_supplier` triggers convert-to-supplier modal with pre-filled data
- [ ] Converting creates supplier but does not delete or modify lead record

---

## F8 — Follow-Up Email Templates (mailto:)

**Supplier follow-up mailto: pre-fill:**
```
To: {supplier.email}
Subject: IBC Tote Pickup – {company_name}
Body:
Hi {contact_name},

Hope you're doing well. I wanted to follow up on IBC tote pickups.
It's been {days_since_last_pickup} days since our last pickup on {last_pickup_date}.

Please let me know if you have totes available and I'll coordinate with our dispatch team.

Thank you!
```

**Fallbacks:**
- Missing `contact_name` → use "there"
- Missing `last_pickup_date` → omit the "It's been X days..." line

**Acceptance criteria:**
- [ ] All template variables filled server-side before generating mailto: URL
- [ ] Subject and body URL-encoded using `urllib.parse.quote` (SEC-02)
- [ ] Graceful fallback for missing contact_name and last_pickup_date

---

## F9 — Growth Planning

### Problem Statement
The operator has no way to connect their revenue target to operational decisions. They know what they earn per tote, but can't answer "how many suppliers do I actually need to hit $X this year?" This feature makes the growth target concrete and explorable.

### User Story
As a solo tote sourcing contractor, I want to set an annual revenue target and explore the supplier/shipment combinations required to hit it, so I can make informed decisions about how aggressively to pursue new suppliers.

### User Flow
1. User navigates to **Growth Planning** tab (6th nav item)
2. **Section 1 — Target:** User sees current saved target (or empty state if never set). User enters/edits annual revenue target → saves. Target persists across sessions until explicitly changed.
3. **Section 2 — Sliders:** Four sliders load with DB-derived defaults (active supplier count, avg shipments/supplier/year, avg usable totes/shipment, $5 revenue/tote). Each slider has a companion text input, bidirectionally synced.
4. User drags any slider → dependent slider auto-adjusts in real time to maintain the target.
5. No save action needed for sliders — they're an exploration tool, not persisted state.

### Business Logic

**Formula:**
```
Annual Revenue = Suppliers × Shipments/Supplier/Year × Totes/Shipment × Revenue/Tote
```

**Dependency rules:**
- Move **Suppliers** → recalculate **Shipments/Supplier/Year** to hit target
- Move **Shipments/Supplier/Year**, **Totes/Shipment**, or **Revenue/Tote** → recalculate **Suppliers** to hit target

**Slider defaults (loaded from DB on page render):**
- **Active Suppliers:** count of non-deleted, `is_active=True` suppliers
- **Shipments/Supplier/Year:** average gradeout count per active supplier over the last 12 months (rounded to 1 decimal)
- **Usable Totes/Shipment:** average of `(totes_275_total_usable + totes_330_total_usable)` per gradeout, all time (rounded to 1 decimal)
- **Revenue/Tote:** `settings.TOTE_RATE` ($5)

**Slider scales:**
| Slider | Min | Max | Step |
|---|---|---|---|
| Active Suppliers | 0 | 100 | 1 |
| Shipments/Supplier/Year | 0 | 52 | 1 |
| Usable Totes/Shipment | 0 | 60 | 1 |
| Revenue/Tote | $0 | $10 | $1 |

**Target persistence:** Stored in a new `app_settings` table (key: `growth_target`, value: float). One row, upserted on save.

**Slider math is client-side only** — vanilla JS, no round-trips on drag.

### Acceptance Criteria
- [ ] Target input saves to `app_settings` table and reloads correctly on next page visit
- [ ] Page loads with DB-derived defaults for all 4 sliders
- [ ] Moving Suppliers slider recalculates Shipments/Supplier in real time
- [ ] Moving Shipments, Totes, or Revenue/Tote recalculates Suppliers in real time
- [ ] Each slider and its companion text input stay in sync — changing one updates the other
- [ ] No target set yet → target section shows empty state ("No target set yet")
- [ ] Calculated value exceeding slider max → slider clamps to max, text input shows actual calculated value
- [ ] Division by zero (Totes=0 or Revenue/Tote=0) → dependent slider shows "—", no crash

### Edge Cases
- **No gradeout data yet:** avg shipments/supplier and avg totes/shipment both default to `0` — user adjusts sliders manually
- **No active suppliers:** Suppliers slider defaults to `0`
- **Target not set:** sliders still functional for exploration; target section shows empty state
- **Calculated Suppliers > 100:** clamp slider to 100, show actual number in text input
- **Calculated Shipments > 52:** clamp slider to 52, show actual number in text input

### Out of Scope
- Saving slider state between sessions (sliders always reset to DB-derived defaults on load)
- Historical target tracking / trend over time
- Breaking down the gap as an explicit callout — the math is visible in the sliders
- Any chart or graph visualization (V2)
- Per-supplier breakdown of what's needed

### Success Metric
User can set a target, adjust sliders, and immediately see the operational requirements — without needing a spreadsheet.

---

## F10 — Supplier Last Action Tracking

### Problem Statement
When following up with suppliers, there's no record of where things stand in the outreach cycle. "Last Pickup" tells you when you last got totes, but not what's actively happening — did you just follow up? Did they say maybe? Is a pickup confirmed? Without this, the contractor has to remember each supplier's status in their head.

### User Story
As a solo contractor, I want to record where each supplier stands in my outreach cycle so I can prioritize follow-ups and see at a glance what's in motion across all suppliers.

### User Flow
1. User sees "Last Action" column in the Follow-Up panel (dashboard), suppliers list, and supplier detail page
2. Each row shows a stage badge + date beneath it (or "—" if no action recorded)
3. User taps/clicks the stage badge → dropdown → selects new stage → saves inline via HTMX (no page reload)
4. When a gradeout is saved for a supplier → stage and date automatically reset to "—"

### Business Logic
- Two new columns on `suppliers`: `last_action_stage VARCHAR(32)` nullable, `last_action_date DATE` nullable
- Stage values:

| Value | Display label |
|---|---|
| null | — |
| `followed_up` | Followed Up |
| `responded_no` | Responded No |
| `pickup_confirmed` | Pickup Confirmed |
| `maybe` | Maybe — Follow Up Later |

- Setting a stage → `last_action_date = today` (set server-side, never user-entered)
- Clearing stage (selecting "—") → both `last_action_stage` and `last_action_date` set to null
- Saving a gradeout → auto-resets both fields to null for that supplier (same DB commit as gradeout save)
- `last_contacted_date` renamed to `last_pickup_date` — auto-set from `gradeout.date_received` on gradeout save
- Stage dropdown present in 3 locations via HTMX `PATCH` on change: dashboard Follow-Up panel, suppliers list, supplier detail page

### Acceptance Criteria
- [ ] `last_action_stage` and `last_action_date` columns added to `suppliers` via migration
- [ ] `last_contacted_date` renamed to `last_pickup_date` via same migration
- [ ] `PATCH /suppliers/{id}/action-stage` sets stage + today's date; empty value clears both to null
- [ ] Stage dropdown in dashboard follow-up panel updates inline via HTMX — no page reload
- [ ] Stage dropdown in suppliers list updates inline via HTMX — no page reload
- [ ] Stage dropdown in supplier detail page updates inline via HTMX — no page reload
- [ ] Saving a gradeout resets `last_action_stage` and `last_action_date` to null for that supplier
- [ ] Saving a gradeout sets `last_pickup_date` to `gradeout.date_received` for that supplier
- [ ] Both gradeout save and supplier field updates commit in the same DB transaction (EH-01)
- [ ] `last_action_date` set server-side — never from user input (SEC-02)
- [ ] All DB queries use ORM — no raw SQL (SEC-03)

### Edge Cases
- Gradeout deleted: `last_pickup_date` is NOT rolled back — stays as-is (gradeout happened; deletion is a correction)
- Supplier with no actions: both fields null, display "—" in all locations
- Stage set then gradeout saved same day: gradeout save wins — stage resets to "—"

### Out of Scope
- Full action history log — only current state tracked
- Notes per action stage
- Timestamps beyond date (no time component)
- Auto-setting stage based on any system event other than gradeout save

---

## F11 — Dashboard Enhancements

> **Added 2026-04-16**

### Problem Statement
The dashboard stat cards are read-only and don't help the user act. The "Totes" card shows data already visible elsewhere. There's no way to see pending confirmed pickups at a glance, and no historical view of revenue trends over time.

### User Story
As a contractor, I want my dashboard to show what needs attention now (pending pickups) and how my revenue is trending over time, with quick access to the underlying data.

### User Flow — Stat Card Changes
1. "Totes" stat card replaced with **"Pickups Confirmed"** — shows count of all `status=confirmed` pickups across all suppliers; not period-scoped
2. Tapping "Pickups Confirmed" card → modal listing all confirmed pickups: supplier name, date confirmed, Cancel button
3. Cancel button sets pickup `status=cancelled` → modal count updates via HTMX without full page reload
4. "Suppliers" card → tapping navigates to `/suppliers`
5. "Gradeouts" card → tapping navigates to `/gradeouts`

### User Flow — Revenue Chart
1. Between the stat cards and the two bottom panels: a collapsible chart section
2. Collapsed by default — entire header/bar tappable to expand or collapse
3. Inside: two pill toggles:
   - **Time:** Monthly (12 most recent calendar months) / Annual (last 5 calendar years)
   - **Value:** Per Period (each bar = that period's revenue) / Cumulative (running total left to right)
4. Chart renders immediately on expand using data already injected at page load
5. Toggling time or value re-renders chart client-side — no server round-trip

### Business Logic
- Pickups Confirmed count: `SELECT COUNT(*) FROM pickups WHERE status = 'confirmed'` — not period-scoped, always all-time pending
- Revenue per period: SUM of `(totes_275_total_usable + totes_330_total_usable) × TOTE_RATE` across all gradeouts in that period
- Monthly: last 12 calendar months (include months with $0)
- Annual: last 5 calendar years (include years with $0)
- Cumulative: running sum left to right across displayed periods
- Chart.js loaded from CDN — no npm, no build step

### Acceptance Criteria
- [ ] "Pickups Confirmed" stat card shows count of `status=confirmed` pickups — not period-scoped
- [ ] Tapping Pickups Confirmed card opens modal listing confirmed pickups (supplier name + created date)
- [ ] Cancel button in modal sets pickup `status=cancelled`; modal list updates via HTMX without page reload
- [ ] Suppliers card click navigates to `/suppliers`
- [ ] Gradeouts card click navigates to `/gradeouts`
- [ ] Chart section collapsed by default; tapping anywhere on header/bar toggles open/close
- [ ] Monthly view: 12 bars, one per calendar month, most recent on right
- [ ] Annual view: up to 5 bars, one per calendar year
- [ ] Per Period: each bar is that period's revenue only
- [ ] Cumulative: each bar is running sum from leftmost period
- [ ] Periods with no gradeouts show $0 bar (not omitted)
- [ ] No-data state ("No gradeout data yet") shown when no gradeouts exist at all
- [ ] Chart.js loaded from CDN (CQ-04) — no build step
- [ ] Chart data injected server-side as JSON; chart rendered client-side

### Edge Cases
- All pickups cancelled → Pickups Confirmed shows 0
- No gradeouts in a period → $0 bar displayed, not skipped
- Cumulative with all $0 periods → flat $0 line, no crash

### Out of Scope
- Chart drill-down to individual gradeouts
- Exporting chart data
- More than 5 years of annual history

---

## F12 — Suppliers Tab Improvements

> **Added 2026-04-16**

### Problem Statement
The current supplier filter options (Hazmat Only, Needs Follow-Up) are rarely used. The "Hazmat" column header is misleading — it also shows inactive status. There's no quick way to filter by where you are in the outreach cycle, and inactive suppliers can't be hidden cleanly.

### User Story
As a contractor, I want to filter my supplier list by outreach stage and toggle inactive suppliers in/out so I can focus on what's actionable.

### User Flow
1. Supplier list loads with Active Only toggle on by default (excludes `is_active=False` suppliers)
2. Filter dropdown defaults to "All Suppliers" (no stage filter)
3. User selects a stage from the dropdown (e.g., "Pickup Confirmed") → list filters to only suppliers with that `last_action_stage`, via HTMX
4. User taps "Show All" toggle → inactive suppliers appear in list with Inactive badge
5. Search, stage filter, and active toggle all work together — all three params sent on every HTMX request

### Business Logic
- Filter dropdown values map to `last_action_stage` column: `followed_up`, `responded_no`, `pickup_confirmed`, `maybe`
- "All Suppliers" → no stage filter applied
- Active Only (default): adds `WHERE is_active = TRUE` to query
- Show All: no `is_active` filter
- Column header rename: "Hazmat" → "Status"; cell logic unchanged (already shows Hazmat + Inactive badges)

### Acceptance Criteria
- [ ] Filter dropdown options: All Suppliers / Followed Up / Responded No / Pickup Confirmed / Maybe
- [ ] Selecting a stage filters list via HTMX — no full page reload
- [ ] "Active Only" is the default state on page load — inactive suppliers excluded
- [ ] "Show All" toggle includes `is_active=False` suppliers; Inactive badge visible on those rows
- [ ] Search + stage filter + active toggle all sent together on every HTMX request
- [ ] "Status" replaces "Hazmat" in `<thead>`; `_row.html` cell logic unchanged
- [ ] `list.html` thead column count matches `_row.html` column count exactly (CQ-06)
- [ ] All filtering uses ORM — no raw SQL (SEC-03)

### Edge Cases
- All suppliers inactive + Active Only toggle → empty state shown ("No suppliers found")
- Stage filter + Show All → shows all suppliers with that stage regardless of active status

### Out of Scope
- Saving filter state between sessions
- Multi-select stage filter
- Removing the Hazmat or Needs Follow-Up concepts — only the filter UI is changed
