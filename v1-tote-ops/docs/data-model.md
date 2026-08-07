# Data Model: Tote-Ops

**Version:** 1.0
**Date:** 2026-03-15

---

## Entity Relationship Summary

```
suppliers ──< gradeouts
              invoices (standalone — computed from gradeouts)
leads (standalone)
```

- `suppliers` → `gradeouts`: one-to-many
- `invoices`: standalone, no FK — computed from gradeouts at generation time
- `leads`: standalone, no FK

```
suppliers ──< pickups
suppliers ──< gradeouts
pickups ──── gradeout (one-to-one, optional)
invoices (standalone — computed from gradeouts)
leads (standalone)
```

- `suppliers` → `pickups`: one-to-many (a supplier can have many confirmed pickups)
- `suppliers` → `gradeouts`: one-to-many
- `pickups` → `gradeouts`: one-to-one optional FK (`gradeouts.pickup_id`)
- `invoices`: standalone, no FK
- `leads`: standalone, no FK

> **Note:** `pickups` table was dropped in migration 0004 then recreated in migration 0007. Setting `last_action_stage = 'pickup_confirmed'` on a supplier now triggers a confirmation modal which creates a `pickups` row (`status = 'confirmed'`). The Pickups Confirmed scorecard on the dashboard counts rows in this table.

---

## pickups

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | UUID | PK, default uuid4 | |
| supplier_id | VARCHAR(36) | FK → suppliers.id, NOT NULL | |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'confirmed' | 'confirmed' or 'cancelled' |
| created_at | TIMESTAMP | DEFAULT now() | Date pickup was confirmed |

---

## suppliers

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | UUID | PK, default uuid4 | |
| company_name | VARCHAR(255) | NOT NULL | |
| location | VARCHAR(255) | NOT NULL | |
| contact_name | VARCHAR(255) | | |
| phone | VARCHAR(50) | | |
| email | VARCHAR(255) | | |
| bol_email | VARCHAR(255) | | BOL contact email |
| bol_same_as_primary | BOOLEAN | DEFAULT false | If true, bol_email = email |
| industry | VARCHAR(255) | | |
| tote_types | VARCHAR(20) | | '275', '330', or 'both' |
| average_quantity_275 | INTEGER | | |
| average_quantity_330 | INTEGER | | |
| last_contacted_date | DATE | | Manually updated by user |
| working_hours | VARCHAR(255) | | |
| is_hazmat | BOOLEAN | DEFAULT false | |
| followup_weeks | INTEGER | NOT NULL, DEFAULT 4 | Per-supplier follow-up threshold (1–10 weeks) |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | Inactive suppliers excluded from follow-up lists |
| warnings | TEXT | | |
| notes | TEXT | | |
| is_deleted | BOOLEAN | DEFAULT false | Soft delete flag |
| deleted_at | TIMESTAMP | | Set on soft delete |
| created_at | TIMESTAMP | DEFAULT now() | |
| updated_at | TIMESTAMP | DEFAULT now(), onupdate now() | |

**Indexes:** `is_deleted`

---

## gradeouts

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | String(36) | PK, default uuid4 | |
| supplier_id | String(36) | FK → suppliers.id, NOT NULL | |
| date_received | DATE | NOT NULL | Actual date totes were picked up |
| totes_275_good_washable | INTEGER | DEFAULT 0 | |
| totes_275_good_cage | INTEGER | DEFAULT 0 | |
| totes_275_total_usable | INTEGER | DEFAULT 0 | good_washable + good_cage |
| totes_330_good_washable | INTEGER | DEFAULT 0 | |
| totes_330_good_cage | INTEGER | DEFAULT 0 | |
| totes_330_total_usable | INTEGER | DEFAULT 0 | good_washable + good_cage |
| junk | INTEGER | DEFAULT 0 | Combined junk count (275 + 330) |
| notes | TEXT | | |
| created_at | TIMESTAMP | DEFAULT now() | |

**Indexes:** `supplier_id`, `date_received`

**Computed (not stored):**
- `total_usable_totes` = `totes_275_total_usable + totes_330_total_usable`
- `revenue` = `total_usable_totes * TOTE_RATE` (TOTE_RATE = 5)

---

## invoices

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | UUID | PK, default uuid4 | |
| month | DATE | UNIQUE, NOT NULL | First day of month (e.g., 2026-03-01) |
| gradeout_count | INTEGER | NOT NULL | Number of gradeouts in that month |
| total_usable_275 | INTEGER | NOT NULL | Sum of totes_275_total_usable |
| total_usable_330 | INTEGER | NOT NULL | Sum of totes_330_total_usable |
| total_revenue | NUMERIC(10,2) | NOT NULL | total_usable * TOTE_RATE |
| generated_at | TIMESTAMP | DEFAULT now() | |
| sent_at | TIMESTAMP | | Set when user clicks "Send Invoice" |

**Indexes:** `month`

**Constraints:**
- `UNIQUE(month)` — one invoice per calendar month

**Note:** Invoice rows (individual gradeout breakdown) are not stored — they are re-queried from `gradeouts` table at view time using `gradeouts.date_received` month match.

---

## leads

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | UUID | PK, default uuid4 | |
| company_name | VARCHAR(255) | NOT NULL | |
| location | VARCHAR(255) | | |
| industry | VARCHAR(255) | | |
| contact_name | VARCHAR(255) | | |
| contact_phone | VARCHAR(50) | | |
| contact_email | VARCHAR(255) | | |
| outreach_status | ENUM | DEFAULT 'research' | research / contacted / responded / not_interested / active_supplier |
| last_contact_date | DATE | | |
| potential_volume | VARCHAR(255) | | e.g., "20-30 totes/month" |
| notes | TEXT | | |
| created_at | TIMESTAMP | DEFAULT now() | |
| updated_at | TIMESTAMP | DEFAULT now(), onupdate now() | |

**Indexes:** `outreach_status`

---

## Config Constants

| Constant | Value | Purpose |
|---|---|---|
| `TOTE_RATE` | 5 | USD per usable tote — used in all revenue calculations |
| `FOLLOWUP_WEEKS_DEFAULT` | 4 | Default follow-up threshold for new suppliers (per-supplier, overridable 1–10 weeks) |
| `SESSION_EXPIRY_DAYS` | 30 | Auth session lifetime |
| `PDF_SIGNED_URL_EXPIRY_SECONDS` | 3600 | Supabase Storage signed URL lifetime (1 hour) |
