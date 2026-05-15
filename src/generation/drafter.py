"""
Draft Generation — Gemini-powered grounded case fact summary generator.
"""
import os
import re
import json
from pathlib import Path
from datetime import datetime
from google import genai
from dotenv import load_dotenv

load_dotenv()


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


DRAFT_SYSTEM_PROMPT = """You are a senior legal analyst at Pearson Specter Litt preparing internal case fact summaries.

STRICT RULES:
1. Every factual claim MUST cite its source using [SOURCE: <filename>, Page <N>] format.
2. If a fact is uncertain or partially illegible, flag it with [UNCERTAIN].
3. Do NOT add any information not present in the provided evidence.
4. If the evidence is insufficient to support a section, write "Insufficient evidence in provided documents."
5. Never speculate. Never hallucinate. Ground everything.

OUTPUT FORMAT:
Return a structured JSON with keys: title, parties, key_facts, timeline, obligations, open_questions, evidence_map"""


class DraftGenerator:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        self.client = genai.Client(api_key=api_key)
        self.model = "gemma-4-26b-a4b-it"

    def generate(
        self,
        retrieved_chunks: list[dict],
        structured_fields: dict,
        document_name: str,
        edit_patterns: list[dict] = None
    ) -> dict:
        evidence_block = self._format_evidence(retrieved_chunks)
        pattern_block = self._format_patterns(edit_patterns or [])

        user_prompt = f"""Generate a Case Fact Summary for the following document.

STRUCTURED FIELDS EXTRACTED:
{json.dumps(structured_fields, indent=2)}

RETRIEVED EVIDENCE PASSAGES:
{evidence_block}

{pattern_block}

Document name: {document_name}

Return ONLY valid JSON. No markdown fences."""

        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
        )
        raw = _extract_json(response.text)
        try:
            draft = json.loads(raw)
        except json.JSONDecodeError:
            draft = {"raw_text": response.text, "parse_error": True}

        draft["_meta"] = {
            "generated_at": datetime.utcnow().isoformat(),
            "source_document": document_name,
            "evidence_chunks_used": len(retrieved_chunks),
            "edit_patterns_applied": len(edit_patterns or [])
        }
        return draft

    def _format_evidence(self, chunks: list[dict]) -> str:
        lines = []
        for i, c in enumerate(chunks):
            src = c["metadata"].get("source", "unknown")
            pg = c["metadata"].get("page", "?")
            lines.append(f"[EVIDENCE {i+1}] Source: {src}, Page {pg}\n{c['text']}\n")
        return "\n".join(lines)

    def _format_patterns(self, patterns: list[dict]) -> str:
        if not patterns:
            return ""
        block = "LEARNED PATTERNS FROM PRIOR OPERATOR EDITS (apply these preferences):\n"
        for p in patterns:
            block += f"- {p['description']}\n"
        return block

    def save(self, draft: dict, output_dir: Path, stem: str) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out = output_dir / f"{stem}_draft_{ts}.json"
        out.write_text(json.dumps(draft, indent=2))
        return out
