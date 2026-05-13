"""
Splits raw document text into overlapping chunks with metadata.
Preserves page boundary metadata for source citation.
"""
from __future__ import annotations

import logging
import re

from ingestion.models import StructuredDocumentRecord
from retrieval.models import ChunkMetadata

logger = logging.getLogger(__name__)


def chunk_document(record: StructuredDocumentRecord) -> list[tuple[str, ChunkMetadata]]:
    """Split a structured document into chunks, respecting page boundaries.
    
    Returns list of (chunk_text, ChunkMetadata) tuples.
    Chunks do NOT cross page boundaries.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=64,
        separators=["\n\n", "\n", ". ", " "],
        length_function=len,
    )

    # Split raw text by page markers
    page_pattern = r'--- PAGE (\d+) ---\n\n'
    page_splits = re.split(page_pattern, record.raw_text)

    # page_splits alternates between separators and content:
    # ['', '1', 'page1_text', '2', 'page2_text', ...]
    pages_content = []
    i = 1
    while i < len(page_splits) - 1:
        page_num = int(page_splits[i])
        page_text = page_splits[i + 1]
        pages_content.append((page_num, page_text))
        i += 2

    # If no page markers found, treat entire text as one page
    if not pages_content:
        pages_content = [(1, record.raw_text)]

    # Determine which pages have low confidence
    low_conf_set = set(record.low_confidence_pages)

    all_chunks = []
    global_chunk_index = 0
    global_char_offset = 0

    for page_num, page_text in pages_content:
        page_text = page_text.strip()
        if not page_text:
            continue

        is_low_conf = page_num in low_conf_set

        # Small pages: keep as single chunk
        if len(page_text) < 50:
            meta = ChunkMetadata(
                doc_id=record.doc_id,
                source_file=record.source_file,
                page_number=page_num,
                chunk_index=global_chunk_index,
                char_start=global_char_offset,
                char_end=global_char_offset + len(page_text),
                is_low_confidence=is_low_conf,
            )
            all_chunks.append((page_text, meta))
            global_chunk_index += 1
            global_char_offset += len(page_text)
            continue

        # Split this page's text
        chunks = splitter.split_text(page_text)

        # Track char positions within the page
        local_offset = 0
        for chunk_text in chunks:
            # Find the actual position of this chunk in the page text
            pos = page_text.find(chunk_text[:50], local_offset)
            if pos == -1:
                pos = local_offset

            meta = ChunkMetadata(
                doc_id=record.doc_id,
                source_file=record.source_file,
                page_number=page_num,
                chunk_index=global_chunk_index,
                char_start=global_char_offset + pos,
                char_end=global_char_offset + pos + len(chunk_text),
                is_low_confidence=is_low_conf,
            )
            all_chunks.append((chunk_text, meta))
            global_chunk_index += 1
            local_offset = max(pos + len(chunk_text) - 64, local_offset + 1)

        global_char_offset += len(page_text)

    logger.info(
        f"Chunked document {record.doc_id}: {len(all_chunks)} chunks "
        f"from {len(pages_content)} pages"
    )

    return all_chunks
