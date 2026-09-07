"""Check source_pdfs/ against the checksums in sources.json.

    python scripts/verify_sources.py          # local files only, offline
    python scripts/verify_sources.py --urls   # also re-check the published links

Link rot is the expected failure here: 11 of the 15 documents are advertised on
an official page whose file host is already dead. Run this before citing the
dataset, and record what it says.
"""
import argparse
import hashlib
import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (khmer-lexicon source verification)"}


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def check_local(sid, meta, pdf_dir):
    path = pdf_dir / meta["file"]
    if not path.exists():
        return "MISSING", "not in source_pdfs/"
    if path.stat().st_size != meta["bytes"]:
        return "FAIL", f"{path.stat().st_size} bytes, expected {meta['bytes']}"
    if sha256(path) != meta["sha256"]:
        return "FAIL", "checksum differs — this is not the file that was OCR'd"
    return "ok", ""


def check_url(meta, timeout=30):
    url = meta.get("official_url")
    if not url:
        return "skip", meta["url_status"]
    # Khmer filenames appear percent-decoded on the source pages
    safe = urllib.parse.quote(url, safe=":/?&=%")
    req = urllib.request.Request(safe, method="HEAD", headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            length = resp.headers.get("Content-Length")
            if length and int(length) != meta["bytes"]:
                return "CHANGED", f"{length} bytes, expected {meta['bytes']}"
            return "ok", f"HTTP {resp.status}"
    except Exception as exc:
        # A local trust-store problem is not link rot; saying "DEAD" here would
        # retire a live URL. macOS python.org builds need Install Certificates.command.
        if isinstance(getattr(exc, "reason", None), ssl.SSLCertVerificationError):
            return "TLS?", "local certificate store cannot verify this host"
        return "DEAD", type(exc).__name__ + ": " + str(exc)[:60]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--urls", action="store_true", help="also re-check links")
    ap.add_argument("--sources", type=Path, default=BASE / "sources.json")
    ap.add_argument("--pdf-dir", type=Path, default=BASE / "source_pdfs")
    args = ap.parse_args()

    sources = json.loads(args.sources.read_text(encoding="utf-8"))["sources"]
    bad = 0
    for sid, meta in sorted(sources.items()):
        state, detail = check_local(sid, meta, args.pdf_dir)
        bad += state in ("FAIL", "MISSING")
        line = f"{sid:38} local:{state}"
        if args.urls:
            ustate, udetail = check_url(meta)
            line += f"  url:{ustate}"
            detail = detail or udetail
        print(f"{line}  {detail}".rstrip())
    print(f"\n{len(sources)} sources, {bad} local problem(s)", file=sys.stderr)
    return 1 if bad else 0


def _self_check():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "a.pdf").write_bytes(b"hello")
        meta = {"file": "a.pdf", "bytes": 5,
                "sha256": hashlib.sha256(b"hello").hexdigest()}
        assert check_local("a", meta, d)[0] == "ok"
        # same length, different bytes: size alone must not pass it
        (d / "a.pdf").write_bytes(b"world")
        assert check_local("a", meta, d)[0] == "FAIL"
        assert check_local("a", dict(meta, file="gone.pdf"), d)[0] == "MISSING"
        assert check_url({"official_url": None, "url_status": "not-found"})[0] == "skip"
        # a certificate failure must not be reported as a dead link
        err = urllib.error.URLError(ssl.SSLCertVerificationError("bad chain"))
        assert isinstance(getattr(err, "reason", None), ssl.SSLCertVerificationError)
    print("self-check ok")


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        _self_check()
    else:
        sys.exit(main())
