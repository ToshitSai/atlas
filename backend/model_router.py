"""Intelligent Model Router — invisible, backend-only task routing.

USER MESSAGE -> MODEL ROUTER -> TASK CLASSIFICATION -> MODEL SELECTION ->
PROVIDER (via backend.llm) -> RESPONSE -> USER.

Design rules honoured here:
  * Reuse, never duplicate. Provider calls, admission control, retries, budget,
    telemetry and the engine trace all live in ``backend.llm``. Web search and
    deep research stay in their existing modules and are dispatched by the
    existing intent router; this module only adds *capability-aware model
    selection* plus a structured routing decision on top.
  * No invented model IDs. The registry reads the ACTUAL configured provider
    models from the environment (the same ``*_MODEL`` vars ``backend.llm``
    uses) and falls back to that module's documented defaults.
  * Secret-free. API keys never enter this module, its logs, or its output.
    Only provider names, model IDs, capabilities and timings are recorded.
  * Deterministic and lightweight by default. Classification reuses the rich
    intent heuristics already in the codebase; an optional LLM classifier is
    gated behind ``MODEL_ROUTER_LLM_CLASSIFY`` and its output is validated
    against allowlists before it is ever trusted.
  * Safe by construction. Any error degrades to GENERAL / LOW with the default
    provider order, so the chatbot still answers.
"""
from __future__ import annotations

import os
import re
import threading
import time
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

import backend.config  # auto-loads .env into os.environ
from backend import llm as llm_mod

# --------------------------------------------------------------------------- #
# Task types, complexity, capabilities
# --------------------------------------------------------------------------- #
TASK_GENERAL = "GENERAL"
TASK_CODING = "CODING"
TASK_DEBUGGING = "DEBUGGING"
TASK_MATHEMATICS = "MATHEMATICS"
TASK_RESEARCH = "RESEARCH"
TASK_ANALYSIS = "ANALYSIS"
TASK_WRITING = "WRITING"
TASK_SUMMARIZATION = "SUMMARIZATION"
TASK_DOCUMENT_ANALYSIS = "DOCUMENT_ANALYSIS"
TASK_DATA_ANALYSIS = "DATA_ANALYSIS"
TASK_MULTIMODAL = "MULTIMODAL"
TASK_PLANNING = "PLANNING"
TASK_DEEP_RESEARCH = "DEEP_RESEARCH"

_TASK_TYPES = {
    TASK_GENERAL, TASK_CODING, TASK_DEBUGGING, TASK_MATHEMATICS, TASK_RESEARCH,
    TASK_ANALYSIS, TASK_WRITING, TASK_SUMMARIZATION, TASK_DOCUMENT_ANALYSIS,
    TASK_DATA_ANALYSIS, TASK_MULTIMODAL, TASK_PLANNING, TASK_DEEP_RESEARCH,
}

COMPLEXITY_LOW = "LOW"
COMPLEXITY_MEDIUM = "MEDIUM"
COMPLEXITY_HIGH = "HIGH"
_COMPLEXITIES = {COMPLEXITY_LOW, COMPLEXITY_MEDIUM, COMPLEXITY_HIGH}

CAP_GENERAL = "general"
CAP_CODING = "coding"
CAP_REASONING = "reasoning"
CAP_MATH = "math"
CAP_WRITING = "writing"
CAP_SUMMARIZATION = "summarization"
CAP_LONG_CONTEXT = "long_context"
CAP_MULTIMODAL = "multimodal"
CAP_TOOLS = "tools"
_CAPABILITIES = {
    CAP_GENERAL, CAP_CODING, CAP_REASONING, CAP_MATH, CAP_WRITING,
    CAP_SUMMARIZATION, CAP_LONG_CONTEXT, CAP_MULTIMODAL, CAP_TOOLS,
}

# Capability each task fundamentally needs (hard gate) and merely prefers.
_TASK_REQUIRED: Dict[str, List[str]] = {
    TASK_GENERAL: [CAP_GENERAL],
    TASK_CODING: [CAP_CODING],
    TASK_DEBUGGING: [CAP_CODING],
    TASK_MATHEMATICS: [CAP_REASONING, CAP_MATH],
    TASK_RESEARCH: [CAP_REASONING],
    TASK_ANALYSIS: [CAP_REASONING],
    TASK_WRITING: [CAP_WRITING],
    TASK_SUMMARIZATION: [CAP_SUMMARIZATION],
    TASK_DOCUMENT_ANALYSIS: [CAP_LONG_CONTEXT],
    TASK_DATA_ANALYSIS: [CAP_CODING, CAP_REASONING],
    TASK_MULTIMODAL: [CAP_MULTIMODAL],
    TASK_PLANNING: [CAP_REASONING],
    TASK_DEEP_RESEARCH: [CAP_REASONING],
}
_TASK_PREFERRED: Dict[str, List[str]] = {
    TASK_GENERAL: [],
    TASK_CODING: [CAP_REASONING, CAP_TOOLS],
    TASK_DEBUGGING: [CAP_REASONING, CAP_TOOLS],
    TASK_MATHEMATICS: [CAP_LONG_CONTEXT],
    TASK_RESEARCH: [CAP_LONG_CONTEXT, CAP_TOOLS],
    TASK_ANALYSIS: [CAP_CODING, CAP_LONG_CONTEXT],
    TASK_WRITING: [CAP_REASONING],
    TASK_SUMMARIZATION: [CAP_LONG_CONTEXT],
    TASK_DOCUMENT_ANALYSIS: [CAP_REASONING, CAP_SUMMARIZATION],
    TASK_DATA_ANALYSIS: [CAP_LONG_CONTEXT, CAP_TOOLS],
    TASK_MULTIMODAL: [CAP_GENERAL],
    TASK_PLANNING: [CAP_LONG_CONTEXT],
    TASK_DEEP_RESEARCH: [CAP_LONG_CONTEXT, CAP_TOOLS],
}
# Human-readable primary capability surfaced in the routing decision.
_TASK_CAPABILITY_LABEL: Dict[str, str] = {
    TASK_GENERAL: "general",
    TASK_CODING: "coding",
    TASK_DEBUGGING: "coding+reasoning",
    TASK_MATHEMATICS: "reasoning+math",
    TASK_RESEARCH: "research",
    TASK_ANALYSIS: "reasoning",
    TASK_WRITING: "writing",
    TASK_SUMMARIZATION: "summarization",
    TASK_DOCUMENT_ANALYSIS: "long_context",
    TASK_DATA_ANALYSIS: "coding+reasoning",
    TASK_MULTIMODAL: "multimodal",
    TASK_PLANNING: "reasoning",
    TASK_DEEP_RESEARCH: "deep_research",
}

# --------------------------------------------------------------------------- #
# Model registry — provider-family capability profiles. Model IDs come from the
# environment (the same vars backend.llm reads); profiles describe the family's
# documented default model and are the single source of truth for routing.
# --------------------------------------------------------------------------- #
# (provider, model_env_var, default_model, context_limit,
#  latency_tier[1=fastest], cost_tier[1=cheapest], reasoning_tier[3=strongest],
#  coding_tier, capabilities, strengths)
_PROVIDER_PROFILES: List[Tuple[str, str, str, int, int, int, int, int, List[str], List[str]]] = [
    ("anthropic", "ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929", 200000, 2, 3, 3, 3,
     [CAP_GENERAL, CAP_CODING, CAP_REASONING, CAP_MATH, CAP_WRITING, CAP_SUMMARIZATION,
      CAP_LONG_CONTEXT, CAP_TOOLS],
     ["strongest coding & reasoning", "long-form writing", "200k context"]),
    ("openai", "OPENAI_MODEL", "gpt-4o-mini", 128000, 2, 2, 2, 2,
     [CAP_GENERAL, CAP_CODING, CAP_REASONING, CAP_MATH, CAP_WRITING, CAP_SUMMARIZATION,
      CAP_MULTIMODAL, CAP_TOOLS],
     ["balanced general assistant", "multimodal", "fast"]),
    ("gemini", "GEMINI_MODEL", "gemini-2.5-flash", 1000000, 1, 1, 2, 2,
     [CAP_GENERAL, CAP_CODING, CAP_REASONING, CAP_MATH, CAP_WRITING, CAP_SUMMARIZATION,
      CAP_LONG_CONTEXT, CAP_MULTIMODAL, CAP_TOOLS],
     ["very long context (1M)", "multimodal", "fast & low cost"]),
    ("mistral", "MISTRAL_MODEL", "mistral-tiny-2312", 32000, 1, 1, 1, 1,
     [CAP_GENERAL, CAP_SUMMARIZATION, CAP_WRITING],
     ["cheapest & fastest", "simple general queries"]),
]


def build_registry() -> List[Dict[str, Any]]:
    """Return the model registry using the ACTUAL configured model identifiers.

    ``enabled`` reflects whether the provider's API key is present in the
    environment, so the registry is a truthful single source of truth. No key
    material is ever read into the returned structure beyond a boolean.
    """
    entries: List[Dict[str, Any]] = []
    for (provider, model_env, default_model, ctx, latency, cost,
         reasoning, coding, caps, strengths) in _PROVIDER_PROFILES:
        model = os.environ.get(model_env) or default_model
        configured = bool(os.environ.get(llm_mod._PROVIDER_KEY_ENV.get(provider, "")))
        entries.append({
            "provider": provider,
            "model": model,
            "capabilities": list(caps),
            "strengths": list(strengths),
            "context_limit": ctx,
            "latency_tier": latency,
            "cost_tier": cost,
            "reasoning_tier": reasoning,
            "coding_tier": coding,
            "configured": configured,
            "enabled": configured,
        })
    return entries


_MODEL_BY_PROVIDER = {p[0]: (p[1], p[2]) for p in _PROVIDER_PROFILES}


def model_id_for(provider: Optional[str]) -> Optional[str]:
    if not provider:
        return None
    pair = _MODEL_BY_PROVIDER.get(provider)
    if not pair:
        return None
    return os.environ.get(pair[0]) or pair[1]


# --------------------------------------------------------------------------- #
# Provider health — temporary, self-healing avoidance of failing providers.
# --------------------------------------------------------------------------- #
class ProviderHealth:
    """In-memory, thread-safe provider health with cooldown (never permanent).

    A provider is briefly avoided after repeated failures so one bad key or a
    transient outage does not keep costing latency, but it always recovers once
    its cooldown expires. On ephemeral serverless instances this is best-effort
    per instance, which is the honest scope of a lightweight router.
    """

    _COOLDOWN = {
        "timeout": 20.0,
        "temporary": 20.0,
        "rate_limited": 45.0,
        "error": 20.0,
        "authentication": 300.0,
        "unavailable": 300.0,
    }
    _FAIL_THRESHOLD = 2

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: Dict[str, Dict[str, Any]] = {}

    def _entry(self, provider: str) -> Dict[str, Any]:
        return self._state.setdefault(
            provider, {"consecutive_failures": 0, "status": "available", "cooldown_until": 0.0, "total": 0, "errors": 0, "last_success": None, "last_error": None})

    def record(self, provider: str, ok: bool, note: str = "") -> None:
        if not provider:
            return
        with self._lock:
            entry = self._entry(provider)
            entry["total"] += 1
            if ok:
                entry["consecutive_failures"] = 0
                entry["status"] = "available"
                entry["cooldown_until"] = 0.0
                entry["last_success"] = time.time()
                return
            entry["consecutive_failures"] += 1
            entry["errors"] += 1
            entry["last_error"] = {"time": time.time(), "message": str(note)[:180]}
            status = self._classify_failure(note)
            entry["status"] = status
            if entry["consecutive_failures"] >= self._FAIL_THRESHOLD or status in ("authentication", "unavailable", "rate_limited"):
                entry["cooldown_until"] = time.monotonic() + self._COOLDOWN.get(status, 20.0)

    @staticmethod
    def _classify_failure(note: str) -> str:
        n = (note or "").lower()
        if "timeout" in n or "budget" in n:
            return "timeout"
        if "rate" in n or "429" in n:
            return "rate_limited"
        if "auth" in n or "401" in n or "403" in n or "key" in n:
            return "authentication"
        if "unavailable" in n or "503" in n:
            return "unavailable"
        return "temporary"

    def is_available(self, provider: str) -> bool:
        with self._lock:
            entry = self._state.get(provider)
            if not entry:
                return True
            if entry["cooldown_until"] and time.monotonic() < entry["cooldown_until"]:
                return False
            # Cooldown elapsed -> opportunistically retry.
            if entry["cooldown_until"] and time.monotonic() >= entry["cooldown_until"]:
                entry["cooldown_until"] = 0.0
                entry["status"] = "available"
                entry["consecutive_failures"] = 0
            return True

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            now = time.monotonic()
            out: Dict[str, Any] = {}
            for provider, entry in self._state.items():
                cooling = bool(entry["cooldown_until"]) and now < entry["cooldown_until"]
                out[provider] = {
                    "status": entry["status"] if not cooling else entry["status"],
                    "available": not cooling,
                    "consecutive_failures": entry["consecutive_failures"],
                    "cooldown_remaining_s": round(max(0.0, entry["cooldown_until"] - now), 1) if cooling else 0.0,
                    "last_success": entry.get("last_success"),
                    "last_error": entry.get("last_error"),
                    "rolling_error_rate": round(entry.get("errors", 0) / max(1, entry.get("total", 0)), 3),
                }
            return out


health = ProviderHealth()

# --------------------------------------------------------------------------- #
# Routing logs — bounded, secret-free ring buffer for ops/debug.
# --------------------------------------------------------------------------- #
_LOG_LOCK = threading.Lock()
_ROUTING_LOGS: deque = deque(maxlen=100)


def _record_log(entry: Dict[str, Any]) -> None:
    with _LOG_LOCK:
        _ROUTING_LOGS.append(entry)


def _update_log(request_id: str, **fields: Any) -> None:
    if not request_id:
        return
    with _LOG_LOCK:
        for entry in reversed(_ROUTING_LOGS):
            if entry.get("requestId") == request_id:
                entry.update(fields)
                return


def recent_routing_logs(limit: int = 20) -> List[Dict[str, Any]]:
    with _LOG_LOCK:
        return list(_ROUTING_LOGS)[-limit:]


# --------------------------------------------------------------------------- #
# Routing decision
# --------------------------------------------------------------------------- #
class RoutingDecision:
    def __init__(self) -> None:
        self.task: str = TASK_GENERAL
        self.complexity: str = COMPLEXITY_LOW
        self.flags: Dict[str, bool] = {
            "needs_web": False, "needs_deep_research": False,
            "needs_long_context": False, "needs_code_execution": False,
            "needs_multimodal": False,
        }
        self.recommended_capability: str = "general"
        self.reason: str = "Default general routing."
        self.provider_order: List[str] = []
        self.provider: Optional[str] = None
        self.model: Optional[str] = None
        self.classify_latency_ms: float = 0.0
        self.started_at: float = time.monotonic()
        self.request_id: str = ""
        self.classifier: str = "deterministic"

    def to_safe_dict(self) -> Dict[str, Any]:
        """Internal/debug summary. Contains NO secrets and NO message text."""
        return {
            "task": self.task,
            "complexity": self.complexity,
            "recommendedCapability": self.recommended_capability,
            "provider": self.provider,
            "model": self.model,
            "providerOrder": list(self.provider_order),
            "needsWeb": self.flags["needs_web"],
            "needsDeepResearch": self.flags["needs_deep_research"],
            "needsLongContext": self.flags["needs_long_context"],
            "needsCodeExecution": self.flags["needs_code_execution"],
            "needsMultimodal": self.flags["needs_multimodal"],
            "reason": self.reason,
            "classifier": self.classifier,
            "classifyLatencyMs": self.classify_latency_ms,
        }


# --------------------------------------------------------------------------- #
# Classification heuristics
# --------------------------------------------------------------------------- #
_IMG_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".heic")
_AUDIO_EXT = (".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac")
_VIDEO_EXT = (".mp4", ".mov", ".avi", ".mkv", ".webm")
_DOC_EXT = (".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".ppt", ".pptx", ".epub")
_DATA_EXT = (".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".arrow", ".json", ".jsonl")
_CODE_EXT = (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".cc", ".cs",
             ".go", ".rs", ".rb", ".php", ".sh", ".sql", ".html", ".css", ".kt", ".swift")

_MATH_RE = re.compile(
    r"\b(?:derivative|integral|integrals|differentiate|integrate|calculus|equation|"
    r"solve for|matrix|matrices|eigenvalue|probability|statistic(?:al|s)?|"
    r"prove|proof|theorem|limit of|series expansion|linear algebra|ode|pde)\b", re.IGNORECASE)
_SUMMARIZE_RE = re.compile(
    r"\b(?:summar(?:ize|ise|y)|tl;?dr|condense|give me the gist|shorten|abstract of)\b", re.IGNORECASE)
_WRITING_RE = re.compile(
    r"\b(?:write (?:me )?(?:a|an|the)?\s*(?:\w+\s+){0,4}?(?:poem|story|essay|article|blog|"
    r"email|letter|speech|script|haiku|novel|paragraph|caption|slogan|post)|rewrite|"
    r"rephrase|proofread|compose|draft (?:an?|the))\b", re.IGNORECASE)
_PLANNING_RE = re.compile(
    r"\b(?:plan|roadmap|step[- ]by[- ]step (?:plan|guide|approach)|strategy|"
    r"how should i (?:approach|start|structure)|outline (?:a|the) plan)\b", re.IGNORECASE)
_DEBUG_RE = re.compile(
    r"\b(?:crash(?:es|ed|ing)?|error|exception|traceback|stack ?trace|bug|broken|"
    r"not working|doesn'?t work|fails?|failing|segfault|undefined is not|"
    r"cannot read propert|runtime error|wrong output|unexpected (?:result|behavi))\b",
    re.IGNORECASE)
_TECH_CONTEXT_RE = re.compile(
    r"\b(?:react|vue|angular|node|npm|javascript|typescript|python|java|spring|django|"
    r"flask|fastapi|api|endpoint|function|method|class|module|server|deploy(?:ment|ed)?|"
    r"build|compile|docker|kubernetes|sql|database|query|code|script|program|app|"
    r"application|backend|frontend|component|hook|state)\b", re.IGNORECASE)
_CODE_INTENT_RE = re.compile(
    r"\b(?:write|create|make|generate|implement|build|code|refactor|optimize|optimise|"
    r"debug|fix)\b[^.?]*\b(?:function|program|script|class|api|endpoint|app|application|"
    r"component|snippet|code|module|service|query|algorithm|in (?:python|javascript|"
    r"java|c\+\+|sql|typescript|go|rust))\b", re.IGNORECASE)
_DATA_ANALYSIS_RE = re.compile(
    r"\b(?:analy[sz]e|analyse|find (?:the )?anomal|detect (?:the )?anomal|correlat|"
    r"trend|statistics|distribution|clean the data|data ?frame|aggregate|group by)\b",
    re.IGNORECASE)
_RUN_CODE_RE = re.compile(r"\b(?:run|execute|compute the output|what does this .* (?:print|return|output))\b", re.IGNORECASE)


def _ext(name: str) -> str:
    name = (name or "").lower().split("?")[0]
    return name[name.rfind("."):] if "." in name else ""


def _complexity_label(score: float) -> str:
    if score <= 3:
        return COMPLEXITY_LOW
    if score <= 6:
        return COMPLEXITY_MEDIUM
    return COMPLEXITY_HIGH


def classify_task(message: str,
                  files: Optional[List[Dict[str, Any]]] = None,
                  conversation_context: Optional[str] = None,
                  active_mode: Optional[str] = None) -> RoutingDecision:
    """Deterministic, multi-signal task classification (no message text stored).

    Reuses the existing intent heuristics (``detect_question_type``,
    ``classify_research_route``, ``assess_research_complexity``) and
    ``backend.llm.estimate_question_complexity`` so routing reflects real intent
    rather than a single keyword. Always returns a valid decision.
    """
    decision = RoutingDecision()
    text = (message or "").strip()
    low = text.lower()
    files = files or []
    if not text and not files:
        decision.reason = "Empty message; defaulting to general routing."
        return decision

    # --- Reuse existing routing signals ---------------------------------- #
    route: Dict[str, Any] = {}
    qtype = "other"
    complexity_score = 2.0
    try:
        from backend.intent_router import (
            detect_question_type, classify_research_route, assess_research_complexity,
        )
        qtype = detect_question_type(text) or "other"
        route = classify_research_route(text) or {}
        complexity_score = max(complexity_score, float(route.get("complexity_score", 0) or 0))
        assess = assess_research_complexity(text) or {}
        complexity_score = max(complexity_score, float(assess.get("complexity_score", 0) or 0))
        diagnosis = bool((assess.get("signals") or {}).get("diagnosis"))
    except Exception:
        diagnosis = False
    try:
        est = llm_mod.estimate_question_complexity(text) or {}
        complexity_score = max(complexity_score, float(est.get("complexity_score", 2) or 2))
        is_multi_part = bool(est.get("is_multi_part"))
        is_derivation = bool(est.get("is_derivation"))
    except Exception:
        is_multi_part = False
        is_derivation = False

    # --- Capability flags ------------------------------------------------- #
    flags = decision.flags
    flags["needs_web"] = bool(route.get("requires_web"))
    flags["needs_deep_research"] = bool(route.get("requires_deep_research"))
    if len(text) > 4000 or is_multi_part or low.count("\n") >= 12:
        flags["needs_long_context"] = True
    if is_derivation or _MATH_RE.search(low):
        complexity_score = max(complexity_score, 5.0)

    # --- File-driven classification (highest priority) -------------------- #
    exts = {_ext(f.get("name") or f.get("filename") or "") for f in files if isinstance(f, dict)}
    exts.discard("")
    mimes = " ".join(str(f.get("type") or f.get("mime") or "").lower() for f in files if isinstance(f, dict))
    has_img = bool(exts & set(_IMG_EXT)) or "image/" in mimes
    has_av = bool(exts & set(_AUDIO_EXT + _VIDEO_EXT)) or "audio/" in mimes or "video/" in mimes
    has_data = bool(exts & set(_DATA_EXT)) or "text/csv" in mimes
    has_doc = bool(exts & set(_DOC_EXT)) or "application/pdf" in mimes
    has_code = bool(exts & set(_CODE_EXT)) or "text/x-" in mimes
    if files:
        flags["needs_long_context"] = True  # attached content is fed to the model

    # --- Decide the task -------------------------------------------------- #
    task = TASK_GENERAL
    reason = "Ordinary question; a general model is sufficient."

    if has_img or has_av:
        task = TASK_MULTIMODAL
        flags["needs_multimodal"] = True
        reason = "Message includes image/audio/video content requiring a multimodal model."
    elif route.get("mode") == "deep_research":
        task = TASK_DEEP_RESEARCH
        flags["needs_web"] = True
        flags["needs_deep_research"] = True
        reason = route.get("reason") or "Multi-step investigation; routed to the deep-research pipeline."
    elif has_data and (_DATA_ANALYSIS_RE.search(low) or "analy" in low):
        task = TASK_DATA_ANALYSIS
        flags["needs_code_execution"] = bool(_RUN_CODE_RE.search(low))
        reason = "Attached/quoted dataset with an analysis request."
    elif has_doc and (_SUMMARIZE_RE.search(low) or "analy" in low or "read" in low or True):
        task = TASK_DOCUMENT_ANALYSIS
        reason = "Attached document requiring long-context reading."
    elif has_code:
        task = TASK_DEBUGGING if _DEBUG_RE.search(low) else TASK_CODING
        reason = "Attached source file; routed to a coding-capable model."
    elif _DEBUG_RE.search(low) and _TECH_CONTEXT_RE.search(low):
        task = TASK_DEBUGGING
        flags["needs_code_execution"] = bool(_RUN_CODE_RE.search(low))
        reason = "Describes a code/runtime failure; needs strong coding + reasoning."
    elif qtype == "coding" or _CODE_INTENT_RE.search(low):
        task = TASK_CODING
        flags["needs_code_execution"] = bool(_RUN_CODE_RE.search(low))
        reason = "Requests writing or implementing code."
    elif _MATH_RE.search(low) and not flags["needs_web"]:
        task = TASK_MATHEMATICS
        reason = "Mathematical derivation or quantitative reasoning."
    elif _SUMMARIZE_RE.search(low):
        task = TASK_SUMMARIZATION
        reason = "Summarization request."
    elif _WRITING_RE.search(low):
        task = TASK_WRITING
        reason = "Creative/professional writing request."
    elif _PLANNING_RE.search(low):
        task = TASK_PLANNING
        reason = "Asks for a plan or structured approach."
    elif route.get("mode") == "web_search":
        task = TASK_RESEARCH
        flags["needs_web"] = True
        reason = route.get("reason") or "Needs current/external information; web search first."
    elif qtype == "research" or (diagnosis and route.get("complexity_score", 0) >= 4):
        task = TASK_RESEARCH if not diagnosis else TASK_ANALYSIS
        reason = "Investigative/analytical question requiring reasoning."
    elif _DATA_ANALYSIS_RE.search(low) and ("data" in low or "dataset" in low or "csv" in low):
        task = TASK_DATA_ANALYSIS
        reason = "Data-analysis request."

    # A debugging/diagnosis signal on an otherwise-coding task upgrades intent.
    if task == TASK_CODING and (diagnosis or _DEBUG_RE.search(low)):
        task = TASK_DEBUGGING
        reason = "Code request framed as a failure to diagnose (coding + debugging)."

    decision.task = task
    decision.recommended_capability = _TASK_CAPABILITY_LABEL.get(task, "general")
    decision.flags = flags

    # --- Complexity ------------------------------------------------------- #
    if task in (TASK_DEEP_RESEARCH, TASK_RESEARCH, TASK_ANALYSIS):
        complexity_score = max(complexity_score, 5.0)
    if task == TASK_DEBUGGING:
        # Diagnosing a failure needs reasoning, never the cheapest/fastest model.
        complexity_score = max(complexity_score, 4.0)
    if task in (TASK_DEBUGGING, TASK_CODING) and flags["needs_long_context"]:
        complexity_score = max(complexity_score, 7.0)
    decision.complexity = _complexity_label(complexity_score)
    decision.reason = reason

    # --- Optional, validated LLM classification (off by default) ---------- #
    if os.environ.get("MODEL_ROUTER_LLM_CLASSIFY", "").strip().lower() in ("1", "true", "yes"):
        llm_decision = _llm_classify(text)
        if llm_decision is not None:
            decision = llm_decision
            decision.classifier = "llm"
    return decision


_ROUTING_SYSTEM_PROMPT = (
    "You are the routing engine of an AI research assistant. Determine the user's "
    "actual task, complexity, required capabilities, and tools. Do NOT answer the "
    "question. Return ONLY a compact JSON object with keys: task (one of "
    + ",".join(sorted(_TASK_TYPES)) + "), complexity (LOW|MEDIUM|HIGH), needs_web "
    "(bool), needs_deep_research (bool), needs_long_context (bool), "
    "needs_code_execution (bool), needs_multimodal (bool), reason (short string). "
    "Prefer the simplest capable execution path. Use deep research only when a "
    "genuine multi-step investigation is required; use web search when current or "
    "external information is required; use coding-capable models for substantial "
    "coding or debugging; use general models for ordinary questions. Consider "
    "conversation context but the current message is authoritative."
)


def _llm_classify(text: str) -> Optional[RoutingDecision]:
    """Optional LLM classifier. Output is validated against allowlists; any
    malformed or untrustworthy result returns None so the deterministic
    decision stands (never blindly trust model output)."""
    import json as _json
    try:
        raw = llm_mod.query_llm(text, _ROUTING_SYSTEM_PROMPT, timeout=8)
        if not raw:
            return None
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        data = _json.loads(match.group(0))
        task = str(data.get("task", "")).upper()
        if task not in _TASK_TYPES:
            return None
        cx = str(data.get("complexity", "")).upper()
        if cx not in _COMPLEXITIES:
            cx = COMPLEXITY_MEDIUM
        d = RoutingDecision()
        d.task = task
        d.complexity = cx
        for key in d.flags:
            val = data.get(key)
            if isinstance(val, bool):
                d.flags[key] = val
        d.recommended_capability = _TASK_CAPABILITY_LABEL.get(task, "general")
        reason = str(data.get("reason") or "")[:160]
        d.reason = reason or "LLM routing classification."
        return d
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Scoring & selection
# --------------------------------------------------------------------------- #
def _score(entry: Dict[str, Any], decision: RoutingDecision, health_ok: bool) -> float:
    caps = set(entry.get("capabilities") or [])
    required = _TASK_REQUIRED.get(decision.task, [CAP_GENERAL])
    preferred = _TASK_PREFERRED.get(decision.task, [])
    flags = decision.flags

    # Flag-driven hard requirements augment the task's required capabilities.
    required = list(required)
    if flags["needs_multimodal"] and CAP_MULTIMODAL not in required:
        required.append(CAP_MULTIMODAL)
    if flags["needs_long_context"] and CAP_LONG_CONTEXT not in required:
        required.append(CAP_LONG_CONTEXT)
    if flags["needs_code_execution"] and CAP_CODING not in required:
        required.append(CAP_CODING)

    score = 0.0
    missing = [c for c in required if c not in caps]
    score -= 6.0 * len(missing)
    score += 1.5 * sum(1 for c in preferred if c in caps)

    tier = float(entry.get("reasoning_tier", 1))
    if decision.complexity == COMPLEXITY_HIGH:
        score += tier * 1.5
    elif decision.complexity == COMPLEXITY_MEDIUM:
        score += tier * 0.5
    else:  # LOW: favour cheap/fast over the strongest reasoner
        score -= tier * 0.75

    if flags["needs_long_context"]:
        ctx = int(entry.get("context_limit", 0))
        if ctx >= 500000:
            score += 2.5
        elif ctx >= 128000:
            score += 1.0
        else:
            score -= 2.0

    latency_weight = {COMPLEXITY_LOW: 1.2, COMPLEXITY_MEDIUM: 0.7, COMPLEXITY_HIGH: 0.3}[decision.complexity]
    score -= float(entry.get("latency_tier", 2)) * latency_weight
    score -= float(entry.get("cost_tier", 2)) * 0.4  # cost is secondary
    score += 2.0 if health_ok else -5.0
    return round(score, 3)


def select_providers(decision: RoutingDecision) -> Tuple[List[str], Optional[Dict[str, Any]]]:
    """Score configured models and return a capability-ordered provider list.

    Healthier providers are preferred, but a cooling provider is never removed
    (it recovers on its own), so a single capable provider still gets used.
    """
    entries = [e for e in build_registry() if e["configured"] and e["enabled"] and not (e["provider"] == "mistral" and decision.complexity != COMPLEXITY_LOW)]
    if not entries:
        return [], None
    scored = [(_score(e, decision, health.is_available(e["provider"])), e) for e in entries]
    # Available providers first, then by score descending. Stable tie-break on
    # provider name keeps the order deterministic across requests.
    scored.sort(key=lambda pair: (0 if health.is_available(pair[1]["provider"]) else 1,
                                  -pair[0], pair[1]["provider"]))
    order = [e["provider"] for _, e in scored]
    return order, scored[0][1]


# --------------------------------------------------------------------------- #
# Public API used by the chat endpoint
# --------------------------------------------------------------------------- #
def route(request_id: str, message: str,
          files: Optional[List[Dict[str, Any]]] = None,
          conversation_context: Optional[str] = None,
          active_mode: Optional[str] = None) -> RoutingDecision:
    """Classify + select. Records a secret-free routing log. Never raises."""
    started = time.monotonic()
    decision = RoutingDecision()
    decision.request_id = request_id or ""
    try:
        decision = classify_task(message, files, conversation_context, active_mode)
        decision.request_id = request_id or ""
        order, top = select_providers(decision)
        decision.provider_order = order
        decision.provider = top["provider"] if top else None
        decision.model = top["model"] if top else None
    except Exception as exc:  # router failure must never block the chatbot
        decision = RoutingDecision()
        decision.request_id = request_id or ""
        decision.reason = f"Router fallback to general default ({type(exc).__name__})."
        try:
            order, top = select_providers(decision)
            decision.provider_order, decision.provider = order, (top["provider"] if top else None)
            decision.model = top["model"] if top else None
        except Exception:
            pass
    decision.started_at = started
    decision.classify_latency_ms = round((time.monotonic() - started) * 1000, 2)
    _record_log({
        "requestId": decision.request_id or None,
        "task": decision.task,
        "complexity": decision.complexity,
        "recommendedCapability": decision.recommended_capability,
        "provider": decision.provider,
        "model": decision.model,
        "needsWeb": decision.flags["needs_web"],
        "needsDeepResearch": decision.flags["needs_deep_research"],
        "fallbackUsed": False,
        "latencyMs": None,
        "classifier": decision.classifier,
    })
    return decision


def apply(decision: RoutingDecision) -> None:
    """Push the routing decision into backend.llm for this request only.

    Sets the capability-ordered provider preference (used by query_llm's auto
    path) and opens the per-request outcome trace. A user-pinned provider in
    settings still wins because it makes query_llm strict, preserving existing
    behaviour. Never touches global process state or the UI.
    """
    try:
        llm_mod.begin_provider_outcomes()
        if decision.provider_order:
            llm_mod.set_provider_preference(decision.provider_order)
    except Exception:
        pass


def finalize(request_id: str, decision: RoutingDecision) -> Dict[str, Any]:
    """Update provider health + routing log from real outcomes; clear preference.

    Returns the safe summary to attach to the chat response. Secret-free.
    """
    outcomes: List[Dict[str, Any]] = []
    try:
        outcomes = llm_mod.get_provider_outcomes()
    except Exception:
        outcomes = []
    for outcome in outcomes:
        try:
            health.record(outcome.get("provider"), bool(outcome.get("ok")), outcome.get("note", ""))
            if outcome.get("provider"):
                health.record(f"{outcome.get('provider')}:{model_id_for(outcome.get('provider'))}", bool(outcome.get("ok")), outcome.get("note", ""))
        except Exception:
            continue
    succeeded = next((o.get("provider") for o in outcomes if o.get("ok")), None)
    fallback_used = bool(succeeded and decision.provider and succeeded != decision.provider)
    actual_provider = succeeded or decision.provider
    actual_model = model_id_for(actual_provider) if actual_provider != decision.provider else decision.model
    latency_ms = round((time.monotonic() - decision.started_at) * 1000, 2)
    _update_log(request_id or decision.request_id,
                provider=actual_provider, model=actual_model,
                fallbackUsed=fallback_used, latencyMs=latency_ms)
    try:
        llm_mod.clear_provider_preference()
    except Exception:
        pass
    summary = decision.to_safe_dict()
    summary["provider"] = actual_provider
    summary["model"] = actual_model
    summary["fallbackUsed"] = fallback_used
    summary["latencyMs"] = latency_ms
    return summary


def snapshot() -> Dict[str, Any]:
    """Secret-free ops/debug view: registry capabilities + provider health."""
    debug = os.environ.get("MODEL_ROUTER_DEBUG", "").strip().lower() in ("1", "true", "yes")
    out: Dict[str, Any] = {
        "enabled": True,
        "anyProviderConfigured": llm_mod.any_provider_configured(),
        "registry": [
            {
                "provider": e["provider"], "model": e["model"],
                "capabilities": e["capabilities"], "strengths": e["strengths"],
                "contextLimit": e["context_limit"], "enabled": e["enabled"],
            } for e in build_registry()
        ],
        "providerHealth": health.snapshot(),
    }
    if debug:
        out["recentRouting"] = recent_routing_logs(20)
    return out
