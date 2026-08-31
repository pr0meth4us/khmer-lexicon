import os
import sys

# Add the scratch directory to Python path so we can import the extraction logic
sys.path.append(os.path.join(BUILD_DIR, "khmer-lexicon"))
from extract_lexicons_cloud_vision import process_pdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_PDFS = os.environ.get("LEXICON_SOURCE_PDFS", os.path.join(ROOT, "source_pdfs"))
BUILD_DIR = os.environ.get("LEXICON_BUILD_DIR", os.path.join(ROOT, "build"))
DIST_DIR = os.environ.get("LEXICON_DIST_DIR", os.path.join(ROOT, "dist"))


def main():
    target_dir = os.path.join(BUILD_DIR, "ោក")
    out_dir = BUILD_DIR
    
    pdfs = [
        {
            "pdf": os.path.join(SOURCE_PDFS, "RAC_New_Words_2018.pdf"),
            "source_name": "extra-lexicon-1",
            "out": os.path.join(out_dir, "extra_lexicon_1.json")
        },
        {
            "pdf": os.path.join(SOURCE_PDFS, "NCKL_Country_and_City_Names_2013.pdf"),
            "source_name": "country-and-city-names",
            "out": os.path.join(out_dir, "country_and_city_names_lexicon.json")
        },
        {
            "pdf": os.path.join(SOURCE_PDFS, "NCKL_Economics_2019.pdf"),
            "source_name": "extra-lexicon-2",
            "out": os.path.join(out_dir, "extra_lexicon_2.json")
        }
    ]
    
    for src in pdfs:
        print(f"Starting extraction for {src['source_name']}...")
        process_pdf(src["pdf"], src["source_name"], src["out"])
        
    print("\nAll extra extractions completed successfully!")

if __name__ == "__main__":
    main()
