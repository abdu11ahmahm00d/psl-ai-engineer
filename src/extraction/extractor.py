"""
Structured Field Extraction — Gemini-powered legal document analyzer.
Extracts parties, dates, case numbers, key facts, obligations, etc.
"""
import os
import re
import json
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


class LegalDocumentFields(BaseModel):
    document_type: Optional[str] = Field(None, description="e.g. contract, notice, deposition, motion")
    parties: List[str] = Field(default_factory=list, description="All named parties")
    dates: List[str] = Field(default_factory=list, description="All dates mentioned")
    case_number: Optional[str] = None
    jurisdiction: Optional[str] = None
    key_facts: List[str] = Field(default_factory=list, description="Core factual claims")
    obligations: List[str] = Field(default_factory=list, description="Legal obligations mentioned")
    amounts: List[str] = Field(default_factory=list, description="Monetary amounts")
    deadlines: List[str] = Field(default_factory=list, description="Deadlines or time limits")
    signatures: List[str] = Field(default_factory=list, description="Signatories found")
    confidence_notes: List[str] = Field(default_factory=list, description="Uncertain or illegible fields")


def _extract_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()
    candidates = []
    for match in re.finditer(r'\{', text):
        start = match.start()
        brace_count = 0
        in_string = False
        escape_next = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape_next:
                escape_next = False
                continue
            if ch == '\\':
                escape_next = True
                continue
            if ch == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == '{':
                brace_count += 1
            elif ch == '}':
                brace_count -= 1
                if brace_count == 0:
                    candidates.append(text[start:i+1])
                    break
    if candidates:
        return max(candidates, key=len)
    return text


class StructuredExtractor:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemma-4-26b-a4b-it")

    def extract(self, document_text: str, source_file: str) -> LegalDocumentFields:
        schema_json = json.dumps(LegalDocumentFields.model_json_schema(), indent=2)

        prompt = f"""You are a legal document analyst. Extract structured fields from the following document text.
Return ONLY valid JSON matching this schema. Do NOT include any text before or after the JSON.

SCHEMA:
{schema_json}

CRITICAL RULES:
- Only extract what is explicitly present in the text.
- If a field is unclear or partially illegible, note it in confidence_notes.
- Never invent or infer information not present.
- For partially legible text, include what you can read with [ILLEGIBLE] markers.
- If a list field has no values, return an empty array [].

DOCUMENT TEXT:
{document_text[:12000]}
"""
        response = self.model.generate_content(prompt)
        raw = _extract_json(response.text)

        return LegalDocumentFields(**json.loads(raw))

    def save(self, fields: LegalDocumentFields, source_file: str, output_dir: Path):
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(source_file).stem
        out = output_dir / f"{stem}_fields.json"
        out.write_text(fields.model_dump_json(indent=2))
        return out
