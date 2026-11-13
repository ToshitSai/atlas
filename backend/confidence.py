"""Auditable evidence scoring for completed answers."""
from __future__ import annotations
import re
import os
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
    if not verification.get("available"): return None
    domains = {_domain(s) for s in sources}
    coverage = min(len(domains) / 6, 1.0)
    quality = sum(_quality(s) for s in sources) / len(sources) if sources else 0.0
    claims = claims or []
    agreement = sum(1 for c in claims if len(c.get("supporting_sources") or []) >= 2) / len(claims) if claims else 0.0
    verified = sum(1 for c in claims if c.get("verified") is True) / len(claims) if claims else 0.0
    relevant = (sum(1 for s in sources if float(s.get("relevance_score", 0) or 0) >= 0.6 and not s.get("is_stale", False)) / len(sources)) if sources else 0.0
    components = [(0.20, coverage), (0.20, quality), (0.10, relevant)]
    if claims:
        components += [(0.25, agreement), (0.25, verified)]
    denominator = sum(weight for weight, _ in components)
    raw = 100 * sum(weight * value for weight, value in components) / denominator
    caps = []
    if len(domains) < 3: caps.append({"reason": "fewer_than_3_independent_sources", "maximum": 50})
    if verification.get("failed"): caps.append({"reason": "verification_failed", "maximum": 60})
    if dataset_specific and not experiment_run: caps.append({"reason": "dataset_claim_without_experiment", "maximum": 70})
    score = min([raw] + [c["maximum"] for c in caps])
    level = "High" if score >= 70 else "Moderate" if score >= 40 else "Low"
    return {"score": round(score, 1), "percentage": round(score), "level": level, "components": {"source_coverage": round(coverage, 4), "source_quality": round(quality, 4), "agreement": round(agreement, 4) if claims else None, "claim_verification": round(verified, 4) if claims else None, "relevance_recency": round(relevant, 4)}, "caps": caps, "claims_applicable": bool(claims)}

def extract_claims(answer: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Conservative factual-claim candidates; skip headings, greetings and opinions."""
    claims = []
    for sentence in re.split(r"(?<=[.!?])\s+", str(answer or "")):
        text = re.sub(r"^[-*#\s]+", "", sentence).strip()
        if len(text.split()) < 5 or text.lower().startswith(("sure", "i think", "in my opinion")):
            continue
        claims.append({"text": text, "supporting_sources": [], "verified": False, "status": "no evidence"})
        if len(claims) >= limit: break
    return claims

def run_evidence_check(answer: str, sources: List[Dict[str, Any]] | None = None, question: str = "") -> Dict[str, Any]:
    """Deterministic evidence pass used after answer delivery; never invents support."""
    sources = [s for s in (sources or []) if isinstance(s, dict)]
    claims = extract_claims(answer)
    if not sources and question:
        try:
            from backend.web_search import search_web
            providers = [name for name, key in (("Tavily", "TAVILY_API_KEY"), ("Serper", "SERPER_API_KEY"), ("Brave", "BRAVE_API_KEY"), ("Scrape.do", "SCRAPE_DO_API_KEY")) if os.environ.get(key)]
            if os.environ.get("ATLAS_ENV", "").lower() in {"dev", "development", "test"}:
                print(f"[CONFIDENCE INPUTS] claims={len(claims)} providers={providers} query={question!r}")
            sources = search_web(question, limit=6) or search_web(" ".join(question.split()[:6]), limit=6)
            sources = [{**s, "tier": s.get("tier") or "general web", "relevance_score": s.get("relevance_score", 0.8)} for s in sources]
            if os.environ.get("ATLAS_ENV", "").lower() in {"dev", "development", "test"}:
                print(f"[CONFIDENCE RETRIEVAL] results={len(sources)} sources={[{'url': s.get('url'), 'status': s.get('status'), 'tier': s.get('tier'), 'date': s.get('publishedAt')} for s in sources]}")
        except Exception as error:
            if os.environ.get("ATLAS_ENV", "").lower() in {"dev", "development", "test"}:
                print(f"[CONFIDENCE SEARCH ERROR] {type(error).__name__}: {error}")
    for claim in claims:
        words = {w.lower() for w in re.findall(r"[a-zA-Z]{4,}", claim["text"])}
        matches = []
        for idx, source in enumerate(sources):
            hay = " ".join(str(source.get(k) or "") for k in ("title", "snippet", "text", "abstract")).lower()
            overlap = len(words & set(re.findall(r"[a-z]{4,}", hay)))
            if overlap >= max(2, min(5, len(words) // 4)):
                matches.append(idx)
        claim["supporting_sources"] = matches
        claim["verified"] = bool(matches)
        claim["status"] = "supported" if len(matches) >= 1 else "no evidence"
    result = {"sources": sources, "claims": claims, "verification": {"available": True, "failed": False}}
    confidence = assess_confidence(question, {"response": answer, "intent": "WEB_SEARCH", **result})
    if confidence is None:
        confidence = {"overall": {"percentage": 0, "level": "Low", "band": "low"}, "basis": ["No sources found to support this answer."], "claims": claims, "components": {"source_coverage": 0, "source_quality": 0, "agreement": 0, "claim_verification": 0, "relevance_recency": 0}, "caps": [{"reason": "fewer_than_3_independent_sources", "maximum": 50}]}
    confidence["claims"] = claims
    unsupported = sum(1 for claim in claims if not claim.get("verified"))
    confidence["basis"] = [f"No sources found for {unsupported} of {len(claims)} claims."] if unsupported else [f"Sources checked for all {len(claims)} extracted claims."]
    confidence["overall"]["level"] = str(confidence["overall"].get("level") or "low").capitalize()
    try:
        from backend.math_verification import verify_math_answer
        math_check = verify_math_answer(question, answer)
        if math_check:
            confidence["math_check"] = math_check
            if math_check.get("status") == "failed":
                confidence.setdefault("caps", []).append({"reason": "math_verification_failed", "maximum": 40})
                confidence["overall"]["percentage"] = min(confidence["overall"].get("percentage", 0), 40)
                confidence["overall"]["level"] = "Moderate" if confidence["overall"]["percentage"] >= 40 else "Low"
    except Exception as error:
        confidence["math_check"] = {"status": "failed", "reason": type(error).__name__}
    return confidence

def assess_confidence(question: str, result: Dict[str, Any]) -> Dict[str, Any] | None:
    intent, answer = str(result.get("intent") or "").upper(), str(result.get("response") or "").strip()
    if not answer or intent not in _SUBSTANTIVE: return None
    sources = [s for s in (result.get("sources") or []) if isinstance(s, dict)]
    math_check = None
    if intent in {"MATHEMATICS", "CALCULATION"}:
        try:
            from backend.math_verification import verify_math_answer
            math_check = verify_math_answer(question, answer)
        except Exception:
            math_check = None
    # Confidence is modality-specific: mathematics and code are checked by
    # deterministic verifiers, while current/research claims use evidence.
    dataset_specific = bool(_DATASET.search(question))
    if not sources and not math_check:
        claims = extract_claims(answer)
        for claim in claims:
            if re.search(r"\bhypothesis\b", claim["text"], re.I):
                claim.update({"kind": "hypothesis", "status": "proposed"})
            else:
                claim.update({"kind": "unsupported", "status": "unverified"})
        is_current = intent in {"CURRENT_INFORMATION", "WEB_SEARCH", "DEEP_RESEARCH"}
        if dataset_specific:
            return {
                "overall": {"score": 0.5, "percentage": 50, "level": "medium", "band": "medium"},
                "verification_status": "not_verified",
                "basis": ["No experiment was run to validate this dataset-specific claim."],
                "verification": [{"status": "not_run", "reason": "no experiment"}],
                "evidence": {"sources_used": 0, "tool_verified": False, "experiment_ids": []},
                "claims": claims,
                "components": {},
                "caps": [{"reason": "dataset_claim_without_experiment", "maximum": 70}],
            }
        if is_current:
            return {
                "overall": {"score": 0.0, "percentage": 0, "level": "low", "band": "low"},
                "verification_status": "not_verified",
                "basis": ["No sources were retrieved for this current-information claim."],
                "verification": [],
                "evidence": {"sources_used": 0, "tool_verified": False, "experiment_ids": []},
                "claims": claims,
                "unknown": True,
                "components": {},
                "caps": [{"reason": "no_sources", "maximum": 0}],
            }
        return {
            "overall": {"score": 0.9, "percentage": 90, "level": "high", "band": "high"},
            "verification_status": "not_required",
            "basis": ["Established explanation; no external sources were required."],
            "verification": [],
            "evidence": {"sources_used": 0, "tool_verified": False, "experiment_ids": []},
            "claims": claims,
            "components": {},
            "caps": [],
        }

    if intent in {"MATHEMATICS", "CALCULATION"} and math_check:
        passed = math_check.get("status") == "passed"
        pct = 90 if passed else 20
        return {"overall": {"score": pct / 100, "percentage": pct,
                             "level": "high" if passed else "low", "band": "high" if passed else "low"},
                "verification_status": "completed",
                "basis": ["Verified with numerical calculation." if passed else "Numerical verification failed."],
                "verification": [math_check], "evidence": {"sources_used": 0, "tool_verified": passed, "experiment_ids": []},
                "components": {"math_verification": 1.0 if passed else 0.0}, "caps": [] if passed else [{"reason": "math_verification_failed", "maximum": 20}],
                "claims": []}

    if not sources:
        return None

    score = calculate_evidence_score(
        sources,
        result.get("claims"),
        result.get("verification") or {"available": True},
        dataset_specific,
        bool(result.get("experimentIds")),
    )
    if not score:
        return None

    level = score["level"].lower()
    if dataset_specific and not result.get("experimentIds"):
        level = "medium"
    elif len(sources) >= 3:
        level = "high"
    claims = extract_claims(answer)
    for claim in claims:
        if re.search(r"\bhypothesis\b", claim["text"], re.I):
            claim.update({"kind": "hypothesis", "status": "proposed"})
        else:
            claim.update({"kind": "source_supported", "status": "supported"})
    confidence = {
        "overall": {"level": level, "score": score["score"] / 100, "percentage": score["percentage"], "band": level.lower()},
        "verification_status": "completed",
        "basis": (["No experiment was run to validate this dataset-specific claim."]
                  if dataset_specific and not result.get("experimentIds") else
                  ["Calculated from source coverage, quality, agreement, verification, and relevance/recency."]),
        "verification": [],
        "evidence": {"sources_used": len(sources), "tool_verified": bool(result.get("verification", {}).get("available")), "experiment_ids": result.get("experimentIds") or []},
        "claims": claims,
        "components": score.get("components"),
        "caps": score.get("caps")
    }
    return confidence
