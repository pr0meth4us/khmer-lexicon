"""Characters that do not belong in Khmer text, and what they should have been.

Three different relations get confused with each other, so they are kept apart:

1. SAME LETTER, WRONG SCRIPT. The Brahmic scripts share letter names, so
   U+0940 DEVANAGARI VOWEL SIGN II and U+17B8 KHMER VOWEL SIGN II are the same
   letter encoded in the wrong block. This is the failure mode actually observed
   in production -- Gemini emitted the Devanagari code point mid-Khmer, and it is
   invisible in most editors. Derived by matching Unicode NAMEs across script
   prefixes rather than hand-listing pairs: 195 pairs over 7 scripts, which
   includes the 4 that were hand-listed.

2. VISUAL CONFUSABLE (UTS #39). Characters that LOOK alike regardless of name --
   Thai SARA I for Khmer VOWEL SIGN I, COMBINING RING ABOVE for NIKAHIT.
   Unicode publishes this; we read it from confusable_homoglyphs rather than
   maintaining it. Only 10 non-Khmer characters map into Khmer.

   These two sets barely overlap. UTS #39 does NOT contain any of the four
   Devanagari pairs above, because those do not look alike -- they are the same
   letter, not a look-alike. Using UTS #39 *instead of* the hand-written table
   would have dropped 4 mappings observed in production and added 10 never
   observed. The union is what is correct.

3. NOVEL SCRIPT. Everything outside Khmer + Latin + shared punctuation, caught
   by a negated class rather than an allow-list, because the point is to catch
   what neither table above anticipated. Over dist/unified_lexicon.json this
   finds a Cyrillic ш that both tables miss.
"""
import unicodedata as ud

KHMER = range(0x1780, 0x1800)
KHMER_DIGITS = range(0x17E0, 0x17EA)
# Zero-width joiners, Khmer-legal spacing, and the house punctuation set.
SHARED_PUNCT = set(" \t\n​‌‍–—‘’“”…")

_SCRIPT_PREFIXES = (
    "DEVANAGARI ", "THAI CHARACTER ", "THAI ", "LAO ", "MYANMAR ",
    "BENGALI ", "TAMIL ", "TELUGU ", "SINHALA ",
)


def _khmer_by_name():
    out = {}
    for cp in KHMER:
        try:
            name = ud.name(chr(cp))
        except ValueError:
            continue
        if name.startswith("KHMER "):
            out[name[len("KHMER "):]] = chr(cp)
    return out


def _same_letter_wrong_script():
    """Cross-script pairs whose Unicode NAME matches after the script prefix."""
    khmer, pairs = _khmer_by_name(), {}
    for cp in range(0x0900, 0x1780):
        char = chr(cp)
        try:
            name = ud.name(char)
        except ValueError:
            continue
        for prefix in _SCRIPT_PREFIXES:
            if name.startswith(prefix):
                target = khmer.get(name[len(prefix):])
                if target:
                    pairs[char] = target
                break
    return pairs


def _visual_confusables():
    """UTS #39 confusables that resolve to a Khmer character."""
    try:
        import json
        import os

        import confusable_homoglyphs
        path = os.path.join(os.path.dirname(confusable_homoglyphs.__file__),
                            "confusables.json")
        data = json.load(open(path, encoding="utf-8"))
    except Exception:            # data file absent -> lose 10 pairs, not correctness
        return {}
    pairs = {}
    for source, targets in data.items():
        if len(source) != 1 or is_khmer(source) or source.isascii():
            continue
        for entry in targets:
            target = entry.get("c", "")
            if len(target) == 1 and is_khmer(target):
                pairs[source] = target
                break
    return pairs


def is_khmer(char: str) -> bool:
    return ord(char[0]) in KHMER or ord(char[0]) in KHMER_DIGITS


SAME_LETTER = _same_letter_wrong_script()
VISUAL = _visual_confusables()
# same-letter wins where both have an opinion: it is the observed failure mode.
CONFUSABLES = {**VISUAL, **SAME_LETTER}


def repair(text: str) -> str:
    """Map every known wrong-script character to its Khmer counterpart."""
    return text.translate({ord(k): v for k, v in CONFUSABLES.items()})


def contaminants(text: str, allow_latin: bool = True) -> list[dict]:
    """Every character that does not belong, with why and (if known) the fix.

    `allow_latin=False` is for fields that must be Khmer-only, such as the
    `khmer` column of the lexicon; document text legitimately mixes in Latin
    for acronyms and phone numbers, so guards keep the default.
    """
    out = []
    for i, char in enumerate(text):
        if is_khmer(char) or char in SHARED_PUNCT:
            continue
        if char.isascii():
            if allow_latin or not char.isalnum():
                continue
            reason = "Latin in a Khmer-only field"
        elif char in SAME_LETTER:
            reason = "same letter, wrong script"
        elif char in VISUAL:
            reason = "UTS #39 visual confusable"
        else:
            reason = "outside Khmer, Latin and shared punctuation"
        out.append({
            "index": i,
            "char": char,
            "name": ud.name(char, f"U+{ord(char):04X}"),
            "reason": reason,
            "suggest": CONFUSABLES.get(char, ""),
        })
    return out


def as_table() -> dict:
    """The merged mapping as plain JSON, for consumers that should not take a
    dependency on this package just to read a lookup table."""
    return {
        "_comment": (
            "Generated by khmerlex/contamination.py -- do not hand-edit; "
            "regenerate with `python3 -m khmerlex.contamination`. "
            "Maps a wrong-script character to the Khmer character intended. "
            "same_letter: Unicode NAME matches across script prefixes (the "
            "observed production failure -- Devanagari code point emitted for "
            "the Khmer one). visual: UTS #39 confusables that resolve to Khmer. "
            "UTS #39 contains none of the same_letter pairs, so the union is "
            "required: neither table alone is sufficient."
        ),
        "same_letter": SAME_LETTER,
        "visual": VISUAL,
    }


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(as_table(), ensure_ascii=False, indent=2), file=sys.stdout)
