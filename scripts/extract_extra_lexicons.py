import os
import sys

# Add the scratch directory to Python path so we can import the extraction logic
sys.path.append("/Users/nicksng/code/khmer-lexicon")
from extract_lexicons_cloud_vision import process_pdf

def main():
    target_dir = "/Users/nicksng/code/ោក"
    out_dir = "/Users/nicksng/code/egd platform/data/ai_letter_writer/training_datasets"
    
    pdfs = [
        {
            "pdf": os.path.join(target_dir, "/Users/nicksng/code/khmer-lexicon/source_pdfs/RAC_New_Words_2018.pdf"),
            "source_name": "extra-lexicon-1",
            "out": os.path.join(out_dir, "extra_lexicon_1.json")
        },
        {
            "pdf": os.path.join(target_dir, "/Users/nicksng/code/khmer-lexicon/source_pdfs/NCKL_Country_and_City_Names_2013.pdf"),
            "source_name": "country-and-city-names",
            "out": os.path.join(out_dir, "country_and_city_names_lexicon.json")
        },
        {
            "pdf": os.path.join(target_dir, "/Users/nicksng/code/khmer-lexicon/source_pdfs/NCKL_Economics_2019.pdf"),
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
