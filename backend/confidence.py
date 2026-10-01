"""Evidence-aware uncertainty metadata for AI Scientist responses.

This module intentionally does not use LLM self-reported probabilities.  Its
levels are explainable communication categories derived from execution facts:
retrieval, source count, tool use, experiment records, ambiguity and whether a
statement is a proposal.  They are heuristic estimates until evaluated against
held-out, expert-labelled examples.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

_SUBSTANTIVE = {"EXPLANATION", "REASONING", "MATHEMATICS", "CALCULATION", "CODING", "DATA_ANALYSIS", "DOCUMENT_ANALYSIS", "CURRENT_INFORMATION", "WEB_SEARCH", "DEEP_RESEARCH", "RESEARCH_START", "ENTITY_INFORMATION"}
_ML_PERSONAL = re.compile(r"\b(?:my|your|best|will|should|improve|outperform|fraud|churn|smote|dataset|model)\b", re.I)
_HYPOTHESIS = re.compile(r"\b(?:hypothesis|could|may|might|propose|suggest(?:ed|ion)?)\b", re.I)
_AMBIGUOUS = re.compile(r"\b(?:best|right model|improve|optimi[sz]e)\b", re.I)


def _sources(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [s for s in (result.get("sources") or []) if isinstance(s, dict) and s.get("url")]


def _claim_text(answer: str) -> str:
    # A concise, user-visible claim reference; never hidden reasoning.
    sentence = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", answer).strip())[0] if answer else ""
    return sentence[:280] or "The response"


def assess_confidence(question: str, result: Dict[str, Any]) -> Dict[str, Any] | None:
    """Return safe, structured confidence metadata for one completed response."""
    intent = str(result.get("intent") or "").upper()
    answer = str(result.get("response") or "").strip()
    if not answer or intent not in _SUBSTANTIVE:
        return None

    sources = _sources(result)
    activity = result.get("activity") or []
    executed = [a for a in activity if isinstance(a, dict) and str(a.get("stage", "")).upper() in {"EXPERIMENT_EXEC", "EXPERIMENT", "SANDBOXED_EXECUTION"} and str(a.get("status", "")).lower() in {"completed", "complete"}]
    is_research = intent in {"DEEP_RESEARCH", "WEB_SEARCH", "CURRENT_INFORMATION"}
    is_math = intent in {"MATHEMATICS", "CALCULATION"}
    personal_ml = bool(_ML_PERSONAL.search(question))
    hypothesis = bool(_HYPOTHESIS.search(answer)) and not executed

    level, basis, verification = "high", ["well-established general knowledge"], None
    if executed:
        level = "high"
        basis = ["an experiment was recorded as completed", "the result is distinguished from a proposal"]
        verification = "Inspect the recorded experiment configuration and repeat the evaluation on a fresh split."
    elif is_research:
        if len(sources) >= 3:
            level = "high"
            basis = [f"directly supported by {len(sources)} retrieved sources", "no experiment is implied"]
        elif sources:
            level = "medium"
            basis = [f"supported by only {len(sources)} retrieved source(s)", "evidence coverage is limited"]
            verification = "Open the cited primary sources and compare their methods and dates."
        else:
            level = "low"
            basis = ["no verified source was retrieved", "a current or research claim cannot be established from model knowledge alone"]
            verification = "Check a current primary or official source before relying on this conclusion."
    elif is_math:
        level = "high"
        basis = ["the response uses the deterministic mathematics path"]
        verification = "Recalculate independently from the displayed equation."
    elif personal_ml or _AMBIGUOUS.search(question):
        level = "medium"
        basis = ["the recommendation depends on data and validation details that were not provided", "no experiment was run on the user's dataset"]
        verification = "Run a leakage-safe comparison with an appropriate validation split and metric."

    claim: Dict[str, Any] = {
        "text": _claim_text(answer),
        "level": level,
        "basis": basis,
        "kind": "result" if executed else "hypothesis" if hypothesis else "source_supported" if sources else "general_knowledge",
    }
    if hypothesis:
        claim["status"] = "proposed"
        claim.pop("level", None)
        claim["basis"] = ["This is a testable proposal, not an established result."]

    confidence: Dict[str, Any] = {
        "overall": {"level": level, "band": {"high": "~90%+", "medium": "~60-90%", "low": "<60%"}[level]},
        "claims": [claim],
        "basis": basis,
        "verification": [verification] if verification else [],
        "heuristic": True,
        "evidence": {"sources_used": len(sources), "tool_verified": is_math, "experiment_ids": result.get("experimentIds") or []},
    }
    if level == "low":
        confidence["unknown"] = "I don't have enough verified evidence to establish this confidently."
    return confidence
