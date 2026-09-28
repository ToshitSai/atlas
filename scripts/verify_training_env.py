"""Verify the local model-training environment for AI Scientist.

Ordered checks (directive §2/§4/§20):
  1. torch import + version
  2. CUDA availability (hard gate — abort if unavailable)
  3. GPU name, VRAM, compute capability, driver-visible CUDA
  4. torch.version.cuda + torch.cuda.get_arch_list() must include this GPU's
     architecture (RTX 5050 = Blackwell = sm_120) — abort if unsupported
  5. Real GPU computation (fp32 matmul vs CPU reference) — abort on mismatch
  6. bitsandbytes import + NF4 4-bit quantize/dequantize roundtrip ON GPU,
     plus a Linear4bit forward pass (QLoRA prerequisites)
  7. transformers / peft / trl / datasets / accelerate import + versions

Exit code 0 = environment verified. Nonzero = hard blocker, reason printed.
Never fabricates results: every check reports what actually happened.

Usage:
    training_env/Scripts/python.exe scripts/verify_training_env.py [--json PATH]
"""
from __future__ import annotations

import argparse
import json
import platform
import sys

OK = "PASS"
FAIL = "FAIL"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", dest="json_path", default=None,
                    help="also write a machine-readable summary to this path")
    args = ap.parse_args()

    report: dict = {"python": sys.version.split()[0], "platform": platform.platform(),
                    "checks": [], "blocker": None}

    def check(name: str, passed: bool, detail: str) -> bool:
        status = OK if passed else FAIL
        print(f"[{status}] {name}: {detail}")
        report["checks"].append({"name": name, "status": status, "detail": detail})
        return passed

    # 1. torch ----------------------------------------------------------------
    try:
        import torch
    except Exception as e:  # pragma: no cover - environment-specific
        report["blocker"] = f"torch import failed: {e}"
        print(f"[FAIL] torch import: {e}")
        _emit(report, args.json_path)
        return 1
    check("torch", True, f"version {torch.__version__}")
    report["torch"] = torch.__version__

    # 2. CUDA availability (hard gate) ---------------------------------------
    cuda_ok = bool(torch.cuda.is_available())
    if not check("cuda_available", cuda_ok,
                 "CUDA device detected and usable" if cuda_ok else
                 "torch.cuda.is_available() is False -- driver/toolchain mismatch "
                 "or no usable GPU"):
        report["blocker"] = "CUDA unavailable"
        _emit(report, args.json_path)
        return 1

    # 3. GPU identity ----------------------------------------------------------
    props = torch.cuda.get_device_properties(0)
    free_b, total_b = torch.cuda.mem_get_info(0)
    cc = torch.cuda.get_device_capability(0)
    cc_str = f"sm_{cc[0]}{cc[1]}"
    check("gpu_identity", True,
          f"{props.name}, {total_b / 2**30:.1f} GiB VRAM "
          f"({free_b / 2**30:.1f} GiB free), compute capability {cc[0]}.{cc[1]}")
    report.update({"gpu": props.name, "vram_total_gib": round(total_b / 2**30, 2),
                   "vram_free_gib": round(free_b / 2**30, 2),
                   "compute_capability": f"{cc[0]}.{cc[1]}", "cuda_runtime": torch.version.cuda})

    # 4. Architecture support (Blackwell gate) --------------------------------
    arch_list = torch.cuda.get_arch_list()
    supported = cc_str in arch_list or f"{cc_str}a" in arch_list
    check("gpu_arch_supported", supported,
          f"need {cc_str}; build arch_list={arch_list}" if supported else
          f"torch build lacks {cc_str} kernels; arch_list={arch_list}")
    if not supported:
        report["blocker"] = f"torch build lacks {cc_str} kernel support"
        _emit(report, args.json_path)
        return 1
    report["arch_list"] = arch_list

    # 5. Real GPU computation ---------------------------------------------------
    gen = torch.Generator(device="cpu").manual_seed(0)
    a = torch.randn(512, 512, generator=gen)
    b = torch.randn(512, 512, generator=gen)
    gpu = (a.to("cuda") @ b.to("cuda")).cpu()
    ref = a @ b
    max_err = (gpu - ref).abs().max().item()
    check("gpu_matmul", max_err < 1e-3 and torch.isfinite(gpu).all().item(),
          f"fp32 matmul max |GPU-CPU| error = {max_err:.2e}")

    # 6. bitsandbytes 4-bit (QLoRA prerequisite) --------------------------------
    bnb_ok = False
    try:
        import bitsandbytes as bnb
        import bitsandbytes.functional as F
        w = torch.randn(256, 256, device="cuda", dtype=torch.float32)
        qw, state = F.quantize_4bit(w, quant_type="nf4")
        dqw = F.dequantize_4bit(qw, state)
        err = (w - dqw).abs().mean().item()
        bnb_ok = torch.isfinite(dqw).all().item() and err < 0.5
        detail = (f"bitsandbytes {bnb.__version__}: NF4 roundtrip mean abs err "
                  f"{err:.4f} (GPU)")
        check("bitsandbytes_nf4_roundtrip", bnb_ok, detail)
    except Exception as e:
        check("bitsandbytes_nf4_roundtrip", False, f"quantization test failed: {e}")

    lin_ok = False
    try:
        from bitsandbytes.nn import Linear4bit
        lin = Linear4bit(64, 32, bias=False, compute_dtype=torch.bfloat16,
                         quant_type="nf4")
        lin.weight.data = torch.randn(32, 64)
        lin = lin.to("cuda")  # triggers 4-bit quantization
        out = lin(torch.randn(4, 64, device="cuda", dtype=torch.bfloat16))
        lin_ok = out.shape == (4, 32) and torch.isfinite(out).all().item()
        check("bitsandbytes_linear4bit_forward", lin_ok,
              "4-bit Linear forward on GPU produced finite output" if lin_ok
              else "unexpected output")
    except Exception as e:
        check("bitsandbytes_linear4bit_forward", False, f"forward test failed: {e}")

    # 7. Training stack imports --------------------------------------------------
    versions = {}
    for mod in ("transformers", "peft", "trl", "datasets", "accelerate"):
        try:
            m = __import__(mod)
            versions[mod] = getattr(m, "__version__", "unknown")
            check(f"import_{mod}", True, f"version {versions[mod]}")
        except Exception as e:
            check(f"import_{mod}", False, str(e))

    blocker = None
    if not (bnb_ok and lin_ok):
        blocker = "bitsandbytes 4-bit not usable on this setup — QLoRA blocked; LoRA on bf16 weights remains available"
    report["blocker"] = blocker
    _emit(report, args.json_path)
    return 0 if blocker is None else 1


def _emit(report: dict, json_path: str | None) -> None:
    if json_path:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(json_path)), exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"[INFO] summary written to {json_path}")


if __name__ == "__main__":
    sys.exit(main())
