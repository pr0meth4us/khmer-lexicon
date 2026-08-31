import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

import api as public_api
from khmerlex import Checker, Dictionary
from samples import SAMPLES

BASE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("LEXICON_PATH", BASE.parent / "dist" / "unified_lexicon.json"))
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
