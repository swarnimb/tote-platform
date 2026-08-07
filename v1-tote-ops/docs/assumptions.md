# Assumptions: Tote-Ops

> Per-project file. Produced by `@assumptions` command.
> Loaded by `@session-start` alongside `architecture.md` and `constraints.md`.
> This file is complete when every critical assumption is either validated or explicitly accepted as a known risk with a contingency.

---

## Status

**Overall:** [x] Complete — all assumptions resolved or accepted

**Last updated:** 2026-03-15

---

## Assumptions Log

---

### [ASSUMPTION-01] Supabase Storage available on free tier

**Category:** Service capability

**Assumption:** Supabase free tier includes file storage for gradeout PDFs.

**Why it's critical:** Render's filesystem is ephemeral — PDFs must be stored in Supabase Storage or they are lost on redeploy.

**Resolution approach:** Research

**Resolution detail:** Confirmed via Supabase pricing documentation. Free tier includes 1GB Storage. At the expected volume (handful of PDFs per month), this limit will not be reached.

**Outcome:** Supabase Storage is available and sufficient on the free tier.

**Status:** [x] Resolved

---

### [ASSUMPTION-02] mailto: links open Outlook on iPad

**Category:** Service capability

**Assumption:** Tapping a mailto: link on the iPad opens Outlook pre-filled with the correct recipient, subject, and body.

**Why it's critical:** All email flows (follow-up emails, invoice sending) depend on mailto: links. If Outlook is not the default mail app, a different client opens.

**Resolution approach:** Accepted risk

**Resolution detail:** mailto: behavior is controlled by the iPad's default mail app setting, not the application. If Outlook is not set as default, the iPad's default mail client opens instead — the link still works and the email is still pre-filled, just not in Outlook specifically. To fix: Settings → Default Apps → Mail → set to Outlook.

**Outcome:** Accepted. Contingency: set Outlook as default mail app in iPad Settings. Risk is trivial — any mail client opening pre-filled is still functional.

**Status:** [x] Accepted risk

---

### [ASSUMPTION-03] Gradeout PDFs are text-extractable

**Category:** Technical feasibility

**Assumption:** Gradeout PDFs contain machine-readable text that pdfplumber can extract.

**Why it's critical:** The entire PDF extraction feature depended on pdfplumber reading text from the PDF. If PDFs are scanned images, pdfplumber returns nothing.

**Resolution approach:** Spike (answered by builder)

**Resolution detail:** Builder confirmed gradeout PDFs are hand-written and scanned to PDF. pdfplumber cannot extract text from scanned images. Tesseract OCR is not reliable for handwriting. AI Vision (Claude API) would work but introduces cost.

**Outcome:** Assumption is FALSE. Auto-extraction is not feasible in V1 within the $0 constraint.

**Scope impact:** PDF auto-extraction removed from V1. Replaced with: manual entry form + PDF upload for record-keeping. PDFs stored in Supabase Storage alongside the gradeout record. User fills in the gradeout form manually.

@pdf-extractor skill moved to Inactive for V1. May be revisited in V2 with Claude Vision API.

**Status:** [x] Resolved — scope updated

---

### [ASSUMPTION-04] Gradeout PDF field layout is consistent

**Category:** Technical feasibility

**Assumption:** All gradeout PDFs follow the same template, enabling reliable pattern-based extraction.

**Why it's critical:** Extraction patterns must be written against the real PDF template to work correctly.

**Resolution approach:** N/A — moot. Assumption-03 resolved this category. Manual entry removes dependency on PDF structure entirely.

**Outcome:** No longer applicable. Manual entry has no dependency on PDF field layout.

**Status:** [x] Resolved — moot due to ASSUMPTION-03 outcome

---

## Summary

| # | Assumption | Category | Approach | Status |
|---|---|---|---|---|
| 01 | Supabase Storage on free tier | Service capability | Research | Resolved |
| 02 | mailto: opens Outlook on iPad | Service capability | Accepted risk | Accepted |
| 03 | Gradeout PDFs are text-extractable | Technical feasibility | Spike (builder confirmed) | Resolved — scope updated |
| 04 | Gradeout PDF field layout consistent | Technical feasibility | N/A | Resolved — moot |

**Open count:** 0 — `@plan` can proceed.

---

## Spike Notes

| Spike | Question answered | Result |
|---|---|---|
| PDF text check | Are gradeout PDFs text-based or scanned images? | Scanned handwritten images — pdfplumber cannot extract. Auto-extraction removed from V1. |
