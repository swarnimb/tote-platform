# Kickoff Brief: Tote-Ops

**Date:** 2026-03-15

## One-Line Description
A personal operations dashboard for a solo IBC tote sourcing contractor to manage suppliers, pickups, gradeouts, invoices, and leads — replacing notes, Excel, and manual follow-up tracking.

## Problem
A solo contractor sourcing IBC totes (275 and 330 gallon) from companies that no longer need them is losing supplier relationships and revenue because follow-ups fall through the cracks. Supplier data lives in notes, invoice data in Excel, and pickup coordination happens via email and text with no central system. The most painful failure: forgetting to follow up with suppliers who haven't had a pickup in 60+ days.

## Target User
One person. The builder. A non-technical solo contractor who works primarily from an iPad. Manages a supplier network, coordinates pickups with a dispatch team, receives gradeout PDFs via Outlook, and sends monthly invoices to one fixed client email. Gets paid $5 per usable tote.

## Core Scope

### In (MVP)
- **Suppliers** — full CRUD with all fields (name, location, contact, phone, email, BOL email, industry, tote types, average quantity, working hours, hazmat, warnings, notes)
- **Pickups** — log and track status (requested, scheduled, completed, cancelled), linked to supplier and gradeout
- **Gradeouts** — manual PDF upload, rule-based auto-extraction, confirm and save to database. Fields: supplier name, address, date received, 275 totes (good washable, good cage, total usable, junk), 330 totes (good washable, good cage, total usable, junk)
- **Monthly Invoice Generation** — auto-aggregate all gradeouts for a selected month, preview (one row per gradeout, total revenue footer), send via mailto: to configurable recipient email
- **Leads** — track potential suppliers with outreach status (research, contacted, responded, not interested, active supplier)
- **Dashboard** — revenue this month, total totes this month, upcoming pickups, needs follow-up list, active supplier count
- **Follow-up Logic** — suppliers with no pickup in 60+ days flagged as "Needs Follow-Up", tap to open mailto: pre-filled follow-up email template
- **Invoice Emailing** — from Invoices tab, review generated invoice then send via mailto: (opens Outlook on iPad)
- **Simple Auth** — single password stored in env variable, not hardcoded
- **Configurable Recipient Email** — invoice recipient email stored in config/env, not hardcoded (can be updated without touching code)

### Explicitly Out (V2 Backlog)
- Email account monitoring for auto-detecting incoming gradeout PDFs
- Automated email sending via SMTP (all email in V1 is via mailto:)
- Invoice PDF export or Excel export
- Multi-user support or full auth system
- Reporting, charts, or analytics
- Push notifications
- Error logging for PDF format changes
- Hosting upgrade to remove cold starts
- Excel/CSV bulk data import

## Risks and Assumptions
- **PDF format consistency** — extraction assumes gradeout PDFs are always the same template. If the format changes, extraction will break silently. Mitigation: add error logging and validation in V2.
- **Render cold starts** — free tier spins down after 15 min inactivity, ~30s wake-up delay. Accepted trade-off for V1. Revisit hosting in V2.
- **mailto: behavior** — assumes Outlook is set as the default mail app on the iPad. If not, a different mail client will open. No code change needed — just a device setting.
- **Supabase free tier** — 500MB storage, 2GB bandwidth/month. Not a real risk for solo use.
- **Dummy data for development** — existing supplier and invoice data will be entered manually once the system is built. No import feature in V1.

## Platform Target
Web — responsive, **iPad primary**. Designed mobile-first, usable on laptop.

## Stack
| Layer | Tool |
|---|---|
| Backend | FastAPI (Python) |
| Database | Supabase (PostgreSQL) |
| Frontend | Jinja2 templates + Tailwind CSS (CDN) |
| Hosting | Render (free tier) |
| PDF Extraction | pdfplumber (rule-based) |
| Email | mailto: links (opens Outlook on iPad) |
| Auth | Single password via env variable |

Two accounts needed at deploy time: Supabase + Render. Both free.

## Constraints
- **Budget:** $0. No paid tools, APIs, or services.
- **Deadline:** None. Goal is to build and deploy in one session.
- **Users:** Single user only.
- **Data:** Start with dummy data. Existing data entered manually post-launch.
- **Email:** All email flows through Outlook on iPad via mailto: links. No SMTP in V1.

## ASCII Wireframe

```
[Dashboard — iPad Primary View]
+------------------------------------------+
|  Tote-Ops             [Nav Menu]          |
+------------------------------------------+
|  This Month                               |
|  Totes: 142    Revenue: $710              |
+------------------------------------------+
|  Needs Follow-Up (3)                      |
|  > ABC Chemical — 72 days                 |
|  > XYZ Plastics — 61 days  [Email]        |
+------------------------------------------+
|  Upcoming Pickups (2)                     |
|  > Mar 18 — Acme Corp — 20 totes          |
+------------------------------------------+

[Nav: Dashboard | Suppliers | Pickups | Gradeouts | Invoices | Leads]

---

[Gradeouts Tab]
+------------------------------------------+
|  Gradeouts              [Upload PDF]      |
+------------------------------------------+
|  Upload → Extract → Confirm → Save        |
|                                           |
|  Confirm Extraction:                      |
|  Supplier: ABC Chemical                   |
|  Date: 2026-03-12                         |
|  275 — Usable: 8  Junk: 2                 |
|  330 — Usable: 4  Junk: 1                 |
|  [Save]  [Cancel]                         |
+------------------------------------------+

---

[Invoices Tab]
+------------------------------------------+
|  Invoices                                 |
|  [Generate Invoice — Select Month ▼]      |
+------------------------------------------+
|  Invoice Preview: March 2026              |
|  Supplier       | Totes | Revenue         |
|  ABC Chemical   |  12   | $60             |
|  XYZ Plastics   |   8   | $40             |
|  Acme Corp      |  20   | $100            |
|  --------------------------------         |
|  Total          |  40   | $200            |
+------------------------------------------+
|  [Send Invoice via Email]                 |
+------------------------------------------+
```

## Open Questions
- What fields does the gradeout PDF contain exactly beyond what was described? (Confirm before building the PDF extractor.)
- Should completed pickups automatically prompt the user to upload a gradeout PDF?
- Should the system store a record of sent invoices (date sent, month covered) for audit purposes?
