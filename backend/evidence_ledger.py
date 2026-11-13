"""Atlas AI Gen-4 — Evidence Ledger & Grounding Engine.

Maintains an immutable, inspectable ledger of research findings:
- Distinguishes verified sources, retrieved snippets, model claims, and assumptions
- Tracks explicit verification status and confidence scores
- Identifies and flags contradictory claims across documents/experiments
- Detects knowledge gaps when evidence is missing or insufficient
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


class EvidenceType:
    VERIFIED_DOC = "VERIFIED_DOC"
    WEB_SEARCH = "WEB_SEARCH"
    EXPERIMENT_RECORD = "EXPERIMENT_RECORD"
    MODEL_INFERENCE = "MODEL_INFERENCE"
    ASSUMPTION = "ASSUMPTION"
    UNKNOWN = "UNKNOWN"


class VerificationStatus:
    CONFIRMED = "CONFIRMED"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass
class LedgerClaim:
    id: str
    text: str
    evidence_type: str
    status: str
    source_id: Optional[str] = None
    source_title: Optional[str] = None
    supporting_quote: Optional[str] = None
    contradicting_claim_id: Optional[str] = None
    contradiction_notes: Optional[str] = None
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EvidenceLedger:
    """Session and project-level evidence registry."""

    def __init__(self):
        self._ledgers: Dict[str, List[LedgerClaim]] = {}

    def get_ledger(self, context_id: str) -> List[LedgerClaim]:
        return self._ledgers.setdefault(context_id, [])

    def record_claim(
        self,
        context_id: str,
        text: str,
        evidence_type: str = EvidenceType.MODEL_INFERENCE,
        status: str = VerificationStatus.UNVERIFIED,
        source_id: Optional[str] = None,
        source_title: Optional[str] = None,
        supporting_quote: Optional[str] = None,
        confidence: float = 1.0,
    ) -> LedgerClaim:
        """Register a verifiable claim with its grounding context."""
        claims = self.get_ledger(context_id)
        claim_id = f"claim_{uuid.uuid4().hex[:8]}"
        claim = LedgerClaim(
            id=claim_id,
            text=text,
            evidence_type=evidence_type,
            status=status,
            source_id=source_id,
            source_title=source_title,
            supporting_quote=supporting_quote,
            confidence=confidence,
        )
        claims.append(claim)
        return claim

    def flag_contradiction(
        self,
        context_id: str,
        claim_a_id: str,
        claim_b_id: str,
        explanation: str,
    ) -> bool:
        """Mark two claims in the ledger as contradictory."""
        claims = self.get_ledger(context_id)
        claim_a = next((c for c in claims if c.id == claim_a_id), None)
        claim_b = next((c for c in claims if c.id == claim_b_id), None)

        if not claim_a or not claim_b:
            return False

        claim_a.status = VerificationStatus.CONTRADICTED
        claim_a.contradicting_claim_id = claim_b_id
        claim_a.contradiction_notes = explanation

        claim_b.status = VerificationStatus.CONTRADICTED
        claim_b.contradicting_claim_id = claim_a_id
        claim_b.contradiction_notes = explanation
        return True

    def detect_knowledge_gaps(
        self,
        required_questions: List[str],
        available_claims: List[LedgerClaim],
    ) -> List[Dict[str, Any]]:
        """Identify which core requirements lack verified supporting evidence."""
        gaps: List[Dict[str, Any]] = []
        confirmed_texts = [
            c.text.lower()
            for c in available_claims
            if c.status == VerificationStatus.CONFIRMED or c.evidence_type in (EvidenceType.VERIFIED_DOC, EvidenceType.EXPERIMENT_RECORD)
        ]

        for req in required_questions:
            req_words = set(req.lower().split())
            # Simple lexical overlap check for groundedness
            has_grounding = any(
                len(req_words.intersection(set(txt.split()))) >= max(2, int(len(req_words) * 0.4))
                for txt in confirmed_texts
            )
            if not has_grounding:
                gaps.append({
                    "question": req,
                    "status": "MISSING_EVIDENCE",
                    "action_required": "Initiate focused web search or document retrieval to verify before claiming factuality."
                })

        return gaps

    def format_evidence_summary(self, context_id: str) -> str:
        """Render a concise markdown table of the evidence ledger."""
        claims = self.get_ledger(context_id)
        if not claims:
            return "No evidence recorded in ledger."

        lines = [
            "### 🔗 Evidence Ledger",
            "| Claim | Source / Type | Status | Confidence |",
            "|---|---|---|---|",
        ]
        for c in claims:
            src = c.source_title or c.evidence_type
            status_icon = "✅" if c.status == VerificationStatus.CONFIRMED else ("⚠️" if c.status == VerificationStatus.CONTRADICTED else "ℹ️")
            lines.append(f"| {c.text[:60]}... | `{src}` | {status_icon} {c.status} | {int(c.confidence * 100)}% |")

        return "\n".join(lines)


# Global singleton instance
evidence_ledger = EvidenceLedger()
