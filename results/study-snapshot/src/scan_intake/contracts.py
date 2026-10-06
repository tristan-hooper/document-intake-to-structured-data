"""Strict input contracts and stable content fingerprints."""
import hashlib
import json
import math
from pathlib import Path


class ContractError(ValueError):
    pass


def unique_pairs(pairs):
    result = {}
    for key,value in pairs:
        if key in result:
            raise ContractError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path):
    def invalid(value):
        raise ContractError(f"Invalid JSON constant: {value}")
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      object_pairs_hook=unique_pairs,parse_constant=invalid)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,
                                    separators=(",",":"),allow_nan=False).encode()).hexdigest()


def validate_bounds(bounds):
    if not isinstance(bounds,list) or len(bounds) != 4:
        raise ContractError("Bounds must contain four numbers")
    if any(type(v) not in (float,int) or not math.isfinite(v) for v in bounds):
        raise ContractError("Bounds must be finite numeric values")
    left,top,right,bottom = bounds
    if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
        raise ContractError("Bounds outside page or without positive area")


def load_contracts(manifest_path,targets_path):
    manifest,targets = read_json(manifest_path),read_json(targets_path)
    expected,sources,hashes = {},{},set()
    for source in manifest["sources"]:
        source_id = source["source_id"]
        if source_id in sources or source["sha256"] in hashes:
            raise ContractError("Duplicate source identity or content")
        if len(source["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in source["sha256"]):
            raise ContractError("Invalid SHA-256")
        name = source["local_file"]
        if Path(name).name != name or "/" in name or "\\" in name:
            raise ContractError("Source filename must be a plain filename")
        if type(source["total_pdf_pages"]) is not int or not 1 <= source["total_pdf_pages"] <= 150:
            raise ContractError("Invalid source page count")
        seen = set()
        for split in ("development","evaluation"):
            for number in source[split+"_pdf_pages"]:
                if type(number) is not int or not 1 <= number <= source["total_pdf_pages"] or number in seen:
                    raise ContractError("Duplicate, overlapping or invalid selected page")
                seen.add(number)
                expected[(source_id,number)] = split
        sources[source_id] = source
        hashes.add(source["sha256"])
    seen_pages,seen_ids = set(),set()
    for page in targets["pages"]:
        if type(page["pdf_page"]) is not int:
            raise ContractError("Target page position must be an integer")
        key = (page["source_id"],page["pdf_page"])
        if key in seen_pages or page["page_id"] in seen_ids or expected.get(key) != page["split"]:
            raise ContractError("Invalid target page identity or split")
        if page["source_sha256"] != sources[key[0]]["sha256"]:
            raise ContractError("Target/source hash mismatch")
        seen_pages.add(key)
        seen_ids.add(page["page_id"])
        if len(page["targets"]) != 4:
            raise ContractError("Each selected page requires four targets")
        region_ids = set()
        for region in [page["text_region"],*page["targets"]]:
            validate_bounds(region["bounds"])
            region_id = region.get("target_id",region.get("region_id"))
            if not region_id or region_id in region_ids:
                raise ContractError("Duplicate or missing region identifier")
            region_ids.add(region_id)
            if {"raw_value","normalized_value","expected_kind","text","verification"} & region.keys():
                raise ContractError("Reference answer in runtime specification")
        for target in page["targets"]:
            if target["data_type"] != "decimal_or_unavailable" or not target["supplied_context"]:
                raise ContractError("Unsupported field contract")
    if seen_pages != set(expected):
        raise ContractError("Target pages do not cover source selection")
    return manifest,targets,sources


def source_snapshot(raw_dir,source):
    path = Path(raw_dir)/source["local_file"]
    if path.stat().st_size > 20*1024*1024:
        raise ContractError("Source exceeds 20 MiB limit")
    snapshot = path.read_bytes()
    if len(snapshot) > 20*1024*1024 or len(snapshot) != source["bytes"]:
        raise ContractError("Source size mismatch or limit exceeded")
    if hashlib.sha256(snapshot).hexdigest() != source["sha256"]:
        raise ContractError("Source hash mismatch")
    return snapshot


def verify_models(root,pipeline=None):
    manifest = read_json(root/"data/model-manifest.json")
    prefixes = {"A":("tools/vendor/",),"B":("models/rapidocr/",),
                "C":("models/rapidocr/","models/docling/")}
    files = [item for item in manifest["files"]
             if pipeline is None or item["path"].startswith(prefixes[pipeline])]
    if not files:
        raise ContractError("Empty model/runtime inventory")
    for item in files:
        path = (root/item["path"]).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ContractError("Model path escapes project")
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ContractError(f'Model hash mismatch: {item["path"]}')
    return {"files":files,"total_bytes":sum(item["bytes"] for item in files)}
