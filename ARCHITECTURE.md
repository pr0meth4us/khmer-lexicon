# Architecture — Khmer Terminology Lexicon

How the pieces fit and *why*. For dependencies and the file roster, see
[README.md](README.md); this doc adds the end-to-end flow and rationale.

## The one idea

Official Khmer government terminology is locked inside scanned PDFs. This repo is
the **builder** that turns those PDFs into one structured, machine-readable
lexicon; the EGD letter-writer over in `egd platform` is the **consumer**. Build
here, publish into the platform, and the RAG picks up the refreshed terminology.

Split out of the `egd platform` repo on 2026-07-24 so the heavy OCR/parse tooling
(and ~200 MB of source PDFs) stops bloating the platform.

## Two artifacts, two roles

The platform ends up with two very different lexicon files doing opposite jobs:

| File | Size | Origin | Role |
|------|------|--------|------|
| `unified_lexicon.json` | large | built here | **RAG retrieval source** — *positive* signal: "use these exact official translations." |
| `house_lexicon.json` | tiny | hand-curated (reviewer VS) | **post-generation guard** — *negative* signal: fault English-only loanwords. |

This repo builds the first. The second lives in `egd platform` and is maintained
by hand — don't confuse them.

## Flow

```
Official PDFs  (source_pdfs/, gitignored ~200 MB)
  NCKL bulletins · MPTC digital terminology · Council-of-Ministers legal terms
  · Pentagonal Strategy · RAC new words · country/city names · extra word lists
        │
        ▼   OCR + parse  (one extractor per source shape)
  extract_nckl_bulletins.py · extract_nckl_tech_pdf.py · extract_pentagon_lexicon.py
  extract_pentagon_vision.py · extract_pdf_lexicons.py · extract_lexicons_cloud_vision.py
  extract_fancy_words.py · extract_extra_lexicons.py · parse_full_nais_pdfs.py
      → Cloud Vision OCR → Gemini parses raw text into
        { khmer, english, french, pos, definition, examples }
  retry_failed_pages.py   → re-run pages that failed extraction
        │
        ▼   normalize + merge
  clean_and_arrange_official_lexicons.py · standardize_pentagon_lexicon.py
  merge_all_lexicons.py   → writes unified_lexicon.json DIRECTLY into the platform
        │
        ▼   PUBLISH BOUNDARY (this repo writes into egd platform)
  egd platform/data/ai_letter_writer/training_datasets/*.json
    mptc_lexicon · nckl_political_science · legal_terms · pentagon · nckl_technology
    · country_and_city_names · extra_lexicon_* · official_lexicon_lookup
    → merge_all_lexicons.py tags each entry with a `source` and concatenates
      [panhavonh glossary, mptc, nckl_political_science, legal_terms] into
      unified_lexicon.json
        │
        ▼   CONSUMER — egd platform/apps/letter-rag/
  index_letters.py  collect_lexicon() reads unified_lexicon.json
    → ChromaDB collection "lexicon" (chroma_db_v2), embedded with a multilingual
      sentence-transformer (e5) or gemini-embedding-001
  query.py / apps/doc-pipeline/retrieve.py
    → semantic top-k EN↔KH terms injected into the Gemini prompt
      ("official EN↔KH terminology — use these exact translations")
        │
        ▼   GUARD — egd platform/apps/doc-pipeline/guards.py
  loanword_faults() reads house_lexicon.json → faults bare English
    (reviewer VS rule: render "ខ្មែរ (English)", never English-only)
  + foreign-script / homoglyph / Chuon-Nath spelling / spoken-register /
    whole-document guards
```

## Dependencies (not vendored here)

- **Bifrost SDK** — `get_genai_client`, `get_vision_client` (scripts add
  `bifrost/sdk/python` to `sys.path`).
- **`~/code/random`** — generic OCR/JSON helpers (`ocr_tools.pdf_ocr`,
  `json_tools.gemini_json`). Reuse/upgrade there per `~/code/random/AGENTS.md` —
  don't re-hand-roll them in this repo.

## Spot-check helpers

- `search_lexicon.py` — grep the built `unified_official_lexicon.json` by English
  base word.
- `match_terms_nais.py` — cross-check NAIS terms against the lexicon.

## Gotchas

- **The publish target is another repo.** Extractors write into
  `egd platform/data/ai_letter_writer/training_datasets/`. There is no local
  "output" folder — a rebuild mutates the platform's inputs directly.
- **`unified_lexicon.json` ≠ `unified_official_lexicon.json`.** The first is the
  RAG source (built by `merge_all_lexicons.py`); the second is a separate lookup
  used by `search_lexicon.py`.
- **`source_pdfs/` is gitignored.** A fresh clone can't rebuild without the
  originals.

For the knowledge-base view (and how this ties into the Reachsak RAG pipeline),
see the vault note **EGD - Khmer Terminology Lexicon**.
