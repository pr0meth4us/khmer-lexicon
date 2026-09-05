"""Estimate OCR accuracy by checking terms against the Royal Academy dictionary.

There is no ground truth for this lexicon: the source PDFs are scans, and every
defect the validator catches is one that produced something structurally
impossible (Latin in a Khmer field, a dangling coeng). An OCR error that turns a
real Khmer word into a DIFFERENT real Khmer word is invisible to all of it.

This narrows that blind spot using an external authority — the Royal Academy of
Cambodia dictionary 2022, 38,694 headwords, published as
seanghay/khmer-dictionary-44k on HuggingFace.

The test is not "is this word in the dictionary". Most of these glossaries exist
precisely to coin terms a general dictionary does not have, so absence proves
nothing. The test is narrower:

    a term that is NOT in RAC, but is exactly one grapheme cluster
    SUBSTITUTION away from a word that is

Substitution specifically, not insertion or deletion: adding a syllable to a
dictionary word is how Khmer compounds are built (ស្ថិរភាព -> ស្ថិរភាពថ្លៃ,
"price stability"), and counting those inflates the estimate roughly twofold.
Swapping one syllable for another is the OCR signature.

Three gates keep the substitution test honest. Each was added after a downstream
consumer scanned the lexicon against 56,669 real exam questions and found that
the highest-occurrence "suspects" were all false positives:

  1. ្ត and ្ដ are the same letter for this purpose. RAC prescribes ្ដ and the
     source documents vary. Folding them removes 46 pairs that were scoring the
     HIGHEST confusion weight in the list (ធនាគារកណ្តាល/ធនាគារកណ្ដាល, 248) while
     being an orthography question, not an OCR error.
  2. RAC is a headword dictionary and Khmer does not space its words, so
     compounds reach the test looking like single words and can never be in the
     list. For a word RAC does not hold, the nearest string is noise —
     ប៉ារីស → ដំរីស is not a confusion anyone could make. A term that splits into
     two or more RAC headwords is a compound and is skipped (1,211).
  3. The swap must be plausible: a documented human confusion, or two clusters
     sharing a base consonant (ខ → ខ័). វៀ → រ៉ុ is an artefact of the search,
     not a misread (347).

Suspects are then ranked by seanghay/khmer-character-confusions, so pairs that
real people demonstrably confuse sort to the top.

This produces a RANKED SUSPECT LIST, not an error rate. A substitution of a real
word may still be a legitimate variant, and RAC 2022 may simply prescribe a
different orthography than a 2010 bulletin. What it buys is a cheap gold-sample:
checking 50 entries from this list against the page images is worth far more
than checking 200 random ones.

    python3 scripts/check_against_rac.py
"""
import collections
import csv
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from khmerlex import clusters, is_khmer, normalize  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data"
LEXICON = ROOT / "dist" / "unified_lexicon.json"
REPORT = ROOT / "dist" / "ocr_suspects.md"
SIDECAR = ROOT / "dist" / "ocr_suspects.json"

SOURCES = {
    "rac-dictionary-2022": ("khmer-dictionary-44k", "RAC-Khmer-Dict-2022.csv"),
    "khmer-character-confusions": ("khmer-character-confusions", "data.csv"),
}


def _build_id():
    """Stamp sidecars with the build they describe. See scripts/build_manifest.py."""
    m = LEXICON.parent / "manifest.json"
    return json.loads(m.read_text("utf-8"))["build_id"] if m.exists() else None


def fetch(name):
    """Download once into data/ (gitignored: CC-BY-SA, not ours to redistribute)."""
    CACHE.mkdir(exist_ok=True)
    dataset, filename = SOURCES[name]
    path = CACHE / f"{name}.csv"
    if not path.exists():
        url = (f"https://huggingface.co/datasets/seanghay/{dataset}"
               f"/resolve/main/{filename}")
        print(f"fetching {name} …", file=sys.stderr)
        # curl, not urllib: the system Python has no CA bundle wired up.
        subprocess.run(["curl", "-sSfL", "--max-time", "120", "-o", str(path), url],
                       check=True)
    return list(csv.DictReader(path.open(encoding="utf-8")))


def rac_headwords():
    words = set()
    for row in fetch("rac-dictionary-2022"):
        for field in ("t_main", "t_subword"):
            word = (row.get(field) or "").strip()
            if word:
                words.add(normalize(word))
    return words


def deletion_index(words):
    index = collections.defaultdict(set)
    for word in words:
        pieces = clusters(word)
        index[tuple(pieces)].add(word)
        for i in range(len(pieces)):
            index[tuple(pieces[:i] + pieces[i + 1:])].add(word)
    return index


def fold(word):
    """្ត and ្ដ are one letter here: RAC prescribes ្ដ, the sources use both."""
    return word.replace("្ដ", "្ត")


def is_compound(term, rac):
    """Does `term` split into two or more RAC headwords? Then RAC can't hold it."""
    pieces = clusters(term)
    if len(pieces) < 4:
        return False
    reachable = [True] + [False] * len(pieces)
    for i in range(1, len(pieces) + 1):
        reachable[i] = any(reachable[j] and "".join(pieces[j:i]) in rac
                           for j in range(i - 1))
    return reachable[-1]


def is_plausible(mine, theirs, weight):
    """A misread swaps look-alikes. Anything else is the search finding noise."""
    return bool(weight) or (mine[:1] == theirs[:1])


def single_word_terms(rows):
    """RAC is a word dictionary; multiword and punctuated entries can't match."""
    out = []
    for row in rows:
        term = (row.get("khmer") or "").strip()
        if term and any(is_khmer(c) for c in term) \
                and not any(ch in term for ch in " /()"):
            out.append(row)
    return out


def substitutions(term, rac, index):
    """RAC words exactly one cluster-substitution away from `term`."""
    pieces = clusters(normalize(term))
    candidates = set(index.get(tuple(pieces), ()))
    for i in range(len(pieces)):
        candidates |= index.get(tuple(pieces[:i] + pieces[i + 1:]), set())
    for word in candidates:
        other = clusters(word)
        if len(other) != len(pieces):
            continue
        differing = [(a, b) for a, b in zip(pieces, other) if a != b]
        if len(differing) == 1:
            yield word, differing[0]


def main():
    rac = rac_headwords()
    index = deletion_index(rac)
    confusions = {(r["from_char"], r["to_char"]): int(r["count"])
                  for r in fetch("khmer-character-confusions")}

    folded = {fold(w) for w in rac}

    rows = json.loads(LEXICON.read_text("utf-8"))
    terms = single_word_terms(rows)
    known = [r for r in terms if fold(normalize(r["khmer"])) in folded]

    dropped = collections.Counter()
    suspects = []
    for row in terms:
        term = normalize(row["khmer"])
        if fold(term) in folded:
            continue
        if is_compound(term, rac):
            dropped["compound"] += 1
            continue
        # `substitutions` yields in set order, so take the best match rather than
        # an arbitrary one — otherwise the run is not reproducible.
        matches = []
        for word, (mine, theirs) in substitutions(row["khmer"], rac, index):
            only_mine = [c for c in mine if c not in theirs]
            only_theirs = [c for c in theirs if c not in mine]
            weight = 0
            if len(only_mine) == 1 and len(only_theirs) == 1:
                weight = (confusions.get((only_mine[0], only_theirs[0]), 0)
                          or confusions.get((only_theirs[0], only_mine[0]), 0))
            matches.append((is_plausible(mine, theirs, weight), weight, word, mine, theirs))
        if not matches:
            continue
        plausible, weight, word, mine, theirs = max(matches, key=lambda m: (m[0], m[1], m[2]))
        if not plausible:
            dropped["implausible swap"] += 1
            continue
        suspects.append({"weight": weight, "id": row["id"],
                         "khmer": row["khmer"], "rac": word,
                         "source": row.get("source", ""),
                         "english": row.get("english", ""),
                         "swap": f"{mine} → {theirs}"})
    suspects.sort(key=lambda s: -s["weight"])
    backed = [s for s in suspects if s["weight"]]

    by_source = collections.Counter(s["source"] for s in suspects)
    totals = collections.Counter(r.get("source", "") for r in terms)
    swaps = collections.Counter(s["swap"] for s in suspects)

    lines = [
        "# OCR suspects — terms one substitution from a dictionary word", "",
        f"- single-word Khmer terms checked: **{len(terms):,}**",
        f"- present in the RAC 2022 dictionary: **{len(known):,}** "
        f"({len(known)/len(terms)*100:.1f}%)",
        f"- absent, but one cluster-substitution from a RAC word: "
        f"**{len(suspects):,}** ({len(suspects)/len(terms)*100:.1f}%)",
        f"- of those, the swapped characters are a documented human confusion: "
        f"**{len(backed):,}** ({len(backed)/len(terms)*100:.1f}%)",
        f"- excluded as compounds RAC cannot hold: **{dropped['compound']:,}**",
        f"- excluded because the swap is not a plausible misread: "
        f"**{dropped['implausible swap']:,}**", "",
        "Absence from RAC is not evidence — these glossaries exist to coin terms a "
        "general dictionary lacks. Only the substitutions are listed, because "
        "adding a syllable to a dictionary word is ordinary Khmer compounding.",
        "",
        "**This is a ranked suspect list, not an error rate.** A substitution of a "
        "real word can still be a legitimate variant, and RAC 2022 may prescribe a "
        "different orthography than a 2010 bulletin. Verify against the page "
        "images before changing anything.", "",
        "## Most frequent swaps", "",
        "| swap | count |", "| --- | ---: |",
    ]
    lines += [f"| `{swap}` | {n} |" for swap, n in swaps.most_common(12)]
    lines += ["", "## By source", "", "| source | suspects | terms | rate |",
              "| --- | ---: | ---: | ---: |"]
    for source, total in totals.most_common():
        n = by_source.get(source, 0)
        lines.append(f"| {source} | {n} | {total} | {n/total*100:.1f}% |")
    lines += ["", "## Suspects, most-confused characters first", "",
              "| term | RAC has | swap | confused | English | source |",
              "| --- | --- | --- | ---: | --- | --- |"]
    for s in suspects:
        lines.append(f"| {s['khmer']} | {s['rac']} | `{s['swap']}` | "
                     f"{s['weight'] or '—'} | {s['english'][:34]} | {s['source']} |")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    SIDECAR.write_text(json.dumps(
        {"build_id": _build_id(), "count": len(suspects),
         "excluded": dict(dropped), "suspects": suspects},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"{len(terms):,} single-word terms")
    print(f"  {len(known):,} in RAC ({len(known)/len(terms)*100:.1f}%)")
    print(f"  {len(suspects):,} one substitution away ({len(suspects)/len(terms)*100:.1f}%)")
    print(f"  {len(backed):,} of those are known human confusions")
    for reason, n in dropped.most_common():
        print(f"  ({n:,} excluded: {reason})")
    print(f"\ntop swaps: " + ", ".join(f"{s} ×{n}" for s, n in swaps.most_common(5)))
    print(f"report -> {REPORT}, {SIDECAR}")


if __name__ == "__main__":
    main()
