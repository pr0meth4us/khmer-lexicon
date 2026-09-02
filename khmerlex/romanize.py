"""Rough Khmer → Latin transliteration, for search only.

Most people type Latin faster than Khmer, especially on a phone, so a user who
knows a word by sound but not by spelling currently cannot find it at all. This
maps Khmer to an approximate Latin form so "tinnany" can reach ទិន្នន័យ.

It is deliberately NOT a correct romanisation. UNGEGN and the Royal Academy
system both encode distinctions (register, vowel length, final consonant
behaviour) that a person typing into a search box will not reproduce. Accuracy
would make matching WORSE. So this collapses aggressively: one Latin letter per
sound family, doubled letters squashed, silent finals kept, register ignored.
The output is a search key, never shown to a user.
"""
import re

from .graphemes import clusters

# Consonants. The two Khmer registers are collapsed: ក and គ both give "k",
# because someone typing by ear will not know which register a word uses.
_CONSONANT = {
    "ក": "k", "ខ": "kh", "គ": "k", "ឃ": "kh", "ង": "ng",
    "ច": "ch", "ឆ": "ch", "ជ": "ch", "ឈ": "ch", "ញ": "nh",
    "ដ": "d", "ឋ": "th", "ឌ": "d", "ឍ": "th", "ណ": "n",
    "ត": "t", "ថ": "th", "ទ": "t", "ធ": "th", "ន": "n",
    "ប": "b", "ផ": "ph", "ព": "p", "ភ": "ph", "ម": "m",
    "យ": "y", "រ": "r", "ល": "l", "វ": "v",
    "ស": "s", "ហ": "h", "ឡ": "l", "អ": "a",
    "ឣ": "a", "ឤ": "a", "ឥ": "e", "ឦ": "e", "ឧ": "o", "ឩ": "o",
    "ឪ": "ov", "ឫ": "r", "ឬ": "r", "ឭ": "l", "ឮ": "l",
    "ឯ": "ae", "ឰ": "ai", "ឱ": "ao", "ឲ": "ao", "ឳ": "au",
}

# Vowels and diacritics.
_VOWEL = {
    "ា": "a", "ិ": "i", "ី": "i", "ឹ": "eu", "ឺ": "eu",
    "ុ": "u", "ូ": "u", "ួ": "uo", "ើ": "ae", "ឿ": "ea",
    "ៀ": "ie", "េ": "e", "ែ": "ae", "ៃ": "ai", "ោ": "ao",
    "ៅ": "au", "ំ": "m", "ះ": "h", "ៈ": "", "់": "",
    "៌": "r", "៍": "", "៎": "", "៏": "", "័": "a", "្": "",
    "៑": "", "៝": "", "៊": "", "៉": "",
    # ័ SAMYOK SANNYA is a vowel in practice; dropping it loses a whole syllable
    # ("tinnay" became "tiny"), which is fatal for matching.
}

_KHMER_DIGIT = {d: str(i) for i, d in enumerate("០១២៣៤៥៦៧៨៩")}
_SQUASH = re.compile(r"(.)\1+")
_SQUASH_PAIR = re.compile(r"([a-z]{2})\1+")   # "chch" -> "ch", "ngng" -> "ng"


def romanize(text: str) -> str:
    """An approximate Latin search key for a Khmer string."""
    out = []
    for cluster in clusters(text):
        for ch in cluster:
            if ch in _CONSONANT:
                out.append(_CONSONANT[ch])
            elif ch in _VOWEL:
                out.append(_VOWEL[ch])
            elif ch in _KHMER_DIGIT:
                out.append(_KHMER_DIGIT[ch])
            elif ch.isascii() and ch.isalnum():
                out.append(ch.lower())
    return fold(" ".join("".join(out).split()))


def fold(latin: str) -> str:
    """Normalise a Latin string the same way both sides of a match must be.

    Doubled letters collapse ("tinnany" and "tinany" must agree) and everything
    that is not a letter or digit is dropped.
    """
    latin = re.sub(r"[^a-z0-9]+", "", latin.lower())
    latin = _SQUASH_PAIR.sub(r"\1", latin)
    return _SQUASH.sub(r"\1", latin)
