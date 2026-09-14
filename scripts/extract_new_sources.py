"""Extract terms from the 8 NCKL documents recovered from archived captures.

    python scripts/extract_new_sources.py --test nckl-culture-and-fine-arts 20
    python scripts/extract_new_sources.py                 # all 8, resumable
    python scripts/extract_new_sources.py --only nckl-philosophy
    python scripts/extract_new_sources.py --self-check

Same two steps as the original pipeline: Cloud Vision OCRs each page, then
Gemini structures that OCR text into entries. Gemini never sees a page image —
on these scans it invents text (see scripts/identify_candidates.py).

Output is staged in build/new_sources/<source>.json and NOT merged into
dist/unified_lexicon.json: v1.0 is being evaluated as it stands, and folding
827 new pages into it mid-evaluation would make the measured error rate
describe a different dataset. Each entry also records the page it came from,
which the existing sources never did.

Resumable at page level. OCR text is cached, so a rerun does not pay Vision
again. A page that fails is logged and retried next run — never saved as an
empty page, which would silently drop its terms for good.
"""
import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/code/random"))

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = ROOT / "source_pdfs" / "candidates"
BUILD = Path(os.environ.get("LEXICON_BUILD_DIR", ROOT / "build"))
OUT_DIR = BUILD / "new_sources"
CACHE = BUILD / "ocr_cache"
MODEL = "gemini-2.5-flash"
NCKL = "National Council of Khmer Language (NCKL)"

SOURCES = {
    "nckl-linguistics-and-literature": ("219.pdf", "Linguistics & Literature", "2013"),
    "nckl-culture-and-fine-arts": ("227.pdf", "Culture & Fine Arts", "2015"),
    "nckl-medicine-and-agriculture": ("230.pdf", "Medicine & Agriculture", "2015"),
    "nckl-philosophy": ("240.pdf", "Philosophy", "2019"),
    "nckl-health": ("241.pdf", "Health", "2019"),
    "nckl-bulletin-vol6-2014": ("231.pdf", "General & Specialized Terms (NCKL Bulletin)", "2014"),
    "nckl-bulletin-vol2-2009": ("235.pdf", "General & Specialized Terms (NCKL Bulletin)", "2009"),
    "nckl-bulletin-vol1-2008": ("236.pdf", "General & Specialized Terms (NCKL Bulletin)", "2008"),
}
FIELDS = ("khmer", "english", "french", "pos", "definition", "examples")

PROMPT = """Extract every terminology entry from this OCR text of one page into a
JSON array. If the page has no term entries (cover, contents, preface,
committee list, index), return [].

The page is a two-column table. Left cell: an item number such as ៣១- followed
by the Khmer headword, then glosses marked អ. (English; OCR sometimes reads it
as H.) and បារ. (French). Right cell: the Khmer definition, then an example
marked ឧ. The OCR often lists several left cells before their right cells, so
pair them by item number and order.

Each entry:
{"item": "the item number as printed, e.g. ៣១", "khmer": "the headword only, without the item number",
 "english": "text after អ. or H.", "french": "text after បារ.", "pos": "part of speech if printed",
 "definition": "the Khmer definition", "examples": "text after ឧ."}

Rules:
- The headword is ONLY the text printed right after the item number. If an item
  number has no text after it, the headword was not read: set "khmer" to "".
  Never use definition text as a headword.
- Copy text as it appears in the OCR. Do not correct spelling, translate, or
  invent glosses; use "" for anything absent.
Output ONLY the JSON array.

OCR text:
"""


ITEM_PREFIX = re.compile(r"^\s*([០-៩0-9]+)\s*[-–—.]\s*")


def clean(raw, source, page):
    """Normalise one model entry.

    Strips a leading item number (៣១-) from the headword. An entry whose
    headword the OCR did not read is kept and marked needs_review rather than
    dropped: its definition is real, and dropping it would lose the term
    silently. None only if the entry is empty.
    """
    if not isinstance(raw, dict):
        return None
    entry = {f: str(raw.get(f) or "").strip() for f in FIELDS}
    item = str(raw.get("item") or "").strip()
    match = ITEM_PREFIX.match(entry["khmer"])
    if match:
        item = item or match.group(1)
        entry["khmer"] = entry["khmer"][match.end():].strip()
    if not any(entry.values()):
        return None
    category, year = SOURCES[source][1], SOURCES[source][2]
    out = {**entry, "category": category, "source": source, "author": NCKL,
           "version": "1.0", "year": year, "page": page, "item": item}
    if not entry["khmer"]:
        out["needs_review"] = "headword not read by OCR"
    return out


def ocr_page(pdf, index, source, vision):
    from ocr_tools.pdf_ocr import ocr_image, render_pdf_page
    import fitz

    cached = CACHE / source / f"{index + 1:04d}.txt"
    if cached.exists():
        return cached.read_text(encoding="utf-8")
    doc = fitz.open(pdf)
    try:
        text = ocr_image(render_pdf_page(doc, index, dpi=200), vision)
    finally:
        doc.close()
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(text, encoding="utf-8")
    return text


def structure(text, gemini):
    from google.genai import types
    from json_tools.gemini_json import parse_gemini_json

    if not text.strip():
        return []
    last = None
    for attempt in range(4):
        try:
            res = gemini.models.generate_content(
                model=MODEL, contents=[PROMPT + text],
                config=types.GenerateContentConfig(response_mime_type="application/json",
                                                   temperature=0.0))
            data = parse_gemini_json(res.text)
            return data if isinstance(data, list) else []
        except Exception as exc:
            last = exc
            time.sleep(3 * (attempt + 1))
    raise last


def run_source(source, vision, gemini, workers=4):
    filename = SOURCES[source][0]
    pdf = CANDIDATES / filename
    import fitz
    pages = fitz.open(pdf).page_count
    out = OUT_DIR / f"{source}.json"
    state = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"pages": {}}
    todo = [i for i in range(pages) if str(i + 1) not in state["pages"]]
    print(f"{source}: {pages} pages, {len(todo)} to do", flush=True)

    def work(i):
        text = ocr_page(pdf, i, source, vision)
        entries = [e for e in (clean(r, source, i + 1) for r in structure(text, gemini)) if e]
        return i, entries

    failed = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(work, i): i for i in todo}
        for n, fut in enumerate(as_completed(futures), 1):
            i = futures[fut]
            try:
                _, entries = fut.result()
            except Exception as exc:
                failed.append(i + 1)
                print(f"  {source} p{i + 1} FAILED ({type(exc).__name__}: {str(exc)[:90]}), retry next run",
                      flush=True)
                continue
            state["pages"][str(i + 1)] = entries
            if n % 10 == 0 or n == len(todo):
                done = sum(len(v) for v in state["pages"].values())
                print(f"  {source}: {len(state['pages'])}/{pages} pages, {done} entries", flush=True)
                OUT_DIR.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    state["complete"] = not failed and len(state["pages"]) == pages
    state["failed_pages"] = failed
    out.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(len(v) for v in state["pages"].values())
    print(f"{source}: DONE {total} entries" + (f", {len(failed)} pages failed" if failed else ""),
          flush=True)
    return total, failed


def clients():
    from gemini_tools.transcribe_audio import get_vertex_client
    from ocr_tools.pdf_ocr import _default_vision_client
    return _default_vision_client(), get_vertex_client()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=sorted(SOURCES))
    ap.add_argument("--test", nargs=2, metavar=("SOURCE", "PAGE"))
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()
    if args.self_check:
        return _self_check()

    vision, gemini = clients()  # hold references: a temporary genai client is closed on GC
    if args.test:
        source, page = args.test[0], int(args.test[1])
        text = ocr_page(CANDIDATES / SOURCES[source][0], page - 1, source, vision)
        entries = [e for e in (clean(r, source, page) for r in structure(text, gemini)) if e]
        print(f"--- {source} p{page}: {len(entries)} entries ---")
        for e in entries:
            flag = "  <-- " + e["needs_review"] if e.get("needs_review") else ""
            print(f"  [{e['item']:>3}] {e['khmer'] or '(none)'} | en: {e['english'][:26]} | "
                  f"fr: {e['french'][:18]} | def: {e['definition'][:30]}{flag}")
        return

    grand, failures = 0, {}
    for source in ([args.only] if args.only else SOURCES):
        n, failed = run_source(source, vision, gemini)
        grand += n
        if failed:
            failures[source] = failed
    print(f"\nALL DONE: {grand} entries staged in {OUT_DIR}")
    if failures:
        print("pages to retry (rerun the same command):", failures)


def _self_check():
    src = "nckl-philosophy"
    e = clean({"khmer": " ទស្សនវិជ្ជា ", "english": "philosophy", "pos": None}, src, 12)
    assert e["khmer"] == "ទស្សនវិជ្ជា" and e["pos"] == "" and e["page"] == 12
    assert (e["source"], e["year"], e["author"]) == (src, "2019", NCKL)
    # item number stripped from the headword and kept separately
    n = clean({"khmer": "៣២- ជើងស្រាពក៍", "definition": "ជើងទម្រ"}, src, 20)
    assert (n["khmer"], n["item"]) == ("ជើងស្រាពក៍", "៣២"), n
    assert "needs_review" not in n
    # an unread headword is kept and flagged, not dropped and not guessed
    r = clean({"item": "៣១", "khmer": "", "definition": "ខ្នាតខ្មែរពីបុរាណ"}, src, 20)
    assert r["needs_review"] and r["khmer"] == "" and r["item"] == "៣១", r
    assert clean({"khmer": "", "english": ""}, src, 1) is None
    assert clean("not a dict", src, 1) is None
    assert set(FIELDS) <= set(e)
    assert len(SOURCES) == 8 and len({v[0] for v in SOURCES.values()}) == 8
    print("self-check ok")


if __name__ == "__main__":
    main()
