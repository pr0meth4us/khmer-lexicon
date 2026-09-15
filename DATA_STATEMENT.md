# Data Statement: Khmer Official Terminology

Following the schema of Bender & Friedman (2018), *Data Statements for Natural
Language Processing*, TACL 6:587–604.

Dataset: `dist/unified_lexicon.json`
Version: 1.1 · Build `0e11fa6c1df3` · Built 2026-09-15 · 6,702 entries

> **Measured Khmer headword error rate: 20.1% [14.7–27.3%]** (n=153, seed
> 20260907, covering 3,807 of the 5,934 v1.0 entries). English glosses: 0.0%
> [0.0–2.4%] (n=158). The seven documents added in v1.1, measured on their own:
> Khmer 17.9% [13.1–23.7%] (n=197), English 0.4% [0.1–3.4%] (n=163). One
> annotator, an AI model reading page renders; not yet confirmed by a native
> Khmer reader. See §7 and `EVALUATION.md`.

## 1. Curation rationale

Khmer is under-resourced in NLP, and Cambodian government bodies publish official
terminology — the standardised Khmer renderings of technical, legal and policy
concepts — as scanned PDFs with no machine-readable release. The intent is to
make that published terminology available as structured data, with each entry
traceable to the document that issued it, so that the official form of a term can
be checked rather than guessed.

Entries were not selected on linguistic criteria. The unit of selection was the
*document*: fifteen official sources were digitised in full for v1.0, and every
term they contain is included. v1.1 adds seven documents recovered from archived
captures of the NCKL's previous website. From those, three kinds of entry were
left out:
- terms already present with the same Khmer and English;
- the word-formation tables on pages 8–19 of Bulletin No. 2, which are a grammar
  exercise, not terminology;
- 18 entries that were empty or plainly extraction failures: no Khmer, OCR junk
  characters, definition text in the headword, or a lone consonant.

Beyond that there is no sampling, filtering or quality threshold.

## 2. Language variety

Khmer (`km`, ISO 639-3 `khm`), standard written register as used in Cambodian
government publication. English (`en`) and French (`fr`) appear as gloss
languages, not as independently curated content — French coverage reflects which
source documents happened to be trilingual, chiefly the Council of Ministers
legal terms and the country/city name lists.

This is formal, institutional, prescriptive language. It is not conversational
Khmer, not regional, and not representative of general usage. Terms are
frequently neologisms coined by the issuing body.

## 3. Speaker / author demographic

Not individual speakers. Authorship is institutional:

| Issuing body | Entries |
|---|---:|
| National Council of Khmer Language (NCKL) | 4,341 |
| Royal Academy of Cambodia (National Language Institute) | 1,223 |
| Royal Government of Cambodia | 486 |
| Council of Ministers | 373 |
| Ministry of Post and Telecommunications (MPTC) | 279 |

Individual committee members are not named in the source documents and are not
recorded here. Publication years span 2007–2025.

## 4. Annotator demographic

None. There is no human annotation layer. The `pos`, `category` and `definition`
fields are transcriptions of what the source documents themselves printed, not
judgements added by an annotator. Where those fields are inconsistent, the
inconsistency is inherited from the sources (see §6).

## 5. Speech situation

Written, edited, published, asynchronous. Each source is an official terminology
bulletin, lexicon or glossary intended as normative guidance for translators,
civil servants and the press. The intended audience is professional, and the
register is uniformly formal.

## 6. Text characteristics

6,702 entries across 22 sources and 14 subject categories. Field coverage:

| Field | Non-empty | Coverage |
|---|---:|---:|
| `khmer` | 6,678 | 99.6% |
| `english` | 4,870 | 72.7% |
| `french` | 4,011 | 59.8% |
| `definition` | 5,485 | 81.8% |
| `pos` | 1,712 | 25.5% |
| `examples` | 1,416 | 21.1% |
| `category` | 6,702 | 100% |

Entries are terms, not running text — typically one to five words. Definitions,
where present, are one or two sentences of Khmer.

**Known inconsistencies.** The `pos` field is not normalised: it mixes Khmer
abbreviations (`ន.`, `កិ.`), English labels (`noun`, `Proper Noun`), and French
gender markers (`m.`, `f.`) that are not parts of speech at all. `scripts/export_tbx.py`
normalises these for TBX output; the JSON preserves the source forms. The
`version` field is `1.0` for every entry and carries no information.

## 7. Provenance and known defects

Every entry was produced by running OCR (Google Cloud Vision) over a scanned
paper document, then having a language model parse the OCR output into fields.
Both steps introduce errors. **No entry has been verified against its source page
by a human reader.**

### Measured accuracy (2026-09-14)

A seeded stratified sample of 401 entries (`scripts/evaluate_sample.py`,
seed 20260907) was checked against the source pages. Each entry was located by
its English gloss, the page rendered, and the headword compared character by
character, zooming to 600–700 dpi wherever a mark was in doubt.

| Field | Rows checked | Errors | Error rate (size-weighted) | 95% interval |
|---|---:|---:|---:|---|
| Khmer headword | 153 | 34 | 20.1% | 14.7–27.3% |
| English gloss | 158 | 0 | 0.0% | 0.0–2.4% |

About one Khmer headword in five differs from the printed page. The English
glosses were correct in every row checked. Of the 34 Khmer errors, 21 are a
dropped vowel or subscript (ឥណ្ឌា → ឥណ្ឌ, គណនេយ្យ → គណនយ្យ); the rest are a
letter swapped for another, a leading word lost, a garbled word, a stray
character, or an empty field. Per-source figures are in
`dist/evaluation_result.json`; they range from 0 of 6 to 12 of 30 and are
indicative only at these sample sizes.

**What the figure does not cover.** It speaks for 3,807 of 5,934 entries. Three
sources could not be checked this way: RAC New Words (1,223 entries; image-only
scan, and most entries have no English gloss to locate them by), the Pentagonal
Strategy glossary (486; image-only), and NCKL Bulletin Vol. 4 (418; legacy-font
text layer). Entries containing ្ត or ្ដ were excluded by design, because the
two render identically and cannot be judged by eye; they are listed, with the
Royal Academy dictionary's spelling, in the ្ត/្ដ worklist.

### Recovered sources, added in v1.1 (2026-09-15)

The 2,624 entries extracted from the seven recovered documents were sampled on
their own, located and checked the same way, from 300 dpi crops placed by Cloud
Vision word boxes.

| Field | Rows checked | Errors | Error rate (size-weighted) | 95% interval |
|---|---:|---:|---:|---|
| Khmer headword | 197 | 34 | 17.9% | 13.1–23.7% |
| English gloss | 163 | 1 | 0.4% | 0.1–3.4% |

A first pass found 46 Khmer and 12 English errors. 19 of the Khmer errors were
the extraction step, not OCR: a headword wrapping onto a second line was cut
off, or a printed second form ("/ …", "(…)") was dropped. Most of the English
errors came from Bulletin No. 2's country tables, where the English column was
never read. After the extraction prompt was fixed, the same rows were checked
again. The rows that had not changed kept their verdicts, and the 23 that had
changed were judged afresh:
- 9 of the extraction errors were fixed outright;
- 8 now expose an OCR misread in the recovered text;
- 1 pulled definition text into the headword.

That re-check is paired, not a fresh sample, and the annotator had seen the
first verdicts. The figure describes the 2,624 entries of the first extraction.
The fixed extraction yields 2,697, of which 768 were merged.

**Who checked.** One annotator: an AI model (Claude) reading rendered pages.
No native Khmer reader has confirmed the verdicts. A second, human pass over the
34 recorded errors is the obvious next step, and the error rate should be read
as provisional until then.

**Cause.** Re-running Cloud Vision on six pages with known errors showed no single
cause: Vision itself misread two words, one was lost when the OCR text was
structured into entries, and two matched neither form in a fresh OCR run. A
re-extraction would not clear these errors on its own.

Mechanically detected defects, from `dist/validation_report.md`:

| Check | Count |
|---|---:|
| Entries with no Khmer at all | 24 |
| Khmer field containing no Khmer characters | 21 |
| Khmer field is a single bare consonant | 10 |
| Khmer shorter than 3 characters | 60 |
| Entries with no English gloss | 1,832 |
| Duplicate Khmer forms | 253 |
| Duplicate English glosses (case-insensitive) | 595 |
| Near-duplicate pairs | 417 |
| Single-word terms one plausible misread from a RAC dictionary word (v1.0 entries; not rerun) | 347 |
| Characters outside Khmer, Latin and punctuation | 13 |

These are only defects that produce something *detectably* wrong. The dominant
failure mode of Khmer OCR — a misread that turns one valid Khmer word into a
different valid Khmer word — is invisible to every check above and is not
counted here. The true error rate is therefore higher than this table, by an
unknown margin. Establishing that margin is what `EVALUATION.md` is for.

## 8. Distribution and licence

Public repository: https://github.com/pr0meth4us/khmer-lexicon

The repository ships `dist/sample_lexicon.json` (309 entries drawn from the 15
v1.0 sources) together with the complete extraction pipeline, checker and quality
reports. The full 6,702-entry lexicon is **not** distributed in the repository.

The compilation is licensed CC BY-SA 4.0 (`LICENSE`). What is licensed is the
compilation — the extraction pipeline, normalisation and merge rules, provenance
annotation, checker, and the selection and arrangement of entries. The underlying
terminology is published by Cambodian government bodies and is not claimed here;
each entry carries its `source`, `author` and `year`. Cite the originating
document when what matters is a term's official status.

## 9. Other

Source PDFs are not redistributed. All 22 source documents are held locally in
`source_pdfs/` and `source_pdfs/candidates/` (gitignored), so every entry can be
checked against its page.

`sources.json` records, per source: the issuing body, year, entry count, the
SHA-256 and byte size of the exact file the pipeline read, and where the
document can be obtained. Its `url_status` field is honest about how far each
link was checked:

| Status | Sources | Meaning |
|---|---:|---|
| `verified` | 1 | re-downloaded; SHA-256 identical to the local copy |
| `size-match` | 1 | HTTP 200 and byte size identical; body not re-hashed |
| `content-identical` | 2 | a copy downloads from the Ministry of Education's Sala Digital library; different bytes, but every page renders pixel-identical |
| `listed-but-unreachable` | 11 | advertised on the official NCKL page, but the file host does not resolve |
| `archived-only` | 7 | recovered from a Wayback Machine capture of the NCKL's previous website; the original URL returned 404 on 2026-09-15 |

The eleven NCKL documents are listed for download at
https://nckl.rac.gov.kh/bulletin/index, but that page serves its files from
`panel.racmanagementsystem.academy`, which did not resolve in DNS on 2026-09-07.
The links are therefore dead at the publisher, and the copies here cannot be
re-fetched from source. No Wayback Machine snapshot of that host exists. This is
a preservation problem for Khmer terminology generally, not only for this
dataset.

No personal data. The dataset contains published terminology only.
