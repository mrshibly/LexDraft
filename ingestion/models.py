"""
Ingestion data models for LexDraft.
Defines structures for OCR results, raw file payloads, and structured document records.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field


@dataclass
class PageOCRResult:
    """Result of OCR processing for a single page."""
    page_number: int
    text: str
    confidence: float | None
    word_count: int
    is_low_confidence: bool  # True if confidence < 60.0

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass
class RawFilePayload:
    """Raw extracted content from a document file."""
    file_name: str
    source_type: str          # 'native_pdf' | 'scanned_pdf' | 'image' | 'text'
    pages: list[PageOCRResult]
    raw_text: str             # concatenated full text
    page_count: int
    avg_confidence: float | None  # None if native PDF

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass
class Party:
    """A party involved in a legal document."""
    name: str
    role: str  # plaintiff | defendant | counsel | witness | other

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass
class StructuredDocumentRecord:
    """Structured extraction of key legal fields from a document."""
    doc_id: str
    source_file: str
    document_type: str
    parties: list[Party]
    effective_date: str | None
    filing_date: str | None
    case_number: str | None
    governing_law: str | None
    key_obligations: list[str]
    termination_clauses: list[str]
    signature_parties: list[str]
    raw_text: str
    page_count: int
    avg_ocr_confidence: float | None
    low_confidence_pages: list[int]
    indexed_at: str  # ISO 8601

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> StructuredDocumentRecord:
        """Reconstruct from a dictionary (e.g., loaded from SQLite JSON)."""
        parties = [Party(**p) if isinstance(p, dict) else p for p in d.get("parties", [])]
        d = dict(d)
        d["parties"] = parties
        return cls(**d)
