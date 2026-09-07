"""List every entry whose Khmer contains ្ត or ្ដ, with what RAC prescribes.

    python scripts/coeng_worklist.py

The two subscripts are drawn identically by most Khmer fonts, so an entry that
has the wrong one is invisible to a reader checking against the source page and
invisible to every structural check here. 677 entries carry one of them.

There is no single right answer to apply across the board: the Royal Academy
dictionary uses ្ត in 2,545 headwords and ្ដ in 919, and commits to exactly one
spelling for 99.9% of the words it holds. So the question is per word, and this
resolves it per word where RAC can settle it.

For each entry, the longest run of Khmer around the subscript that RAC holds in
either spelling is located; RAC's spelling of that run is the verdict. Entries
RAC cannot speak to are listed as `unknown` for a human with Chuon Nath.

Writes dist/coeng_worklist.csv and a summary to stdout.
"""
import collections
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from khmerlex import normalize  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LEXICON = ROOT / "dist" / "unified_lexicon.json"
RAC_CSV = ROOT / "data" / "rac-dictionary-2022.csv"
OUT = ROOT / "dist" / "coeng_worklist.csv"
PAIR = ("្ត", "្ដ")


def swap(word):
    """Exchange every ្ត for ្ដ and vice versa."""
    return word.replace(PAIR[0], "\x00").replace(PAIR[1], PAIR[0]).replace("\x00", PAIR[1])


def rac_headwords(path=RAC_CSV):
    words = set()
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            for field in ("t_main", "t_subword"):
                word = (row.get(field) or "").strip()
                if word:
                    words.add(normalize(word))
    return words


def resolve(term, rac):
    """-> (verdict, [(piece, RAC's spelling of it), ...], corrected term).

    A term can contain more than one word carrying the subscript
    (បណ្តឹងអង្គសេចក្តី is two), so every one is resolved, not just the first.
    Matches are found longest-first and non-overlapping: Khmer writes compounds
    unspaced, so a short match is usually an accidental syllable rather than the
    word in question.
    """
    found, taken = [], [False] * len(term)
    for size in range(len(term), 0, -1):
        for start in range(len(term) - size + 1):
            end = start + size
            if any(taken[start:end]):
                continue
            piece = term[start:end]
            if PAIR[0] not in piece and PAIR[1] not in piece:
                continue
            for candidate in (piece, swap(piece)):
                if candidate in rac:
                    found.append((start, piece, candidate))
                    taken[start:end] = [True] * size
                    break
    if not found:
        return "unknown", [], ""
    found.sort()
    corrected, cursor = [], 0
    for start, piece, attested in found:
        corrected.append(term[cursor:start])
        corrected.append(attested)
        cursor = start + len(piece)
    corrected.append(term[cursor:])
    corrected = "".join(corrected)
    pairs = [(piece, attested) for _, piece, attested in found]
    return ("ok" if corrected == term else "differs"), pairs, corrected


def main():
    lex = json.loads(LEXICON.read_text(encoding="utf-8"))
    rac = rac_headwords()
    rows, counts = [], collections.Counter()

    # terms the corpus itself spells both ways: one of the two is wrong
    seen = collections.defaultdict(set)
    for entry in lex:
        k = normalize(entry["khmer"])
        if any(p in k for p in PAIR):
            seen[min(k, swap(k))].add(k)
    inconsistent = {k for group in seen.values() if len(group) > 1 for k in group}

    for entry in lex:
        term = normalize(entry["khmer"])
        if not any(p in term for p in PAIR):
            continue
        verdict, pairs, corrected = resolve(term, rac)
        counts[verdict] += 1
        rows.append({
            "id": entry["id"], "source": entry["source"], "khmer": entry["khmer"],
            "english": entry["english"], "verdict": verdict,
            "rac_word": " ".join(p for p, _ in pairs),
            "rac_spelling": " ".join(a for _, a in pairs),
            "suggested": corrected if verdict == "differs" else "",
            "corpus_inconsistent": "yes" if term in inconsistent else "",
            "decision": "", "notes": "",
        })
    rows.sort(key=lambda r: ({"differs": 0, "unknown": 1, "ok": 2}[r["verdict"]],
                             r["source"], r["id"]))
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"{len(rows)} entries contain ្ត or ្ដ -> {OUT}")
    print(f"  differs from RAC : {counts['differs']:4}  (RAC spells the word the other way)")
    print(f"  matches RAC      : {counts['ok']:4}")
    print(f"  RAC has no ruling: {counts['unknown']:4}  (needs Chuon Nath)")
    print(f"  spelled both ways inside the corpus: "
          f"{sum(1 for r in rows if r['corpus_inconsistent'])}")


def _self_check():
    assert swap("បណ្តោះ") == "បណ្ដោះ" and swap("បណ្ដោះ") == "បណ្តោះ"
    assert swap(swap("កណ្ដក់ ស្តី")) == "កណ្ដក់ ស្តី", "swap must be an involution"
    rac = {"កណ្ដក់", "កត្តា"}
    # RAC spells it ្ដ; an entry using ្ត differs and gets a suggestion
    assert resolve("កណ្តក់", rac) == ("differs", [("កណ្តក់", "កណ្ដក់")], "កណ្ដក់")
    assert resolve("កណ្ដក់", rac)[0] == "ok"
    # RAC spells this one ្ត — a blanket rule would have broken it
    assert resolve("កត្តា", rac)[0] == "ok"
    assert resolve("កត្ដា", rac)[2] == "កត្តា"
    # a compound: the RAC word is found inside it, the rest is left alone
    assert resolve("កណ្តក់ធំ", rac)[2] == "កណ្ដក់ធំ"
    # TWO affected words in one term: both must be corrected, not just the first
    v, pairs, out = resolve("កណ្តក់កត្ដា", rac)
    assert (v, out) == ("differs", "កណ្ដក់កត្តា"), (v, out)
    assert len(pairs) == 2, pairs
    assert resolve("ឡនោះ្តៗ", rac)[0] == "unknown"
    print("self-check ok")


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        _self_check()
    else:
        main()
