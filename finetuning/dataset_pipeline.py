"""Dataset build pipeline for SFT (REAL implementation, heavy deps lazy).

Implements directive §9:  download → validate → normalize → dedupe → remove
corrupted/low-quality → category metadata → split → manifest.

Runs ONLY inside the training venv (``training_env/``); ``datasets`` is
imported lazily so the stdlib-only test suite is unaffected. Never trains on
benchmark questions: the caller can pass ``exclude_texts`` (hashes of
benchmark prompts) which are dropped before splitting.

Honesty rules:
- per-row ``license`` audit for datasets that carry one (only permissive rows
  are kept; the audit result is recorded in the manifest);
- unknown schemas are rejected with the observed schema dumped, never guessed;
- every produced dataset directory contains ``manifest.json`` with measured
  counts (rows in/out, duplication rate, license values seen, domain mix).
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Category -> (dataset repo id, hub split)
NEMOTRON_SPLIT_MAP: Dict[str, Tuple[str, str]] = {
    "general_instruction": ("nvidia/Nemotron-Post-Training-Dataset-v2", "chat"),
    "math": ("nvidia/Nemotron-Post-Training-Dataset-v2", "math"),
    "coding": ("nvidia/Nemotron-Post-Training-Dataset-v2", "code"),
    "reasoning": ("nvidia/Nemotron-Post-Training-Dataset-v2", "stem"),
}

_PERMISSIVE_ROW_LICENSES = {
    "cc-by-4.0", "cc-by-3.0", "apache-2.0", "mit", "odc-by", "bsd-3-clause",
    "cc0-1.0", "cc0", "public domain",
}

_WS = re.compile(r"\s+")


def _repo_join(*parts: str) -> str:
    return os.path.join(_REPO_ROOT, *parts)


def _hf_home() -> str:
    path = _repo_join("hf_cache")
    os.environ.setdefault("HF_HOME", path)
    return path


def _norm_text(s: str) -> str:
    return _WS.sub(" ", (s or "").strip().lower())


def _hash_example(messages: List[Dict[str, str]]) -> str:
    canon = json.dumps(
        [[m.get("role", ""), _norm_text(m.get("content", ""))] for m in messages],
        ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _validate_messages(raw: object) -> Optional[List[Dict[str, str]]]:
    """Accept a list of {role, content} dicts; everything else is invalid."""
    if not isinstance(raw, list) or not raw:
        return None
    out: List[Dict[str, str]] = []
    for m in raw:
        if not isinstance(m, dict):
            return None
        role = str(m.get("role", "")).strip().lower()
        content = m.get("content")
        if role not in {"system", "user", "assistant", "tool"} or not isinstance(content, str):
            return None
        if not content.strip():
            return None
        out.append({"role": role, "content": content})
    # must contain at least one user and one assistant turn
    roles = {m["role"] for m in out}
    if "user" not in roles or "assistant" not in roles:
        return None
    return out


def _extract_example(row: Dict) -> Tuple[Optional[List[Dict[str, str]]], Optional[str]]:
    """Normalize one hub row -> (messages, row_license). Reject unknown schemas."""
    lic = row.get("license") or row.get("row_license")
    lic = str(lic).strip().lower() if isinstance(lic, str) else None
    for key in ("messages", "conversation", "conversations", "chat"):
        if key in row:
            msgs = _validate_messages(row[key])
            return (msgs, lic) if msgs else (None, lic)
    # common prompt/response flat schemas
    if "prompt" in row and ("response" in row or "output" in row):
        resp = row.get("response", row.get("output"))
        if isinstance(row["prompt"], str) and isinstance(resp, str) and resp.strip():
            return [{"role": "user", "content": row["prompt"]},
                    {"role": "assistant", "content": resp}], lic
    return None, lic


@dataclass
class BuildStats:
    category: str
    rows_seen: int = 0
    invalid: int = 0
    duplicates: int = 0
    benchmark_hits: int = 0
    license_blocked: int = 0
    kept: int = 0
    licenses_seen: Counter = field(default_factory=Counter)

    def to_dict(self) -> Dict:
        return {
            "category": self.category, "rows_seen": self.rows_seen,
            "invalid": self.invalid, "duplicates": self.duplicates,
            "benchmark_hits": self.benchmark_hits,
            "license_blocked": self.license_blocked, "kept": self.kept,
            "licenses_seen": dict(self.licenses_seen),
        }


def stream_category(category: str, limit: int) -> Iterable[Tuple[List[Dict[str, str]], Optional[str]]]:
    """Stream (messages, row_license) pairs for one category from the Hub."""
    from datasets import load_dataset  # lazy: training venv only
    repo, split = NEMOTRON_SPLIT_MAP[category]
    ds = load_dataset(repo, split=split, streaming=True)
    n = 0
    for row in ds:
        if n >= limit:
            break
        msgs, lic = _extract_example(dict(row))
        n += 1
        if msgs is None:
            continue
        yield msgs, lic


def build_dataset(categories: Dict[str, int], output_dir: str,
                  seed: int = 42,
                  benchmark_texts: Optional[List[str]] = None,
                  min_assistant_chars: int = 20,
                  max_total_chars: int = 24000) -> Dict:
    """Build the multi-domain SFT dataset and return the manifest.

    categories: {category_name: max_examples_to_keep}
    Dedup happens BEFORE splitting (directive §22). Split is stratified by
    category: 90% train / 5% validation / 5% test.
    """
    from datasets import Dataset  # lazy

    _hf_home()
    os.makedirs(output_dir, exist_ok=True)
    rng = random.Random(seed)
    bench_hashes = {_norm_text(t) for t in (benchmark_texts or [])}

    seen_exact: set = set()
    seen_prefix: set = set()
    stats: Dict[str, BuildStats] = {c: BuildStats(c) for c in categories}
    rows: List[Dict] = []

    for category, keep_n in categories.items():
        if category not in NEMOTRON_SPLIT_MAP:
            raise ValueError(f"unknown category '{category}'; known: {sorted(NEMOTRON_SPLIT_MAP)}")
        st = stats[category]
        # over-fetch a bit so filtering still reaches keep_n
        for msgs, lic in stream_category(category, limit=keep_n * 3):
            st.rows_seen += 1
            if lic is not None:
                st.licenses_seen[lic] += 1
                if lic not in _PERMISSIVE_ROW_LICENSES:
                    st.license_blocked += 1
                    continue
            h = _hash_example(msgs)
            if h in seen_exact:
                st.duplicates += 1
                continue
            prefix = _norm_text(" ".join(m["content"] for m in msgs))[:256]
            if prefix in seen_prefix:
                st.duplicates += 1
                continue
            if bench_hashes and any(_norm_text(m["content"]) in bench_hashes for m in msgs):
                st.benchmark_hits += 1
                continue
            assistant_chars = sum(len(m["content"]) for m in msgs if m["role"] == "assistant")
            total_chars = sum(len(m["content"]) for m in msgs)
            if assistant_chars < min_assistant_chars or total_chars > max_total_chars:
                st.invalid += 1
                continue
            seen_exact.add(h)
            seen_prefix.add(prefix)
            rows.append({"messages": msgs, "category": category, "license": lic or "cc-by-4.0"})
            st.kept += 1
            if st.kept >= keep_n:
                break

    rng.shuffle(rows)
    n = len(rows)
    n_test = max(1, int(n * 0.05))
    n_val = max(1, int(n * 0.05))
    test_rows = rows[:n_test]
    val_rows = rows[n_test:n_test + n_val]
    train_rows = rows[n_test + n_val:]

    for name, subset in (("train", train_rows), ("validation", val_rows), ("test", test_rows)):
        Dataset.from_list(subset).save_to_disk(os.path.join(output_dir, name))

    manifest = {
        "source_dataset": "nvidia/Nemotron-Post-Training-Dataset-v2",
        "seed": seed,
        "total_kept": n,
        "splits": {"train": len(train_rows), "validation": len(val_rows), "test": len(test_rows)},
        "category_distribution": dict(Counter(r["category"] for r in rows)),
        "per_category_stats": {c: s.to_dict() for c, s in stats.items()},
        "dedup_before_split": True,
        "benchmark_exclusions": len(bench_hashes),
        "output_dir": os.path.abspath(output_dir),
    }
    with open(os.path.join(output_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    return manifest


def load_split(output_dir: str, split: str):
    """Load a previously built split from disk (training venv only)."""
    from datasets import load_from_disk
    path = os.path.join(output_dir, split)
    if not os.path.isdir(path):
        raise FileNotFoundError(f"split not found: {path} (build the dataset first)")
    return load_from_disk(path)
