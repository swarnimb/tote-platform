# QA Report

**Date:** 2026-04-17
**Status:** APPROVED

---

## Coverage Assessment

### Critical Paths
- [x] Auth flows tested: **PASS** — 5 tests cover login (correct/wrong password), unauthenticated redirect, expired session redirect, logout + session clearance.
- [ ] Payment flows tested: **N/A** — No payments in V1 scope.
- [x] Data write operations tested: **PASS** — All modules covered.
  - Suppliers: create, soft-delete, action stage set/clear — tested
  - Pickups: create (3 cases), cancel (3 cases), DELETE route, POST route — 11 tests in `test_pickups.py`
  - Gradeouts: create + 4 pickup-linking cases — tested
  - Invoices: save, overwrite, delete, toggle sent — tested
  - Leads: create (error case), update status — tested
  - Growth: set/update setting, reject negative target — tested
- [x] Access control tested: **PASS** — `authenticated_client` / `expired_session_client` fixtures cover unauthorized access throughout.

### Test Suite Results

**100 tests — 100 passed, 0 failed** (run: 2026-04-17, Python 3.13.3, pytest 9.0.2)

All tests isolated (SQLite in-memory, function-scoped fixtures). Storage mocked where Supabase Storage calls occur (TS-03 compliant). Test naming follows `[function] [does X] when [condition]` convention throughout.

### Coverage Gaps

1. **`get_all_confirmed_pickups` not directly unit tested.** The modal list is exercised by the dashboard route test but not directly asserted. Low risk — non-blocking.

2. **`get_followup_suppliers` threshold logic not directly unit tested.** Exercised via dashboard route. Non-blocking.

3. **Dead code: `mark_invoice_sent`.** Superseded by `toggle_invoice_sent`. Still has tests but no route calls it. Non-blocking — remove in cleanup.

---

## Browser Workflow Verification

**Method:** Playwright MCP (partial) + manual verification at 768px iPad viewport.

**Playwright confirmed:**
- Unauthenticated root `/` redirects to `/login` ✓
- Wrong password shows "Incorrect password", no redirect ✓
- Correct password redirects to `/` ✓

**Migration fix applied during QA:** `pickups` table was missing from live Supabase DB (migration 0007 had not been run). Applied via `alembic stamp 0006` + `alembic upgrade 0007`. Dashboard 500 error resolved.

**Manual verification (builder-confirmed at 768px):** All 9 flows passed.

### Flow Results

| Flow | Result |
|------|--------|
| Flow 1 — Login / Logout | PASS |
| Flow 2 — Dashboard (stat cards, pickup modal, revenue chart) | PASS |
| Flow 3 — Supplier CRUD + Confirm Pickup + action stage filter + active toggle | PASS |
| Flow 4 — Pickup management (modal + supplier detail count) | PASS |
| Flow 5 — Gradeout + PDF upload + pickup auto-linking | PASS |
| Flow 6 — Invoices (generate, preview, overwrite, send, delete, toggle sent) | PASS |
| Flow 7 — Leads (create, status change, convert to supplier) | PASS |
| Flow 8 — Growth Planning (target, sliders, edge cases) | PASS |
| Flow 9 — Edge cases (empty forms, 404, unauthenticated access) | PASS |

---

## Findings

### [RESOLVED] Missing pickup tests (TS-04 violation)
Previously blocking. Resolved — `test_pickups.py` exists with 11 tests, all passing.

### [RESOLVED] Missing migration 0007 on live DB
Found during QA browser verification. Dashboard returned 500 (`relation "pickups" does not exist`). Fixed by stamping alembic_version at 0006 and running `alembic upgrade 0007`.

### [NON-BLOCKING] Duplicate Alembic revision ID `0002`
`0002_gradeouts_remove_pickup_pdf.py` and `0002_add_app_settings.py` both declare `revision = "0002"`. This causes a `UserWarning` on every Alembic command and prevents `alembic upgrade head` from working — specific revision IDs must be used instead. Does not affect runtime but will cause friction on future migrations.

**What must be done:** Rename one migration file's revision ID (recommend renaming `0002_add_app_settings.py` to `revision = "000a"` and `down_revision = "0001"`) and re-stamp. Post-release cleanup — not a blocker.

### [NON-BLOCKING] `get_followup_suppliers` threshold not directly unit tested
Exercised via browser (Follow-Up panel correct). Adding direct unit test recommended post-release.

### [NON-BLOCKING] Dead code: `mark_invoice_sent`
Route no longer calls it. Remove in cleanup.

---

## Summary

**Blocking issues:** 0
**Non-blocking issues:** 3

**Verdict:**
APPROVED — all blocking issues resolved. Product is shippable. Complete the 3 non-blocking cleanup items post-release.
