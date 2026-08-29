import os
import json
import re

dataset_dir = "/Users/nicksng/code/egd platform/data/ai_letter_writer/training_datasets"

# Official files and metadata
official_files = [
    {
        "filename": "pentagon_lexicon.json",
        "source_tag": "pentagonal-strategy-phase1",
        "category": "Policy, Tech & Economics",
        "author": "Royal Government of Cambodia",
        "version": "1.0",
        "year": "2023"
    },
    {
        "filename": "mptc_lexicon.json",
        "source_tag": "mptc-digital-lexicon",
        "category": "Digital Technology & Telecom",
        "author": "Ministry of Post and Telecommunications (MPTC)",
        "version": "1.0",
        "year": "2025"
    },
    {
        "filename": "nckl_political_science_lexicon.json",
        "source_tag": "nckl-political-science-and-diplomacy",
        "category": "Political Science & Diplomacy",
        "author": "National Council of Khmer Language (NCKL)",
        "version": "1.0",
        "year": "2014"
    },
    {
        "filename": "legal_terms_lexicon.json",
        "source_tag": "council-of-ministers-legal-terms",
        "category": "Law & Civil Procedure",
        "author": "Council of Ministers",
        "version": "1.0",
        "year": "2007"
    },
    {
        "filename": "nckl_technology_lexicon.json",
        "source_tag": "nckl-technology-and-science",
        "category": "Science, Tech & Mathematics",
        "author": "National Council of Khmer Language (NCKL)",
        "version": "1.0",
        "year": "2014"
    },
    {
        "filename": "extra_lexicon_1.json",
        "source_tag": "rac-new-words",
        "category": "General & New Words",
        "author": "Royal Academy of Cambodia (National Language Institute)",
        "version": "1.0",
        "year": "2018"
    },
    {
        "filename": "country_and_city_names_lexicon.json",
        "source_tag": "nckl-country-and-city-names",
        "category": "Geography",
        "author": "National Council of Khmer Language (NCKL)",
        "version": "1.0",
        "year": "2013"
    },
    {
        "filename": "extra_lexicon_2.json",
        "source_tag": "nckl-economics",
        "category": "Economics",
        "author": "National Council of Khmer Language (NCKL)",
        "version": "1.0",
        "year": "2019"
    },
    {
        "filename": "nckl_bulletin_vol3.json",
        "source_tag": "nckl-bulletin-vol3-2010",
        "category": "General & Specialized Terms (NCKL Bulletin)",
        "author": "National Council of Khmer Language (NCKL)",
        "version": "1.0",
        "year": "2010"
    },
    {
        "filename": "nckl_bulletin_vol4.json",
        "source_tag": "nckl-bulletin-vol4-2012",
        "category": "General & Specialized Terms (NCKL Bulletin)",
        "author": "National Council of Khmer Language (NCKL)",
        "version": "1.0",
        "year": "2012"
    },
    {
        "filename": "nckl_bulletin_vol5.json",
        "source_tag": "nckl-bulletin-vol5-2013",
        "category": "General & Specialized Terms (NCKL Bulletin)",
        "author": "National Council of Khmer Language (NCKL)",
        "version": "1.0",
        "year": "2013"
    },
    {
        "filename": "nckl_bulletin_vol7.json",
        "source_tag": "nckl-bulletin-vol7-2015",
        "category": "General & Specialized Terms (NCKL Bulletin)",
        "author": "National Council of Khmer Language (NCKL)",
        "version": "1.0",
        "year": "2015"
    },
    {
        "filename": "nckl_bulletin_vol8.json",
        "source_tag": "nckl-bulletin-vol8-2017",
        "category": "General & Specialized Terms (NCKL Bulletin)",
        "author": "National Council of Khmer Language (NCKL)",
        "version": "1.0",
        "year": "2017"
    },
    {
        "filename": "nckl_bulletin_vol9.json",
        "source_tag": "nckl-bulletin-vol9-2018",
        "category": "General & Specialized Terms (NCKL Bulletin)",
        "author": "National Council of Khmer Language (NCKL)",
        "version": "1.0",
        "year": "2018"
    },
    {
        "filename": "nckl_bulletin_vol10.json",
        "source_tag": "nckl-bulletin-vol10-2019",
        "category": "General & Specialized Terms (NCKL Bulletin)",
        "author": "National Council of Khmer Language (NCKL)",
        "version": "1.0",
        "year": "2019"
    }
]

def clean_khmer(text):
    if not text:
        return ""
    text = text.strip()
    # Remove leading numbering like "១- ", "៨១-", "1> ", "1.", "1-", "១. "
    text = re.sub(r'^[០-៩0-9]+[\s\->\.\)\}]*', '', text).strip()
    # Common OCR/typo fixes
    text = text.replace("កតិកាសញ្ញដ", "កតិកាសញ្ញា")
    text = text.replace("ដមារ", "ខ្មែរ")
    text = text.replace("ដមរា", "ខ្មែរ")
    return text.strip()

def clean_english(text):
    if not text:
        return ""
    text = text.strip()
    # Remove prefixes like "Eng. ", "H. ", "អ. ", "អង់. "
    text = re.sub(r'^(Eng\.|H\.|អ\.|អង់\.)\s*', '', text, flags=re.IGNORECASE).strip()
    return text

def clean_french(text):
    if not text:
        return ""
    text = text.strip()
    # Remove prefixes like "Fr. ", "បារ. ", "Fr "
    text = re.sub(r'^(Fr\.|បារ\.|Fr)\s*', '', text, flags=re.IGNORECASE).strip()
    return text

def clean_pos(text):
    if not text:
        return ""
    text = text.strip()
    return text

def process_official_data():
    all_official_entries = []
    en_to_kh_map = {}
    kh_to_en_map = {}
    
    seen_keys = set()
    entry_counter = 1

    for file_info in official_files:
        filepath = os.path.join(dataset_dir, file_info["filename"])
        if not os.path.exists(filepath):
            print(f"Warning: {filepath} not found!")
            continue
            
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        count = 0
        for raw_entry in data:
            kh = clean_khmer(raw_entry.get("khmer", ""))
            en = clean_english(raw_entry.get("english", ""))
            fr = clean_french(raw_entry.get("french", ""))
            pos = clean_pos(raw_entry.get("pos", ""))
            definition = raw_entry.get("definition", "").strip()
            examples = raw_entry.get("examples", "").strip()
            
            # Skip invalid entries (must have either Khmer or English)
            if not kh and not en:
                continue
            # Skip metadata/header entries from MPTC OCR text
            if "រាជបណ្ឌិត្យសភាកម្ពុជា" in kh or "សូមថ្លែងអំណរគុណ" in kh or "CONCH" in kh:
                continue
                
            dedup_key = f"{en.lower()}|{kh.lower()}"
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)
            
            entry_id = f"official_lex_{entry_counter:04d}"
            entry_counter += 1
            
            cleaned_entry = {
                "id": entry_id,
                "english": en,
                "khmer": kh,
                "french": fr,
                "pos": pos,
                "category": file_info["category"],
                "definition": definition,
                "examples": examples,
                "source": file_info["source_tag"],
                "author": file_info.get("author", ""),
                "version": file_info.get("version", ""),
                "year": file_info.get("year", "")
            }
            
            all_official_entries.append(cleaned_entry)
            count += 1
            
            # Build fast lookup dictionary
            if en and kh:
                en_key = en.lower()
                kh_key = kh.strip()
                
                if en_key not in en_to_kh_map:
                    en_to_kh_map[en_key] = {
                        "khmer": kh,
                        "english": en,
                        "french": fr,
                        "category": file_info["category"],
                        "source": file_info["source_tag"],
                        "author": file_info.get("author", ""),
                        "version": file_info.get("version", ""),
                        "year": file_info.get("year", "")
                    }
                    
                if kh_key not in kh_to_en_map:
                    kh_to_en_map[kh_key] = {
                        "khmer": kh,
                        "english": en,
                        "french": fr,
                        "category": file_info["category"],
                        "source": file_info["source_tag"],
                        "author": file_info.get("author", ""),
                        "version": file_info.get("version", ""),
                        "year": file_info.get("year", "")
                    }

        print(f"Processed {file_info['filename']}: {count} clean official entries")

    # 1. Save clean official unified dataset (EXCLUDING panhavonh)
    official_unified_path = os.path.join(dataset_dir, "unified_official_lexicon.json")
    with open(official_unified_path, "w", encoding="utf-8") as f:
        json.dump(all_official_entries, f, ensure_ascii=False, indent=2)
    print(f"\n✓ Saved {len(all_official_entries)} entries to {official_unified_path}")

    # Also overwrite unified_lexicon.json so the rest of the project pipeline (ChromaDB indexer, RAG, etc.) automatically uses ONLY official sources!
    unified_path = os.path.join(dataset_dir, "unified_lexicon.json")
    with open(unified_path, "w", encoding="utf-8") as f:
        json.dump(all_official_entries, f, ensure_ascii=False, indent=2)
    print(f"✓ Overwrote unified_lexicon.json with official entries (Panhavonh excluded)!")

    # 2. Save Fast-Lookup Index for instant pipeline query
    lookup_data = {
        "metadata": {
            "total_entries": len(all_official_entries),
            "sources": [f["source_tag"] for f in official_files],
            "excluded": ["panhavonh-glossary"]
        },
        "en_to_kh": en_to_kh_map,
        "kh_to_en": kh_to_en_map
    }
    
    lookup_path = os.path.join(dataset_dir, "official_lexicon_lookup.json")
    with open(lookup_path, "w", encoding="utf-8") as f:
        json.dump(lookup_data, f, ensure_ascii=False, indent=2)
    print(f"✓ Created fast lookup index at {lookup_path} (EN->KH: {len(en_to_kh_map)}, KH->EN: {len(kh_to_en_map)})")

if __name__ == "__main__":
    process_official_data()
