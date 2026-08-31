---
title: Khmer Official Terminology
emoji: 🇰🇭
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
pinned: false
license: cc-by-sa-4.0
short_description: Search 5,929 official Cambodian government terms, or check a Khmer draft
---

# khmer-lexicon

Build pipeline for Khmer government terminology lexicons: OCR official PDFs
(NCKL bulletins, MPTC digital lexicon, Council of Ministers legal terms,
Pentagonal Strategy, RAC new words, …) with Cloud Vision, parse the text into
structured `{khmer, english, french, pos, definition, examples}` entries with
Gemini, then merge + standardize into a unified lexicon.

Split out of a larger internal system — this is the **builder**; the downstream
letter-writer RAG is the **consumer** of the built lexicon.

## Dependencies (not vendored here)

- **Google AI + credentials** → a small internal helper that wraps Vertex AI
  client construction (`bifrost_ai`). Substitute `google.genai` directly if you
  do not have it; it only loads credentials.
  (`get_genai_client`, `get_vision_client`). Scripts add it to `sys.path`.
- **Generic OCR / JSON helpers** → `~/code/random`
  (`ocr_tools.pdf_ocr`, `json_tools.gemini_json`). Reuse/upgrade there, per
  `~/code/random/AGENTS.md` — don't re-hand-roll them here.
- `pip install pymupdf google-genai google-cloud-vision python-dotenv requests`

## Layout

- `source_pdfs/` — the official source PDFs (gitignored, ~200 MB).
- `extract_*.py` / `parse_*.py` — per-source OCR → JSON extractors.
- `retry_failed_pages.py` — re-run pages that failed extraction.
- `merge_all_lexicons.py`, `clean_and_arrange_official_lexicons.py`,
  `standardize_pentagon_lexicon.py` — combine/normalize into the unified lexicon.
- `search_lexicon.py`, `match_terms_nais.py` — query/spot-check helpers.

## Publishing to the platform

The extractors write their output JSONs into `$LEXICON_BUILD_DIR` (default
`build/`), previously a
`data/ai_letter_writer/training_datasets/`, which the letter-rag app reads
(`unified_lexicon.json`). That is the publish target — rebuild here, and the
platform picks up the refreshed lexicon.
