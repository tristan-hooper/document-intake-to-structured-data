import copy
import hashlib
import io
import json
from pathlib import Path

from pypdf import PdfWriter
import pytest

from scan_intake.contracts import ContractError, load_contracts, read_json, source_snapshot, validate_bounds
from scan_intake.extraction import normalize_number, normalize_text, select_region
from scan_intake.rendering import open_document

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("raw,expected",[("1,234.50","1234.50"),("-0.05","-0.05"),("+12.00","+12.00"),("0003","0003"),("9007199254740993","9007199254740993")])
def test_exact_decimal_text(raw,expected):
    result = normalize_number(raw)
    assert result["kind"] == "number" and result["value"] == expected and result["raw_value"] == raw


@pytest.mark.parametrize("raw",["1,23","1O0","NaN","1e3","12*","1 234","12,34,567","--1","1.2.3"])
def test_invalid_digits_are_not_repaired(raw):
    assert normalize_number(raw)["kind"] == "invalid"


def test_missing_unavailable_and_zero_are_distinct():
    assert normalize_number("")["kind"] == "missing"
    assert normalize_number("...")["kind"] == "unavailable"
    assert normalize_number("...")["marker_kind"] == "dot_leader_no_value"
    assert normalize_number("—")["marker_kind"] == "dash_no_value"
    assert normalize_number("0")["value"] == "0"


def test_normalization_preserves_required_distinctions():
    assert normalize_text("ABC,\n de-\n f") == "ABC, de- f"
    assert normalize_text("Que\u0301bec") == "Québec"
    assert normalize_text("Maine...* 2", "table_labels_v1") == "Maine"


def test_no_invented_word_geometry_for_crossing_line():
    raw = [{"text":"Count 123 and other text","bounds":[.1,.1,.9,.2],"scope":"line"}]
    text,evidence,crossing = select_region(raw,[.3,.1,.6,.2])
    assert text == "Count 123 and other text" and crossing and evidence == raw


def test_duplicate_json_keys_and_nonfinite_values_rejected(tmp_path):
    path = tmp_path/"bad.json"
    for text in ['{"x":1,"x":2}','{"x":NaN}']:
        path.write_text(text,encoding="utf-8")
        with pytest.raises(ContractError):
            read_json(path)


def test_manifest_overlap_rejected(tmp_path):
    manifest = read_json(ROOT/"data/manifest.json")
    manifest["sources"][0]["development_pdf_pages"] = [1]
    path = tmp_path/"manifest.json"
    path.write_text(json.dumps(manifest),encoding="utf-8")
    with pytest.raises(ContractError,match="overlapping"):
        load_contracts(path,ROOT/"data/annotations/targets.json")


def test_bounds_reject_boolean_and_outside_page():
    for bounds in ([False,.1,.5,.5],[-.1,.1,.5,.5],[.5,.1,.5,.5]):
        with pytest.raises(ContractError):
            validate_bounds(bounds)


def test_target_page_boolean_is_not_page_one(tmp_path):
    targets=read_json(ROOT/'data/annotations/targets.json')
    targets['pages'][0]['pdf_page']=True
    path=tmp_path/'targets.json'
    path.write_text(json.dumps(targets),encoding='utf-8')
    with pytest.raises(ContractError,match='integer'):
        load_contracts(ROOT/'data/manifest.json',path)


def test_pipeline_model_verification_is_scoped_and_rejects_hash(tmp_path):
    from scan_intake.contracts import verify_models
    (tmp_path/'data').mkdir()
    (tmp_path/'models/rapidocr').mkdir(parents=True)
    file=tmp_path/'models/rapidocr/model.onnx'
    file.write_bytes(b'known')
    items=[{'path':'models/rapidocr/model.onnx','bytes':5,'sha256':hashlib.sha256(b'known').hexdigest()},
           {'path':'tools/vendor/missing.exe','bytes':1,'sha256':'0'*64}]
    (tmp_path/'data/model-manifest.json').write_text(json.dumps({'files':items}),encoding='utf-8')
    assert verify_models(tmp_path,'B')['total_bytes']==5
    file.write_bytes(b'wrong')
    with pytest.raises(ContractError,match='hash mismatch'):
        verify_models(tmp_path,'B')


def test_hash_and_size_rejected_but_renamed_content_preserved(tmp_path):
    data = b"source bytes"
    source = dict(local_file="original.pdf",bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    (tmp_path/source["local_file"]).write_bytes(data)
    assert source_snapshot(tmp_path,source) == data
    renamed = {**source,"local_file":"renamed.pdf"}
    (tmp_path/renamed["local_file"]).write_bytes(data)
    assert source_snapshot(tmp_path,renamed) == data
    (tmp_path/source["local_file"]).write_bytes(b"wrong bytes!")
    with pytest.raises(ContractError):
        source_snapshot(tmp_path,source)


def test_actual_encrypted_and_malformed_pdfs_rejected():
    writer = PdfWriter()
    writer.add_blank_page(width=72,height=72)
    writer.encrypt("secret")
    buffer = io.BytesIO()
    writer.write(buffer)
    for data in (b"not a PDF",buffer.getvalue()):
        with pytest.raises(ContractError,match="Malformed, encrypted"):
            open_document(data,{"total_pdf_pages":1})


def test_render_pixel_cap_precedes_allocation(tmp_path):
    from scan_intake.rendering import render_page
    writer = PdfWriter()
    writer.add_blank_page(width=2000,height=2000)
    buffer = io.BytesIO()
    writer.write(buffer)
    data = buffer.getvalue()
    with pytest.raises(ContractError,match="pixel limit"):
        render_page(data,{"total_pdf_pages":1,"sha256":hashlib.sha256(data).hexdigest()},1,tmp_path)
