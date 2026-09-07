"""Export dist/unified_lexicon.json to TBX (ISO 30042:2019, TBX-Basic).

    python scripts/export_tbx.py [-o dist/unified_lexicon.tbx]

One <conceptEntry> per lexicon row, with a <langSec> per non-empty language
field. Provenance (source document, issuing body, year) is attached at the
concept level as TBX-Basic <admin type="source">.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

BASE = Path(__file__).resolve().parent.parent
DEFAULT_IN = BASE / "dist" / "unified_lexicon.json"
DEFAULT_OUT = BASE / "dist" / "unified_lexicon.tbx"

# The `pos` field is inconsistent across sources: Khmer abbreviations from the
# NCKL bulletins, French gender markers from the country-name lists, and plain
# English elsewhere. Normalise to the TBX-Basic partOfSpeech picklist; anything
# unrecognised is dropped rather than guessed at.
POS_MAP = {
    "ន.": "noun", "ន": "noun", "noun": "noun", "n.": "noun", "n": "noun",
    "កិ.": "verb", "កិ": "verb", "verb": "verb", "v.": "verb", "v": "verb",
    "គុ.": "adjective", "adj.": "adjective", "adj": "adjective",
    "adjective": "adjective",
    "កិ.វិ.": "adverb", "adv.": "adverb", "adv": "adverb", "adverb": "adverb",
    "proper noun": "properNoun", "country": "properNoun",
    "capital": "properNoun", "city": "properNoun",
    "proper noun (country)": "properNoun",
    "proper noun (capital)": "properNoun",
}
# French gender markers are not a part of speech — in TBX they are
# grammaticalGender, and they imply the term is a noun.
GENDER_MAP = {"m": "masculine", "m.": "masculine", "(m.)": "masculine",
              "f": "feminine", "f.": "feminine", "(f.)": "feminine"}


def parse_pos(raw):
    """-> (partOfSpeech or None, grammaticalGender or None)."""
    key = (raw or "").strip().lower()
    if not key:
        return None, None
    if key in GENDER_MAP:
        return "noun", GENDER_MAP[key]
    return POS_MAP.get(key), None


def sub(parent, tag, text=None, **attrs):
    el = ET.SubElement(parent, tag, {k: v for k, v in attrs.items() if v})
    if text is not None:
        el.text = text
    return el


def lang_sec(concept, lang, term, entry, with_pos):
    """Append one <langSec>; the definition rides on the Khmer section."""
    sec = sub(concept, "langSec", **{"{http://www.w3.org/XML/1998/namespace}lang": lang})
    tsec = sub(sec, "termSec")
    sub(tsec, "term", term)
    if with_pos:
        pos, gender = parse_pos(entry.get("pos"))
        if pos:
            sub(tsec, "termNote", pos, type="partOfSpeech")
        if gender:
            sub(tsec, "termNote", gender, type="grammaticalGender")
    if lang == "km" and entry.get("definition", "").strip():
        sub(sec, "descrip", entry["definition"].strip(), type="definition")
    if entry.get("examples", "").strip():
        sub(tsec, "descrip", entry["examples"].strip(), type="context")
    return sec


def build(entries, title):
    ET.register_namespace("", "urn:iso:std:iso:30042:ed-2")
    root = ET.Element("tbx", {
        "type": "TBX-Basic",
        "style": "dca",
        "{http://www.w3.org/XML/1998/namespace}lang": "en",
        "xmlns": "urn:iso:std:iso:30042:ed-2",
    })
    header = sub(root, "tbxHeader")
    fileDesc = sub(header, "fileDesc")
    sub(sub(fileDesc, "titleStmt"), "title", title)
    sub(sub(fileDesc, "sourceDesc"), "p",
        "Compiled from published Cambodian government terminology documents. "
        "OCR output; not fully verified against the source PDFs.")
    body = sub(sub(root, "text"), "body")

    skipped = 0
    for entry in entries:
        khmer = (entry.get("khmer") or "").strip()
        if not khmer:
            skipped += 1  # 24 rows have no Khmer headword; nothing to anchor on
            continue
        concept = sub(body, "conceptEntry", id=entry.get("id"))
        if entry.get("category", "").strip():
            sub(concept, "descrip", entry["category"].strip(), type="subjectField")
        provenance = ", ".join(p for p in (
            entry.get("source", "").strip(),
            entry.get("author", "").strip(),
            entry.get("year", "").strip()) if p)
        if provenance:
            sub(concept, "admin", provenance, type="source")

        lang_sec(concept, "km", khmer, entry, with_pos=False)
        for field, lang in (("english", "en"), ("french", "fr")):
            value = (entry.get(field) or "").strip()
            if value:
                lang_sec(concept, lang, value, entry, with_pos=True)
    return root, skipped


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-i", "--input", type=Path, default=DEFAULT_IN)
    ap.add_argument("-o", "--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--title", default="Khmer Official Terminology")
    args = ap.parse_args(argv)

    entries = json.loads(args.input.read_text(encoding="utf-8"))
    root, skipped = build(entries, args.title)
    ET.indent(root, space="  ")
    args.output.write_bytes(
        b'<?xml version="1.0" encoding="UTF-8"?>\n'
        + ET.tostring(root, encoding="utf-8"))
    print(f"{len(entries) - skipped} concepts -> {args.output} "
          f"({skipped} skipped: no Khmer headword)", file=sys.stderr)


def _self_check():
    rows = [
        {"id": "a", "khmer": "ក", "english": "Alpha", "french": "Alpha",
         "pos": "f.", "category": "Test", "definition": "និយមន័យ",
         "examples": "", "source": "doc", "author": "Body", "year": "2020"},
        {"id": "b", "khmer": "", "english": "Orphan", "french": "", "pos": "",
         "category": "", "definition": "", "examples": "", "source": "",
         "author": "", "year": ""},
        {"id": "c", "khmer": "ខ", "english": "Gamma", "french": "", "pos": "ន.",
         "category": "", "definition": "", "examples": "", "source": "",
         "author": "", "year": ""},
    ]
    root, skipped = build(rows, "t")
    xml = ET.tostring(root, encoding="unicode")
    assert skipped == 1, "row with no Khmer must be skipped"
    assert xml.count("<conceptEntry") == 2
    # French gender marker becomes gender + noun, never a partOfSpeech value
    assert 'type="grammaticalGender">feminine' in xml
    assert ">f.<" not in xml
    # 2 from row a (en+fr, gender implies noun) + 1 from row c (ន. -> noun)
    assert xml.count('type="partOfSpeech">noun') == 3
    # definition attaches to the Khmer section only
    assert xml.count("និយមន័យ") == 1
    assert 'type="source">doc, Body, 2020' in xml
    # unknown pos is dropped, not emitted raw
    root2, _ = build([dict(rows[0], pos="Policy", french="")], "t")
    assert "Policy" not in ET.tostring(root2, encoding="unicode")
    print("self-check ok")


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        _self_check()
    else:
        main()
