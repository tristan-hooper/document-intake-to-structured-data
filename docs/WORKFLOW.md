# How the prototype works

## The problem it explores

In this fictional example, an analyst receives public reports and must copy selected values into a structured file. Today, the analyst finds each value, records its source and context, and checks the transcription. This prototype tests whether OCR (optical character recognition, software that reads text from an image) can help with the reading step. It does not test whether a person can be removed from the review process or whether the work becomes faster overall.

The reports are real, scanned U.S. Census publications. They were chosen to include different print quality and page layouts. The task is guided: the target regions and labels are supplied to each pipeline. The prototype does not search a whole report to discover which facts matter.

## Processing flow

1. Read the approved source manifest and target list.
2. Check each PDF's SHA-256 file hash (a digital fingerprint) and page count, then turn the selected page into an image.
3. Send the page image to the selected OCR pipeline.
4. Match recognized words or lines to each supplied target region by box center. For Docling table output, assign the cell whose center falls in the target.
5. Check numeric candidates and record their text, source page, region, and review reason.
6. Save each completed page in a small SQLite database, then write the CSV (plain-text table) and JSON outputs.
7. A person reviews every candidate against the source page. This review happens outside the prototype.

The comparison uses four pipelines: Tesseract, RapidOCR, Docling with RapidOCR, and text already embedded in the PDF. The first three receive the same rendered page images. The Docling comparison also changes page handling and layout analysis, so it does not isolate the OCR engine alone.

The value/marker count measures exact output matches without requiring resolved placement. A strict field match also requires placement in the supplied target. A table cell is one unit, so a neighboring cell that touches a tight target edge does not make the selected cell ambiguous. If a larger OCR line or text block crosses the target, placement stays unresolved because it may include text from more than one value. These scores combine reading and target placement; they are not a pure OCR comparison. Row, column, period, and unit context were supplied, so the test does not measure whether a pipeline could discover those labels or rebuild a full table.

## Inputs, outputs, and evidence

The source manifest identifies the PDFs by file hash and records their page counts. The runtime target list gives the page, region, requested label, period, and unit for each value. These details help the pipeline find the requested text. The answer key is used only by the scorer; OCR pipelines must not read it.

Each output row represents one target on one page. It records the source and page, supplied context, recognized text, any normalized value, available confidence information, region alignment, and why the row needs review. The requested region is provided in advance; it is not a field discovered by the system. The prototype keeps any actual word or line positions in its page-level output.

Every candidate is marked for human review, even when it matches the reference answer. A candidate is not an approved fact. The records keep three cases separate: no OCR candidate, a printed value that is unavailable, and a numeric value of zero. A dot leader in the source means no value; it does not mean zero.

## Errors and restart behavior

Before processing, the prototype checks the source file's SHA-256 hash and page count. It records an error when a PDF cannot be read or turned into an image, or when a required OCR engine or model is missing. A failed page remains available for review and retry.

Each page is committed to SQLite as a unit. The cache reuses only completed pages and keys them by source bytes, page, rendering settings, target configuration, OCR settings, model, and repetition. Renaming a source file does not make its contents a new source.

Exports are written to a staging folder first. Once all required files are complete, the prototype moves them into place and updates the `current.json` pointer. If export fails, already committed page records remain intact and the pointer does not advance to a partial export. On Windows, the worker tracks its launched process so a timeout can stop that work rather than leave it running in the background.

The 120-second response limit applies to each OCR call. A benchmark page has one initial call and three warmed repeats, each with its own limit. Initialization has a separate limit. Rendering, storage, and export are outside the OCR-call limit.

The benchmark configuration records this experiment's settings. Engine settings and the geometry margin are fixed in the adapters and extraction code; editing their entries in the configuration file alone does not change those settings.

## Limits and next evidence

The evaluation has 12 pages from four reports, with four other pages used for development. Pages from the same report are related, so the 12 pages are not 12 independent reports. Scan quality and layout also vary together. The regions and labels are supplied, which makes this a guided-reading test rather than a test of open-ended document understanding.

The reference text was prepared with Codex assistance and checked in a second pass by the same annotator. There was no independent human adjudication. The study measures exact matches on selected targets and warmed processing time; it does not measure staff time saved, return on investment, or suitability for confidential or patient records.

Before making a stronger accuracy claim, the references need an independent review and the pipelines need testing on more report families and pages. A production system would also need a defined human review process, audit and retention rules, and a clear way to handle changes in source reports, models, and software. This prototype does not approve values automatically.
