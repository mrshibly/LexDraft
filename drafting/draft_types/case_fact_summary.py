"""
Draft type definition for Case Fact Summary.
Provides: task query, system instruction, output structure template.
"""
from __future__ import annotations

DRAFT_TYPE_ID = "case_fact_summary"

RETRIEVAL_QUERY = (
    "parties names roles dates timeline events core dispute "
    "obligations clauses termination signatures governing law"
)

TASK_INSTRUCTION = """
TASK: Generate a Case Fact Summary with the following sections:

## 1. MATTER OVERVIEW
One paragraph. Include: parties, matter number, document type, and filing date. Cite every fact.

## 2. KEY PARTIES
Markdown table with columns: Name | Role | Notes. Cite each row.

## 3. TIMELINE OF KEY EVENTS
Chronological bullet list. Each item: `[DATE] — [EVENT] [citation]`
If date is unknown, write `[DATE UNKNOWN] — [EVENT]`.

## 4. CORE DISPUTE / SUBJECT MATTER
2–3 sentences describing the nature of this matter. Cite every claim.

## 5. RELEVANT CLAUSES & OBLIGATIONS
Numbered list of specific clauses or obligations found in the document. Cite each.

## 6. FLAGGED GAPS & AMBIGUITIES
Bullet list of:
- Missing required fields (e.g. no signature date found)
- Low-confidence OCR pages that may have extraction errors
- Internal contradictions detected between evidence passages
- Fields that are ⚠ NOT SUPPORTED IN DOCUMENTS

This section requires NO citations. It is your gap analysis layer.

Begin the Case Fact Summary now. Output only the summary, no preamble.
"""
