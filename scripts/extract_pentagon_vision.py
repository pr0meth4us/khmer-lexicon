import os
"""OCR every page of a PDF to a text file via Cloud Vision.
    python scratch/extract_pentagon_vision.py <pdf> <out.txt>
"""
import sys
from pathlib import Path

import fitz
sys.path.insert(0, os.path.join(BUILD_DIR, "random"))
# Vertex AI clients. Swap for google.genai directly if you do not
# have this helper; it only wraps credential loading.
from bifrost_ai import get_vision_client
from ocr_tools.pdf_ocr import render_pdf_page, ocr_image  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_PDFS = os.environ.get("LEXICON_SOURCE_PDFS", os.path.join(ROOT, "source_pdfs"))
BUILD_DIR = os.environ.get("LEXICON_BUILD_DIR", os.path.join(ROOT, "build"))
DIST_DIR = os.environ.get("LEXICON_DIST_DIR", os.path.join(ROOT, "dist"))


pdf_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BUILD_DIR, "KH-PENTAGONAL-STRATEGY-PHASE-I.pdf")
out_path = sys.argv[2] if len(sys.argv) > 2 else "scratch/pentagon_kh_vision_output.txt"


def main():
    if not Path(pdf_path).exists():
        sys.exit(f"Error: PDF not found at {pdf_path}")

    vision = get_vision_client()
    doc = fitz.open(pdf_path)
    print(f"PDF has {len(doc)} pages.")

    parts = []
    for i in range(len(doc)):
        if i % 10 == 0:
            print(f"OCRing page {i + 1}/{len(doc)}...")
        try:
            text = ocr_image(render_pdf_page(doc, i), vision)
        except RuntimeError as e:
            print(f"Page {i + 1}: {e}")
            text = ""
        parts.append(f"\n\n--- Page {i + 1} ---\n{text}")

    Path(out_path).write_text("".join(parts), encoding="utf-8")
    print(f"✓ Saved OCR output to {out_path}")


if __name__ == "__main__":
    main()
