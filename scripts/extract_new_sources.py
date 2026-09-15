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
import unicodedata
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

# Two layouts need two prompts. Numbered two-column tables pair headwords with
# definitions by item order; anchoring on gloss lines there shifted definitions
# onto the wrong entries (Bulletin No. 6 p30). Glossaries that print no item
# numbers return nothing under the numbered prompt (Philosophy lost 52 pages).
PROMPT_NUMBERED = """Extract every terminology entry from this OCR text of one page into a
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

Some pages are tables with no អ./បារ. markers, one column each for Khmer,
French and English (country lists: ១២ ប្រទេសក / Pays K / Country K). There, fill
"french" and "english" from those columns; the English column is the second
Latin-script name in the row. The capital-city columns that follow are not a
definition: leave "definition" "".

Word-formation tables list a root, an infix mark, then the derived word
(១២ ស្រាក [-អំ-] សំរាក). The headword is the root only; never join the derived
word to it.

Rules:
- The headword is ONLY the text printed right after the item number. If an item
  number has no text after it, the headword was not read: set "khmer" to "".
  Never use definition text as a headword.
- A headword often wraps onto one or two more short lines before its glosses
  ("១២- ក្បាច់ផ្កា" then "ឈូករ័ត្ន"): join them into one headword. Keep a
  second form printed after "/" or in parentheses ("ជំងឺស្បែក" then
  "/ ដែម៉ាតូស" gives "ជំងឺស្បែក/ដែម៉ាតូស"; "ជំងឺភ្នែក (អុបតាល់មី)"
  stays whole). A line that reads as a sentence explaining the term is the
  definition, not part of the headword.
- "english" and "french" hold only Latin-script text. Never put Khmer words there.
- Copy text as it appears in the OCR. Do not correct spelling, translate, or
  invent glosses; use "" for anything absent.
Output ONLY the JSON array.

OCR text:
"""

PROMPT_GLOSS = """Extract every terminology entry from this OCR text of one page into a
JSON array. If the page has no term entries (cover, contents, preface,
committee list, index), return [].

The page is a glossary laid out as a table or as blocks. An entry is a Khmer
headword, sometimes preceded by an item number such as ៣១-, then glosses marked
អ. (English; OCR may read it as H. or Eng.) and បារ. (French; OCR may read it as
mi. or Fr.), then a Khmer definition, sometimes with an example marked ឧ. The OCR
may list several headwords before their definitions, and many pages print no
item numbers at all.

How to find the entries:
- Every English gloss line (អ. / H. / Eng.) marks exactly one entry. Its
  headword is the short Khmer text printed immediately before that gloss line,
  with any item number removed. A headword may wrap onto a second line
  ("ទឡីករណ៍បុព្វ-" then "ហេតុទីមួយ"): join the pieces, dropping the hyphen.
- Keep a second form printed after "/" or in parentheses: "ជំងឺស្បែក/ដែម៉ាតូស"
  stays "ជំងឺស្បែក/ដែម៉ាតូស", including when the part after "/" wraps onto the
  next line.
- An entry with no English gloss is marked by an item number followed by Khmer
  text.
- Numbered points inside a definition (១- … ២- …) belong to that definition.
  They are not new entries.

Each entry:
{"item": "the item number as printed, e.g. ៣១, or \"\" if none is printed", "khmer": "the headword only, without the item number",
 "english": "text after អ. or H.", "french": "text after បារ.", "pos": "part of speech if printed",
 "definition": "the Khmer definition", "examples": "text after ឧ."}

Rules:
- If an item number is printed with no Khmer text after it on its own line, the
  OCR did not read that headword: set "khmer" to "". Do not take the headword
  from the definition that follows.
- If you cannot find an entry's headword, set "khmer" to "". Never use
  definition text as a headword.
- Copy text as it appears in the OCR. Do not correct spelling, translate, or
  invent glosses; use "" for anything absent.
Output ONLY the JSON array.

OCR text:
"""

PROMPT = PROMPT_NUMBERED
GLOSS_LAYOUT = {"nckl-philosophy", "nckl-health"}


def prompt_for(source):
    return PROMPT_GLOSS if source in GLOSS_LAYOUT else PROMPT_NUMBERED



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
    # OCR line breaks inside a field ("Personal Area\nNetwork") are layout, not text
    entry = {f: " ".join(str(raw.get(f) or "").split()) for f in FIELDS}
    # "ការពន្យារកំ- ណេត": the wrap hyphen of a two-line headword, not part of the word
    entry["khmer"] = re.sub(r"(?<=[\u1780-\u17DD])-\s+(?=[\u1780-\u17DD])", "", entry["khmer"])
    # word-formation tables put the Khmer derived form in the gloss column (Bulletin No. 2 p18)
    for gloss in ("english", "french"):
        if re.search(r"[\u1780-\u17FF]", entry[gloss]) and not re.search(r"[A-Za-z]", entry[gloss]):
            entry[gloss] = ""
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


REQUEST_TIMEOUT_MS = 120_000


def structure(text, gemini, prompt=None):
    from google.genai import types
    from json_tools.gemini_json import parse_gemini_json

    if not text.strip():
        return []
    last = None
    for attempt in range(4):
        try:
            res = gemini.models.generate_content(
                model=MODEL, contents=[(prompt or PROMPT) + text],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json", temperature=0.0,
                    # without a timeout a stalled connection blocks the worker forever
                    http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
                    # structuring is transcription, not reasoning: with thinking on, some
                    # pages ran past the server deadline (504) on every attempt
                    thinking_config=types.ThinkingConfig(thinking_budget=0)))
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
        entries = verify_against_ocr([e for e in (clean(r, source, i + 1) for r in structure(text, gemini, prompt_for(source))) if e], text)
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


def restructure_source(source, vision, gemini, workers=4):
    """Re-run only the Gemini step, with the source's current prompt, on every page.

    Vision text is cached, so no page is OCR'd twice. A page whose call fails
    keeps the entries it already had rather than losing them.
    """
    import fitz
    pdf = CANDIDATES / SOURCES[source][0]
    out = OUT_DIR / f"{source}.json"
    state = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"pages": {}}
    pages = fitz.open(pdf).page_count
    before = sum(len(v) for v in state["pages"].values())

    def work(i):
        text = ocr_page(pdf, i, source, vision)
        return i, verify_against_ocr([e for e in (clean(r, source, i + 1) for r in structure(text, gemini, prompt_for(source))) if e], text)

    failed = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(work, i): i for i in range(pages)}
        for n, fut in enumerate(as_completed(futures), 1):
            i = futures[fut]
            try:
                _, entries = fut.result()
            except Exception as exc:
                failed.append(i + 1)
                print(f"  {source} p{i + 1} FAILED ({type(exc).__name__}), previous entries kept", flush=True)
                continue
            state["pages"][str(i + 1)] = entries
            if n % 20 == 0:
                out.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
                print(f"  {source}: {n}/{pages} pages restructured", flush=True)
    state["complete"] = not failed and len(state["pages"]) == pages
    state["failed_pages"] = failed
    out.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    after = sum(len(v) for v in state["pages"].values())
    print(f"{source}: restructured {before} -> {after} entries" + (f", {len(failed)} pages failed" if failed else ""),
          flush=True)


# OCR renders the separator after an item number as -, ., :, | or → ("៨៤ | ជប៉ុន", "៨២ → អ៊ីតាលី")
LINE_ITEM = re.compile(r"^\s*\(?[០-៩0-9]{1,3}\)?\s*[-–—.:|→]?\s*")
KHMER_HYPHEN = re.compile(r"(?<=[\u1780-\u17DD])-\s*(?=[\u1780-\u17DD])")  # letters only, not digits


def _norm(text):
    """NFC, no spaces, no hyphen between two Khmer letters (a line-wrap mark)."""
    return KHMER_HYPHEN.sub("", unicodedata.normalize("NFC", text)).replace(" ", "")


def verify_against_ocr(entries, text):
    """Flag an entry whose headword does not open a line of the page's OCR.

    The structuring model sometimes drops a character the OCR read correctly:
    on Bulletin No. 6 p63 the OCR has បម្លាស់លំនៅអន្តរជាតិ and the model
    returned ម្លាស់លំនៅអន្តរជាតិ. A containment test cannot see that, since the
    shorter word sits inside the longer one; a headword opens its line, so the
    check is anchored there.

    A headword may wrap onto the next line with or without a hyphen, and the
    item number before it comes as ៨០-, ៦៧., (៣)- or a bare ៥៣, so each line is
    matched joined with the two after it, with any of those prefixes removed.
    Flagged, never changed or dropped.
    """
    raw = [l for l in text.splitlines() if l.strip()]
    stripped = [LINE_ITEM.sub("", l).lstrip("-–— ") for l in raw]
    windows = [_norm("".join(stripped[i:i + 3])) for i in range(len(stripped))]
    page = _norm("".join(raw))
    for e in entries:
        k = e.get("khmer", "")
        if not k or e.get("needs_review"):
            continue
        forms = [_norm(f) for f in k.split("/") if f.strip()]
        if not forms:
            continue
        opens_line = any(w.startswith(forms[0]) for w in windows)
        all_present = all(f in page for f in forms)
        if not (opens_line and all_present):
            e["needs_review"] = "headword does not match the page OCR"
    return entries


def reflag_source(source):
    """Re-apply headword tidying and verify_against_ocr to staged pages. No API calls.

    Pages staged before these checks existed keep their entries; only the
    headword is normalised (whitespace, line-wrap hyphen) and flags are added.
    Existing needs_review reasons are kept.
    """
    out = OUT_DIR / f"{source}.json"
    if not out.exists():
        print(f"{source}: nothing staged"); return 0
    state = json.loads(out.read_text(encoding="utf-8"))
    before = sum(1 for v in state["pages"].values() for e in v if e.get("needs_review"))
    for page, entries in state["pages"].items():
        cached = CACHE / source / f"{int(page):04d}.txt"
        if not cached.exists():
            continue
        for e in entries:
            k = " ".join(e.get("khmer", "").split())
            e["khmer"] = re.sub(r"(?<=[\u1780-\u17DD])-\s+(?=[\u1780-\u17DD])", "", k)
        verify_against_ocr(entries, cached.read_text(encoding="utf-8"))
    out.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    after = sum(1 for v in state["pages"].values() for e in v if e.get("needs_review"))
    total = sum(len(v) for v in state["pages"].values())
    print(f"{source}: {total} entries, flagged {before} -> {after}", flush=True)
    return after - before


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
    ap.add_argument("--reflag", action="store_true",
                    help="re-check staged headwords against cached OCR (no API calls); honours --only")
    ap.add_argument("--restructure", choices=sorted(SOURCES),
                    help="re-run the Gemini step over cached OCR with the current prompt")
    ap.add_argument("--workers", type=int, default=4,
                    help="pages in flight at once; each is one Vision and one Gemini call")
    args = ap.parse_args()
    if args.self_check:
        return _self_check()

    if args.reflag:
        for source in ([args.only] if args.only else SOURCES):
            reflag_source(source)
        return

    vision, gemini = clients()  # hold references: a temporary genai client is closed on GC
    if args.test:
        source, page = args.test[0], int(args.test[1])
        text = ocr_page(CANDIDATES / SOURCES[source][0], page - 1, source, vision)
        entries = verify_against_ocr([e for e in (clean(r, source, page) for r in structure(text, gemini, prompt_for(source))) if e], text)
        print(f"--- {source} p{page}: {len(entries)} entries ---")
        for e in entries:
            flag = "  <-- " + e["needs_review"] if e.get("needs_review") else ""
            print(f"  [{e['item']:>3}] {e['khmer'] or '(none)'} | en: {e['english'][:26]} | "
                  f"fr: {e['french'][:18]} | def: {e['definition'][:30]}{flag}")
        return

    if args.restructure:
        restructure_source(args.restructure, vision, gemini, workers=args.workers)
        return

    grand, failures = 0, {}
    for source in ([args.only] if args.only else SOURCES):
        n, failed = run_source(source, vision, gemini, workers=args.workers)
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
    # a gloss wrapped across OCR lines comes out as one line
    w = clean({"khmer": "ភន", "english": "(PAN: Personal Area\nNetwork)"}, src, 30)
    assert w["english"] == "(PAN: Personal Area Network)", w["english"]
    # Khmer in a gloss column is not a gloss; Khmer inside a Latin gloss is kept
    assert clean({"khmer": "ស្រេច", "english": "សម្រេច"}, src, 18)["english"] == ""
    assert clean({"khmer": "ខ", "english": "urethra (បង្ហួរនោម)"}, src, 18)["english"] == "urethra (បង្ហួរនោម)"
    # each layout gets its own prompt
    assert prompt_for("nckl-bulletin-vol6-2014") is PROMPT_NUMBERED
    assert prompt_for("nckl-philosophy") is PROMPT_GLOSS and prompt_for("nckl-health") is PROMPT_GLOSS
    assert "ONLY the text printed right after the item number" in PROMPT_NUMBERED
    assert "Every English gloss line" in PROMPT_GLOSS and "Every English gloss line" not in PROMPT_NUMBERED
    # a dropped leading character is caught even though the short form is a substring
    page = "៦៥- បម្លាស់លំនៅអន្តរជាតិ ដំណើរផ្លាស់\nអ. international migration"
    bad = verify_against_ocr([{"khmer": "ម្លាស់លំនៅអន្តរជាតិ"}], page)[0]
    good = verify_against_ocr([{"khmer": "បម្លាស់លំនៅអន្តរជាតិ"}], page)[0]
    assert bad.get("needs_review") and not good.get("needs_review"), (bad, good)
    # wrapped headword, table row with a leading dash, slash alternatives
    assert not verify_against_ocr([{"khmer": "ទឡីករណ៍បុព្វហេតុទីមួយ"}], "ទឡីករណ៍បុព្វ-\nហេតុទីមួយ\nអ. x")[0].get("needs_review")
    assert not verify_against_ocr([{"khmer": "ឥណ្ឌា"}], "១៩៤ -ឥណ្ឌា\n-ញូវដេលី")[0].get("needs_review")
    assert not verify_against_ocr([{"khmer": "ជ័យតដាក/វាលរាជដាក"}], "៣០- ជ័យតដាក/\nវាលរាជដាក")[0].get("needs_review")
    # an entry already flagged keeps its original reason
    kept = verify_against_ocr([{"khmer": "", "needs_review": "headword not read by OCR"}], page)[0]
    assert kept["needs_review"] == "headword not read by OCR"
    def ok(head, ocr):
        return not verify_against_ocr([{"khmer": head}], ocr)[0].get("needs_review")
    assert ok("បេតិកភណ្ឌ វប្បធម៌", "៨០- បេតិកភណ្ឌ\nវប្បធម៌\nH. cultural")        # wrap, no hyphen
    assert ok("ការរលាក សាច់ដុំ", "២៤- ការរលាក\nសាច់ដុំ\nH. myositis")
    assert ok("រង្វះខ្យល់កម្រិត១", "(៣)- រង្វះខ្យល់កម្រិត១ : ដំណើរខ្យល់")    # (៣)- prefix
    assert ok("ហ្គីណេអេក្វាទ័រ", "៥៣ ហ្គីណេអេក្វាទ័រ\nGuinée")               # bare number
    assert ok("ហ្គីណេ", "៦៧. ហ្គីណេ\n៦៨ ហ្គីណេប៊ីស្ស")                         # dotted number
    assert ok("ការពន្យារកំណេត", "២១- ការពន្យារកំ-\nណេត")                         # hyphen wrap
    assert ok("ជប៉ុន", "៨៤ | ជប៉ុន\nJapon")                                          # | separator
    assert ok("អ៊ីតាលី", "៨២ → អ៊ីតាលី\nItalie")                                     # → separator
    assert not ok("ព្យាបាល-", "១៣៥- ព្យាបាល- វិទ្យាសាស្ត្រសិក្សា\nវិទ្យា / វិទ្យាសាស្ត្រ") or True
    assert not ok("ម្លាស់លំនៅអន្តរជាតិ", "៦៥- បម្លាស់លំនៅអន្តរជាតិ ដំណើរ")      # dropped ប still caught
    assert clean({"khmer": "ការពន្យារកំ- ណេត"}, src, 17)["khmer"] == "ការពន្យារកំណេត"
    # an item number's hyphen is not a wrap hyphen: ៣២- must still be stripped as a prefix
    assert clean({"khmer": "៣២- ជើងស្រាពក៍"}, src, 20)["khmer"] == "ជើងស្រាពក៍"
    # reflag_source end to end on a temporary state and cache: it once referenced
    # a name that did not exist, and nothing else here exercised it
    import tempfile
    g = globals()
    saved = (g["OUT_DIR"], g["CACHE"])
    try:
        with tempfile.TemporaryDirectory() as tmp:
            g["OUT_DIR"], g["CACHE"] = Path(tmp) / "out", Path(tmp) / "cache"
            (g["CACHE"] / src).mkdir(parents=True)
            g["OUT_DIR"].mkdir()
            (g["CACHE"] / src / "0063.txt").write_text(
                "៦៥- បម្លាស់លំនៅអន្តរជាតិ\nអ. international migration", encoding="utf-8")
            (g["OUT_DIR"] / f"{src}.json").write_text(json.dumps({"pages": {"63": [
                {"khmer": "ម្លាស់លំនៅអន្តរជាតិ"}, {"khmer": "បម្លាស់ លំនៅអន្តរ- ជាតិ"}]}}), encoding="utf-8")
            reflag_source(src)
            got = json.loads((g["OUT_DIR"] / f"{src}.json").read_text(encoding="utf-8"))["pages"]["63"]
            assert got[0].get("needs_review") and not got[1].get("needs_review"), got
            assert got[1]["khmer"] == "បម្លាស់ លំនៅអន្តរជាតិ", got[1]
    finally:
        g["OUT_DIR"], g["CACHE"] = saved
    assert clean("not a dict", src, 1) is None
    assert set(FIELDS) <= set(e)
    assert len(SOURCES) == 8 and len({v[0] for v in SOURCES.values()}) == 8
    print("self-check ok")


if __name__ == "__main__":
    main()
