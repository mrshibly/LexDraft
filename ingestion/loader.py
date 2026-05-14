"""
Detects document type and routes to appropriate extractor.
Entry point for all document ingestion.
"""
from __future__ import annotations

import logging
import os

from ingestion.models import RawFilePayload, PageOCRResult

logger = logging.getLogger(__name__)

# Maximum file size to process (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024
# Maximum pages for very large files
MAX_PAGES = 20


def detect_source_type(file_path: str) -> str:
    """Detect the source type of a file using MIME type detection.
    
    Returns one of: 'native_pdf', 'scanned_pdf', 'image', 'text'.
    """
    import mimetypes

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    mime, _ = mimetypes.guess_type(file_path)
    if not mime:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf": mime = "application/pdf"
        elif ext in (".png", ".jpg", ".jpeg"): mime = "image/png"
        elif ext in (".tif", ".tiff"): mime = "image/tiff"
        elif ext == ".txt": mime = "text/plain"
        else: mime = "application/octet-stream"

    logger.info(f"Detected MIME type: {mime} for {file_path}")

    if mime == "application/pdf":
        # Check if PDF has native text or is a scanned image
        from ingestion.extractor import extract_native_pdf, avg_chars_per_page
        try:
            # Load first 3 pages to check text density
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                test_pages = []
                for i, page in enumerate(pdf.pages[:3]):
                    text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
                    test_pages.append(PageOCRResult(
                        page_number=i + 1,
                        text=text,
                        confidence=None,
                        word_count=len(text.split()),
                        is_low_confidence=False
                    ))

            avg = avg_chars_per_page(test_pages)
            if avg < 50:
                logger.info(f"PDF text density too low ({avg:.0f} chars/page) — treating as scanned")
                return "scanned_pdf"
            else:
                logger.info(f"PDF has text content ({avg:.0f} chars/page) — treating as native")
                return "native_pdf"
        except Exception as e:
            logger.warning(f"Error checking PDF type, defaulting to scanned: {e}")
            return "scanned_pdf"

    elif mime in ("image/png", "image/jpeg", "image/tiff", "image/bmp"):
        return "image"
    elif mime in ("text/plain", "text/html"):
        return "text"
    else:
        raise ValueError(f"Unsupported file type: {mime}")


def load_document(file_path: str) -> RawFilePayload:
    """Load a document from disk, detect its type, and extract text content.
    
    This is the main entry point for document ingestion.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE:
        logger.warning(
            f"File {file_path} is {file_size / 1024 / 1024:.1f}MB — "
            f"processing first {MAX_PAGES} pages only"
        )

    file_name = os.path.basename(file_path)
    source_type = detect_source_type(file_path)

    pages: list[PageOCRResult] = []

    if source_type == "native_pdf":
        from ingestion.extractor import extract_native_pdf
        pages = extract_native_pdf(file_path)
    elif source_type == "scanned_pdf":
        from ingestion.ocr import ocr_pdf
        pages = ocr_pdf(file_path)
    elif source_type == "image":
        from ingestion.ocr import ocr_image
        pages = ocr_image(file_path)
    elif source_type == "text":
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        pages = [PageOCRResult(
            page_number=1,
            text=content,
            confidence=100.0,
            word_count=len(content.split()),
            is_low_confidence=False
        )]

    # Limit pages for very large files
    if len(pages) > MAX_PAGES:
        logger.warning(f"Truncating from {len(pages)} to {MAX_PAGES} pages")
        pages = pages[:MAX_PAGES]

    # Concatenate all page texts with page boundary markers
    raw_text = "\n\n".join(
        f"--- PAGE {p.page_number} ---\n\n{p.text}" for p in pages
    )

    # Compute average confidence (skip None confidence pages)
    conf_values = [p.confidence for p in pages if p.confidence is not None]
    avg_confidence = round(sum(conf_values) / len(conf_values), 2) if conf_values else None

    payload = RawFilePayload(
        file_name=file_name,
        source_type=source_type,
        pages=pages,
        raw_text=raw_text,
        page_count=len(pages),
        avg_confidence=avg_confidence
    )

    logger.info(
        f"Loaded {file_name}: type={source_type}, pages={len(pages)}, "
        f"avg_confidence={avg_confidence}"
    )

    return payload
