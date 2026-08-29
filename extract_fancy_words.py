import os
import sys
import glob
import json
import time
import signal
from pathlib import Path
from google.genai import types
from dotenv import load_dotenv
import requests

load_dotenv()
sys.path.insert(0, "/Users/nicksng/code/bifrost/sdk/python")
sys.path.insert(0, "/Users/nicksng/code/random")
from bifrost_ai import get_genai_client  # noqa: E402

INPUT_DIR = "data/ai_letter_writer/raw_extracted/kh/"
OUTPUT_FILE = "data/ai_letter_writer/raw_extracted/fancy_lexicon.json"
CHUNK_SIZE_LIMIT = 15000  # Characters per chunk (reduced to prevent timeout)

def load_text_chunks(input_dir):
    files = glob.glob(os.path.join(input_dir, "*.txt"))
    chunks = []
    current_chunk = ""
    
    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            if len(current_chunk) + len(content) > CHUNK_SIZE_LIMIT and current_chunk:
                chunks.append(current_chunk)
                current_chunk = content
            else:
                current_chunk += "\n" + content
                
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks

def fetch_tech_review_chunks():
    """Fetch Khmer text from pending solutions in the 'tech-review' stage via EGD API."""
    chunks = []
    current_chunk = ""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            token = config.get('token')
            cookie = config.get('cookie')
            
        print("Fetching solutions in tech review stage from EGD API...", flush=True)
        headers = {'Authorization': f'Bearer {token}'}
        if cookie:
            headers['Cookie'] = cookie
            
        res = requests.get(
            'https://backoffice.enterprisedigital.gov.kh/api/backoffice/service-provider-solutions?size=200',
            headers=headers,
            timeout=30
        )
        res.raise_for_status()
        sols = res.json().get('data', [])
        
        tech_review_sols = [
            s for s in sols
            if s.get('latest_profile_request') and 
               s['latest_profile_request'].get('current_stage') and 
               s['latest_profile_request']['current_stage'].get('slug') == 'technical-review'
        ]
        
        res_prof = requests.get(
            'https://backoffice.enterprisedigital.gov.kh/api/backoffice/service-providers?size=200',
            headers=headers,
            timeout=30
        )
        res_prof.raise_for_status()
        profs = res_prof.json().get('data', [])
        
        tech_review_profs = [
            p for p in profs
            if p.get('latest_profile_request') and 
               p['latest_profile_request'].get('current_stage') and 
               p['latest_profile_request']['current_stage'].get('slug') == 'technical-review'
        ]
        
        print(f"Found {len(tech_review_sols)} solutions and {len(tech_review_profs)} profiles in technical review stage.", flush=True)
        
        for s in tech_review_sols:
            parts = [s.get('description_km', '')]
            for p in s.get('packages', []):
                parts.append(p.get('benefit_km', ''))
                parts.append(p.get('feature_km', ''))
                
            combined = "\n".join(filter(None, parts)).strip()
            if combined:
                if len(current_chunk) + len(combined) > CHUNK_SIZE_LIMIT and current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = combined
                else:
                    current_chunk += "\n\n" + combined
                    
        for p in tech_review_profs:
            about_km = p.get('about_km', '').strip()
            if about_km:
                if len(current_chunk) + len(about_km) > CHUNK_SIZE_LIMIT and current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = about_km
                else:
                    current_chunk += "\n\n" + about_km
                    
        if current_chunk:
            chunks.append(current_chunk)
            
    except Exception as e:
        print(f"Warning: Failed to fetch tech review API: {e}", flush=True)
        
    return chunks

def timeout_handler(signum, frame):
    raise TimeoutError("API call hung indefinitely")

def extract_fancy_terms(text_chunk, chunk_index, total_chunks):
    client = get_genai_client()

    prompt = f"""You are an expert bilingual linguist and administrative writer for the Cambodian government.
Your task is to scan the provided raw Khmer administrative letters and reports and extract highly formal, elevated administrative phrasing (often called "fancy words").
These are phrases or words that replace common, everyday language to make the document sound more professional, authoritative, and strategic (e.g. replacing 'ស្វែងយល់' with 'វិភាគឱ្យបានស៊ីជម្រៅ', or 'ជួយ' with 'ជ្រោមជ្រែង').

Extract as many of these formal/fancy terms as you can find in the text.

Output ONLY a JSON array of objects with the following keys:
- "base_term": The simple/standard Khmer equivalent that a layperson might use.
- "fancy_term": The elevated/formal phrasing found in the text.
- "english_equivalent": The English translation of the fancy term.
- "context": A brief description of when or how to use this fancy term in administrative writing.

Text to analyze:
{text_chunk}
"""
    print(f"Sending Chunk {chunk_index}/{total_chunks} to Gemini...", flush=True)
    retries = 3
    for attempt in range(retries):
        try:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(60)  # strict 60 seconds timeout
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            signal.alarm(0)  # disable alarm on success
            
            data = json.loads(response.text)
            print(f"Extracted {len(data)} terms from Chunk {chunk_index}", flush=True)
            time.sleep(5)
            return data
        except TimeoutError as e:
            print(f"Attempt {attempt+1} hung: {e}", flush=True)
            signal.alarm(0)
            time.sleep(5)
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}", flush=True)
            signal.alarm(0)
            time.sleep(15)
    return []

def save_lexicon(all_extracted_terms, new_additions_count=0):
    existing_lexicon = []
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            try:
                existing_lexicon = json.load(f)
            except json.JSONDecodeError:
                pass
                
    unique_terms = {}
    for term in existing_lexicon:
        key = term.get('fancy_term', '').strip()
        if key:
            unique_terms[key] = term
            
    for term in all_extracted_terms:
        key = term.get('fancy_term', '').strip()
        if key and key not in unique_terms:
            unique_terms[key] = {
                "base_term": term.get('base_term', '').strip(),
                "fancy_term": key,
                "english_equivalent": term.get('english_equivalent', '').strip(),
                "context": term.get('context', '').strip()
            }
            new_additions_count += 1
            
    final_lexicon = list(unique_terms.values())
    final_lexicon.sort(key=lambda x: x.get('fancy_term', ''))
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_lexicon, f, ensure_ascii=False, indent=2)
    return new_additions_count, len(final_lexicon)

def main():
    print("Loading raw files...", flush=True)
    chunks = load_text_chunks(INPUT_DIR)
    
    api_chunks = fetch_tech_review_chunks()
    chunks.extend(api_chunks)
    
    print(f"Grouped into {len(chunks)} chunks.", flush=True)
    
    total_new = 0
    for i, chunk in enumerate(chunks, 1):
        terms = extract_fancy_terms(chunk, i, len(chunks))
        if terms:
            added, total = save_lexicon(terms)
            total_new += added
            print(f"Saved chunk {i}. Progress: {total} total terms.", flush=True)
            
    print(f"Finished! Added {total_new} new terms overall.", flush=True)

if __name__ == "__main__":
    main()
