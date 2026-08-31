"""Public API: /api/v1, CORS-enabled, rate-limited.

Why this exists at all: fifteen government documents that existed only as paper
are now machine-readable. A website makes that readable by people; an API makes
it usable by every other Khmer-language tool — spellcheckers, keyboards,
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
import time

from flask import Blueprint, jsonify, request

api = Blueprint("api", __name__, url_prefix="/api/v1")

# Caps. No endpoint returns the whole lexicon: a caller who wants everything
# should clone the repo, which is cheaper for them and for us.
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
        return jsonify({"query": query, "category": category, **found})

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

    @api.get("/about")
    def about():
        return jsonify(check.about())

    app.register_blueprint(api)
    return api
