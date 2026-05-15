# Best Practices — Lessons Learned

> **Format**: "Do this instead of that" — each lesson captures a mistake we made, the fix, and why it matters.
> Feed this file into future projects to avoid repeating the same stumbles.

---

## Package Management

### Do use `uv` instead of `pip` for Python dependency management
**Instead of:** `pip install package1 package2`
**Do:** `uv add package1 package2` then `uv sync`

**Why:** `uv` is 10-100x faster than pip, resolves dependencies deterministically, produces a lockfile (`uv.lock`), and handles virtual environments automatically. Never use `pip` in a `uv` project — it bypasses the lockfile and creates conflicts.

---

### Do remove `.venv` and recreate instead of trying to fix a broken venv
**Instead of:** Manually deleting individual files from `.venv/` when sync fails
**Do:** `Remove-Item -LiteralPath .venv -Recurse -Force; uv sync`

**Why:** Windows file locks, symlink issues, and partial installs corrupt the venv in ways that are hard to debug. A clean rebuild is always faster.

---

### Do use CPU torch instead of CUDA torch unless GPU is critical
**Instead of:** `uv add torch --index-url https://download.pytorch.org/whl/cu118` (2.6 GB download)
**Do:** `uv add torch --index-url https://download.pytorch.org/whl/cpu` (117 MB download)

**Why:** The CUDA wheel is 22x larger and takes 10+ minutes to download. For embedding models (BGE-base) and lightweight inference, CPU is fine. Only use CUDA if you're running local LLMs or heavy training.

---

## SDK & Library Imports

### Do use `google.genai` instead of `google.generativeai`
**Instead of:** `import google.generativeai as genai` then `genai.GenerativeModel("model-name")`
**Do:** `from google import genai` then `genai.Client(api_key=key).models.generate_content(model="model-name", contents=prompt)`

**Why:** `google.generativeai` is deprecated and emits a `FutureWarning` on every import. It will stop receiving updates. The new `google.genai` package has a cleaner API with explicit `Client` objects.

---

### Do use `langchain_text_splitters` instead of `langchain.text_splitter`
**Instead of:** `from langchain.text_splitter import RecursiveCharacterTextSplitter`
**Do:** `from langchain_text_splitters import RecursiveCharacterTextSplitter`

**Why:** LangChain split its monolithic package into smaller subpackages. `langchain.text_splitter` no longer exists in newer versions. The functionality moved to `langchain-text-splitters`.

---

### Do install `python-multipart` when using FastAPI file uploads
**Instead of:** Assuming FastAPI handles `UploadFile` out of the box
**Do:** `uv add python-multipart`

**Why:** FastAPI requires `python-multipart` for form data and file upload parsing. Without it, any endpoint using `UploadFile = File(...)` crashes at import time with a cryptic `RuntimeError`.

---

## JSON Parsing from LLMs

### Do use brace-matching to extract JSON instead of simple prefix/suffix stripping
**Instead of:** `text.removeprefix("```json").removesuffix("```").strip()`
**Do:** Scan for `{`, track brace depth while respecting string boundaries, collect all complete JSON objects, return the longest one

**Why:** Models like Gemma-4-26b output chain-of-thought reasoning before the JSON. Simple prefix stripping leaves conversational text that breaks `json.loads()`. The brace-matching approach finds the actual JSON regardless of what surrounds it.

**Reusable function:**
```python
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
```

---

### Do set `response_format={"type": "json_object"}` when the API supports it
**Instead of:** Relying solely on prompt instructions like "Return ONLY valid JSON"
**Do:** Use the API's native JSON mode when available, combined with brace-matching as a safety net

**Why:** Prompt instructions are often ignored by larger reasoning models. Native JSON mode forces structured output. When not available (like with some models via Gemini API), brace-matching is the fallback.

---

## Windows-Specific Issues

### Do set `PYTHONIOENCODING=utf-8` before running Python scripts on Windows
**Instead of:** Assuming Python uses UTF-8 on Windows
**Do:** `$env:PYTHONIOENCODING="utf-8"; python script.py`

**Why:** Windows PowerShell defaults to cp1252 encoding. Any unicode characters in output (progress bars, checkmarks, emoji) cause `UnicodeEncodeError: 'charmap' codec can't encode character`.

---

### Do disable EasyOCR verbose mode on Windows
**Instead of:** `easyocr.Reader(['en'], gpu=True)` (default verbose=True)
**Do:** `easyocr.Reader(['en'], gpu=False, verbose=False)`

**Why:** EasyOCR's progress bar uses unicode block characters (`█`) that break on Windows cp1252 console encoding. Setting `verbose=False` suppresses the progress bar entirely. Also, `gpu=False` avoids CUDA dependency issues when you're using CPU torch.

---

### Do activate Windows Developer Mode for HuggingFace cache symlinks
**Instead of:** Ignoring the "failed to hardlink" warning from `huggingface_hub`
**Do:** Enable Developer Mode in Windows Settings → For Developers → Developer Mode

**Why:** Without symlinks, HuggingFace copies model files instead of linking them, wasting disk space (each model download duplicates ~400MB). The cache degrades to a "full copy" mode that uses significantly more storage.

---

## Dataclass & Serialization

### Do reconstruct dataclass objects when deserializing cached JSON
**Instead of:** `DocumentResult(**json.loads(cache_path.read_text()))`
**Do:** Parse the JSON, then reconstruct nested dataclass objects: `data["pages"] = [PageResult(**p) for p in data["pages"]]` then `DocumentResult(**data)`

**Why:** `json.loads()` returns plain dicts, not dataclass instances. When `DocumentResult.full_text()` tries to access `p.raw_text` on a dict, it raises `AttributeError: 'dict' object has no attribute 'raw_text'`.

---

## Model Selection

### Do use cloud API models instead of local LLMs for prototyping
**Instead of:** Running GLM-4V-9B locally with 4-bit quantization (complex setup, VRAM constraints)
**Do:** Use Gemma-4-26b-a4b-it via Gemini API (zero setup, no VRAM needed)

**Why:** Local LLMs require careful VRAM management, quantization config, and device mapping. Cloud APIs handle all of that server-side. For a project with an 8GB GTX 1080, the API approach is simpler and more reliable.

---

### Do pick a single LLM across all pipeline stages for consistency
**Instead of:** Using Claude for extraction, Gemini for OCR, and GPT for generation
**Do:** Use one model (e.g., Gemma-4-26b-a4b-it) for all text generation stages

**Why:** Fewer API keys to manage, consistent JSON output behavior, simpler error handling, and easier prompt debugging. Switch models only when a stage has unique requirements (e.g., multimodal input for OCR).

---

## Git & Version Control

### Do stage specific files instead of `git add .`
**Instead of:** `git add .` (catches `.venv/`, `__pycache__/`, cache files)
**Do:** `git add src/ tests/ README.md ARCHITECTURE.md sample_inputs/ sample_outputs/`

**Why:** `git add .` picks up virtual environment files, Python cache, and model weights that should never be committed. Always be explicit about what goes into the repo.

---

### Do add a proper `.gitignore` before the first commit
**Instead of:** Committing first and adding `.gitignore` later
**Do:** Create `.gitignore` with `.venv/`, `__pycache__/`, `*.pyc`, `.env`, `vectorstore/`, `processed/`, `drafts/` before any commit

**Why:** Once files are tracked, `.gitignore` won't untrack them. You have to use `git rm --cached` to fix it. Prevent the problem upfront.

---

## Architecture & Pipeline Design

### Do cache OCR results by file hash to avoid re-processing
**Instead of:** Re-running OCR on the same document every time
**Do:** Hash the input file (SHA-256), check if `{hash}.json` exists in the output directory, return cached result if found

**Why:** OCR is the slowest stage (especially with multimodal models). Caching by hash means identical files are instant on subsequent runs. Critical for development iteration speed.

---

### Do use `sys.path.insert()` for clean imports in CLI scripts
**Instead of:** Complex relative imports like `from ...ocr.engine import OCREngine`
**Do:** `sys.path.insert(0, str(Path(__file__).parent.parent))` at the top, then `from src.ocr.engine import OCREngine`

**Why:** Running `python src/pipeline.py` sets the working directory to `src/`, breaking relative imports. Adding the project root to `sys.path` makes all imports work regardless of where the script is invoked from.

---

### Do separate the pipeline into distinct phases with clear interfaces
**Instead of:** One monolithic script that does everything
**Do:** Separate modules: `ocr/engine.py`, `extraction/extractor.py`, `retrieval/store.py`, `generation/drafter.py`, `feedback/edit_capture.py` — each with a clear input/output contract

**Why:** Each phase can be tested independently, swapped out (e.g., change OCR backend without touching extraction), and reused in other projects. The pipeline orchestrator just wires them together.

---

## API Key Management

### Do use `.env` with `python-dotenv` instead of hardcoded keys
**Instead of:** `api_key = "AIzaSy..."` in source code
**Do:** `GEMINI_API_KEY=...` in `.env`, then `load_dotenv()` + `os.environ.get("GEMINI_API_KEY")`

**Why:** Hardcoded keys get committed to git, leaked in screenshots, and are a pain to rotate. `.env` keeps secrets out of source control. Always add `.env` to `.gitignore`.

---

### Do validate API key presence at init time, not at call time
**Instead of:** Checking for the API key inside every method that uses it
**Do:** Check once in `__init__` and raise `ValueError` immediately if missing

**Why:** Failing fast gives a clear error message at startup instead of a cryptic API error deep in the call stack.

---

## Prompt Engineering

### Do include the Pydantic schema directly in the prompt for structured extraction
**Instead of:** Describing the output format in natural language
**Do:** `json.dumps(MyModel.model_json_schema(), indent=2)` embedded in the prompt

**Why:** Models follow JSON schemas more reliably than prose descriptions. The schema is auto-generated from the Pydantic model, so it stays in sync with code changes.

---

### Do add explicit negative constraints to prompts
**Instead of:** "Extract the relevant information from this document"
**Do:** "Only extract what is explicitly present. Never invent or infer. If unclear, note it in confidence_notes."

**Why:** LLMs default to being helpful, which means they fill in gaps with plausible but incorrect information. Explicit negative constraints reduce hallucination in legal/structured contexts.

---

## Testing

### Do test imports before testing functionality
**Instead of:** Running the full pipeline to check if code compiles
**Do:** `python -c "from src.module import Class; print('OK')"` for each module

**Why:** Import errors are caught instantly without waiting for model downloads, API calls, or file processing. Fast feedback loop during development.

---

### Do use synthetic documents for initial testing
**Instead of:** Hunting for real legal documents to test with
**Do:** Generate PDFs programmatically with `reportlab` containing known text, parties, dates, and amounts

**Why:** You know exactly what the output should contain, so you can verify extraction accuracy. Real documents are messy and you don't have ground truth.

---

## File Path Handling

### Do use `pathlib.Path` instead of string concatenation
**Instead of:** `output_dir + "/" + filename` or `os.path.join(dir, file)`
**Do:** `Path(output_dir) / filename`

**Why:** `Path` handles cross-platform separators automatically, provides useful methods (`.exists()`, `.read_text()`, `.mkdir()`), and is more readable.

---

### Do use `os.environ.get()` with defaults for directory paths
**Instead of:** Hardcoding `D:/psl-ai-engineer/processed` everywhere
**Do:** `Path(os.environ.get("PROCESSED_DIR", "D:/psl-ai-engineer/processed"))`

**Why:** Makes the code portable. Different machines can set different base directories via `.env` without changing source code.

---

## Lessons Summary Table

| # | Instead Of | Do This | Impact |
|---|---|---|---|
| 1 | `pip install` | `uv add` + `uv sync` | 10-100x faster installs |
| 2 | Fix broken `.venv` in-place | Delete and recreate | Saves hours of debugging |
| 3 | CUDA torch (2.6 GB) | CPU torch (117 MB) | 22x smaller download |
| 4 | `google.generativeai` | `google.genai` | No deprecation warnings |
| 5 | `langchain.text_splitter` | `langchain_text_splitters` | Works with modern versions |
| 6 | Assume FastAPI handles uploads | Install `python-multipart` | Prevents import crashes |
| 7 | `removeprefix("```json")` | Brace-matching JSON extraction | Handles chain-of-thought output |
| 8 | Default Windows encoding | Set `PYTHONIOENCODING=utf-8` | No UnicodeEncodeError |
| 9 | EasyOCR verbose mode | `verbose=False` | No unicode progress bar crash |
| 10 | Direct `**json.loads()` for dataclasses | Reconstruct nested objects | No AttributeError on cached data |
| 11 | Local LLMs with quantization | Cloud API models | Zero VRAM management |
| 12 | Multiple LLMs across stages | Single LLM everywhere | Simpler debugging |
| 13 | `git add .` | Stage specific files | No accidental venv commits |
| 14 | Re-run OCR every time | Cache by SHA-256 hash | Instant re-runs |
| 15 | Relative imports in CLI | `sys.path.insert()` | Works from any directory |
| 16 | Hardcoded API keys | `.env` + `dotenv` | No leaked secrets |
| 17 | Natural language output format | Embed Pydantic schema in prompt | Reliable JSON output |
| 18 | "Extract relevant info" | Add negative constraints | Fewer hallucinations |
| 19 | Full pipeline for compile check | Test imports first | Instant feedback |
| 20 | String path concatenation | `pathlib.Path` | Cross-platform, readable |
