"""Near-duplicate Khmer terms: same word, two spellings, distance 1 apart.

Exact-match dedup keeps every OCR variant, because two scans of the same
glossary entry differ by one character and hash differently. This finds the
pairs that exact matching misses, and -- crucially -- says WHY each pair
differs, because the right action is different for each reason.

Method
------
1. Normalise (khmerlex.normalize) so pure mark-order variants are already gone.
2. Index every term by each of its single-cluster deletions. Two terms at edit
   distance <= 1 must share a deletion neighbour, so candidates come out of a
   dict instead of an all-pairs sweep: 5,777 forms would be 16.7M comparisons;
   the index produces ~8.6k candidates in about 40 ms.
3. Confirm with Levenshtein distance over GRAPHEME CLUSTERS, not code points.
   A term is a sequence of syllables; one dropped mark is not "one character"
   in any sense a reader would recognise.
4. Require the pair to share an English gloss. Distance alone is useless here:
   7,140 pairs are 1 apart, and most are simply short words (ក and ខ). Agreeing
   on meaning is what separates a variant from a different word. 164 survive.
5. Classify the difference, and where it is a single character substitution,
   look it up in seanghay/khmer-character-confusions -- 1,261 confusion pairs
   aggregated from 3.2M real khmerdict.com searches (CC-BY-SA-4.0). This turns
   "these two look similar" into "real people confuse these two N times".

Nothing is merged. The report is for a human to rule on.
"""
import collections
import csv
import itertools
import json
import subprocess
import sys
from pathlib import Path

from khmerlex import clusters, edit_distance

# scripts/ lives one level below the repo root; dist/ and data/ are up there.
HERE = Path(__file__).resolve().parent.parent
CACHE = HERE / "data"
LEXICON = HERE / "dist" / "unified_lexicon.json"
REPORT = HERE / "dist" / "near_duplicates.md"
SIDECAR = HERE / "dist" / "near_duplicates.json"

# seanghay/khmer-* on HuggingFace, CC-BY-SA-4.0, aggregates only, no personal data.
DATASETS = {
    "khmer-character-confusions": "from_char,to_char",
    "khmer-search-frequency": "word",
}
PUNCT = set(" /-().,​")


def _build_id():
    """Stamp sidecars with the build they describe. See scripts/build_manifest.py."""
    m = LEXICON.parent / "manifest.json"
    return json.loads(m.read_text("utf-8"))["build_id"] if m.exists() else None


def _fetch(name):
    """Download once into data/ (gitignored -- CC-BY-SA, not ours to vendor)."""
    CACHE.mkdir(exist_ok=True)
    path = CACHE / f"{name}.csv"
    if not path.exists():
        url = f"https://huggingface.co/datasets/seanghay/{name}/resolve/main/data.csv"
        print(f"fetching {name} ...", file=sys.stderr)
        # curl, not urllib: the system Python here has no CA bundle wired up.
        subprocess.run(["curl", "-sSfL", "--max-time", "60", "-o", str(path), url],
                       check=True)
    return list(csv.DictReader(path.open(encoding="utf-8")))


def load_signals():
    try:
        confusions = {(r["from_char"], r["to_char"]): int(r["count"])
                      for r in _fetch("khmer-character-confusions")}
        frequency = {r["word"]: int(r["sessions"])
                     for r in _fetch("khmer-search-frequency")}
        return confusions, frequency
    except Exception as exc:                    # offline: report without weights
        print(f"warning: empirical signals unavailable ({exc})", file=sys.stderr)
        return {}, {}


def candidates(forms):
    """Pairs sharing a single-cluster deletion. Superset of distance <= 1."""
    index = collections.defaultdict(set)
    for term in forms:
        pieces = clusters(term)
        index[tuple(pieces)].add(term)
        for i in range(len(pieces)):
            index[tuple(pieces[:i] + pieces[i + 1:])].add(term)
    return {pair for group in index.values() if len(group) > 1
            for pair in itertools.combinations(sorted(group), 2)}


def char_span(a, b):
    """The differing region, trimmed to characters, not clusters."""
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    j = 0
    while j < min(len(a), len(b)) - i and a[len(a) - 1 - j] == b[len(b) - 1 - j]:
        j += 1
    return a[i:len(a) - j], b[i:len(b) - j]


def classify(a, b, confusions):
    left, right = char_span(a, b)
    blob = left + right
    weight = confusions.get((left, right)) or confusions.get((right, left)) or 0
    if not blob.strip():
        return "whitespace", weight
    if all(ch in PUNCT for ch in blob):
        return "punctuation", weight
    if len(left) == 1 and len(right) == 1:
        return ("confusion" if weight else "substitution"), weight
    if not left or not right:
        return "one character added or dropped", weight
    return "multi-character", weight


# Merge rules, by reason. Deliberately NOT applied -- see the report footer.
RULES = {
    "whitespace": "safe to merge: collapse to the unspaced form, union the sources",
    "punctuation": "safe to merge: strip the separator, union the sources",
    "confusion": "merge toward the form real users search for; empirical weight given",
    "one character added or dropped": "prefer the longer form when the shorter is a "
                                      "truncation; otherwise review",
    "substitution": "review: one character apart but never observed as a confusion",
    "multi-character": "review individually: likely damaged, possibly different words",
}
ORDER = ["whitespace", "punctuation", "confusion", "one character added or dropped",
         "substitution", "multi-character"]


def main():
    rows = json.loads(LEXICON.read_text("utf-8"))
    by_form = collections.defaultdict(list)
    for row in rows:
        term = (row.get("khmer") or "").strip()
        if term:
            by_form[term].append(row)
    confusions, frequency = load_signals()

    def glosses(term):
        return {(r.get("english") or "").strip().lower() for r in by_form[term]} - {""}

    pairs = candidates(by_form)
    at_distance_1 = [(a, b) for a, b in pairs if edit_distance(a, b, cutoff=1) == 1]
    near = [(a, b) for a, b in at_distance_1 if glosses(a) & glosses(b)]

    exact = [(k, v) for k, v in by_form.items() if len(v) > 1]
    groups = collections.defaultdict(list)
    for a, b in near:
        reason, weight = classify(a, b, confusions)
        groups[reason].append((weight, a, b))

    out = [
        "# Near-duplicate report",
        "",
        f"- entries: {len(rows):,}",
        f"- distinct Khmer forms: {len(by_form):,}",
        f"- exact duplicate forms: {len(exact)} "
        f"({sum(len(v) - 1 for _, v in exact)} redundant rows)",
        f"- pairs at cluster distance 1: {len(at_distance_1):,}",
        f"- of those, sharing an English gloss: **{len(near)}** "
        f"-- the actual near-duplicates",
        "",
        "Distance alone is not evidence: most distance-1 pairs are short words that "
        "are simply different. Agreement on the English gloss is what makes a pair a "
        "spelling variant rather than two words.",
        "",
        "Confusion weights come from seanghay/khmer-character-confusions "
        "(CC-BY-SA-4.0), 1,261 pairs aggregated from 3.2M khmerdict.com searches.",
        "",
    ]
    for reason in ORDER:
        items = sorted(groups.get(reason, []), reverse=True)
        if not items:
            continue
        out += [f"## {reason} ({len(items)})", "", f"*{RULES[reason]}*", ""]
        for weight, a, b in items:
            left, right = char_span(a, b)
            note = f" — `{left}`→`{right}`" if (left or right) else ""
            if weight:
                note += f", confused **{weight}×** by real users"
            fa, fb = frequency.get(a, 0), frequency.get(b, 0)
            if fa or fb:
                note += f", searched {fa}/{fb}"
            out.append(f"- {a} ~ {b}{note}")
        out.append("")
    out += [
        "## Not applied",
        "",
        "No merge has been performed. `whitespace` and `punctuation` are mechanical "
        "and could be automated today; `confusion` needs a ruling on which spelling "
        "the official lexicon should carry, which is an editorial decision about "
        "government terminology, not a data-cleaning one.",
    ]
    REPORT.write_text("\n".join(out), encoding="utf-8")
    # a form can be carried by more than one entry, so a pair of forms is a pair
    # of id *groups*, not a pair of ids.
    sidecar = []
    for reason in ORDER:
        for weight, a, b in sorted(groups.get(reason, []), reverse=True):
            sidecar.append({
                "reason": reason, "weight": weight,
                "a": {"khmer": a, "ids": [r["id"] for r in by_form[a]],
                      "year": sorted({r.get("year", "") for r in by_form[a]})[-1]},
                "b": {"khmer": b, "ids": [r["id"] for r in by_form[b]],
                      "year": sorted({r.get("year", "") for r in by_form[b]})[-1]},
            })
    SIDECAR.write_text(json.dumps(
        {"build_id": _build_id(), "count": len(sidecar), "pairs": sidecar},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(near)} near-duplicates -> {REPORT}, {SIDECAR}")
    for reason in ORDER:
        if groups.get(reason):
            print(f"  {len(groups[reason]):>4}  {reason}")


if __name__ == "__main__":
    main()
