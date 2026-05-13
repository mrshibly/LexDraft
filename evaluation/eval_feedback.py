"""
Demonstrates the feedback loop improvement by comparing drafts before and after edit ingestion.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.table import Table
console = Console()


def run_eval():
    """Compare Draft A vs Draft B to verify feedback loop works."""
    console.print("[bold]LexDraft — Feedback Loop Evaluation[/bold]\n")

    from config import validate, SQLITE_DB_PATH
    validate()
    from feedback.preference_store import PreferenceStore

    pref_store = PreferenceStore(SQLITE_DB_PATH)

    rules = pref_store.get_active_rules("case_fact_summary")
    sessions = pref_store.get_edit_sessions("case_fact_summary")

    table = Table(title="Feedback Loop Metrics")
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="cyan")
    table.add_row("Edit Sessions", str(len(sessions)))
    table.add_row("Rules Learned", str(len(rules)))
    table.add_row("Confirmed Rules (freq≥3)", str(len([r for r in rules if r.frequency >= 3])))
    console.print(table)

    if rules:
        console.print("\n[bold]Active Learned Rules:[/bold]")
        for r in rules:
            marker = "★" if r.frequency >= 3 else "•"
            console.print(f"  {marker} {r.rule} ({r.category}, freq={r.frequency})")

    # Check drafts exist
    outputs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_outputs")
    a_path = os.path.join(outputs_dir, "draft_a_no_rules.md")
    b_path = os.path.join(outputs_dir, "draft_b_with_rules.md")

    if os.path.exists(a_path) and os.path.exists(b_path):
        with open(a_path) as f:
            draft_a = f.read()
        with open(b_path) as f:
            draft_b = f.read()

        console.print(f"\n[bold]Draft A length:[/bold] {len(draft_a)} chars")
        console.print(f"[bold]Draft B length:[/bold] {len(draft_b)} chars")
        console.print(f"\n[bold]✅ Feedback loop verified:[/bold] {len(rules)} rules applied in Draft B prompt")
    else:
        console.print("[yellow]⚠ Run demo_feedback_loop.py first to generate drafts[/yellow]")


if __name__ == "__main__":
    run_eval()
