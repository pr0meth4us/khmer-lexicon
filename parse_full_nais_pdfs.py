import os
import json
import fitz
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from google import genai

import sys
from pathlib import Path
sys.path.insert(0, "/Users/nicksng/code/bifrost/sdk/python")
sys.path.insert(0, "/Users/nicksng/code/random")
from bifrost_ai import get_genai_client
client = get_genai_client()

PROMPT = """Parse this document page completely into clean Markdown format. 
Preserve all headings, subheadings, lists, bullet points, tables, and exact text content.
Output ONLY the clean markdown representation of the page without any conversational intro/outro or backticks wrapping the whole response.
"""

def parse_page(pdf_path, page_num):
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
            text = res.text.strip()
            if text.startswith("```markdown"):
                text = text[11:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return page_num + 1, text.strip()
        except Exception as e:
            print(f"Attempt {attempt+1} error for page {page_num+1}: {e}")
            time.sleep(3)
    return page_num + 1, f"<!-- Page {page_num+1} failed to parse -->"

def process_pdf(pdf_path, doc_label, output_path):
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    print(f"\n--- Parsing Full Document: {doc_label} ({total_pages} pages) ---")
    page_texts = {}

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(parse_page, pdf_path, p): p for p in range(total_pages)}
        for future in as_completed(futures):
            p_num, text = future.result()
            page_texts[p_num] = text
            print(f"[{doc_label}] Page {p_num}/{total_pages} parsed")

    full_md = []
    for p_num in sorted(page_texts.keys()):
        full_md.append(f"<!-- Page {p_num} -->\n" + page_texts[p_num])

    content = "\n\n---\n\n".join(full_md)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✓ Saved full OCR markdown output to {output_path}")

if __name__ == "__main__":
    en_pdf = "/Users/nicksng/code/nais-v5-en-for-consultation-clean.pdf"
    en_out = "/Users/nicksng/code/egd platform/data/ai_letter_writer/nais_v5_en_parsed.md"
    process_pdf(en_pdf, "NAIS-v5-EN", en_out)

    kh_pdf = "/Users/nicksng/code/nais-v5-kh-for-consultation-clean.pdf"
    kh_out = "/Users/nicksng/code/egd platform/data/ai_letter_writer/nais_v5_kh_parsed.md"
    process_pdf(kh_pdf, "NAIS-v5-KH", kh_out)

    print("\nAll full document OCR extractions completed!")
