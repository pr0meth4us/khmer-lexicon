import os
import sys
import json
import time
import fitz
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.genai import types
sys.path.insert(0, os.path.join(BUILD_DIR, "random"))
# Vertex AI clients. Swap for google.genai directly if you do not
# have this helper; it only wraps credential loading.
from bifrost_ai import get_genai_client, get_vision_client  # noqa: E402
from json_tools.gemini_json import strip_json_fences as clean_json_response

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_PDFS = os.environ.get("LEXICON_SOURCE_PDFS", os.path.join(ROOT, "source_pdfs"))
BUILD_DIR = os.environ.get("LEXICON_BUILD_DIR", os.path.join(ROOT, "build"))
DIST_DIR = os.environ.get("LEXICON_DIST_DIR", os.path.join(ROOT, "dist"))


vision_client = get_vision_client()
genai_client = get_genai_client()

PROMPT = """Extract all dictionary/lexicon/terminology entries from this OCR text into a JSON array.
If there are no terminology entries in this text (e.g. cover, TOC, introduction, preface), return an empty JSON array [].

For each term entry, create a JSON object with this schema:
{
  "khmer": "Khmer term (clean Khmer Unicode text)",
  "english": "English translation/term",
  "french": "French translation/term if present",
  "pos": "Part of speech if present, else empty string",
  "definition": "Khmer definition or explanation text",
  "examples": "Khmer example text if present, else empty string"
}

Output ONLY a valid JSON array of objects. Do not include markdown code block formatting or backticks.
Here is the raw OCR text of the page:
"""

def process_page(pdf_path, page_num):
    from ocr_tools.pdf_ocr import render_pdf_page, ocr_image

    doc = fitz.open(pdf_path)
    img_bytes = render_pdf_page(doc, page_num)
    doc.close()

    try:
        ocr_text = ocr_image(img_bytes, vision_client)
        if not ocr_text.strip():
            return page_num + 1, []
    except Exception as e:
        print(f"Vision API Exception page {page_num + 1}: {e}")
        return page_num + 1, []

    for attempt in range(3):
        try:
            res = genai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[PROMPT + "\n\n" + ocr_text],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
            cleaned = clean_json_response(res.text)
            entries = json.loads(cleaned)
            if isinstance(entries, list):
                return page_num + 1, entries
            return page_num + 1, []
        except Exception as e:
            if "429" in str(e):
                time.sleep(3 * (attempt + 1))
            else:
                print(f"Gemini Error page {page_num + 1}: {e}")
                break
    return page_num + 1, []

def process_pdf(pdf_path, source_name, output_path, start_page, end_page, batch_size=15):
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found.")
        return []
        
    print(f"\n--- Extracting {source_name} (Pages {start_page} to {end_page}) ---")
    
    page_results = {}
    # Convert from 1-indexed to 0-indexed for fitz
    page_indices = list(range(start_page - 1, end_page))
    
    for i in range(0, len(page_indices), batch_size):
        batch_indices = page_indices[i:i + batch_size]
        print(f"Processing pages {[p+1 for p in batch_indices]}...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(process_page, pdf_path, p): p for p in batch_indices}
            for future in as_completed(futures):
                p_num, entries = future.result()
                page_results[p_num] = entries
                print(f"[{source_name}] Page {p_num} done: {len(entries)} entries")
        time.sleep(2)

    all_entries = []
    for p_num in sorted(page_results.keys()):
        for entry in page_results[p_num]:
            entry["source"] = source_name
            all_entries.append(entry)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)

    print(f"✓ Saved {len(all_entries)} entries to {output_path}")
    return all_entries

if __name__ == "__main__":
    sources = [
        {
            "pdf": os.path.join(SOURCE_PDFS, "NCKL_Bulletin_Vol8_2017.pdf"),
            "source_name": "nckl-bulletin-vol8-2017",
            "out": os.path.join(BUILD_DIR, "nckl_bulletin_vol8.json"),
            "start": 29, "end": 116
        },
        {
            "pdf": os.path.join(SOURCE_PDFS, "NCKL_Bulletin_Vol9_2018.pdf"),
            "source_name": "nckl-bulletin-vol9-2018",
            "out": os.path.join(BUILD_DIR, "nckl_bulletin_vol9.json"),
            "start": 43, "end": 144
        },
        {
            "pdf": os.path.join(SOURCE_PDFS, "NCKL_Bulletin_Vol10_2019.pdf"),
            "source_name": "nckl-bulletin-vol10-2019",
            "out": os.path.join(BUILD_DIR, "nckl_bulletin_vol10.json"),
            "start": 19, "end": 82
        }
    ]

    for src in sources:
        process_pdf(src["pdf"], src["source_name"], src["out"], src["start"], src["end"])
        
    print("\nAll extractions completed successfully!")
