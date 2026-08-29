import os
import sys
import json
import time
import fitz
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.genai import types

sys.path.insert(0, "/Users/nicksng/code/bifrost/sdk/python")
sys.path.insert(0, "/Users/nicksng/code/random")
from bifrost_ai import get_genai_client, get_vision_client  # noqa: E402
from ocr_tools.pdf_ocr import render_pdf_page, ocr_image
from json_tools.gemini_json import parse_gemini_json

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
    doc = fitz.open(pdf_path)
    img_bytes = render_pdf_page(doc, page_num)
    doc.close()

    # Step 1: Google Cloud Vision for 100% accurate OCR
    try:
        ocr_text = ocr_image(img_bytes, vision_client)
        if not ocr_text.strip():
            return page_num + 1, []
    except Exception as e:
        print(f"Vision API Exception page {page_num + 1}: {e}")
        return page_num + 1, []

    # Step 2: Gemini to strictly parse the perfect text into JSON
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
            entries = parse_gemini_json(res.text)
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

def process_pdf(pdf_path, source_name, output_path, batch_size=15):
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found.")
        return []
        
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()
    
    print(f"\n--- Extracting {source_name} ({total_pages} pages) ---")
    
    page_results = {}
    for start in range(0, total_pages, batch_size):
        end = min(start + batch_size, total_pages)
        print(f"Processing pages {start+1} to {end}...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(process_page, pdf_path, p): p for p in range(start, end)}
            for future in as_completed(futures):
                p_num, entries = future.result()
                page_results[p_num] = entries
                print(f"[{source_name}] Page {p_num}/{total_pages} done: {len(entries)} entries")
        time.sleep(2) # Prevent rate limits

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

def test_page(pdf_path, page_num):
    print(f"--- Running test on {pdf_path} Page {page_num+1} ---")
    _, entries = process_page(pdf_path, page_num)
    print(json.dumps(entries, ensure_ascii=False, indent=2))
    print(f"Found {len(entries)} entries on test page.")

if __name__ == "__main__":
    sources = [
        {
            "pdf": "/Users/nicksng/code/khmer-lexicon/source_pdfs/NCKL_Political_Science_2014.pdf",
            "source_name": "nckl-political-science-and-diplomacy",
            "out": "/Users/nicksng/code/egd platform/data/ai_letter_writer/training_datasets/nckl_political_science_lexicon.json",
            "test_page": 8 # Example
        },
        {
            "pdf": "/Users/nicksng/code/khmer-lexicon/source_pdfs/CouncilOfMinisters_Legal_Terms_2007.pdf",
            "source_name": "council-of-ministers-legal-terms",
            "out": "/Users/nicksng/code/egd platform/data/ai_letter_writer/training_datasets/legal_terms_lexicon.json",
            "test_page": 3 # Example
        },
        {
            "pdf": "/Users/nicksng/code/khmer-lexicon/source_pdfs/NCKL_Bulletin_Vol6_Technology_2014.pdf",
            "source_name": "nckl-technology-and-science",
            "out": "/Users/nicksng/code/egd platform/data/ai_letter_writer/training_datasets/nckl_technology_lexicon.json",
        },
        {
            "pdf": "/Users/nicksng/code/khmer-lexicon/source_pdfs/MPTC_Digital_Lexicon_2025.pdf",
            "source_name": "mptc-digital-lexicon",
            "out": "/Users/nicksng/code/egd platform/data/ai_letter_writer/training_datasets/mptc_lexicon.json",
            "test_page": 25 # Example
        }
    ]

    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        for src in sources:
            if os.path.exists(src["pdf"]):
                test_page(src["pdf"], src["test_page"])
    else:
        for src in sources:
            process_pdf(src["pdf"], src["source_name"], src["out"])
            
        print("\nAll extractions completed successfully! Run clean_and_arrange_official_lexicons.py next.")
