---
title: Khmer Official Terminology
emoji: 🇰🇭
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
pinned: false
license: cc-by-sa-4.0
short_description: Search 6,702 official Cambodian government terms, or check a Khmer draft
---

# khmer-lexicon

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22746199.svg)](https://doi.org/10.5281/zenodo.22746199)

> ## ⚠️ This data is OCR output and has not been fully verified
>
> Every entry was produced by running optical character recognition over a
> **scanned paper document**, then having a language model parse the result into
> structured fields. Both steps make mistakes. **A sample checked against the
> source pages found about one Khmer headword in five wrong: 20.1% [14.7–27.3%],
> n=153.** English glosses were correct in every row checked (0.0% [0.0–2.4%],
> n=158). The figure covers 3,807 of the 5,934 v1.0 entries. The documents added
> in v1.1 measured 17.9% [13.1–23.7%] on their own (n=197). Both figures were
> made by one annotator (an AI model reading page renders) and have not yet been
> confirmed by a native Khmer reader. Details in `DATA_STATEMENT.md` §7.
>
> Mechanically detected so far: 21 entries whose Khmer field contains no Khmer,
> 347 single-word terms one plausible misread from a Royal Academy dictionary
> word (v1.0 entries), 417 near-duplicate pairs, 24 entries with no Khmer, 1,832 with no English. Those
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

## Licence and what it covers

The compilation is licensed **CC BY-SA 4.0** (see `LICENSE`). Share-alike:
anything built on this data must be released under the same terms.

What that licence covers is the *compilation* — the extraction pipeline, the
normalisation and merge rules, the provenance annotation, the checker, and the
selection and arrangement of entries. The underlying terminology is published by
Cambodian government bodies (NCKL, the Royal Academy of Cambodia, MPTC, the
Council of Ministers and others) and is not claimed here; each entry carries its
`source`, `author` and `year`. Cite the originating document, not this repo, when
what you need is the term's official status.

### What this repository contains

Not the full lexicon. `dist/unified_lexicon.json` (6,702 entries) and
`dist/unified_official_lexicon.json` are gitignored; what ships is
`dist/sample_lexicon.json` — 309 entries drawn from the 15 v1.0 sources —
alongside the extractors, the checker and the quality reports, which are complete.

So a clone reproduces the pipeline, not the dataset. `CITATION.cff` and the
release tags describe the compilation as a whole; anyone citing the repository
for the *data* is citing the 309-entry sample unless the full file has been
shared with them separately.

`sources.json` records where each of the 22 source documents came from, with a
SHA-256 of the exact file the pipeline read; `python scripts/verify_sources.py`
checks the local PDFs against it, and `--urls` re-checks the published links.

`candidates.json` lists 40 further NCKL PDFs recovered from Wayback Machine
captures of the council's previous website; seven of them became sources in
v1.1 — see "Recovered from archived captures" below.

`DATA_STATEMENT.md` describes the dataset in the Bender & Friedman schema —
curation rationale, language variety, provenance, and known defects.
`EVALUATION.md` is the procedure for replacing the missing accuracy figure with
a measured one.

Cite the dataset with `CITATION.cff`, or via the "Cite this repository" button on
GitHub.

DOI (all versions): [10.5281/zenodo.22746199](https://doi.org/10.5281/zenodo.22746199). v1.1.0: [10.5281/zenodo.22761423](https://doi.org/10.5281/zenodo.22761423). v1.0.0: [10.5281/zenodo.22746200](https://doi.org/10.5281/zenodo.22746200).

## Other formats

    python scripts/export_tbx.py

writes `dist/unified_lexicon.tbx` — TBX (ISO 30042:2019, TBX-Basic dialect) for
termbase and CAT tools. One concept per entry, `km`/`en`/`fr` sections, with
source/author/year as concept-level `<admin type="source">`. The 24 entries with
no Khmer headword are skipped. The output is gitignored, like the full lexicon it
is built from.

## Recovered from archived captures

The National Council of Khmer Language lists its terminology documents for
download at https://nckl.rac.gov.kh/bulletin/index, but that page serves the
files from `panel.racmanagementsystem.academy`, a domain that no longer resolves.
Captures of the council's *previous* website survive, and
`source_pdfs/candidates/` (gitignored) holds 40 PDFs recovered from them.
`candidates.json` records each one's checksum, capture URL and what it is.

Identified by Cloud Vision OCR of each file's title, middle and last pages
(`scripts/identify_candidates.py`), with duplicates confirmed by pixel
comparison against `source_pdfs/`:

- **7 new term sources, merged in v1.1:** glossaries of Linguistics &
  Literature (2013), Culture & Fine Arts (2015), Medicine & Agriculture (2015),
  Philosophy (2019) and Health (2019); NCKL Bulletins No. 2 (2009) and No. 6
  (2014). They yielded 2,697 entries, but most repeat terms first published in
  Bulletins 3–10 (Bulletin No. 6 is almost entirely the 2014 Technology &
  Science lexicon), so 768 were added. `python scripts/merge_new_sources.py`
  appends them to the lexicon, and its docstring gives the rules.
- **11 duplicates** of documents already here.
- **22 without term entries:** founding decrees and decisions for the NCKL and
  Royal Academy, NCKL Bulletin No. 1 (2008; committee lists and decree articles,
  no glosses in 61 pages), a national Khmer language policy (2019), a grammar book, an
  orthography guide, a 2020 round-table report, and one file truncated in the
  only capture that exists.

One correction fell out of this: `NCKL_Bulletin_Vol6_Technology_2014.pdf` is not
Bulletin No. 6 but the NCKL Science & Technology glossary. Its entries are
correctly attributed (`nckl-technology-and-science`); only the filename is wrong.
