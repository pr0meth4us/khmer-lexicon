import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

import api as public_api
from khmerlex import Checker, Dictionary
from samples import SAMPLES

BASE = Path(__file__).resolve().parent
# The full lexicon if it is present (deployments mount it), otherwise the
# 309-entry sample committed here. The full file is deliberately not published;
# it is served through /api/v1 instead. See dist/README.md.
_FULL = BASE.parent / "dist" / "unified_lexicon.json"
_SAMPLE = BASE.parent / "dist" / "sample_lexicon.json"


def _fetch_lexicon():
    """Pull the full lexicon at boot if LEXICON_URL is configured.

    The full file is deliberately not in the repository, so a host that builds
    from GitHub would otherwise serve the 309-entry sample. Point LEXICON_URL at
    private storage (a private release asset, a secret gist, an R2/S3 object) and
    set LEXICON_TOKEN if it needs auth. Both are host secrets, never committed.

    Fetched once into a temp path at start-up, so the running container holds the
    data but nothing serves the file itself.
    """
    url = os.environ.get("LEXICON_URL", "").strip()
    if not url:
        return None
    import json
    import tempfile
    import urllib.request
    target = Path(tempfile.gettempdir()) / "unified_lexicon.json"
    if target.exists():
        return target
    request = urllib.request.Request(url)
    token = os.environ.get("LEXICON_TOKEN", "").strip()
    if token:
        request.add_header("Authorization", f"token {token}")
    request.add_header("Accept", "application/octet-stream")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read()
        entries = json.loads(body)
        if not isinstance(entries, list) or len(entries) < 1000:
            raise ValueError(f"expected the full lexicon, got {len(entries)} entries")
        target.write_bytes(body)
        print(f"loaded {len(entries):,} entries from LEXICON_URL", flush=True)
        return target
    except Exception as exc:                    # never fail to boot over this
        print(f"LEXICON_URL fetch failed ({exc}); falling back to the bundled "
              f"file", flush=True)
        return None


# Path("") is Path("."), which is truthy — check the string, not the Path.
_explicit = os.environ.get("LEXICON_PATH", "").strip()
DATA = Path(_explicit) if _explicit else (
    _fetch_lexicon() or (_FULL if _FULL.exists() else _SAMPLE))
MAX_CHARS = 8000

app = Flask(__name__)

CHECK = Checker(DATA)
WORDS = Dictionary(CHECK.entries)
# Warm the CRF model and both scan paths, so the first person to check a letter
# does not wait two seconds for a model to load.
CHECK.check(SAMPLES[0]["text"])


@app.get("/")
def index():
    return render_template("index.html", about=CHECK.about(), samples=SAMPLES,
                           categories=WORDS.categories())


@app.get("/how")
def how():
    return render_template("how.html", about=CHECK.about())


@app.get("/admin")
def admin():
    return render_template("admin.html", about=CHECK.about())


@app.get("/api")
def api_docs():
    return render_template("api.html", about=CHECK.about(),
                           categories=WORDS.categories())


@app.get("/api/search")
def api_search():
    limit = request.args.get("limit", 60, type=int)
    found = WORDS.search(request.args.get("q", ""),
                         category=request.args.get("category", ""),
                         limit=limit)
    return jsonify(found)


@app.get("/api/senses")
def api_senses():
    return jsonify({"senses": WORDS.senses(request.args.get("khmer", ""))})


@app.post("/api/check")
def api_check():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    if not text.strip():
        return jsonify({"error": "empty text"}), 400
    if len(text) > MAX_CHARS:
        return jsonify({"error": f"text too long ({MAX_CHARS} character limit)"}), 400
    return jsonify(CHECK.check(text, use_segmenter=payload.get("segmenter", True)))


@app.get("/api/about")
def api_about():
    return jsonify(CHECK.about())


@app.get("/healthz")
def healthz():
    return jsonify({"ok": True, "entries": len(CHECK.entries)})


public_api.register(app, WORDS, CHECK)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=False)
