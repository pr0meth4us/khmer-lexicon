import sys
import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/nicksng/code/egd platform/claude.json"

from google import genai

client = genai.Client(
    vertexai=True, 
    project="egd-ai-services-1782364268", 
    location="us-central1"
)

print("Listing models...")
for model in client.models.list():
    print(model.name)
