"""
POST /api/v1/draft — Draft generation endpoint.
Retrieves relevant chunks and generates a grounded legal draft.
"""
from __future__ import annotations

import importlib
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class DraftRequest(BaseModel):
    """Request body for draft generation."""
    doc_id: str
    draft_type: str = "case_fact_summary"
    top_k: int = 8


@router.post("/draft")
async def generate_draft_endpoint(req: DraftRequest):
    """Generate a grounded legal draft for an indexed document.
    
    Retrieves relevant chunks, applies learned preferences,
    and generates a draft with citations.
    """
    from api.dependencies import get_embedder, get_vector_store, get_preference_store
    from retrieval.retriever import retrieve
    from drafting.generator import generate_draft
    from feedback.prompt_updater import get_preference_rules_list

    embedder = get_embedder()
    vector_store = get_vector_store()
    pref_store = get_preference_store()

    # 1. Load structured record from SQLite
    record = pref_store.get_document_record(req.doc_id)
    if not record:
        raise HTTPException(status_code=404, detail={
            "error_code": "DOC_NOT_FOUND",
            "message": f"Document {req.doc_id} not found. Ingest it first."
        })

    # 2. Retrieve relevant chunks
    try:
        retrieval_result = retrieve(
            doc_id=req.doc_id,
            draft_type=req.draft_type,
            structured_record=record,
            vector_store=vector_store,
            embedder=embedder,
            top_k=req.top_k
        )
    except Exception as e:
        logger.error(f"Retrieval failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={
            "error_code": "RETRIEVAL_ERROR",
            "message": str(e)
        })

    # 3. Load preference rules
    preference_rules = get_preference_rules_list(req.draft_type, pref_store)

    # 4. Import draft type module
    try:
        draft_type_module = importlib.import_module(f"drafting.draft_types.{req.draft_type}")
    except ModuleNotFoundError:
        raise HTTPException(status_code=400, detail={
            "error_code": "INVALID_DRAFT_TYPE",
            "message": f"Draft type '{req.draft_type}' not found"
        })

    # 5. Generate draft
    try:
        result = generate_draft(
            retrieval_result=retrieval_result,
            structured_record=record,
            preference_rules=preference_rules,
            draft_type_module=draft_type_module
        )
    except Exception as e:
        logger.error(f"Draft generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={
            "error_code": "GENERATION_ERROR",
            "message": str(e)
        })

    # 6. Build response
    response = {
        "draft_id": result.draft_id,
        "doc_id": result.doc_id,
        "draft_text": result.draft_text,
        "citations": [
            {
                "label": c.citation_label,
                "source_file": c.metadata.source_file,
                "page_number": c.metadata.page_number,
                "chunk_text": c.text[:200],
                "relevance_score": c.score
            }
            for c in result.citations_used
        ],
        "preferences_applied": result.preferences_applied,
        "tokens_used": result.tokens_used,
        "generation_time_ms": result.generation_time_ms
    }

    return response
