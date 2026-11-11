# Atlas AI — Qwen Fine-Tuning Dataset Preparation Report

## 1. Dataset Discovery & Source Registry

| Dataset Name | Category | License | Format | Quality Rating | Status |
|---|---|---|---|---|---|
| **Atlas Project Identity & Personalization** | Personalization & Project Knowledge | `MIT (Project-Specific)` | JSONL (Multi-turn ChatML & Instruction) | High | `Locally Generated / Verified` |
| **General Instruction & Reasoning (Curated Mini-Hermes)** | General Question Answering & Reasoning | `MIT / Apache-2.0` | JSONL | High | `Curated Local Subset` |
| **Python & Software Engineering Instruction (CodeFeedback Subset)** | Coding & Software Engineering | `Apache-2.0` | JSONL | High | `Curated Local Subset` |
| **Mathematical Reasoning & Step-by-Step Problem Solving (GSM8K & MathInstruct)** | Mathematics & Symbolic Reasoning | `MIT` | JSONL | High | `Curated Local Subset` |
| **Scientific Inquiry & Machine Learning Research (Atlas Research Seed)** | Scientific Inquiry & ML Methodology | `MIT` | JSONL | High | `Locally Generated` |
| **Tool Selection & Structured Function Calling (Hermes Function Calling)** | Tool Selection & Action Execution | `Apache-2.0` | JSONL | High | `Curated Local Subset` |

## 2. Dataset Pipeline Quality & Filtration Statistics

- **Total Raw Samples Ingested:** 22
- **Valid Cleaned Samples:** 22
- **Duplicates Removed:** 0
- **Malformed/Incomplete Removed:** 0
- **Train Set Size:** 19 samples
- **Evaluation Set Size:** 3 samples
- **Data Leakage Overlap:** 0 (Strictly Isolated)

## 3. Category Distribution

- **Identity:** 6 samples (27.3%)
- **Tool Selection:** 4 samples (18.2%)
- **Multi Turn:** 2 samples (9.1%)
- **Coding:** 2 samples (9.1%)
- **Research:** 3 samples (13.6%)
- **Reasoning:** 2 samples (9.1%)
- **Mathematics:** 1 samples (4.5%)
- **Factual:** 2 samples (9.1%)

## 4. Token & Character Length Distribution

- **Average Characters / Turn:** 659.8
- **Average Estimated Tokens:** 173.1
- **Max Estimated Tokens:** 402 (Safely under 1024/2048 context limit)
- **Min Estimated Tokens:** 11

## 5. Artifacts Created

- Train Split: `C:\Users\Toshit\Desktop\Atlas\data\processed\train.jsonl`
- Eval Split: `C:\Users\Toshit\Desktop\Atlas\data\processed\eval.jsonl`
- Machine-Readable Report: `C:\Users\Toshit\Desktop\Atlas\data\dataset_preparation_report.json`
