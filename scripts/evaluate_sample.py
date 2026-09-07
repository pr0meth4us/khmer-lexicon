"""Draw a stratified sample for manual verification, and score it once checked.

    python scripts/evaluate_sample.py draw  -n 400 -o dist/eval_sample.csv
    python scripts/evaluate_sample.py score dist/eval_sample.csv

`draw` takes a reproducible stratified random sample across the 15 sources and
writes a CSV with blank verdict columns. You fill `khmer_ok` and `english_ok`
with y/n by comparing each row against its source PDF page. `score` reads the
filled CSV back and reports per-source and overall error rates with Wilson
95% confidence intervals, weighting strata by their true size so the overall
figure is not skewed by the minimum-per-source floor.
"""
import argparse
import csv
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DEFAULT_LEXICON = BASE / "dist" / "unified_lexicon.json"
DEFAULT_SAMPLE = BASE / "dist" / "eval_sample.csv"
FIELDS = ["id", "source", "pdf", "page", "khmer", "english", "french",
          "definition", "year"]
VERDICTS = ["khmer_ok", "english_ok", "notes"]
MIN_PER_SOURCE = 10  # so a 121-entry source still gets looked at
SEED = 20260907


def draw(entries, n, seed=SEED):
    """Proportional allocation with a floor, capped at stratum size."""
    by_source = defaultdict(list)
    for e in entries:
        by_source[e["source"]].append(e)

    total = len(entries)
    alloc = {}
    for source, rows in by_source.items():
        want = max(MIN_PER_SOURCE, round(n * len(rows) / total))
        alloc[source] = min(want, len(rows))

    rng = random.Random(seed)
    sample = []
    for source in sorted(by_source):
        sample.extend(rng.sample(by_source[source], alloc[source]))
    return sample, {s: len(r) for s, r in by_source.items()}


def locate(entries, sources_path, pdf_dir):
    """Add `pdf` and `page` to each entry by finding its English gloss in the
    PDF's text layer.

    The Khmer in these text layers is mis-mapped and unusable (archaic
    codepoints, visual order), but the Latin comes out clean, so the gloss is a
    reliable locator even though the Khmer beside it is not. Entries with no
    gloss, or whose gloss is not found, get a blank page and are looked up by
    hand.
    """
    try:
        import fitz
    except ImportError:
        print("PyMuPDF not installed; skipping page location", file=sys.stderr)
        return
    meta = json.loads(Path(sources_path).read_text(encoding="utf-8"))["sources"]
    cache = {}
    for entry in entries:
        sid = entry["source"]
        entry["pdf"] = meta.get(sid, {}).get("file", "")
        entry["page"] = ""
        if sid not in cache:
            path = Path(pdf_dir) / entry["pdf"]
            if not path.exists():
                cache[sid] = []
            else:
                doc = fitz.open(path)
                cache[sid] = [doc[i].get_text().lower() for i in range(doc.page_count)]
                doc.close()
        gloss = (entry.get("english") or "").strip().lower()
        if len(gloss) <= 3:
            continue
        for number, text in enumerate(cache[sid], start=1):
            if gloss in text:
                entry["page"] = number
                break


def wilson(errors, n, z=1.96):
    """Wilson score interval — correct at 0 and n errors, where the normal
    approximation collapses to a zero-width interval."""
    if n == 0:
        return 0.0, 0.0, 0.0
    p = errors / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, centre - half), min(1.0, centre + half)


def cmd_draw(args):
    entries = json.loads(args.lexicon.read_text(encoding="utf-8"))
    sample, sizes = draw(entries, args.n, args.seed)
    if not args.no_locate:
        locate(sample, args.sources, args.pdf_dir)
    with args.output.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS + VERDICTS,
                           extrasaction="ignore")
        w.writeheader()
        for row in sample:
            w.writerow({**{k: row.get(k, "") for k in FIELDS},
                        **dict.fromkeys(VERDICTS, "")})
    # stratum sizes are needed to weight the score; keep them next to the CSV
    args.output.with_suffix(".strata.json").write_text(
        json.dumps({"seed": args.seed, "population": sizes}, indent=1))
    located = sum(1 for r in sample if r.get("page"))
    print(f"{len(sample)} rows across {len(sizes)} sources -> {args.output}\n"
          f"{located} located to a page; the rest need finding by hand\n"
          f"Fill khmer_ok / english_ok with y or n, leave blank to skip, "
          f"then: python {Path(__file__).name} score {args.output}",
          file=sys.stderr)


def tally(rows, column):
    """-> {source: (errors, checked)} counting only y/n rows."""
    out = defaultdict(lambda: [0, 0])
    for r in rows:
        v = (r.get(column) or "").strip().lower()
        if v not in ("y", "n"):
            continue
        out[r["source"]][1] += 1
        if v == "n":
            out[r["source"]][0] += 1
    return {s: tuple(v) for s, v in out.items()}


def weighted_rate(counts, population):
    """Stratified estimate: sum over strata of (N_h/N) * p_h.

    The floor means small sources are over-sampled; an unweighted mean would
    over-count them. Effective n uses the same weights so the interval is not
    narrower than the sample supports.
    """
    strata = {s: c for s, c in counts.items() if c[1] > 0}
    if not strata:
        return None
    total = sum(population[s] for s in strata)
    p = sum(population[s] / total * (e / n) for s, (e, n) in strata.items())
    n_eff = sum(n for _, n in strata.values())
    return p, n_eff, total


def cmd_score(args):
    rows = list(csv.DictReader(args.sample.open(encoding="utf-8")))
    strata_file = args.sample.with_suffix(".strata.json")
    population = json.loads(strata_file.read_text())["population"]

    for column in ("khmer_ok", "english_ok"):
        counts = tally(rows, column)
        checked = sum(n for _, n in counts.values())
        print(f"\n== {column} ==  {checked} of {len(rows)} rows checked")
        if not checked:
            print("  (nothing filled in yet)")
            continue
        for source in sorted(counts):
            errors, n = counts[source]
            p, lo, hi = wilson(errors, n)
            print(f"  {source:42} {errors:3}/{n:<3} {p:6.1%} "
                  f"[{lo:.1%}–{hi:.1%}]")
        p, n_eff, covered = weighted_rate(counts, population)
        _, lo, hi = wilson(round(p * n_eff), n_eff)
        print(f"  {'OVERALL (size-weighted)':42} {p:16.1%} [{lo:.1%}–{hi:.1%}]"
              f"  n={n_eff}, covering {covered} entries")


def _self_check():
    # Wilson stays finite at the boundaries, where the normal approximation
    # would report a zero-width interval and claim certainty.
    p, lo, hi = wilson(0, 50)
    assert p == 0.0 and lo == 0.0 and 0.0 < hi < 0.15, (p, lo, hi)
    p, lo, hi = wilson(50, 50)
    assert p == 1.0 and hi == 1.0 and 0.85 < lo < 1.0
    p, lo, hi = wilson(5, 100)
    assert lo < 0.05 < hi

    # A tiny source must not drag the overall rate around.
    big = [{"source": "big", "id": str(i)} for i in range(1000)]
    small = [{"source": "small", "id": "s%d" % i} for i in range(20)]
    sample, sizes = draw(big + small, 100)
    assert sizes == {"big": 1000, "small": 20}
    assert sum(1 for r in sample if r["source"] == "small") == MIN_PER_SOURCE
    assert draw(big + small, 100)[0] == sample, "draw must be reproducible"

    # big is clean, small is entirely wrong; weighting by population must land
    # near big's rate, not near the midpoint an unweighted mean would give.
    counts = {"big": (0, 98), "small": (10, 10)}
    p, n_eff, covered = weighted_rate(counts, sizes)
    assert abs(p - 20 / 1020) < 1e-9, p
    assert n_eff == 108 and covered == 1020

    # a source with nothing filled in is excluded, not treated as zero errors
    p2, _, covered2 = weighted_rate({"big": (0, 98)}, sizes)
    assert p2 == 0.0 and covered2 == 1000

    assert tally([{"source": "a", "khmer_ok": "N"},
                  {"source": "a", "khmer_ok": ""},
                  {"source": "a", "khmer_ok": "y"}], "khmer_ok") == {"a": (1, 2)}
    print("self-check ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draw")
    d.add_argument("-n", type=int, default=400, help="target sample size")
    d.add_argument("--seed", type=int, default=SEED)
    d.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    d.add_argument("-o", "--output", type=Path, default=DEFAULT_SAMPLE)
    d.add_argument("--sources", type=Path, default=BASE / "sources.json")
    d.add_argument("--pdf-dir", type=Path, default=BASE / "source_pdfs")
    d.add_argument("--no-locate", action="store_true",
                   help="skip page lookup (no PyMuPDF, or PDFs unavailable)")
    d.set_defaults(func=cmd_draw)
    s = sub.add_parser("score")
    s.add_argument("sample", type=Path, nargs="?", default=DEFAULT_SAMPLE)
    s.set_defaults(func=cmd_score)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        _self_check()
    else:
        main()
