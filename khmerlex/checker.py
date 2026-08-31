"""Official Terminology Checker — one pass over the draft, every term at once.

The three things this has to get right, and why each is not obvious:

MATCHING. A dictionary of 5,700 Khmer terms scanned naively is 5,700 passes
over the document. Aho-Corasick is one pass whose cost does not grow with the
dictionary. Both are implemented and both are timed on every request, because
the honest answer depends on size: below ~220 terms the naive loop wins (C
`in` beats a Python automaton walk) and the UI says so.

BOUNDARIES. Khmer has no spaces between words, so a dictionary match can land
inside an unrelated longer word. Two filters, in order:
  1. Grapheme clusters — a match must start and end on a UAX #29 cluster
     boundary, or the highlight would cut a syllable in half. Cheap, and always
     applied.
  2. Word boundaries from khmer-nltk's CRF tokenizer — a match must also align
     with token edges. This is what removes ប្រក sitting inside ប្រកាស.
Cluster boundaries alone are NOT enough: nearly every spurious match begins and
ends on one. That was measured on the lexicon, not assumed.

OVERLAP. Longest match wins at each position, so ក្រុមប្រឹក្សាធម្មនុញ្ញ is
reported once rather than as three nested terms.
"""
import collections
import json
import time
from pathlib import Path

from .aho import AhoCorasick
from .contamination import contaminants, is_khmer
from .graphemes import boundaries, clusters

# Below this many clusters a "term" matches almost anything in spaceless Khmer.
MIN_TERM_CLUSTERS = 2
# Function words that appear in official glossaries but carry no terminology.
# The lexicon mixes technical terminology with general vocabulary (the Royal
# Academy new-word lists in particular), so a few very common words are excluded
# by hand. This is a hand-tuned list, not a learned one -- see the README.
STOP_WORDS = {
    "ការ", "ភាព", "នេះ", "នោះ", "អ្នក", "មាន", "និង", "ដែល", "ជា", "ក្នុង",
    "ដើម្បី", "ជាមួយ", "របស់", "ដោយ", "លើ", "ពី", "ទៅ", "គឺ", "បាន", "ហើយ",
    "ចូល", "ចេញ", "ប្រទេស", "ឯកសារ", "ធ្វើ", "ដាក់", "យក", "ឲ្យ", "ឱ្យ",
    "ត្រូវ", "នឹង", "ពេល", "ថ្ងៃ", "ឆ្នាំ", "ខែ", "រួច", "ម្តង", "គ្នា",
}


class Checker:
    TIMING_RUNS = 7

    @classmethod
    def _best(cls, fn):
        """Milliseconds for the fastest of TIMING_RUNS identical runs."""
        best = float("inf")
        for _ in range(cls.TIMING_RUNS):
            started = time.perf_counter()
            fn()
            best = min(best, time.perf_counter() - started)
        return best * 1000

    def __init__(self, path: Path):
        self.entries, self.by_khmer, self.by_english = self._load(Path(path))
        self.khmer_terms = sorted(self.by_khmer)
        self.english_terms = sorted(self.by_english)
        self.khmer_ac = AhoCorasick(self.khmer_terms)
        self.english_ac = AhoCorasick(self.english_terms)
        self._segmenter = None

    # ---- data ----------------------------------------------------------

    def _load(self, path):
        rows = json.loads(path.read_text(encoding="utf-8"))
        entries, by_khmer, by_english = [], collections.defaultdict(list), {}
        for row in rows:
            khmer = (row.get("khmer") or "").strip()
            english = (row.get("english") or "").strip()
            entry = {k: (row.get(k) or "").strip() for k in
                     ("id", "khmer", "english", "french", "category",
                      "source", "author", "year", "definition", "pos",
                      "examples")}
            entries.append(entry)
            # Entries whose "khmer" field holds no Khmer at all are extraction
            # failures (legacy-font OCR read as Latin). 21 of them; indexing
            # them would match that garbage in a draft. See the validator.
            if khmer and any(is_khmer(c) for c in khmer) \
                    and len(clusters(khmer)) >= MIN_TERM_CLUSTERS \
                    and khmer not in STOP_WORDS:
                by_khmer[khmer].append(entry)
            # Loanword direction: an English term whose approved Khmer we know.
            if english and khmer and len(english) >= 4 and english.isascii():
                by_english.setdefault(english.lower(), entry)
        return entries, dict(by_khmer), by_english

    def segmenter(self):
        """khmer-nltk's CRF tokenizer, imported lazily so the app boots fast."""
        if self._segmenter is None:
            from khmernltk import word_tokenize
            self._segmenter = word_tokenize
        return self._segmenter

    # ---- matching ------------------------------------------------------

    @staticmethod
    def _longest_only(hits):
        """Drop any match fully contained in another. Longest wins per position."""
        hits = sorted(hits, key=lambda h: (h["start"], -(h["end"] - h["start"])))
        kept, covered_to = [], -1
        for hit in hits:
            if hit["start"] >= covered_to:
                kept.append(hit)
                covered_to = hit["end"]
            elif hit["end"] > covered_to:          # partial overlap, keep longer
                if hit["end"] - hit["start"] > kept[-1]["end"] - kept[-1]["start"]:
                    kept[-1] = hit
                    covered_to = hit["end"]
        return kept

    def word_bounds(self, text):
        """Token start/end offsets from the CRF segmenter."""
        starts, ends, cursor = {0}, {len(text)}, 0
        for token in self.segmenter()(text):
            start = text.find(token, cursor)
            if start == -1:
                continue
            starts.add(start)
            ends.add(start + len(token))
            cursor = start + len(token)
        return starts, ends

    def check(self, text: str, use_segmenter: bool = True):
        counters = {"characters": len(text),
                    "clusters": len(clusters(text)),
                    "khmer_terms_in_automaton": len(self.khmer_terms),
                    "english_terms_in_automaton": len(self.english_terms),
                    "automaton_nodes": len(self.khmer_ac)}

        # Best of N, not one shot. A single timing on a short draft is mostly
        # cache noise -- on the first request it can even show the naive scan
        # winning at 5,689 terms, which is not true. Best-of is the standard
        # way to time this and is stated in the UI.
        raw = [{"term": term, "start": start, "end": end}
               for start, end, term in self.khmer_ac.finditer(text)]
        counters["aho_ms"] = round(self._best(
            lambda: list(self.khmer_ac.finditer(text))), 3)
        counters["naive_ms"] = round(self._best(
            lambda: {t for t in self.khmer_terms if t in text}), 3)
        counters["timing_runs"] = self.TIMING_RUNS
        counters["agree"] = ({t for t in self.khmer_terms if t in text}
                             == {h["term"] for h in raw})
        counters["raw_matches"] = len(raw)

        cluster_edges = boundaries(text)
        on_cluster, split_cluster = [], []
        for hit in raw:
            target = on_cluster if (hit["start"] in cluster_edges
                                    and hit["end"] in cluster_edges) else split_cluster
            target.append(hit)
        counters["rejected_split_cluster"] = len(split_cluster)

        rejected = [dict(h, reason="would split a grapheme cluster")
                    for h in split_cluster]
        kept = on_cluster
        if use_segmenter:
            started = time.perf_counter()
            starts, ends = self.word_bounds(text)
            counters["segmenter_ms"] = round((time.perf_counter() - started) * 1000, 3)
            counters["rejected_inside_word"] = 0
            aligned = []
            for hit in on_cluster:
                if hit["start"] in starts and hit["end"] in ends:
                    aligned.append(hit)
                else:
                    rejected.append(dict(hit, reason="sits inside a longer word"))
            kept = aligned
        before_overlap = len(kept)
        kept = self._longest_only(kept)
        # Every raw hit is accounted for, so the panel adds up:
        #   raw = matches + split-cluster + inside-a-word + nested
        counters["merged_into_longer"] = before_overlap - len(kept)
        counters["matches"] = len(kept)
        counters["rejected"] = len(rejected)
        assert (counters["matches"] + counters["rejected"]
                + counters["merged_into_longer"] == counters["raw_matches"])

        for hit in kept:
            hit["senses"] = self.by_khmer.get(hit["term"], [])

        return {
            "text": text,
            "matches": kept,
            "rejected": sorted(rejected, key=lambda h: h["start"]),
            "loanwords": self.loanwords(text),
            "contamination": self.contamination(text),
            "counters": counters,
        }

    def loanwords(self, text):
        """English sitting in Khmer text that the lexicon has an approved form for."""
        lowered = text.lower()
        out = []
        for start, end, term in self.english_ac.finditer(lowered):
            before = lowered[start - 1] if start else " "
            after = lowered[end] if end < len(lowered) else " "
            if before.isalnum() or after.isalnum():      # whole word only
                continue
            entry = self.by_english[term]
            if entry["khmer"] in text:                   # already rendered
                continue
            out.append({"term": text[start:end], "start": start, "end": end,
                        "suggest": entry["khmer"], "entry": entry})
        return self._longest_only(out)

    @staticmethod
    def contamination(text):
        return contaminants(text, allow_latin=True)

    # ---- about ---------------------------------------------------------

    def about(self):
        sources = collections.Counter()
        for entry in self.entries:
            if entry["source"]:
                sources[(entry["source"], entry["author"], entry["year"])] += 1
        return {
            "entries": len(self.entries),
            "distinct_khmer_forms": len({e["khmer"] for e in self.entries if e["khmer"]}),
            "terms_indexed": len(self.khmer_terms),
            "english_indexed": len(self.english_terms),
            "sources": [{"tag": t, "author": a, "year": y, "count": n}
                        for (t, a, y), n in sorted(sources.items())],
        }
