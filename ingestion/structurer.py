"""
Extracts structured legal fields from raw document text.
Uses regex for fast extraction + LLM (via OpenRouter) for anything missed.
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone

from ingestion.models import RawFilePayload, StructuredDocumentRecord, Party

logger = logging.getLogger(__name__)

# Regex patterns for fast extraction of common legal fields
PATTERNS = {
    "dates": r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+ \d{1,2},? \d{4})\b',
    "case_numbers": r'\b(?:Case|Matter|Docket|File)\s*(?:No\.?|Number|#)\s*:?\s*([\w\d\-\/]+)',
    "party_vs": r'([A-Z][A-Za-z\s,\.]+)\s+v\.?\s+([A-Z][A-Za-z\s,\.]+)',
    "money_amounts": r'\$[\d,]+(?:\.\d{2})?',
    "section_headers": r'^(?:WHEREAS|NOW THEREFORE|ARTICLE|SECTION|CLAUSE)\s+[\dIVX]+',
}

# LLM extraction prompt
LLM_EXTRACT_PROMPT = """Extract the following fields from the legal document text below.
Return ONLY a JSON object with these exact keys. If a field cannot be found, use null.

Fields to extract:
- document_type: one of [contract, notice, affidavit, motion, memo, filing, agreement, other]
- parties: list of {{"name": "...", "role": "..."}} where role is one of [plaintiff, defendant, petitioner, respondent, counsel, witness, notary, other]
- effective_date: ISO 8601 date string or null
- filing_date: ISO 8601 date string or null
- case_number: case/matter number string or null
- governing_law: jurisdiction string or null
- key_obligations: list of strings (max 5)
- termination_clauses: list of strings (max 3)
- signature_parties: list of names who signed

Regex pre-extraction found these potential values: {regex_hints}
Confirm or correct them.

Document text:
{text}
"""


def regex_extract(text: str) -> dict:
    """Apply regex patterns for fast extraction of common legal patterns.
    
    Returns raw match strings without over-parsing.
    """
    results = {
        "dates": [],
        "case_numbers": [],
        "party_strings": [],
        "money_amounts": [],
        "section_headers": [],
    }

    for match in re.finditer(PATTERNS["dates"], text):
        results["dates"].append(match.group(0))

    for match in re.finditer(PATTERNS["case_numbers"], text, re.IGNORECASE):
        results["case_numbers"].append(match.group(1))

    for match in re.finditer(PATTERNS["party_vs"], text):
        results["party_strings"].append(f"{match.group(1).strip()} v. {match.group(2).strip()}")

    for match in re.finditer(PATTERNS["money_amounts"], text):
        results["money_amounts"].append(match.group(0))

    for match in re.finditer(PATTERNS["section_headers"], text, re.MULTILINE):
        results["section_headers"].append(match.group(0))

    logger.info(
        f"Regex found: {len(results['dates'])} dates, "
        f"{len(results['case_numbers'])} case numbers, "
        f"{len(results['party_strings'])} party strings, "
        f"{len(results['money_amounts'])} amounts"
    )

    return results


def llm_extract(text: str, regex_hints: dict) -> dict:
    """Use LLM (via OpenRouter) to extract structured fields from document text.
    
    Sends first 3000 chars of text plus regex hints to the LLM.
    """
    from openai import OpenAI
    from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, LLM_MODEL, LLM_TEMPERATURE

    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
    )

    prompt = LLM_EXTRACT_PROMPT.format(
        regex_hints=json.dumps(regex_hints, indent=2),
        text=text[:3000]
    )

    try:
        logger.info("Calling LLM for structured field extraction...")
        response = client.chat.completions.create(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=1000,
            messages=[
                {"role": "system", "content": "You are a precise legal document analyser. Return ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            extra_headers={
                "HTTP-Referer": "https://lexdraft.local",
                "X-Title": "LexDraft"
            }
        )

        raw_text = response.choices[0].message.content.strip()

        # Strip markdown fences before parsing
        raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
        raw_text = re.sub(r'\s*```$', '', raw_text)

        parsed = json.loads(raw_text)
        logger.info(f"LLM extracted {len(parsed)} fields")
        return parsed

    except json.JSONDecodeError as e:
        logger.warning(f"LLM returned malformed JSON: {e}")
        # Try to extract JSON with regex
        match = re.search(r'\{[\s\S]*\}', raw_text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        logger.error("Could not parse LLM response — using regex-only results")
        return {}

    except Exception as e:
        logger.warning(f"LLM extraction failed: {e} — using regex-only results")
        return {}


def structure_document(raw: RawFilePayload, doc_id: str) -> StructuredDocumentRecord:
    """Extract structured fields from a raw file payload using regex + LLM.
    
    Two-pass approach: regex for speed, LLM for completeness.
    LLM values take priority; regex used as fallback.
    """
    # Pass 1: Regex extraction
    regex_hints = regex_extract(raw.raw_text)

    # Pass 2: LLM extraction
    llm_result = llm_extract(raw.raw_text, regex_hints)

    # Build parties list
    parties = []
    raw_parties = llm_result.get("parties") or []
    for p in raw_parties:
        if isinstance(p, dict) and p.get("name"):
            parties.append(Party(
                name=p["name"],
                role=p.get("role", "other")
            ))

    # Low-confidence pages
    low_conf_pages = [p.page_number for p in raw.pages if p.is_low_confidence]

    record = StructuredDocumentRecord(
        doc_id=doc_id,
        source_file=raw.file_name,
        document_type=llm_result.get("document_type") or "other",
        parties=parties,
        effective_date=llm_result.get("effective_date"),
        filing_date=llm_result.get("filing_date") or (regex_hints["dates"][0] if regex_hints["dates"] else None),
        case_number=llm_result.get("case_number") or (regex_hints["case_numbers"][0] if regex_hints["case_numbers"] else None),
        governing_law=llm_result.get("governing_law"),
        key_obligations=llm_result.get("key_obligations") or [],
        termination_clauses=llm_result.get("termination_clauses") or [],
        signature_parties=llm_result.get("signature_parties") or [],
        raw_text=raw.raw_text,
        page_count=raw.page_count,
        avg_ocr_confidence=raw.avg_confidence,
        low_confidence_pages=low_conf_pages,
        indexed_at=datetime.now(timezone.utc).isoformat()
    )

    logger.info(
        f"Structured document {doc_id}: type={record.document_type}, "
        f"parties={len(record.parties)}, obligations={len(record.key_obligations)}"
    )

    return record
