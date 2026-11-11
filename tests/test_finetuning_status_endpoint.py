"""Tests for the /api/finetuning/status endpoint."""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_finetuning_status_endpoint():
    res = client.get("/api/finetuning/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("completed", "idle")
    assert data["base_model"] in ("Qwen/Qwen3-1.7B", "Qwen/Qwen3-0.6B")
    assert data["generation"] in (1, 2, 3)
    assert "generations" in data
    assert "gpu_info" in data
    assert isinstance(data["gpu_info"]["cuda_available"], bool)
    assert "training_completed" in data
    assert "adapter_available" in data
    assert "adapter_loaded" in data
    assert "gpu_detected" in data
    assert "inference_server_running" in data
    assert "remote_inference_connected" in data
    assert "production_inference" in data
    assert "local_inference_server" in data
    if data["training_summary"]:
        assert "telemetry" in data["training_summary"]
    if data["eval_report"]:
        assert "base_metrics" in data["eval_report"]
        assert "finetuned_metrics" in data["eval_report"]
