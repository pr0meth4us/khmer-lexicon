import os
import re

# File paths
ocr_file = "/Users/nicksng/.gemini/antigravity-ide/brain/eb6df402-0643-44b2-ae93-172ada213240/scratch/ocr_output.md"
target_file = "/Users/nicksng/code/egd platform/data/egd-master-docs/Enterprises Go Digital Program_ocr_transcription.txt"
output_file = "/Users/nicksng/.gemini/antigravity-ide/brain/eb6df402-0643-44b2-ae93-172ada213240/scratch/matched_terms.md"

def extract_terms_from_ocr(filepath):
    terms = {}
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return terms
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Simple heuristic: English letters vs Khmer script
            eng_match = re.search(r'([A-Za-z][A-Za-z\s\-\_]+)', line)
            khm_match = re.search(r'([\u1780-\u17FF\u19E0-\u19FF]+[\s\u1780-\u17FF\u19E0-\u19FF]*)', line)
            
            if eng_match and khm_match:
                eng = eng_match.group(1).strip()
                khm = khm_match.group(1).strip()
                if len(eng) > 2 and len(khm) > 1:
                    terms[eng.lower()] = (eng, khm)
    return terms

def main():
    print("Extracting terms from OCR output...")
    lexicon_terms = extract_terms_from_ocr(ocr_file)
    print(f"Extracted {len(lexicon_terms)} technical term candidates.")

    print("Reading EGD Transcription...")
    with open(target_file, 'r', encoding='utf-8') as f:
        egd_text = f.read()

    print("Matching terms...")
    matches = []
    # Test each term in the lexicon against the EGD transcript
    for eng_lower, (eng, khm) in lexicon_terms.items():
        pattern = r'\b' + re.escape(eng) + r'\b'
        if re.search(pattern, egd_text, re.IGNORECASE):
            matches.append((eng, khm))

    matches.sort(key=lambda x: x[0].lower())
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Technical Term Matches\n\n")
        f.write("| English Term (from EGD) | Official Khmer (from OCR Lexicon) |\n")
        f.write("|---|---|\n")
        for eng, khm in matches:
            f.write(f"| {eng} | {khm} |\n")
            
    print(f"Found {len(matches)} matching terms. Results saved to {output_file}")

if __name__ == "__main__":
    main()
