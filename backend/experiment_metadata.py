"""Atlas AI — Versioned Experiment Metadata & Training Telemetry Engine.

Provides an authoritative, honest inspection of training artifacts, evaluation metrics,
hardware availability, and inference server state. Never fabricates numbers or substitutes
synthetic telemetry when artifacts are missing or corrupted.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.request


def find_repo_root() -> Path:
    """Locate the repository root containing training_artifacts or backend."""
    candidates = [
        Path(__file__).resolve().parents[1],
        Path(os.getcwd()),
        Path(__file__).resolve().parent.parent,
    ]
    for c in candidates:
        if (c / "training_artifacts").exists() or (c / "backend").exists():
            return c
    return candidates[0]


def read_json_safely(file_path: Path) -> Tuple[Optional[Dict[str, Any]], str]:
    """Safely read and validate a JSON file.
    
    Returns:
        (data_dict, status_code) where status_code is one of:
        - "ok": valid JSON read successfully
        - "missing": file does not exist
        - "corrupted": invalid JSON syntax
        - "read_error": IO or permission error
    """
    if not file_path.exists():
        return None, "missing"
    if not file_path.is_file():
        return None, "missing"
    try:
        content = file_path.read_text(encoding="utf-8")
        if not content.strip():
            return None, "corrupted"
        data = json.loads(content)
        if not isinstance(data, dict):
            return None, "corrupted"
        return data, "ok"
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, "corrupted"
    except Exception as exc:
        return None, "read_error"


def validate_training_summary(summary: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
    """Verify that a training summary contains legitimate, complete telemetry keys."""
    if summary is None:
        return False, "missing"
    if not isinstance(summary, dict) or not summary:
        return False, "incomplete"
    required_keys = {"model", "parameters", "telemetry"}
    if not required_keys.issubset(summary.keys()):
        return False, "incomplete"
    telemetry = summary.get("telemetry")
    if not isinstance(telemetry, dict):
        return False, "incomplete"
    if "steps_completed" not in telemetry or "final_loss" not in telemetry:
        return False, "incomplete"
    return True, "valid"



def inspect_gpu_environment() -> Dict[str, Any]:
    """Inspect real GPU hardware in the executing environment without hardcoding values."""
    try:
        import torch
        if torch.cuda.is_available():
            dev_idx = torch.cuda.current_device()
            props = torch.cuda.get_device_properties(dev_idx)
            vram_gib = round(props.total_memory / (1024 ** 3), 2)
            name = torch.cuda.get_device_name(dev_idx)
            major = props.major
            return {
                "detected": True,
                "device": name,
                "total_vram_gib": vram_gib,
                "cuda_available": True,
                "cuda_version": torch.version.cuda or "unknown",
                "compute_capability": f"{major}.{props.minor}",
                "blackwell_sm120": major >= 12,
                "status": "ready"
            }
    except Exception:
        pass
    
    return {
        "detected": False,
        "device": "unavailable",
        "total_vram_gib": 0.0,
        "cuda_available": False,
        "cuda_version": "unavailable",
        "compute_capability": "unavailable",
        "blackwell_sm120": False,
        "status": "unavailable",
        "reason": "No GPU or CUDA runtime detected in current process environment."
    }


def check_local_inference_server(base_url: Optional[str] = None) -> Dict[str, Any]:
    """Check connectivity to the dedicated local Qwen QLoRA inference server."""
    url = (base_url or os.environ.get("LOCAL_LLM_BASE_URL") or "http://127.0.0.1:8001").rstrip("/")
    try:
        req = urllib.request.Request(f"{url}/health", headers={"User-Agent": "Atlas-MetadataEngine"})
        with urllib.request.urlopen(req, timeout=1.2) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "running": True,
                    "connected": True,
                    "url": url,
                    "adapter_loaded": data.get("adapter_loaded", True),
                    "active_model": data.get("active_model", "Qwen/Qwen3-1.7B"),
                    "details": data
                }
    except Exception as exc:
        pass
    return {
        "running": False,
        "connected": False,
        "url": url,
        "adapter_loaded": False,
        "status": "offline",
        "hint": "Run `python scripts/serve_qlora.py --port 8001` to start the local GPU server."
    }


def get_versioned_telemetry(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Build honest, comprehensive telemetry for all three generations and runtime states."""
    root = repo_root or find_repo_root()
    artifacts_dir = root / "training_artifacts"
    processed_dir = root / "data" / "processed"

    # Generations directories
    gens = {
        1: {
            "name": "Gen 1 (0.6B)",
            "base_model": "Qwen/Qwen3-0.6B",
            "dir": artifacts_dir / "qwen3-06b-qlora",
            "summary_file": artifacts_dir / "qwen3-06b-qlora" / "training_summary.json",
            "eval_file": artifacts_dir / "evaluation_report.json",
            "manifest_file": processed_dir / "manifest.json",
        },
        2: {
            "name": "Gen 2 (1.7B)",
            "base_model": "Qwen/Qwen3-1.7B",
            "dir": artifacts_dir / "qwen3-17b-qlora",
            "summary_file": artifacts_dir / "qwen3-17b-qlora" / "training_summary.json",
            "eval_file": artifacts_dir / "evaluation_report_gen2.json",
            "manifest_file": processed_dir / "manifest_gen2.json",
        },
        3: {
            "name": "Gen 3 (1.7B)",
            "base_model": "Qwen/Qwen3-1.7B",
            "dir": artifacts_dir / "qwen3-17b-gen3-qlora",
            "summary_file": artifacts_dir / "qwen3-17b-gen3-qlora" / "training_summary.json",
            "eval_file": artifacts_dir / "evaluation_report_gen3.json",
            "manifest_file": processed_dir / "manifest_gen3.json",
        },
    }

    generations_data: Dict[str, Any] = {}
    highest_valid_gen = 0
    active_summary = None
    active_eval = None
    active_manifest = None
    active_adapter_path = None
    active_base_model = "Qwen/Qwen3-1.7B"

    for g_num in sorted(gens.keys()):
        g_info = gens[g_num]
        summary, s_status = read_json_safely(g_info["summary_file"])
        eval_data, e_status = read_json_safely(g_info["eval_file"])
        manifest, m_status = read_json_safely(g_info["manifest_file"])

        is_valid_summary, summary_validity = validate_training_summary(summary)
        adapter_weights = g_info["dir"] / "adapter_model.safetensors"
        adapter_config = g_info["dir"] / "adapter_config.json"
        has_adapter_files = adapter_weights.exists() or adapter_config.exists()

        gen_status = "unavailable"
        if s_status == "corrupted":
            gen_status = "corrupted_metadata"
        elif s_status == "ok" and not is_valid_summary:
            gen_status = "incomplete_metadata"
        elif s_status == "ok" and is_valid_summary:
            gen_status = "completed"
            highest_valid_gen = g_num
            active_summary = summary
            active_eval = eval_data
            active_manifest = manifest
            active_adapter_path = str(g_info["dir"].relative_to(root)).replace("\\", "/")
            active_base_model = g_info["base_model"]

        generations_data[f"gen{g_num}"] = {
            "model": g_info["base_model"],
            "adapter": str(g_info["dir"].relative_to(root)).replace("\\", "/") if g_info["dir"].exists() else "unavailable",
            "status": gen_status,
            "training_completed": is_valid_summary,
            "adapter_available": has_adapter_files,
            "summary": summary if is_valid_summary else None,
            "eval_report": eval_data,
            "manifest_status": m_status,
        }

    # System runtime & server checks
    gpu_info = inspect_gpu_environment()
    local_server = check_local_inference_server()
    
    # Check production inference connectivity
    remote_inference = {
        "configured": bool(os.environ.get("REMOTE_LLM_URL")),
        "connected": False,
        "status": "unavailable"
    }
    
    # Provider routing check
    from backend import model_router
    any_cloud = model_router.any_provider_configured() if hasattr(model_router, "any_provider_configured") else False

    production_inference = {
        "cloud_providers_configured": any_cloud,
        "local_server_connected": local_server.get("connected", False),
        "production_mode": "hybrid (Vercel Serverless + Local/Cloud GPU)",
        "ready": any_cloud or local_server.get("connected", False)
    }

    # Overall system status
    status = "completed" if highest_valid_gen > 0 else "idle"
    if not active_summary and any(g["status"] == "corrupted_metadata" for g in generations_data.values()):
        status = "corrupted"

    return {
        "status": status,
        "generation": highest_valid_gen,
        "base_model": active_base_model,
        "adapter_model": active_adapter_path or "unavailable",
        "training_completed": highest_valid_gen > 0,
        "adapter_available": generations_data.get(f"gen{highest_valid_gen}", {}).get("adapter_available", False) if highest_valid_gen > 0 else False,
        "adapter_loaded": local_server.get("adapter_loaded", False),
        "gpu_detected": gpu_info.get("detected", False),
        "gpu_info": gpu_info,
        "inference_server_running": local_server.get("running", False),
        "local_inference_server": local_server,
        "remote_inference_connected": remote_inference,
        "production_inference": production_inference,
        "training_summary": active_summary,
        "eval_report": active_eval,
        "manifest": active_manifest,
        "generations": generations_data,
    }
