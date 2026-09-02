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
from .romanize import fold, romanize

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
        # Latin search key per distinct form, so someone who knows a word by
        # sound can find it without a Khmer keyboard.
        self._roman = {form: romanize(form) for form in self.by_khmer}

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
        roman_needle = fold(query) if not khmer_query else ""
        exact, partial, loose = [], [], []
        for entry in rows:
            if khmer_query:
                if entry["khmer"] == query:
                    exact.append(entry)
                elif query in entry["khmer"]:
                    partial.append(entry)
                # 1,657 entries have no English at all; searching the Khmer
                # definition is the only way they are ever discoverable.
                elif query in entry["definition"]:
                    loose.append(entry)
            else:
                english = entry["english"].lower()
                french = entry["french"].lower()
                if english == needle or french == needle:
                    exact.append(entry)
                elif needle in english or needle in french:
                    partial.append(entry)
                elif roman_needle and len(roman_needle) >= 3:
                    key = self._roman.get(entry["khmer"], "")
                    if not key:
                        continue
                    distance = 0 if roman_needle in key else edit_distance(
                        roman_needle, key, cutoff=2)
                    if distance <= 2:
                        loose.append((distance, len(entry["khmer"]), entry))

        partial.sort(key=lambda e: len(e["english"] or e["khmer"]))
        # Sound-alike hits rank by how close the Latin key is, not by length:
        # sorting by length put តិណាសី above ទិន្នន័យ for "tinnany".
        if loose and isinstance(loose[0], tuple):
            loose.sort(key=lambda t: (t[0], t[1]))
            loose = [t[2] for t in loose]
        else:
            loose.sort(key=lambda e: len(e["khmer"]))
        results = exact + partial + loose
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

    def sources(self):
        """Browse by publication. The category field puts 3,482 of 5,934 entries
        under two labels, which makes browsing by category nearly useless; the
        source document is meaningful, dated and attributable."""
        seen = {}
        for entry in self.entries:
            key = entry["source"]
            if not key:
                continue
            row = seen.setdefault(key, {"source": key, "author": entry["author"],
                                        "year": entry["year"], "count": 0})
            row["count"] += 1
        return sorted(seen.values(), key=lambda r: (-r["count"], r["source"]))

    def letters(self):
        """Khmer alphabet index — the affordance every paper dictionary has."""
        counts = collections.Counter()
        for form in self.by_khmer:
            first = clusters(form)[0] if form else ""
            if first and is_khmer(first[0]):
                counts[first[0]] += 1
        return [{"letter": ch, "count": n} for ch, n in sorted(counts.items())]

    def by_source(self, source, limit=200):
        rows = [e for e in self.entries if e["source"] == source]
        return {"results": rows[:limit], "total": len(rows), "suggestions": []}

    def by_letter(self, letter, limit=200):
        rows = [e for e in self.entries
                if e["khmer"] and clusters(e["khmer"])[0].startswith(letter)]
        rows.sort(key=lambda e: e["khmer"])
        return {"results": rows[:limit], "total": len(rows), "suggestions": []}

    def senses(self, khmer):
        return self.by_khmer.get(khmer, [])


def gloss_note(entry):
    """Why an entry has no English, said plainly instead of showing a dash."""
    if entry["english"]:
        return ""
    return "ប្រភពជាឯកសារភាសាខ្មែរសុទ្ធ — គ្មានពាក្យអង់គ្លេសភ្ជាប់មកទេ"
