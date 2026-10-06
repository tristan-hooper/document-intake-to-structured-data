"""Scorer-only reference access. Adapters and extraction never import this module."""
from collections import Counter
import json
from pathlib import Path
from statistics import median

from .contracts import ContractError, read_json
from .extraction import normalize_text


def edit_distance(reference,prediction):
    previous = list(range(len(prediction)+1))
    for index,expected in enumerate(reference,1):
        current = [index]
        for j,actual in enumerate(prediction,1):
            current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(expected != actual)))
        previous = current
    return previous[-1]


def evaluate_run(run_path,references_path,targets_path):
    results = read_json(Path(run_path)/"pages.json")
    references = read_json(references_path)
    targets = read_json(targets_path)
    reference_by_id = {p["page_id"]:p for p in references["pages"]}
    target_by_id = {p["page_id"]:p for p in targets["pages"]}
    split = read_json(Path(run_path)/"run.json")["split"]
    expected = {p["page_id"] for p in targets["pages"] if p["split"] == split}
    if len(results) != len(expected) or {p["page_id"] for p in results} != expected:
        raise ContractError("Run missing, duplicating or adding selected pages")
    summaries = []
    for result in results:
        page_id = result["page_id"]
        reference,spec = reference_by_id[page_id],target_by_id[page_id]
        policy = spec["text_region"].get("normalization","default")
        text_ref = normalize_text(reference["text"],policy)
        text_pred = normalize_text(result["regions"]["text"],policy)
        chars,words = edit_distance(text_ref,text_pred),edit_distance(text_ref.split(),text_pred.split())
        actual = {f["target_id"]:f for f in result["regions"]["fields"]}
        field_results = []
        for expected_field in reference["targets"]:
            field = actual[expected_field["target_id"]]
            equal = field["kind"] == expected_field["expected_kind"] and field["value"] == expected_field["normalized_value"]
            if expected_field["expected_kind"] == "unavailable":
                equal = equal and field.get("marker_kind") in expected_field["markers"]
            strict = equal and field["alignment"] == "resolved" and result["status"] == "completed"
            field_results.append(dict(target_id=field["target_id"],evaluable=expected_field["evaluable"],
                expected_kind=expected_field["expected_kind"],expected_value=expected_field["normalized_value"],
                actual_kind=field["kind"],actual_value=field["value"],candidate_match=equal,
                strict_match=strict,alignment=field["alignment"],disposition=field["disposition"],reason=field["reason"]))
        timings = result.get("warmed_processing_seconds",[])
        summaries.append(dict(page_id=page_id,source_id=spec["source_id"],status=result["status"],
            visual_tags=result["source"].get("visual_tags",[]),
            text_policy=policy,char_edits=chars,reference_chars=len(text_ref),word_edits=words,
            reference_words=len(text_ref.split()),CER=chars/len(text_ref) if text_ref else None,
            WER=words/len(text_ref.split()) if text_ref.split() else None,
            text_alignment=result["regions"]["text_alignment"],fields=field_results,
            processing_seconds=result.get("output",{}).get("processing_seconds"),
            warmed_processing_seconds=timings,warmed_median_seconds=median(timings) if timings else None))
    def aggregate(pages):
        fields = [f for p in pages for f in p["fields"] if f["evaluable"]]
        accepted = [f for f in fields if f["disposition"] == "candidate_accepted"]
        wrong = sum(not f["strict_match"] for f in accepted)
        char_n,word_n = sum(p["reference_chars"] for p in pages),sum(p["reference_words"] for p in pages)
        char_e,word_e = sum(p["char_edits"] for p in pages),sum(p["word_edits"] for p in pages)
        numeric = [f for f in fields if f["expected_kind"] == "number"]
        unavailable = [f for f in fields if f["expected_kind"] == "unavailable"]
        return dict(pages=len(pages),completion=dict(Counter(p["status"] for p in pages)),
            reference_chars=char_n,char_edits=char_e,CER=char_e/char_n if char_n else None,
            reference_words=word_n,word_edits=word_e,WER=word_e/word_n if word_n else None,
            text_regions_resolved=sum(p["text_alignment"] == "resolved" for p in pages),
            evaluable_targets=len(fields),candidate_matches=sum(f["candidate_match"] for f in fields),
            strict_field_matches=sum(f["strict_match"] for f in fields),
            strict_field_accuracy=sum(f["strict_match"] for f in fields)/len(fields) if fields else None,
            numeric_targets=len(numeric),numeric_candidate_matches=sum(f["candidate_match"] for f in numeric),
            numeric_strict_matches=sum(f["strict_match"] for f in numeric),
            unavailable_targets=len(unavailable),unavailable_matches=sum(f["strict_match"] for f in unavailable),
            unavailable_review_routed=sum(f["disposition"] == "review_required" for f in unavailable),
            accepted_targets=len(accepted),accepted_coverage=len(accepted)/len(fields) if fields else None,
            incorrect_acceptances=wrong,incorrect_acceptance_rate=wrong/len(accepted) if accepted else None,
            acceptance_note="All fields require review; absence of accepted targets does not validate automatic acceptance.",
            reasons=dict(Counter(f["reason"] for f in fields)))
    summary = dict(split=split,pipeline=results[0]["pipeline"],overall=aggregate(summaries),
        by_source={s:aggregate([p for p in summaries if p["source_id"] == s]) for s in sorted({p["source_id"] for p in summaries})},
        by_text_policy={s:aggregate([p for p in summaries if p["text_policy"] == s]) for s in sorted({p["text_policy"] for p in summaries})},
        by_visual_tag={tag:aggregate([p for p in summaries if tag in p["visual_tags"]])
                       for tag in sorted({tag for p in summaries for tag in p["visual_tags"]})},
        visual_tag_note="Tags overlap and are report-level descriptions; groups are not independent quality strata or causal comparisons.",
        pages=summaries,context_accuracy="not scored: all field context supplied",
        timing_note="Warmed medians exclude rendering and initialization; per-page initial calls and total command duration are separate.")
    return summary
