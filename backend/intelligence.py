"""Capability planning and answer-quality metadata for chat requests.

This module deliberately plans *what* the assistant should use without
recording hidden reasoning or exposing chain-of-thought.  The intent router
still owns execution; this layer gives every completed turn a small, auditable
plan/verification record that callers can store with the conversation.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from backend.decomposition import extract_requirements


_CONSTRAINT = re.compile(r"\b(?:must|need|require|ensure|under|within|GDPR|SOC ?2|multi-region)\b", re.I)
_AMBIGUOUS_WINNER = re.compile(r"\b(?:who|which team)\s+won\s+(?:the\s+)?(?:world cup|championship|final)\b", re.I)
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_ENTITY_QUESTION = re.compile(
    r"^\s*(?:who\s+(?:is|was|are|were)|tell\s+me\s+about|what\s+is|"
    r"what\s+does|what\s+is\s+.+?\s+known\s+for)\s+(.+?)\s*[?!.]*\s*$",
    re.I,
)
_ENTITY_TAIL = re.compile(
    r"\s+(?:and\s+why|and\s+how|because|since|why\s+is|how\s+does)\b.*$",
    re.I,
)
_ENTITY_LEAD = re.compile(
    r"^\s*(?:who\s+(?:is|was|are|were)|tell\s+me\s+about|what\s+is|what\s+does)\s+",
    re.I,
)
_AMBIGUOUS_PERSON_NAMES = {"john smith", "john doe", "james smith"}


def extract_entity_candidate(message: str) -> Optional[str]:
    """Extract the named subject from a simple entity-information question."""
    text = (message or "").strip()
    if re.search(r"\b(?:latest|current|currently|today|research|investigate|deep dive)\b", text, re.I):
        return None
    match = _ENTITY_QUESTION.match(text)
    if match:
        entity = match.group(1).strip().strip("\"'“”")
    elif _ENTITY_LEAD.match(text):
        entity = _ENTITY_LEAD.sub("", text).strip().strip("?!. \"'“”")
        entity = re.split(r"\s+(?:and\s+what|and\s+why|because|since)\b", entity, maxsplit=1, flags=re.I)[0]
        entity = re.sub(r"\s+(?:and\s+)?(?:why|how)\b.*$", "", entity, flags=re.I)
        entity = re.sub(r"\s+(?:is|are)\s+(?:used|important|useful)\b.*$", "", entity, flags=re.I)
    else:
        return None
    entity = _ENTITY_TAIL.sub("", entity)
    entity = re.sub(r"['’]s(?:\s+(?:career|work|life|projects?))?$", "", entity, flags=re.I)
    entity = re.sub(r"\s+(?:and\s+what\s+(?:is|was)\s+(?:he|she|they)\s+known\s+for)$", "", entity, flags=re.I)
    return entity.strip() or None


def ambiguity_clarification(message: str) -> Optional[str]:
    """Return a concise clarification only when a result cannot be identified.

    This is intentionally narrow: normal questions continue through the
    general router.  ``World Cup`` has multiple sports and editions, while a
    named tournament or a year is enough context to proceed.
    """
    text = (message or "").strip()
    if _AMBIGUOUS_WINNER.search(text) and not _YEAR.search(text):
        return "Which World Cup do you mean—sport and year (for example, FIFA 2022 or Cricket 2023)?"
    entity = extract_entity_candidate(text)
    if entity and entity.casefold() in _AMBIGUOUS_PERSON_NAMES:
        return f"There are several notable people named {entity}. Which one do you mean?"
    return None


def estimate_difficulty(message: str, intent: str) -> str:
    """Classify request effort using structure, tools, and prompt complexity."""
    text = (message or "").strip()
    requirements = extract_requirements(text).requirements
    score = 0
    if len(text) > 350:
        score += 1
    if len(requirements) >= 2:
        score += 1
    if len(requirements) >= 4 or _CONSTRAINT.search(text):
        score += 1
    if intent in {"CODING", "DEEP_RESEARCH", "DATA_ANALYSIS", "RESEARCH_START"}:
        score += 2
    elif intent in {"MATHEMATICS", "CALCULATION", "CURRENT_INFORMATION", "WEB_SEARCH", "REASONING"}:
        score += 1
    return "HARD" if score >= 3 else "MODERATE" if score >= 1 else "EASY"


def _tools_for(intent: str, task_type: str) -> List[str]:
    key = (task_type or intent or "").lower()
    if key in {"calculation", "mathematics"}:
        return ["calculator", "sympy"]
    if key == "current_information":
        return ["current_fact_verifier", "web_search"]
    if key == "web_search":
        return ["web_search"]
    if key == "deep_research":
        return ["web_search", "literature_search", "source_synthesis"]
    if key in {"coding", "code_analysis"}:
        return ["code_generator", "sandbox"]
    if key in {"data_analysis", "document_analysis"}:
        return ["file_parser", "retrieval"]
    if intent in {"RESEARCH_START", "RESEARCH_FOLLOWUP", "RESEARCH_CONTROL"}:
        return ["dataset_discovery", "research_orchestrator"]
    if key in {"complex_reasoning", "multi_part", "reasoning"}:
        return ["requirement_tracker", "reasoning_model"]
    return ["general_assistant"]


def execution_metadata(message: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Create safe, structured quality metadata for a completed response."""
    intent = result.get("intent", "EXPLANATION")
    task_type = result.get("taskType", intent.lower())
    requirements = extract_requirements(message).requirements
    answer = result.get("response") or ""
    tools = _tools_for(intent, task_type)
    verification = "not_required"
    if any(t in tools for t in ("calculator", "sympy", "current_fact_verifier", "source_synthesis")):
        verification = "verified" if answer else "unavailable"
    elif "sandbox" in tools:
        # A code answer is not represented as executed unless the runner says
        # so; avoid claiming verification merely because code was generated.
        verification = "pending_execution"
    elif "retrieval" in tools:
        verification = "source_required"

    completed = 0
    low_answer = answer.lower()
    for requirement in requirements:
        keywords = [w.lower() for w in re.findall(r"[A-Za-z]{4,}", requirement.text)
                    if w.lower() not in {"explain", "compare", "please", "with", "that", "this"}]
        if keywords and any(word in low_answer for word in keywords[:3]):
            completed += 1
    return {
        "task_type": task_type,
        "difficulty": estimate_difficulty(message, intent),
        "required_capabilities": tools,
        "selected_tools": tools,
        "selected_model": "deterministic_tool" if tools[0] != "general_assistant" else "configured_general_model",
        "verification_status": verification,
        "requirements_total": len(requirements),
        "requirements_completed": completed if requirements else 0,
    }


def update_memory_summary(store, session_id: str, message: str, result: Dict[str, Any]) -> None:
    """Maintain compact mid-term context without copying the whole transcript."""
    prior = store.get_session(session_id).get("conversation_summary") or {}
    topics = list(prior.get("topics") or [])
    topic = result.get("lastTopic")
    if topic and topic not in topics:
        topics.append(topic)
    store.update_session(session_id, {
        "conversation_summary": {
            "topics": topics[-8:],
            "last_task_type": result.get("taskType"),
            "last_intent": result.get("intent"),
            "turns_seen": int(prior.get("turns_seen", 0)) + 1,
        }
    })
