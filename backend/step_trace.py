"""Unified step trace event system for real-time background work streaming.

Provides a shared event schema and emitter for all multi-step flows:
Deep Research, Dataset Search, ML Pipeline, Literature Search.

Every event is emitted because the corresponding backend action actually runs
(a search with its real query, a fetch, a ranking step) — never on a timer.
While a chat request is in flight its trace is registered under the request id
so the frontend can poll ``GET /api/activity/{requestId}``; when the request
finishes the collected step list is persisted with the assistant message so
reopening the conversation still shows the real trace.
"""
import time
import uuid
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from threading import Lock


# Canonical order shared by the UI and all orchestrators. Repeated events for
# one stage are still allowed, but a later stage may never leave an earlier
# stage running in the persisted trace.
_STAGE_ORDER = {
    name: index for index, name in enumerate([
        "research_question", "planning", "web_search", "literature_search",
        "source_reading", "verification", "dataset_search", "dataset_inspection",
        "dataset_ranking", "dataset_selection", "dataset_analysis",
        "baseline_training", "hypothesis_generation", "experiment_execution",
        "error_analysis", "synthesis", "cross_checking", "report_generation",
        "report", "completed",
    ], start=1)
}


@dataclass
class StepEvent:
    """Single step in a multi-step operation."""
    id: str
    trace_id: str
    stage: str
    status: str  # pending, running, completed, failed, skipped, waiting
    label: str
    detail: Optional[str] = None
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StepTrace:
    """Manages a collection of step events for a single operation."""

    def __init__(self, trace_id: Optional[str] = None, operation: str = "operation"):
        self.trace_id = trace_id or f"trace-{uuid.uuid4().hex[:12]}"
        self.operation = operation
        self.steps: List[StepEvent] = []
        self.active = True
        self._lock = Lock()
        self._callbacks: List[Callable[[StepEvent], None]] = []

    def add_callback(self, callback: Callable[[StepEvent], None]) -> None:
        self._callbacks.append(callback)

    def emit(self, stage: str, status: str, label: str, detail: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> StepEvent:
        """Emit a step event."""
        step = StepEvent(
            id=f"{self.trace_id}-{len(self.steps)}",
            trace_id=self.trace_id,
            stage=stage,
            status=status,
            label=label,
            detail=detail,
            metadata=metadata,
        )
        prior_closed = []
        with self._lock:
            current_order = _STAGE_ORDER.get(stage)
            if status == "running" and current_order is not None:
                for prior in self.steps:
                    if (prior.status == "running"
                            and _STAGE_ORDER.get(prior.stage, 0) < current_order):
                        prior.status = "completed"
                        prior.detail = prior.detail or "Completed before the next research stage began"
                        prior.timestamp = int(time.time() * 1000)
                        prior_closed.append(prior)
            self.steps.append(step)
        # Callbacks (SSE publishers, pollers) receive the plain dict form so
        # consumers never depend on the dataclass internals.
        payload = step.to_dict()
        for closed in prior_closed:
            closed_payload = closed.to_dict()
            for cb in self._callbacks:
                try:
                    cb(closed_payload)
                except Exception:
                    pass
        for cb in self._callbacks:
            try:
                cb(payload)
            except Exception:
                pass
        return step

    def start_step(self, stage: str, label: str, detail: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> StepEvent:
        return self.emit(stage, "running", label, detail, metadata)

    def complete_step(self, stage: str, label: str, detail: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> StepEvent:
        return self._finish_running(stage, "completed", label, detail, metadata)

    def fail_step(self, stage: str, label: str, detail: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> StepEvent:
        return self._finish_running(stage, "failed", label, detail, metadata)

    def _finish_running(self, stage: str, status: str, label: str, detail: Optional[str], metadata: Optional[Dict[str, Any]]) -> StepEvent:
        """Finish the most recent real operation for a stage in-place.

        A start and completion are lifecycle updates for one operation, not two
        independent UI rows. Re-emitting the same id lets the client upsert it
        and ensures no stale spinner remains after completion.
        """
        with self._lock:
            running = next((step for step in reversed(self.steps)
                            if step.stage == stage and step.status == "running"), None)
            if running:
                running.status = status
                running.label = label
                running.detail = detail
                running.metadata = metadata
                running.timestamp = int(time.time() * 1000)
                payload = running.to_dict()
            else:
                running = None
        if running is None:
            return self.emit(stage, status, label, detail, metadata)
        for callback in self._callbacks:
            try:
                callback(payload)
            except Exception:
                pass
        return running

    def skip_step(self, stage: str, label: str, detail: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> StepEvent:
        return self.emit(stage, "skipped", label, detail, metadata)

    def get_steps(self) -> List[StepEvent]:
        with self._lock:
            return list(self.steps)

    def mark_finished(self) -> None:
        self.active = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "traceId": self.trace_id,
            "operation": self.operation,
            "status": "running" if self.active else "completed",
            "steps": [s.to_dict() for s in self.get_steps()],
        }


# Global registry for active traces, keyed by the chat request id so the
# polling endpoint can find the live trace of an in-flight request.
_active_traces: Dict[str, StepTrace] = {}
_registry_lock = Lock()
_MAX_TRACES = 300


def get_trace(trace_id: str) -> Optional[StepTrace]:
    with _registry_lock:
        return _active_traces.get(trace_id)


def begin_trace(trace_id: str, operation: str = "chat_request") -> StepTrace:
    """Open (or reset) the live trace for an in-flight request."""
    with _registry_lock:
        trace = StepTrace(trace_id, operation)
        _active_traces[trace_id] = trace
        if len(_active_traces) > _MAX_TRACES:
            done = [k for k, t in _active_traces.items() if not t.active]
            for key in done[: len(done) // 2 or 1]:
                _active_traces.pop(key, None)
        return trace


def poll_trace(trace_id: str) -> Optional[Dict[str, Any]]:
    """Snapshot of a live trace for the polling endpoint.

    Returned steps are plain dicts matching the shared event schema, so
    polling clients see exactly what SSE consumers see. ``status`` is
    "running" while work is in flight, "completed" after finish_trace().
    Returns None for unknown request ids (the frontend then simply renders no
    panel — never a placeholder).
    """
    trace = get_trace(trace_id)
    if trace is None:
        return None
    return trace.to_dict()


def finish_trace(trace_id: str) -> List[Dict[str, Any]]:
    """Mark the trace completed (kept for late pollers) and return its real
    step dicts as the final, persisted list."""
    with _registry_lock:
        trace = _active_traces.get(trace_id)
    if trace is None:
        return []
    trace.mark_finished()
    return trace.to_dict()["steps"]


def discard_trace(trace_id: str) -> None:
    with _registry_lock:
        _active_traces.pop(trace_id, None)


def create_trace(operation: str, trace_id: Optional[str] = None) -> StepTrace:
    """Create and register a new step trace (kept for direct flow use)."""
    return begin_trace(trace_id or f"trace-{uuid.uuid4().hex[:12]}", operation)


def event_to_activity(step: StepEvent, request_id: Optional[str] = None) -> Dict[str, Any]:
    """Map a StepEvent onto the chat activity-event contract (make_activity).

    The chat contract carries requestId/stage/status/label/timestamp; the step
    id ties each row to its trace entry so updates upsert by id.
    """
    data = step.to_dict()
    activity = {
        "id": data["id"],
        "requestId": request_id or data["trace_id"],
        "jobId": data["trace_id"],
        "stage": data["stage"],
        "status": data["status"],
        "label": data["label"],
        "detail": data.get("detail"),
        "timestamp": data["timestamp"],
    }
    return activity


# Standard stage names for consistency across flows
class Stages:
    # Deep Research
    PLANNING = "planning"
    WEB_SEARCH = "web_search"
    LITERATURE_SEARCH = "literature_search"
    SOURCE_READING = "source_reading"
    CROSS_CHECKING = "cross_checking"
    SYNTHESIS = "synthesis"
    VERIFICATION = "verification"
    REPORT_GENERATION = "report_generation"

    # Dataset Search
    DATASET_SEARCH = "dataset_search"
    DATASET_INSPECTION = "dataset_inspection"
    DATASET_RANKING = "dataset_ranking"
    DATASET_SELECTION = "dataset_selection"

    # ML Pipeline
    RESEARCH_QUESTION = "research_question"
    DATASET_ANALYSIS = "dataset_analysis"
    BASELINE_TRAINING = "baseline_training"
    HYPOTHESIS_GENERATION = "hypothesis_generation"
    EXPERIMENT_EXECUTION = "experiment_execution"
    ERROR_ANALYSIS = "error_analysis"
    REPORT = "report"

    # General
    COMPLETED = "completed"
    FAILED = "failed"


# Human-readable labels for stages
STAGE_LABELS = {
    Stages.PLANNING: "Planning the investigation",
    Stages.WEB_SEARCH: "Searching relevant sources",
    Stages.LITERATURE_SEARCH: "Searching academic literature",
    Stages.SOURCE_READING: "Evaluating sources",
    Stages.CROSS_CHECKING: "Cross-checking evidence",
    Stages.SYNTHESIS: "Synthesizing evidence",
    Stages.VERIFICATION: "Verifying citations",
    Stages.REPORT_GENERATION: "Preparing research report",
    Stages.DATASET_SEARCH: "Searching datasets",
    Stages.DATASET_INSPECTION: "Inspecting dataset",
    Stages.DATASET_RANKING: "Ranking candidates",
    Stages.DATASET_SELECTION: "Selecting dataset",
    Stages.RESEARCH_QUESTION: "Understanding research question",
    Stages.DATASET_ANALYSIS: "Analyzing dataset",
    Stages.BASELINE_TRAINING: "Establishing baseline models",
    Stages.HYPOTHESIS_GENERATION: "Testing competing explanations",
    Stages.EXPERIMENT_EXECUTION: "Executing experiment",
    Stages.ERROR_ANALYSIS: "Analyzing errors",
    Stages.REPORT: "Preparing research report",
}
