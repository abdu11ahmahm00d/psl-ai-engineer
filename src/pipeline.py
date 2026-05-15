"""
Main pipeline orchestrator. Ties all phases together.
Usage: uv run python src/pipeline.py --input docs/sample.pdf
"""
import sys
import os
import json
import uuid
from pathlib import Path
import typer
from rich.console import Console
from rich.progress import track
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ocr.engine import OCREngine
from src.extraction.extractor import StructuredExtractor
from src.retrieval.store import DocumentVectorStore, chunk_document
from src.generation.drafter import DraftGenerator
from src.feedback.edit_capture import PatternStore, OperatorEdit, EditPatternExtractor

app = typer.Typer()
console = Console()


@app.command()
def process(
    input_path: Path = typer.Argument(..., help="Path to input document (PDF or image)"),
    draft_only: bool = typer.Option(False, help="Skip re-indexing, just generate draft"),
    interactive_edit: bool = typer.Option(False, help="Prompt for operator edit after draft"),
):
    base = Path(os.environ.get("BASE_DIR", "D:/psl-ai-engineer"))
    processed_dir = base / "processed"
    drafts_dir = base / "drafts"

    console.rule("[bold blue]PHASE 1: Document Processing")
    engine = OCREngine(backend="auto")
    doc_result = engine.process_file(input_path, processed_dir)
    console.print(f"[green]✓ Extracted {doc_result.total_pages} pages via {doc_result.extraction_method}")
    if doc_result.warnings:
        for w in doc_result.warnings:
            console.print(f"[yellow]⚠ {w}")

    console.rule("[bold blue]PHASE 2: Structured Extraction")
    extractor = StructuredExtractor()
    fields = extractor.extract(doc_result.full_text(), str(input_path))
    extractor.save(fields, str(input_path), processed_dir)
    console.print(f"[green]✓ Extracted {len(fields.parties)} parties, {len(fields.key_facts)} key facts")

    if not draft_only:
        console.rule("[bold blue]PHASE 3: Indexing for Retrieval")
        store = DocumentVectorStore()
        for page in track(doc_result.pages, description="Chunking & indexing..."):
            chunks = chunk_document(page.raw_text, str(input_path), page.page_num)
            store.add_chunks(chunks)
        console.print(f"[green]✓ Indexed {doc_result.total_pages} pages into vector store")

    console.rule("[bold blue]PHASE 4: Draft Generation")
    store = DocumentVectorStore()
    query = f"key facts parties obligations deadlines {' '.join(fields.parties[:3])}"
    retrieved = store.retrieve(query, top_k=10)

    pattern_store = PatternStore()
    patterns = pattern_store.load_all()

    generator = DraftGenerator()
    draft = generator.generate(
        retrieved_chunks=retrieved,
        structured_fields=fields.model_dump(),
        document_name=input_path.name,
        edit_patterns=patterns,
    )
    draft_path = generator.save(draft, drafts_dir, input_path.stem)
    console.print(f"[green]✓ Draft saved → {draft_path}")
    console.print_json(json.dumps(draft, indent=2))

    if interactive_edit:
        _handle_operator_edit(draft, input_path.name, str(draft_path), pattern_store)


def _handle_operator_edit(draft: dict, doc_name: str, draft_version: str, pattern_store: PatternStore):
    """CLI-based operator edit capture for the feedback loop."""
    console.rule("[bold magenta]PHASE 5: Operator Edit Capture")
    section = typer.prompt("Which section are you editing? (e.g. key_facts, timeline)")
    original = json.dumps(draft.get(section, ""), indent=2)
    console.print(f"[dim]Original:\n{original}")
    edited = typer.prompt("Paste your edited version")
    note = typer.prompt("Any note about why you made this change? (Enter to skip)", default="")

    edit = OperatorEdit(
        edit_id=str(uuid.uuid4())[:8],
        document_name=doc_name,
        draft_version=draft_version,
        section_edited=section,
        original_text=original,
        edited_text=edited,
        operator_note=note or None,
    )

    edits_dir = Path(os.environ.get("EDITS_DIR", "D:/psl-ai-engineer/edits"))
    edits_dir.mkdir(exist_ok=True)
    (edits_dir / f"{edit.edit_id}.json").write_text(edit.model_dump_json(indent=2))

    extractor = EditPatternExtractor()
    pattern = extractor.extract_pattern(edit)
    if pattern:
        pattern_store.save_pattern(pattern)
        console.print(f"[green]✓ Pattern learned: {pattern['description']}")
    else:
        console.print("[dim]Edit was document-specific — no generalizable pattern extracted")


if __name__ == "__main__":
    app()
