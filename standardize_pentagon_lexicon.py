import json
import os

source_file = "data/pentagon_lexicon.json"
dest_file = "data/ai_letter_writer/training_datasets/pentagon_lexicon.json"

with open(source_file, "r", encoding="utf-8") as f:
    data = json.load(f)

standardized = []
for item in data:
    standardized.append({
        "english": item.get("en", ""),
        "khmer": item.get("kh", ""),
        "french": "",
        "pos": "",
        "definition": "",
        "examples": "",
    })

os.makedirs(os.path.dirname(dest_file), exist_ok=True)
with open(dest_file, "w", encoding="utf-8") as f:
    json.dump(standardized, f, ensure_ascii=False, indent=2)

print(f"Standardized {len(standardized)} entries and saved to {dest_file}")
