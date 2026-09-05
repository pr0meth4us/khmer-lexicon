# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
### Added
- Build stamp: `dist/manifest.json` (build id, date, entry/source/quality counts)
  and `dist/build_index.json` (term id → hash of the normalised Khmer form).
  `scripts/build_manifest.py --diff OLD_INDEX` turns two indexes into an
  entry-level changelog — added, removed, khmer_changed — so a consumer can
  re-process only what moved. The id is content-addressed over Khmer forms only,
  so it changes when and only when a stored character offset could be invalid.
  Written by the build gate, so a build that regresses quality is never stamped.
- Two validator checks for truncated headwords: `khmer shorter than 3
  characters` (52) and `khmer is a single bare consonant` (10). Found by a
  consumer whose pipeline forced `official_lex_0907` — "quorum" rendered as the
  single consonant ម — into a generated sentence. The entry carries a full
  Council of Ministers definition and a French gloss; only the headword is gone,
  so every structural check passed it. The bare-consonant count is the
  recoverable set: a lone consonant has no vowel, so it is the first letter of a
  word rather than a word. A Khmer-vs-English length-ratio test was tried and
  rejected — Khmer is dense enough that one cluster spells a six-letter English
  word (មុំ "angle", កោះ "island"), so it flags 625 entries, nearly all correct.
- Id-level JSON sidecars beside the markdown reports: `dist/ocr_suspects.json`
  and `dist/near_duplicates.json`, each stamped with the build they describe.
  Near-duplicate pairs carry id *groups* per side, since a Khmer form can be
  carried by more than one entry.

### Changed
- The RAC suspect check flagged 682 terms and was mostly wrong. A downstream
  consumer scanned the lexicon against 56,669 real exam questions; of the six
  highest-occurrence suspects, none was an OCR error. Three gates now apply:
  ្ត and ្ដ are folded (46 pairs that were sorting to the top of the ranking are
  an orthography question, not a misread); compounds are skipped, because Khmer
  does not space its words and a headword dictionary structurally cannot hold
  them (1,211); and the swap must be a plausible misread rather than the nearest
  string in a 38,694-word list (183). **682 → 347.** No entry changed — the
  check got stricter, the data did not get better.
- `scripts/check_against_rac.py` is now reproducible. `substitutions()` yields
  from a set and the caller took the first match, so two identical runs gave
  183 and 176 suspects. It scores every candidate and takes the best.
- Canaries take ordinary `official_lex_NNNN` ids and sit inside the block of
  entries from the source each claims, instead of `canary_01`..`canary_05`
  appended at the end of the file, which anyone stripping the lexicon would have
  found with one grep.
- Near-duplicate pairs 164 → 162: a stale report catching up to a build that had
  already happened.
- **API, breaking:** `known_defects.one_syllable_from_a_dictionary_word` is
  renamed `one_misread_from_a_dictionary_word`. The old name no longer describes
  the test.

## [2026-08-31]
### Added
- Added `dist/` directory to track the generated output (`unified_lexicon.json` and `unified_official_lexicon.json`).
- Added `dist/README.md` containing a manifest and terminology count (5,932 entries).
- Added a "Sources" (ប្រភពឯកសារ) tab to clearly define citation abbreviations and books.
- Added pagination (Load More) functionality to category browsing.

### Changed
- Complete redesign of the UI to a minimal, professional aesthetic.
- Fully localized the user interface and category/author mappings to Khmer.
- Updated search result cards to strictly use the `Abbr · Book` citation format.
- Reorganized project structure by moving data processing scripts to the `scripts/` directory.
- Fixed OCR spelling and spacing defects in the entry for "life annuity contract" (`កិច្ចសន្យាធនលាភសមយិកមួយជីវិត`).

### Removed
- Removed the separate `/technical` page.
- Removed legacy UI elements and English placeholder labels.
