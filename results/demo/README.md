# Selected-pipeline demonstration

This is a separate workflow demo of the selected RapidOCR pipeline. It uses the four development pages, not the evaluation pages, so it does not add to the accuracy results.

```powershell
.venv/Scripts/python.exe -m scan_intake.cli extract --pipeline B --split development --fresh --cold-render --repetitions 0
```

The completed run processed S2 page 2, S3 pages 6 and 11, and S4 page 6. It wrote 16 candidate rows and 16 review rows. Every candidate still needed human review. The run did not compare results with the answer references.

The recorded workload took 52.34 seconds. That time includes checking the source and model files, starting the OCR adapter, rendering pages, recognizing text, and saving page results. It excludes the final export step. The model files and software packages were already on the computer, so the time does not include their first download or setup.

The run folder [`B-development-isolated-20261006T153036Z-B-7513530a`](B-development-isolated-20261006T153036Z-B-7513530a/) contains the run record, page outputs, and CSV files. `demo-record.json` records the command and checksums. The copied output files were checked against the saved SHA-256 checksums. The original PDFs and model files remain local and are not in Git.
