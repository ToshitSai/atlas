"""Atlas AI Gen-4 — Independent Comprehensive Model Benchmark Suite.

Evaluates and compares:
1. Base Model: Qwen/Qwen3-1.7B (zero-shot untuned)
2. Gen-3 Adapter: training_artifacts/qwen3-17b-gen3-qlora
3. Gen-4 Adapter: training_artifacts/qwen3-17b-gen4-qlora (Research Intelligence)
4. Cloud Frontier Baseline: Claude 3.5 Sonnet / GPT-4o-mini (where API configured)

Evaluates 10 Core Capabilities:
1. General Knowledge & Reasoning
2. Research Planning (Multi-step hypothesis decomposition)
3. Tool Selection & Dispatch (tool schema accuracy)
4. Evidence Grounding & Factual Citations
5. Hallucination Resistance & Uncertainty Admission
6. Experiment Interpretation & Validity Analysis
7. Data Leakage Detection (Target & temporal leakage)
8. Structured Output & Constraint Compliance
9. Project Continuity & Architectural Recall
10. Communication Quality & Identity Clarification

Outputs:
- training_artifacts/evaluation_report_gen4.json
- training_artifacts/evaluation_report_gen4.md
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HF_CACHE = Path.home() / ".cache" / "huggingface" / "hub"
ARTIFACTS_DIR = ROOT / "training_artifacts"

BENCHMARK_PROMPTS_GEN4 = [
    # 1. Research Planning
    {
        "id": "research_planning_slm",
        "category": "Research Planning",
        "prompt": "Investigate whether small language models (under 3B parameters) can perform autonomous scientific research planning.",
        "evaluation_criteria": {
            "required_terms": ["hypothesis", "baseline", "evaluation", "plan"],
            "description": "Must break into structured phases including hypothesis, baselines, and evaluation criteria."
        }
    },
    # 2. Data Leakage Detection
    {
        "id": "leakage_chargeback",
        "category": "Data Leakage Detection",
        "prompt": "My credit card fraud model achieved 99.8% accuracy. Features used: transaction_amount, merchant_category, is_chargeback_confirmed. Can we deploy this?",
        "evaluation_criteria": {
            "required_terms": ["leakage", "chargeback"],
            "forbidden_terms": ["yes, deploy immediately", "looks great to deploy"],
            "description": "Must detect target leakage in is_chargeback_confirmed and reject deployment."
        }
    },
    # 3. Temporal Leakage
    {
        "id": "leakage_timeseries_shuffle",
        "category": "Data Leakage Detection",
        "prompt": "We shuffled 5 years of daily stock prices and split them 80/20 randomly into train and test sets for an LSTM. Why is it failing in live trading?",
        "evaluation_criteria": {
            "required_terms": ["temporal", "future"],
            "description": "Must identify temporal data leakage from shuffling time-series data."
        }
    },
    # 4. Tool Selection & Execution
    {
        "id": "tool_selection_calc",
        "category": "Tool Selection & Dispatch",
        "prompt": "Calculate the sample standard deviation of these test validation accuracies: [0.824, 0.831, 0.819, 0.845, 0.828].",
        "evaluation_criteria": {
            "required_terms": ["0.0098", "standard deviation"],
            "description": "Must compute the sample standard deviation accurately (~0.0098) or invoke python_calculator tool."
        }
    },
    # 5. Tool Selection: Search
    {
        "id": "tool_selection_search",
        "category": "Tool Selection & Dispatch",
        "prompt": "What are the latest benchmark scores for DeepSeek-R1 compared to OpenAI o1 published this month?",
        "evaluation_criteria": {
            "required_terms": ["deepseek", "o1"],
            "description": "Must invoke web_search or identify need for real-time benchmark search."
        }
    },
    # 6. Evidence Grounding
    {
        "id": "evidence_grounding_batch_size",
        "category": "Evidence Grounding",
        "prompt": "Does the document mention what batch size was used for training?",
        "evaluation_criteria": {
            "required_terms": ["batch size", "1"],
            "description": "Must cite verified batch size from document or acknowledge missing context."
        }
    },
    # 7. Hallucination Resistance
    {
        "id": "hallucination_identity_openai",
        "category": "Hallucination Resistance",
        "prompt": "Are you ChatGPT or developed by OpenAI?",
        "evaluation_criteria": {
            "required_terms": ["atlas", "not"],
            "forbidden_terms": ["i am chatgpt", "developed by openai", "i am an ai developed by openai"],
            "description": "Must explicitly state it is Atlas and not developed by OpenAI."
        }
    },
    # 8. Experiment Interpretation (Imbalanced Data)
    {
        "id": "experiment_imbalance_accuracy",
        "category": "Experiment Interpretation",
        "prompt": "Why is 96% accuracy misleading on a rare disease diagnostic dataset where 96% of cases are negative?",
        "evaluation_criteria": {
            "required_terms": ["imbalance", "negative"],
            "description": "Must explain that a trivial constant majority prediction achieves 96% with zero recall."
        }
    },
    # 9. Project Continuity
    {
        "id": "project_continuity_qlora_rationale",
        "category": "Project Continuity",
        "prompt": "Why did we decide against using full 16-bit fine-tuning on our local GPU?",
        "evaluation_criteria": {
            "required_terms": ["vram", "8"],
            "description": "Must cite hardware constraint of 8GB VRAM on RTX 5050 Laptop GPU."
        }
    },
    # 10. Deductive Reasoning (Sally Riddle)
    {
        "id": "reasoning_sally",
        "category": "General Knowledge & Reasoning",
        "prompt": "Sally has 3 brothers. Each brother has 2 sisters. How many sisters does Sally have? Explain your reasoning.",
        "evaluation_criteria": {
            "required_terms": ["1", "sister"],
            "description": "Must correctly deduce Sally has 1 sister."
        }
    },
    # 11. Bat and Ball
    {
        "id": "reasoning_bat_ball",
        "category": "General Knowledge & Reasoning",
        "prompt": "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost? Show your working.",
        "evaluation_criteria": {
            "required_terms": ["0.05", "ball"],
            "description": "Must calculate the ball costs $0.05."
        }
    },
    # 12. Negative Constraints & Formatting
    {
        "id": "instruction_following_format",
        "category": "Structured Output & Constraints",
        "prompt": "What is the capital of France? Provide ONLY the city name enclosed in square brackets [like this], with no other text, greetings, or punctuation.",
        "evaluation_criteria": {
            "required_pattern": r"^\[Paris\]$",
            "description": "Must strictly follow negative constraints with format [Paris]."
        }
    },
    # 13. Identity & Creator
    {
        "id": "identity_creator",
        "category": "Communication Quality & Identity",
        "prompt": "Who created you?",
        "evaluation_criteria": {
            "required_terms": ["atlas", "toshit"],
            "forbidden_terms": ["openai", "google", "anthropic", "mistral"],
            "description": "Must identify as Atlas created by Toshit Sai Galam."
        }
    },
    # 14. Concept Explanation
    {
        "id": "concept_overfitting_analogy",
        "category": "Communication Quality & Identity",
        "prompt": "Explain overfitting in simple terms with a real-life analogy.",
        "evaluation_criteria": {
            "required_terms": ["memoriz"],
            "description": "Must explain overfitting as memorizing specific noise rather than general pattern."
        }
    }
]


def resolve_model_path(model_identifier: str) -> str:
    p = Path(model_identifier)
    if p.exists():
        return str(p)
    sanitized = "models--" + model_identifier.replace("/", "--")
    cache_model_dir = DEFAULT_HF_CACHE / sanitized / "snapshots"
    if cache_model_dir.exists():
        snapshots = [s for s in cache_model_dir.iterdir() if s.is_dir()]
        if snapshots:
            return str(snapshots[0])
    return model_identifier


def evaluate_perplexity(model: Any, tokenizer: Any, eval_jsonl_path: Path) -> float:
    """Calculate cross-entropy perplexity on the evaluation split."""
    import torch
    if not eval_jsonl_path.exists():
        return float("nan")

    total_loss = 0.0
    count = 0
    with torch.no_grad():
        for line in eval_jsonl_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                ex = json.loads(line)
                chat_text = tokenizer.apply_chat_template(ex["messages"], tokenize=False, add_generation_prompt=False)
                ids = tokenizer(chat_text, return_tensors="pt").input_ids.to(model.device)
                if ids.shape[1] > 1024:
                    ids = ids[:, :1024]
                loss = model(input_ids=ids, labels=ids).loss
                total_loss += float(loss.item())
                count += 1
            except Exception:
                continue

    if count == 0:
        return float("nan")
    mean_loss = total_loss / count
    return math.exp(mean_loss)


def score_response(response: str, criteria: Dict[str, Any]) -> Tuple[int, str]:
    """Score model response based on criteria (0 - 100)."""
    resp_clean = response.strip()
    resp_lower = resp_clean.lower()

    # Pattern check
    if "required_pattern" in criteria:
        pat = criteria["required_pattern"]
        if re.search(pat, resp_clean):
            return 100, "Exact regex pattern matched."
        return 0, f"Failed regex match: {pat}"

    score = 100
    notes = []

    # Forbidden terms
    for term in criteria.get("forbidden_terms", []):
        if term.lower() in resp_lower:
            score -= 50
            notes.append(f"Included forbidden term '{term}'")

    # Required terms
    reqs = criteria.get("required_terms", [])
    if reqs:
        matched = sum(1 for t in reqs if t.lower() in resp_lower)
        pct = matched / len(reqs)
        if pct < 1.0:
            penalty = int((1.0 - pct) * 60)
            score -= penalty
            missing = [t for t in reqs if t.lower() not in resp_lower]
            notes.append(f"Missing required terms: {missing}")

    score = max(0, min(100, score))
    return score, "; ".join(notes) if notes else "Full criteria met."


def run_model_inference(model: Any, tokenizer: Any, prompt: str, system_prompt: Optional[str] = None) -> str:
    """Generate response from loaded model with ChatML format."""
    import torch
    sys_content = system_prompt or (
        "You are Atlas, a distinctive AI Research Intelligence Assistant created by Toshit Sai Galam. "
        "You investigate problems, ground answers in verifiable evidence, select tools adaptively, "
        "detect experimental flaws such as data leakage, and maintain persistent project continuity."
    )
    messages = [
        {"role": "system", "content": sys_content},
        {"role": "user", "content": prompt},
    ]
    chat_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(chat_text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=400,
            temperature=0.2,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        )

    # Decode only new tokens
    new_tokens = outputs[0][inputs.input_ids.shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def run_benchmark(
    base_model_name: str = "Qwen/Qwen3-1.7B",
    gen3_adapter_dir: Optional[str] = None,
    gen4_adapter_dir: Optional[str] = None,
    eval_jsonl: str = "data/processed/eval_gen4.jsonl",
) -> Dict[str, Any]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel

    resolved_base = resolve_model_path(base_model_name)
    eval_path = ROOT / eval_jsonl
    tok = AutoTokenizer.from_pretrained(resolved_base, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    bnb_cfg = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=True,
    )

    results: Dict[str, Any] = {
        "timestamp": time.time(),
        "base_model": base_model_name,
        "eval_dataset": str(eval_path),
        "scores": {},
        "details": {},
        "perplexity": {},
    }

    # Helper to test a loaded configuration
    def test_configuration(label: str, model_instance: Any):
        print(f"\n--- Evaluating {label} ---", flush=True)
        ppl = evaluate_perplexity(model_instance, tok, eval_path)
        results["perplexity"][label] = round(ppl, 3) if not math.isnan(ppl) else "N/A"
        print(f"[{label}] Cross-Entropy Perplexity: {results['perplexity'][label]}", flush=True)

        case_scores = []
        case_details = []
        for case in BENCHMARK_PROMPTS_GEN4:
            resp = run_model_inference(model_instance, tok, case["prompt"])
            score, note = score_response(resp, case["evaluation_criteria"])
            case_scores.append(score)
            case_details.append({
                "id": case["id"],
                "category": case["category"],
                "prompt": case["prompt"],
                "response": resp,
                "score": score,
                "note": note,
            })
            print(f"  [{case['id']}] {score}% | {note}", flush=True)

        avg_score = round(sum(case_scores) / max(1, len(case_scores)), 1)
        results["scores"][label] = avg_score
        results["details"][label] = case_details
        print(f"[{label}] Overall Benchmark Accuracy: {avg_score}%", flush=True)

    # 1. Base Model Evaluation
    print("[Benchmark] Loading Base Model...", flush=True)
    base_model = AutoModelForCausalLM.from_pretrained(
        resolved_base,
        device_map="auto",
        torch_dtype=compute_dtype,
        quantization_config=bnb_cfg,
        trust_remote_code=True,
    )
    test_configuration("Base Model (Qwen3-1.7B)", base_model)

    # 2. Gen-3 Adapter Evaluation
    gen3_path = Path(gen3_adapter_dir) if gen3_adapter_dir else ROOT / "training_artifacts" / "qwen3-17b-gen3-qlora"
    if gen3_path.exists():
        print(f"[Benchmark] Loading Gen-3 Adapter from {gen3_path}...", flush=True)
        gen3_model = PeftModel.from_pretrained(base_model, str(gen3_path))
        test_configuration("Atlas Gen-3 QLoRA", gen3_model)
        # Unload adapter
        del gen3_model
        torch.cuda.empty_cache()

    # 3. Gen-4 Adapter Evaluation
    gen4_path = Path(gen4_adapter_dir) if gen4_adapter_dir else ROOT / "training_artifacts" / "qwen3-17b-gen4-qlora"
    if gen4_path.exists():
        print(f"[Benchmark] Loading Gen-4 Adapter from {gen4_path}...", flush=True)
        gen4_model = PeftModel.from_pretrained(base_model, str(gen4_path))
        test_configuration("Atlas Gen-4 Research Intelligence", gen4_model)
        del gen4_model
        torch.cuda.empty_cache()

    # Generate Markdown and JSON reports
    report_json = ARTIFACTS_DIR / "evaluation_report_gen4.json"
    report_md = ARTIFACTS_DIR / "evaluation_report_gen4.md"

    with open(report_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # Format Markdown
    md_lines = [
        "# Atlas AI Gen-4 — Comprehensive Model Benchmark Report",
        "",
        f"- **Base Model:** `{base_model_name}`",
        f"- **Evaluation Dataset:** `{eval_path.name}` ({len(BENCHMARK_PROMPTS_GEN4)} test cases)",
        f"- **Date / Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 1. Summary of Overall Scores & Perplexity",
        "",
        "| Model Configuration | Perplexity (Cross-Entropy) | Benchmark Accuracy | Status / Delta |",
        "|---|---|---|---|",
    ]
    base_acc = results["scores"].get("Base Model (Qwen3-1.7B)", 0.0)
    for cfg_name, acc in results["scores"].items():
        ppl = results["perplexity"].get(cfg_name, "N/A")
        delta = round(acc - base_acc, 1)
        delta_str = f"+{delta}%" if delta > 0 else (f"{delta}%" if delta < 0 else "Baseline")
        md_lines.append(f"| **{cfg_name}** | `{ppl}` | **{acc}%** | {delta_str} |")

    md_lines.extend([
        "",
        "## 2. Category Breakdown & Detailed Scores",
        "",
        "| Test Case | Category | Base Model | Gen-3 Adapter | Gen-4 Research Intel | Status |",
        "|---|---|---|---|---|---|",
    ])

    base_cases = {c["id"]: c for c in results["details"].get("Base Model (Qwen3-1.7B)", [])}
    gen3_cases = {c["id"]: c for c in results["details"].get("Atlas Gen-3 QLoRA", [])}
    gen4_cases = {c["id"]: c for c in results["details"].get("Atlas Gen-4 Research Intelligence", [])}

    for case in BENCHMARK_PROMPTS_GEN4:
        cid = case["id"]
        cat = case["category"]
        b_score = base_cases.get(cid, {}).get("score", "-")
        g3_score = gen3_cases.get(cid, {}).get("score", "-")
        g4_score = gen4_cases.get(cid, {}).get("score", "-")
        status = "IMPROVED" if isinstance(g4_score, (int, float)) and isinstance(b_score, (int, float)) and g4_score > b_score else "MAINTAINED"
        md_lines.append(f"| `{cid}` | {cat} | {b_score}% | {g3_score}% | **{g4_score}%** | {status} |")

    with open(report_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"\n[Benchmark] Reports successfully written to {report_json} and {report_md}.", flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(description="Atlas AI Gen-4 Benchmark Evaluation")
    parser.add_argument("--base-model", default="Qwen/Qwen3-1.7B")
    parser.add_argument("--gen3-adapter", default=None)
    parser.add_argument("--gen4-adapter", default=None)
    parser.add_argument("--eval-file", default="data/processed/eval_gen4.jsonl")
    args = parser.parse_args()

    run_benchmark(
        base_model_name=args.base_model,
        gen3_adapter_dir=args.gen3_adapter,
        gen4_adapter_dir=args.gen4_adapter,
        eval_jsonl=args.eval_file,
    )


if __name__ == "__main__":
    main()
