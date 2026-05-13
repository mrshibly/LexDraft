"""
SQLite-backed store for learned operator preferences.
Deduplicates semantically similar rules using embedding cosine similarity.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone

import numpy as np

from feedback.models import LearnedRule, EditSession

logger = logging.getLogger(__name__)


class PreferenceStore:
    """Manages learned operator preferences in SQLite with semantic deduplication.
    
    New rules are compared against existing rules using cosine similarity.
    If similarity > 0.85, the existing rule's frequency is incremented.
    Otherwise, a new rule is inserted.
    """

    def __init__(self, db_path: str):
        """Initialise the preference store and create tables if needed."""
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create the database tables if they don't exist."""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS learned_preferences (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    draft_type  TEXT NOT NULL,
                    rule        TEXT NOT NULL,
                    category    TEXT NOT NULL,
                    frequency   INTEGER DEFAULT 1,
                    confidence  REAL DEFAULT 1.0,
                    created_at  TEXT NOT NULL,
                    last_seen   TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS edit_sessions (
                    session_id    TEXT PRIMARY KEY,
                    doc_id        TEXT NOT NULL,
                    draft_type    TEXT NOT NULL,
                    original_draft TEXT NOT NULL,
                    edited_draft  TEXT NOT NULL,
                    operator_note TEXT,
                    timestamp     TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS document_records (
                    doc_id      TEXT PRIMARY KEY,
                    record_json TEXT NOT NULL,
                    indexed_at  TEXT NOT NULL
                );
            """)
            conn.commit()
        finally:
            conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a SQLite connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def add_rule(self, rule: str, category: str, draft_type: str) -> LearnedRule:
        """Add a learned rule, deduplicating against existing rules.
        
        Uses cosine similarity of embeddings to detect duplicate/similar rules.
        If max similarity > 0.85: increment frequency + update last_seen.
        Otherwise: insert as new rule with frequency=1.
        
        Returns the LearnedRule that was created or updated.
        """
        from retrieval.embedder import Embedder

        embedder = Embedder.get_instance()
        now = datetime.now(timezone.utc).isoformat()

        # Embed the new rule
        new_emb = embedder.encode_single(rule)

        # Load existing rules for this draft type
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT id, rule, frequency FROM learned_preferences WHERE draft_type = ?",
                (draft_type,)
            ).fetchall()

            if rows:
                # Embed existing rules
                existing_rules = [dict(r) for r in rows]
                existing_texts = [r["rule"] for r in existing_rules]
                existing_embs = embedder.encode(existing_texts)

                # Compute cosine similarities
                similarities = np.dot(existing_embs, new_emb)
                max_idx = int(np.argmax(similarities))
                max_sim = float(similarities[max_idx])

                if max_sim > 0.85:
                    # Update existing rule
                    existing = existing_rules[max_idx]
                    new_freq = existing["frequency"] + 1
                    conn.execute(
                        "UPDATE learned_preferences SET frequency = ?, last_seen = ? WHERE id = ?",
                        (new_freq, now, existing["id"])
                    )
                    conn.commit()
                    logger.info(
                        f"Updated existing rule (sim={max_sim:.2f}): "
                        f"'{existing['rule'][:50]}...' → freq={new_freq}"
                    )
                    return LearnedRule(
                        rule=existing["rule"],
                        category=category,
                        frequency=new_freq,
                        confidence=1.0
                    )

            # Insert new rule
            conn.execute(
                "INSERT INTO learned_preferences (draft_type, rule, category, frequency, confidence, created_at, last_seen) "
                "VALUES (?, ?, ?, 1, 1.0, ?, ?)",
                (draft_type, rule, category, now, now)
            )
            conn.commit()
            logger.info(f"Added new rule: '{rule[:50]}...'")

            return LearnedRule(
                rule=rule,
                category=category,
                frequency=1,
                confidence=1.0
            )

        finally:
            conn.close()

    def get_active_rules(self, draft_type: str, min_frequency: int = 1) -> list[LearnedRule]:
        """Get active rules for a draft type, ordered by frequency descending.
        
        Returns at most 8 rules.
        """
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT rule, category, frequency, confidence FROM learned_preferences "
                "WHERE draft_type = ? AND frequency >= ? "
                "ORDER BY frequency DESC LIMIT 8",
                (draft_type, min_frequency)
            ).fetchall()

            return [
                LearnedRule(
                    rule=row["rule"],
                    category=row["category"],
                    frequency=row["frequency"],
                    confidence=row["confidence"]
                )
                for row in rows
            ]
        finally:
            conn.close()

    def get_confirmed_rules(self, draft_type: str) -> list[LearnedRule]:
        """Get confirmed rules (frequency >= 3)."""
        return self.get_active_rules(draft_type, min_frequency=3)

    def save_edit_session(self, session: EditSession) -> None:
        """Persist an edit session to SQLite."""
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO edit_sessions "
                "(session_id, doc_id, draft_type, original_draft, edited_draft, operator_note, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (session.session_id, session.doc_id, session.draft_type,
                 session.original_draft, session.edited_draft,
                 session.operator_note, session.timestamp)
            )
            conn.commit()
            logger.info(f"Saved edit session: {session.session_id}")
        finally:
            conn.close()

    def get_edit_sessions(self, draft_type: str = None) -> list[EditSession]:
        """Get all edit sessions, optionally filtered by draft type."""
        conn = self._get_conn()
        try:
            if draft_type:
                rows = conn.execute(
                    "SELECT * FROM edit_sessions WHERE draft_type = ? ORDER BY timestamp DESC",
                    (draft_type,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM edit_sessions ORDER BY timestamp DESC"
                ).fetchall()

            return [EditSession.from_dict(dict(row)) for row in rows]
        finally:
            conn.close()

    def save_document_record(self, record) -> None:
        """Persist a StructuredDocumentRecord to SQLite as JSON."""
        conn = self._get_conn()
        try:
            record_json = json.dumps(record.to_dict())
            conn.execute(
                "INSERT OR REPLACE INTO document_records (doc_id, record_json, indexed_at) VALUES (?, ?, ?)",
                (record.doc_id, record_json, record.indexed_at)
            )
            conn.commit()
            logger.info(f"Saved document record: {record.doc_id}")
        finally:
            conn.close()

    def get_document_record(self, doc_id: str):
        """Load a StructuredDocumentRecord from SQLite."""
        from ingestion.models import StructuredDocumentRecord
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT record_json FROM document_records WHERE doc_id = ?",
                (doc_id,)
            ).fetchone()
            if row:
                data = json.loads(row["record_json"])
                return StructuredDocumentRecord.from_dict(data)
            return None
        finally:
            conn.close()

    def get_all_document_records(self) -> list[dict]:
        """Get basic info for all stored document records."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT doc_id, indexed_at FROM document_records ORDER BY indexed_at DESC"
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def rule_count(self, draft_type: str) -> int:
        """Count total rules for a draft type."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM learned_preferences WHERE draft_type = ?",
                (draft_type,)
            ).fetchone()
            return row["cnt"] if row else 0
        finally:
            conn.close()

    def session_count(self) -> int:
        """Count total edit sessions."""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT COUNT(*) as cnt FROM edit_sessions").fetchone()
            return row["cnt"] if row else 0
        finally:
            conn.close()
