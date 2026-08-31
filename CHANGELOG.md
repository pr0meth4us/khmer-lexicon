# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
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

### Removed
- Removed the separate `/technical` page.
- Removed legacy UI elements and English placeholder labels.
