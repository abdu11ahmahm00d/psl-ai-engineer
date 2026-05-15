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
│  PyMuPDF (native) → EasyOCR (GPU) → Gemini 2.0 Flash    │
│  Output: DocumentResult (raw text + confidence)         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           PHASE 2: STRUCTURED EXTRACTION                │
│   Gemini 2.0 Flash → LegalDocumentFields (Pydantic)     │
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
│   + Learned patterns → Gemini → Grounded Draft          │
│   Every claim cited with [SOURCE: file, Page N]         │
└────────────────────┬────────────────────────────────────┘
                     │
              Operator reviews
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           PHASE 5: EDIT CAPTURE & LEARNING              │
│   Raw edit saved → Pattern extracted via Gemini         │
│   Pattern stored in edit_patterns/patterns.json         │
│   Injected into next draft generation prompt            │
└─────────────────────────────────────────────────────────┘
```

## Components

### OCR Engine (`src/ocr/engine.py`)
Three-tier fallback strategy:
1. **PyMuPDF native** — instant text extraction for digital PDFs
2. **EasyOCR** — GPU-accelerated local OCR for standard scans
3. **Gemini 2.0 Flash** — cloud multimodal for noisy/handwritten docs

### Structured Extractor (`src/extraction/extractor.py`)
Uses Gemini 2.0 Flash to extract legal document fields into a Pydantic schema: parties, dates, case numbers, key facts, obligations, amounts, deadlines.

### Vector Store (`src/retrieval/store.py`)
Chunks documents with 800-char / 150-overlap strategy. Embeds with BGE-base (runs on GPU if available). Stores in ChromaDB persistent client for cosine similarity retrieval.

### Draft Generator (`src/generation/drafter.py`)
Generates grounded case fact summaries. Every claim cites `[SOURCE: file, Page N]`. Injects learned patterns from prior operator edits.

### Edit Capture (`src/feedback/edit_capture.py`)
Captures operator edits, uses Gemini to extract reusable drafting patterns, stores them for future draft generation.

## Key Tradeoffs

| Decision | Approach | Rationale |
|---|---|---|
| LLM | Gemini 2.0 Flash | Consistent across all phases, multimodal fallback |
| Embeddings | BAAI/bge-base-en-v1.5 | Fits 8GB VRAM, strong retrieval |
| Vector store | ChromaDB local | No infrastructure needed |
| Chunk size | 800 / 150 overlap | Legal context needs larger chunks |
| Edit learning | LLM-extracted patterns | Generalizable, not just diffs |
| OCR fallback | Gemini 2.0 Flash | Strong on noisy/handwritten docs |
| Caching | SHA-256 hash per file | Avoid re-processing |
