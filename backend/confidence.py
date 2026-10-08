"""Auditable evidence scoring for completed answers."""
from __future__ import annotations
import re
from urllib.parse import urlparse
from typing import Any, Dict, List

_SUBSTANTIVE = {"EXPLANATION", "REASONING", "MATHEMATICS", "CALCULATION", "CODING", "DATA_ANALYSIS", "DOCUMENT_ANALYSIS", "CURRENT_INFORMATION", "WEB_SEARCH", "DEEP_RESEARCH", "RESEARCH_START", "ENTITY_INFORMATION"}
_DATASET = re.compile(r"\b(?:my|your|dataset|fraud|churn|model|improve|outperform)\b", re.I)

def _domain(source: Dict[str, Any]) -> str:
    return str(source.get("domain") or urlparse(str(source.get("url") or "")).netloc).lower().removeprefix("www.")

def _quality(source: Dict[str, Any]) -> float:
    tier = str(source.get("tier") or source.get("quality") or source.get("type") or "").lower()
    if source.get("peer_reviewed") or source.get("academic") or source.get("official") or any(x in tier for x in ("peer", "academic", "official")): return 1.0
    if any(x in tier for x in ("encyclopedia", "news", "organization", "reputable")): return 0.7
    if any(x in tier for x in ("blog", "general", "web")): return 0.4
    return 0.2

def calculate_evidence_score(sources: List[Dict[str, Any]], claims: List[Dict[str, Any]] | None = None, verification: Dict[str, Any] | None = None, dataset_specific: bool = False, experiment_run: bool = False) -> Dict[str, Any] | None:
    sources = [s for s in sources if isinstance(s, dict) and _domain(s)]
    verification = verification or {}
    if not sources or not claims or not verification.get("available"): return None
    domains = {_domain(s) for s in sources}
    coverage = min(len(domains) / 6, 1.0)
    quality = sum(_quality(s) for s in sources) / len(sources)
    agreement = sum(1 for c in claims if len(c.get("supporting_sources") or []) >= 2) / len(claims)
    verified = sum(1 for c in claims if c.get("verified") is True) / len(claims)
    relevant = sum(1 for s in sources if float(s.get("relevance_score", 0) or 0) >= 0.6 and not s.get("is_stale", False)) / len(sources)
    raw = 100 * (0.20 * coverage + 0.20 * quality + 0.25 * agreement + 0.25 * verified + 0.10 * relevant)
    caps = []
    if len(domains) < 3: caps.append({"reason": "fewer_than_3_independent_sources", "maximum": 50})
    if verification.get("failed"): caps.append({"reason": "verification_failed", "maximum": 60})
    if dataset_specific and not experiment_run: caps.append({"reason": "dataset_claim_without_experiment", "maximum": 70})
    score = min([raw] + [c["maximum"] for c in caps])
    level = "High" if score >= 70 else "Moderate" if score >= 40 else "Low"
    return {"score": round(score, 1), "percentage": round(score), "level": level, "components": {"source_coverage": round(coverage, 4), "source_quality": round(quality, 4), "agreement": round(agreement, 4), "claim_verification": round(verified, 4), "relevance_recency": round(relevant, 4)}, "caps": caps}

def assess_confidence(question: str, result: Dict[str, Any]) -> Dict[str, Any] | None:
    intent, answer = str(result.get("intent") or "").upper(), str(result.get("response") or "").strip()
    if not answer or intent not in _SUBSTANTIVE: return None
    sources = [s for s in (result.get("sources") or []) if isinstance(s, dict)]
    score = calculate_evidence_score(sources, result.get("claims"), result.get("verification"), bool(_DATASET.search(question)), bool(result.get("experimentIds")))
    level = score["level"] if score else ("Moderate" if sources else "Unavailable")
    confidence = {"overall": {"level": level}, "basis": ["Calculated from source coverage, quality, agreement, verification, and relevance/recency."] if score else ["A numeric score is unavailable because source claims or verification records were not provided."], "verification": [], "evidence": {"sources_used": len(sources), "tool_verified": bool(result.get("verification", {}).get("available")), "experiment_ids": result.get("experimentIds") or []}, "claims": result.get("claims") or []}
    if score:
        confidence["overall"].update({"score": score["score"] / 100, "percentage": score["percentage"], "band": level.lower()})
        confidence["components"], confidence["caps"] = score["components"], score["caps"]
    else: confidence["unknown"] = "A numeric score is unavailable because the independent claim-verification record is missing."
    return confidence
