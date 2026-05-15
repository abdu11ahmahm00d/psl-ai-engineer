"""
Operator Edit Capture & Learning Loop — Extracts reusable patterns from edits.
"""
import os
import json
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


class OperatorEdit(BaseModel):
    edit_id: str
    document_name: str
    draft_version: str
    section_edited: str
    original_text: str
    edited_text: str
    operator_note: Optional[str] = None
    timestamp: str = datetime.utcnow().isoformat()


class EditPatternExtractor:
    """Uses Gemini to analyze operator edits and extract reusable generation preferences."""

    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    def extract_pattern(self, edit: OperatorEdit) -> Optional[dict]:
        prompt = f"""An operator edited a legal draft. Analyze the edit and extract a reusable drafting pattern.

SECTION EDITED: {edit.section_edited}
ORIGINAL TEXT:
{edit.original_text}

EDITED TO:
{edit.edited_text}

OPERATOR NOTE: {edit.operator_note or "None provided"}

Return JSON with:
{{
  "pattern_type": "tone" | "structure" | "inclusion" | "exclusion" | "format" | "citation",
  "description": "<concise, reusable instruction for future drafts>",
  "applies_to": "<which section or globally>",
  "confidence": 0.0-1.0
}}

Only return a pattern if the edit reveals a clear, generalizable preference.
If the edit is document-specific and not generalizable, return {{"pattern_type": "skip"}}.
Return ONLY valid JSON."""

        response = self.model.generate_content(prompt)
        raw = response.text.strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            result = json.loads(raw)
            if result.get("pattern_type") == "skip":
                return None
            return result
        except Exception:
            return None


class PatternStore:
    """Persists and retrieves learned patterns. Patterns are loaded into each new draft generation."""

    def __init__(self, store_dir: Path = None):
        self.store_dir = store_dir or Path(os.environ.get("EDIT_PATTERNS_DIR", "D:/psl-ai-engineer/edit_patterns"))
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.patterns_file = self.store_dir / "patterns.json"

    def save_pattern(self, pattern: dict):
        patterns = self.load_all()
        pattern["id"] = f"pat_{len(patterns)+1:04d}"
        pattern["created_at"] = datetime.utcnow().isoformat()
        patterns.append(pattern)
        self.patterns_file.write_text(json.dumps(patterns, indent=2))

    def load_all(self) -> list[dict]:
        if not self.patterns_file.exists():
            return []
        return json.loads(self.patterns_file.read_text())

    def load_for_section(self, section: str) -> list[dict]:
        all_patterns = self.load_all()
        return [p for p in all_patterns if p.get("applies_to") in (section, "global", "all")]

    def prune_low_confidence(self, threshold: float = 0.5):
        patterns = [p for p in self.load_all() if p.get("confidence", 1.0) >= threshold]
        self.patterns_file.write_text(json.dumps(patterns, indent=2))
