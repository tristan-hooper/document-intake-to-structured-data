# Scanned Public Reports to Structured Data

## The project in brief

I tested whether OCR (optical character recognition, software that reads text from an image) and page-layout tools could help a person move statistics from scanned reports into a spreadsheet. I built a local prototype with Codex assistance and compared three ways to read the same scanned pages.

The research office is a hypothetical example; no real agency asked for this work. The PDFs are real public reports from the U.S. Census Bureau. This lets me test a realistic document problem without using private records.

## The problem and question

Imagine an analyst copying a number from an old report. The analyst must choose the right row and column, keep the time period and unit, and enter the number correctly. A missed minus sign or a value from the wrong column can make the result unreliable.

My question was: **Does adding another OCR engine or table-layout analysis find more exact targets, and is any gain worth the extra time and setup?** I used real scanned pages because made-up blur or noise may not match problems found in actual reports.

This is a guided test. I chose the page areas and supplied each value's row, column, time period, and unit. The software did not have to find unknown fields in a whole document. The test measures how well it reads known areas.

## The documents and test method

I chose four real Census PDFs. The test set has 12 pages, and the development set has four different pages. The pages vary in print quality, font size, noise, and table layout. I did not add artificial blur or compression. Two PDFs have no useful text layer on the selected pages; two have older OCR text. I measured that older text as a separate baseline.

For each test page, I made one 300-DPI color image and gave the same image to all three OCR pipelines. This helps keep the page image the same across the comparison. Each pipeline ran once before three warmed repeats per page. I measured page-reading time after startup and rendering, and also recorded the full repeat-workload time.

I compared:

- **A — Tesseract 5.5.3:** English LSTM OCR with `--psm 3`, its full-page automatic segmentation mode.
- **B — RapidOCR 3.4.2:** the English PP-OCRv4 recognition model on the same image.
- **C — Docling 2.67.0 with RapidOCR:** the same RapidOCR weights as B, with full-page OCR, layout analysis, and table-structure extraction enabled. It uses `en`, the [documented PP-OCR English code](https://docling-project.github.io/docling/concepts/OCR/).
- **N — PDF text:** text already stored inside the original PDF; this is a baseline, not an OCR engine.

The three OCR pipelines use two recognition engines. B and C use the same RapidOCR recognition models. Docling also resizes the image and analyzes layout, so the test does not isolate layout analysis as the only difference between B and C.

Tesseract returned word positions, but it did not return a reconstructed table grid. RapidOCR returned recognized words with positions. Docling returned structured table cells, and its OCR and table-structure stages were enabled. For each table target, the cell whose center falls in the target area is assigned to that target. A neighboring cell may touch the target edge without making the selected cell ambiguous. If a larger OCR line or text block crosses a target, placement remains unresolved because the output may contain more than one value. The test did not ask any pipeline to find unknown fields or reconstruct every table in a report.

## Results and choice

The **value/marker matches** count outputs that match the reference without requiring resolved placement. A **strict field match** also needs placement in the target area. The strict score combines reading and location; it is not a pure OCR-accuracy score. For unavailable values, the returned marker must match the reference marker class.

| Pipeline | Value/marker matches | Strict field matches | Strict table matches | Strict narrative matches | Warmed time per page* |
|---|---:|---:|---:|---:|---:|
| A — Tesseract | 14/48 | 14/48 | 7/40 | 7/8 | 3.23 s |
| B — RapidOCR | 31/48 | 31/48 | 25/40 | 6/8 | 4.92 s |
| C — Docling + RapidOCR | 23/48 | 19/48 | 19/40 | 0/8 | 11.80 s |
| N — PDF text | 5/48 | 5/48 | 3/40 | 2/8 | — |

*For each page, the time is the median of three warmed repeats; the table reports the median across pages. It excludes startup and page rendering. The PDF-text time is not comparable to the OCR times.

On table targets, RapidOCR passed 25/40, Docling passed 19/40, and Tesseract passed 7/40. On the eight narrative targets, Tesseract passed 7/8, RapidOCR passed 6/8, and Docling passed 0/8. These small task groups support choices for this demo, not broad claims about all report types.

I chose RapidOCR for the table-focused demo because it passed the strict rule for the most table targets, 25 of 40. Tesseract was fastest and passed seven of the eight narrative targets; RapidOCR passed six. Eight narrative targets are too few for a general recommendation.

Docling matched 23 reference values or markers, and 19 also passed the placement rule. Tesseract matched 14, all with resolved placement. In an inspected example, Docling returned the expected 15.9 cell beside 19.6. The scorer assigns a table cell by its center, so the neighboring cell's small overlap with the target edge does not change which cell was selected. Under this rule, Docling passed more targets than Tesseract overall and on the table subset. This result covers selected values in known regions; it does not measure complete table reconstruction or performance on other reports.

This was a guided scalar-reading task: I supplied target areas and labels. It was not a test of finding and rebuilding all tables across whole reports. B and C share the same RapidOCR recognition models, while Docling also resizes the image and analyzes page layout. The results support choosing B for this table-focused demo, but they do not show that B is better in every task or that Docling reconstructs full tables more accurately. A broader test should score values, row and column assignment, and table structure across more reports.

I also compared full-text reading with two common measures. **Character error rate (CER)** divides character edits—inserts, deletions, and substitutions—by the number of characters in the reference. **Word error rate (WER)** does the same for words. On ordinary prose, Tesseract scored 0.31% CER and 1.64% WER; RapidOCR scored 2.48% and 5.94%; Docling scored 1.38% and 4.80%. Table labels use a different rule that removes punctuation, symbols, and numbers, so I report those scores separately. They should not be compared directly with ordinary-prose scores.

## What I built

I kept the first version small: a local Python command-line tool, an SQLite database for saved page results, and CSV files (plain-text tables) for review. It checks each PDF's file hash and page count, then processes only the pages in the source list. It saves the source page, selected area, OCR text, value, and reason for review.

The tool keeps three cases distinct: no text was found, the report marks a value as not reported, and the value is zero. It does not guess missing digits. Every value remains marked for human review.

The selected RapidOCR demo ran on the four development pages. It completed all four pages, wrote 16 candidate rows and 16 review rows, and approved no values. It took 52.34 seconds, not counting final file export. This was a workflow demonstration, not another accuracy test. The source PDFs and model files were already on the computer, so this did not measure a first-time download.

## Limits and next steps

The test includes 12 pages from four reports. The pages are not independent reports, and scan quality changes along with page layout. I cannot use this sample to say what caused each error or how the software would work on new report families.

This is an exploratory comparison on selected pages, not an untouched holdout test. The scores describe these pages under the stated rules; they do not estimate accuracy on new documents.

Codex helped transcribe the reference answers, and the same annotator checked them a second time. No independent person checked the answers. This is not two-person agreement. A person also needs to check the references before I make stronger accuracy claims.

All 48 targets stayed in the review queue. No value was automatically approved, so this test says nothing about the safety of automatic approval. I did not measure staff time, savings, return on investment, or use with patient records.

Before using a system like this at work, I would test more report types, have another person check the reference answers, design the real review process, and measure the time needed for both data entry and review.

The [current comparison](../results/final/comparison.csv) and its per-pipeline run files include scores and shared-image checks. A separate study snapshot is kept for audit history.

For the data sources and page choices, see the [dataset record](DATASET.md). For setup steps, see the [README](../README.md). The [decision record](DECISION.md) gives the short technology choice, and the [demo record](../results/demo/README.md) describes the separate development run.
