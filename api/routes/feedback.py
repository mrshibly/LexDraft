"""
POST /api/v1/feedback — Feedback submission endpoint.
Captures operator edits and extracts learned rules.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class FeedbackRequest(BaseModel):
    """Request body for feedback submission."""
    doc_id: str
    draft_type: str
    original_draft: str
    edited_draft: str
    operator_note: str | None = None


@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Submit an operator edit for analysis and rule extraction.
    
    Captures the edit session, runs semantic diff analysis,
    and stores learned rules in the preference store.
    """
    from api.dependencies import get_preference_store
    from feedback.capture import capture_edit
    from feedback.diff_analyzer import process_edit

    pref_store = get_preference_store()

    # 1. Capture the edit session
    try:
        session = capture_edit(
            doc_id=req.doc_id,
            draft_type=req.draft_type,
            original_draft=req.original_draft,
            edited_draft=req.edited_draft,
            operator_note=req.operator_note,
            preference_store=pref_store
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail={
            "error_code": "INVALID_EDIT",
            "message": str(e)
        })

    # 2. Analyse diff and extract rules
    try:
        diff_analysis, added_rules = process_edit(session, pref_store)
    except Exception as e:
        logger.error(f"Diff analysis failed: {e}", exc_info=True)
        # Still return the session even if analysis fails
        return {
            "session_id": session.session_id,
            "rules_extracted": 0,
            "rules_detail": [],
            "total_active_rules": pref_store.rule_count(req.draft_type),
            "analysis_error": str(e)
        }

    # 3. Build response
    rules_detail = [
        {
            "rule": r.rule,
            "category": r.category,
            "is_new": r.frequency == 1
        }
        for r in added_rules
    ]

    response = {
        "session_id": session.session_id,
        "rules_extracted": len(added_rules),
        "rules_detail": rules_detail,
        "total_active_rules": pref_store.rule_count(req.draft_type)
    }

    logger.info(
        f"Feedback processed: session={session.session_id}, "
        f"rules={len(added_rules)}, total={response['total_active_rules']}"
    )

    return response
