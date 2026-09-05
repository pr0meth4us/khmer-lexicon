"""Canary entries: plausible fakes that prove copying.

The lexicon can be read through the API, so it can eventually be copied. What
cannot be argued with is provenance. A handful of entries that exist ONLY here —
well-formed Khmer, a real ministry, a real year, a definition that reads like the
others — are invisible in normal use and decisive if they appear in someone
else's dictionary, dataset or app.

Cartographers have done this for a century (trap streets); dictionaries have
done it for longer (mountweazels). For terminology it is close to ideal: nobody
looks up a word that does not exist, so a canary is never served to a real user
by accident, but a bulk copy takes them along with everything else.

The canaries are built from real Khmer morphemes so they survive inspection, and
each is recorded in dist/canaries.json (gitignored, private) with the date it was
planted and the id it was given. Keep that file. It is the evidence.

They take ordinary `official_lex_NNNN` ids and sit inside the block of entries
from the source they claim — not a `canary_NN` namespace at the end of the file,
which anyone stripping the lexicon would find with one grep.

    python3 scripts/add_canaries.py --plant     # insert into dist/unified_lexicon.json
    python3 scripts/add_canaries.py --check     # confirm they are all still present
    python3 scripts/add_canaries.py --audit F   # is our data inside file F?
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from khmerlex import is_khmer, normalize  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LEXICON = ROOT / "dist" / "unified_lexicon.json"
LEDGER = ROOT / "dist" / "canaries.json"

# Constructed from real morphemes so each reads as a plausible coinage, but none
# is an actual term: no glossary, dictionary or corpus contains these strings.
CANARIES = [
    {"khmer": "សន្ទានុពលដ្ឋាន", "english": "reference substrate",
     "category": "Digital Technology & Telecom",
     "definition": "មូលដ្ឋានទិន្នន័យយោងសម្រាប់ការផ្ទៀងផ្ទាត់បច្ចេកសព្ទ។",
     "source": "mptc-digital-lexicon",
     "author": "Ministry of Post and Telecommunications (MPTC)", "year": "2025"},
    {"khmer": "អនុវិធានភាវូបនីយកម្ម", "english": "sub-procedural formalization",
     "category": "Law & Civil Procedure",
     "definition": "ដំណើរការធ្វើឲ្យនីតិវិធីរងក្លាយជាទម្រង់ផ្លូវការ។",
     "source": "council-of-ministers-legal-terms",
     "author": "Council of Ministers", "year": "2007"},
    {"khmer": "ប្រាក្រមវិស័យភាព", "english": "sectoral antecedence",
     "category": "Economics",
     "definition": "លក្ខណៈនៃវិស័យដែលមានអាទិភាពមុនគេក្នុងផែនការអភិវឌ្ឍន៍។",
     "source": "nckl-economics",
     "author": "National Council of Khmer Language (NCKL)", "year": "2019"},
    {"khmer": "ឧបលក្ខិតកម្មវត្ថុ", "english": "annotated subject-matter",
     "category": "Political Science & Diplomacy",
     "definition": "កម្មវត្ថុដែលមានការកត់សម្គាល់បន្ថែមក្នុងឯកសារផ្លូវការ។",
     "source": "nckl-political-science-and-diplomacy",
     "author": "National Council of Khmer Language (NCKL)", "year": "2014"},
    {"khmer": "ទ្វារបញ្ជូនអន្តរដ្ឋាន", "english": "inter-substrate relay gate",
     "category": "Science, Tech & Mathematics",
     "definition": "ច្រកបញ្ជូនទិន្នន័យរវាងមូលដ្ឋានពីរផ្សេងគ្នា។",
     "source": "nckl-technology-and-science",
     "author": "National Council of Khmer Language (NCKL)", "year": "2014"},
]

FIELDS = ("french", "pos", "examples", "version")


def _rows():
    return json.loads(LEXICON.read_text("utf-8"))


def plant():
    rows = _rows()
    present = {(r.get("khmer") or "").strip() for r in rows}
    used = {r["id"] for r in rows}
    next_id = max((int(r["id"].rsplit("_", 1)[1]) for r in rows
                   if r["id"].startswith("official_lex_")), default=0)
    planted = []
    for canary in CANARIES:
        if canary["khmer"] in present:
            continue
        next_id += 1
        while f"official_lex_{next_id:04d}" in used:
            next_id += 1
        entry = {"id": f"official_lex_{next_id:04d}", **canary}
        for field in FIELDS:
            entry.setdefault(field, "1.0" if field == "version" else "")
        # sit with the source it claims: appended at the end, a canary is the
        # one entry whose neighbours come from a different document.
        after = max((i for i, r in enumerate(rows)
                     if r.get("source") == entry["source"]), default=len(rows) - 1)
        rows.insert(after + 1, entry)
        planted.append({"id": entry["id"], "khmer": entry["khmer"]})
    if not planted:
        print("all canaries already present")
        return 0
    LEXICON.write_text(json.dumps(rows, ensure_ascii=False, indent=2), "utf-8")
    ledger = json.loads(LEDGER.read_text("utf-8")) if LEDGER.exists() else []
    ledger.append({"planted": date.today().isoformat(),
                   "terms": [c["khmer"] for c in planted],
                   "ids": [c["id"] for c in planted]})
    LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), "utf-8")
    print(f"planted {len(planted)} canaries -> {LEXICON.name}; ledger -> {LEDGER.name}")
    for c in planted:
        print(f"  {c['id']}  {c['khmer']}")
    return 0


def check():
    present = {(r.get("khmer") or "").strip() for r in _rows()}
    missing = [c["khmer"] for c in CANARIES if c["khmer"] not in present]
    for canary in CANARIES:
        assert all(is_khmer(ch) for ch in canary["khmer"]), canary["khmer"]
        assert normalize(canary["khmer"]) == canary["khmer"], canary["khmer"]
    print(f"{len(CANARIES) - len(missing)}/{len(CANARIES)} canaries present"
          + (f"; MISSING {missing}" if missing else ""))
    return 1 if missing else 0


def audit(path):
    """Does someone else's file contain our canaries?"""
    text = Path(path).read_text("utf-8", errors="ignore")
    hits = [c["khmer"] for c in CANARIES if c["khmer"] in text]
    if hits:
        print(f"MATCH: {len(hits)} canary term(s) found in {path}")
        for term in hits:
            print(f"   {term}")
        print("\nThese terms exist in no dictionary, glossary or corpus. Their "
              "presence is evidence this file derives from ours.")
        return 0
    print(f"no canaries found in {path}")
    return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--plant", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--audit", metavar="FILE")
    args = parser.parse_args()
    if args.plant:
        sys.exit(plant())
    if args.audit:
        sys.exit(audit(args.audit))
    sys.exit(check())
