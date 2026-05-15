"""
OCR Engine — Hybrid Tiered Intelligence
Tiers:
1. PyMuPDF Native (Digital PDFs)
2. EasyOCR (Local CPU-accelerated for standard scans)
3. Gemma-4-26b-a4b-it (Cognitive Multimodal for noisy/complex/handwritten docs)
"""
import os
import json
import hashlib
from pathlib import Path
from PIL import Image
import fitz  # PyMuPDF
import easyocr
from google import genai
from dataclasses import dataclass, asdict
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class PageResult:
    page_num: int
    raw_text: str
    confidence: Optional[float]
    source_file: str
    method_used: str  # "pymupdf_native" | "easyocr" | "gemma_multimodal"


@dataclass
class DocumentResult:
    source_file: str
    file_hash: str
    pages: list[PageResult]
    total_pages: int
    extraction_method: str
    warnings: list[str]

    def full_text(self) -> str:
        return "\n\n".join(p.raw_text for p in self.pages)


class OCREngine:
    def __init__(self, backend: str = "auto"):
        """
        backend: "auto" | "easyocr" | "gemma"
        "auto" uses the tiered approach: Native -> EasyOCR -> Gemma
        """
        self.backend = backend
        self.reader = None
        self._setup_backends()

    def _setup_backends(self):
        # Setup EasyOCR (CPU mode)
        if self.backend in ["auto", "easyocr"]:
            try:
                self.reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            except Exception as e:
                print(f"WARNING: EasyOCR init failed: {e}. Falling back to Gemma.")
                self.reader = None

        # Setup Gemma (Cloud Multimodal)
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            self.vision_client = genai.Client(api_key=api_key)
            self.vision_model = "gemma-4-26b-a4b-it"
        else:
            self.vision_client = None
            self.vision_model = None
            if self.backend == "gemma":
                print("WARNING: GEMINI_API_KEY not found in environment. Gemma tier disabled.")

    def process_file(self, filepath: str | Path, output_dir: str | Path) -> DocumentResult:
        """Main entry point. Accepts PDF or image. Writes JSON to output_dir."""
        filepath = Path(filepath)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        file_hash = self._hash_file(filepath)
        cache_path = output_dir / f"{file_hash}.json"

        # Cache check — skip re-processing
        if cache_path.exists():
            data = json.loads(cache_path.read_text())
            data["pages"] = [PageResult(**p) for p in data.get("pages", [])]
            return DocumentResult(**data)

        if filepath.suffix.lower() == ".pdf":
            result = self._process_pdf(filepath)
        else:
            result = self._process_image(filepath)

        result.file_hash = file_hash
        cache_path.write_text(json.dumps(asdict(result), indent=2))
        return result

    def _process_pdf(self, path: Path) -> DocumentResult:
        doc = fitz.open(str(path))
        pages = []
        warnings = []

        for i, page in enumerate(doc):
            # TIER 1: Native PDF Text
            native_text = page.get_text().strip()
            if len(native_text) > 100:
                pages.append(PageResult(i+1, native_text, 1.0, str(path), "pymupdf_native"))
                continue

            # TIER 2 & 3: Image-based OCR
            pix = page.get_pixmap(dpi=300)
            img_path = Path(os.environ.get("PROCESSED_DIR", "D:/psl-ai-engineer/processed")) / f"_page_{i+1}_{self._hash_file(path)}.png"
            pix.save(str(img_path))

            text, method = self._ocr_with_fallback(str(img_path))

            if not text.strip():
                warnings.append(f"Page {i+1}: OCR returned empty")

            pages.append(PageResult(i+1, text, None, str(path), method))

        return DocumentResult(str(path), "", pages, len(pages), "hybrid_tiered", warnings)

    def _process_image(self, path: Path) -> DocumentResult:
        text, method = self._ocr_with_fallback(str(path))
        return DocumentResult(str(path), "", [PageResult(1, text, None, str(path), method)], 1, "hybrid_tiered", [])

    def _ocr_with_fallback(self, img_path: str) -> tuple[str, str]:
        """Tiered fallback logic: EasyOCR -> Gemma"""
        # If explicitly set to gemma, skip EasyOCR
        if self.backend == "gemma":
            return self._ocr_multimodal(img_path), "gemma_multimodal"

        # TIER 2: EasyOCR
        if self.reader:
            results = self.reader.readtext(img_path, detail=0)
            text = "\n".join(results)

            # Heuristic: If EasyOCR finds very little text on a document, it's likely a complex scan/handwriting
            if len(text.strip()) > 50:
                return text, "easyocr"

        # TIER 3: Gemma Multimodal (Cognitive Fallback)
        if self.vision_client:
            return self._ocr_multimodal(img_path), "gemma_multimodal"

        return "", "failed"

    def _ocr_multimodal(self, img_path: str) -> str:
        """Uses Gemma-4-26b-a4b-it to perform high-accuracy visual OCR."""
        try:
            img = Image.open(img_path)
            prompt = "Extract all text from this document image exactly as it appears. Maintain layout where possible. Output only the raw extracted text."
            response = self.vision_client.models.generate_content(
                model=self.vision_model,
                contents=[prompt, img],
            )
            return response.text
        except Exception as e:
            print(f"Gemma OCR Error: {e}")
            return ""

    @staticmethod
    def _hash_file(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
