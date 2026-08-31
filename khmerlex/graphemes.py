"""Grapheme clusters for Khmer, so nothing ever cuts a syllable in half.

Khmer writes one syllable as several code points: a base consonant, optional
subscript consonants introduced by COENG (U+17D2), and vowel/diacritic marks
(U+17B6-U+17D3). `len()`, slicing and indexing all operate on code points and
will happily cut between them, producing a fragment that renders as a stray
mark and matches nothing.

    len("ក្រសួង")                      -> 6 code points
    len(clusters("ក្រសួង"))            -> 3 clusters:  ក្រ | សួ | ង

UAX #29 extended grapheme clusters are exactly this boundary, and the `regex`
module's \\X implements them. Verified on real lexicon terms that \\X binds
COENG to the consonant that follows it and attaches marks to their base, so no
Khmer-specific approximation is needed:

    ក្រសួង   6 cp -> 3 clusters   ក្រ | សួ | ង
    ស្ត្រី   6 cp -> 1 cluster    ស្ត្រី
    សេចក្ដី  7 cp -> 3 clusters   សេ | ច | ក្ដី
"""
import regex

_CLUSTER = regex.compile(r"\X")


def clusters(text: str) -> list[str]:
    """Split into UAX #29 extended grapheme clusters."""
    return _CLUSTER.findall(text)


def cluster_len(text: str) -> int:
    """Length in clusters, i.e. in things a reader would call a character."""
    return len(_CLUSTER.findall(text))


def boundaries(text: str) -> set[int]:
    """Code-point offsets at which a cluster starts (plus the end offset).

    An offset NOT in this set points into the middle of a cluster: slicing
    there splits a syllable, and a match landing there is spurious.
    """
    out, i = {0}, 0
    for cluster in _CLUSTER.findall(text):
        i += len(cluster)
        out.add(i)
    return out


def on_boundary(text: str, start: int, end: int) -> bool:
    """Does [start:end) begin and end on cluster boundaries?"""
    bounds = boundaries(text)
    return start in bounds and end in bounds


def edit_distance(a: str, b: str, cutoff: int | None = None) -> int:
    """Levenshtein distance in CLUSTERS, not code points.

    Code-point distance is meaningless for Khmer: dropping one mark from a
    3-cluster word is distance 1 in code points but changes a whole syllable,
    while two words differing by a full syllable can also be distance 1. This
    counts the units a reader perceives.

    `cutoff` returns early (as cutoff + 1) once every cell of a row exceeds it,
    which is what makes the all-pairs sweep in task 5 tractable.
    """
    xs, ys = clusters(a), clusters(b)
    if abs(len(xs) - len(ys)) > (cutoff if cutoff is not None else len(xs) + len(ys)):
        return cutoff + 1
    previous = list(range(len(ys) + 1))
    for i, x in enumerate(xs, 1):
        current = [i]
        for j, y in enumerate(ys, 1):
            current.append(min(previous[j] + 1,          # deletion
                               current[j - 1] + 1,       # insertion
                               previous[j - 1] + (x != y)))  # substitution
        if cutoff is not None and min(current) > cutoff:
            return cutoff + 1
        previous = current
    return previous[-1]
