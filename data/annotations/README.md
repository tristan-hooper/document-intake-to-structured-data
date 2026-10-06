# Reference answers and scoring rules

This folder contains the text used to score OCR results. Codex helped transcribe the reference answers from page images. The same annotator then checked them in a second visual pass. A second pass by one person is not independent review or agreement between two annotators. The saved source coordinates let another reviewer check where each answer came from.

## Which files the OCR tools can use

- `targets.json` gives each OCR pipeline the page area, label, time period, and unit to read.
- `references.json` contains the answers used by the scorer. OCR adapters must not read this file.
- `tools/author_annotations.py` writes the saved annotation files. It is a serializer; it does not perform the visual check.

The target details are supplied in this benchmark, so the scores measure reading values and text in known places. They do not measure whether a system can recover missing context or discover unknown fields in a report.

## Counts and meanings

There are 16 text regions and 64 targets. The evaluation set has 48 targets: 46 numeric values and two cells marked unavailable. The development set has 16 targets: 15 numeric values and one unavailable cell.

These cases are different:

- **Missing:** OCR did not provide usable text.
- **Unavailable:** the report marks that no value was reported.
- **Zero:** the report gives the numeric value `0`.

The three selected cells use dot leaders, printed rows of dots, to show that no value was reported. The tool does not treat those marks as zero. It does not score the exact number of dots as a value.

For narrative measurements, I excluded dates, page references, footnote numbers, and paragraph numbering. I kept ages, counts, and calculation factors. Two pages did not have enough measurements in the first column, so I continued in the second. Some selected paragraphs and table-label passages are shorter than 80 words; the scores use their actual lengths.

## Text matching rules

For ordinary text, both the reference and OCR output use Unicode NFC, a standard way to represent equivalent text, and repeated spaces are reduced to one. Case, punctuation, quotation marks, and printed line-end hyphens remain. A line-end hyphen followed by a line break is changed to a hyphen and a space; words are not joined by removing the hyphen.

Three table-label regions use a separate rule called `table_labels_v1`. It keeps only English ASCII letters and spaces, then reduces repeated spaces. It removes punctuation, numbers, and symbols from both the answer and OCR text. Letter case still matters. These scores are reported separately; they do not measure punctuation-preserving transcription.

## Matching text to a page area

The scorer uses the center of an OCR word or line to decide whether it falls inside a supplied area. A Docling table cell is treated as one unit: the cell whose center falls in the target is assigned to it. A neighboring cell that touches the target edge does not make the selected cell ambiguous. If a larger OCR line or text block crosses an area boundary, placement remains unresolved because the unit may contain more than one value. The scorer does not crop text using the answer key.

A **value/marker match** means the returned value or unavailable marker matches the reference. A **strict field match** also requires resolved placement in the supplied target. The strict measure therefore combines reading and location. It is not a pure OCR score, and the test does not measure whether a system can discover row labels, column labels, units, or unknown fields.

## Frozen record

The `status` fields in the frozen JSON files show the earlier authoring checkpoint. They are kept as part of the historical record. The current comparison inputs and checks are recorded in `data/evaluation-freeze-cell-aware.json`, and its outputs are in `results/final/`. The earlier `data/evaluation-freeze.json` and study snapshot remain separate records. The authoring tool refuses to overwrite the frozen annotations; any annotation change needs a revision record and consistent scoring.
