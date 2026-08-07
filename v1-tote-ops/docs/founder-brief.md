# Founder Brief: Tote-Ops

> Plain-language record of every architectural decision.
> Updated in parallel with every `docs/architecture.md` change.
> Each entry links to the relevant architecture section.

---

## 2026-04-19 — Decision: Pickup confirmation triggered via action stage dropdown, not a dedicated button
**Architecture section:** `docs/architecture.md → Data Layer`, `migrations/versions/0008`, `0010`

**Decided:** Confirming a pickup no longer requires a separate "Confirm Pickup" button. Instead, selecting `pickup_confirmed` in the Last Action dropdown (on the dashboard, suppliers list, or supplier detail page) shows a confirmation modal. Tapping "Yes, record it" creates a `pickups` row and saves the stage. Tapping "No" resets the dropdown. Re-selecting `pickup_confirmed` when already set also triggers the modal. The modal lives in `base.html` so it works everywhere without duplication.

**Means for your product:** You confirm pickups in the same place you already log follow-up actions — no separate button to find. Works from the dashboard follow-up table without even opening the supplier detail page. The Pickups Confirmed scorecard on the dashboard now accurately reflects real pickup events, not just the action stage label.

**Check before approving:** Confirmed — implemented, backfill migrations run, dates corrected.

**What this closes off:** The dedicated "Confirm Pickup" button spec in PRD F4 is superseded. If a non-dropdown confirmation surface is ever needed (e.g. bulk confirm), it would be additive — this change doesn't prevent that.

---

## 2026-04-16 — Decision: Chart.js CDN added for dashboard revenue chart
**Architecture section:** `docs/architecture.md → Stack`

**Decided:** Chart.js loaded from CDN (`https://cdn.jsdelivr.net/npm/chart.js`) to power the revenue bar chart on the dashboard. No npm, no build step — consistent with the existing CDN-only frontend approach.

**Means for your product:** You get an interactive bar chart on the dashboard showing monthly and annual revenue trends. One new CDN dependency — the app will not render the chart if the CDN is unreachable (offline use), but all other functionality is unaffected.

**Check before approving:** Does the chart render correctly on iPad (768px viewport) with the collapse/expand toggle working?

**What this closes off:** If you ever need a more advanced chart library (D3, Recharts), you'd swap Chart.js out — no lock-in.

---

## 2026-04-16 — Correction: Stack table Render → Vercel (completing prior session fix)
**Architecture section:** `docs/architecture.md → Stack`

**Decided:** The Stack table row previously still read "Render (free tier)" after last session's correction. Fixed to "Vercel (Python/WSGI)" — consistent with the Deployment section and all other docs.

**Means for your product:** Documentation only — no functional change.

**Check before approving:** Nothing to verify — documentation correction only.

**What this closes off:** Nothing.

---

## 2026-04-14 — Decision: Deployment platform corrected to Vercel
**Architecture section:** `docs/architecture.md → Deployment`

**Decided:** Tote-Ops deploys to Vercel, not Render. Architecture docs updated to reflect this.

**Means for your product:** No functional change — the app runs the same way. Vercel handles the hosting. Environment variables are set in the Vercel dashboard. The `Procfile` start command is unchanged.

**Check before approving:** Are your environment variables (DATABASE_URL, SUPABASE_URL, etc.) set correctly in the Vercel dashboard?

**What this closes off:** Nothing — this was a documentation correction, not a new decision.

---

## 2026-03-15 — Decision 1: Sync SQLAlchemy over Async
**Architecture section:** `docs/architecture.md → Stack + Key Architectural Decisions`

**Decided:** Use synchronous SQLAlchemy 2.0, not async SQLAlchemy.

**Means for your product:** Simpler code throughout the entire backend. Every database call is straightforward — no async/await complexity. For a single-user tool with no concurrent requests, this is the right trade-off.

**Check before approving:** Are you comfortable accepting slightly slower theoretical performance under load, knowing it will never matter for solo use?

**What this closes off:** Migrating to async SQLAlchemy later requires rewriting all DB queries across every service file. For a personal tool, this will likely never be necessary.

---

## 2026-03-15 — Decision 2: Session-Based Auth via Signed Cookies
**Architecture section:** `docs/architecture.md → Auth Flow`

**Decided:** Starlette `SessionMiddleware` handles auth via signed browser cookie. Single password checked against `APP_PASSWORD` env var. 30-day session expiry.

**Means for your product:** You log in once on your iPad, stay logged in for 30 days. No username, no token refresh, no complexity. The session is just a signed cookie in your browser.

**Check before approving:** `SESSION_SECRET_KEY` must be a long random string set in Render's env vars before deploying. If someone obtains this key, they can forge a session. Keep it secret.

**What this closes off:** Adding multi-user support later requires replacing this entirely with a proper auth system (Supabase Auth or similar). Straightforward to do — just a swap.

---

## 2026-03-15 — Decision 3: HTML-First Responses (No JSON API)
**Architecture section:** `docs/architecture.md → API Layer`

**Decided:** All FastAPI routes return HTML (full pages or HTMX fragments). No JSON API layer exists.

**Means for your product:** Simpler backend — one response format, no serialization layer, no frontend/backend split. The app works entirely in the browser without JavaScript frameworks.

**Check before approving:** Confirmed in kickoff — browser only, no mobile app in scope. This is the right call for V1.

**What this closes off:** Building a native mobile app or third-party integration later requires adding a JSON API layer from scratch. Not hard, but it's additive work, not a refactor.

---

## 2026-03-15 — Decision 4: Supabase Storage for PDFs
**Architecture section:** `docs/architecture.md → File Upload Flow`

**Decided:** All uploaded gradeout PDFs stored in Supabase Storage bucket `gradeout-pdfs`. Path stored in DB. Signed URLs generated on-demand with 1-hour expiry.

**Means for your product:** PDFs survive Render redeploys (Render's filesystem is wiped on every deploy — local file storage would lose all PDFs). Files are accessible via a time-limited link when you click to view.

**Check before approving:** You need to manually create the `gradeout-pdfs` bucket in your Supabase dashboard before deploying. This is a one-time setup step.

**What this closes off:** Nothing meaningful. Supabase Storage can be swapped for any S3-compatible storage later with changes only to `app/storage.py`.

---

## 2026-03-15 — Decision 5: No PDF Auto-Extraction in V1
**Architecture section:** `docs/architecture.md → Stack (PDF Extraction row)`
**Related:** `docs/assumptions.md → ASSUMPTION-03`

**Decided:** No PDF extraction logic in V1. Gradeout PDFs are scanned handwriting — pdfplumber cannot read them. Manual form entry is the input method. PDFs stored alongside the record for reference.

**Means for your product:** You upload the PDF (it's saved), then manually fill in the gradeout form. Two steps instead of one. Fast on iPad with the structured form.

**Check before approving:** This was the correct call given the constraint discovery. Claude Vision API could automate extraction in V2 at minimal cost (~$0.01–0.05/month).

**What this closes off:** Nothing. V2 can add extraction by adding a route that sends the uploaded PDF to Claude Vision API and pre-fills the form. The form and storage infrastructure are already in place.

---

## 2026-03-18 — Decision 7: app_settings Key-Value Table for Growth Target Persistence
**Architecture section:** `docs/architecture.md → Data Layer`

**Decided:** A new `app_settings` table stores app-level configuration as key-value pairs. The growth revenue target is the first key (`growth_target`). The key is the primary key — no UUID.

**Means for your product:** Your revenue target persists across page reloads, browser restarts, and Render redeploys. It stays set until you explicitly change it. The table is also available for future app-level settings without needing a new migration each time.

**Check before approving:** Confirmed — no concerns raised.

**What this closes off:** Nothing. This is additive. New settings keys can be added without schema changes.

---

## 2026-03-18 — Decision 8: Client-Side Vanilla JS for Growth Planning Slider Math
**Architecture section:** `docs/architecture.md → HTMX Usage`

**Decided:** All slider recalculation logic runs in vanilla JS embedded in `growth/index.html`. No server round-trips on drag. Page loads with server-rendered defaults; JS takes over from there.

**Means for your product:** Sliders respond instantly as you drag — no lag, no network dependency. The trade-off is that the calculation logic lives in the browser, not the server. For a formula this simple (`Suppliers × Shipments × Totes × Rate = Target`), that's the right call.

**Check before approving:** Confirmed — no concerns raised.

**What this closes off:** Nothing. If the formula ever becomes complex enough to warrant server-side logic, the JS can be replaced with HTMX calls to a `/growth/calculate` endpoint without touching anything else.

---

## 2026-03-15 — Decision 6: String(36) for UUID Primary and Foreign Keys
**Architecture section:** `docs/architecture.md → Data Layer`

**Decided:** All primary key and foreign key columns store UUIDs as 36-character strings (`String(36)`) rather than using PostgreSQL's native UUID type.

**Means for your product:** No visible difference — UUIDs still look and behave the same. IDs are still unique and unguessable. The only difference is internal: they're stored as text in the database rather than as a native 16-byte binary type.

**Check before approving:** Are you OK with UUIDs stored as strings? The trade-off is a small amount of extra storage per row (36 bytes vs 16 bytes) — irrelevant at your volume.

**What this closes off:** Nothing. A future migration could change all PK columns to native UUID type if desired — straightforward but tedious. Not worth doing.
