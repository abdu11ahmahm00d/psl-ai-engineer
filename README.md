# Pearson Specter Litt — Document Intelligence Pipeline

An agentic document processing pipeline for legal document analysis. Processes PDFs and images through OCR, structured field extraction, vector retrieval, and grounded draft generation with a continuous learning loop from operator edits.

## Overview

This system ingests legal documents (contracts, notices, depositions, motions) and produces structured, cited case fact summaries. It uses a tiered OCR engine (PyMuPDF → EasyOCR → Gemini 2.0 Flash), Gemini-powered structured extraction and draft generation, ChromaDB for semantic retrieval, and an edit-capture learning loop that extracts reusable drafting patterns from operator corrections.

## Prerequisites

- Python 3.11+
- `uv` package manager
- CUDA 11.8 (optional, for GPU acceleration)
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

## Evaluation

Run the evaluation script:
```bash
uv run python tests/evaluate.py
```

| Criteria | Metric | Status |
|---|---|---|
| OCR Coverage | % pages with >50 words | TBD |
| Field Accuracy | Manual verification | TBD |
| Retrieval Relevance | Top-5 relevance | TBD |
| Citation Completeness | % claims with [SOURCE:] | TBD |
| Pattern Extraction | % edits → patterns | TBD |
