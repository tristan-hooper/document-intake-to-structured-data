# Scanned Public Reports to Structured Data

## Project purpose

This project asks a practical question: **When does adding OCR (optical character recognition, software that reads text from an image) or table-reading tools help enough to justify the extra time and complexity?**

The example is hypothetical: a public research office copies statistics from old reports into a spreadsheet. A wrong digit, sign, or table column could make a value unreliable. I built a local prototype with Codex assistance, then tested three ways to read real scanned reports. Every result still goes to a person for review.

I used real U.S. Census reports instead of making artificial scans. Their pages vary in print quality and layout. That makes the test more realistic, though it also means I cannot tell whether an error came from the scan, the page layout, or both.

## What I compared

I selected 12 pages for testing and four separate pages for development. The test pages come from four full reports, so they are not 12 independent sources. I fixed the page list before testing OCR.

Each OCR system received the same 300-DPI color image of a page. The systems did not receive the answer key. I also measured text already stored inside the original PDFs as a separate baseline.

| Option | What it does | Value/marker matches | Strict field matches | Strict table matches | Strict narrative matches | Warmed page time* |
|---|---|---:|---:|---:|---:|---:|
| A — Tesseract | Reads text from the page image | 14/48 | 14/48 | 7/40 | 7/8 | 3.23 s |
| B — RapidOCR | Uses a different OCR engine on the same image | 31/48 | 31/48 | 25/40 | 6/8 | 4.92 s |
| C — Docling + RapidOCR | Adds page and table layout analysis | 23/48 | 19/48 | 19/40 | 0/8 | 11.80 s |
| N — PDF text | Reads text already stored in the PDF | 5/48 | 5/48 | 3/40 | 2/8 | — |

The value/marker count asks whether the returned value matches the reference. The strict count also requires the result to be placed in the requested area. It therefore measures both reading and placement, not OCR alone. The test includes 48 targets: 46 numbers and two cells marked unavailable. Forty targets are in tables and eight are in narrative text. For each page, I took the median of three warmed repeats, then the median across pages. These times exclude startup and page rendering.

For ordinary words, the pipeline assigns a recognized unit to a target when the unit's box center falls inside it. Docling's reconstructed table cells are treated as whole cells: the cell whose center falls in the target is selected. A neighboring cell box may touch the target's edge without making the selected cell ambiguous. If a larger OCR line or text block crosses the target, its placement stays unresolved because it may contain text from more than one value.

Docling matched 23 reference values or markers; 19 also passed the placement rule. Tesseract passed for 14 targets. This sample therefore shows more strict matches for Docling than Tesseract, including 19/40 versus 7/40 on table targets. RapidOCR had the most strict table matches at 25/40. Tesseract was fastest and did slightly better on the eight narrative targets. B and C use the same RapidOCR recognition models, but Docling also changes image size and analyzes page and table layout. The task supplied target areas and labels; it did not test finding every row and rebuilding every table in a report.

I chose B for the table-focused demo, not as a general winner. **All 48 targets still require review.** I did not test automatic approval, staff-time savings, return on investment, or use with patient records.

## What I built

The local command-line tool checks each PDF's SHA-256 file hash (a digital fingerprint), processes only selected pages, stores page results in a small SQLite database, and exports candidate values to CSV files that open in spreadsheet software. It keeps the source page, selected area, raw OCR text, and review reason with each value.

The tool keeps three cases separate: OCR found no value, the report shows that no value was reported, and the value is zero. It does not guess missing digits or automatically approve a result. See the [workflow notes](docs/WORKFLOW.md) for more detail.

## Try the selected demo on Windows

I tested this setup on Windows with Python 3.12 and the pinned RapidOCR package list. I have not tested other operating systems.

```powershell
uv --cache-dir .cache/uv venv --python 3.12 .venv
uv --cache-dir .cache/uv pip install --python .venv/Scripts/python.exe -r requirements-rapidocr.lock
uv --cache-dir .cache/uv pip install --python .venv/Scripts/python.exe --no-deps -e .
.venv/Scripts/python.exe tools/fetch_sources.py
.venv/Scripts/python.exe tools/fetch_models.py --pipeline B
.venv/Scripts/python.exe -m scan_intake.cli verify-sources
.venv/Scripts/python.exe -m scan_intake.cli extract --pipeline B --split development --fresh --cold-render --repetitions 0
```

The last command runs the four development pages. It exported 16 candidate rows, all marked for review. It did not score answers, so it is a demonstration, not another accuracy test. The saved [demo record](results/demo/README.md) has more detail.

To run the tests:

```powershell
uv --cache-dir .cache/uv pip install --python .venv/Scripts/python.exe -e ".[test]"
New-Item -ItemType Directory -Force .cache | Out-Null
.venv/Scripts/python.exe -m pytest -q --basetemp .cache/pytest
```

The current test suite passed 36 tests. The [versioned evaluation record](data/evaluation-freeze-cell-aware.json) includes source checks, annotation checks, and the test result.

## Reproduce the full comparison

The full test needs all three OCR setups and their model files. Install the full benchmark package list and fetch the pinned PDFs and models first:

```powershell
uv --cache-dir .cache/uv pip install --python .venv/Scripts/python.exe -r requirements-benchmark.lock
uv --cache-dir .cache/uv pip install --python .venv/Scripts/python.exe --no-deps -e .
.venv/Scripts/python.exe tools/fetch_sources.py
.venv/Scripts/python.exe tools/fetch_models.py --pipeline all
```

On a clean Windows setup, fetching the pinned Tesseract files may also require 7-Zip. For each comparison, create a new freeze file and use a new, empty output folder so existing results are not replaced. The filename below is an example; choose an unused suffix for later runs.

```powershell
.venv/Scripts/python.exe tools/freeze_evaluation.py --output data/evaluation-freeze-reproduction-20261006.json
.venv/Scripts/python.exe tools/run_benchmark.py --freeze-file data/evaluation-freeze-reproduction-20261006.json --results-dir results/reproduction-20261006
.venv/Scripts/python.exe tools/finalize_benchmark_integrity.py --results-dir results/reproduction-20261006
.venv/Scripts/python.exe tools/summarize_benchmark.py --results-dir results/reproduction-20261006
```

The second command runs Tesseract, RapidOCR, Docling with RapidOCR, and the PDF-text baseline on the 12 evaluation pages. The last two commands check the run files and write the comparison summary.

## Limits and release status

I supplied the page areas, row and column names, time periods, and units. The test measures reading known areas; it does not find fields in an unknown report. Codex helped transcribe the reference answers, and the same annotator checked them a second time. No independent person checked the answers. This limits how strongly I can claim that the scores represent true accuracy.

The sample is small, and scan quality varies along with page layout. The results do not show how well the tool would work on new reports. They also do not show staff-time savings or prove that automatic approval would be safe.

This is an exploratory comparison on selected pages. It is not an untouched holdout test that can estimate performance on new documents.

The local V1 is complete: the prototype, comparison, selected demo, and case study are finished. The current [comparison](results/final/comparison.csv), run records, and page-level scores are in `results/final/`. The source release is prepared locally; GitHub publication is pending. A clean Windows Git checkout, with a new Python environment, downloaded the pinned PDFs and RapidOCR models, completed the four-page demo, and passed all 36 tests. Package installation used a local download cache. The full three-pipeline benchmark has not been repeated from this clean checkout.

Original project code and documentation use the [MIT license](LICENSE). The [third-party notices](THIRD_PARTY_NOTICES.md) and [dependency inventory](docs/DEPENDENCY_LICENSES.csv) explain the separate terms for sources, software, models, and fonts. I keep original PDFs, model files, runtime binaries, execution logs, and internal audit notes out of Git. See the [closeout record](docs/CLOSEOUT.md) for delivered scope and the [release record](docs/RELEASE.md) for publication checks.

## More detail

[Case study](docs/CASE_STUDY.md) · [Decision record](docs/DECISION.md) · [Dataset and sources](docs/DATASET.md) · [Interview notes](docs/INTERVIEW_NOTES.md) · [Results](results/final/comparison.csv)
