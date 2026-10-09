"""Canonical question -> answer pipeline primitives.

This module deliberately contains no HTTP, UI, auth, or persistence code.  It
provides the stable contract used by the API boundary while the established
intent/research/model implementations remain the execution engines.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


MODES = {"NORMAL", "WEB_SEARCH", "DEEP_RESEARCH", "ML_RESEARCH", "EXPERIMENT"}


def normalize_question(value: Any) -> str:
    """Normalize transport noise without changing the user's meaning."""
    if value is None:
        return ""
    # Keep newlines meaningful for code/questions, only collapse whitespace
    # created by the transport layer.
    return re.sub(r"[ \t\r\f\v]+", " ", str(value)).strip()


def build_context(
    current_message: str,
    history: Iterable[Mapping[str, Any]] | None = None,
    *,
    research_context: Mapping[str, Any] | None = None,
    tool_results: Iterable[Mapping[str, Any]] | None = None,
    experiment_results: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create explicit, isolated context buckets for one request."""
    clean_history = []
    for item in history or []:
        if not isinstance(item, Mapping):
            continue
        role = str(item.get("role") or "").lower()
        content = normalize_question(item.get("content"))
        if role in {"user", "assistant", "system"} and content:
            clean_history.append({"role": role, "content": content})
    return {
        "current_message": normalize_question(current_message),
        "conversation_history": clean_history[-20:],
        "research_context": dict(research_context or {}),
        "tool_results": list(tool_results or []),
        "experiment_results": list(experiment_results or []),
    }


def classify_mode(message: str, research_route: Mapping[str, Any] | None = None) -> str:
    """Map the authoritative three-way route to the public execution mode."""
    text = normalize_question(message).lower()
    if re.search(r"\b(?:compare|benchmark|experiment(?:ally)?|ablation|test whether|run experiments?)\b", text):
        if re.search(r"\b(?:model|xgboost|lightgbm|catboost|random forest|fraud|churn|classifier|regressor)\b", text):
            return "EXPERIMENT"
    if re.search(r"\b(?:train|build)\s+(?:a|an|the)\s+(?:model|classifier|regressor|pipeline)\b", text):
        return "ML_RESEARCH"
    route = str((research_route or {}).get("mode") or "normal").lower()
    return {"deep_research": "DEEP_RESEARCH", "web_search": "WEB_SEARCH"}.get(route, "NORMAL")


def validate_response(
    answer: Any,
    *,
    question: str,
    history: Iterable[Mapping[str, Any]] | None = None,
    mode: str = "NORMAL",
    citations: Any = None,
) -> dict[str, Any]:
    """Validate the generated result and return a renderer-safe contract."""
    text = normalize_question(answer)
    if not text:
        raise ValueError("Model returned an empty answer")
    normalized_mode = mode if mode in MODES else "NORMAL"
    previous = {
        normalize_question(item.get("content"))
        for item in (history or [])
        if isinstance(item, Mapping) and str(item.get("role")) == "assistant"
    }
    # A response equal to a previous turn is almost always the old-buffer
    # regression; reject it rather than silently displaying stale content.
    # Exclude short fallbacks, greetings, and system messages to avoid false positives.
    if text in previous and normalize_question(question) not in previous:
        if len(text) > 150 and not text.startswith(("I'm Atlas", "Hello", "Here are", "I couldn't", "A sensible first step", "Understood")):
            raise ValueError("Model returned a stale previous response")
    return {
        "answer": text,
        "mode": normalized_mode,
        "evidence": list(citations or []) if isinstance(citations, (list, tuple)) else [],
        "citations": list(citations or []) if isinstance(citations, (list, tuple)) else [],
        "validated": True,
    }


def structured_response(
    result: Mapping[str, Any], *, question: str, history: Iterable[Mapping[str, Any]] | None = None,
    mode: str = "NORMAL", citations: Any = None,
) -> dict[str, Any]:
    """Attach the canonical answer contract without dropping legacy fields."""
    contract = validate_response(result.get("response") or result.get("answer"), question=question,
                                 history=history, mode=mode,
                                 citations=citations if citations is not None else result.get("sources"))
    merged = dict(result)
    merged.update(contract)
    # Existing clients consume ``response``; keep it byte-for-byte identical.
    merged["response"] = contract["answer"]
    return merged

