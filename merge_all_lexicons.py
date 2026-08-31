import os
import json

dataset_dir = "/Users/nicksng/code/egd platform/data/ai_letter_writer/training_datasets"

files_to_merge = [
    ("unified_lexicon.json", "panhavonh-glossary"),
    ("mptc_lexicon.json", "mptc-digital-lexicon"),
    ("nckl_political_science_lexicon.json", "nckl-political-science-and-diplomacy"),
    ("legal_terms_lexicon.json", "council-of-ministers-legal-terms")
]

master_lexicon = []

for filename, default_source in files_to_merge:
    filepath = os.path.join(dataset_dir, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"Loaded {len(data)} entries from {filename}")
            for item in data:
                if "source" not in item or not item["source"]:
                    item["source"] = default_source
                master_lexicon.append(item)

unified_path = os.path.join(dataset_dir, "unified_lexicon.json")
with open(unified_path, "w", encoding="utf-8") as f:
    json.dump(master_lexicon, f, ensure_ascii=False, indent=2)

local_dist_path = os.path.join(os.path.dirname(__file__), "dist", "unified_lexicon.json")
os.makedirs(os.path.dirname(local_dist_path), exist_ok=True)
with open(local_dist_path, "w", encoding="utf-8") as f:
    json.dump(master_lexicon, f, ensure_ascii=False, indent=2)

print(f"\n✓ Successfully compiled master unified_lexicon.json with {len(master_lexicon)} total entries!")
print(f"✓ Saved to {unified_path} and {local_dist_path}")
