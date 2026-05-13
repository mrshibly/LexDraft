"""
Native PDF text extraction via pdfplumber.
Used when PDF pages contain actual text layers (not scanned).
"""
from __future__ import annotations

import logging

from ingestion.models import PageOCRResult

logger = logging.getLogger(__name__)


def table_to_markdown(table: list[list]) -> str:
    """Convert pdfplumber table output to a markdown table string.
    
    Handles None cells by replacing with empty string.
    """
    if not table or len(table) < 1:
        return ""

    # Clean cells
    cleaned = []
    for row in table:
        cleaned.append([str(cell).strip() if cell else "" for cell in row])

    # Build markdown
    header = cleaned[0]
    lines = ["| " + " | ".join(header) + " |"]
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for row in cleaned[1:]:
        # Pad row if shorter than header
        while len(row) < len(header):
            row.append("")
        lines.append("| " + " | ".join(row[:len(header)]) + " |")

    return "\n".join(lines)


def extract_native_pdf(pdf_path: str) -> list[PageOCRResult]:
    """Extract text from a native/digital PDF using pdfplumber.
    
    Extracts both text content and tables, converting tables to markdown.
    Returns a list of PageOCRResult (confidence=None for native PDFs).
    """
    import pdfplumber

    results = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                # Extract main text
                text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""

                # Extract tables and convert to markdown
                tables = page.extract_tables()
                table_markdowns = []
                for table in tables:
                    md = table_to_markdown(table)
                    if md:
                        table_markdowns.append(md)

                # Combine text and tables
                combined = text
                if table_markdowns:
                    combined += "\n\n[TABLE]\n" + "\n\n[TABLE]\n".join(table_markdowns)

                word_count = len(combined.split()) if combined else 0

                results.append(PageOCRResult(
                    page_number=i + 1,
                    text=combined,
                    confidence=None,  # Not OCR'd — treat as 100% reliable
                    word_count=word_count,
                    is_low_confidence=False
                ))

                logger.info(f"Extracted page {i + 1}: {word_count} words")

    except Exception as e:
        logger.error(f"Failed to extract native PDF: {e}")
        raise

    return results


def avg_chars_per_page(pages: list[PageOCRResult]) -> float:
    """Compute average characters per page. Used to detect scanned vs native PDFs."""
    if not pages:
        return 0.0
    total_chars = sum(len(p.text) for p in pages)
    return total_chars / len(pages)
