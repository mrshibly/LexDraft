"""
Retrieval data models for LexDraft.
Defines structures for chunk metadata, retrieved chunks, and retrieval results.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field


@dataclass
class ChunkMetadata:
    """Metadata attached to each text chunk for traceability."""
    doc_id: str
    source_file: str
    page_number: int
    chunk_index: int
    char_start: int
    char_end: int
    is_low_confidence: bool

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass
class RetrievedChunk:
    """A single chunk retrieved from the vector store with relevance score."""
    text: str
    score: float
    metadata: ChunkMetadata
    citation_label: str  # '[1]', '[2]', etc.

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass
class RetrievalResult:
    """Complete retrieval output including ranked chunks and coverage map."""
    doc_id: str
    query: str
    ranked_chunks: list[RetrievedChunk]
    coverage_map: dict[str, RetrievedChunk]  # label → chunk
    low_confidence_warnings: list[str]

    def to_dict(self) -> dict:
        result = {
            "doc_id": self.doc_id,
            "query": self.query,
            "ranked_chunks": [c.to_dict() for c in self.ranked_chunks],
            "coverage_map": {k: v.to_dict() for k, v in self.coverage_map.items()},
            "low_confidence_warnings": self.low_confidence_warnings,
        }
        return result
