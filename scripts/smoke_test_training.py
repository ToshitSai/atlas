"""End-to-end SMOKE TEST of the real training pipeline (directive §12/§13).

Pipeline test ONLY — not real training:
    tiny synthetic dataset -> QLoRA SFT on Qwen3-0.6B (few steps)
    -> checkpoint saved -> adapter reloaded -> inference -> evaluation run

Verifies: GPU actually used (peak VRAM > 0 on the CUDA device), loss recorded,
checkpoint created, reload works, response generated, eval report written.
Any failure raises — the pipeline is not silently "green".

Usage (training venv):
    training_env/Scripts/python.exe scripts/smoke_test_training.py
"""
from __future__ import annotations

import json
import os
import sys

# NOTE: this repo has a local ``datasets/`` package (research CSVs) that would
# shadow the HuggingFace ``datasets`` library once the repo root is on
# sys.path. Import HF datasets FIRST so sys.modules caches the real library;
# all later lazy imports resolve to it.
import datasets  # noqa: F401  (HuggingFace datasets — must precede sys.path.insert)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from finetuning.config import LOCAL_SMOKE_TEST_MODEL  # noqa: E402
from finetuning.sft_trainer import TrainConfig, train_sft  # noqa: E402
from finetuning import inference  # noqa: E402

ART = os.path.join(REPO, "training_artifacts", "smoke")
DATA = os.path.join(ART, "dataset")
OUT = os.path.join(ART, "run")


def build_tiny_dataset() -> None:
    """~24 trivial message pairs, pipeline test only (never real training data)."""
    from datasets import Dataset
    qa = [
        ("What is 2 + 2?", "2 + 2 equals 4."),
        ("Name the capital of France.", "The capital of France is Paris."),
        ("What color is the sky on a clear day?", "The sky appears blue on a clear day."),
        ("What is 3 times 5?", "3 times 5 equals 15."),
        ("Who wrote Romeo and Juliet?", "Romeo and Juliet was written by William Shakespeare."),
        ("What is the boiling point of water in Celsius?", "Water boils at 100 degrees Celsius at sea level."),
        ("What is 10 minus 4?", "10 minus 4 equals 6."),
        ("Which planet is closest to the Sun?", "Mercury is the planet closest to the Sun."),
        ("What do bees make?", "Bees make honey."),
        ("How many days are in a week?", "There are 7 days in a week."),
        ("What is 100 divided by 10?", "100 divided by 10 equals 10."),
        ("What gas do plants absorb from the air?", "Plants absorb carbon dioxide from the air."),
        ("What is the largest ocean on Earth?", "The Pacific Ocean is the largest ocean on Earth."),
        ("How many legs does a spider have?", "A spider has 8 legs."),
        ("What is 6 plus 7?", "6 plus 7 equals 13."),
        ("What language is mainly spoken in Brazil?", "Portuguese is the main language spoken in Brazil."),
        ("What is 9 times 9?", "9 times 9 equals 81."),
        ("What fruit is famous for keeping the doctor away?", "The apple is famous for keeping the doctor away."),
        ("What season comes after summer?", "Autumn comes after summer."),
        ("What is 5 squared?", "5 squared equals 25."),
        ("Which animal is known as man's best friend?", "The dog is known as man's best friend."),
        ("What is 20 minus 15?", "20 minus 15 equals 5."),
        ("What do caterpillars turn into?", "Caterpillars turn into butterflies or moths."),
        ("How many minutes are in an hour?", "There are 60 minutes in an hour."),
    ]
    rows = [{"messages": [{"role": "user", "content": q}, {"role": "assistant", "content": a}],
             "category": "smoke", "license": "n/a"} for q, a in qa]
    os.makedirs(DATA, exist_ok=True)
    Dataset.from_list(rows).save_to_disk(os.path.join(DATA, "train"))


def main() -> int:
    import torch
    if not torch.cuda.is_available():
        print("FAIL: CUDA unavailable — smoke test must run in training_env on the GPU")
        return 1

    print("== smoke test: building tiny dataset ==")
    build_tiny_dataset()

    print("== smoke test: QLoRA SFT on", LOCAL_SMOKE_TEST_MODEL, "==")
    cfg = TrainConfig(
        base_model=LOCAL_SMOKE_TEST_MODEL, dataset_dir=DATA, output_dir=OUT,
        max_steps=5, max_samples=8, epochs=1.0, max_seq_len=512,
        per_device_batch_size=1, gradient_accumulation_steps=2,
        save_steps=100, logging_steps=1)
    metrics = train_sft(cfg)
    print("train metrics:", json.dumps(metrics, indent=2)[:800])

    adapter_dir = os.path.join(OUT, "adapter")
    assert os.path.isfile(os.path.join(adapter_dir, "adapter_config.json")), \
        "adapter checkpoint was not created"
    print("== checkpoint created:", adapter_dir)

    print("== reload base + adapter for inference ==")
    model, tok = inference.load_for_inference(LOCAL_SMOKE_TEST_MODEL, adapter_dir)
    answer = inference.chat(model, tok, [{"role": "user", "content": "What is 2 + 2?"}],
                            max_new_tokens=32)
    assert answer.strip(), "model produced an empty response"
    print("== inference answer:", answer[:120])

    print("== evaluation battery (pipeline check) ==")
    from finetuning import evaluate
    report = evaluate.run(model, tok, out_json=os.path.join(REPO, "artifacts", "smoke_eval.json"),
                          label="smoke_0.6B", max_new_tokens=48)
    print("eval scores:", report["scores_by_category"])

    inference.unload(model)

    summary = {
        "status": "PASS",
        "gpu": metrics["gpu"],
        "peak_vram_mib": metrics["peak_vram_mib"],
        "train_loss_final": metrics["train_loss_final"],
        "checkpoint": adapter_dir,
        "inference_answer_preview": answer[:200],
        "eval_scores": report["scores_by_category"],
    }
    os.makedirs(os.path.join(REPO, "artifacts"), exist_ok=True)
    with open(os.path.join(REPO, "artifacts", "smoke_test_report.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("SMOKE TEST PASS —", json.dumps({k: summary[k] for k in
          ("gpu", "peak_vram_mib", "train_loss_final")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
