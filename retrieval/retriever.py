"""
Retrieves and ranks relevant chunks for a given drafting task.
Produces a coverage map for citation grounding.
"""
from __future__ import annotations

import logging

from ingestion.models import StructuredDocumentRecord
from retrieval.models import ChunkMetadata, RetrievedChunk, RetrievalResult
from retrieval.vector_store import VectorStore
from retrieval.embedder import Embedder

logger = logging.getLogger(__name__)

# Task-specific query templates
TASK_QUERIES = {
    "case_fact_summary": (
        "parties names dates timeline events dispute obligations "
        "clauses termination signatures governing law"
    ),
}


def build_task_query(draft_type: str, structured_fields: dict) -> str:
    """Build a task-specific search query string for retrieval.
    
    Includes party names from structured fields if available.
    """
    base_query = TASK_QUERIES.get(draft_type, TASK_QUERIES["case_fact_summary"])

    # Inject party names if available
    parties = structured_fields.get("parties", [])
    party_names = []
    for p in parties:
        if isinstance(p, dict):
            party_names.append(p.get("name", ""))
        elif hasattr(p, "name"):
            party_names.append(p.name)

    if party_names:
        query = f"parties: {', '.join(party_names)} {base_query}"
    else:
        query = base_query

    return query


def retrieve(
    doc_id: str,
    draft_type: str,
    structured_record: StructuredDocumentRecord,
    vector_store: VectorStore,
    embedder: Embedder,
    top_k: int = 8
) -> RetrievalResult:
    """Retrieve and rank relevant chunks for a drafting task.
    
    Builds task-specific query, retrieves from vector store,
    assigns citation labels, and builds the coverage map.
    
    Args:
        doc_id: Document to retrieve from.
        draft_type: Type of draft being generated.
        structured_record: Structured fields from the document.
        vector_store: VectorStore instance.
        embedder: Embedder instance.
        top_k: Number of top chunks to retrieve.
    
    Returns:
        RetrievalResult with ranked chunks, coverage map, and warnings.
    """
    # 1. Build task query
    structured_fields = structured_record.to_dict()
    query = build_task_query(draft_type, structured_fields)
    logger.info(f"Retrieval query: {query[:100]}...")

    # 2. Embed query
    query_embedding = embedder.encode_single(query)

    # 3. Query vector store
    raw_results = vector_store.query(doc_id, query_embedding, top_k)

    if not raw_results:
        logger.warning(f"No results found for doc_id={doc_id}")
        return RetrievalResult(
            doc_id=doc_id,
            query=query,
            ranked_chunks=[],
            coverage_map={},
            low_confidence_warnings=[]
        )

    # 4. Convert to RetrievedChunk objects with citation labels
    ranked_chunks = []
    coverage_map = {}
    low_confidence_warnings = []

    # Sort by score descending
    raw_results.sort(key=lambda x: x["score"], reverse=True)

    for i, result in enumerate(raw_results):
        label = f"[{i + 1}]"
        meta_dict = result["metadata"]

        metadata = ChunkMetadata(
            doc_id=meta_dict.get("doc_id", doc_id),
            source_file=meta_dict.get("source_file", ""),
            page_number=int(meta_dict.get("page_number", 0)),
            chunk_index=int(meta_dict.get("chunk_index", i)),
            char_start=int(meta_dict.get("char_start", 0)),
            char_end=int(meta_dict.get("char_end", 0)),
            is_low_confidence=bool(meta_dict.get("is_low_confidence", False)),
        )

        chunk = RetrievedChunk(
            text=result["text"],
            score=result["score"],
            metadata=metadata,
            citation_label=label
        )

        ranked_chunks.append(chunk)
        coverage_map[label] = chunk

        # Collect low-confidence warnings
        if metadata.is_low_confidence:
            low_confidence_warnings.append(
                f"⚠ Chunk {label} from page {metadata.page_number} has low OCR confidence"
            )

    logger.info(
        f"Retrieved {len(ranked_chunks)} chunks for doc {doc_id}, "
        f"{len(low_confidence_warnings)} low-confidence warnings"
    )

    return RetrievalResult(
        doc_id=doc_id,
        query=query,
        ranked_chunks=ranked_chunks,
        coverage_map=coverage_map,
        low_confidence_warnings=low_confidence_warnings
    )
