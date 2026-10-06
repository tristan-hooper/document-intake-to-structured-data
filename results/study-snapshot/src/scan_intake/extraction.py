"""Deterministic geometry selection and lossless numeric normalization."""
from decimal import Decimal
import math
import re
import unicodedata

NUMBER = re.compile(r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?",re.ASCII)
UNAVAILABLE = re.compile(r"(?:\.{2,}|[-—–]{1,2}|[·•]{2,})")


def normalize_number(raw):
    if not isinstance(raw,str):
        return dict(kind="missing",value=None,raw_value=raw,markers=[])
    stripped = raw.strip()
    if not stripped:
        return dict(kind="missing",value=None,raw_value=raw,markers=[])
    if UNAVAILABLE.fullmatch(stripped):
        marker_kind = "dot_leader_no_value" if re.fullmatch(r"[.·•]{2,}",stripped) else "dash_no_value"
        return dict(kind="unavailable",value=None,raw_value=raw,markers=[stripped],marker_kind=marker_kind)
    if not NUMBER.fullmatch(stripped):
        return dict(kind="invalid",value=None,raw_value=raw,markers=[])
    normalized = stripped.replace(",","")
    # Construct Decimal directly from text; keep original scale/sign in the exported string.
    if not Decimal(normalized).is_finite():
        return dict(kind="invalid",value=None,raw_value=raw,markers=[])
    return dict(kind="number",value=normalized,raw_value=raw,markers=[])


def select_region(units,bounds):
    left,top,right,bottom = bounds
    chosen,crossing = [],False
    for item in units:
        box = item.get("bounds")
        if not box or len(box) != 4 or any(not math.isfinite(v) for v in box):
            continue
        x0,y0,x1,y1 = box
        cx,cy = (x0+x1)/2,(y0+y1)/2
        intersects = x0 < right and x1 > left and y0 < bottom and y1 > top
        coarse = item["scope"] in {"line","block","table_cell"}
        # A small OCR-box margin is allowed for numeric table cells; text strings are never split.
        margin = 0.003
        outside = x0 < left-margin or x1 > right+margin or y0 < top-margin or y1 > bottom+margin
        if coarse and intersects and outside:
            crossing = True
        if left <= cx < right and top <= cy < bottom:
            chosen.append(item)
    return " ".join(item["text"] for item in chosen),chosen,crossing


def extract_regions(output,page_spec):
    text_id = page_spec["text_region"]["region_id"]
    if "native_regions" in output:
        text = output["native_regions"][text_id]
        text_crossing = False
    else:
        text,_,text_crossing = select_region(output.get("units",[]),page_spec["text_region"]["bounds"])
    result = dict(text=text,text_alignment="unresolved" if text_crossing else "resolved",fields=[])
    for target in page_spec["targets"]:
        if "native_regions" in output:
            raw = output["native_regions"][target["target_id"]]
            evidence,crossing = [],False
        else:
            available = output.get("field_units",[])
            # A Docling cell has priority when its center belongs to this target.
            cell_units = [u for u in available if u["scope"] == "table_cell"]
            raw,evidence,crossing = select_region(cell_units,target["bounds"])
            if not evidence:
                raw,evidence,crossing = select_region([u for u in available if u["scope"] != "table_cell"],target["bounds"])
        value = normalize_number(raw)
        reason = {"missing":"missing_field","invalid":"invalid_number",
                  "unavailable":"unavailable_value","number":"prototype_requires_review"}[value["kind"]]
        if crossing:
            reason = "unresolved_region_alignment"
        result["fields"].append(dict(target_id=target["target_id"],**value,
            row_label=target["row_label"],column_label=target["column_label"],
            period_label=target["period_label"],unit_label=target["unit_label"],
            context_source="supplied_target_specification",bounds=target["bounds"],
            evidence=evidence,alignment="unresolved" if crossing else "resolved",
            disposition="review_required",reason=reason,human_confirmation="unconfirmed"))
    return result


def normalize_text(text,policy="default"):
    text = unicodedata.normalize("NFC",text)
    if policy == "table_labels_v1":
        text = re.sub(r"[^A-Za-z\s]","",text)
    elif policy != "default":
        raise ValueError("Unknown text normalization policy")
    return " ".join(text.split())
