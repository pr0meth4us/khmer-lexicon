import os
import sys
import json
import time
from pathlib import Path
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(BUILD_DIR, "random"))
# Vertex AI clients. Swap for google.genai directly if you do not
# have this helper; it only wraps credential loading.
from bifrost_ai import get_genai_client  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_PDFS = os.environ.get("LEXICON_SOURCE_PDFS", os.path.join(ROOT, "source_pdfs"))
BUILD_DIR = os.environ.get("LEXICON_BUILD_DIR", os.path.join(ROOT, "build"))
DIST_DIR = os.environ.get("LEXICON_DIST_DIR", os.path.join(ROOT, "dist"))


EN_FILE = "scratch/pentagon_en_vision_output.txt"
KH_FILE = "scratch/pentagon_kh_vision_output.txt"
OUT_FILE = "data/pentagon_lexicon.json"

EN_SPLITS = [1513, 1764, 2068, 2329, 2642]
KH_SPLITS = [1437, 1665, 1946, 2176, 2457]

def load_chunks(file_path, splits):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    chunks = []
    start = 0
    for split in splits:
        chunks.append("".join(lines[start:split]))
        start = split
    chunks.append("".join(lines[start:]))
    return chunks

def extract_terms(en_text, kh_text, chunk_index):
    client = get_genai_client()

    prompt = f"""You are an expert bilingual linguist and policy analyst specializing in the Cambodian government's Pentagonal Strategy.
I will provide you with aligned chunks of the English and Khmer official strategy document.
Your task is to extract a comprehensive lexicon of terminology from these texts.
You must extract terms related to tech, policy, and economics alike.
Focus on specialized vocabulary, recurring policy phrases, jargon, and high-level concepts.
Find the exact Khmer translation for each English term as used in the provided text.
Extract AS MANY terms as possible from this section (aim for 50+ if available).

Output ONLY a JSON array of objects with keys:
- "en": English term
- "kh": Khmer term
- "category": String enum (tech, policy, or econ)

English Text:
{en_text}

Khmer Text:
{kh_text}
"""
    print(f"Sending Chunk {chunk_index+1} to Gemini...")
    retries = 3
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-pro',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            data = json.loads(response.text)
            print(f"Extracted {len(data)} terms from Chunk {chunk_index+1}")
            return data
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(5)
    return []

def main():
    print("Loading documents...")
    en_chunks = load_chunks(EN_FILE, EN_SPLITS)
    kh_chunks = load_chunks(KH_FILE, KH_SPLITS)
    
    all_terms = []
    
    for i in range(len(en_chunks)):
        terms = extract_terms(en_chunks[i], kh_chunks[i], i)
        all_terms.extend(terms)
        
    print(f"Total raw terms extracted: {len(all_terms)}")
    
    # Deduplicate based on English term (case insensitive)
    unique_terms = {}
    for term in all_terms:
        key = term.get('en', '').strip().lower()
        if key and key not in unique_terms:
            unique_terms[key] = {
                "en": term.get('en', '').strip(),
                "kh": term.get('kh', '').strip(),
                "category": term.get('category', 'policy')
            }
            
    final_lexicon = list(unique_terms.values())
    final_lexicon.sort(key=lambda x: x['en'])
    
    print(f"Final deduplicated lexicon size: {len(final_lexicon)}")
    
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_lexicon, f, ensure_ascii=False, indent=2)
        
    print(f"Saved to {OUT_FILE}")

if __name__ == "__main__":
    main()
