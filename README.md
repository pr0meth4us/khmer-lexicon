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

> ## ⚠️ This data is OCR output and has not been fully verified
>
> Every entry was produced by running optical character recognition over a
> **scanned paper document**, then having a language model parse the result into
> structured fields. Both steps make mistakes. **Nobody has checked the output
> against the source PDFs page by page, and there is no measured accuracy figure
> for this dataset.**
>
> Mechanically detected so far: 21 entries whose Khmer field contains no Khmer,
> 682 single-word terms one syllable from a Royal Academy dictionary word, 164
> near-duplicate pairs, 24 entries with no Khmer, 1,657 with no English. Those
> are only the errors that produce something *detectably* wrong — an OCR mistake
> that turns one real Khmer word into a different real Khmer word is invisible to
> every check here.
>
> **This is actively being refined.** Corrections are applied as they are found
> and the dataset is re-validated on every build, so these numbers move.
>
> Every entry names its ministry, document and year. **If a term matters, open
> the original publication.** Treat this as a research tool and a finding aid,
> not an authoritative citation.
>
> **Spotted an error?**
> [Report it](https://github.com/pr0meth4us/khmer-lexicon/issues/new?labels=data-error)
> — every entry on the site has a one-click report link that pre-fills the term
> and its citation. That is the fastest way this improves.


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
