"""
Validates and stores operator edit sessions.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from feedback.models import EditSession
from feedback.preference_store import PreferenceStore

logger = logging.getLogger(__name__)


def capture_edit(
    doc_id: str,
    draft_type: str,
    original_draft: str,
    edited_draft: str,
    operator_note: str | None,
    preference_store: PreferenceStore
) -> EditSession:
    """Validate and store an operator edit session.
    
    Args:
        doc_id: Document the draft was generated for.
        draft_type: Type of draft (e.g. 'case_fact_summary').
        original_draft: The AI-generated draft text.
        edited_draft: The operator-edited draft text.
        operator_note: Optional free-text comment from operator.
        preference_store: PreferenceStore to persist the session.
    
    Returns:
        The created EditSession.
    
    Raises:
        ValueError: If drafts are empty or identical.
    """
    # Validate inputs
    if not original_draft or not original_draft.strip():
        raise ValueError("Original draft is empty")
    if not edited_draft or not edited_draft.strip():
        raise ValueError("Edited draft is empty")
    if original_draft.strip() == edited_draft.strip():
        raise ValueError("Edited draft is identical to original — no edit detected")

    # Build session
    session = EditSession(
        session_id=uuid.uuid4().hex,
        doc_id=doc_id,
        draft_type=draft_type,
        original_draft=original_draft,
        edited_draft=edited_draft,
        operator_note=operator_note,
        timestamp=datetime.now(timezone.utc).isoformat()
    )

    # Persist
    preference_store.save_edit_session(session)

    logger.info(f"Captured edit session {session.session_id} for doc {doc_id}")

    return session
