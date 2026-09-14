"""Identify the recovered NCKL PDFs in source_pdfs/candidates/.

    python scripts/identify_candidates.py                    # all, Cloud Vision
    python scripts/identify_candidates.py 203.pdf 216.pdf    # just these
    python scripts/identify_candidates.py --backend gemini   # see warning below
    python scripts/identify_candidates.py --self-check

Page reading is generic and lives in ~/code/random (ocr_tools/pdf_page_reader).
What stays here is NCKL-specific: which folder, which Khmer words mark a
document's type, and how a year is read off a Cambodian government page.

Backend: Cloud Vision by default. Gemini was tried first and is not trustworthy
for this — checked against their pages, 203/216/217 came back with invented
title subjects (an IT glossary for a 2008 sub-decree; the Royal Academy swapped
for a ministry, with a Thai character in the Khmer) from both flash and pro.
Vision must be enabled on the project:
    gcloud services enable vision.googleapis.com --project khmer-ocr-496606
"""
import argparse
import glob
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.expanduser("~/code/random"))
from ocr_tools.pdf_page_reader import ocr_pdf_pages, transcribe_pdf_pages  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES_DIR = os.path.join(ROOT, "source_pdfs", "candidates")
OUTPUT_FILE = os.path.join(ROOT, "dist", "candidate_identifications.json")

# First word found near the top of page 1 decides the type. Decrees list the
# laws they cite in the body, so only the opening lines are searched.
KIND_WORDS = [
    ("ព្រះរាជក្រឹត្យ", "law-or-decree"), ("ព្រះរាជក្រម", "law-or-decree"),
    ("អនុក្រឹត្យ", "law-or-decree"), ("សេចក្តីសម្រេច", "law-or-decree"),
    ("ប្រកាស", "law-or-decree"), ("សារាចរ", "law-or-decree"),
    ("ព្រឹត្តិបត្រ", "bulletin"), ("BULLETIN", "bulletin"),
    ("សទ្ទានុក្រម", "terminology-glossary"), ("LEXICON", "terminology-glossary"),
    ("វចនានុក្រម", "dictionary"), ("វេយ្យាករណ៍", "grammar"),
    ("របាយការណ៍", "report"),
]
TITLE_LINES = 12
KHMER_DIGITS = str.maketrans("០១២៣៤៥៦៧៨៩", "0123456789")
YEAR = re.compile(r"(?<!\d)(19[5-9]\d|20[0-4]\d)(?!\d)")

GEMINI_SCHEMA = """These images are pages from ONE scanned Cambodian government PDF,
each preceded by its page label. Return ONE JSON object:
{
  "title_lines": ["largest or boldest heading lines on the first page, in reading order"],
  "date_lines": [{"page": 1, "text": "a printed line containing a date"}],
  "term_entry_example": {"page": 1, "text": "a line with a Khmer headword beside an English or French gloss"}
}
term_entry_example must be a real dictionary-style entry, else null."""


def fold(text):
    """្ត and ្ដ compare equal: the sources use both for the same word."""
    return text.replace("្ដ", "្ត")


def classify(lines):
    """Type from the type word printed EARLIEST in the lines.

    Not the first word in KIND_WORDS order: a sub-decree's opening lines already
    cite a royal decree (បានឃើញព្រះរាជក្រឹត្យ… on line 10 of 203.pdf, below the
    អនុក្រឹត្យ title on line 5), and list order picked the citation.
    """
    text = fold(" ".join(lines or []))
    upper = text.upper()
    hits = []
    for word, kind in KIND_WORDS:
        at = upper.find(fold(word).upper())
        if at >= 0:
            hits.append((at, word, kind))
    if hits:
        _, word, kind = min(hits)
        return kind, word
    return ("other" if text.strip() else "indeterminate"), None


def years_in(text):
    return [int(y) for y in YEAR.findall((text or "").translate(KHMER_DIGITS))]


def from_vision(texts):
    """Classify from {page_index: OCR text}. The year is the latest one on the
    last page (signature or colophon), else the latest on page 1."""
    first = texts.get(min(texts), "") if texts else ""
    last = texts.get(max(texts), "") if texts else ""
    top = [l for l in first.splitlines() if l.strip()][:TITLE_LINES]
    kind, word = classify(top)
    years = years_in(last) or years_in(first)
    return {"doc_type": kind, "doc_type_from_word": word,
            "title_area": " / ".join(top) or None,
            "year": max(years) if years else None}


def identify(path, backend, client):
    name = os.path.basename(path)
    try:
        if backend == "vision":
            texts = ocr_pdf_pages(path, client=client)
            row = from_vision(texts)
            row["ocr"] = {str(k + 1): v for k, v in texts.items()}
        else:
            copied, _ = transcribe_pdf_pages(path, GEMINI_SCHEMA, client)
            kind, word = classify(copied.get("title_lines"))
            years = [y for d in copied.get("date_lines") or []
                     for y in years_in(d.get("text") if isinstance(d, dict) else d)]
            row = {"doc_type": kind, "doc_type_from_word": word,
                   "title_area": " / ".join(copied.get("title_lines") or []) or None,
                   "year": max(years) if years else None, "copied": copied,
                   "warning": "gemini output: verify against the page"}
    except Exception as exc:
        return {"source": name, "doc_type": "error",
                "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
    return {"source": name, "backend": backend, **row}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--backend", choices=("vision", "gemini"), default="vision")
    ap.add_argument("--out", default=OUTPUT_FILE)
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()
    if args.self_check:
        return _self_check()

    paths = ([os.path.join(CANDIDATES_DIR, f) for f in args.files] if args.files
             else sorted(glob.glob(os.path.join(CANDIDATES_DIR, "*.pdf")),
                         key=lambda p: int(os.path.basename(p).split(".")[0])))
    results = []
    if os.path.exists(args.out):
        with open(args.out, encoding="utf-8") as fh:
            results = [r for r in json.load(fh) if r.get("doc_type") != "error"]
    done = {r["source"] for r in results}
    todo = [p for p in paths if os.path.basename(p) not in done]
    print(f"{len(todo)} to process ({len(paths) - len(todo)} done), backend={args.backend}")

    if args.backend == "vision":
        from ocr_tools.pdf_ocr import _default_vision_client
        client = _default_vision_client()
    else:
        from gemini_tools.transcribe_audio import get_vertex_client
        client = get_vertex_client(location="us-central1")  # pro is not in asia-southeast1

    for i, path in enumerate(todo, 1):
        row = identify(path, args.backend, client)
        print(f"[{i}/{len(todo)}] {row['source']}: {row['doc_type']} {row.get('year') or ''} "
              f"{(row.get('title_area') or row.get('error') or '')[:70]}", flush=True)
        results = [r for r in results if r["source"] != row["source"]] + [row]
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=2)
        time.sleep(0.5)


def _self_check():
    assert classify(["អនុក្រឹត្យ", "ស្ដីពី"]) == ("law-or-decree", "អនុក្រឹត្យ")
    assert classify(["សេចក្ដីសម្រេច"])[0] == "law-or-decree"  # ្ដ spelling still matches
    assert classify(["BULLETIN OF THE NATIONAL COUNCIL"])[0] == "bulletin"
    assert classify([]) == ("indeterminate", None)
    # 203.pdf: title word on line 5 beats a royal decree cited on line 10
    assert classify(["រាជរដ្ឋភិបាលកម្ពុជា", "អនុក្រឹត្យ", "ស្តីពី",
                     "បានឃើញព្រះរាជក្រឹត្យលេខ នស/រកត"]) == ("law-or-decree", "អនុក្រឹត្យ")
    assert classify(["មាតិកា", "សទ្ទានុក្រម វប្បធម៌", "ព្រឹត្តិបត្រ លេខ៧"])[1] == "សទ្ទានុក្រម"
    assert years_in("ថ្ងៃទី៦ ខែកញ្ញា ឆ្នាំ២០១៨ លេខ ១៨៨") == [2018]
    # signature year on the last page beats years cited on page 1
    row = from_vision({0: "រាជរដ្ឋាភិបាល\nអនុក្រឹត្យ\nចុះថ្ងៃ ឆ្នាំ២០០៤", 1: "ភ្នំពេញ ឆ្នាំ ២០០៨"})
    assert (row["doc_type"], row["year"]) == ("law-or-decree", 2008), row
    # a type word cited deep in the body must not decide the type
    body = "\n".join(["ព្រះរាជាណាចក្រកម្ពុជា"] + ["-"] * TITLE_LINES + ["ព្រឹត្តិបត្រ"])
    assert from_vision({0: body})["doc_type"] == "other"
    print("self-check ok")


if __name__ == "__main__":
    main()
