# Benchmark results

Use the files in `results/final/` for the current comparison. The main summary is `comparison.csv`; `comparison.json` explains how the pipelines were grouped and confirms that A, B, and C received the same rendered page images. The `A/`, `B/`, `C/`, and `N/` folders contain the run records, extracted candidates, review rows, and scores for each option. `benchmark-index.json` records the evaluation-freeze hash, completion, and file hashes.

The scoring inputs and test checks are recorded in `data/evaluation-freeze-cell-aware.json`. The root-level result files, older verification notes, and `results/study-snapshot/` are retained as separate historical records. When quoting this project, use the comparison in `results/final/`.

All extracted fields remain marked for human review. A strict match is not an approved value.
