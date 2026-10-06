# OCR choice for the guided demo

## Decision

I chose RapidOCR with ONNX Runtime on CPU for the main demo. OCR means optical character recognition: software that reads text from an image. ONNX Runtime runs the recognition model on the computer's CPU. I chose RapidOCR because this task focuses on table values, and it passed the strict value-and-location rule for the most table targets in the test. I kept automatic approval off. A person must review every result.

This choice applies to one small test. It does not mean RapidOCR is the best OCR tool for every job.

## Evidence

I compared three OCR pipelines on the same page images. I also tested text already stored in the PDFs as a separate baseline. A value/marker match means the output matched the reference. A strict field match also requires resolved placement in the selected area, so it combines reading and location rather than measuring OCR alone.

| Pipeline | Value/marker matches | Strict field matches | Strict table matches | Strict narrative matches | Warmed time per page* |
|---|---:|---:|---:|---:|---:|
| A — Tesseract | 14/48 | 14/48 | 7/40 | 7/8 | 3.23 s |
| B — RapidOCR | 31/48 | 31/48 | 25/40 | 6/8 | 4.92 s |
| C — Docling + RapidOCR | 23/48 | 19/48 | 19/40 | 0/8 | 11.80 s |
| N — text stored in the PDF | 5/48 | 5/48 | 3/40 | 2/8 | — |

*For each page, the time is the median of three warmed repeats; the table reports the median across pages. It excludes startup and page rendering.

For Docling table output, the cell whose center falls in a target is assigned to it. A neighboring cell that touches the target edge does not make the selected cell ambiguous. Larger OCR lines or text blocks that cross a target stay unresolved. Docling matched 23 reference values or markers, and 19 passed the placement rule. Tesseract passed the strict rule for 14 targets; Docling passed it for 19. RapidOCR passed the strict rule for the most table targets, 25/40, followed by Docling at 19/40 and Tesseract at 7/40. Tesseract was faster and matched seven of the eight narrative targets, one more than RapidOCR. Docling matched none of the eight narrative targets.

I selected RapidOCR for this guided demo because it had the strongest strict result on table targets in this sample. This is a choice for this workflow, not a general ranking. The task supplied regions and labels; it did not test finding unknown facts or reconstructing complete tables. B and C use the same RapidOCR recognition models, while Docling adds image scaling and layout processing. A broader test should measure table structure and row/column assignment on more report families.

## Limits

The test covers 12 pages from four public Census reports. The pages are selected samples, not a broad or independent survey. I supplied the page areas and labels, so the systems did not have to find fields in unknown documents.

Codex helped transcribe the reference answers, and the same annotator checked them again. No independent person reviewed them. All 48 targets remained in the review queue. Since the tool approved none automatically, the test gives no automatic-approval score; it does not show that automatic approval would be error-free.

I measured no staff-time savings, return on investment, results on new report types, or fitness for patient records. See the [case study](CASE_STUDY.md) for the full method and limits, and the [comparison table](../results/final/comparison.csv) for the results.
