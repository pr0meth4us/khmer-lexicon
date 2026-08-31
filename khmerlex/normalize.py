"""Canonical mark order for Khmer, which Unicode normalisation will not give you.

NFC reorders combining marks by canonical combining class. Khmer has almost no
canonical combining classes to reorder: of the 114 named characters in the
block, only U+17D2 COENG and U+17DD ATTHACAN have a nonzero ccc. Every vowel
and every sign is ccc=0, and NFC treats ccc=0 as "already in order". So two
spellings of the same syllable that differ only in the order their marks were
typed are NFC-identical and byte-different, forever.

    ភ្ជាប់  = ភ ្ ជ ា ប ់     (canonical: coeng before vowel)
    ភា្ជប់  = ភ ា ្ ជ ប ់     (as typed: vowel before coeng)
    NFC leaves both exactly as they are; they never compare equal.

The second is a real entry in dist/unified_lexicon.json. It renders wrong and
sorts, searches and dedupes as a different word.

So the ordering has to be imposed by a script-specific rule. The model is the
Khmer orthographic syllable from the Unicode Standard:

    base  robat  (coeng + consonant)*  shifter  vowel  sign*

`normalize()` stable-sorts the marks of each syllable into that order and
touches nothing else. It is idempotent, and it never adds, drops or substitutes
a character -- only reorders -- so it cannot invent a word that was not typed.
"""
import unicodedata as ud

COENG = "្"
ROBAT = "៌"
_BASE = range(0x1780, 0x17B4)        # consonants + independent vowels
_VOWEL = range(0x17B6, 0x17C6)
_SHIFTER = ("៉", "៊")      # MUUSIKATOAN, TRIISAP
_SIGN = tuple("ំះៈ់៍៎៏័៑៝")

# Order within a syllable. Coeng pairs keep their relative order (stable sort),
# because ស្ត្រ and ស្រ្ត are genuinely different words, not orderings.
_ROBAT, _COENG_PAIR, _SHIFT, _VOW, _SIGNS = 1, 2, 3, 4, 5


def _rank(piece: str) -> int:
    if piece.startswith(COENG):
        return _COENG_PAIR
    if piece == ROBAT:
        return _ROBAT
    if piece in _SHIFTER:
        return _SHIFT
    if len(piece) == 1 and ord(piece) in _VOWEL:
        return _VOW
    return _SIGNS


def _is_base(char: str) -> bool:
    return ord(char) in _BASE


def _is_mark(char: str) -> bool:
    return char == COENG or ord(char) in _VOWEL or char in _SIGNER


_SIGNER = set(_SIGN) | set(_SHIFTER) | {ROBAT}


def _syllable_pieces(text: str, i: int):
    """Read the marks following a base at text[i], as indivisible pieces.

    A coeng and the consonant it introduces are ONE piece: they move together
    or the word changes.
    """
    pieces, j = [], i + 1
    while j < len(text):
        char = text[j]
        if char == COENG and j + 1 < len(text) and _is_base(text[j + 1]):
            pieces.append(text[j:j + 2])
            j += 2
        elif _is_mark(char):
            pieces.append(char)
            j += 1
        else:
            break
    return pieces, j


def normalize(text: str) -> str:
    """Put each Khmer syllable's marks into canonical order."""
    out, i = [], 0
    while i < len(text):
        char = text[i]
        if not _is_base(char):
            out.append(char)
            i += 1
            continue
        pieces, j = _syllable_pieces(text, i)
        out.append(char)
        out.extend(sorted(pieces, key=_rank))     # stable: ties keep input order
        i = j
    return "".join(out)


def nfc_evidence() -> str:
    """Why NFC cannot do this. Printed rather than asserted, so it can be read."""
    named = [chr(cp) for cp in range(0x1780, 0x1800)
             if ud.name(chr(cp), "").startswith("KHMER")]
    nonzero = [c for c in named if ud.combining(c)]
    pairs = [("ភ្ជាប់", "ភា្ជប់"), ("ក្តី", "កី្ត")]
    lines = [
        f"Khmer characters with a name:            {len(named)}",
        f"...with a nonzero combining class:       {len(nonzero)}"
        f"   {' '.join(f'U+{ord(c):04X}({ud.combining(c)})' for c in nonzero)}",
        "NFC reorders only by combining class, and ccc=0 counts as ordered,",
        "so every vowel and sign in the block is invisible to it.",
        "",
    ]
    for good, bad in pairs:
        lines.append(
            f"  {good!r} vs {bad!r}: "
            f"equal? {good == bad}   "
            f"NFC-equal? {ud.normalize('NFC', good) == ud.normalize('NFC', bad)}   "
            f"NFD-equal? {ud.normalize('NFD', good) == ud.normalize('NFD', bad)}   "
            f"khmerlex-equal? {normalize(good) == normalize(bad)}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(nfc_evidence())
