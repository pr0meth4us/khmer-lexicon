"""Data-quality gate for the merged lexicon.

Runs after the build, writes dist/validation_report.md, and exits non-zero if
any defect count is worse than the committed baseline in dist/quality_baseline
.json. That makes it usable as a build gate: a re-OCR or a new source that
introduces defects fails loudly instead of quietly landing in dist/.

Ratchet, not a threshold. The baseline records what is wrong today; the gate
only refuses to let it get worse. Improvements print as such and the baseline
is updated with --accept.

    python3 validate_lexicon.py            # check, exit 1 on regression
    python3 validate_lexicon.py --accept   # rewrite the baseline
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

from khmerlex import cluster_len, clusters, contaminants, is_khmer, normalize

HERE = Path(__file__).parent
LEXICON = HERE / "dist" / "unified_lexicon.json"
BASELINE = HERE / "dist" / "quality_baseline.json"
REPORT = HERE / "dist" / "validation_report.md"

# 143 terms exceed 20 clusters. The longest is 52 and is a slash-separated
# definition dumped into the khmer field, not a term -- so length is a signal
# for extraction failure, but only well past the 95th percentile.
LONG_TERM_CLUSTERS = 20
ASCII_DIGIT = re.compile(r"[0-9]")
KHMER_DIGIT = re.compile(r"[០-៩]")


def check(rows):
    """Every check returns (count, [examples]). Counts are what the gate ratchets."""
    khmer = [(r, (r.get("khmer") or "").strip()) for r in rows]
    non_empty = [(r, t) for r, t in khmer if t]
    out = {}

    out["empty khmer"] = [r["id"] for r, t in khmer if not t]
    out["empty english"] = [r["id"] for r in rows if not (r.get("english") or "").strip()]

    # A khmer field with no Khmer in it is an extraction failure, unlike a
    # khmer field that merely also carries a Latin acronym -- which is house
    # style. Distinguishing these is the whole point; "has Latin" is not a bug.
    out["khmer field with no Khmer at all"] = [
        f"{r['id']} {t!r}" for r, t in non_empty if not any(is_khmer(c) for c in t)
    ]
    out["characters outside Khmer, Latin and punctuation (occurrences)"] = [
        f"{r['id']} {t!r} ({c['name']})"
        for r, t in non_empty
        for c in contaminants(t, allow_latin=True)
    ]
    out["ASCII digits in khmer"] = [
        f"{r['id']} {t!r}" for r, t in non_empty if ASCII_DIGIT.search(t)
    ]
    out["not in canonical mark order"] = [
        f"{r['id']} {t!r} -> {normalize(t)!r}" for r, t in non_empty if normalize(t) != t
    ]

    forms = collections.defaultdict(list)
    for r, t in non_empty:
        forms[t].append(r)
    out["duplicate khmer forms"] = [
        f"{t!r} x{len(v)}" for t, v in forms.items() if len(v) > 1
    ]
    english = collections.Counter(
        (r.get("english") or "").strip().lower() for r in rows
        if (r.get("english") or "").strip()
    )
    out["duplicate english glosses (case-insensitive)"] = [
        f"{e!r} x{n}" for e, n in english.items() if n > 1
    ]
    out[f"terms longer than {LONG_TERM_CLUSTERS} clusters"] = sorted(
        (f"{cluster_len(t)} clusters: {t[:60]}" for _, t in non_empty
         if cluster_len(t) > LONG_TERM_CLUSTERS),
        key=lambda s: -int(s.split()[0]),
    )
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--accept", action="store_true",
                        help="rewrite the baseline from the current numbers")
    args = parser.parse_args()

    rows = json.loads(LEXICON.read_text("utf-8"))
    results = check(rows)
    counts = {name: len(items) for name, items in results.items()}
    counts["entries"] = len(rows)

    baseline = json.loads(BASELINE.read_text("utf-8")) if BASELINE.exists() else {}
    regressions, improvements = [], []
    for name, now in counts.items():
        if name == "entries":
            continue
        was = baseline.get(name)
        if was is None:
            continue
        if now > was:
            regressions.append((name, was, now))
        elif now < was:
            improvements.append((name, was, now))

    lines = [
        "# Lexicon validation report",
        "",
        f"`{LEXICON.name}` — {len(rows):,} entries",
        "",
        "| check | count | baseline |",
        "| --- | ---: | ---: |",
    ]
    for name in results:
        was = baseline.get(name)
        mark = ""
        if was is not None and counts[name] > was:
            mark = " ⬆ REGRESSION"
        elif was is not None and counts[name] < was:
            mark = " ⬇ improved"
        lines.append(f"| {name} | {counts[name]} | {'—' if was is None else was}{mark} |")
    lines.append("")
    for name, items in results.items():
        if not items:
            continue
        lines += [f"## {name} ({len(items)})", ""]
        lines += [f"- {i}" for i in items[:25]]
        if len(items) > 25:
            lines.append(f"- …and {len(items) - 25} more")
        lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")

    for name, count in counts.items():
        print(f"{count:>6}  {name}")
    print(f"\nreport -> {REPORT}")

    if args.accept:
        BASELINE.write_text(json.dumps(counts, indent=2, sort_keys=True) + "\n", "utf-8")
        print(f"baseline updated -> {BASELINE}")
        return 0
    for name, was, now in improvements:
        print(f"improved: {name} {was} -> {now} (run --accept to lock it in)")
    if regressions:
        print("\nFAILED — these got worse:", file=sys.stderr)
        for name, was, now in regressions:
            print(f"  {name}: {was} -> {now}", file=sys.stderr)
        return 1
    print("\nok — no regressions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
