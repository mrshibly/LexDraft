# LexDraft — Architecture Documentation

## System Diagram

See README.md for the ASCII system diagram.

## Stage 1: Document Ingestion

**Files:** `ingestion/loader.py`, `ingestion/ocr.py`, `ingestion/extractor.py`, `ingestion/structurer.py`

Documents enter through `loader.py` which detects MIME type via `python-magic`:
- Native PDFs → `pdfplumber` text extraction with table detection
- Scanned PDFs (< 50 chars/page) → OCR pipeline
- Images → Direct OCR
- Text files → Passthrough

OCR preprocessing (OpenCV): grayscale → Otsu binarisation → denoising → deskew → upscale.

Structuring uses two-pass extraction:
1. Regex patterns for dates, case numbers, party names, amounts, section headers
2. LLM call (Claude via OpenRouter) with regex hints for confirmation/completion

Output: `StructuredDocumentRecord` with all extracted fields + raw text with page markers.

## Stage 2: Retrieval & Grounding

**Files:** `retrieval/chunker.py`, `retrieval/embedder.py`, `retrieval/vector_store.py`, `retrieval/retriever.py`

Text is split into chunks respecting page boundaries (no cross-page chunks).
Chunk size: 512 chars, overlap: 64 chars.

Embeddings: `all-MiniLM-L6-v2` (384-dimensional), normalised to unit length.

ChromaDB stores embeddings in per-document collections + a global collection.

Retriever builds task-specific queries, retrieves top-k chunks, and assigns citation labels `[1]`, `[2]`, etc. This creates the **coverage map** — the critical data structure linking draft citations to source evidence.

## Stage 3: Draft Generation

**Files:** `drafting/prompt_builder.py`, `drafting/generator.py`, `drafting/draft_types/case_fact_summary.py`

Prompt assembly order:
1. System prompt (legal drafting persona + strict grounding rules)
2. Evidence passages with citation labels and confidence
3. Structured fields extracted from document
4. Learned operator preferences (if any)
5. Task instruction (Case Fact Summary template)

Post-processing: Extract `[N]` citation tags from output, link to coverage map entries.

## Stage 4: Feedback Loop

**Files:** `feedback/capture.py`, `feedback/diff_analyzer.py`, `feedback/preference_store.py`, `feedback/prompt_updater.py`

### Before (no rules):
```
EVIDENCE PASSAGES:
[1] Source: doc.pdf | Page 1 | ...
[2] Source: doc.pdf | Page 2 | ...

TASK: Generate a Case Fact Summary...
```

### After (with learned rules):
```
EVIDENCE PASSAGES:
[1] Source: doc.pdf | Page 1 | ...
[2] Source: doc.pdf | Page 2 | ...

OPERATOR PREFERENCES FROM PRIOR EDITS:
───────────────────────────────────────────
• Always state the filing date in the first sentence
• Use "Respondent" instead of "defendant"
• List obligations as numbered items, not prose
★ Include governing law in matter overview

TASK: Generate a Case Fact Summary...
```

Rules with ★ (frequency ≥ 3) are confirmed by multiple edit sessions.

### Deduplication Logic

When a new rule arrives:
1. Embed the new rule text
2. Load all existing rules for the same draft type
3. Compute cosine similarity against each existing rule
4. If max similarity > 0.85 → increment frequency of the matching rule
5. Otherwise → insert as new rule with frequency = 1

## Data Flow Diagram

```
File Upload → MIME Detection → Extractor Selection
     ↓
Raw Text + Pages → Regex Extraction → LLM Extraction → Merge
     ↓
StructuredDocumentRecord → Chunker → Embedder → ChromaDB
     ↓                                              ↓
SQLite (metadata)                          Query → Ranked Chunks
                                                    ↓
                                     Coverage Map + Evidence Block
                                                    ↓
                              Prompt (system + evidence + prefs + task)
                                                    ↓
                                          Claude API → Draft Text
                                                    ↓
                                     Citation Post-Processing → DraftResult
                                                    ↓
                         Operator Edit → Diff Analysis → Rule Storage → Better Prompts
```

## Persistence Layer

| Store | Contents |
|-------|----------|
| ChromaDB (`data/chroma_db/`) | Document embeddings, per-doc and global collections |
| SQLite (`data/lexdraft.db`) | Document records (JSON), edit sessions, learned rules |
| Filesystem (`sample_outputs/`) | Generated drafts, feedback session exports |

## Design Decisions

1. **OpenRouter over direct Anthropic SDK**: Provides model flexibility and unified API. Uses OpenAI-compatible SDK with custom base URL.

2. **Page-boundary-aware chunking**: Prevents chunks from spanning pages, which would break citation traceability to specific source pages.

3. **Semantic rule deduplication**: Using embedding cosine similarity (>0.85) rather than exact text matching, so "Use numbered lists" and "Format as numbered list" merge correctly.

4. **Two-pass structuring**: Regex first for speed and reliability on well-formatted patterns; LLM second to catch anything regex missed. LLM values take priority since they're semantically parsed.

5. **Deterministic doc_id**: `md5(filename)[:8]` ensures same file always gets same ID, making retrieval queries consistent across restarts.
