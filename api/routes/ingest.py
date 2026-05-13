"""
POST /api/v1/ingest — Document ingestion endpoint.
Accepts file uploads, processes through OCR/extraction, structures, chunks, and indexes.
"""
from __future__ import annotations

import hashlib
import logging
import os
import tempfile
import time

from fastapi import APIRouter, File, UploadFile, HTTPException

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """Ingest a legal document: extract, structure, chunk, embed, and index.
    
    Accepts PDF, PNG, JPG, TIFF, and TXT files.
    Returns doc_id, structured fields, and indexing stats.
    """
    start_time = time.time()

    # Save upload to temp file
    suffix = os.path.splitext(file.filename or "doc")[1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        content = await file.read()
        tmp.write(content)
        tmp.flush()
        tmp.close()
        temp_path = tmp.name

        # Generate deterministic doc_id
        doc_id = hashlib.md5((file.filename or "unknown").encode()).hexdigest()[:8]

        # 1. Load document
        from ingestion.loader import load_document
        raw = load_document(temp_path)

        # 2. Structure document
        from ingestion.structurer import structure_document
        record = structure_document(raw, doc_id)
        record.source_file = file.filename or "unknown"

        # 3. Chunk document
        from retrieval.chunker import chunk_document
        chunks = chunk_document(record)

        # 4. Embed chunks
        from api.dependencies import get_embedder, get_vector_store, get_preference_store
        embedder = get_embedder()
        chunk_texts = [text for text, _ in chunks]
        embeddings = embedder.encode(chunk_texts)

        # 5. Index in vector store
        vector_store = get_vector_store()
        metadatas = [meta.to_dict() for _, meta in chunks]
        chunks_indexed = vector_store.add_document(doc_id, chunk_texts, list(embeddings), metadatas)

        # 6. Persist structured record in SQLite
        pref_store = get_preference_store()
        pref_store.save_document_record(record)

        processing_time_ms = int((time.time() - start_time) * 1000)

        # Build response
        response = {
            "doc_id": doc_id,
            "source_file": file.filename,
            "source_type": raw.source_type,
            "page_count": raw.page_count,
            "word_count": sum(p.word_count for p in raw.pages),
            "ocr_confidence_avg": raw.avg_confidence,
            "low_confidence_pages": [p.page_number for p in raw.pages if p.is_low_confidence],
            "structured_fields": {
                "document_type": record.document_type,
                "parties": [p.to_dict() for p in record.parties],
                "effective_date": record.effective_date,
                "filing_date": record.filing_date,
                "case_number": record.case_number,
                "governing_law": record.governing_law,
                "key_obligations": record.key_obligations,
                "termination_clauses": record.termination_clauses,
                "signature_parties": record.signature_parties,
            },
            "chunks_indexed": chunks_indexed,
            "processing_time_ms": processing_time_ms
        }

        logger.info(f"Ingested {file.filename} → doc_id={doc_id} in {processing_time_ms}ms")
        return response

    except ValueError as e:
        raise HTTPException(status_code=422, detail={"error_code": "UNSUPPORTED_FILE_TYPE", "message": str(e)})
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail={"error_code": "FILE_NOT_FOUND", "message": str(e)})
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error_code": "INGESTION_ERROR", "message": str(e)})
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_path)
        except Exception:
            pass
