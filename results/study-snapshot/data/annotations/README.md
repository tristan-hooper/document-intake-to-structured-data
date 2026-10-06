# Reference annotations

The references were transcribed by Codex from rendered source images before any OCR evaluation and checked in a second visual pass by the same annotator. This is not independent human adjudication or inter-annotator agreement. The repository retains the authoring source and source-page coordinates so a reviewer can audit them.

`targets.json` contains runtime regions and supplied labels, periods and units. `references.json` and `tools/author_annotations.py` contain scorer-only answers. Adapters must not read either. All context is supplied in this first benchmark, so only values and text are scored as extraction; no recovered-context accuracy is claimed.

There are 16 text regions and 64 field targets: 48 evaluation targets (46 numeric, two unavailable) and 16 development targets (15 numeric, one unavailable). Empty OCR output is missing evidence, not an unavailable value. Dot leaders in the three selected cells mean no value was reported; the prototype does not infer zero. Their exact dot count is structural, not a numeric transcription.

Selection exceptions are recorded per page. No-table measurements exclude publication/observation dates, page references, footnote indices and paragraph enumeration; ages, counts and calculation factors remain measurements. Two narrative pages have too few first-column measurements, so selection continues in the second column. Several complete paragraphs and table-label passages are shorter than 80 words; actual denominators are retained.

## Text normalization fixed before OCR evaluation

Default: Unicode NFC and collapsed whitespace only. Retain case, punctuation, quotes and printed line-end hyphens. A hyphen followed by a line break becomes a hyphen followed by a space; no dehyphenation is performed.

Three table-label regions use `table_labels_v1`: after NFC, retain only ASCII letters and whitespace, then collapse whitespace. These regions contain labels only; this explicitly excludes dot leaders, footnote symbols/numbers and label punctuation from both reference and prediction. Case remains significant. Report their results separately from the default-policy passages; do not describe their CER as punctuation-preserving transcription accuracy.

Geometry selection uses recognized-unit centers. An overlapping line/block extending across a region boundary without finer geometry is unresolved alignment, not a license to crop recognized strings based on expected answers. This limitation may reduce field coverage for pipelines that return coarse units.

Freeze configuration and scoring artifacts after development-only feasibility. Changes made after evaluation starts require a revision record and consistent rescoring; the original evaluation must not be portrayed as untouched.
