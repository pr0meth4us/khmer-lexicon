# Khmer Lexicon — dist

Generated output of the lexicon builder. Committed so the merged resource is
tracked and reproducible.

Rebuild and gate with:

```bash
python3 clean_and_arrange_official_lexicons.py   # merge + normalise + validate
```

## Artifacts

| file | what it is |
|---|---|
| `unified_lexicon.json` | the merged terminology resource |
| `unified_official_lexicon.json` | identical to the above today |
| `validation_report.md` | every defect found, per check, with examples |
| `quality_baseline.json` | the ratchet the build gate compares against |
| `near_duplicates.md` | spelling variants one grapheme cluster apart |

## Metrics

**5,929 entries** across 15 official sources.

Previously reported as 5,932. Canonical mark-order normalisation, applied at
build time, rewrote 23 entries; 3 of those normalised onto a form already
present and the existing dedup collapsed them.

### Khmer term shape, in grapheme clusters (UAX #29, not code points)

| | |
|---|---:|
| entries with a Khmer form | 5,908 |
| distinct Khmer forms | 5,777 |
| shortest term | 1 cluster |
| median | 5 clusters |
| mean | 6.7 clusters |
| longest term | 52 clusters |
| distinct grapheme clusters | 1,542 |
| clusters covering 95% of all occurrences | 637 |
| terms longer than 20 clusters | 143 |

The 52-cluster maximum is not a term: it is a slash-separated definition dumped
into the `khmer` field by the extractor. Length past the 95th percentile is a
usable signal for extraction failure, which is why the validator checks it.

### Known defects

These are the committed baseline in `quality_baseline.json`. The build fails if
any of them grows.

| check | count |
|---|---:|
| empty `khmer` | 24 |
| empty `english` | 1,657 |
| `khmer` field containing no Khmer characters | 21 |
| characters outside Khmer, Latin and punctuation (occurrences) | 13 |
| ASCII digits in `khmer` | 0 |
| not in canonical mark order | 0 |
| duplicate Khmer forms | 121 |
| duplicate English glosses (case-insensitive) | 285 |
| terms longer than 20 clusters | 143 |

Three of these are commonly misread and are worth stating precisely:

- **"26 entries with script contamination" overstates the problem.** 26 entries
  do carry Latin inside the `khmer` field, but 7 of those are `ខ្មែរ (English)`
  acronym style, which is correct house style. The real defect is a `khmer`
  field with *no Khmer at all*: **21 entries** — legacy Limon-font OCR read as
  Latin (`aquñşıyшn`, `Muññ`, mostly `rac-new-words` botanical entries) plus six
  French grammar terms (`Nominatif`, `Génitif`, …) filed into `khmer` when the
  schema has an empty `french` column.
- **"117 entries containing digits" is not a defect count.** All 117 use Khmer
  digits ០-៩ and are legitimate — `បដិវត្តឧស្សាហកម្មទី ៤` ("4th Industrial
  Revolution"). ASCII digits would be the defect; there are none.
- **Duplicate English glosses are 268 case-sensitive, 285 case-insensitive.**
  The validator uses the case-insensitive count.

### Near-duplicates

Beyond the 121 exact duplicates, **164 pairs** are one grapheme cluster apart
*and* share an English gloss. (7,140 pairs are one cluster apart on distance
alone; agreement on meaning is what separates a spelling variant from two
different words.) See `near_duplicates.md`. Nothing has been merged.

33 of the 164 are explained by empirically measured character confusions from
[seanghay/khmer-character-confusions](https://huggingface.co/datasets/seanghay/khmer-character-confusions)
(CC-BY-SA-4.0, aggregated from 3.2M khmerdict.com searches) — ក/គ alone is
confused 551× by real users and produces ម៉ាដាហ្កាស្ក / ម៉ាដាហ្គាស្ក
(Madagascar), រីហ្ក / រីហ្គ (Riga), ប៊ុលហ្ការី / ប៊ុលហ្គារី (Bulgaria).
18 of those 33 come from a single source, `nckl-country-and-city-names`, so this
is a systematic OCR failure on transliterated place names rather than noise.

## Sources

| tag | title | author | year | entries |
|---|---|---|---:|---:|
| `council-of-ministers-legal-terms` | សទ្ទានុក្រមពាក្យច្បាប់ ផ្នែករដ្ឋប្បវេណី និង នីតិវិធីរដ្ឋប្បវេណី | Council of Ministers | 2007 | 372 |
| `mptc-digital-lexicon` | សទ្ទានុក្រមបច្ចេកសព្ទឌីជីថល | Ministry of Post and Telecommunications (MPTC) | 2025 | 278 |
| `nckl-bulletin-vol3-2010` | ព្រឹត្តិបត្រក្រុមប្រឹក្សាជាតិភាសាខ្មែរ លេខ ៣ | National Council of Khmer Language (NCKL) | 2010 | 167 |
| `nckl-bulletin-vol4-2012` | ព្រឹត្តិបត្រក្រុមប្រឹក្សាជាតិភាសាខ្មែរ លេខ ៤ | National Council of Khmer Language (NCKL) | 2012 | 418 |
| `nckl-bulletin-vol5-2013` | ព្រឹត្តិបត្រក្រុមប្រឹក្សាជាតិភាសាខ្មែរ លេខ ៥ | National Council of Khmer Language (NCKL) | 2013 | 124 |
| `nckl-bulletin-vol7-2015` | ព្រឹត្តិបត្រក្រុមប្រឹក្សាជាតិភាសាខ្មែរ លេខ ៧ | National Council of Khmer Language (NCKL) | 2015 | 508 |
| `nckl-bulletin-vol8-2017` | ព្រឹត្តិបត្រក្រុមប្រឹក្សាជាតិភាសាខ្មែរ លេខ ៨ | National Council of Khmer Language (NCKL) | 2017 | 466 |
| `nckl-bulletin-vol9-2018` | ព្រឹត្តិបត្រក្រុមប្រឹក្សាជាតិភាសាខ្មែរ លេខ ៩ | National Council of Khmer Language (NCKL) | 2018 | 376 |
| `nckl-bulletin-vol10-2019` | ព្រឹត្តិបត្រក្រុមប្រឹក្សាជាតិភាសាខ្មែរ លេខ ១០ | National Council of Khmer Language (NCKL) | 2019 | 200 |
| `nckl-country-and-city-names` | សទ្ទានុក្រមនាមទ្វីប ប្រទេស រដ្ឋធានី ទីក្រុង និងរូបិយបណ្ណ | National Council of Khmer Language (NCKL) | 2013 | 510 |
| `nckl-economics` | សទ្ទានុក្រមសេដ្ឋកិច្ច | National Council of Khmer Language (NCKL) | 2019 | 215 |
| `nckl-political-science-and-diplomacy` | សទ្ទានុក្រមវិទ្យាសាស្ត្រនយោបាយ និងការទូត | National Council of Khmer Language (NCKL) | 2014 | 120 |
| `nckl-technology-and-science` | សទ្ទានុក្រមបច្ចេកវិទ្យា និងវិទ្យាសាស្ត្រ | National Council of Khmer Language (NCKL) | 2014 | 466 |
| `pentagonal-strategy-phase1` | យុទ្ធសាស្ត្របញ្ចកោណ ដំណាក់កាលទី១ | Royal Government of Cambodia | 2023 | 486 |
| `rac-new-words` | វចនានុក្រមពាក្យថ្មី | Royal Academy of Cambodia (National Language Institute) | 2018 | 1,223 |
