"""
Retrieves active learned rules and formats them for prompt injection.
"""
from __future__ import annotations

import logging

from feedback.preference_store import PreferenceStore

logger = logging.getLogger(__name__)


def get_preferences_block(draft_type: str, preference_store: PreferenceStore) -> str:
    """Get the formatted preferences block for prompt injection.
    
    Rules with frequency >= 3 get a ★ marker (confirmed preferences).
    Rules with lower frequency get a • marker.
    
    Returns empty string if no rules exist.
    """
    rules = preference_store.get_active_rules(draft_type)
    if not rules:
        return ""

    lines = ["OPERATOR PREFERENCES FROM PRIOR EDITS:", "─" * 43]
    for rule in rules:
        marker = "★" if rule.frequency >= 3 else "•"
        lines.append(f"{marker} {rule.rule}")

    block = "\n".join(lines)
    logger.info(f"Injecting {len(rules)} preference rules into prompt")
    return block


def get_preference_rules_list(draft_type: str, preference_store: PreferenceStore) -> list[str]:
    """Get list of active preference rule strings for a draft type.
    
    Used by the generator to track which preferences were applied.
    """
    rules = preference_store.get_active_rules(draft_type)
    return [r.rule for r in rules]
