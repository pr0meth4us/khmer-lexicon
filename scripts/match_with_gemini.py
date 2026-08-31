import sys
import os
import time

# 1. Dynamically inject GOOGLE_APPLICATION_CREDENTIALS as per user rule
# We use the explicit path mentioned in the rules for the service account
gcp_creds = "/Users/nicksng/code/egd platform/claude.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gcp_creds

from google import genai

# 2. Initialize with vertexai=True, region us-central1
client = genai.Client(
    vertexai=True, 
    project="egd-ai-services-1782364268", 
    location="us-central1"
)

eng_file = "/Users/nicksng/code/egd platform/data/egd-master-docs/Enterprises Go Digital Program_ocr_transcription.txt"
khm_file = "/Users/nicksng/.gemini/antigravity-ide/brain/eb6df402-0643-44b2-ae93-172ada213240/scratch/ocr_output.md"
out_file = "/Users/nicksng/.gemini/antigravity-ide/brain/eb6df402-0643-44b2-ae93-172ada213240/scratch/matched_terms_llm.md"

with open(eng_file, "r", encoding="utf-8") as f:
    eng_text = f.read()

with open(khm_file, "r", encoding="utf-8") as f:
    khm_text = f.read()

prompt = f"""
You are an expert bilingual technical translator for the Cambodian government. 
I am providing you with two versions of the exact same policy document ("Enterprises Go Digital Program"), one in English and one in Khmer (which was OCR'd from a PDF).

Your task: Extract a highly accurate technical glossary of terms.
1. Identify the key technical, programmatic, and business terms in the English version (e.g. Digital Adoption, Digital Service Provider, Enterprises Go Digital Program, Digital Readiness Assessment, Grant Voucher, Ecosystem, Integration, Informal Economy, etc.).
2. Find their EXACT official Khmer translation used in the provided Khmer OCR text. (The Khmer document is the direct translation of the English one).
3. Output the result purely as a Markdown table with two columns: | English Term | Official Khmer Translation |
4. Do NOT output any other text, just the Markdown table. Ensure high accuracy. Do not hallucinate translations; find them in the Khmer text. 
Sort alphabetically by English.

<ENGLISH_DOCUMENT>
{eng_text}
</ENGLISH_DOCUMENT>

<KHMER_DOCUMENT_OCR>
{khm_text}
</KHMER_DOCUMENT_OCR>
"""

print("Sending documents to Vertex AI (us-central1) for extraction and matching...")
start_time = time.time()
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=prompt
)
elapsed = time.time() - start_time

result = response.text.strip()
if result.startswith("```markdown"):
    result = result[11:-3].strip()
elif result.startswith("```"):
    result = result[3:-3].strip()

with open(out_file, "w", encoding="utf-8") as f:
    f.write(result)

print(f"Done in {elapsed:.2f}s. Saved to {out_file}")
