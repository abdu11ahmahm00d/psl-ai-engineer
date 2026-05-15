# PSL Document Intelligence — Architecture

## System Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    INPUT LAYER                          │
│   PDFs / Images / Scans                                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           PHASE 1: OCR ENGINE                           │
│  PyMuPDF (native) → EasyOCR (CPU) → Gemma-4-26b         │
│  Output: DocumentResult (raw text + confidence)         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           PHASE 2: STRUCTURED EXTRACTION                │
│   Gemma-4-26b-a4b-it → LegalDocumentFields (Pydantic)   │
│   Cached as JSON per document hash                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           PHASE 3: VECTOR STORE (ChromaDB)              │
│   BGE-base embeddings → Cosine similarity               │
│   Persistent on D:\psl-ai-engineer\vectorstore\         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           PHASE 4: DRAFT GENERATION                     │
│   Retrieved chunks + Structured fields                  │
│   + Learned patterns → Gemma-4-26b → Grounded Draft     │
│   Every claim cited with [SOURCE: file, Page N]         │
└────────────────────┬────────────────────────────────────┘
                     │
              Operator reviews
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           PHASE 5: EDIT CAPTURE & LEARNING              │
│   Raw edit saved → Pattern extracted via Gemma-4-26b    │
│   Pattern stored in edit_patterns/patterns.json         │
│   Injected into next draft generation prompt            │
└─────────────────────────────────────────────────────────┘
```

## Components

### OCR Engine (`src/ocr/engine.py`)
Three-tier fallback strategy:
1. **PyMuPDF native** — instant text extraction for digital PDFs
2. **EasyOCR (CPU)** — local OCR for standard scans
3. **Gemma-4-26b-a4b-it multimodal** — cloud-based for noisy/handwritten docs

### Structured Extractor (`src/extraction/extractor.py`)
Uses Gemma-4-26b-a4b-it to extract legal document fields into a Pydantic schema: parties, dates, case numbers, key facts, obligations, amounts, deadlines. Robust JSON extraction handles chain-of-thought output.

### Vector Store (`src/retrieval/store.py`)
Chunks documents with 800-char / 150-overlap strategy. Embeds with BGE-base (CPU). Stores in ChromaDB persistent client for cosine similarity retrieval.

### Draft Generator (`src/generation/drafter.py`)
Generates grounded case fact summaries. Every claim cites `[SOURCE: file, Page N]`. Injects learned patterns from prior operator edits. Robust JSON extraction for Gemma's verbose output style.

### Edit Capture (`src/feedback/edit_capture.py`)
Captures operator edits, uses Gemma-4-26b to extract reusable drafting patterns, stores them for future draft generation.

## Key Tradeoffs

| Decision | Approach | Rationale |
|---|---|---|
| LLM | Gemma-4-26b-a4b-it | Strong reasoning, available via Gemini API free tier |
| Embeddings | BAAI/bge-base-en-v1.5 | CPU-compatible, strong retrieval |
| Vector store | ChromaDB local | No infrastructure needed |
| Chunk size | 800 / 150 overlap | Legal context needs larger chunks |
| Edit learning | LLM-extracted patterns | Generalizable, not just diffs |
| OCR fallback | Gemma-4-26b multimodal | Strong on noisy/handwritten docs |
| Caching | SHA-256 hash per file | Avoid re-processing |
| JSON parsing | Brace-matching + longest candidate | Handles Gemma's chain-of-thought output |
