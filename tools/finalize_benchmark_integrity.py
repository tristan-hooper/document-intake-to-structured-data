"""Add score-output hashes to a completed benchmark index without rerunning OCR."""
import hashlib
import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scan_intake.contracts import ContractError, read_json

PIPELINES = ("A", "B", "C", "N")
RUN_ARTIFACTS = ("run.json", "pages.json", "candidates.csv", "review.csv")
SCORE_ARTIFACTS = ("evaluation.json", "scoring.log")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add_score_hashes(results):
    index_path = Path(results) / "benchmark-index.json"
    index = read_json(index_path)
    if index.get("status") != "completed" or set(index.get("pipelines", {})) != set(PIPELINES):
        raise ContractError("Only a fully completed A/B/C/N benchmark can be finalized")

    for pipeline in PIPELINES:
        entry = index["pipelines"][pipeline]
        if (entry.get("status") != "completed" or entry.get("exit_code") != 0
                or entry.get("scoring_exit_code") != 0):
            raise ContractError(f"Pipeline {pipeline} did not complete extraction and scoring")
        folder = Path(results) / pipeline
        run = read_json(folder / "run.json")
        evaluation = read_json(folder / "evaluation.json")
        score_log = read_json(folder / "scoring.log")
        if run.get("run_id") != entry.get("run_id") or run.get("pipeline") != pipeline:
            raise ContractError(f"Pipeline {pipeline} run metadata does not match the index")
        if evaluation.get("pipeline") != pipeline or evaluation.get("split") != "evaluation":
            raise ContractError(f"Pipeline {pipeline} scoring metadata is unexpected")
        if score_log != evaluation.get("overall"):
            raise ContractError(f"Pipeline {pipeline} scoring log disagrees with evaluation output")

        hashes = entry.get("artifact_sha256", {})
        for name in RUN_ARTIFACTS:
            path = folder / name
            if not path.is_file() or sha256(path) != hashes.get(name):
                raise ContractError(f"Pipeline artifact hash mismatch: {pipeline}/{name}")
            if name != "run.json" and run.get("artifact_sha256", {}).get(name) != hashes[name]:
                raise ContractError(f"Run manifest hash mismatch: {pipeline}/{name}")
        for name in SCORE_ARTIFACTS:
            if not (folder / name).is_file():
                raise ContractError(f"Missing score artifact: {pipeline}/{name}")
            digest = sha256(folder / name)
            old = hashes.get(name)
            if old is not None and old != digest:
                raise ContractError(f"Existing score hash disagrees: {pipeline}/{name}")
            hashes[name] = digest
        entry["artifact_sha256"] = hashes

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=index_path.parent,
                                     prefix="benchmark-index-", suffix=".tmp",
                                     delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(index, handle, indent=2)
        handle.write("\n")
    temporary.replace(index_path)
    return index


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir',type=Path,default=Path('results'))
    args=parser.parse_args()
    results=args.results_dir if args.results_dir.is_absolute() else ROOT/args.results_dir
    index = add_score_hashes(results)
    print(f"Added evaluation and score-log hashes for {len(index['pipelines'])} pipelines")


if __name__ == "__main__":
    main()
