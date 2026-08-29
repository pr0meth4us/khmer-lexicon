"""OCR every page of a PDF to a text file via Cloud Vision.
    python scratch/extract_pentagon_vision.py <pdf> <out.txt>
"""
import sys
from pathlib import Path

import fitz

sys.path.insert(0, "/Users/nicksng/code/bifrost/sdk/python")
sys.path.insert(0, "/Users/nicksng/code/random")
from bifrost_ai import get_vision_client
from ocr_tools.pdf_ocr import render_pdf_page, ocr_image  # noqa: E402

pdf_path = sys.argv[1] if len(sys.argv) > 1 else "/Users/nicksng/code/KH-PENTAGONAL-STRATEGY-PHASE-I.pdf"
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
