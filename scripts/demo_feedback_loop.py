"""
End-to-end demonstration of the LexDraft feedback improvement loop.

Usage: python scripts/demo_feedback_loop.py

Steps:
  1. Ingest contract_scan.pdf
  2. Generate Draft A (no learned rules)
  3. Load pre-written operator edit from sample_docs/edited_draft_sample.txt
  4. Submit edit → extract rules → store in preference store
  5. Ingest notice_typed.pdf
  6. Generate Draft B (with learned rules from step 4)
  7. Print comparison showing how Draft B reflects learned rules
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

console = Console()

def run_demo():
    """Run the complete feedback loop demonstration."""
    console.print(Panel("🏛 LexDraft — Feedback Loop Demonstration", style="bold blue"))

    from config import validate
    validate()

    from ingestion.loader import load_document
    from ingestion.structurer import structure_document
    from retrieval.chunker import chunk_document
    from retrieval.embedder import Embedder
    from retrieval.vector_store import VectorStore
    from retrieval.retriever import retrieve
    from drafting.generator import generate_draft
    from drafting.draft_types import case_fact_summary
    from feedback.capture import capture_edit
    from feedback.diff_analyzer import process_edit
    from feedback.preference_store import PreferenceStore
    from feedback.prompt_updater import get_preference_rules_list
    from config import CHROMA_PERSIST_DIR, SQLITE_DB_PATH
    import hashlib

    embedder = Embedder.get_instance()
    vector_store = VectorStore(CHROMA_PERSIST_DIR)
    pref_store = PreferenceStore(SQLITE_DB_PATH)

    sample_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_docs")

    # Step 1: Ingest contract_scan.pdf
    console.print("\n[bold]Step 1/7:[/bold] Ingesting contract_scan.pdf...")
    contract_path = os.path.join(sample_dir, "contract_scan.pdf")
    if not os.path.exists(contract_path):
        console.print("[red]❌ Run scripts/seed_sample_docs.py first[/red]")
        return

    raw = load_document(contract_path)
    doc_id_1 = hashlib.md5("contract_scan.pdf".encode()).hexdigest()[:8]
    record_1 = structure_document(raw, doc_id_1)
    chunks = chunk_document(record_1)
    chunk_texts = [t for t, _ in chunks]
    embeddings = embedder.encode(chunk_texts)
    metadatas = [m.to_dict() for _, m in chunks]
    vector_store.add_document(doc_id_1, chunk_texts, list(embeddings), metadatas)
    pref_store.save_document_record(record_1)
    console.print(f"  ✅ Ingested: {len(chunks)} chunks indexed (doc_id={doc_id_1})")

    # Step 2: Generate Draft A
    console.print("\n[bold]Step 2/7:[/bold] Generating Draft A (no learned preferences)...")
    retrieval_a = retrieve(doc_id_1, "case_fact_summary", record_1, vector_store, embedder)
    draft_a = generate_draft(retrieval_a, record_1, [], case_fact_summary)
    console.print(Panel(draft_a.draft_text[:500] + "...", title="Draft A (first 500 chars)"))

    # Save Draft A
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_outputs"), exist_ok=True)
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_outputs", "draft_a_no_rules.md"), "w", encoding="utf-8") as f:
        f.write(draft_a.draft_text)

    # Step 3: Load operator edit
    console.print("\n[bold]Step 3/7:[/bold] Loading operator edit from edited_draft_sample.txt...")
    edited_path = os.path.join(sample_dir, "edited_draft_sample.txt")
    with open(edited_path, "r", encoding="utf-8") as f:
        edited_text = f.read()
    console.print(f"  Loaded edited draft ({len(edited_text)} chars)")

    # Step 4: Capture edit and extract rules
    console.print("\n[bold]Step 4/7:[/bold] Analysing edit, extracting learned rules...")
    session = capture_edit(doc_id_1, "case_fact_summary", draft_a.draft_text, edited_text, "Demo edit: reordered sections, changed terminology", pref_store)
    diff_analysis, rules = process_edit(session, pref_store)

    rule_table = Table(title="Extracted Rules")
    rule_table.add_column("Rule", style="cyan")
    rule_table.add_column("Category", style="green")
    rule_table.add_column("Frequency", style="yellow")
    for r in rules:
        rule_table.add_row(r.rule[:80], r.category, str(r.frequency))
    console.print(rule_table)

    # Save feedback session
    feedback_output = {
        "session_id": session.session_id,
        "rules_extracted": len(rules),
        "diff_analysis": diff_analysis.to_dict(),
        "rules": [r.to_dict() for r in rules]
    }
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_outputs", "feedback_session.json"), "w") as f:
        json.dump(feedback_output, f, indent=2)

    # Step 5: Ingest notice_typed.pdf
    console.print("\n[bold]Step 5/7:[/bold] Ingesting notice_typed.pdf...")
    notice_path = os.path.join(sample_dir, "notice_typed.pdf")
    raw_2 = load_document(notice_path)
    doc_id_2 = hashlib.md5("notice_typed.pdf".encode()).hexdigest()[:8]
    record_2 = structure_document(raw_2, doc_id_2)
    chunks_2 = chunk_document(record_2)
    chunk_texts_2 = [t for t, _ in chunks_2]
    embeddings_2 = embedder.encode(chunk_texts_2)
    metadatas_2 = [m.to_dict() for _, m in chunks_2]
    vector_store.add_document(doc_id_2, chunk_texts_2, list(embeddings_2), metadatas_2)
    pref_store.save_document_record(record_2)
    console.print(f"  ✅ Ingested: {len(chunks_2)} chunks indexed (doc_id={doc_id_2})")

    # Step 6: Generate Draft B WITH learned rules
    console.print("\n[bold]Step 6/7:[/bold] Generating Draft B (with learned preferences)...")
    pref_rules = get_preference_rules_list("case_fact_summary", pref_store)
    console.print(f"  Applying {len(pref_rules)} learned preferences:")
    for p in pref_rules:
        console.print(f"    • {p[:80]}")

    retrieval_b = retrieve(doc_id_2, "case_fact_summary", record_2, vector_store, embedder)
    draft_b = generate_draft(retrieval_b, record_2, pref_rules, case_fact_summary)
    console.print(Panel(draft_b.draft_text[:500] + "...", title="Draft B (first 500 chars)"))

    # Save Draft B
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_outputs", "draft_b_with_rules.md"), "w") as f:
        f.write(draft_b.draft_text)

    # Step 7: Comparison
    console.print("\n[bold]Step 7/7:[/bold] Comparing Draft A vs Draft B behaviour...\n")
    comparison = Table(title="Feedback Loop Results")
    comparison.add_column("Metric", style="bold")
    comparison.add_column("Value", style="cyan")
    comparison.add_row("Rules Learned", str(len(rules)))
    comparison.add_row("Rules Applied in Draft B", str(len(pref_rules)))
    comparison.add_row("Draft A Length", f"{len(draft_a.draft_text)} chars")
    comparison.add_row("Draft B Length", f"{len(draft_b.draft_text)} chars")
    comparison.add_row("Draft A Citations", str(len(draft_a.citations_used)))
    comparison.add_row("Draft B Citations", str(len(draft_b.citations_used)))
    console.print(comparison)

    console.print(Panel("✅ Demo complete. See sample_outputs/ for full drafts.", style="bold green"))


if __name__ == "__main__":
    run_demo()
