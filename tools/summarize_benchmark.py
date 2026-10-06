"""Build comparison artifacts only from complete, hash-verified runs."""
import csv
import argparse
import hashlib
import json
from pathlib import Path
import re
from statistics import median

from scan_intake.contracts import ContractError, load_contracts, read_json

ROOT = Path(__file__).resolve().parents[1]
PIPELINES = ("A", "B", "C", "N")
RUN_ARTIFACTS = {"run.json", "pages.json", "candidates.csv", "review.csv"}
INDEX_ARTIFACTS = RUN_ARTIFACTS | {"evaluation.json", "scoring.log"}
SHA256 = re.compile(r"[0-9a-f]{64}", re.ASCII)


def validate_benchmark_index(index):
    if index.get("status") != "completed":
        raise ContractError(f"Benchmark is not fully completed: {index.get('status')}")
    pipelines = index.get("pipelines", {})
    if set(pipelines) != set(PIPELINES):
        raise ContractError("Benchmark index must contain exactly A, B, C and N")
    if index.get("order") != list(PIPELINES) or not index.get("timing_protocol"):
        raise ContractError("Benchmark order or timing protocol is missing")
    for pipeline in PIPELINES:
        entry = pipelines[pipeline]
        if (entry.get("status") != "completed" or entry.get("exit_code") != 0
                or entry.get("scoring_exit_code") != 0
                or not isinstance(entry.get("run_id"), str) or not entry["run_id"]):
            raise ContractError(f"Pipeline {pipeline} did not complete extraction and scoring")
        hashes = entry.get("artifact_sha256")
        if not isinstance(hashes, dict) or set(hashes) != INDEX_ARTIFACTS:
            raise ContractError(f"Pipeline {pipeline} is missing required artifact hashes")
        if any(not isinstance(value, str) or SHA256.fullmatch(value) is None
               for value in hashes.values()):
            raise ContractError(f"Pipeline {pipeline} has an invalid artifact hash")


def verify_artifacts(folder, pipeline, entry):
    for name, expected_hash in entry["artifact_sha256"].items():
        path = folder / pipeline / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise ContractError(f"Pipeline artifact hash mismatch: {pipeline}/{name}")


def verify_pipeline(folder, pipeline, entry, expected_page_ids, expected_target_keys):
    verify_artifacts(folder, pipeline, entry)
    pipeline_folder = folder / pipeline
    metadata = read_json(pipeline_folder / "run.json")
    pages = read_json(pipeline_folder / "pages.json")
    metric = read_json(pipeline_folder / "evaluation.json")
    score_log = read_json(pipeline_folder / "scoring.log")
    expected_targets = len(expected_target_keys)

    if (metadata.get("run_id") != entry["run_id"] or metadata.get("pipeline") != pipeline
            or metadata.get("split") != "evaluation"):
        raise ContractError(f"Pipeline {pipeline} run metadata does not match the index")
    if (metadata.get("selected_pages") != len(expected_page_ids)
            or metadata.get("completed_pages") != len(expected_page_ids)):
        raise ContractError(f"Pipeline {pipeline} did not complete every selected page")
    if not isinstance(pages, list) or any(page.get("status") != "completed" for page in pages):
        raise ContractError(f"Pipeline {pipeline} contains a failed page")

    result_page_ids = [page.get("page_id") for page in pages]
    metric_pages = metric.get("pages", [])
    metric_page_ids = [page.get("page_id") for page in metric_pages]
    if (len(result_page_ids) != len(set(result_page_ids))
            or set(result_page_ids) != expected_page_ids
            or len(metric_page_ids) != len(set(metric_page_ids))
            or set(metric_page_ids) != expected_page_ids):
        raise ContractError(f"Pipeline {pipeline} page coverage does not match the frozen evaluation set")
    if any(page.get("status") != "completed" for page in metric_pages):
        raise ContractError(f"Pipeline {pipeline} evaluation contains an incomplete page")
    if metric.get("split") != "evaluation" or metric.get("pipeline") != pipeline:
        raise ContractError(f"Pipeline {pipeline} scoring metadata does not match the run")
    if metric["overall"].get("pages") != len(expected_page_ids):
        raise ContractError(f"Pipeline {pipeline} score denominator does not match page coverage")
    if metric["overall"].get("evaluable_targets") != expected_targets:
        raise ContractError(f"Pipeline {pipeline} target denominator does not match the frozen annotations")
    if metric["overall"].get("completion") != {"completed": len(expected_page_ids)}:
        raise ContractError(f"Pipeline {pipeline} scoring reports incomplete pages")
    if score_log != metric["overall"]:
        raise ContractError(f"Pipeline {pipeline} score log disagrees with evaluation.json")

    # The per-run manifest protects extraction exports; the index additionally protects scoring outputs.
    for name in RUN_ARTIFACTS - {"run.json"}:
        if metadata.get("artifact_sha256", {}).get(name) != entry["artifact_sha256"][name]:
            raise ContractError(f"Pipeline {pipeline} run manifest disagrees for {name}")

    with (pipeline_folder / "candidates.csv").open(encoding="utf-8-sig", newline="") as handle:
        candidate_rows = list(csv.DictReader(handle))
    with (pipeline_folder / "review.csv").open(encoding="utf-8-sig", newline="") as handle:
        review_rows = list(csv.DictReader(handle))
    candidate_keys = [(row["source_id"], row["pdf_page"], row["target_id"])
                      for row in candidate_rows]
    review_keys = [(row["source_id"], row["pdf_page"], row["target_id"])
                   for row in review_rows]
    if (len(candidate_keys) != len(set(candidate_keys))
            or set(candidate_keys) != expected_target_keys
            or len(review_keys) != len(set(review_keys))
            or set(review_keys) != expected_target_keys):
        raise ContractError(f"Pipeline {pipeline} candidate/review rows do not match target coverage")
    if (any(row["pipeline"] != pipeline for row in candidate_rows + review_rows)
            or any(row["disposition"] != "review_required"
                   for row in candidate_rows + review_rows)):
        raise ContractError(f"Pipeline {pipeline} review exports violate the all-review policy")

    return metric, pages


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir',type=Path,default=Path('results'))
    args=parser.parse_args()
    folder = args.results_dir if args.results_dir.is_absolute() else ROOT/args.results_dir
    manifest, targets, _ = load_contracts(ROOT / "data/manifest.json",
                                           ROOT / "data/annotations/targets.json")
    references = read_json(ROOT / "data/annotations/references.json")
    expected_page_ids = {page["page_id"] for page in targets["pages"]
                         if page["split"] == "evaluation"}
    expected_target_keys = {
        (page["source_id"], str(page["pdf_page"]), target["target_id"])
        for page in targets["pages"] if page["split"] == "evaluation"
        for target in page["targets"]
    }
    reference_ids = [page["page_id"] for page in references["pages"]]
    if len(reference_ids) != len(set(reference_ids)) or set(reference_ids) != {
            page["page_id"] for page in targets["pages"]}:
        raise ContractError("Reference pages do not match the validated target set")

    index = read_json(folder / "benchmark-index.json")
    validate_benchmark_index(index)
    notes = {page["page_id"]: page["annotation_notes"] for page in references["pages"]}
    rows, page_rows, image_hashes, layout_groups = [], [], {}, {}

    for pipeline in PIPELINES:
        entry = index["pipelines"][pipeline]
        metric, pages = verify_pipeline(folder, pipeline, entry, expected_page_ids,
                                        expected_target_keys)
        metadata = read_json(folder / pipeline / "run.json")
        overall = metric["overall"]
        warmed = [page["warmed_median_seconds"] for page in metric["pages"]
                  if page["warmed_median_seconds"] is not None]
        row = {
            "pipeline": pipeline,
            "completed_pages": metadata["completed_pages"],
            "selected_pages": len(expected_page_ids),
            "strict_scalar_matches": overall["strict_field_matches"],
            "scalar_targets": overall["evaluable_targets"],
            "numeric_matches": overall["numeric_strict_matches"],
            "numeric_targets": overall["numeric_targets"],
            "unavailable_matches": overall["unavailable_matches"],
            "unavailable_targets": overall["unavailable_targets"],
            "candidate_matches": overall["candidate_matches"],
            "text_regions_resolved": overall["text_regions_resolved"],
            "median_of_warmed_page_medians_seconds": median(warmed) if warmed else None,
            "sum_warmed_page_medians_seconds": sum(warmed) if warmed else None,
            "adapter_initialization_seconds": metadata["initialization_seconds"],
            "repeated_workload_seconds_excluding_export": metadata["command_seconds"],
            "external_workload_seconds_including_export": entry["external_wall_seconds"],
            "accepted_coverage": overall["accepted_coverage"],
            "incorrect_acceptance_rate": overall["incorrect_acceptance_rate"],
        }
        for policy in ("default", "table_labels_v1"):
            group = metric["by_text_policy"][policy]
            for measure in ("pages", "reference_chars", "char_edits", "CER",
                            "reference_words", "word_edits", "WER"):
                row[f"{policy}_{measure}"] = group[measure]
        rows.append(row)

        for page in metric["pages"]:
            task = ("narrative_scalar_targets" if "No table" in notes[page["page_id"]]
                    else "table_scalar_targets")
            text_layout = "table_labels" if page["text_policy"] == "table_labels_v1" else "prose_passage"
            page_rows.append({
                "pipeline": pipeline,
                "page_id": page["page_id"],
                "source_id": page["source_id"],
                "status": page["status"],
                "field_task_layout": task,
                "text_reference_type": text_layout,
                "text_policy": page["text_policy"],
                "CER": page["CER"],
                "WER": page["WER"],
                "text_alignment": page["text_alignment"],
                "strict_matches": sum(field["strict_match"] for field in page["fields"]
                                       if field["evaluable"]),
                "targets": sum(field["evaluable"] for field in page["fields"]),
                "warmed_median_seconds": page["warmed_median_seconds"],
            })
        layout_groups[pipeline] = {
            task: {
                "pages": sum(page["field_task_layout"] == task for page in page_rows
                             if page["pipeline"] == pipeline),
                "strict_matches": sum(page["strict_matches"] for page in page_rows
                                      if page["pipeline"] == pipeline
                                      and page["field_task_layout"] == task),
                "targets": sum(page["targets"] for page in page_rows
                               if page["pipeline"] == pipeline
                               and page["field_task_layout"] == task),
            }
            for task in ("table_scalar_targets", "narrative_scalar_targets")
        }
        if pipeline != "N":
            for page in pages:
                render = page.get("render")
                if not render or not render.get("image_sha256"):
                    raise ContractError(f"Pipeline {pipeline} has no render hash for {page['page_id']}")
                image_hashes.setdefault(page["page_id"], {})[pipeline] = render["image_sha256"]

    if set(image_hashes) != expected_page_ids:
        raise ContractError("Shared image evidence does not cover every evaluation page")
    for page_id, hashes in image_hashes.items():
        if set(hashes) != {"A", "B", "C"} or len(set(hashes.values())) != 1:
            raise ContractError(f"Primary OCR pipelines received different page pixels: {page_id}")

    for filename, items in (("comparison.csv", rows), ("per-page.csv", page_rows)):
        with (folder / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(items[0]))
            writer.writeheader()
            writer.writerows(items)
    summary = {
        "pipelines": rows,
        "shared_image_hashes_verified": image_hashes,
        "by_field_task_layout": layout_groups,
        "layout_note": "Field-task groups derive from frozen annotation exceptions (No table) versus the default first-table selection rule. They are descriptive tasks, not independently randomized page-layout conditions.",
        "field_exactness": "Normalized decimal-string equality preserving scale/sign; unavailable symbols scored by explicit marker class.",
        "policy_note": "Ordinary-passage and table-label CER/WER remain separate. Source/visual-tag breakdowns are in each evaluation.json.",
        "timing_note": index["timing_protocol"],
        "recommendation_status": "Requires case-specific decision; N is not an OCR candidate.",
    }
    (folder / "comparison.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("Comparison exports written; all run, score and shared-image checks passed", flush=True)


if __name__ == "__main__":
    main()
