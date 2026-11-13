"""Atlas AI Gen-4 — Research Continuity Engine.

Maintains durable, project-aware research context across sessions:
- Research objectives & hypotheses
- Decisions made & technical rationales
- Experiment histories, configs, and metrics
- Anti-patterns and failed approaches (avoiding repeated mistakes)
- Open questions and unexplored branches
- High-density project summaries for instant multi-turn recall without retraining
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from database.store import store


@dataclass
class ResearchObjective:
    id: str
    title: str
    description: str
    status: str = "active"  # "active" | "completed" | "paused" | "deprioritized"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class ResearchDecision:
    id: str
    decision: str
    rationale: str
    alternatives_considered: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class FailedApproach:
    id: str
    approach: str
    failure_mode: str
    lessons_learned: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class ResearchContext:
    project_id: str
    project_name: str
    objectives: List[Dict[str, Any]] = field(default_factory=list)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    failed_approaches: List[Dict[str, Any]] = field(default_factory=list)
    open_questions: List[Dict[str, Any]] = field(default_factory=list)
    datasets_used: List[Dict[str, Any]] = field(default_factory=list)
    experiment_history: List[Dict[str, Any]] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ResearchContinuityEngine:
    """Manages long-term research continuity for Atlas projects."""

    def __init__(self):
        self._memory_cache: Dict[str, ResearchContext] = {}

    def get_or_create_context(self, project_id: str, project_name: Optional[str] = None) -> ResearchContext:
        """Fetch or initialize research continuity state for a project."""
        if project_id in self._memory_cache:
            return self._memory_cache[project_id]

        project = store.get_project(project_id) or {}
        name = project_name or project.get("name") or f"Research Project {project_id[:8]}"
        saved_context = project.get("research_continuity")

        if saved_context and isinstance(saved_context, dict):
            ctx = ResearchContext(
                project_id=project_id,
                project_name=saved_context.get("project_name", name),
                objectives=saved_context.get("objectives", []),
                decisions=saved_context.get("decisions", []),
                failed_approaches=saved_context.get("failed_approaches", []),
                open_questions=saved_context.get("open_questions", []),
                datasets_used=saved_context.get("datasets_used", []),
                experiment_history=saved_context.get("experiment_history", []),
                updated_at=saved_context.get("updated_at", time.time()),
            )
        else:
            ctx = ResearchContext(project_id=project_id, project_name=name)

        self._memory_cache[project_id] = ctx
        return ctx

    def save_context(self, ctx: ResearchContext) -> None:
        """Persist updated research context to project store."""
        ctx.updated_at = time.time()
        self._memory_cache[ctx.project_id] = ctx
        store.update_project(ctx.project_id, {"research_continuity": ctx.to_dict()})

    def record_objective(self, project_id: str, title: str, description: str) -> Dict[str, Any]:
        ctx = self.get_or_create_context(project_id)
        obj_id = f"obj_{int(time.time() * 1000)}"
        obj = ResearchObjective(id=obj_id, title=title, description=description)
        ctx.objectives.append(asdict(obj))
        self.save_context(ctx)
        return asdict(obj)

    def record_decision(self, project_id: str, decision: str, rationale: str, alternatives: Optional[List[str]] = None) -> Dict[str, Any]:
        ctx = self.get_or_create_context(project_id)
        dec_id = f"dec_{int(time.time() * 1000)}"
        dec = ResearchDecision(
            id=dec_id,
            decision=decision,
            rationale=rationale,
            alternatives_considered=alternatives or [],
        )
        ctx.decisions.append(asdict(dec))
        self.save_context(ctx)
        return asdict(dec)

    def record_failed_approach(self, project_id: str, approach: str, failure_mode: str, lessons_learned: str) -> Dict[str, Any]:
        ctx = self.get_or_create_context(project_id)
        fail_id = f"fail_{int(time.time() * 1000)}"
        fa = FailedApproach(
            id=fail_id,
            approach=approach,
            failure_mode=failure_mode,
            lessons_learned=lessons_learned,
        )
        ctx.failed_approaches.append(asdict(fa))
        self.save_context(ctx)
        return asdict(fa)

    def record_open_question(self, project_id: str, question: str, priority: str = "medium") -> Dict[str, Any]:
        ctx = self.get_or_create_context(project_id)
        q_id = f"q_{int(time.time() * 1000)}"
        item = {"id": q_id, "question": question, "priority": priority, "timestamp": time.time()}
        ctx.open_questions.append(item)
        self.save_context(ctx)
        return item

    def record_experiment_outcome(self, project_id: str, experiment_name: str, config: Dict[str, Any], metrics: Dict[str, Any], conclusion: str) -> Dict[str, Any]:
        ctx = self.get_or_create_context(project_id)
        exp_id = f"exp_{int(time.time() * 1000)}"
        item = {
            "id": exp_id,
            "name": experiment_name,
            "config": config,
            "metrics": metrics,
            "conclusion": conclusion,
            "timestamp": time.time(),
        }
        ctx.experiment_history.append(item)
        self.save_context(ctx)
        return item

    def build_continuity_prompt_brief(self, project_id: str) -> str:
        """Produce a structured continuity brief injected into agent prompt."""
        ctx = self.get_or_create_context(project_id)
        lines = [f"=== RESEARCH CONTINUITY: {ctx.project_name} ==="]

        if ctx.objectives:
            lines.append("\n[Active Research Objectives]")
            for o in ctx.objectives[-3:]:
                lines.append(f"- {o.get('title')}: {o.get('description')} ({o.get('status')})")

        if ctx.decisions:
            lines.append("\n[Key Architectural & Research Decisions]")
            for d in ctx.decisions[-3:]:
                lines.append(f"- {d.get('decision')} | Rationale: {d.get('rationale')}")

        if ctx.failed_approaches:
            lines.append("\n[Failed Approaches & Lessons Learned — DO NOT REPEAT]")
            for f in ctx.failed_approaches[-3:]:
                lines.append(f"- {f.get('approach')} failed due to: {f.get('failure_mode')} (Lesson: {f.get('lessons_learned')})")

        if ctx.experiment_history:
            lines.append("\n[Recent Experiment History]")
            for e in ctx.experiment_history[-3:]:
                metrics_summary = ", ".join(f"{k}: {v}" for k, v in (e.get("metrics") or {}).items())
                lines.append(f"- {e.get('name')}: {metrics_summary} -> {e.get('conclusion')}")

        if ctx.open_questions:
            lines.append("\n[Open Research Questions]")
            for q in ctx.open_questions[-3:]:
                lines.append(f"- {q.get('question')} (Priority: {q.get('priority')})")

        lines.append("================================================")
        return "\n".join(lines)


# Global singleton instance
research_continuity = ResearchContinuityEngine()
