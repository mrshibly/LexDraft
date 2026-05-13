"""
Measures citation coverage: what fraction of factual draft sentences have citations.
"""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
console = Console()

CITATION_PATTERN = re.compile(r'\[\d+\]')
SKIP_SECTION = "FLAGGED GAPS"


def citation_coverage(draft_text: str) -> dict:
    """Calculate citation coverage for a draft text."""
    import nltk
    lines = draft_text.split("\n")
    in_skip = False
    scoreable = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if SKIP_SECTION in stripped.upper():
            in_skip = True
            continue
        if stripped.startswith("##") and in_skip:
            in_skip = False
        if in_skip:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("|") and "---" in stripped:
            continue

        sentences = nltk.sent_tokenize(stripped)
        scoreable.extend(sentences)

    cited = [s for s in scoreable if CITATION_PATTERN.search(s)]
    uncited = [s for s in scoreable if not CITATION_PATTERN.search(s)]
    ratio = len(cited) / len(scoreable) if scoreable else 0

    return {
        "total_sentences": len(scoreable),
        "cited_sentences": len(cited),
        "coverage_ratio": round(ratio, 4),
        "uncited_sentences": uncited[:5]
    }


def run_eval():
    """Run grounding evaluation on sample outputs."""
    console.print("[bold]LexDraft — Grounding Evaluation[/bold]\n")
    outputs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_outputs")

    for fname in ["draft_a_no_rules.md", "draft_b_with_rules.md"]:
        path = os.path.join(outputs_dir, fname)
        if not os.path.exists(path):
            console.print(f"[yellow]⚠ {fname} not found — run demo first[/yellow]")
            continue
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        result = citation_coverage(text)
        pct = result["coverage_ratio"] * 100
        icon = "✅" if pct >= 85 else "⚠️"
        console.print(f"{icon} [bold]{fname}[/bold]: {pct:.1f}% coverage ({result['cited_sentences']}/{result['total_sentences']} sentences)")
        if result["uncited_sentences"]:
            console.print(f"  Sample uncited: {result['uncited_sentences'][0][:80]}...")
    console.print(f"\nTarget: ≥ 85% citation coverage")


if __name__ == "__main__":
    run_eval()
