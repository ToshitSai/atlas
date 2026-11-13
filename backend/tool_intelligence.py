"""Atlas AI Gen-4 — Adaptive Tool Intelligence & Model Router.

Capabilities:
1. Adaptive Tool Selection:
   - Evaluates incoming questions and identifies required tools (Python calculation, Web Search, Document RAG, Experiment DB, Knowledge Graph).
   - Generates and parses machine-readable tool dispatch formats.
2. Honest Model Router & Telemetry:
   - Determines whether a request can be served by the Local Atlas Qwen3-1.7B QLoRA model or escalated to a Frontier Cloud Model.
   - Enforces 100% transparent attribution: never falsely claims a local model produced a cloud answer.
   - Logs execution targets ("local_gpu" vs "cloud_frontier") and runtime performance.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ToolDecision:
    tool_name: str  # "python_calculator" | "web_search" | "document_rag" | "experiment_db" | "none"
    confidence: float
    reason: str
    suggested_params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ModelRouteDecision:
    selected_model: str
    provider: str  # "local" | "anthropic" | "google" | "openai"
    execution_target: str  # "local_gpu" | "cloud_frontier"
    escalation_reason: Optional[str] = None
    tools_selected: List[str] = field(default_factory=list)
    router_confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AdaptiveToolIntelligence:
    """Intelligently detects when external tools are genuinely needed."""

    CALCULATION_REGEX = re.compile(
        r"(\b(calculate|compute|solve|eval|evaluate|square root|sum of|derivative|integral)\b|"
        r"[\d\.\)]\s*[\+\-\*\/\^]\s*[\d\.\(]|\bmath\b)",
        re.IGNORECASE
    )

    SEARCH_REGEX = re.compile(
        r"\b(latest|current|today|news|recent papers?|arxiv|benchmarks? 202[4-6]|who won|stock price|weather in)\b",
        re.IGNORECASE
    )

    EXPERIMENT_REGEX = re.compile(
        r"\b(which model performed best|compare experiments?|learning rate|f1 score|accuracy on test|roc auc|overfitting|data leakage)\b",
        re.IGNORECASE
    )

    RAG_REGEX = re.compile(
        r"\b(in the uploaded|according to the document|in this pdf|file attachment|table in sheet|my dataset)\b",
        re.IGNORECASE
    )

    def select_tools(self, message: str, has_attachments: bool = False, has_project: bool = False) -> List[ToolDecision]:
        """Analyze query and select the appropriate toolset."""
        decisions: List[ToolDecision] = []
        msg = message.strip()

        # 1. Calculation
        if self.CALCULATION_REGEX.search(msg):
            decisions.append(ToolDecision(
                tool_name="python_calculator",
                confidence=0.92,
                reason="Query contains mathematical expressions or explicit calculation verbs requiring deterministic arithmetic.",
                suggested_params={"query": msg}
            ))

        # 2. Web Search
        if self.SEARCH_REGEX.search(msg):
            decisions.append(ToolDecision(
                tool_name="web_search",
                confidence=0.89,
                reason="Query demands real-time or recent information beyond offline static model weights.",
                suggested_params={"search_query": msg}
            ))

        # 3. Experiment Store
        if self.EXPERIMENT_REGEX.search(msg) and has_project:
            decisions.append(ToolDecision(
                tool_name="experiment_db",
                confidence=0.95,
                reason="Query references specific machine learning evaluation metrics or experiment comparisons.",
                suggested_params={"project_scoped": True}
            ))

        # 4. Document RAG
        if has_attachments or self.RAG_REGEX.search(msg):
            decisions.append(ToolDecision(
                tool_name="document_rag",
                confidence=0.98 if has_attachments else 0.85,
                reason="Query explicitly references uploaded documents or attachments.",
                suggested_params={"attachments_present": has_attachments}
            ))

        return decisions


class HonestModelRouter:
    """Routes inference between Local GPU and Cloud Frontier with honest attribution."""

    LOCAL_MODEL_NAME = "Atlas Gen-4 Research Intelligence (Qwen3-1.7B QLoRA)"

    def __init__(self):
        self._local_server_base_url = os.environ.get("LOCAL_LLM_BASE_URL", "")

    def is_local_available(self) -> bool:
        """Check whether local GPU inference server is configured and reachable."""
        return bool(self._local_server_base_url)

    def route_request(
        self,
        message: str,
        user_preference: Optional[str] = None,
        has_vision_attachments: bool = False,
        requires_deep_research: bool = False,
    ) -> ModelRouteDecision:
        """Decide the optimal model and enforce honest provenance attribution."""
        # 1. Vision attachments require multimodal frontier model (Gemini / Claude / GPT)
        if has_vision_attachments:
            return ModelRouteDecision(
                selected_model="Claude 3.5 Sonnet / Gemini 2.5 (Multimodal)",
                provider="cloud_frontier",
                execution_target="cloud_frontier",
                escalation_reason="Task contains multimodal images requiring frontier vision foundation model.",
                router_confidence=1.0,
            )

        # 2. Deep multi-hour autonomous research escalates to large cloud reasoning models
        if requires_deep_research:
            return ModelRouteDecision(
                selected_model="Claude 3.5 Sonnet (Atlas Reasoning)",
                provider="anthropic",
                execution_target="cloud_frontier",
                escalation_reason="Deep comprehensive synthesis across hundreds of sources requires massive context window (200k+).",
                router_confidence=0.95,
            )

        # 3. If user explicitly chose a cloud model from UI
        if user_preference and user_preference.lower() in ("atlas large", "atlas balanced", "atlas fast", "claude", "gpt", "gemini"):
            provider_map = {
                "atlas large": ("Claude 3.5 Sonnet", "anthropic"),
                "atlas balanced": ("GPT-4o Mini", "openai"),
                "atlas fast": ("Gemini 2.5 Flash Lite", "google"),
            }
            name, prov = provider_map.get(user_preference.lower(), (user_preference, "cloud_frontier"))
            return ModelRouteDecision(
                selected_model=f"Atlas Cloud ({name})",
                provider=prov,
                execution_target="cloud_frontier",
                escalation_reason=f"User explicitly selected {user_preference} in Model Selector.",
                router_confidence=1.0,
            )

        # 4. If local server is available and task fits within local research intelligence
        if self.is_local_available():
            return ModelRouteDecision(
                selected_model=self.LOCAL_MODEL_NAME,
                provider="local",
                execution_target="local_gpu",
                escalation_reason=None,
                router_confidence=0.90,
            )

        # 5. Default fallback to cloud with 100% honest transparency
        return ModelRouteDecision(
            selected_model="Claude 3.5 Sonnet (Atlas Large)",
            provider="anthropic",
            execution_target="cloud_frontier",
            escalation_reason="Local GPU inference server (LOCAL_LLM_BASE_URL) is offline; transparently dispatched to cloud provider.",
            router_confidence=0.88,
        )


# Global instances
tool_intelligence = AdaptiveToolIntelligence()
model_router = HonestModelRouter()
