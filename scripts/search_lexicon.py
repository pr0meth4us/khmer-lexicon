import json

filepath = "/Users/nicksng/code/egd platform/data/ai_letter_writer/training_datasets/unified_official_lexicon.json"

with open(filepath, "r", encoding="utf-8") as f:
    data = json.load(f)

queries = [
    "business",
    "development",
    "digital",
    "root",
    "cause",
    "diagnostic"
]

results = {q: [] for q in queries}

for entry in data:
    eng = str(entry.get("english", "")).lower()
    khm = entry.get("khmer", "")
    for q in queries:
        # Search for exact word match (surrounded by bounds) to avoid partial matches like "business" in "businesses"
        import re
        if re.search(r'\b' + re.escape(q) + r'\b', eng):
            results[q].append(f"- **{entry.get('english')}**: {khm} *(Source: {entry.get('source', 'Unknown')})*")

for q, res in results.items():
    print(f"### Matches for base word '{q}'")
    if not res:
        print("*(No direct matches found)*\n")
    else:
        unique_res = list(set(res))
        for r in unique_res[:10]:
            print(r)
        if len(unique_res) > 10:
            print(f"... and {len(unique_res) - 10} more.")
        print()
