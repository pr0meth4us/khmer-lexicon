import os
import json
import re
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

PROMPT = """Extract all dictionary/lexicon entries on this page into a JSON array.
If there are no lexicon entries on this page (e.g. cover, title page, index, table of contents, or empty page), return an empty JSON array [].

For each entry on the page, create a JSON object with the following schema:
{
  "khmer": "Khmer term (clean Unicode Khmer text)",
  "english": "English translation/term",
  "french": "French translation/term if present",
  "pos": "Part of speech (e.g. (n.), (v.), (m.), (f.)) if present, else empty string",
  "definition": "Khmer definition or explanation text",
  "examples": "Khmer example text if present, else empty string"
}

Output ONLY valid JSON (a JSON array of objects). Do not include markdown code block formatting or backticks.
"""

def process_page(pdf_path, page_num):
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")
    doc.close()

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
        else:
            return page_num + 1, []
    except Exception as e:
        print(f"Error processing page {page_num + 1} of {pdf_path}: {e}")
        return page_num + 1, []

def process_pdf(pdf_path, source_name, output_path):
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()
    
    print(f"\n--- Extracting {source_name} ({total_pages} pages) ---")
    all_entries = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_page, pdf_path, p): p for p in range(total_pages)}
        page_results = {}
        for future in as_completed(futures):
            p_num, entries = future.result()
            page_results[p_num] = entries
            print(f"[{source_name}] Page {p_num}/{total_pages} done: {len(entries)} entries extracted")
            
    # Combine entries in page order
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
    pdf1 = os.path.join(SOURCE_PDFS, "NCKL_Political_Science_2014.pdf")
    out1 = os.path.join(BUILD_DIR, "nckl_political_science_lexicon.json")
    entries1 = process_pdf(pdf1, "nckl-political-science-and-diplomacy", out1)

    pdf2 = os.path.join(SOURCE_PDFS, "CouncilOfMinisters_Legal_Terms_2007.pdf")
    out2 = os.path.join(BUILD_DIR, "legal_terms_lexicon.json")
    entries2 = process_pdf(pdf2, "council-of-ministers-legal-terms", out2)

    print("\nAll extractions completed successfully!")
