"""Build stamp + entry-level delta for the published lexicon.

Consumers vendor dist/unified_lexicon.json and need to answer two questions:
"which build was this generated against?" and "what changed since?".

    python3 scripts/build_manifest.py            # write manifest + index
    python3 scripts/build_manifest.py --diff OLD_INDEX   # delta vs an old index

Writes two files:
  dist/manifest.json     — build id, date, counts. Small, committed, safe to publish.
  dist/build_index.json  — {id: 8-hex of the normalised Khmer form}, gitignored,
                           ships with the lexicon. Two of these diff into an
                           entry-level changelog without needing either lexicon.
"""
import argparse
import collections
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from khmerlex import normalize  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LEXICON = ROOT / "dist" / "unified_lexicon.json"
MANIFEST = ROOT / "dist" / "manifest.json"
INDEX = ROOT / "dist" / "build_index.json"
BASELINE = ROOT / "dist" / "quality_baseline.json"


def khmer_hash(entry):
    return hashlib.sha256(normalize(entry.get("khmer", "")).encode()).hexdigest()[:8]


def build(entries):
    index = {e["id"]: khmer_hash(e) for e in entries}
    # build_id is content-addressed: same data in, same id out, on any machine.
    digest = hashlib.sha256(
        json.dumps(index, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:12]
    manifest = {
        "build_id": digest,
        "built_at": datetime.now(timezone.utc).date().isoformat(),
        "entries": len(entries),
        "sources": dict(
            sorted(collections.Counter(e.get("source", "") for e in entries).items())
        ),
        "quality": json.loads(BASELINE.read_text()) if BASELINE.exists() else {},
    }
    return manifest, {"build_id": digest, "entries": index}


def diff(old, new):
    a, b = old["entries"], new["entries"]
    return {
        "from_build": old["build_id"],
        "to_build": new["build_id"],
        "added": sorted(b.keys() - a.keys()),
        "removed": sorted(a.keys() - b.keys()),
        "khmer_changed": sorted(k for k in a.keys() & b.keys() if a[k] != b[k]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diff", metavar="OLD_INDEX", help="old build_index.json to diff against")
    args = ap.parse_args()

    entries = json.loads(LEXICON.read_text(encoding="utf-8"))
    manifest, index = build(entries)

    if args.diff:
        old = json.loads(Path(args.diff).read_text(encoding="utf-8"))
        d = diff(old, index)
        print(json.dumps(d, indent=2))
        print(
            f"\n{d['from_build']} -> {d['to_build']}: "
            f"+{len(d['added'])} -{len(d['removed'])} ~{len(d['khmer_changed'])}",
            file=sys.stderr,
        )
        return 0

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", "utf-8")
    INDEX.write_text(json.dumps(index, ensure_ascii=False) + "\n", "utf-8")
    print(f"build {manifest['build_id']}  {manifest['entries']} entries  -> {MANIFEST}, {INDEX}")
    return 0


def _selfcheck():
    old = {"build_id": "a", "entries": {"x": "1", "y": "2", "z": "3"}}
    new = {"build_id": "b", "entries": {"x": "1", "y": "9", "w": "4"}}
    d = diff(old, new)
    assert d["added"] == ["w"], d
    assert d["removed"] == ["z"], d
    assert d["khmer_changed"] == ["y"], d
    m1, i1 = build([{"id": "a", "khmer": "ក"}])
    m2, i2 = build([{"id": "a", "khmer": "ក"}])
    assert i1 == i2 and m1["build_id"] == m2["build_id"]
    m3, _ = build([{"id": "a", "khmer": "ខ"}])
    assert m3["build_id"] != m1["build_id"]
    print("selfcheck ok")


if __name__ == "__main__":
    sys.exit(_selfcheck() if "--selfcheck" in sys.argv else main())
