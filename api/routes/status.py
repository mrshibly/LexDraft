"""
GET endpoints for system status, document listing, preferences, and health.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "1.0.0"}


@router.get("/documents")
async def list_documents():
    """List all indexed documents with metadata."""
    from api.dependencies import get_vector_store, get_preference_store

    vector_store = get_vector_store()
    pref_store = get_preference_store()

    doc_ids = vector_store.list_documents()
    documents = []

    for doc_id in doc_ids:
        record = pref_store.get_document_record(doc_id)
        doc_info = {
            "doc_id": doc_id,
            "source_file": record.source_file if record else "unknown",
            "indexed_at": record.indexed_at if record else None,
            "chunk_count": None  # Would need to query collection
        }
        documents.append(doc_info)

    return {"documents": documents}


@router.get("/preferences/{draft_type}")
async def get_preferences(draft_type: str):
    """Get all active learned preferences for a draft type."""
    from api.dependencies import get_preference_store

    pref_store = get_preference_store()
    rules = pref_store.get_active_rules(draft_type)

    return {
        "draft_type": draft_type,
        "rules": [
            {
                "rule": r.rule,
                "category": r.category,
                "frequency": r.frequency,
                "confidence": r.confidence
            }
            for r in rules
        ]
    }
