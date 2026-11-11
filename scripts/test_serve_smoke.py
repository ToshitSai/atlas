"""Smoke test for Atlas Local Qwen Inference Server and backend/llm integration."""

import os
import sys
import time
import json
import urllib.request
import urllib.error
import subprocess
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY_EXE = ROOT / "training_env" / "Scripts" / "python.exe"

def run_smoke_test(adapter_path: str = None, model_name: str = None):
    adapter = adapter_path or str(ROOT / "training_artifacts" / "qwen3-17b-qlora")
    if not Path(adapter).exists():
        adapter = str(ROOT / "training_artifacts" / "qwen3-06b-qlora")

    print(f"[1/5] Launching local Qwen inference server with adapter: {adapter} on port 8001...")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    cmd = [
        str(PY_EXE),
        str(ROOT / "scripts" / "serve_qlora.py"),
        "--port", "8001",
        "--adapter", adapter
    ]
    if model_name:
        cmd.extend(["--model", model_name])

    server_proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    base_url = "http://127.0.0.1:8001"
    health_url = f"{base_url}/health"

    try:
        print("[2/5] Waiting for server initialization...")
        healthy = False
        start_wait = time.time()
        while time.time() - start_wait < 90:
            if server_proc.poll() is not None:
                out = server_proc.stdout.read()
                raise RuntimeError(f"Server exited prematurely with code {server_proc.returncode}:\n{out}")
            try:
                with urllib.request.urlopen(health_url, timeout=2) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode())
                        if data.get("status") == "healthy":
                            print(f"Server is healthy! Device: {data.get('device')}, VRAM: {data.get('vram_allocated_mb')}MB, Model: {data.get('model')}")
                            healthy = True
                            break
            except Exception:
                time.sleep(1)

        if not healthy:
            raise TimeoutError("Server failed to become healthy within 90 seconds.")

        # Test non-streaming
        print("[3/5] Testing standard completion (/v1/chat/completions)...")
        chat_url = f"{base_url}/v1/chat/completions"
        req_data = {
            "model": "local-qwen",
            "messages": [{"role": "user", "content": "What is Python?"}],
            "max_tokens": 64,
            "stream": False
        }
        req = urllib.request.Request(
            chat_url,
            data=json.dumps(req_data).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            res_body = json.loads(resp.read().decode("utf-8"))
            answer = res_body["choices"][0]["message"]["content"]
            print(f"Non-streaming response received ({len(answer)} chars):")
            print(f"  --> {answer.strip()[:100]}...")

        # Test streaming SSE
        print("[4/5] Testing streaming SSE completion (stream: true)...")
        req_data["stream"] = True
        req_stream = urllib.request.Request(
            chat_url,
            data=json.dumps(req_data).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        chunks = []
        with urllib.request.urlopen(req_stream, timeout=60) as resp:
            for line in resp:
                decoded = line.decode("utf-8").strip()
                if decoded.startswith("data: ") and decoded != "data: [DONE]":
                    chunk_obj = json.loads(decoded[6:])
                    delta = chunk_obj["choices"][0].get("delta", {}).get("content", "")
                    if delta:
                        chunks.append(delta)
        streamed_text = "".join(chunks)
        print(f"Streaming completed successfully ({len(chunks)} chunks, {len(streamed_text)} chars):")
        print(f"  --> {streamed_text.strip()[:100]}...")

        # Test backend integration via call_local_api
        print("[5/5] Testing backend/llm.py call_local_api integration...")
        sys.path.insert(0, str(ROOT))
        os.environ["LOCAL_LLM_BASE_URL"] = base_url
        os.environ["LOCAL_LLM_MODEL"] = "local-qwen"
        from backend.llm import call_local_api
        local_resp = call_local_api("Who created you?", return_details=True)
        print(f"backend.llm call_local_api succeeded:")
        print(f"  Text: {local_resp.get('text', '').strip()[:100]}...")
        print(f"  Model: {local_resp.get('model')}")
        print(f"  Gen Time: {local_resp.get('generation_time')}s")

        print("\nALL INFERENCE SMOKE TESTS PASSED!")

    finally:
        print("Terminating test inference server...")
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_proc.kill()
        print("Test server shutdown complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", default=None)
    parser.add_argument("--model", default=None)
    args = parser.parse_args()
    run_smoke_test(adapter_path=args.adapter, model_name=args.model)
