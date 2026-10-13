"""Distill research-assistant demonstrations from DeepSeek via its OpenAI API."""
from __future__ import annotations
import argparse, datetime as dt, json, os, random, re, time, urllib.request
from pathlib import Path

CATEGORIES = {
    "literature review": ["Compare recent methods for", "Find limitations in work on", "Plan a literature review about", "Synthesize competing findings on", "Identify open questions in", "Suggest search terms for", "Evaluate evidence quality for", "Contrast theoretical views on", "Map the main subtopics of", "Design inclusion criteria for", "Explain how citations support", "Separate foundational from recent work on", "Find likely confounders in studies of", "Assess reproducibility in", "Create an annotated bibliography plan for"],
    "methodology": ["Choose a study design for", "Explain threats to validity in", "Recommend controls for", "Describe an ablation plan for", "Suggest a preregistration for", "Compare qualitative and quantitative methods for", "Design a replication of", "Explain sampling decisions for", "Select a measurement protocol for", "Identify bias risks in", "Propose an observational design for", "Explain blinding and randomization for", "Plan missing-data handling for", "Recommend a baseline for", "Review ethical issues in"],
    "experiment design": ["Design an experiment testing", "Define hypotheses for", "Choose metrics for", "Plan a hyperparameter study for", "Estimate sample size for", "Create a train-validation-test split for", "Design a robustness check for", "Plan error analysis for", "Choose a benchmark for", "Explain power analysis for", "Design a multi-seed evaluation of", "Plan a fair comparison between", "Recommend a stopping rule for", "Create a reproducibility checklist for", "Interpret an unexpected result in"],
    "paper summarization": ["Summarize the contributions of", "Explain the theorem in", "Extract assumptions from", "Describe the method in", "Explain the experiments in", "List limitations of", "Translate the abstract of", "Compare the introduction and conclusion of", "Identify the novelty of", "Explain a figure from", "Turn a paper into study notes about", "Review the evidence in", "Summarize a paper for a beginner about", "Check whether claims follow from", "Create discussion questions for"],
    "ML implementation": ["Implement a PyTorch baseline for", "Debug a data-loader issue in", "Explain batching for", "Optimize memory when training", "Choose an embedding model for", "Write pseudocode for", "Explain attention in", "Add evaluation metrics to", "Handle class imbalance in", "Design a feature pipeline for", "Use cross-validation with", "Explain mixed precision for", "Diagnose overfitting in", "Refactor an inference service for", "Write tests for"],
    "statistics": ["Interpret a confidence interval for", "Choose a statistical test for", "Explain Bayesian updating for", "Calculate an effect size for", "Assess multiple comparisons in", "Explain statistical power for", "Interpret a regression coefficient in", "Check assumptions of", "Explain bootstrap uncertainty for", "Compare mean and median for", "Design a causal analysis of", "Interpret a p-value for", "Explain calibration of", "Detect leakage in", "Report uncertainty for"],
    "academic writing": ["Rewrite a research question about", "Draft an abstract about", "Improve the clarity of a methods section on", "Outline a discussion for", "Write a limitations paragraph about", "Create a precise hypothesis about", "Edit a claim to avoid overstatement about", "Draft a peer-review response about", "Write a related-work paragraph on", "Structure a results section for", "Suggest a paper title about", "Turn notes into an introduction about", "Write a reproducibility statement for", "Create a figure caption for", "Explain a result without causal overclaiming about"],
    "research communication": ["Prepare a conference poster outline about", "Explain a result to a nontechnical audience about", "Create a lab meeting agenda for", "Write reviewer questions about", "Draft a data availability note for", "Plan a replication briefing on", "Turn an experiment into a tutorial about", "Create a glossary for", "Write a responsible disclosure for", "Prepare a grant significance paragraph about", "Draft a research blog outline on", "Explain uncertainty to stakeholders about", "Make a checklist for sharing", "Create oral-exam questions about", "Plan a workshop exercise on"],
}
TOPICS = ["retrieval-augmented generation", "small language models", "medical image classification", "graph neural networks", "climate forecasting", "privacy-preserving ML", "long-context evaluation", "causal inference", "dataset shift", "calibration", "federated learning", "multimodal agents", "reinforcement learning", "synthetic data", "scientific foundation models"]

def starter_prompts() -> list[str]:
    return [f"{prefix} {topic}. Give a careful, evidence-aware answer." for category, prefixes in CATEGORIES.items() for prefix, topic in zip(prefixes, TOPICS)]

def load_prompts(path: str | None) -> list[str]:
    p = Path(path) if path else Path("data/distill_prompts.txt")
    values = p.read_text(encoding="utf-8").splitlines() if p.exists() else starter_prompts()
    out, seen = [], set()
    for value in values:
        key = re.sub(r"\W+", " ", value.lower()).strip()
        if len(key.split()) >= 4 and key not in seen: seen.add(key); out.append(value.strip())
    return out

def call(prompt: str, key: str, model: str, timeout: int = 90) -> tuple[str, str, int]:
    body = json.dumps({"model": model, "temperature": .4, "messages": [{"role": "system", "content": "You are a careful research assistant. Provide a concise private reasoning trace, then a well-supported final answer. Do not invent sources."}, {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.deepseek.com/chat/completions", data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8")); msg = data["choices"][0]["message"]; usage = data.get("usage", {})
    return str(msg.get("reasoning_content") or ""), str(msg.get("content") or ""), int(usage.get("completion_tokens", 0))

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--prompts", default=None); ap.add_argument("--output", default=None); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--max-output-tokens", type=int, default=8_000_000); ap.add_argument("--budget-usd", type=float, default=25); ap.add_argument("--delay", type=float, default=1.0); args = ap.parse_args()
    prompts = load_prompts(args.prompts); out = Path(args.output or f"data/raw/distilled_{dt.date.today():%Y%m%d}.jsonl"); out.parent.mkdir(parents=True, exist_ok=True)
    estimated_tokens = len(prompts) * 1800; estimated_cost = estimated_tokens / 1_000_000 * (3.96 + 1.32) / 2
    print(f"prompts={len(prompts)} estimated_output_tokens={estimated_tokens} estimated_cost_upper_bound=${estimated_cost:.2f}")
    if args.dry_run: return 0 if estimated_tokens <= args.max_output_tokens and estimated_cost <= args.budget_usd else 1
    key = os.environ.get("DEEPSEEK_API_KEY");
    if not key: print("DEEPSEEK_API_KEY is not configured; use --dry-run or set it in the environment."); return 1
    done = {json.loads(line).get("instruction") for line in out.read_text(encoding="utf-8").splitlines() if line.strip()} if out.exists() else set(); used_tokens = 0; spent = 0.0
    with out.open("a", encoding="utf-8") as handle:
        for index, prompt in enumerate(prompts, 1):
            if prompt in done: continue
            if used_tokens >= args.max_output_tokens or spent >= args.budget_usd: print("budget cap reached; stopping cleanly"); break
            for attempt in range(3):
                try:
                    reasoning, answer, tokens = call(prompt, key, "deepseek-v4-pro"); used_tokens += tokens; spent += tokens / 1_000_000 * 3.96
                    handle.write(json.dumps({"instruction": prompt, "input": "", "output": answer, "reasoning": reasoning}, ensure_ascii=False) + "\n"); handle.flush(); break
                except Exception as exc:
                    if attempt == 2: print(f"prompt {index} failed: {type(exc).__name__}")
                    else: time.sleep(2 ** attempt + random.random())
            if index % 50 == 0: print(f"progress={index}/{len(prompts)} output_tokens={used_tokens} spend_estimate=${spent:.2f}")
            time.sleep(args.delay)
    return 0
if __name__ == "__main__": raise SystemExit(main())
