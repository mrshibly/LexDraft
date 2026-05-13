"""
Sends original and edited drafts to LLM for semantic diff analysis.
Returns structured DiffAnalysis with reusable learned rules.
"""
from __future__ import annotations

import json
import logging
import re

from feedback.models import DiffAnalysis, EditSession, LearnedRule
from feedback.preference_store import PreferenceStore

logger = logging.getLogger(__name__)

DIFF_PROMPT = """You are analysing the difference between an AI-generated legal draft (ORIGINAL) \
and a human-edited version (EDITED).

Your job is to extract reusable preferences that explain WHY the editor made these changes.
Do NOT describe what changed — extract the underlying rule or preference.

Return ONLY a JSON object with this exact schema:
{{
  "structural_changes": [
    "description of a structural preference, e.g. 'Move timeline before parties section'"
  ],
  "tone_changes": [
    "description of a tone preference, e.g. 'Use formal third-person throughout'"
  ],
  "content_additions": [
    "description of content that was added, e.g. 'Always include governing law in matter overview'"
  ],
  "content_removals": [
    "description of content that was removed, e.g. 'Remove boilerplate disclaimer paragraph'"
  ],
  "formatting_changes": [
    "description of formatting preference, e.g. 'Use numbered lists for obligations, not bullet points'"
  ],
  "learned_rules": [
    "Actionable, generalised rule extracted from the edit, written as an instruction to the AI"
  ]
}}

ORIGINAL DRAFT:
{original_draft}

EDITED DRAFT:
{edited_draft}

Return only the JSON object. No preamble, no markdown fences."""


def analyze_edit(session: EditSession) -> DiffAnalysis:
    """Send both drafts to LLM for semantic diff analysis.
    
    Extracts intent-level changes, not naive line diffs.
    Returns a structured DiffAnalysis.
    """
    from openai import OpenAI
    from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, LLM_MODEL, LLM_TEMPERATURE

    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
    )

    prompt = DIFF_PROMPT.format(
        original_draft=session.original_draft,
        edited_draft=session.edited_draft
    )

    try:
        logger.info("Analysing edit with LLM...")
        response = client.chat.completions.create(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": "You are a precise legal document analyst. Return ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            extra_headers={
                "HTTP-Referer": "https://lexdraft.local",
                "X-Title": "LexDraft"
            }
        )

        raw_text = response.choices[0].message.content.strip()

        # Strip markdown fences
        raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
        raw_text = re.sub(r'\s*```$', '', raw_text)

        parsed = json.loads(raw_text)

    except json.JSONDecodeError:
        logger.warning("LLM returned malformed JSON in diff analysis")
        # Try regex extraction
        match = re.search(r'\{[\s\S]*\}', raw_text)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                logger.error("Could not parse diff analysis response")
                parsed = {}
        else:
            parsed = {}

    except Exception as e:
        logger.error(f"Diff analysis LLM call failed: {e}")
        parsed = {}

    # Build DiffAnalysis with validation
    analysis = DiffAnalysis(
        structural_changes=parsed.get("structural_changes", []),
        tone_changes=parsed.get("tone_changes", []),
        content_additions=parsed.get("content_additions", []),
        content_removals=parsed.get("content_removals", []),
        formatting_changes=parsed.get("formatting_changes", []),
        learned_rules=parsed.get("learned_rules", [])
    )

    logger.info(f"Diff analysis extracted {len(analysis.learned_rules)} learned rules")

    return analysis


def process_edit(
    session: EditSession,
    preference_store: PreferenceStore
) -> tuple[DiffAnalysis, list[LearnedRule]]:
    """Run diff analysis and store learned rules in preference store.
    
    Returns (DiffAnalysis, list of added/updated LearnedRules).
    """
    # 1. Run diff analysis
    diff_analysis = analyze_edit(session)

    # 2. Store each learned rule
    added_rules = []

    # Map rules to categories based on which list they came from
    category_map = {
        "structural_changes": "structural",
        "tone_changes": "tone",
        "content_additions": "content",
        "content_removals": "content",
        "formatting_changes": "formatting",
    }

    # Process categorised rules
    for field_name, category in category_map.items():
        rules = getattr(diff_analysis, field_name, [])
        for rule_text in rules:
            if rule_text and rule_text.strip():
                learned = preference_store.add_rule(
                    rule_text.strip(), category, session.draft_type
                )
                added_rules.append(learned)

    # Process generic learned_rules
    for rule_text in diff_analysis.learned_rules:
        if rule_text and rule_text.strip():
            learned = preference_store.add_rule(
                rule_text.strip(), "general", session.draft_type
            )
            added_rules.append(learned)

    logger.info(
        f"Processed edit session {session.session_id}: "
        f"{len(added_rules)} rules added/updated"
    )

    return diff_analysis, added_rules
