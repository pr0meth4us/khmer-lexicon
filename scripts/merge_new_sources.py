"""Append the recovered NCKL sources (build/new_sources) to dist/unified_lexicon.json.

    python3 scripts/merge_new_sources.py              # merge, then gate + manifest
    python3 scripts/merge_new_sources.py --dry-run    # counts only, writes nothing
    python3 scripts/merge_new_sources.py --self-check

Append-only. clean_and_arrange_official_lexicons.py cannot be rerun: its inputs
in build/ are gone, and a rebuild would also drop the canaries that live in
dist/. So v1.0 entries keep their ids and order, and new entries take ids after
the highest one in use. Rerunning first removes the entries of these sources,
so the result is the same each time.

Cleaning and the duplicate rule are the ones the v1.0 build used (English and
Khmer both equal, case-insensitive), imported rather than copied. Most of these
handbooks republish terms from Bulletins 3-10; those exact repeats are skipped.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from clean_and_arrange_official_lexicons import clean_english, clean_french, clean_khmer  # noqa: E402
from khmerlex import cluster_len, contaminants  # noqa: E402
from extract_new_sources import NCKL, OUT_DIR, SOURCES  # noqa: E402

DIST = ROOT / "dist"
LEXICON = DIST / "unified_lexicon.json"
OFFICIAL = DIST / "unified_official_lexicon.json"
# Bulletin No. 1 carries no term entries (docs: 7 new sources, not 8)
MERGED = [s for s in SOURCES if s != "nckl-bulletin-vol1-2008"]
# Bulletin No. 2 pp8-19 are word-formation tables (root, infix, derived word),
# a grammar exercise rather than terminology; extraction put the derived word
# in "definition". Pages 20+ are glossaries and country tables.
EXCLUDED_PAGES = {"nckl-bulletin-vol2-2009": set(range(8, 20))}
HEADER_JUNK = ("រាជបណ្ឌិត្យសភាកម្ពុជា", "សូមថ្លែងអំណរគុណ", "CONCH")
FLOOR = 5000  # v1.0 has 5,934; fewer means the wrong file was read
# Past 30 clusters every staged headword checked was definition text run into
# the khmer field (179-cluster maximum). v1.0 is not filtered: this only keeps
# the merge from adding more. ponytail: length cap, not a parser for the layout.
MAX_CLUSTERS = 30
COENG_RO_FIRST = re.compile(r"([ក-អ])្រ្([ក-អ])")  # ស្រ្ត typed for ស្ត្រ; renders the same
KHMER = re.compile(r"[ក-៿]")


def dedup_key(entry):
    return f"{entry['english'].lower()}|{entry['khmer'].lower()}"


def rejected(kh):
    """Why a cleaned headword is an extraction failure, or "" if it is usable."""
    if not kh:
        return ""
    if not KHMER.search(kh):
        return "no Khmer"
    if re.search(r"[0-9]", kh) or contaminants(kh):
        return "OCR junk characters"
    if cluster_len(kh) > MAX_CLUSTERS:
        return "definition text in headword"
    # ក glossed "precipitate" (Bulletin No. 2 p20) is a truncation; a lone
    # consonant also matches inside almost any word (see validate_lexicon.py)
    if re.fullmatch(r"[ក-អ]", kh):
        return "single bare consonant"
    return ""


def to_entry(raw, source):
    """Staged entry -> v1.0 schema, or None if the v1.0 build would have skipped it."""
    kh, en = clean_khmer(raw.get("khmer", "")), clean_english(raw.get("english", ""))
    kh = COENG_RO_FIRST.sub(r"\1្\2្រ", kh)
    if not kh and not en or any(j in kh for j in HEADER_JUNK) or rejected(kh):
        return None
    return {"english": en, "khmer": kh, "french": clean_french(raw.get("french", "")),
            "pos": (raw.get("pos") or "").strip(), "category": SOURCES[source][1],
            "definition": (raw.get("definition") or "").strip(),
            "examples": (raw.get("examples") or "").strip(), "source": source,
            "author": NCKL, "version": "1.0", "year": SOURCES[source][2]}


def merge(existing, staged):
    """existing: lexicon list; staged: {source: {page: [raw entries]}} -> (lexicon, stats)."""
    kept = [e for e in existing if e["source"] not in staged]
    seen = {dedup_key(e) for e in kept}
    next_id = 1 + max(int(re.sub(r"\D", "", e["id"])) for e in kept)
    added, stats = [], {}
    for source in staged:
        s = stats[source] = {"added": 0, "duplicate": 0, "skipped": 0, "excluded_page": 0}
        for page in sorted(staged[source], key=int):
            for raw in staged[source][page]:
                if int(page) in EXCLUDED_PAGES.get(source, ()):
                    s["excluded_page"] += 1
                    continue
                entry = to_entry(raw, source)
                if entry is None:
                    s["skipped"] += 1
                    continue
                if dedup_key(entry) in seen:
                    s["duplicate"] += 1
                    continue
                seen.add(dedup_key(entry))
                added.append({"id": f"official_lex_{next_id:04d}", **entry})
                next_id += 1
                s["added"] += 1
    return kept + added, stats


def load_staged():
    staged = {}
    for source in MERGED:
        state = json.loads((OUT_DIR / f"{source}.json").read_text(encoding="utf-8"))
        if not state.get("complete"):
            raise SystemExit(f"{source}: staging incomplete, failed pages {state.get('failed_pages')}")
        staged[source] = state["pages"]
    return staged


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()
    if args.self_check:
        return _self_check()

    existing = json.loads(LEXICON.read_text(encoding="utf-8"))
    if len(existing) < FLOOR:
        raise SystemExit(f"{LEXICON} has {len(existing)} entries; expected the full lexicon")
    lexicon, stats = merge(existing, load_staged())
    for source, s in stats.items():
        print(f"{source:34} {s}")
    print(f"{len(existing)} -> {len(lexicon)} entries")
    if args.dry_run:
        return 0
    text = json.dumps(lexicon, ensure_ascii=False, indent=2)
    LEXICON.write_text(text, encoding="utf-8")
    OFFICIAL.write_text(text, encoding="utf-8")
    sys.stdout.flush()
    rc = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_lexicon.py")]).returncode
    return rc or subprocess.run([sys.executable, str(ROOT / "scripts" / "build_manifest.py")]).returncode


def _self_check():
    src, other = "nckl-bulletin-vol2-2009", "rac-new-words"
    base = {"french": "", "pos": "", "category": "c", "definition": "", "examples": "",
            "author": "a", "version": "1.0", "year": "2018"}
    existing = [
        {**base, "id": "official_lex_0001", "english": "Chad", "khmer": "ឆាដ", "source": other},
        {**base, "id": "official_lex_0007", "english": "canary", "khmer": "ក", "source": other},
        {**base, "id": "official_lex_0008", "english": "stale", "khmer": "ខ", "source": src},
    ]
    staged = {src: {
        "9": [{"khmer": "ក្រិត", "definition": "កម្រិត"}],                        # word-formation page
        "32": [{"khmer": "ឆាដ", "english": "chad"},                                # repeat of v1.0, any case
               {"khmer": "៣៣- កាណាដា", "english": "H. Canada", "french": "Fr. Canada"},
               {"khmer": "កាណាដា", "english": "Canada"},                           # repeat within the source
               {"khmer": "", "english": ""}],
    }}
    # extraction failures are not merged; a reversed coeng ro is repaired
    assert rejected("orale") and rejected("ក្រួសវÅ/ក្រួស") and rejected("ក" * 31) and rejected("ក")
    assert not rejected("កក") and not rejected("ឫស")
    assert not rejected("ក" * 30) and not rejected("ជប៉ុន") and not rejected("")
    assert to_entry({"khmer": "orale", "english": "oral"}, src) is None
    assert to_entry({"khmer": "រោគស្រ្តីវិទ្យា", "english": "gynecology"}, src)["khmer"] == "រោគស្ត្រីវិទ្យា"
    out, stats = merge(existing, staged)
    assert stats[src] == {"added": 1, "duplicate": 2, "skipped": 1, "excluded_page": 1}, stats
    assert [e["id"] for e in out] == ["official_lex_0001", "official_lex_0007", "official_lex_0008"], out
    new = out[-1]
    assert (new["khmer"], new["english"], new["french"]) == ("កាណាដា", "Canada", "Canada"), new
    assert set(new) == set(existing[0]) and new["year"] == "2009" and new["source"] == src
    # rerunning over its own output gives the same lexicon
    again, _ = merge(out, staged)
    assert again == out, again
    print("self-check ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
