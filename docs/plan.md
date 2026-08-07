# Plan: tote-platform

**What this is:** A public demo repo showcasing two IBC-tote business applications as v1 (before) and v2 (after). Not production. Source repos stay at `github.com/aliciaherr/Tote-ops` and `github.com/aliciaherr/ToteTrack` and remain the live systems.

**Deliverables:**
1. A live, clickable demo of ToteTrack (v2) at `https://swarnimb.github.io/tote-platform/`
2. Screenshot assets from both apps, paired before/after, for `swarnimbagre.com`

**Non-goals:** merging the two codebases, any production deployment, any real data.

---

## Repo layout

```
tote-platform/
  v1-tote-ops/      FastAPI + Jinja + Postgres. Runs locally only. Screenshot source.
  v2-totetrack/     Next.js 14. Static-exported to GitHub Pages. Live demo.
  assets/           before/after screenshot pairs
  docs/plan.md      this file
  README.md
  .github/workflows/deploy-demo.yml
```

---

## Seed data standard (applies to BOTH apps)

This is the quality bar, not a footnote. Both demos are judged on whether they look like a real business that has been running for a year.

- **Span:** exactly 12 months back from the seed date. No gaps — every month has activity.
- **Coverage:** every table populated. Every list view has enough rows to scroll and paginate.
- **No blanks:** every screen, tab, filter, dropdown, chart, counter, badge and empty-state path must render real data. If a button reveals a panel, that panel has content.
- **Distribution:** records spread across every enum value — every status, stage, grade, priority. No status with zero rows.
- **Realism:** plausible company names, contact names, addresses, phone numbers, tote counts, dollar amounts, dates. Amounts consistent with the app's own business rules (e.g. Tote-Ops `TOTE_RATE = 5`).
- **Internal consistency:** invoices reconcile to their pickups/orders; totals match line items; dashboard aggregates match the underlying rows.
- **Recency:** some records dated within the last 7 days so "recent activity", "upcoming", and "follow-up due" surfaces are populated.
- **Fully synthetic:** zero real supplier, customer, or contact names. Both apps have live daily users — nothing traceable.

---

## What changed during the build

Three things landed differently from the plan below. Recorded here rather than
edited away, so the reasoning survives.

1. **PostgreSQL is portable, not installed.** `winget install` needs a UAC
   elevation prompt that could not be answered from an automated shell. The
   EDB binary zip extracted to `%LOCALAPPDATA%\pgsql-demo`, running on port
   5433, needs no admin rights and leaves no system service behind. Zero code
   changes either way, which was the point of choosing Postgres over SQLite.

2. **v2 needed no fixture layer.** The plan assumed the card-benefits pattern:
   replace every Supabase read with seeded JSON. That turned out to be
   unnecessary — `output: 'export'` prerenders at build time, so pointing the
   real Drizzle queries at a locally seeded Postgres bakes genuine query output
   into the HTML. What the export genuinely cannot contain is Server Actions
   and a cookie-reading auth client; those are swapped by webpack module
   replacement (`lib/demo/actions/`, `lib/demo/supabase-server.ts`). Far less
   code than a fixture layer, and the demo exercises the real query paths.

3. **The seed data standard was the real work, as predicted.** Its assertions
   caught three defects that all render as "the demo looks fake": a status rule
   that left the current month with no completed orders, a calendar fill that
   starved whichever end of its window came last, and a scheduling pass that
   piled an extra month of revenue into one chart bar.

## Tasks

### Phase 1 — Repo setup

**T1. [x] Install PostgreSQL 17 locally**
Create database `toteops_demo`. Verify connection.

**T2. [x] Create the repo**
`git init` in `tote-platform/`, first commit. The GitHub remote is created as part of T10.

**T3. [x] Copy both codebases**
Copy `Tote-ops/` → `v1-tote-ops/` and `ToteTrack/` → `v2-totetrack/`.
Exclude: `.git`, `.env`, `.env.local`, `node_modules`, `.next`, `__pycache__`, `.pytest_cache`, `tsconfig.tsbuildinfo`.
Verify no secrets landed in the copy before the first commit.

### Phase 2 — v1 Tote-Ops (local, screenshot source)

**T4. [x] Boot Tote-Ops against local Postgres**
`.env` with local `DATABASE_URL`, dummy Supabase values, demo password. Run `alembic upgrade head`.

**T5. [x] Write `seed_demo.py`**
Suppliers, pickups, gradeouts, leads, invoices, app_settings — to the seed data standard above.

**T6. [x] Screenshot every v1 screen**
Dashboard, suppliers (list + detail), pickups, gradeouts (list/new/edit), leads, invoices, growth. Desktop 1280px + iPad 768px.

### Phase 3 — v2 ToteTrack (live demo)

**T7. [x] Build the demo fixture layer**
Superseded — see "What changed during the build" above. No fixture layer was needed: the export prerenders the real queries against a seeded Postgres. Only Server Actions and the cookie-reading auth client are shimmed, both gated on `NEXT_PUBLIC_DEMO_MODE`.

**T8. [x] Seed the v2 fixtures**
Customers, contacts, orders, leads, lead notes, invoices, support tickets, attachments — same seed data standard.

**T9. [x] Static export config**
Folded into `next.config.js` behind `NEXT_PUBLIC_DEMO_MODE` rather than a separate `next.config.demo.mjs`, so the production config path stays byte-identical with the flag unset: `output: 'export'`, `basePath: '/tote-platform'`, `images.unoptimized`, `trailingSlash`.

**T10. [ ] Deploy to GitHub Pages**
`deploy-demo.yml` is written and the schema/seed/build chain it runs is verified end to end against a fresh database locally. Still open: create the GitHub repo, push, enable Pages, and verify the live URL — no 404s on basePath assets, no console errors, every route renders.

**T11. [x] Screenshot every v2 screen**
Dashboard, customers, orders, leads, invoices, calendar, support. Same widths as T6.

### Phase 4 — Assets

**T12. [x] Build before/after pairs**
Matched screens only: Dashboard, Leads, Invoices. Remaining v2 screens ship as standalone shots.

**T13. [x] README**
What the repo is, the live demo link, the v1/v2 framing, a note that all data is synthetic.

---

## Risks

- **T7 is the long pole.** ToteTrack is RSC + Server Actions end to end. Static export rewrites every data path. Fallback if it fights back: v2 becomes screenshot-only, losing the live URL but keeping the assets.
- **T5/T8 volume.** The seed data standard is the bulk of the effort, deliberately. Thin seed data is the most likely way this demo reads as fake.
