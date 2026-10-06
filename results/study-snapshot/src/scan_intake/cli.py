"""One bounded CLI for verification, rendering, extraction and scoring."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter
from uuid import uuid4

from .contracts import ContractError, fingerprint, load_contracts, read_json, source_snapshot, verify_models
from .extraction import extract_regions
from .process import AdapterProcess
from .rendering import RENDER_SETTINGS, native_regions, render_page
from .storage import Store, export_run

ROOT = Path(__file__).resolve().parents[2]


def verify_freeze(root):
    freeze = read_json(root/"data/evaluation-freeze.json")
    for filename,expected in freeze["artifact_sha256"].items():
        if hashlib.sha256((root/filename).read_bytes()).hexdigest() != expected:
            raise ContractError(f"Frozen evaluation artifact changed: {filename}")
    return freeze


def implementation_fingerprint(root):
    return fingerprint({p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted((root/"src/scan_intake").glob("*.py"))})


def run_extraction(args):
    root = args.project.resolve()
    began = perf_counter()
    manifest,targets,sources = load_contracts(args.manifest,args.targets)
    config = read_json(root/"config/benchmark.json")
    if args.split == "evaluation":
        verify_freeze(root)
        if args.manifest.resolve() != (root/"data/manifest.json").resolve() or args.targets.resolve() != (root/"data/annotations/targets.json").resolve():
            raise ContractError("Evaluation must use frozen manifest and targets")
    model_manifest = verify_models(root,args.pipeline) if args.pipeline != "N" else {}
    configuration = fingerprint(dict(config=config,models=model_manifest,implementation=implementation_fingerprint(root)))
    pages = [p for p in targets["pages"] if p["split"] == args.split]
    if not pages:
        raise ContractError("No selected pages")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+args.pipeline+"-"+uuid4().hex[:8]
    runs = root/"runs"
    runs.mkdir(exist_ok=True)
    store = Store(runs/"state.sqlite")
    snapshots,source_errors = {},{}
    for source_id,source in sources.items():
        try:
            snapshots[source_id] = source_snapshot(args.raw_dir,source)
        except (OSError,ContractError) as error:
            source_errors[source_id] = f"{type(error).__name__}: {error}"
    worker,initializations = None,[]
    results = []
    try:
        for spec in pages:
            source = sources[spec["source_id"]]
            key = fingerprint(dict(source_sha256=source["sha256"],page=spec["pdf_page"],
                render=RENDER_SETTINGS,pipeline=args.pipeline,configuration=configuration,
                target_spec=spec,repetitions=args.repetitions))
            previous = None if args.fresh or spec["source_id"] in source_errors else store.lookup(key)
            if previous is not None:
                store.observe_alias(source)
                results.append({**previous,"result_cache_hit":True})
                print(spec["page_id"],"resumed committed page",flush=True)
                continue
            result = dict(page_id=spec["page_id"],source=source,pdf_page=spec["pdf_page"],
                printed_page_label=spec["printed_page_label"],pipeline=args.pipeline,
                configuration_fingerprint=configuration,status="failed",output={},result_cache_hit=False,
                processed_at=datetime.now(timezone.utc).isoformat())
            try:
                if spec["source_id"] in source_errors:
                    raise ContractError(source_errors[spec["source_id"]])
                snapshot = snapshots[spec["source_id"]]
                if args.pipeline == "N":
                    start = perf_counter()
                    output = native_regions(snapshot,source,spec)
                    output["processing_seconds"] = perf_counter()-start
                    response = dict(status="completed",output=output,warmed_processing_seconds=[])
                    result["render"] = None
                else:
                    render_cache = root/"data/rendered"/("cold/"+run_id if args.cold_render else "cache")
                    image,render = render_page(snapshot,source,spec["pdf_page"],render_cache)
                    result["render"] = render
                    if worker is None:
                        worker = AdapterProcess(root,args.pipeline,runs/(run_id+"-adapter.log"),
                            threads=config["threads"],initialization_timeout=config["initialization_timeout_seconds"])
                        initializations.append(worker.initialization_seconds)
                    response = worker.extract(image,args.repetitions,timeout=config["page_timeout_seconds"])
                if response["status"] != "completed":
                    raise RuntimeError(response.get("error","Extraction failed"))
                result.update(status="completed",output=response["output"],
                              warmed_processing_seconds=response["warmed_processing_seconds"])
                result["regions"] = extract_regions(response["output"],spec)
            except (Exception,KeyboardInterrupt) as error:
                if isinstance(error,KeyboardInterrupt):
                    raise
                result["error"] = f"{type(error).__name__}: {error}"
                result["status"] = "timeout" if isinstance(error,TimeoutError) else "failed"
                result["regions"] = extract_regions({},spec)
                for field in result["regions"]["fields"]:
                    field["reason"] = "ocr_timeout" if result["status"] == "timeout" else "extraction_failure"
                if worker is not None and worker.process.poll() is not None:
                    worker.close()
                    worker = None
            store.commit_page(key,source,args.pipeline,result)
            results.append(result)
            print(spec["page_id"],result["status"],result.get("error",""),flush=True)
    finally:
        if worker is not None:
            worker.close()
        store.close()
    metadata = dict(run_id=run_id,pipeline=args.pipeline,split=args.split,
        configuration_fingerprint=configuration,source_manifest_fingerprint=fingerprint(manifest),
        target_spec_fingerprint=fingerprint(targets),initialization_seconds=initializations,
        command_seconds=perf_counter()-began,repetitions=args.repetitions,
        cold_render=args.cold_render,
        timing_scope="includes source/model verification, initialization, render/cache, all recognition repetitions and page commits; excludes final export",
        cache_hits=sum(r["result_cache_hit"] for r in results),
        completed_pages=sum(r["status"] == "completed" for r in results),selected_pages=len(results),
        acceptance_policy=config["acceptance_policy"])
    destination = export_run(runs,run_id,results,metadata)
    print(json.dumps({"run":str(destination),"completed_pages":metadata["completed_pages"],"selected_pages":len(results)}))
    return 0 if metadata["completed_pages"] == len(results) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Real public scans -> traceable candidate and review CSVs")
    parser.add_argument("--project",type=Path,default=ROOT)
    parser.add_argument("--manifest",type=Path)
    parser.add_argument("--targets",type=Path)
    parser.add_argument("--raw-dir",type=Path)
    subparsers = parser.add_subparsers(dest="command",required=True)
    subparsers.add_parser("verify-sources")
    render = subparsers.add_parser("render")
    render.add_argument("--split",choices=["development","evaluation","all"],default="development")
    extract = subparsers.add_parser("extract")
    extract.add_argument("--pipeline",choices=["A","B","C","N"],required=True)
    extract.add_argument("--split",choices=["development","evaluation"],default="development")
    extract.add_argument("--repetitions",type=int,choices=[0,3],default=0)
    extract.add_argument("--fresh",action="store_true",help="Rerun extraction; retain render cache")
    extract.add_argument("--cold-render",action="store_true",help="Use a new render cache for this run; pair with --fresh")
    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("run",type=Path)
    evaluate.add_argument("--references",type=Path)
    evaluate.add_argument("--output",type=Path)
    args = parser.parse_args(argv)
    args.manifest = args.manifest or args.project/"data/manifest.json"
    args.targets = args.targets or args.project/"data/annotations/targets.json"
    args.raw_dir = args.raw_dir or args.project/"data/raw"
    try:
        if args.command == "extract":
            return run_extraction(args)
        manifest,targets,sources = load_contracts(args.manifest,args.targets)
        if args.command == "evaluate":
            from .evaluation import evaluate_run
            if read_json(args.run/"run.json")["split"] == "evaluation":
                verify_freeze(args.project)
                if args.references and args.references.resolve() != (args.project/"data/annotations/references.json").resolve():
                    raise ContractError("Evaluation must use frozen references")
            summary = evaluate_run(args.run,args.references or args.project/"data/annotations/references.json",args.targets)
            output = args.output or args.run/"evaluation.json"
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            print(json.dumps(summary["overall"],indent=2))
        else:
            snapshots = {source_id:source_snapshot(args.raw_dir,source) for source_id,source in sources.items()}
            if args.command == "verify-sources":
                from .rendering import open_document
                for source_id,source in sources.items():
                    document = open_document(snapshots[source_id],source)
                    document.close()
                    print(source_id,"hash, byte count and PDF page count verified")
            else:
                for spec in targets["pages"]:
                    if args.split != "all" and spec["split"] != args.split:
                        continue
                    path,metadata = render_page(snapshots[spec["source_id"]],sources[spec["source_id"]],
                                               spec["pdf_page"],args.project/"data/rendered/cache")
                    print(spec["page_id"],metadata["dimensions"],"cached" if metadata["cache_hit"] else "rendered")
        return 0
    except (OSError,ValueError,KeyError,RuntimeError) as error:
        print(f"{type(error).__name__}: {error}",file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
