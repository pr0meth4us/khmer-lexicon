"""Looking a word up — the thing people actually come here to do.

Search has to forgive spelling. Khmer is hard to type correctly and users get it
wrong constantly, so an exact-match-only dictionary tells most people "not
found" when the word is right there. When an exact search finds nothing we look
for entries one grapheme cluster away and offer them as suggestions.

That is done with a deletion index rather than comparing the query against all
5,777 forms: every form is stored under each of its single-cluster deletions, so
a near-match is a dict lookup. Built once at start-up.
"""
import collections
import unicodedata

from .contamination import is_khmer
from .graphemes import clusters, edit_distance
from .normalize import normalize

# Khmer labels are the primary UI language; English rides along for reviewers
# and for the many students who work bilingually.
CATEGORY_LABELS = {
    "Law & Civil Procedure": "ច្បាប់ និងនីតិវិធីរដ្ឋប្បវេណី",
    "Digital Technology & Telecom": "បច្ចេកវិទ្យាឌីជីថល និងទូរគមនាគមន៍",
    "Economics": "សេដ្ឋកិច្ច",
    "Policy, Tech & Economics": "គោលនយោបាយ បច្ចេកវិទ្យា និងសេដ្ឋកិច្ច",
    "Political Science & Diplomacy": "រដ្ឋបាលសាស្ត្រ និងការទូត",
    "Science, Tech & Mathematics": "វិទ្យាសាស្ត្រ បច្ចេកវិទ្យា និងគណិតវិទ្យា",
    "Geography": "ភូមិសាស្ត្រ",
    "General & New Words": "ពាក្យទូទៅ និងពាក្យថ្មី",
    "General & Specialized Terms (NCKL Bulletin)": "ពាក្យទូទៅ និងឯកទេស",
}


class Dictionary:
    def __init__(self, entries):
        self.entries = entries
        self.by_khmer = collections.defaultdict(list)
        for entry in entries:
            if entry["khmer"]:
                self.by_khmer[entry["khmer"]].append(entry)
        self._deletions = self._build_deletion_index()

    def _build_deletion_index(self):
        index = collections.defaultdict(set)
        for form in self.by_khmer:
            pieces = clusters(normalize(form))
            index[tuple(pieces)].add(form)
            for i in range(len(pieces)):
                index[tuple(pieces[:i] + pieces[i + 1:])].add(form)
        return index

    # ---- search --------------------------------------------------------

    def search(self, query, category="", limit=60):
        query = query.strip()
        if not query and not category:
            return {"results": [], "suggestions": [], "total": 0}

        rows = self.entries
        if category:
            rows = [e for e in rows if e["category"] == category]
        if not query:
            return {"results": rows[:limit], "suggestions": [],
                    "total": len(rows)}

        khmer_query = any(is_khmer(c) for c in query)
        needle = query.lower()
        exact, partial = [], []
        for entry in rows:
            if khmer_query:
                if entry["khmer"] == query:
                    exact.append(entry)
                elif query in entry["khmer"]:
                    partial.append(entry)
            else:
                english = entry["english"].lower()
                french = entry["french"].lower()
                if english == needle or french == needle:
                    exact.append(entry)
                elif needle in english or needle in french:
                    partial.append(entry)

        partial.sort(key=lambda e: len(e["english"] or e["khmer"]))
        results = exact + partial
        suggestions = [] if results else self.did_you_mean(query)
        return {"results": results[:limit], "suggestions": suggestions,
                "total": len(results)}

    def did_you_mean(self, query, limit=6):
        """Forms one grapheme cluster away. Empty for non-Khmer queries."""
        if not any(is_khmer(c) for c in query):
            return []
        pieces = clusters(normalize(query.strip()))
        keys = [tuple(pieces)]
        keys += [tuple(pieces[:i] + pieces[i + 1:]) for i in range(len(pieces))]
        seen = set()
        for key in keys:
            seen |= self._deletions.get(key, set())
        scored = []
        for form in seen:
            distance = edit_distance(normalize(query), normalize(form), cutoff=1)
            if distance <= 1:
                scored.append((distance, len(form), form))
        return [self.by_khmer[f][0] for _, _, f in sorted(scored)[:limit]]

    # ---- browse --------------------------------------------------------

    def categories(self):
        counts = collections.Counter(e["category"] for e in self.entries
                                     if e["category"])
        return [{"name": name,
                 "khmer": CATEGORY_LABELS.get(name, name),
                 "count": count}
                for name, count in counts.most_common()]

    def senses(self, khmer):
        return self.by_khmer.get(khmer, [])


def gloss_note(entry):
    """Why an entry has no English, said plainly instead of showing a dash."""
    if entry["english"]:
        return ""
    return "ប្រភពជាឯកសារភាសាខ្មែរសុទ្ធ — គ្មានពាក្យអង់គ្លេសភ្ជាប់មកទេ"
