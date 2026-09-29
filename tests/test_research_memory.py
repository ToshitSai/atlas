"""Directive §7 (research memory) + §2 (research question quality).

The hypothesis agent must SEE the executed experiment history (so it proposes
the next distinct experiment instead of repeating itself), and the stored
research question must be plain text — never markdown-wrapped LLM output that
the UI would render verbatim.
"""
import json

import pytest

from backend import llm as llm_mod


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    """No provider is reachable: query_llm returns None -> deterministic path."""
    monkeypatch.setattr(llm_mod, "query_llm", lambda *a, **k: None)


def _ds():
    return {"filename": "creditcard.csv", "rowCount": 284807, "columnCount": 31,
            "taskType": "classification", "targetCandidate": "Class",
            "isImbalanced": True, "minorityClassPct": 0.17}


# ---------------------------------------------------------------------------
# §7: research memory reaches the hypothesis prompt
# ---------------------------------------------------------------------------
def test_hypothesis_prompt_includes_previous_experiments(monkeypatch):
    captured = {}

    def fake_query(user_prompt, system_prompt, role=None, **kw):
        captured["prompt"] = user_prompt
        return json.dumps({
            "title": "Exp 2: SMOTE Oversampling",
            "hypothesis": "Oversampling recovers minority separation.",
            "hyperparams": "SMOTE k=5",
            "python_script": "print('hi')",
        })

    monkeypatch.setattr(llm_mod, "query_llm", fake_query)
    prev = [
        {"title": "Exp 1: Class-Weighted Gradient Boosting", "hypothesis": "weighting helps",
         "metricName": "PR-AUC", "metricValue": 0.73, "status": "PLATEAUED"},
    ]
    res = llm_mod.generate_hypothesis_llm(
        "Train a fraud detection model", _ds(),
        [{"name": "XGBoost", "metrics": {"pr_auc": 0.87}}], [], 2, previous_experiments=prev)

    assert res["title"] == "Exp 2: SMOTE Oversampling"
    prompt = captured["prompt"]
    assert "Previous Experiments" in prompt
    assert "Exp 1: Class-Weighted Gradient Boosting" in prompt
    assert "PR-AUC=0.73" in prompt
    assert "do NOT repeat" in prompt or "NOT repeat" in prompt


def test_hypothesis_prompt_without_history_has_no_memory_block(monkeypatch):
    captured = {}

    def fake_query(user_prompt, system_prompt, role=None, **kw):
        captured["prompt"] = user_prompt
        return json.dumps({"title": "t", "hypothesis": "h", "hyperparams": "x", "python_script": "s"})

    monkeypatch.setattr(llm_mod, "query_llm", fake_query)
    llm_mod.generate_hypothesis_llm("objective", _ds(), [], [], 1)
    assert "Previous Experiments" not in captured["prompt"]


def test_orchestrator_passes_real_history_to_hypothesis_agent():
    """The orchestrator call site must thread the accumulated tree nodes."""
    import inspect
    import agents.orchestrator as orch
    src = inspect.getsource(orch)
    assert "previous_experiments=tree_nodes" in src
    assert "generate_hypothesis_llm(" in src


# ---------------------------------------------------------------------------
# Fallback variety: no identical repeat titles within one run (§7)
# ---------------------------------------------------------------------------
def test_fallback_hypotheses_are_distinct_per_index():
    titles = []
    for idx in range(1, 6):
        res = llm_mod.generate_hypothesis_llm("fraud study", _ds(), [], [], idx)
        titles.append(res["title"])
    assert len(set(titles)) == len(titles), f"fallback repeated a title: {titles}"


# ---------------------------------------------------------------------------
# §2: research questions are stored as plain text
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ('**"How can fraud recall be improved under class imbalance?"**',
     "How can fraud recall be improved under class imbalance?"),
    ('__How can fraud recall be improved?__', "How can fraud recall be improved?"),
])
def test_research_question_strips_markdown(monkeypatch, raw, expected):
    monkeypatch.setattr(llm_mod, "query_llm", lambda *a, **k: raw)
    q = llm_mod.generate_research_question("Improve fraud detection")
    assert q == expected
    assert "**" not in q and "__" not in q


def test_research_question_fallback_still_works(monkeypatch):
    monkeypatch.setattr(llm_mod, "query_llm", lambda *a, **k: None)
    q = llm_mod.generate_research_question("Improve fraud detection")
    assert q.startswith("How can fraud")
