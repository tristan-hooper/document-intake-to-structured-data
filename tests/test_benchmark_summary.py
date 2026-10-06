import hashlib

import pytest

from scan_intake.contracts import ContractError
from tools.summarize_benchmark import INDEX_ARTIFACTS, PIPELINES, validate_benchmark_index, verify_artifacts


def completed_index():
    return {
        "status": "completed",
        "order": list(PIPELINES),
        "timing_protocol": "fixed protocol",
        "pipelines": {
            pipeline: {
                "status": "completed",
                "exit_code": 0,
                "scoring_exit_code": 0,
                "run_id": f"run-{pipeline}",
                "artifact_sha256": {name: "0" * 64 for name in INDEX_ARTIFACTS},
            }
            for pipeline in PIPELINES
        },
    }


def test_summary_index_requires_every_completed_pipeline_and_score_hash():
    index = completed_index()
    validate_benchmark_index(index)

    index["status"] = "completed_with_failures"
    with pytest.raises(ContractError, match="not fully completed"):
        validate_benchmark_index(index)

    index = completed_index()
    index["pipelines"]["B"]["scoring_exit_code"] = 1
    with pytest.raises(ContractError, match="did not complete"):
        validate_benchmark_index(index)

    index = completed_index()
    del index["pipelines"]["C"]["artifact_sha256"]["evaluation.json"]
    with pytest.raises(ContractError, match="missing required artifact hashes"):
        validate_benchmark_index(index)


def test_score_artifact_tampering_is_rejected(tmp_path):
    pipeline = "A"
    (tmp_path / pipeline).mkdir()
    data = b"scored output"
    (tmp_path / pipeline / "scoring.log").write_bytes(data)
    entry = {"artifact_sha256": {"scoring.log": hashlib.sha256(data).hexdigest()}}
    verify_artifacts(tmp_path, pipeline, entry)

    (tmp_path / pipeline / "scoring.log").write_bytes(b"changed output")
    with pytest.raises(ContractError, match="artifact hash mismatch"):
        verify_artifacts(tmp_path, pipeline, entry)
