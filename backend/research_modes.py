"""Research modes and autonomous dataset selection.

Modes (section 2 of the workflow directive):

  AUTONOMOUS  — never stop unnecessarily. Candidates are compared, the best
                suitable one is selected, and the pipeline continues through
                EDA -> baselines -> experiments -> report.
  GUIDED      — pause at genuinely user-owned decisions (default). This is the
                historical "Choose a dataset below to continue." behavior and
                it remains fully available.
  MANUAL      — the user drives every stage; the assistant presents options and
                never launches work on its own.

The mode is resolved from (in priority order): an explicit request field, the
session's stored choice, then the persisted app setting ``researchMode``,
falling back to GUIDED. A bare message like "use autonomous mode" in the chat
also flips the session mode.

Dataset selection (sections 3, 11, 14):

  * Candidates are ranked by the existing suitability scorer.
  * AUTONOMOUS selects the top candidate WITHOUT asking, when it clearly wins:
    the runner-up must be strictly lower scoring and the winner must have a
    non-trivial score itself.
  * When the top candidates are statistically indistinguishable (a near-tie),
    or no candidate clears the minimum suitability bar, the system pauses and
    asks the user — WAITING_FOR_USER is only ever entered for a genuine human
    decision, never as a routine checkpoint.

Activity events (sections 5, 6, 7) are plain, factual records of application
actions. They never contain model reasoning, prompts, or secrets.
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional

AUTONOMOUS = "AUTONOMOUS"
GUIDED = "GUIDED"
MANUAL = "MANUAL"
VALID_MODES = (AUTONOMOUS, GUIDED, MANUAL)
DEFAULT_MODE = GUIDED

# Generic research-stage keys. The frontend maps these to human labels; the
# backend only guarantees that every activity event carries the correlation
# fields (request_id / job_id / stage / status / label / timestamp) required
# by the event contract.
STAGE_LABELS = {
    "PLANNING": "Understanding the research goal",
    "DATASET_SEARCH": "Finding relevant datasets",
    "DATASET_EVALUATION": "Comparing datasets",
    "DATASET_SELECTED": "Selecting a dataset",
    "EDA": "Inspecting the data",
    "BASELINE": "Training the baseline",
    "EVALUATION": "Evaluating the baseline",
    "ERROR_ANALYSIS": "Analyzing errors",
    "HYPOTHESIS": "Planning the next experiment",
    "NEXT_EXPERIMENT": "Running the next experiment",
    "REPORT": "Writing the research report",
    "COMPLETED": "Research complete",
    "FAILED": "Research failed",
    "WAITING_FOR_USER": "Waiting for your input",
}

# Above this the top candidate is considered suitable at all.
_MIN_TOP_SCORE = 20.0
# Relative margin the winner must hold over the runner-up to auto-select.
_MIN_RELATIVE_MARGIN = 0.12
# Absolute margin fallback: within this the candidates are "nearly equal".
_NEAR_TIE_ABS = 3.0

_MODE_PATTERNS = (
    (re.compile(r"\bautonomous\s+(?:mode|research)?\b|\bmode\s*(?:to)?\s*autonomous\b|\bfull[ -]auto\b", re.I), AUTONOMOUS),
    (re.compile(r"\bguided\s+(?:mode|research)?\b|\bmode\s*(?:to)?\s*guided\b|\bask\s+me\s+(?:first|before)\b", re.I), GUIDED),
    (re.compile(r"\bmanual\s+(?:mode|research)?\b|\bmode\s*(?:to)?\s*manual\b|\bstep\s+by\s+step\b", re.I), MANUAL),
)


def normalize_mode(value: Any) -> Optional[str]:
    """Return a valid mode name for raw user/config input, else None."""
    if not isinstance(value, str):
        return None
    cleaned = value.strip().upper()
    aliases = {
        "AUTO": AUTONOMOUS,
        "FULLY_AUTONOMOUS": AUTONOMOUS,
        "FULL-AUTO": AUTONOMOUS,
        "USER_APPROVAL": GUIDED,
        "APPROVAL": GUIDED,
        "ASSISTED": GUIDED,
    }
    return aliases.get(cleaned) or (cleaned if cleaned in VALID_MODES else None)


def parse_mode_from_message(message: str) -> Optional[str]:
    """Detect an explicit in-chat mode switch like \"switch to autonomous mode\".

    Deliberately narrow: a mention of the word autonomous inside a research
    goal ("build an autonomous vehicle classifier") must NOT flip the mode,
    so only explicit mode-change phrasings match.
    """
    text = (message or "").strip()
    lowered = text.lower()
    if not re.search(r"\bmode\b|\bfull[ -]auto\b|\bask me\b|\bstep by step\b", lowered):
        return None
    for pattern, mode in _MODE_PATTERNS:
        if pattern.search(lowered):
            return mode
    return None


def resolve_mode(explicit: Any = None, session: Optional[Dict[str, Any]] = None,
                 settings: Optional[Dict[str, Any]] = None) -> str:
    """Resolve the effective research mode from request > session > settings."""
    return (
        normalize_mode(explicit)
        or normalize_mode((session or {}).get("research_mode"))
        or normalize_mode((settings or {}).get("researchMode"))
        or DEFAULT_MODE
    )


def make_activity(request_id: str, job_id: str, stage: str, status: str,
                  label: str, detail: Any = None) -> Dict[str, Any]:
    """One activity event per the event contract.

    Carries ONLY factual, high-level application state — no prompts, no
    model reasoning, no internal engineering details (directive §7).
    """
    event: Dict[str, Any] = {
        "requestId": request_id or None,
        "jobId": job_id or None,
        "stage": stage,
        "status": status,
        "label": label,
        "timestamp": int(time.time() * 1000),
    }
    if detail is not None:
        event["detail"] = detail
    return event


def stage_activity(request_id: str, job_id: str, stage: str, completed: bool,
                   label: Optional[str] = None, detail: Any = None) -> Dict[str, Any]:
    """Convenience wrapper: a stage that has just finished (or failed)."""
    default = STAGE_LABELS.get(stage, stage.replace("_", " ").title())
    if stage in ("FAILED",):
        status = "failed"
        default = label or default
    else:
        status = "completed" if completed else "running"
    return make_activity(request_id, job_id, stage, status, label or default, detail)


def _candidates_from(comp: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [c for c in (comp.get("candidates") or []) if c]


def selection_decision(comp: Dict[str, Any], mode: str) -> Dict[str, Any]:
    """Decide whether to auto-select, pause for the user, or give up.

    Returns a dict:
      decision: "AUTO_SELECT" | "ASK_USER" | "NO_CANDIDATES"
      dataset:  the selected candidate (when AUTO_SELECT)
      reason:   short factual reason shown to the user
    """
    top = _candidates_from(comp)
    if not top:
        return {"decision": "NO_CANDIDATES", "dataset": None, "reason": None}

    best = top[0]
    best_score = float(best.get("score") or 0.0)

    if mode != AUTONOMOUS:
        return {"decision": "ASK_USER", "dataset": None,
                "reason": "Guided mode asks before every dataset choice."}
    if mode == MANUAL:
        return {"decision": "ASK_USER", "dataset": None,
                "reason": "Manual mode leaves every stage to you."}

    if best_score < _MIN_TOP_SCORE:
        return {"decision": "ASK_USER", "dataset": None,
                "reason": "No candidate clearly satisfies the research goal."}

    if len(top) > 1:
        second_score = float(top[1].get("score") or 0.0)
        if best_score - second_score <= _NEAR_TIE_ABS or second_score < _MIN_RELATIVE_MARGIN * best_score:
            return {"decision": "ASK_USER", "dataset": None,
                    "reason": "Several candidates are nearly equally suitable."}
    return {"decision": "AUTO_SELECT", "dataset": best,
            "reason": (best.get("reasons") or ["it best matches the research goal"])[0]}


def user_approval_message(entity: str) -> str:
    return f"Use {entity} instead."


def set_session_mode(session_id: str, mode: str) -> None:
    """Persist the user's research mode on their chat session."""
    from database.store import store  # local import avoids a module cycle
    store.update_session(session_id or "default-session", {"research_mode": normalize_mode(mode) or DEFAULT_MODE})


def mode_requested_in_message(message: str) -> Optional[str]:
    """Mode requested via an explicit in-chat switch phrase, if any."""
    return parse_mode_from_message(message)
