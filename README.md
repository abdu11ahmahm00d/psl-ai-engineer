# Pearson Specter Litt — Document Intelligence Pipeline

An agentic document processing pipeline for legal document analysis. Processes PDFs and images through OCR, structured field extraction, vector retrieval, and grounded draft generation with a continuous learning loop from operator edits.

## Overview

This system ingests legal documents (contracts, notices, depositions, motions) and produces structured, cited case fact summaries. It uses a tiered OCR engine (PyMuPDF → EasyOCR → Gemma-4-26b multimodal), Gemma-4-26b-a4b-it-powered structured extraction and draft generation, ChromaDB for semantic retrieval, and an edit-capture learning loop that extracts reusable drafting patterns from operator corrections.

## Prerequisites

- Python 3.11+
- `uv` package manager
- `GEMINI_API_KEY` set in `.env`

## Setup

```bash
cd D:\psl-ai-engineer
uv sync
```

Create `.env` with:
```
GEMINI_API_KEY=your_key_here
BASE_DIR=D:\psl-ai-engineer
```

## Running the Pipeline

```bash
# Process a document end-to-end
uv run python src/pipeline.py docs/sample.pdf

# Generate draft only (skip re-indexing)
uv run python src/pipeline.py docs/sample.pdf --draft-only

# Interactive edit mode (captures patterns)
uv run python src/pipeline.py docs/sample.pdf --interactive-edit
```

## Running the API

```bash
uv run uvicorn src.api.main:app --reload --port 8000
```

Endpoints:
- `POST /ingest` — Upload and process a document
- `GET /draft/{doc_id}` — Retrieve latest draft
- `POST /edit` — Submit operator edit for pattern learning
- `GET /patterns` — List all learned patterns

## Sample Inputs

Generate synthetic test documents:
```bash
uv run python sample_inputs/generate_samples.py
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system diagram and component details.

## Evaluation Results

All 3 sample documents processed end-to-end successfully.

| Criteria | Metric | Result |
|---|---|---|
| OCR Coverage | % pages with >50 words | 100% (3/3) |
| Field Extraction | Parties detected | 6/6 correct |
| Processing Time | Seconds per page | ~60s (Gemma-4-26b) |
| Noise Handling | Processes without crashing | Pass |
| Retrieval Relevance | Top-5 chunks relevant | Pass |
| Citation Completeness | % claims with [SOURCE:] | 100% |
| Draft Structure | Well-structured JSON | Pass (3/3) |
| Pattern Injection | Learned patterns applied | Pass (3 patterns) |

## Assumptions & Tradeoffs

| Decision | Approach | Rationale |
|---|---|---|
| LLM | Gemma-4-26b-a4b-it via Gemini API | Strong reasoning, JSON output, available on free tier |
| OCR Fallback | EasyOCR (CPU) + Gemma multimodal | No GPU torch needed; cloud handles complex scans |
| Embeddings | BAAI/bge-base-en-v1.5 | Fits in CPU memory, strong retrieval |
| Vector store | ChromaDB local persistent | Zero infrastructure, fast enough for scale |
| Chunk size | 800 chars / 150 overlap | Legal context needs larger chunks |
| Edit learning | LLM-extracted patterns | Generalizable across documents |
| Caching | SHA-256 hash per file | Avoids re-processing same document |
