"""Validate source identities, annotation coverage and reference separation."""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scan_intake.contracts import ContractError, load_contracts, read_json, validate_bounds

NUMBER = re.compile(r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", re.ASCII)
VERIFICATION = "second_visual_pass_same_annotator"
UNAVAILABLE_MARKERS = {"dot_leader_no_value", "dash_no_value"}


def require(condition, message):
    if not condition:
        raise ContractError(message)


def validate_annotation_data(manifest, targets, references):
    expected, source_ids, source_hashes = {}, set(), set()
    for source in manifest["sources"]:
        source_id, digest = source["source_id"], source["sha256"]
        require(source_id not in source_ids, f"Duplicate source id: {source_id}")
        require(digest not in source_hashes, f"Duplicate source hash: {source_id}")
        source_ids.add(source_id)
        source_hashes.add(digest)
        for split in ("development", "evaluation"):
            for number in source[f"{split}_pdf_pages"]:
                page_id = f"{source_id}-p{number:03}"
                require(page_id not in expected, f"Duplicate selected page: {page_id}")
                expected[page_id] = (split, digest)

    target_pages, reference_pages = targets["pages"], references["pages"]
    target_ids = [page["page_id"] for page in target_pages]
    reference_ids = [page["page_id"] for page in reference_pages]
    require(len(expected) == 16 and len(target_pages) == 16,
            "Expected 16 selected pages and target specifications")
    require(len(set(target_ids)) == len(target_ids), "Duplicate target page id")
    require(len(reference_ids) == len(set(reference_ids)), "Duplicate reference page id")
    require(set(target_ids) == set(expected), "Target pages do not match source selection")
    require(set(reference_ids) == set(expected), "Reference pages do not match source selection")

    reference_by_id = {page["page_id"]: page for page in reference_pages}
    targets_by_split = {"development": 0, "evaluation": 0}
    unavailable_by_split = {"development": 0, "evaluation": 0}
    all_target_ids = set()

    for page in target_pages:
        page_id = page["page_id"]
        split, digest = expected[page_id]
        require((page["split"], page["source_sha256"]) == (split, digest),
                f"Target source or split mismatch: {page_id}")
        reference = reference_by_id[page_id]
        require(reference.get("verification") == VERIFICATION,
                f"Unexpected reference verification state: {page_id}")
        require(isinstance(reference.get("text"), str) and reference.get("text_evaluable") is True,
                f"Invalid text reference: {page_id}")

        page_targets, page_references = page["targets"], reference["targets"]
        target_keys = [target["target_id"] for target in page_targets]
        reference_keys = [target["target_id"] for target in page_references]
        require(len(page_targets) == 4 and len(page_references) == 4,
                f"Each selected page requires four scalar targets: {page_id}")
        require(len(target_keys) == len(set(target_keys)), f"Duplicate runtime target id: {page_id}")
        require(len(reference_keys) == len(set(reference_keys)), f"Duplicate reference target id: {page_id}")
        require(set(target_keys) == set(reference_keys), f"Runtime/reference target mismatch: {page_id}")

        for region in [page["text_region"], *page_targets]:
            validate_bounds(region["bounds"])
            require(not ({"raw_value", "normalized_value", "expected_kind", "verification", "text"}
                         & region.keys()),
                    f"Reference answer found in runtime target file: {page_id}")

        for target in page_targets:
            target_id = target["target_id"]
            require(target_id not in all_target_ids, f"Duplicate target id across pages: {target_id}")
            all_target_ids.add(target_id)

        reference_by_target = {target["target_id"]: target for target in page_references}
        for target in page_targets:
            expected_value = reference_by_target[target["target_id"]]
            targets_by_split[split] += 1
            require(expected_value.get("verification") == VERIFICATION,
                    f"Unexpected target verification state: {target['target_id']}")
            require(expected_value.get("evaluable") is True,
                    f"Unexpected non-evaluable target: {target['target_id']}")

            if expected_value.get("expected_kind") == "number":
                raw = expected_value.get("raw_value")
                require(isinstance(raw, str) and NUMBER.fullmatch(raw) is not None,
                        f"Invalid numeric reference: {target['target_id']}")
                require(expected_value.get("normalized_value") == raw.replace(",", ""),
                        f"Numeric normalization mismatch: {target['target_id']}")
                require(expected_value.get("markers") == [],
                        f"Unexpected marker on numeric reference: {target['target_id']}")
            else:
                require(expected_value.get("expected_kind") == "unavailable"
                        and expected_value.get("raw_value") is None
                        and expected_value.get("normalized_value") is None,
                        f"Invalid unavailable reference: {target['target_id']}")
                markers = expected_value.get("markers")
                require(isinstance(markers, list) and len(markers) == 1
                        and markers[0] in UNAVAILABLE_MARKERS,
                        f"Invalid unavailable marker class: {target['target_id']}")
                unavailable_by_split[split] += 1

    require(targets_by_split == {"development": 16, "evaluation": 48},
            f"Unexpected target counts: {targets_by_split}")
    require(unavailable_by_split == {"development": 1, "evaluation": 2},
            f"Unexpected unavailable counts: {unavailable_by_split}")
    return {"pages": len(expected), "targets": targets_by_split,
            "unavailable_targets": unavailable_by_split,
            "runtime_reference_separation": "verified"}


def verify_source_files(manifest, raw_dir):
    for source in manifest["sources"]:
        path = Path(raw_dir) / source["local_file"]
        data = path.read_bytes()
        require(len(data) == source["bytes"], f"Source byte-count mismatch: {source['source_id']}")
        require(hashlib.sha256(data).hexdigest() == source["sha256"],
                f"Source hash mismatch: {source['source_id']}")


def main():
    manifest = read_json(ROOT / "data/manifest.json")
    targets = read_json(ROOT / "data/annotations/targets.json")
    references = read_json(ROOT / "data/annotations/references.json")
    load_contracts(ROOT / "data/manifest.json", ROOT / "data/annotations/targets.json")
    summary = validate_annotation_data(manifest, targets, references)
    verify_source_files(manifest, ROOT / "data/raw")
    summary["hashes_and_bounds"] = "verified"
    summary["source_files"] = "hashes and byte counts verified"
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
