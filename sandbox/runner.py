import os
import sys
import time
import tempfile
import subprocess
import json
from typing import Dict, Any, Tuple

def is_docker_available() -> bool:
    """Checks if Docker daemon is accessible."""
    try:
        res = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=3)
        return res.returncode == 0
    except Exception:
        return False

def build_docker_run_args(temp_dir: str, dataset_path: str, extra_env: dict = None) -> list:
    """
    Build the `docker run` argv for an experiment (pure helper, unit-testable).

    The dataset — and the held-out test split when its host path exists — are
    mounted under /app with their REAL basenames, and DATASET_PATH / TEST_PATH
    are pointed at the container paths:
      * mounting a parquet file as 'dataset.csv' breaks the extension-based
        readers inside generated experiment scripts;
      * host paths (e.g. TEST_PATH set by the orchestrator) do not exist inside
        the container, so any host TEST_PATH is overridden with the mounted
        container path.
    """
    extra_env = extra_env or {}
    dataset_name = os.path.basename(str(dataset_path).replace("\\", "/")) or "dataset"
    container_dataset = f"/app/dataset/{dataset_name}"

    env = {
        "DATASET_PATH": container_dataset,
        "METRICS_PATH": "/app/metrics.json",
    }
    for k, v in extra_env.items():
        if v is not None:
            env[k] = str(v)

    mounts = [
        f"{temp_dir}:/app",
        f"{dataset_path}:{container_dataset}:ro",
    ]

    host_test_path = extra_env.get("TEST_PATH")
    if host_test_path and os.path.exists(str(host_test_path)):
        test_name = os.path.basename(str(host_test_path).replace("\\", "/")) or "test"
        container_test = f"/app/test/{test_name}"
        mounts.append(f"{host_test_path}:{container_test}:ro")
        env["TEST_PATH"] = container_test  # container path replaces host path

    cmd = ["docker", "run", "--rm"]
    for m in mounts:
        cmd += ["-v", m]
    # Defence in depth for generated code: no root user, no privilege
    # escalation, no network, bounded process count, and a read-only base
    # filesystem. The temporary /app bind mount is the only writable workspace
    # and is discarded after execution; datasets are separately mounted read-only.
    cmd += [
        "--cpus=2", "--memory=2g", "--pids-limit=128", "--network=none",
        "--read-only", "--tmpfs=/tmp:rw,noexec,nosuid,size=64m",
        "--security-opt=no-new-privileges", "--user=65534:65534",
    ]
    for k, v in env.items():
        cmd += ["-e", f"{k}={v}"]
    cmd += ["python:3.11-slim", "python", "/app/experiment.py"]
    return cmd


def execute_sandboxed_experiment(script_code: str, dataset_path: str, timeout_sec: int = 60,
                                 extra_env: dict = None) -> Dict[str, Any]:
    """
    Executes an experiment script in an isolated environment.
    Supports Docker container isolation if available, with automatic fallback
    to an isolated process sandbox.
    """
    docker_ready = is_docker_available()
    sandbox_mode = "Docker Container (Isolated)" if docker_ready else "Process Sandbox (Subprocess isolation)"
    extra_env = extra_env or {}

    with tempfile.TemporaryDirectory() as temp_dir:
        script_file = os.path.join(temp_dir, "experiment.py")
        metrics_file = os.path.join(temp_dir, "metrics.json")

        with open(script_file, "w", encoding="utf-8") as f:
            f.write(script_code)

        start_time = time.time()
        stdout = ""
        stderr = ""
        exit_code = -1
        metrics = {}

        if docker_ready:
            try:
                cmd = build_docker_run_args(temp_dir, dataset_path, extra_env)
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
                stdout = proc.stdout
                stderr = proc.stderr
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                stderr = f"Execution timed out after {timeout_sec} seconds in Docker sandbox."
                exit_code = 124
            except Exception as e:
                stderr = f"Docker execution error: {str(e)}"
                exit_code = 1
        else:
            # Subprocess Isolation Fallback
            # Do not inherit API keys, database URLs, or arbitrary application
            # configuration into generated code. This remains a development
            # fallback only; Docker is the production sandbox boundary.
            # APPDATA is allowlisted because on this Python install the ML stack
            # (pandas/numpy/sklearn) resolves through the USER site-packages
            # (%APPDATA%\\Python\\PythonXY\\site-packages); without it the child
            # interpreter loses every pip package ("No module named 'numpy'").
            # It is a filesystem path only — no credentials pass through.
            _sandbox_env_allowlist = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "APPDATA"}
            env = {key: value for key, value in os.environ.items()
                   if key in _sandbox_env_allowlist}
            env["DATASET_PATH"] = dataset_path
            env["METRICS_PATH"] = metrics_file
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            # Safety net independent of APPDATA: pass every resolved package
            # directory from the parent interpreter.  Windows installs may put
            # packages in either the roaming user site or the interpreter's
            # local Lib/site-packages.  Keeping only one made a valid local ML
            # runtime disappear inside experiments ("No module named numpy").
            try:
                import site as _site
                _package_dirs = [_site.getusersitepackages(), *_site.getsitepackages()]
                _package_dirs = [p for p in _package_dirs if p and os.path.isdir(p)]
                if _package_dirs:
                    env["PYTHONPATH"] = os.pathsep.join(
                        dict.fromkeys([*_package_dirs, *filter(None, env.get("PYTHONPATH", "").split(os.pathsep))])
                    )
            except Exception:
                pass
            for k, v in extra_env.items():
                if v is not None:
                    env[k] = str(v)

            try:
                proc = subprocess.run(
                    [sys.executable, script_file],
                    cwd=temp_dir,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec
                )
                stdout = proc.stdout
                stderr = proc.stderr
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                stderr = f"Execution timed out after {timeout_sec} seconds."
                exit_code = 124
            except Exception as e:
                stderr = f"Subprocess execution error: {str(e)}"
                exit_code = 1

        elapsed = round(time.time() - start_time, 2)

        # Parse output metrics JSON if created by script
        if os.path.exists(metrics_file):
            try:
                with open(metrics_file, "r", encoding="utf-8") as mf:
                    metrics = json.load(mf)
            except Exception:
                metrics = {}

        return {
            "sandboxMode": sandbox_mode,
            "dockerAvailable": docker_ready,
            "exitCode": exit_code,
            "runtime": f"{elapsed}s",
            "stdout": stdout,
            "stderr": stderr,
            "metrics": metrics,
            "success": exit_code == 0
        }
