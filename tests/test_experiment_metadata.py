"""Tests for backend.experiment_metadata — versioned telemetry, corrupted & missing file handling, and hardware audit."""

import json
from pathlib import Path
import tempfile
import pytest

from backend import experiment_metadata


def test_inspect_real_environment():
    gpu = experiment_metadata.inspect_gpu_environment()
    assert "detected" in gpu
    assert "device" in gpu
    assert "cuda_available" in gpu
    assert isinstance(gpu["cuda_available"], bool)
    if not gpu["cuda_available"]:
        assert gpu["status"] == "unavailable"
        assert gpu["device"] == "unavailable"


def test_validate_training_summary_schema():
    assert experiment_metadata.validate_training_summary(None) == (False, "missing")
    assert experiment_metadata.validate_training_summary({}) == (False, "incomplete")
    assert experiment_metadata.validate_training_summary({"model": "test"}) == (False, "incomplete")
    assert experiment_metadata.validate_training_summary({
        "model": "test",
        "parameters": {},
        "telemetry": {}
    }) == (False, "incomplete")
    assert experiment_metadata.validate_training_summary({
        "model": "test",
        "parameters": {"lr": 0.001},
        "telemetry": {"steps_completed": 100, "final_loss": 0.85}
    }) == (True, "valid")


def test_corrupted_and_missing_telemetry_files():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Missing file
        data, status = experiment_metadata.read_json_safely(tmp_path / "nonexistent.json")
        assert data is None
        assert status == "missing"

        # Corrupted JSON (syntax error)
        corrupted = tmp_path / "corrupted.json"
        corrupted.write_text("{invalid json here: 123", encoding="utf-8")
        data, status = experiment_metadata.read_json_safely(corrupted)
        assert data is None
        assert status == "corrupted"

        # Empty file
        empty = tmp_path / "empty.json"
        empty.write_text("   \n", encoding="utf-8")
        data, status = experiment_metadata.read_json_safely(empty)
        assert data is None
        assert status == "corrupted"

        # Valid file
        valid = tmp_path / "valid.json"
        valid.write_text('{"model": "test", "parameters": {}, "telemetry": {"steps_completed": 50, "final_loss": 1.1}}', encoding="utf-8")
        data, status = experiment_metadata.read_json_safely(valid)
        assert data is not None
        assert status == "ok"
        valid_flag, reason = experiment_metadata.validate_training_summary(data)
        assert valid_flag is True
        assert reason == "valid"


def test_versioned_telemetry_with_synthetic_repo():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        art = tmp_path / "training_artifacts" / "qwen3-17b-gen3-qlora"
        art.mkdir(parents=True)
        
        # When artifact directory exists but summary is corrupted:
        (art / "training_summary.json").write_text("NOT_JSON", encoding="utf-8")
        res = experiment_metadata.get_versioned_telemetry(repo_root=tmp_path)
        assert res["generations"]["gen3"]["status"] == "corrupted_metadata"
        assert res["generations"]["gen3"]["training_completed"] is False
        assert res["training_completed"] is False

        # When summary is incomplete:
        (art / "training_summary.json").write_text(json.dumps({"model": "Qwen3"}), encoding="utf-8")
        res = experiment_metadata.get_versioned_telemetry(repo_root=tmp_path)
        assert res["generations"]["gen3"]["status"] == "incomplete_metadata"
        assert res["generations"]["gen3"]["training_completed"] is False

        # When summary is completely valid:
        valid_summary = {
            "model": "Qwen/Qwen3-1.7B",
            "parameters": {"learning_rate": 0.00018},
            "telemetry": {"steps_completed": 237, "final_loss": 0.9024}
        }
        (art / "training_summary.json").write_text(json.dumps(valid_summary), encoding="utf-8")
        (art / "adapter_config.json").write_text("{}", encoding="utf-8")
        res = experiment_metadata.get_versioned_telemetry(repo_root=tmp_path)
        assert res["generations"]["gen3"]["status"] == "completed"
        assert res["generations"]["gen3"]["training_completed"] is True
        assert res["training_completed"] is True
        assert res["adapter_available"] is True
        assert res["generation"] == 3


def test_real_repo_telemetry():
    res = experiment_metadata.get_versioned_telemetry()
    assert res["status"] in ("completed", "idle")
    assert res["generation"] in (1, 2, 3)
    assert "generations" in res
    assert "gpu_info" in res
    assert "local_inference_server" in res
    assert "production_inference" in res
