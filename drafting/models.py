"""
Drafting data models for LexDraft.
Defines the DraftResult structure returned by the generator.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

from retrieval.models import RetrievedChunk


@dataclass
class DraftResult:
    """Result of a draft generation call."""
    draft_id: str
    doc_id: str
    draft_type: str
    draft_text: str
    citations_used: list[RetrievedChunk]
    preferences_applied: list[str]
    model_used: str
    tokens_used: int
    generation_time_ms: int

    def to_dict(self) -> dict:
        result = dataclasses.asdict(self)
        return result
