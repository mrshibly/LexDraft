# LexDraft — AI Legal Document Processing & Grounded Drafting

An AI-powered system that ingests messy legal documents, extracts structured content, retrieves relevant evidence, generates grounded legal draft summaries with citations, and continuously improves from operator edits.

## Quick Start

### Prerequisites
```bash
# Windows (via winget)
winget install UB-Mannheim.TesseractOCR
# Also install Poppler: download from https://github.com/oschwartz10612/poppler-windows/releases

# macOS
brew install tesseract poppler

# Linux
sudo apt-get install tesseract-ocr poppler-utils
```

### Installation
```bash
cd lexdraft
pip install -r requirements.txt
python -c "import nltk; nltk.download('punkt_tab', quiet=True)"
```

### Configuration
```bash
cp .env.example .env
# Edit .env and set your OPENROUTER_API_KEY
```

### Running
```bash
# Generate sample documents
python scripts/seed_sample_docs.py

# Start API server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Start Streamlit UI (in another terminal)
streamlit run ui/app.py

# Run end-to-end demo
python scripts/demo_feedback_loop.py
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          LexDraft System                            │
│                                                                     │
│  ┌──────────────┐    ┌─────────────────────────────────────────┐   │
│  │   Streamlit  │    │              FastAPI Layer               │   │
│  │      UI      │◄──►│  /ingest  │  /draft  │  /feedback       │   │
│  └──────────────┘    └─────────────────────────────────────────┘   │
│                                    │                                │
│            ┌───────────────────────┼───────────────────────┐        │
│            ▼                       ▼                       ▼        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │    INGESTION     │  │    RETRIEVAL     │  │    FEEDBACK      │  │
│  │ • File routing   │  │ • Text chunking  │  │ • Edit capture   │  │
│  │ • OCR pipeline   │  │ • Embedding      │  │ • Diff analysis  │  │
│  │ • Text extract   │  │ • ChromaDB       │  │ • Rule learning  │  │
│  │ • Structuring    │  │ • Coverage map   │  │ • Pref. store    │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
│           └──────────────┬──────┘                     │             │
│                          ▼                             │             │
│               ┌──────────────────┐                    │             │
│               │  DRAFT GENERATOR │◄───────────────────┘             │
│               │ • Prompt builder │                                  │
│               │ • Claude API     │                                  │
│               │ • Citation linker│                                  │
│               └──────────────────┘                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │    ChromaDB (vectors)  │  SQLite (edits, rules, metadata)    │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Overview

**Document Ingestion** — Accepts PDFs (native & scanned), images, and text files. Uses pytesseract with OpenCV preprocessing for OCR. Applies pdfplumber for native PDFs. Extracts structured fields via regex + LLM two-pass approach.

**Retrieval & Grounding** — Chunks documents by page boundaries using RecursiveCharacterTextSplitter. Embeds with sentence-transformers (all-MiniLM-L6-v2, 384-dim). Indexes in ChromaDB per-document and globally. Builds coverage maps linking citation labels to source chunks.

**Draft Generation** — Assembles prompts with evidence passages, structured fields, and learned preferences. Calls Claude via OpenRouter. Post-processes citations to link `[N]` tags to source evidence.

**Feedback Loop** — Captures operator edits. Sends to LLM for semantic diff analysis (not line diffs). Extracts reusable rules. Deduplicates via embedding cosine similarity (threshold 0.85). Injects confirmed rules into future prompts.

## The Feedback Loop

1. Operator generates a draft via `/draft`
2. Operator edits the draft and submits via `/feedback`
3. System sends original + edited to LLM for semantic diff → extracts rules
4. Rules are deduplicated against existing rules (cosine similarity > 0.85)
5. New rules get `frequency=1`; duplicates increment existing rule frequency
6. On next draft generation, rules with `frequency >= 1` are injected into the prompt
7. Rules with `frequency >= 3` (confirmed) get priority marker ★

## Evaluation Results

### Retrieval Quality
| Metric | Score | Target |
|--------|-------|--------|
| Precision@3 | TBD | ≥ 0.80 |
| Recall@3 | TBD | — |
| MRR | TBD | ≥ 0.75 |

### Grounding Quality
| Metric | Score | Target |
|--------|-------|--------|
| Citation Coverage | TBD | ≥ 85% |

### Feedback Loop
| Metric | Value |
|--------|-------|
| Edit sessions processed | TBD |
| Rules extracted | TBD |
| Rules applied in next draft | TBD |

*Run `python scripts/demo_feedback_loop.py` and evaluation scripts to fill these.*

## Sample Documents

| File | Type | Description |
|------|------|-------------|
| contract_scan.pdf | Scanned PDF | 4-page service agreement (Acme Corp v. Globex LLC) |
| notice_typed.pdf | Native PDF | Legal notice of breach (Hartman & Associates) |
| case_filing.pdf | Native PDF | Court motion with mixed formatting |
| handwritten_notes.png | Image | Simulated handwritten case notes |
| edited_draft_sample.txt | Text | Pre-written operator edit for demo |

## Assumptions & Tradeoffs

- **Why OpenRouter over direct Anthropic**: Flexible model routing, single API key for multiple providers
- **Why ChromaDB over Pinecone**: Local-only requirement, no external services, simpler deployment
- **Why sentence-transformers over OpenAI embeddings**: Free, local, no API dependency, 384-dim is sufficient
- **Why Case Fact Summary as draft type**: Clearly scoped, demonstrably grounded, directly useful for legal workflows
- **Why SQLite over PostgreSQL**: Assessment scope is single-user, no multi-tenant needed
- **Handling low-confidence OCR**: Flagged but never dropped — propagated through chunks to citations
- **What "grounded" means**: Every factual claim must cite a source evidence passage via `[N]` tags

## Known Limitations

- OCR accuracy depends on Tesseract quality for handwritten/poor scans
- Cross-document retrieval not demonstrated in demo (but supported via global collection)
- Only one draft type implemented (case_fact_summary) — extensible via draft_types module
- No authentication or multi-user support
- Large documents (>20 pages) are truncated

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/ingest` | Upload and process a document |
| POST | `/api/v1/draft` | Generate a grounded draft |
| POST | `/api/v1/feedback` | Submit operator edit for learning |
| GET | `/api/v1/documents` | List indexed documents |
| GET | `/api/v1/preferences/{type}` | Get learned preferences |
| GET | `/api/v1/health` | Health check |
