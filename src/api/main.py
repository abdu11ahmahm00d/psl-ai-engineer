"""
FastAPI endpoints for PSL Document Intelligence API.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pathlib import Path
import shutil
import uuid
import json
import os
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.feedback.edit_capture import OperatorEdit, EditPatternExtractor, PatternStore
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="PSL Document Intelligence API", version="1.0.0")
UPLOAD_DIR = Path(os.environ.get("DOCS_DIR", "D:/psl-ai-engineer/docs"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/ingest")
async def ingest_document(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """Upload and fully process a document."""
    doc_id = str(uuid.uuid4())[:8]
    dest = UPLOAD_DIR / f"{doc_id}_{file.filename}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    if background_tasks:
        from src.pipeline import process
        background_tasks.add_task(process, dest)
        return {"doc_id": doc_id, "file": str(dest), "status": "queued"}
    else:
        from src.pipeline import process
        process(dest)
        return {"doc_id": doc_id, "file": str(dest), "status": "processed"}


@app.get("/draft/{doc_id}")
async def get_draft(doc_id: str):
    """Retrieve the latest draft for a document."""
    drafts_dir = Path(os.environ.get("DRAFTS_DIR", "D:/psl-ai-engineer/drafts"))
    drafts = sorted(drafts_dir.glob(f"*{doc_id}*.json"))
    if not drafts:
        raise HTTPException(404, "No draft found for this doc_id")
    return JSONResponse(content=json.loads(drafts[-1].read_text()))


@app.post("/edit")
async def submit_edit(payload: dict):
    """Submit an operator edit to trigger learning."""
    edit = OperatorEdit(
        edit_id=str(uuid.uuid4())[:8],
        document_name=payload["doc_id"],
        draft_version=payload.get("draft_version", "unknown"),
        section_edited=payload["section"],
        original_text=payload["original"],
        edited_text=payload["edited"],
        operator_note=payload.get("note"),
    )
    edits_dir = Path(os.environ.get("EDITS_DIR", "D:/psl-ai-engineer/edits"))
    edits_dir.mkdir(exist_ok=True)
    (edits_dir / f"{edit.edit_id}.json").write_text(edit.model_dump_json(indent=2))

    ps = PatternStore()
    ep = EditPatternExtractor()
    pattern = ep.extract_pattern(edit)
    if pattern:
        ps.save_pattern(pattern)
    return {"edit_captured": True, "pattern_learned": pattern is not None, "pattern": pattern}


@app.get("/patterns")
async def list_patterns():
    """List all learned patterns."""
    return {"patterns": PatternStore().load_all()}
