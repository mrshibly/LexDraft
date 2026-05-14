import pytest
import os
import hashlib
from ingestion.models import StructuredDocumentRecord, Party
from feedback.preference_store import PreferenceStore
from feedback.models import LearnedRule

@pytest.fixture
def pref_store(tmp_path):
    db_path = str(tmp_path / "test_lexdraft.db")
    return PreferenceStore(db_path)

def test_document_record_serialization():
    data = {
        "doc_id": "test1",
        "source_file": "test.pdf",
        "document_type": "contract",
        "parties": [{"name": "Acme", "role": "plaintiff"}],
        "effective_date": "2024-01-01",
        "filing_date": None,
        "case_number": "123",
        "governing_law": "NY",
        "key_obligations": [],
        "termination_clauses": [],
        "signature_parties": [],
        "raw_text": "Hello world",
        "page_count": 1,
        "avg_ocr_confidence": 1.0,
        "low_confidence_pages": [],
        "indexed_at": "now"
    }
    
    restored = StructuredDocumentRecord.from_dict(data)
    assert restored.doc_id == "test1"
    assert restored.parties[0].name == "Acme"
    
    back_to_dict = restored.to_dict()
    assert back_to_dict["doc_id"] == "test1"

def test_preference_store_rules(pref_store):
    import sqlite3
    conn = sqlite3.connect(pref_store.db_path)
    conn.execute(
        "INSERT INTO learned_preferences (draft_type, rule, category, frequency, confidence, created_at, last_seen) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("test_draft", "Use direct tone", "style", 1, 1.0, "now", "now")
    )
    conn.commit()
    conn.close()
    
    rules = pref_store.get_active_rules("test_draft")
    assert len(rules) == 1
    assert rules[0].rule == "Use direct tone"
    assert rules[0].frequency == 1
