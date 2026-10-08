"""Classification contract for normal, live-lookup, and deep-study modes."""
import pytest

from backend.intent_router import classify_research_route, handle_intent_message


@pytest.mark.parametrize("message,mode", [
    ("What is machine learning?", "normal"),
    ("Explain overfitting.", "normal"),
    ("What is precision and recall?", "normal"),
    ("What is Python?", "normal"),
    ("Write a binary search algorithm.", "normal"),
    ("What is a neural network?", "normal"),
    ("Calculate 25 * 37.", "normal"),
    ("Explain REST APIs.", "normal"),
    ("What is a database?", "normal"),
    ("Difference between SQL and NoSQL.", "normal"),
    ("What is today's NVIDIA stock price?", "web_search"),
    ("What are the latest Python releases?", "web_search"),
    ("What happened in today's AI news?", "web_search"),
    ("Improve fraud detection.", "deep_research"),
    ("Investigate methods for reducing false negatives in fraud detection.", "deep_research"),
    ("Compare recent fraud detection approaches using research papers.", "deep_research"),
    ("Find suitable datasets for fraud detection and evaluate candidate models.", "deep_research"),
    ("Design experiments to determine whether SMOTE improves fraud detection.", "deep_research"),
    ("Study recent techniques for transformer-based tabular classification.", "deep_research"),
    ("Find a research gap in automated ML.", "deep_research"),
    ("Reproduce a machine-learning research paper experimentally.", "deep_research"),
    ("Compare XGBoost, Random Forest and neural networks on a selected dataset.", "deep_research"),
    ("Research why my model performs poorly and design experiments to improve it.", "deep_research"),
    ("Conduct a full autonomous ML research cycle for fraud detection.", "deep_research"),
    ("What is the best ML algorithm?", "normal"),
    ("Best model for fraud detection?", "normal"),
    ("How can I improve my model?", "normal"),
    ("Research fraud detection.", "deep_research"),
    # Semantic variations: no dependency on the literal word "research".
    ("How can we significantly improve the minority-class detection rate in this ML problem?", "deep_research"),
    ("Figure out why the model is failing and test possible solutions.", "deep_research"),
    ("Which approach actually works better on this dataset?", "deep_research"),
    ("Explore alternative modeling strategies and validate them.", "deep_research"),
    ("Can you investigate whether feature engineering is responsible for the improvement?", "deep_research"),
    ("Find out what is causing the performance degradation.", "deep_research"),
    ("Determine experimentally which preprocessing strategy is most effective.", "deep_research"),
    ("Try several scientifically justified approaches and learn from the results.", "deep_research"),
    # Negative educational ML cases remain fast.
    ("What is the best way to reduce overfitting?", "normal"),
    ("How does XGBoost work?", "normal"),
    ("Explain SMOTE.", "normal"),
    ("Why is recall important in fraud detection?", "normal"),
    ("Give me three ways to handle class imbalance.", "normal"),
    ("What is the difference between ROC-AUC and PR-AUC?", "normal"),
    ("Write a Python example using Random Forest.", "normal"),
])
def test_master_routing_matrix(message, mode):
    result = classify_research_route(message)
    assert {"mode", "confidence", "reason", "requires_web", "requires_deep_research", "complexity_score", "signals"} <= set(result)
    assert result["mode"] == mode
    assert 0 <= result["confidence"] <= 1
    assert result["requires_deep_research"] is (mode == "deep_research")


def _trace(steps):
    return {"trace": {"steps": steps}}


def test_deep_research_activity_contains_only_executed_stages(isolate_store, monkeypatch):
    import backend.deep_research as deep
    executed = [
        {"id": "t-0", "trace_id": "t", "stage": "planning", "status": "completed",
         "label": "Planned research approach", "detail": "Created 2 search queries", "timestamp": 1},
        {"id": "t-1", "trace_id": "t", "stage": "web_search", "status": "completed",
         "label": "Search completed: \"one\"", "detail": "Found 3 web results", "timestamp": 2},
    ]
    monkeypatch.setattr(deep, "run_deep_research", lambda goal, progress_callback=None, **kwargs: {
        "status": "ok", "report": "# Report\n\nEvidence-backed finding.",
        "sourceCount": 2, "subqueries": ["one", "two"], **_trace(executed),
    })
    result = handle_intent_message("Research this topic", session_id="deep-events")
    stages = [(event["stage"], event["status"]) for event in result["activity"]]
    assert result["intent"] == "DEEP_RESEARCH"
    # The activity list IS the executed trace: only real steps, in execution
    # order, and nothing re-derived after the fact.
    assert [("planning", "completed"), ("web_search", "completed")] == stages
    assert result["activity"][1]["label"] == 'Search completed: "one"'
    assert result["activity"][1]["detail"] == "Found 3 web results"
    assert not any(stage in {"baseline", "evaluation", "error_analysis"} for stage, _ in stages)
    assert all(event.get("detail") for event in result["activity"])


def test_deep_research_failure_is_visible_not_fabricated(isolate_store, monkeypatch):
    import backend.deep_research as deep
    failed = [
        {"id": "t-0", "trace_id": "t", "stage": "planning", "status": "completed",
         "label": "Planned research approach", "detail": "Created 1 search query", "timestamp": 1},
        {"id": "t-1", "trace_id": "t", "stage": "literature_search", "status": "failed",
         "label": "Literature search failed", "detail": "No verifiable sources were retrieved", "timestamp": 2},
    ]
    monkeypatch.setattr(deep, "run_deep_research", lambda goal, progress_callback=None, **kwargs: {
        "status": "no_sources", "report": "", "sourceCount": 0, "subqueries": ["one"], **_trace(failed),
    })
    result = handle_intent_message("Research this topic", session_id="deep-failure")
    assert any(event["stage"] == "literature_search" and event["status"] == "failed"
               for event in result["activity"])
    assert "won't pretend" in result["response"].lower()


def test_deep_research_pipeline_crash_is_honest(isolate_store, monkeypatch):
    """If the pipeline itself cannot run, the UI gets one honest failure row —
    not a fabricated stage history."""
    import backend.deep_research as deep

    def boom(goal, progress_callback=None, **kwargs):
        raise RuntimeError("search provider unreachable")

    monkeypatch.setattr(deep, "run_deep_research", boom)
    result = handle_intent_message("Research this topic", session_id="deep-crash")
    assert result["intent"] == "DEEP_RESEARCH"
    assert len(result["activity"]) == 1
    assert result["activity"][0]["status"] == "failed"
    assert "search provider unreachable" in result["activity"][0]["detail"]


def test_deep_research_streams_real_steps_as_they_happen(monkeypatch):
    """Live progress carries the ACTUAL search queries and result counts, in
    execution order — no generic filler, no post-hoc summary."""
    import backend.deep_research as deep
    import backend.ai_scientist_pipeline as aisp

    # The staged scientist pass is covered by test_ai_scientist_pipeline.py; keep
    # this test focused on deep_research's own streaming by no-op'ing it (it runs
    # first and would otherwise emit its own PLANNING events before ours).
    monkeypatch.setattr(aisp, "run_ai_scientist_pipeline", lambda *args, **kwargs: {})

    monkeypatch.setattr(deep, "plan_subqueries", lambda goal, max_subqueries=3, trace=None: ["first query", "second query"])
    monkeypatch.setattr(deep, "search_web", lambda query, limit=3: [
        {"title": f"Web hit {i} for {query}", "url": f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}_{i}", "snippet": "Evidence"}
        for i in range(3)
    ])
    monkeypatch.setattr(deep, "search_literature", lambda query, limit=2: [
        {"title": f"Paper on {query}", "url": f"https://doi.org/{query.replace(' ', '-')}", "abstract": "Real abstract text"},
    ])
    monkeypatch.setattr(deep, "_synthesize", lambda goal, queries, sources, trace=None, **kwargs: "# Report")
    events = []

    result = deep.run_deep_research("Test goal", progress_callback=events.append)

    assert result["status"] == "ok"
    # Callbacks receive the shared dict schema (SSE publishes **event).
    assert all(isinstance(event, dict) for event in events)
    labels = [event["label"] for event in events]
    # Real work items appear: the actual search query text and result counts.
    assert any('Searching: "first query"' in label for label in labels)
    assert any('Searching: "second query"' in label for label in labels)
    assert any("Found 3 web results" in (event.get("detail") or "") for event in events)
    assert any("Found 1 papers" in (event.get("detail") or "") for event in events)
    assert any("Collected 8 unique sources" in (event.get("detail") or "") for event in events)
    # Never generic filler: no "understanding your question" placeholders.
    assert not any("understanding" in label.lower() for label in labels)
    # Steps stream in execution order: planning starts first, search runs per query.
    assert events[0]["stage"] == deep.Stages.PLANNING and events[0]["status"] == "running"
    search_positions = [i for i, event in enumerate(events) if event["stage"] == deep.Stages.WEB_SEARCH]
    assert search_positions == sorted(search_positions) and len(search_positions) >= 4


def test_deep_research_trace_registry_roundtrip(monkeypatch):
    """begin_trace/poll_trace/finish_trace: polling clients see the same real
    steps while running, and the final list is returned for persistence."""
    from backend import step_trace as st

    trace = st.begin_trace("req-roundtrip", "deep_research")
    seen = []
    trace.add_callback(seen.append)
    trace.start_step(st.Stages.WEB_SEARCH, 'Searching: "history of quantum computing"')
    polled = st.poll_trace("req-roundtrip")
    assert polled["status"] == "running"
    assert polled["steps"][0]["label"] == 'Searching: "history of quantum computing"'
    assert seen and seen[0]["trace_id"] == "req-roundtrip"
    final = st.finish_trace("req-roundtrip")
    assert final == polled["steps"]
    assert st.poll_trace("req-roundtrip")["status"] == "completed"
    assert st.poll_trace("unknown-request") is None


def test_deep_research_drops_irrelevant_results(monkeypatch):
    """A generic title such as a TV programme must never enter a fraud report."""
    import backend.deep_research as deep
    import backend.ai_scientist_pipeline as aisp

    monkeypatch.setattr(aisp, "run_ai_scientist_pipeline", lambda *args, **kwargs: {})
    monkeypatch.setattr(deep, "plan_subqueries", lambda *args, **kwargs: [
        "improve credit card fraud detection model",
    ])
    monkeypatch.setattr(deep, "search_web", lambda *args, **kwargs: [
        {"title": "How (TV series)", "url": "https://example.test/how", "snippet": "British television programme"},
        {"title": "Credit card fraud detection methods", "url": "https://en.wikipedia.org/wiki/Credit_card_fraud", "snippet": "Fraud detection model evaluation"},
    ])
    monkeypatch.setattr(deep, "search_literature", lambda *args, **kwargs: [])
    monkeypatch.setattr(deep, "_synthesize", lambda goal, queries, sources, trace=None, **kwargs: "# Report")

    result = deep.run_deep_research("Improve credit card fraud detection")

    assert result["status"] == "ok"
    sources = result["trace"]  # report inputs are captured through the collector path
    assert result["sourceCount"] == 1


def test_deep_research_drops_low_quality_domains(monkeypatch):
    import backend.deep_research as deep
    import backend.ai_scientist_pipeline as aisp

    monkeypatch.setattr(aisp, "run_ai_scientist_pipeline", lambda *args, **kwargs: {})
    monkeypatch.setattr(deep, "plan_subqueries", lambda *args, **kwargs: ["history of coffee origins"])
    monkeypatch.setattr(deep, "search_web", lambda *args, **kwargs: [
        {"title": "Coffee history discussion", "url": "https://random-seo-blog.example/coffee", "snippet": "Coffee origins"},
        {"title": "History of coffee", "url": "https://en.wikipedia.org/wiki/History_of_coffee", "snippet": "Coffee originated in Ethiopia"},
    ])
    monkeypatch.setattr(deep, "search_literature", lambda *args, **kwargs: [])
    monkeypatch.setattr(deep, "_synthesize", lambda goal, queries, sources, trace=None, **kwargs: "# Report")

    result = deep.run_deep_research("history of coffee origins")

    assert result["status"] == "ok"
    assert result["sourceCount"] == 1
