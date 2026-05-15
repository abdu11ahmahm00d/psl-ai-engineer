"""
Evaluation metrics for the full pipeline.
Run: uv run python tests/evaluate.py
"""
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

EVALUATION_CRITERIA = {
    "document_processing": {
        "ocr_coverage": "% of pages with >50 words extracted",
        "field_extraction_accuracy": "Manually verify 5 key fields per document",
        "processing_time": "Seconds per page",
        "noise_handling": "Does it process high-noise docs without crashing?",
    },
    "retrieval_grounding": {
        "relevance_at_k": "Are top-5 chunks relevant to the query?",
        "evidence_traceability": "Can every draft claim be traced to a chunk?",
        "hallucination_rate": "% of draft claims NOT present in source",
    },
    "draft_quality": {
        "structure_score": "1-5: Is the draft well-structured?",
        "citation_completeness": "% of claims with [SOURCE:] tags",
        "usefulness": "1-5: Could an operator use this as a first pass?",
    },
    "improvement_loop": {
        "pattern_extraction_rate": "% of edits that yield a reusable pattern",
        "pattern_application": "Are patterns correctly injected into next draft?",
        "draft_improvement": "Side-by-side quality score before/after 5 edits",
    },
}


def run_evaluation():
    base = Path(os.environ.get("BASE_DIR", "D:/psl-ai-engineer"))
    sample_dir = base / "sample_inputs"
    results = {}

    print("=" * 60)
    print("PSL AI Engineer — Pipeline Evaluation")
    print("=" * 60)

    samples = list(sample_dir.glob("*.pdf"))
    print(f"\n[1] Sample documents found: {len(samples)}")
    for s in samples:
        print(f"    - {s.name}")

    try:
        from src.ocr.engine import OCREngine
        print("\n[2] OCR Engine: OK - Import successful")
    except Exception as e:
        print(f"\n[2] OCR Engine: FAIL - {e}")
        return

    try:
        from src.extraction.extractor import StructuredExtractor
        print("[3] Structured Extractor: OK - Import successful")
    except Exception as e:
        print(f"[3] Structured Extractor: FAIL - {e}")

    try:
        from src.retrieval.store import DocumentVectorStore, chunk_document
        print("[4] Vector Store: OK - Import successful")
    except Exception as e:
        print(f"[4] Vector Store: FAIL - {e}")

    try:
        from src.generation.drafter import DraftGenerator
        print("[5] Draft Generator: OK - Import successful")
    except Exception as e:
        print(f"[5] Draft Generator: FAIL - {e}")

    try:
        from src.feedback.edit_capture import PatternStore, EditPatternExtractor
        print("[6] Edit Capture: OK - Import successful")
    except Exception as e:
        print(f"[6] Edit Capture: FAIL - {e}")

    try:
        from src.pipeline import process
        print("[7] Pipeline: OK - Import successful")
    except Exception as e:
        print(f"[7] Pipeline: FAIL - {e}")

    try:
        from src.api.main import app
        print("[8] FastAPI: OK - Import successful")
    except Exception as e:
        print(f"[8] FastAPI: FAIL - {e}")

    print("\n" + "=" * 60)
    print("EVALUATION CRITERIA (manual scoring needed):")
    print("=" * 60)
    print(json.dumps(EVALUATION_CRITERIA, indent=2))
    print("\n[INFO] Run each test document through pipeline.py and record results above.")


if __name__ == "__main__":
    run_evaluation()
