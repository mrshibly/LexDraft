"""
Assembles the complete prompt for draft generation.
Combines: system prompt + evidence + structured fields + learned preferences + task.
"""
from __future__ import annotations

import logging

from retrieval.models import RetrievalResult
from ingestion.models import StructuredDocumentRecord

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are LexDraft, an internal legal drafting assistant for Pearson Specter Litt.

Your job is to generate a Case Fact Summary grounded entirely in the provided evidence passages.

STRICT RULES:
1. Every factual claim MUST be followed by a citation like [1], [2], or [1,3] referencing the evidence passage(s) below.
2. If a required field cannot be supported by any evidence passage, write exactly: "⚠ NOT SUPPORTED IN DOCUMENTS"
3. Do not invent, infer, or extrapolate beyond the evidence.
4. Structure your output exactly as specified in the TASK section.
5. Flag any internal contradictions you detect across evidence passages."""


def format_evidence_block(retrieval_result: RetrievalResult) -> str:
    """Format retrieved chunks into the evidence block for the prompt.
    
    Includes citation label, source file, page number, confidence, and chunk text.
    Truncates individual chunk text at 400 chars if needed.
    """
    lines = ["EVIDENCE PASSAGES:", "──────────────────"]

    for chunk in retrieval_result.ranked_chunks:
        label = chunk.citation_label
        source = chunk.metadata.source_file
        page = chunk.metadata.page_number

        # Format confidence
        conf_str = ""
        if chunk.metadata.is_low_confidence:
            conf_str = " | Confidence: LOW ⚠"

        # Truncate text if needed
        text = chunk.text
        if len(text) > 400:
            text = text[:397] + "..."

        lines.append(
            f'{label} Source: {source} | Page {page}{conf_str}\n'
            f'"{text}"'
        )
        lines.append("")

    return "\n".join(lines)


def format_structured_fields(record: StructuredDocumentRecord) -> str:
    """Format extracted structured fields into the prompt block.
    
    Skips fields that are None or empty lists.
    """
    lines = ["EXTRACTED STRUCTURED FIELDS:", "─────────────────────────────"]

    if record.document_type:
        lines.append(f"Document Type: {record.document_type}")

    if record.parties:
        party_str = " | ".join(f"{p.name} ({p.role})" for p in record.parties)
        lines.append(f"Parties: {party_str}")

    if record.filing_date:
        lines.append(f"Filing Date: {record.filing_date}")

    if record.effective_date:
        lines.append(f"Effective Date: {record.effective_date}")

    if record.case_number:
        lines.append(f"Matter Number: {record.case_number}")

    if record.governing_law:
        lines.append(f"Governing Law: {record.governing_law}")

    if record.key_obligations:
        lines.append(f"Key Obligations: {'; '.join(record.key_obligations)}")

    if record.termination_clauses:
        lines.append(f"Termination Clauses: {'; '.join(record.termination_clauses)}")

    if record.signature_parties:
        lines.append(f"Signature Parties: {', '.join(record.signature_parties)}")

    return "\n".join(lines)


def build_prompt(
    retrieval_result: RetrievalResult,
    structured_record: StructuredDocumentRecord,
    draft_type_module,
    learned_preferences: list[str]
) -> tuple[str, str]:
    """Assemble the complete prompt for draft generation.
    
    Returns (system_prompt, user_message).
    """
    # Evidence block
    evidence_block = format_evidence_block(retrieval_result)

    # Structured fields block
    fields_block = format_structured_fields(structured_record)

    # Preferences block (only if rules exist)
    prefs_block = ""
    if learned_preferences:
        prefs_lines = ["OPERATOR PREFERENCES FROM PRIOR EDITS:", "─" * 43]
        for pref in learned_preferences:
            prefs_lines.append(f"• {pref}")
        prefs_block = "\n".join(prefs_lines)

    # Task instruction
    task = draft_type_module.TASK_INSTRUCTION

    # Assemble user message
    parts = [evidence_block, "", fields_block]
    if prefs_block:
        parts.extend(["", prefs_block])
    parts.extend(["", task])

    user_message = "\n".join(parts)

    logger.info(
        f"Built prompt: {len(SYSTEM_PROMPT)} chars system, "
        f"{len(user_message)} chars user, "
        f"{len(learned_preferences)} preferences applied"
    )

    return SYSTEM_PROMPT, user_message
