# Project One closeout

Closed locally on October 6, 2026. The V1 prototype and exploratory comparison are complete. The project has not been published or deployed.

## Purpose and delivered scope

The project tests ways to read known values from real scanned reports and send them to a person for review. It includes a local command-line tool, saved page results, candidate and review CSV files, and a comparison of Tesseract, RapidOCR, and Docling with RapidOCR. Text stored inside the PDFs is a separate baseline.

The dataset contains four public Census PDFs, with 12 evaluation pages and four development pages. The tools receive target areas and labels. They do not have to discover unknown fields or rebuild every table.

## Decision and evidence

RapidOCR is the selected table-focused demo. It passed the strict value-and-placement rule for 25 of 40 table targets, compared with 19 for Docling and seven for Tesseract. Tesseract was faster and passed seven of eight narrative targets. These results support a choice for this demo, not a general ranking.

All four pipelines completed the evaluation pages. Saved extraction and scoring results were recomputed and agreed with the reported scores. The three OCR pipelines received identical rendered images. Source and annotation checks passed, all 74 model/runtime files matched their recorded hashes, and 36 tests passed. Every extracted value remains marked for human review.

The [comparison](../results/final/comparison.csv), [case study](CASE_STUDY.md), [decision record](DECISION.md), and [development demo](../results/demo/README.md) contain the results and supporting detail. The [README](../README.md) provides setup and reproduction commands.

## Limits and future work

This is an exploratory study of selected pages. The references were checked twice by the same Codex-assisted annotator, with no independent human adjudication. The study does not estimate accuracy on unseen reports, measure complete table reconstruction, or demonstrate staff-time savings or safe automatic approval.

Before public release, verify the project from a clean checkout, finish source/software/model reuse and notice checks, choose a project license, and add public repository metadata and links. Before making stronger accuracy claims, have an independent person check the references and evaluate more report families.

Future benchmark executions must create a new freeze and use a new output folder, as described in the README. Existing benchmark records are retained unchanged.
