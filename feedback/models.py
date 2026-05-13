"""
Feedback data models for LexDraft.
Defines structures for edit sessions, learned rules, and diff analysis.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field


@dataclass
class LearnedRule:
    """A rule learned from operator edits, stored in preference store."""
    rule: str
    category: str  # 'structural' | 'tone' | 'content' | 'formatting'
    frequency: int
    confidence: float

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass
class DiffAnalysis:
    """Result of semantic diff analysis between original and edited drafts."""
    structural_changes: list[str]
    tone_changes: list[str]
    content_additions: list[str]
    content_removals: list[str]
    formatting_changes: list[str]
    learned_rules: list[str]

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass
class EditSession:
    """A recorded operator edit session."""
    session_id: str
    doc_id: str
    draft_type: str
    original_draft: str
    edited_draft: str
    operator_note: str | None
    timestamp: str  # ISO 8601

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> EditSession:
        """Reconstruct from a dictionary (e.g., loaded from SQLite)."""
        return cls(**d)
