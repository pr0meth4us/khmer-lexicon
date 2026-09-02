"""Public API: /api/v1, CORS-enabled, rate-limited.

Why this exists at all: fifteen government documents that existed only as paper
are now machine-readable. A website makes that readable by people; an API makes
it usable by every other Khmer-language tool — keyboards,
translation memories, government CMSes. That is the difference between a demo
and a piece of infrastructure.

On making it "unscrapable": it cannot be, and pretending otherwise would be
worse than useless. dist/unified_lexicon.json is a public file in a public
repository, and the web page itself has to read it. What these limits actually
buy is protection from *cheap* bulk pulls and from one caller degrading the
service for everyone — a speed bump, not a lock. The honest posture is the one
khmerdict takes: give the data away deliberately, and ask for attribution.
"""
import collections
import json
import os
import subprocess
import time

from flask import Blueprint, jsonify, request

api = Blueprint("api", __name__, url_prefix="/api/v1")

# Caps. No endpoint returns the whole lexicon: a caller who wants everything
# should clone the repo, which is cheaper for them and for us.
# DO NOT ADD AN offset/page/cursor PARAMETER.
#
# This is the single measure that actually prevents enumeration, and it happened
# by accident before it was a decision. Without it, extracting the lexicon means
# guessing Khmer search terms you do not already have; /categories caps at
# MAX_LIMIT per category, so at most ~900 of 5,929 entries are reachable however
# patient you are. Rate limits only slow a scraper down. This stops one.
#
# A future "helpful" pagination parameter would undo every other protection here
# in a single commit. If bulk access is genuinely needed, hand over a file.
MAX_LIMIT = 100
DEFAULT_LIMIT = 40
MAX_CHARS = 8000

# Per-IP sliding window, in memory. Deliberately not Redis: one process, one
# demo, and a dependency that can fail at request time is worse than a limit
# that resets on deploy.
WINDOW_SECONDS = 60
MAX_REQUESTS = 60
_hits = collections.defaultdict(collections.deque)


def _client():
    forwarded = request.headers.get("X-Forwarded-For", "")
    return forwarded.split(",")[0].strip() or request.remote_addr or "unknown"


def _rate_limited():
    now = time.monotonic()
    seen = _hits[_client()]
    while seen and now - seen[0] > WINDOW_SECONDS:
        seen.popleft()
    if len(seen) >= MAX_REQUESTS:
        return True
    seen.append(now)
    if len(_hits) > 10_000:                     # bound the table, not the users
        for key in [k for k, v in _hits.items() if not v]:
            del _hits[key]
    return False


@api.before_request
def _guard():
    if request.method == "OPTIONS":
        return None
    if _rate_limited():
        return jsonify({"error": "rate limited",
                        "limit": f"{MAX_REQUESTS} requests per {WINDOW_SECONDS}s",
                        "hint": "the whole lexicon is at "
                                "github.com/pr0meth4us/khmer-lexicon-demo — clone "
                                "it instead of paging through this"}), 429
    return None


@api.after_request
def _cors(response):
    # Read-only public data, so a wildcard origin is the correct answer.
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Cache-Control"] = "public, max-age=300"
    response.headers["X-Licence"] = "Khmer government terminology; attribution requested"
    # Anyone consuming this programmatically deserves the same warning the web
    # page carries, in a place they cannot miss.
    response.headers["X-Data-Warning"] = (
        "OCR-derived from scanned documents and not fully verified; entries may "
        "be wrong. Check the cited source publication before relying on a term.")
    return response


def _limit():
    asked = request.args.get("limit", DEFAULT_LIMIT, type=int) or DEFAULT_LIMIT
    return max(1, min(asked, MAX_LIMIT))


def register(app, words, check):
    """Bind the blueprint to the loaded dictionary and checker."""

    @api.get("/search")
    def search():
        query = request.args.get("q", "")
        category = request.args.get("category", "")
        if not query and not category:
            return jsonify({"error": "pass q= or category="}), 400
        found = words.search(query, category=category, limit=_limit())
        if query and not found["results"]:
            # A query that returns nothing is a user telling us exactly which
            # term is missing or misspelled. Logged as structured JSON so the
            # gap list builds itself instead of waiting for someone to complain.
            #   gcloud logging read 'jsonPayload.kind="zero_result"' \
            #       --project khmer-ocr-496606 --limit 100
            print(json.dumps({
                "kind": "zero_result",
                "query": query[:120],
                "category": category[:80],
                "had_suggestions": bool(found.get("suggestions")),
            }, ensure_ascii=False), flush=True)
        return jsonify({"query": query, "category": category, **found})

    @api.get("/sources")
    def sources():
        return jsonify({"sources": words.sources()})

    @api.get("/letters")
    def letters():
        return jsonify({"letters": words.letters()})

    @api.get("/browse")
    def browse():
        source = request.args.get("source", "")
        letter = request.args.get("letter", "")
        if source:
            return jsonify(words.by_source(source, limit=_limit()))
        if letter:
            return jsonify(words.by_letter(letter, limit=_limit()))
        return jsonify({"error": "pass source= or letter="}), 400

    @api.get("/term")
    def term():
        khmer = request.args.get("khmer", "").strip()
        if not khmer:
            return jsonify({"error": "pass khmer="}), 400
        senses = words.senses(khmer)
        if not senses:
            return jsonify({"khmer": khmer, "senses": [],
                            "suggestions": words.did_you_mean(khmer)}), 404
        return jsonify({"khmer": khmer, "senses": senses})

    @api.get("/categories")
    def categories():
        return jsonify({"categories": words.categories()})

    @api.post("/check")
    def check_text():
        payload = request.get_json(silent=True) or {}
        text = payload.get("text", "")
        if not text.strip():
            return jsonify({"error": "pass text"}), 400
        if len(text) > MAX_CHARS:
            return jsonify({"error": f"text too long ({MAX_CHARS} character limit)"}), 400
        return jsonify(check.check(text, use_segmenter=payload.get("segmenter", True)))

    @api.post("/report")
    def report():
        """A correction from a reader.

        Written to Cloud Logging as a structured entry rather than a database:
        the service is stateless and free, and reports are rare enough that a
        log query is the right tool. Read them with:

            gcloud logging read 'jsonPayload.kind="lexicon_report"' \
                --project khmer-ocr-496606 --limit 50 --format json

        Inherits the blueprint's 60/minute rate limit, so it cannot be flooded
        cheaply. No account, no email required — the point is that a civil
        servant who spots a wrong term can say so in ten seconds.
        """
        payload = request.get_json(silent=True) or {}
        message = (payload.get("message") or "").strip()
        if not message:
            return jsonify({"error": "message required"}), 400
        entry = {
            "kind": "lexicon_report",
            "khmer": (payload.get("khmer") or "")[:200],
            "entry_id": (payload.get("entry_id") or "")[:60],
            "source": (payload.get("source") or "")[:120],
            "message": message[:2000],
            "contact": (payload.get("contact") or "")[:200],
        }
        # print() lands in Cloud Logging; JSON on one line becomes jsonPayload.
        print(json.dumps(entry, ensure_ascii=False), flush=True)
        return jsonify({"ok": True})

    @api.get("/feedback")
    def feedback():
        """Recent corrections and failed searches, for the maintainer.

        Reads Cloud Logging directly rather than keeping a database: the service
        is stateless, reports are rare, and the log sink already archives them
        to Cloud Storage permanently. Guarded by ADMIN_TOKEN — without one set,
        the endpoint refuses rather than defaulting to open.
        """
        expected = os.environ.get("ADMIN_TOKEN", "").strip()
        supplied = (request.args.get("token", "")
                    or request.headers.get("X-Admin-Token", "")).strip()
        if not expected or supplied != expected:
            return jsonify({"error": "not authorised"}), 403

        def read(kind, limit):
            try:
                out = subprocess.run(
                    ["gcloud", "logging", "read", f'jsonPayload.kind="{kind}"',
                     "--project", os.environ.get("GOOGLE_CLOUD_PROJECT", "khmer-ocr-496606"),
                     "--limit", str(limit), "--format", "json"],
                    capture_output=True, text=True, timeout=25)
                rows = json.loads(out.stdout or "[]")
                return [{"time": r.get("timestamp", "")[:19],
                         **{k: v for k, v in r.get("jsonPayload", {}).items() if k != "kind"}}
                        for r in rows]
            except Exception as exc:
                return [{"error": str(exc)[:120]}]

        reports = read("lexicon_report", 100)
        misses = read("zero_result", 300)
        counts = collections.Counter(m.get("query", "") for m in misses if m.get("query"))
        return jsonify({
            "reports": reports,
            "zero_result_top": [{"query": q, "times": n} for q, n in counts.most_common(40)],
            "zero_result_recent": misses[:40],
        })

    @api.get("/about")
    def about():
        return jsonify({
            **check.about(),
            "disclaimer": (
                "This lexicon was produced by OCR over scanned government PDFs "
                "and parsed by a language model. It has NOT been fully verified "
                "against the source documents and has no measured accuracy "
                "figure. Individual entries may be wrong. Every entry names its "
                "source publication and year — check the original before relying "
                "on a term in official writing. It is actively being refined; "
                "report errors at "
                "https://github.com/pr0meth4us/khmer-lexicon/issues"),
            "known_defects": {
                "khmer_field_with_no_khmer": 21,
                "one_syllable_from_a_dictionary_word": 682,
                "near_duplicate_pairs": 164,
                "mark_order_corrected_at_build": 23,
                "missing_khmer": 24,
                "missing_english": 1657,
            },
        })

    app.register_blueprint(api)
    return api
