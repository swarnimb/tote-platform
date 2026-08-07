# Skill: @pdf-extractor

## Purpose
Implements and maintains the pdfplumber-based gradeout PDF extraction logic for Tote-Ops.
Extracts structured data from consistently-formatted gradeout PDFs and returns validated
field values for user confirmation before database save.

---

## Pre-conditions
1. Read `docs/architecture.md` for the Gradeout model field definitions
2. Confirm the PDF template structure with the builder before implementing
3. pdfplumber must be in requirements.txt

---

## What It Extracts

From each gradeout PDF:

| Field | Type | Notes |
|-------|------|-------|
| supplier_name | string | Company name |
| supplier_address | string | Full address |
| date_received | date | Transaction date |
| totes_275_good_washable | int | |
| totes_275_good_cage | int | |
| totes_275_total_usable | int | |
| totes_275_junk | int | |
| totes_330_good_washable | int | |
| totes_330_good_cage | int | |
| totes_330_total_usable | int | |
| totes_330_junk | int | |

---

## Process

### Extraction
1. Open PDF with pdfplumber
2. Extract all text from page(s)
3. Apply field-specific regex patterns to locate each value
4. Parse and type-cast each extracted value
5. Run validation checks (see below)
6. Return structured dict with extracted values + confidence flags

### Validation checks
- All numeric fields are non-negative integers
- total_usable ≤ (good_washable + good_cage) for each capacity
- date_received is a valid parseable date
- supplier_name is non-empty
- If any check fails: flag the field, do not block — return with `warnings` list

### Confirmation flow
- FastAPI route returns extracted data as JSON
- HTMX swaps in the confirmation form pre-populated with extracted values
- User reviews, corrects any flagged fields, confirms
- On confirm: validated data POSTed to save endpoint

---

## Error Handling
- If PDF cannot be opened: return `{"error": "Could not read PDF — file may be corrupted"}`
- If a field cannot be extracted: return `None` for that field with a warning flag
- Never save to database without user confirmation — extraction feeds a form, not a direct DB write
- Log all extraction attempts with filename, timestamp, and which fields failed

---

## Code Pattern

```python
import pdfplumber
import re
from typing import Optional

def extract_gradeout(file_path: str) -> dict:
    warnings = []
    result = {}

    try:
        with pdfplumber.open(file_path) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as e:
        return {"error": f"Could not read PDF: {str(e)}"}

    # Example field extraction — patterns must be confirmed against actual PDF template
    supplier_match = re.search(r"Company:\s*(.+)", text)
    result["supplier_name"] = supplier_match.group(1).strip() if supplier_match else None
    if not result["supplier_name"]:
        warnings.append("supplier_name could not be extracted")

    # ... repeat for each field with appropriate regex

    result["warnings"] = warnings
    return result
```

---

## When to Invoke
- Building the gradeout PDF upload endpoint
- Writing or updating extraction regex patterns
- Building the extraction confirmation UI flow
- Adding validation logic

## When Not to Invoke
- Saving the confirmed data to the database — that is @dev
- Building the upload form UI — that is @ui-tote-ops
