# Project One interview notes

These drafts use the results recorded in this project. Keep the limits beside the numbers: this was a small, guided test, and every result still needs human review.

## One-sentence summary

I built a small document-reading prototype with Codex's help, tested three OCR (optical character recognition) options on real scanned Census reports, and chose the one that found the most table targets in this sample.

## Resume bullets

- Built a Python tool that checks approved PDF files, records page-level evidence, saves work so it can resume, and exports each candidate with a reason for human review.
- Compared Tesseract, RapidOCR, and Docling with RapidOCR on 12 pages from four public reports. RapidOCR had 31 strict value-and-placement matches out of 48 targets, including 25 of 40 table targets. Tesseract was fastest at 3.23 seconds per warmed page; RapidOCR took 4.92 seconds.

## About 30 seconds

I built a small tool for a common document task: moving selected statistics from scanned reports into a traceable spreadsheet. The office in my example is fictional, but I used real public Census reports. I compared three ways to read them and chose RapidOCR for the table-focused demo because it had the most strict value-and-location matches in this sample. The tool keeps the source page with each result and sends every result to a person for review. I did not measure staff time or test production accuracy.

## About 60 seconds

Imagine an analyst copying numbers from an old report. The right value depends on the row, column, time period, and unit. I built a prototype to test whether optical character recognition, or OCR, can help with this reading step.

I tested four public Census PDFs. I chose the pages before running the OCR tools and supplied the areas and labels to read. This was a guided reading test, not a test of finding unknown facts in a whole report. RapidOCR passed the strict value-and-placement rule for 31 of 48 targets, including 25 of 40 table targets, so I chose it for the table-focused demo. Docling passed 19 of 40 table targets, and Tesseract passed seven. Tesseract was faster and did slightly better on the eight narrative targets. All results still need human review.

## About two minutes

The problem is simple: an analyst copies a fact from a report into a spreadsheet, but a missed sign or a value from the wrong column can make the record unreliable. In my fictional example, the analyst also needs to keep the source page and context with each value.

I kept the first version small. It checks approved PDF files, reads selected pages, saves page results in a small SQLite database, and exports candidate values to CSV files that open in spreadsheet software. It does not try to handle every kind of document or make the final decision. Each candidate stays in a human-review queue.

To choose an OCR path, I compared Tesseract, RapidOCR, and Docling with RapidOCR on 12 pages from four real public Census reports. A value match required the right number or unavailable marker. A strict match also required resolved placement in the target area. RapidOCR passed the strict rule for 31 of 48 targets, including 25 of 40 table targets. Docling matched 23 values or markers, and 19 passed the placement rule. Tesseract passed the strict rule for 14 of 48 overall, ran fastest, and matched seven of eight narrative targets; RapidOCR matched six. The cell-level rule matters: Docling table cells are assigned by their center, while a line or block that crosses a target remains unresolved.

I chose RapidOCR for this table-focused demo. The results apply only to this small set of guided pages. Pages from the same report are related, print quality changes along with layout, and the reference answers were checked twice by the same person. I did not measure staff-time savings or test automatic approval.

## About five minutes

Optical character recognition (OCR) is software that reads text from an image. I tested it on four public Census PDFs: 12 pages for evaluation and four different pages for development. I chose the pages before the test. The scans vary in print and layout, but I did not add artificial blur or divide the pages into balanced quality groups. Two PDFs have no useful text on the selected pages; two contain older OCR text. I treated that existing text as a separate baseline, not as the answer key.

I rendered each evaluation page as the same 300-DPI color image for the three OCR pipelines. Tesseract read the image directly. RapidOCR read the same image with ONNX Runtime on the CPU. Docling used the same RapidOCR recognition models, with OCR and table-structure extraction enabled, and also changed image size and analyzed page layout. This is three pipelines using two recognition engines, not a three-model leaderboard. The RapidOCR/Docling comparison does not isolate layout analysis by itself.

I supplied the page areas and labels to each pipeline. The tool matched recognized words or lines to those areas by the center of each box. For Docling's table output, it assigned the cell whose center fell inside the target. A neighboring cell may touch the target edge without making the selected cell ambiguous. Larger OCR lines or blocks that cross a target remain unresolved. The test had 48 targets: 46 numbers and two cells marked unavailable. Forty targets were in tables and eight were in narrative text. RapidOCR passed the strict rule for 31 targets, Docling for 19, Tesseract for 14, and text already in the PDFs for five. Docling matched 23 references by value or marker, and 19 also passed the placement rule. Tesseract matched seven of the eight narrative targets, compared with six for RapidOCR; Docling matched none of the eight.

The median warmed time per page was 3.23 seconds for Tesseract, 4.92 for RapidOCR, and 11.80 for Docling. These timings came from one Windows computer, after startup and page rendering. They are not end-to-end service times. I chose RapidOCR for the table-heavy demo because it had the strongest strict score on the table targets. This test reads selected values in known regions; it does not measure full table reconstruction or performance on new report types.

The references cover 16 text regions and 64 targets: 48 evaluation targets and 16 development targets. The 48 evaluation targets include 46 numeric values and two cells marked unavailable. The OCR pipelines missed those two unavailable targets; the PDF-text baseline returned them. An empty OCR result is not the same as a printed unavailable value, and neither means zero.

Codex helped transcribe the references, and the same annotator checked them in a second visual pass. There was no independent review of the answers. The 12 pages come from four reports, so they are not 12 independent reports. The page areas and labels were supplied, which makes this a guided test. All candidates stayed in the review queue, so I did not measure an automatic-approval error rate. I also did not measure staff time, savings, return on investment, or suitability for patient records.

All 48 candidates stayed in the human-review queue. The references were checked twice by the same annotator, with Codex assistance; no independent person checked them. Before real use, I would have another person review the references, test more report types, define the review process, and measure the time for both entry and review. The current automated test suite passes 36 tests.
