import os
import json
import time
import fitz
from google import genai

import sys
from pathlib import Path
sys.path.insert(0, "/Users/nicksng/code/bifrost/sdk/python")
sys.path.insert(0, "/Users/nicksng/code/random")
from bifrost_ai import get_genai_client
from json_tools.gemini_json import strip_json_fences as clean_json_response
client = get_genai_client()

PROMPT = """Extract all dictionary/lexicon entries on this page into a JSON array.
If there are no lexicon entries on this page, return an empty JSON array [].

For each entry on the page, create a JSON object with the following schema:
{
  "khmer": "Khmer term (clean Unicode Khmer text)",
  "english": "English translation/term",
  "french": "French translation/term if present",
  "pos": "Part of speech (e.g. (n.), (v.), (m.), (f.)) if present, else empty string",
  "definition": "Khmer definition or explanation text",
  "examples": "Khmer example text if present, else empty string",
  "source": "council-of-ministers-legal-terms"
}

Output ONLY valid JSON (a JSON array of objects). Do not include markdown code block formatting or backticks.
"""

pdf2 = "/Users/nicksng/code/de39d3c0-5d2b-4f64-ab83-3c6e780002b2.pdf"
failed_pages = [26, 37, 47] # 1-indexed

doc2 = fitz.open(pdf2)
recovered_entries = {}

for p_num in failed_pages:
    page = doc2[p_num - 1]
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")
    
    success = False
    for attempt in range(5):
        try:
            print(f"Retrying page {p_num} (attempt {attempt+1})...")
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    genai.types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                    PROMPT
                ]
            )
            cleaned = clean_json_response(res.text)
            entries = json.loads(cleaned)
            recovered_entries[p_num] = entries
            print(f"✓ Page {p_num} recovered successfully: {len(entries)} entries")
            success = True
            break
        except Exception as e:
            print(f"Attempt {attempt+1} failed for page {p_num}: {e}")
            time.sleep(3)
doc2.close()

# Update legal_terms_lexicon.json
legal_path = "/Users/nicksng/code/egd platform/data/ai_letter_writer/training_datasets/legal_terms_lexicon.json"
with open(legal_path, "r", encoding="utf-8") as f:
    existing_entries = json.load(f)

# Combine and deduplicate / replace.
# Re-running recovery must be idempotent: a page that was already merged in a
# previous run must not append its entries a second time. Keyed on
# (khmer, english) -- do NOT .lower() the Khmer, it is a no-op (Khmer has no
# case) and only hides the fact that mark-order variants are still distinct.
def entry_key(entry):
    return (str(entry.get("khmer", "")).strip(),
            str(entry.get("english", "")).strip().lower())


seen = {entry_key(e) for e in existing_entries}
print(f"Existing total entries: {len(existing_entries)}")

added = skipped = 0
for p_num, entries in recovered_entries.items():
    for entry in entries:
        key = entry_key(entry)
        if key in seen:
            skipped += 1
            continue
        seen.add(key)
        existing_entries.append(entry)
        added += 1
    print(f"  page {p_num}: {len(entries)} recovered")

print(f"Added {added} new entries, skipped {skipped} already present")
print(f"New total entries after recovery: {len(existing_entries)}")

with open(legal_path, "w", encoding="utf-8") as f:
    json.dump(existing_entries, f, ensure_ascii=False, indent=2)

print("✓ Successfully updated legal_terms_lexicon.json with recovered pages!")
