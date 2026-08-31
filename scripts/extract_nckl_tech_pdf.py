import os
import json
import time
import fitz
from concurrent.futures import ThreadPoolExecutor, as_completed
from google import genai

import sys
from pathlib import Path
sys.path.insert(0, os.path.join(BUILD_DIR, "random"))
# Vertex AI clients. Swap for google.genai directly if you do not
# have this helper; it only wraps credential loading.
from bifrost_ai import get_genai_client
from json_tools.gemini_json import strip_json_fences as clean_json_response

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_PDFS = os.environ.get("LEXICON_SOURCE_PDFS", os.path.join(ROOT, "source_pdfs"))
BUILD_DIR = os.environ.get("LEXICON_BUILD_DIR", os.path.join(ROOT, "build"))
DIST_DIR = os.environ.get("LEXICON_DIST_DIR", os.path.join(ROOT, "dist"))

client = get_genai_client()

PROMPT = """Extract all dictionary/lexicon/terminology entries on this page into a JSON array.
If there are no terminology entries on this page (e.g. cover, TOC, introduction, preface), return an empty JSON array [].

For each term entry on the page, create a JSON object with this schema:
{
  "khmer": "Khmer term (clean Khmer Unicode text)",
  "english": "English translation/term",
  "french": "French translation/term if present",
  "pos": "Part of speech if present, else empty string",
  "definition": "Khmer definition or explanation text",
  "examples": "Khmer example text if present, else empty string"
}

Output ONLY a valid JSON array of objects. Do not include markdown code block formatting or backticks.
"""

def process_page(pdf_path, page_num):
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")
    doc.close()

    for attempt in range(3):
        try:
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    genai.types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                    PROMPT
                ]
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
                print(f"Error page {page_num + 1}: {e}")
                break
    return page_num + 1, []

def main():
    pdf_path = os.path.join(SOURCE_PDFS, "NCKL_Bulletin_Vol6_Technology_2014.pdf")
    output_path = os.path.join(BUILD_DIR, "nckl_technology_lexicon.json")
    
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()
    
    print(f"--- Extracting NCKL Technology Lexicon ({total_pages} pages) ---")
    
    # Process pages in batches to avoid rate limits
    page_results = {}
    batch_size = 15
    for start in range(0, total_pages, batch_size):
        end = min(start + batch_size, total_pages)
        print(f"Processing pages {start+1} to {end}...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(process_page, pdf_path, p): p for p in range(start, end)}
            for future in as_completed(futures):
                p_num, entries = future.result()
                page_results[p_num] = entries
                print(f"Page {p_num}/{total_pages} done: {len(entries)} entries")
        time.sleep(2)

    all_entries = []
    for p_num in sorted(page_results.keys()):
        for entry in page_results[p_num]:
            entry["source"] = "nckl-technology-and-science"
            all_entries.append(entry)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Saved {len(all_entries)} entries to {output_path}")

    # Now re-run master merge
    files_to_merge = [
        ("unified_lexicon.json", "panhavonh-glossary"),
        ("mptc_lexicon.json", "mptc-digital-lexicon"),
        ("nckl_political_science_lexicon.json", "nckl-political-science-and-diplomacy"),
        ("legal_terms_lexicon.json", "council-of-ministers-legal-terms"),
        ("nckl_technology_lexicon.json", "nckl-technology-and-science")
    ]

    master_lexicon = []
    dataset_dir = BUILD_DIR
    for filename, default_source in files_to_merge:
        filepath = os.path.join(dataset_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    if "source" not in item or not item["source"]:
                        item["source"] = default_source
                    master_lexicon.append(item)

    unified_path = os.path.join(dataset_dir, "unified_lexicon.json")
    with open(unified_path, "w", encoding="utf-8") as f:
        json.dump(master_lexicon, f, ensure_ascii=False, indent=2)

    print(f"✓ Master unified_lexicon.json updated with {len(master_lexicon)} total entries!")

if __name__ == "__main__":
    main()
