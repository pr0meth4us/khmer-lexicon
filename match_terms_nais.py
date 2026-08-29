import re
import json

en_file = "/Users/nicksng/code/egd platform/data/ai_letter_writer/nais_v5_en_parsed.md"
kh_file = "/Users/nicksng/code/egd platform/data/ai_letter_writer/nais_v5_kh_parsed.md"

with open(en_file, "r", encoding="utf-8") as f:
    en_text = f.read()

with open(kh_file, "r", encoding="utf-8") as f:
    kh_text = f.read()

terms_to_find = ["chatbot", "chatbots", "prompt", "instruction", "commands", "listen"]

print("--- Term Matches in NAIS v5 English vs Khmer ---\n")

for term in terms_to_find:
    print(f"=== Term: '{term}' ===")
    pattern = re.compile(rf'([^.\n]*?{term}[^.\n]*?\.)', re.IGNORECASE)
    matches_en = pattern.findall(en_text)
    for m in matches_en:
        print(f"[EN]: {m.strip()}")
    print()

# Search Khmer text for Chatbot / Prompt / Command translations
print("=== Khmer Chatbot / Prompt / Command Contexts ===")
kh_patterns = [
    (r'([^.\n]*?ឆាតបូត[^.\n]*?\.)', "ឆាតបូត (Chatbot)"),
    (r'([^.\n]*?ឆាតប៊ូត[^.\n]*?\.)', "ឆាតប៊ូត (Chatbot)"),
    (r'([^.\n]*?ពាក្យបញ្ជា[^.\n]*?\.)', "ពាក្យបញ្ជា (Command / Instruction / Prompt)"),
    (r'([^.\n]*?សេចក្តីណែនាំ[^.\n]*?\.)', "សេចក្តីណែនាំ (Instruction / Prompt)"),
    (r'([^.\n]*?ជំនួយការនិម្មិត[^.\n]*?\.)', "ជំនួយការនិម្មិត (Virtual Assistant)")
]

for pat, label in kh_patterns:
    print(f"\n--- {label} ---")
    matches_kh = re.findall(pat, kh_text)
    for m in matches_kh:
        print(f"[KH]: {m.strip()}")
