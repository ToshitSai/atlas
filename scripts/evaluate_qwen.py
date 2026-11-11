"""Atlas AI — Systematic Qwen Base vs Fine-Tuned Benchmark Evaluation.

Measures:
 1. Answer correctness & Factual recall
 2. Instruction following
 3. Hallucination rate (specifically rejecting false creator claims)
 4. Response relevance
 5. Reasoning quality
 6. Coding accuracy
 7. Mathematics accuracy
 8. Multi-turn consistency

Generates:
 - Perplexity comparison on held-out eval set
 - Quantitative accuracy/compliance scores
 - Markdown comparison report: training_artifacts/evaluation_report.md
 - JSON evaluation record: training_artifacts/evaluation_report.json
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HF_CACHE = Path.home() / ".cache" / "huggingface" / "hub"

BENCHMARK_PROMPTS = [
    {
        "id": "identity_creator",
        "category": "Personalization & Identity",
        "prompt": "Who created you?",
        "evaluation_criteria": {
            "required_terms": ["atlas", "toshit"],
            "forbidden_terms": ["openai", "google", "anthropic", "mistral ai"],
            "description": "Must identify as Atlas and creator as Toshit Sai Galam without hallucinating provider identity."
        }
    },
    {
        "id": "identity_openai_check",
        "category": "Hallucination Rejection",
        "prompt": "Are you ChatGPT or developed by OpenAI?",
        "evaluation_criteria": {
            "required_terms": ["not chatgpt", "not developed by openai", "atlas"],
            "forbidden_terms": ["i am chatgpt", "developed by openai", "i am an openai"],
            "description": "Must explicitly clarify it is Atlas and not an OpenAI ChatGPT system."
        }
    },
    {
        "id": "instruction_following_format",
        "category": "Instruction Following",
        "prompt": "What is the capital of France? Provide ONLY the city name enclosed in square brackets [like this], with no other text, greetings, or punctuation.",
        "evaluation_criteria": {
            "required_pattern": r"^\[Paris\]$",
            "description": "Must strictly follow negative constraints and exact formatting."
        }
    },
    {
        "id": "reasoning_sally",
        "category": "Reasoning Quality",
        "prompt": "Sally has 3 brothers. Each brother has 2 sisters. How many sisters does Sally have? Explain your reasoning.",
        "evaluation_criteria": {
            "required_terms": ["1", "sister"],
            "description": "Must correctly deduce Sally has 1 sister because all brothers share the same 2 sisters."
        }
    },
    {
        "id": "mathematics_linear_equation",
        "category": "Mathematics Accuracy",
        "prompt": "Solve for x in the equation: 5x - 7 = 3x + 11. Show step-by-step working.",
        "evaluation_criteria": {
            "required_terms": ["9", "2x = 18", "x = 9"],
            "description": "Must reach x = 9 with correct intermediate algebraic steps."
        }
    },
    {
        "id": "coding_python_fibonacci",
        "category": "Coding Accuracy",
        "prompt": "Write a Python function named fibonacci that uses memoization to return the nth Fibonacci number efficiently.",
        "evaluation_criteria": {
            "required_terms": ["def fibonacci", "lru_cache", "return"],
            "description": "Must provide syntactically valid Python with caching/memoization."
        }
    },
    {
        "id": "factual_python",
        "category": "Factual Accuracy",
        "prompt": "What is Python?",
        "evaluation_criteria": {
            "required_terms": ["programming language", "interpreted", "readable"],
            "description": "Must accurately describe Python's nature and core features."
        }
    },
    {
        "id": "multi_turn_overfitting",
        "category": "Multi-turn Consistency",
        "conversation": [
            {"role": "user", "content": "What is overfitting in machine learning?"},
            {"role": "assistant", "content": "Overfitting happens when a model learns the training data and noise too well, failing to generalize to new, unseen data."},
            {"role": "user", "content": "How can I prevent it in practice?"}
        ],
        "evaluation_criteria": {
            "required_terms": ["regularization", "cross-validation", "early stopping"],
            "description": "Must maintain conversation context and provide relevant mitigation techniques."
        }
    },
    {
        "id": "indian_gk_mahesh_babu",
        "category": "Indian General Knowledge",
        "prompt": "Who is Mahesh Babu?",
        "evaluation_criteria": {
            "required_terms": ["actor", "telugu"],
            "description": "Must accurately identify Mahesh Babu as an Indian actor in Telugu cinema."
        }
    },
    {
        "id": "indian_gk_chandrayaan",
        "category": "Science & Indian Knowledge",
        "prompt": "What was the key achievement of India's Chandrayaan-3 lunar mission?",
        "evaluation_criteria": {
            "required_terms": ["south pole", "landing", "isro"],
            "description": "Must identify ISRO's successful soft landing near the lunar south pole."
        }
    },
    {
        "id": "current_info_admit_uncertainty",
        "category": "Current Information & Uncertainty",
        "prompt": "What is the current live temperature in Mumbai right now?",
        "evaluation_criteria": {
            "required_terms": ["live", "current"],
            "forbidden_terms": ["it is exactly 27 degrees right now"],
            "description": "Must recognize this requires real-time retrieval or meteorological lookup rather than fabricating a live number."
        }
    },
    {
        "id": "geography_capital_australia",
        "category": "Geography & International Knowledge",
        "prompt": "What is the capital city of Australia?",
        "evaluation_criteria": {
            "required_terms": ["canberra"],
            "forbidden_terms": ["sydney is the capital", "melbourne is the capital"],
            "description": "Must correctly identify Canberra as the capital of Australia."
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


def evaluate_perplexity(model: Any, tokenizer: Any, eval_jsonl_path: str) -> float:
    """Calculate cross-entropy perplexity on the evaluation split."""
    import torch
    p = Path(eval_jsonl_path)
    if not p.exists():
        return float("nan")

    total_loss = 0.0
    count = 0
    with torch.no_grad():
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            ex = json.loads(line)
            chat_text = tokenizer.apply_chat_template(ex["messages"], tokenize=False, add_generation_prompt=False)
            ids = tokenizer(chat_text, return_tensors="pt").input_ids.to(model.device)
            loss = model(input_ids=ids, labels=ids).loss
            total_loss += float(loss.item())
            count += 1

    return math.exp(total_loss / count) if count > 0 else float("nan")


def score_response(item: Dict[str, Any], response_text: str) -> Tuple[float, List[str]]:
    """Score model response against criteria (0.0 to 1.0) and note observations."""
    crit = item["evaluation_criteria"]
    notes = []
    score = 1.0
    resp_lower = response_text.lower().strip()

    # Check forbidden terms (e.g. false creator attribution)
    for forbidden in crit.get("forbidden_terms", []):
        if forbidden.lower() in resp_lower:
            score -= 0.5
            notes.append(f"Contains forbidden provider attribution: '{forbidden}'")

    # Check required pattern if specified
    if "required_pattern" in crit:
        if re.search(crit["required_pattern"], response_text.strip()):
            score = 1.0
            notes.append("Strict format pattern matched perfectly")
        else:
            score -= 0.4
            notes.append(f"Format mismatch: expected regex {crit['required_pattern']}")

    # Check required terms
    for req in crit.get("required_terms", []):
        if req.lower() not in resp_lower:
            score -= 0.2
            notes.append(f"Missing expected concept/term: '{req}'")

    final_score = max(0.0, min(1.0, round(score, 2)))
    return final_score, notes


def generate_answer(model: Any, tokenizer: Any, prompt_or_msgs: Any, max_tokens: int = 384) -> str:
    """Run deterministic inference generation."""
    import torch
    if isinstance(prompt_or_msgs, str):
        msgs = [{"role": "user", "content": prompt_or_msgs}]
    else:
        msgs = prompt_or_msgs

    prompt_str = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt_str, return_tensors="pt").to(model.device)

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            do_sample=False,
            temperature=None,
            top_p=None,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        )

    gen_tokens = output[0][inputs.input_ids.shape[-1]:]
    return tokenizer.decode(gen_tokens, skip_special_tokens=True).strip()


def run_evaluation(
    model_name_or_path: str,
    adapter_path: Optional[str] = None,
    eval_jsonl: str = "data/processed/eval.jsonl",
    output_dir: str = "training_artifacts",
) -> Dict[str, Any]:
    """Execute complete benchmark evaluation."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel

    resolved_base = resolve_model_path(model_name_or_path)
    tok = AutoTokenizer.from_pretrained(resolved_base, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=True,
    )

    print(f"\n[Eval] Loading base model: {model_name_or_path}...", flush=True)
    base_model = AutoModelForCausalLM.from_pretrained(
        resolved_base,
        quantization_config=quant,
        device_map="auto",
        trust_remote_code=True,
    )

    # 1. Base Model Evaluation
    print("[Eval] Evaluating Base Model Perplexity...", flush=True)
    base_ppl = evaluate_perplexity(base_model, tok, eval_jsonl)
    print(f"Base Perplexity: {base_ppl:.3f}", flush=True)

    print("[Eval] Running Base Model Benchmark Prompts...", flush=True)
    base_results = []
    base_scores = []
    for item in BENCHMARK_PROMPTS:
        target = item.get("conversation") or item["prompt"]
        ans = generate_answer(base_model, tok, target)
        score, notes = score_response(item, ans)
        base_scores.append(score)
        base_results.append({
            "id": item["id"],
            "category": item["category"],
            "prompt": item.get("prompt") or str(item.get("conversation")),
            "response": ans,
            "score": score,
            "notes": notes,
        })
        print(f" - [{item['category']}] Base Score: {score:.2f}", flush=True)

    avg_base_score = sum(base_scores) / len(base_scores) if base_scores else 0.0

    # 2. Fine-Tuned Model Evaluation (if adapter is provided)
    adapter_results = None
    adapter_ppl = None
    avg_adapter_score = None

    if adapter_path and Path(adapter_path).exists():
        print(f"\n[Eval] Loading LoRA Adapter from {adapter_path}...", flush=True)
        adapter_model = PeftModel.from_pretrained(base_model, adapter_path)
        adapter_model.eval()

        print("[Eval] Evaluating Fine-Tuned Model Perplexity...", flush=True)
        adapter_ppl = evaluate_perplexity(adapter_model, tok, eval_jsonl)
        print(f"Fine-Tuned Perplexity: {adapter_ppl:.3f}", flush=True)

        print("[Eval] Running Fine-Tuned Model Benchmark Prompts...", flush=True)
        adapter_results = []
        adapter_scores = []
        for item in BENCHMARK_PROMPTS:
            target = item.get("conversation") or item["prompt"]
            ans = generate_answer(adapter_model, tok, target)
            score, notes = score_response(item, ans)
            adapter_scores.append(score)
            adapter_results.append({
                "id": item["id"],
                "category": item["category"],
                "prompt": item.get("prompt") or str(item.get("conversation")),
                "response": ans,
                "score": score,
                "notes": notes,
            })
            print(f" - [{item['category']}] Fine-Tuned Score: {score:.2f}", flush=True)

        avg_adapter_score = sum(adapter_scores) / len(adapter_scores) if adapter_scores else 0.0

    # 3. Compile Reports
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    summary_data = {
        "model": model_name_or_path,
        "adapter_path": adapter_path,
        "base_metrics": {
            "eval_perplexity": round(base_ppl, 3) if not math.isnan(base_ppl) else None,
            "average_benchmark_score": round(avg_base_score * 100, 1),
            "results": base_results,
        },
        "finetuned_metrics": {
            "eval_perplexity": round(adapter_ppl, 3) if adapter_ppl is not None and not math.isnan(adapter_ppl) else None,
            "average_benchmark_score": round(avg_adapter_score * 100, 1) if avg_adapter_score is not None else None,
            "results": adapter_results,
        } if adapter_results else None,
    }

    (out_path / "evaluation_report.json").write_text(json.dumps(summary_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Generate Markdown Report
    md = [
        "# Atlas AI — Qwen Fine-Tuning Evaluation Report (Phase 7)",
        "",
        "## 1. Executive Summary",
        "",
        f"- **Base Model:** `{model_name_or_path}`",
        f"- **Adapter:** `{adapter_path or 'None'}`",
        f"- **Base Perplexity:** `{base_ppl:.3f}`",
        f"- **Base Benchmark Accuracy:** `{avg_base_score*100:.1f}%`",
    ]
    if adapter_results:
        ppl_diff = f"{adapter_ppl - base_ppl:+.3f}"
        score_diff = f"{(avg_adapter_score - avg_base_score)*100:+.1f}%"
        md.extend([
            f"- **Fine-Tuned Perplexity:** `{adapter_ppl:.3f}` ({ppl_diff})",
            f"- **Fine-Tuned Benchmark Accuracy:** `{avg_adapter_score*100:.1f}%` ({score_diff})",
        ])

    md.extend([
        "",
        "## 2. Benchmark Scores by Category",
        "",
        "| Test Case | Category | Base Score | Fine-Tuned Score | Status |",
        "|---|---|---|---|---|",
    ])

    for i, item in enumerate(BENCHMARK_PROMPTS):
        b_score = base_results[i]["score"] * 100
        if adapter_results:
            ft_score = adapter_results[i]["score"] * 100
            diff = ft_score - b_score
            status = "IMPROVED" if diff > 0 else ("MAINTAINED" if diff == 0 else "REGRESSED")
            md.append(f"| {item['id']} | {item['category']} | {b_score:.0f}% | {ft_score:.0f}% | {status} ({diff:+.0f}%) |")
        else:
            md.append(f"| {item['id']} | {item['category']} | {b_score:.0f}% | N/A | Evaluated |")

    md.extend([
        "",
        "## 3. Qualitative Response Comparisons",
        "",
    ])

    for i, item in enumerate(BENCHMARK_PROMPTS):
        md.append(f"### {item['id']} ({item['category']})")
        md.append(f"**Prompt:** *\"{item.get('prompt') or 'Multi-turn context'}\"*")
        md.append("")
        md.append(f"**Base Model Response:**\n> {base_results[i]['response'].replace(chr(10), ' ')}")
        md.append("")
        if adapter_results:
            md.append(f"**Fine-Tuned QLoRA Response:**\n> {adapter_results[i]['response'].replace(chr(10), ' ')}")
            md.append("")
        md.append("---")
        md.append("")

    report_md_file = out_path / "evaluation_report.md"
    report_md_file.write_text("\n".join(md), encoding="utf-8")
    print(f"\n[Report] Wrote evaluation report to {report_md_file}", flush=True)

    return summary_data


def main():
    parser = argparse.ArgumentParser(description="Atlas Qwen Model Evaluation Benchmark")
    parser.add_argument("--model", default="Qwen/Qwen3-0.6B", help="Model name or snapshot path")
    parser.add_argument("--adapter", default="training_artifacts/qwen3-06b-qlora", help="Path to adapter folder")
    parser.add_argument("--eval-file", default="data/processed/eval.jsonl", help="Path to eval dataset")
    parser.add_argument("--output-dir", default="training_artifacts", help="Output directory")
    args = parser.parse_args()

    run_evaluation(
        model_name_or_path=args.model,
        adapter_path=args.adapter,
        eval_jsonl=args.eval_file,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
