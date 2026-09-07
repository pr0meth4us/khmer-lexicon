# Data Statement: Khmer Official Terminology

Following the schema of Bender & Friedman (2018), *Data Statements for Natural
Language Processing*, TACL 6:587–604.

Dataset: `dist/unified_lexicon.json`
Version: 1.0 · Build `1744764254eb` · Built 2026-09-05 · 5,934 entries

> **Status: unevaluated.** No measured accuracy figure exists for this dataset.
> See §7 and `EVALUATION.md`. Figures below are counts, not quality claims.

## 1. Curation rationale

Khmer is under-resourced in NLP, and Cambodian government bodies publish official
terminology — the standardised Khmer renderings of technical, legal and policy
concepts — as scanned PDFs with no machine-readable release. The intent is to
make that published terminology available as structured data, with each entry
traceable to the document that issued it, so that the official form of a term can
be checked rather than guessed.

Entries were not selected on linguistic criteria. The unit of selection was the
*document*: fifteen official sources were digitised in full, and every term they
contain is included. There is no sampling, filtering or quality threshold.

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
| National Council of Khmer Language (NCKL) | 3,573 |
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

5,934 entries across 15 sources and 9 subject categories. Field coverage:

| Field | Non-empty | Coverage |
|---|---:|---:|
| `khmer` | 5,910 | 99.6% |
| `english` | 4,277 | 72.1% |
| `french` | 3,448 | 58.1% |
| `definition` | 4,776 | 80.5% |
| `pos` | 1,601 | 27.0% |
| `examples` | 1,116 | 18.8% |
| `category` | 5,934 | 100% |

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

Mechanically detected defects, from `dist/validation_report.md`:

| Check | Count |
|---|---:|
| Entries with no Khmer at all | 24 |
| Khmer field containing no Khmer characters | 21 |
| Khmer field is a single bare consonant | 10 |
| Khmer shorter than 3 characters | 52 |
| Entries with no English gloss | 1,657 |
| Duplicate Khmer forms | 123 |
| Duplicate English glosses (case-insensitive) | 285 |
| Near-duplicate pairs | 162 |
| Single-word terms one plausible misread from a RAC dictionary word | 347 |
| Characters outside Khmer, Latin and punctuation | 13 |

These are only defects that produce something *detectably* wrong. The dominant
failure mode of Khmer OCR — a misread that turns one valid Khmer word into a
different valid Khmer word — is invisible to every check above and is not
counted here. The true error rate is therefore higher than this table, by an
unknown margin. Establishing that margin is what `EVALUATION.md` is for.

## 8. Distribution and licence

Public repository: https://github.com/pr0meth4us/khmer-lexicon

The repository ships `dist/sample_lexicon.json` (309 entries drawn from all 15
sources) together with the complete extraction pipeline, checker and quality
reports. The full 5,934-entry lexicon is **not** distributed in the repository.

The compilation is licensed CC BY-SA 4.0 (`LICENSE`). What is licensed is the
compilation — the extraction pipeline, normalisation and merge rules, provenance
annotation, checker, and the selection and arrangement of entries. The underlying
terminology is published by Cambodian government bodies and is not claimed here;
each entry carries its `source`, `author` and `year`. Cite the originating
document when what matters is a term's official status.

## 9. Other

Source PDFs are not redistributed. 13 of the 15 source documents are held
locally in `source_pdfs/` (gitignored); the remaining two — the Pentagonal
Strategy Phase 1 glossary and the NCKL technology and science volume — were
extracted from documents not retained in that directory, which limits
re-verification of those 953 entries.

No personal data. The dataset contains published terminology only.
