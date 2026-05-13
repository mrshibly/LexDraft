"""
Evaluates retrieval quality using Precision@k, Recall@k, and MRR.
Run after ingesting sample documents.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.table import Table

console = Console()


def precision_at_k(retrieved: list[int], relevant: list[int], k: int) -> float:
    """Fraction of top-k retrieved chunks that are relevant."""
    top_k = retrieved[:k]
    return len(set(top_k) & set(relevant)) / k if k > 0 else 0.0


def recall_at_k(retrieved: list[int], relevant: list[int], k: int) -> float:
    """Fraction of relevant chunks that appear in top-k."""
    top_k = retrieved[:k]
    return len(set(top_k) & set(relevant)) / len(relevant) if relevant else 0.0


def mean_reciprocal_rank(retrieved: list[int], relevant: list[int]) -> float:
    """1/rank of the first relevant chunk."""
    for i, idx in enumerate(retrieved):
        if idx in relevant:
            return 1.0 / (i + 1)
    return 0.0


def run_eval():
    """Run retrieval evaluation on test queries."""
    console.print("[bold]LexDraft — Retrieval Evaluation[/bold]\n")

    from config import validate, CHROMA_PERSIST_DIR, SQLITE_DB_PATH
    validate()

    from retrieval.embedder import Embedder
    from retrieval.vector_store import VectorStore
    from feedback.preference_store import PreferenceStore
    from retrieval.retriever import retrieve
    import hashlib

    embedder = Embedder.get_instance()
    vector_store = VectorStore(CHROMA_PERSIST_DIR)
    pref_store = PreferenceStore(SQLITE_DB_PATH)

    # Load test queries
    eval_dir = os.path.dirname(os.path.abspath(__file__))
    queries_path = os.path.join(eval_dir, "test_queries.json")
    with open(queries_path, "r") as f:
        test_queries = json.load(f)

    # Get doc_id for contract_scan
    doc_id = hashlib.md5("contract_scan.pdf".encode()).hexdigest()[:8]
    record = pref_store.get_document_record(doc_id)
    if not record:
        console.print("[red]❌ Ingest contract_scan.pdf first (run demo script)[/red]")
        return

    results_table = Table(title="Retrieval Metrics")
    results_table.add_column("Query", style="cyan", max_width=40)
    results_table.add_column("P@3", style="green")
    results_table.add_column("R@3", style="yellow")
    results_table.add_column("MRR", style="blue")

    all_p3, all_r3, all_mrr = [], [], []

    for q in test_queries:
        query_text = q["query"]
        relevant = q["relevant_chunk_indices"]

        result = retrieve(doc_id, "case_fact_summary", record, vector_store, embedder, top_k=5)
        retrieved_indices = [c.metadata.chunk_index for c in result.ranked_chunks]

        p3 = precision_at_k(retrieved_indices, relevant, 3)
        r3 = recall_at_k(retrieved_indices, relevant, 3)
        mrr = mean_reciprocal_rank(retrieved_indices, relevant)

        all_p3.append(p3)
        all_r3.append(r3)
        all_mrr.append(mrr)

        results_table.add_row(query_text[:40], f"{p3:.2f}", f"{r3:.2f}", f"{mrr:.2f}")

    # Averages
    avg_p3 = sum(all_p3) / len(all_p3) if all_p3 else 0
    avg_r3 = sum(all_r3) / len(all_r3) if all_r3 else 0
    avg_mrr = sum(all_mrr) / len(all_mrr) if all_mrr else 0

    results_table.add_row("", "", "", "")
    results_table.add_row("[bold]AVERAGE[/bold]", f"[bold]{avg_p3:.2f}[/bold]", f"[bold]{avg_r3:.2f}[/bold]", f"[bold]{avg_mrr:.2f}[/bold]")

    console.print(results_table)
    console.print(f"\nTarget: P@3 ≥ 0.80, MRR ≥ 0.75")
    console.print(f"Result: P@3 = {avg_p3:.2f}, MRR = {avg_mrr:.2f}")

    return {"precision_at_3": avg_p3, "recall_at_3": avg_r3, "mrr": avg_mrr}


if __name__ == "__main__":
    run_eval()
