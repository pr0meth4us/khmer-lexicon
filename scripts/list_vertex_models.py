import sys
import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")

from google import genai

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_PDFS = os.environ.get("LEXICON_SOURCE_PDFS", os.path.join(ROOT, "source_pdfs"))
BUILD_DIR = os.environ.get("LEXICON_BUILD_DIR", os.path.join(ROOT, "build"))
DIST_DIR = os.environ.get("LEXICON_DIST_DIR", os.path.join(ROOT, "dist"))


client = genai.Client(
    vertexai=True, 
    project="egd-ai-services-1782364268", 
    location="us-central1"
)

print("Listing models...")
for model in client.models.list():
    print(model.name)
