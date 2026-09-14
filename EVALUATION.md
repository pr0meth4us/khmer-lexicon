# Evaluating this lexicon

**First result (2026-09-14):** Khmer headword error rate 20.1% [14.7–27.3%],
n=153; English gloss 0.0% [0.0–2.4%], n=158; seed 20260907; covering 3,807 of
5,934 entries; one annotator, an AI model reading page renders. Summary counts in
`dist/evaluation_result.json`, discussion in `DATA_STATEMENT.md` §7.

Before this, the dataset had counts but no measured accuracy. Every figure in
`dist/validation_report.md` is a *detectable* defect — an empty field, a
duplicate, a character out of range. The dominant failure mode of Khmer OCR is
none of those: it turns one valid Khmer word into a different valid Khmer word,
and no automated check here can see it. Only a human with the source page can.

This document is the procedure for producing that number. It needs no tooling
beyond the two scripts below and the PDFs in `source_pdfs/`.

## What is being measured

Two independent error rates, per entry:

- **`khmer_ok`** — does the Khmer headword match the source page exactly?
  This is the number that matters. A wrong headword makes the entry actively
  misleading, because the whole point of the dataset is the official form.
- **`english_ok`** — does the English gloss match what the source printed?
  Lower stakes: a wrong gloss is findable by a reader who knows the term.

Judge against **what the document printed**, not against what is correct. If
the ministry published a typo, the entry is right to reproduce it — note it in
`notes` and mark it `y`. This is a transcription evaluation, not a review of
Cambodian terminology policy.

Count as an error (`n`): any difference in characters, including a missing or
added diacritic, wrong subscript, wrong vowel, or wrong zero-width character.
Khmer renders such differences invisibly at small sizes — compare at high zoom,
and when in doubt paste both strings into a diff rather than eyeballing them.

Leave blank to skip: rows you cannot locate on a page, and rows from the two
sources whose PDFs are missing (below). Blank rows are excluded from the
result rather than counted as correct.

## Procedure

### 1. Draw the sample

```bash
python scripts/evaluate_sample.py draw -n 400 -o dist/eval_sample.csv
```

Stratified random sample across all 15 sources, proportional to source size
with a floor of 10 per source so small sources are still covered. The seed is
fixed, so the same command always yields the same rows — say so when you report
the result, and do not redraw after seeing the outcome.

Sample size against the precision it buys, for an error rate near 10%:

| n | 95% interval half-width |
|---:|---|
| 150 (the floor: 10 × 15 sources) | ±5% |
| 400 | ±3% |
| 1,000 | ±2% |

400 is the recommended starting point — roughly two evenings of checking, and
enough to distinguish "a few percent" from "a fifth of the dataset", which is
the distinction anyone reading the number actually cares about. Per-source rates
at that size are indicative only; their intervals will be wide, and the script
prints them so you can see that.

### 2. Check each row against its page

Open the CSV; each row carries its `source`, `author` and `year`, which identify
the PDF in `source_pdfs/`. Find the term on the page and fill `khmer_ok` and
`english_ok` with `y` or `n`. Use `notes` for anything worth keeping — a
recurring confusion between two characters is more useful than the rate itself,
because it can be fixed in the pipeline.

Work through the file in order rather than skipping around: consecutive rows
often come from the same source, so you page through one PDF at a time.

### 3. Score it

```bash
python scripts/evaluate_sample.py score dist/eval_sample.csv
```

Reports per-source and overall error rates with Wilson 95% confidence intervals.
The overall figure weights each source by its true size, so the per-source floor
does not let a 121-entry source distort a 5,934-entry estimate. The `covering`
figure states how many entries the estimate actually speaks for.

## Reporting it

Put the headline number in `README.md` and `DATA_STATEMENT.md` §7, replacing the
"unevaluated" notice. Report it as an interval, with the sample size and the
seed — `khmer` headword error rate 4.2% [2.6–6.7%], n=400, seed 20260907 — not
as a bare percentage. State that it was single-annotator if it was.

An honest wide interval is worth more than a precise-looking number: it is the
difference between a dataset a reviewer can reason about and one they have to
take on trust.

## What the first run learned about the method

- **Locate by the whole gloss line.** Matching a gloss as a substring, or even as
  whole words, sent annotators to the wrong entry: "architecture" sat inside the
  wrapped gloss of "landscape architecture". `relocate` recomputes pages for
  unjudged rows without touching recorded verdicts.
- **Crop, don't read whole pages.** Most errors are one dropped vowel or
  subscript. A 300 dpi crop of the headword cell shows them; a full-page render
  often does not. Zoom to 600–700 dpi before recording any doubtful mark.
- **Some pages are indexes.** The country-names volume repeats its English names
  in a French/English index with no Khmer column; a gloss found there is a
  locator miss, not a verdict.
- **Visible is not encoded.** ឫ typed as ប + coeng ញ looks identical on screen and
  on the page. Where a headword looks right but will not match a search, check its
  code points.

## Limits worth stating alongside the result

**Confirm you are checking the right file.** Run
`python scripts/verify_sources.py` first. It hashes every PDF in `source_pdfs/`
against `sources.json` and fails if any file is not the one the pipeline read —
a re-downloaded or re-scanned PDF can differ from the original while looking
identical, which would make your error rate a measurement of the wrong document.

**Some errors cannot be settled by looking.** Khmer has subscript pairs that
most fonts render identically — ្ត and ្ដ above all, which appears in 677
entries, 11.4% of the corpus. In the source PDFs at 700 dpi the two are the
same shape, and the text layer is no help: it encodes the whole cluster as one
mis-mapped glyph. An entry differing only in that subscript is therefore not
checkable by eye, and a `y` on such a row means "no visible difference", not
"correct". Leave those blank and note them; they need the printed book, a
native reader who knows the intended spelling, or a comparison against the
Royal Academy dictionary — which is what `check_against_rac.py` is for.

**One annotator is a known weakness.** A second person checking the same rows
blind, with agreement reported, is meaningfully stronger. If that is not
possible, say so plainly rather than leaving it implied.

**The sample says nothing about coverage.** It measures whether the entries that
are present are right. Terms the OCR dropped entirely never appear in the
dataset and so can never be sampled. Measuring that needs the opposite exercise:
take a page, count its terms, and check how many reached the JSON.
