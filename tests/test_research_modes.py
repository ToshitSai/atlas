"""Research-mode workflow tests (autonomous / guided / manual).

Covers the workflow directive:
  * §2  modes behave differently (autonomous never stops unnecessarily,
        guided asks, manual defers every stage)
  * §3  autonomous dataset selection with a confidence gate
  * §5/§6  real activity events with the correlation contract
  * §11 WAITING_FOR_USER only for genuine decisions
  * §13 honest failure when dataset discovery breaks
  * §15 the same flow works across many research goals (no fraud hard-coding)
  * §19 normal questions must NOT trigger ML research

All network, ML runtime, and pipeline launch dependencies are stubbed; the
store is isolated by tests/conftest.py.
"""
import pytest

from backend import research_modes as rm


# ---------------------------------------------------------------------------
# 1. Mode resolution and parsing
# ---------------------------------------------------------------------------
def test_resolve_mode_priority_request_over_session_over_settings():
    assert rm.resolve_mode("AUTONOMOUS", {"research_mode": "GUIDED"}, {"researchMode": "MANUAL"}) == "AUTONOMOUS"
    assert rm.resolve_mode(None, {"research_mode": "MANUAL"}, {"researchMode": "AUTONOMOUS"}) == "MANUAL"
    assert rm.resolve_mode(None, None, {"researchMode": "AUTONOMOUS"}) == "AUTONOMOUS"
    assert rm.resolve_mode(None, None, {}) == "GUIDED"  # directive default


def test_resolve_mode_aliases_and_garbage():
    assert rm.normalize_mode("auto") == "AUTONOMOUS"
    assert rm.normalize_mode("USER_APPROVAL") == "GUIDED"
    assert rm.normalize_mode("banana") is None
    assert rm.normalize_mode(None) is None
    assert rm.resolve_mode("banana", None, None) == "GUIDED"


def test_mode_switch_phrasing_detected_but_goals_not():
    assert rm.parse_mode_from_message("switch to autonomous mode") == "AUTONOMOUS"
    assert rm.parse_mode_from_message("use guided mode from now on") == "GUIDED"
    assert rm.parse_mode_from_message("run it step by step please") == "MANUAL"
    # A research goal that merely contains domain words must NOT flip modes.
    assert rm.parse_mode_from_message("Improve fraud detection") is None
    assert rm.parse_mode_from_message("improve autonomous vehicle detection") is None
    assert rm.parse_mode_from_message("Predict house prices") is None


def test_activity_event_contract():
    ev = rm.make_activity("req-1", "job-1", "DATASET_SEARCH", "completed", "Found 4 candidate datasets")
    assert ev["requestId"] == "req-1"
    assert ev["jobId"] == "job-1"
    assert ev["stage"] == "DATASET_SEARCH"
    assert ev["status"] == "completed"
    assert ev["label"] == "Found 4 candidate datasets"
    assert isinstance(ev["timestamp"], int) and ev["timestamp"] > 10**12  # ms epoch


# ---------------------------------------------------------------------------
# 2. Selection decision (the confidence gate)
# ---------------------------------------------------------------------------
def _comp(*scores):
    cands = []
    for i, s in enumerate(scores):
        cands.append({
            "repoId": f"owner/ds-{i}", "score": s,
            "reasons": [f"Matches the goal terms: topic-{i}."] if s >= 20 else ["License not stated."],
            "downloads": 1000, "license": "mit",
        })
    return {"goal": "g", "candidates": cands, "recommendation": cands[0] if cands else None}


def test_autonomous_selects_a_clear_winner():
    decision = rm.selection_decision(_comp(62, 30, 12), rm.AUTONOMOUS)
    assert decision["decision"] == "AUTO_SELECT"
    assert decision["dataset"]["repoId"] == "owner/ds-0"


def test_autonomous_pauses_on_near_tie():
    decision = rm.selection_decision(_comp(55, 53), rm.AUTONOMOUS)
    assert decision["decision"] == "ASK_USER"


def test_autonomous_pauses_when_nothing_clearly_fits():
    decision = rm.selection_decision(_comp(10, 5), rm.AUTONOMOUS)
    assert decision["decision"] == "ASK_USER"


def test_autonomous_pauses_when_no_candidates():
    assert rm.selection_decision({"candidates": []}, rm.AUTONOMOUS)["decision"] == "NO_CANDIDATES"


def test_guided_always_asks_even_with_clear_winner():
    decision = rm.selection_decision(_comp(90, 10), rm.GUIDED)
    assert decision["decision"] == "ASK_USER"


# ---------------------------------------------------------------------------
# 3. The 7 research goals all reach the same flow (generality, §15)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("goal", [
    "Train a fraud detection model",
    "Predict house prices",
    "Detect anomalies in sensor data",
    "Classify customer reviews",
    "Forecast sales",
    "Train a spam detection classifier",
])
def test_every_goal_classifies_as_research_start(goal):
    from backend.intent_router import classify_intent
    assert classify_intent(goal) == "RESEARCH_START"


@pytest.mark.parametrize("goal", [
        "Improve fraud detection",
])
def test_concrete_improvement_goals_start_research(goal):
    """Corpus-labeled ML improvement objectives use full deep research."""
    from backend.intent_router import classify_intent
    assert classify_intent(goal) == "DEEP_RESEARCH"


def test_normal_question_is_not_research():
    from backend.intent_router import classify_intent
    assert classify_intent("What is Python?") != "RESEARCH_START"


# ---------------------------------------------------------------------------
# 4. Chat-level behavior via the API
# ---------------------------------------------------------------------------
@pytest.fixture
def api_client():
    TestClient = pytest.importorskip("fastapi.testclient").TestClient
    from backend.main import app
    with TestClient(app) as client:
        yield client


def _stub_hf(monkeypatch, scores=(62, 30), recommend=None):
    """Deterministic dataset discovery: no network, fixed ranking."""
    from backend import hf_datasets as hf
    comp = _comp(*scores)
    if recommend is not None:
        comp["recommendation"] = comp["candidates"][recommend]
    monkeypatch.setattr(hf, "search_datasets", lambda goal, limit=6: list(comp["candidates"]))
    monkeypatch.setattr(hf, "compare_and_recommend", lambda cands, goal, top_n=4: comp)
    monkeypatch.setattr(hf, "inspect_dataset",
                        lambda repo_id: {"rowCount": 284807, "targetColumn": "Class",
                                         "featureCount": 30, "minorityClassPct": 0.17,
                                         "availableSplits": {"train": 1}, "license": "mit"})
    return comp


def _stub_launch(monkeypatch, pid="proj-autotest"):
    def fake_approve(repo_id, research_goal, budget=60, max_experiments=5):
        return {
            "action": "START_RESEARCH", "projectId": pid,
            "project": {"id": pid, "status": "RUNNING", "datasetName": repo_id},
            "dataset": {"repoId": repo_id},
            "response": "started",
        }
    monkeypatch.setattr("backend.main._approve_dataset", fake_approve)


def _confirm_research_start(api_client, conversation_id, mode):
    """RESEARCH_START gives goal-specific guidance before discovery runs."""
    offer = api_client.post("/api/chat", json={
        "message": "Train a fraud detection model", "conversationId": conversation_id,
        "requestId": f"req-{conversation_id}-offer", "messageId": f"msg-{conversation_id}-offer",
        "researchMode": mode,
    })
    assert offer.status_code == 200
    offer_body = offer.json()
    assert offer_body["intent"] == "RESEARCH_START"
    assert offer_body["action"] == "NONE"
    assert "**Task type:** binary classification" in offer_body["response"]
    assert "Want me to search for relevant datasets?" in offer_body["response"]
    assert offer_body["pendingAction"]["type"] == "START_RESEARCH"

    confirmed = api_client.post("/api/chat", json={
        "message": "yes", "conversationId": conversation_id,
        "requestId": f"req-{conversation_id}-confirm", "messageId": f"msg-{conversation_id}-confirm",
        "researchMode": mode,
    })
    assert confirmed.status_code == 200
    return confirmed


def test_autonomous_mode_selects_and_continues(api_client, monkeypatch):
    _stub_hf(monkeypatch, scores=(62, 30))
    _stub_launch(monkeypatch, pid="proj-autotest")
    r = _confirm_research_start(api_client, "conv-auto", "AUTONOMOUS")
    body = r.json()
    # NOT stopped at the recommendation gate — the pipeline actually launched.
    assert body["action"] == "START_RESEARCH"
    assert body["projectId"] == "proj-autotest"
    assert body["selectionMode"] == "AUTONOMOUS"
    assert body["selectedDataset"]
    assert "Selected" in body["response"]
    assert "Choose a dataset below to continue" not in body["response"]
    # §5/§6: real activity events with the full correlation contract.
    stages = [(e["stage"], e["status"]) for e in body["activity"]]
    assert ("DATASET_SEARCH", "completed") in stages
    assert ("DATASET_EVALUATION", "completed") in stages
    assert ("DATASET_SELECTED", "completed") in stages
    assert all(e["stage"] != "WAITING_FOR_USER" for e in body["activity"])
    for e in body["activity"]:
        assert e["requestId"] == "req-conv-auto-confirm"
        assert e["jobId"]
        assert e["label"] and e["timestamp"]


def test_guided_mode_still_pauses_for_approval(api_client, monkeypatch):
    _stub_hf(monkeypatch, scores=(62, 30))
    r = _confirm_research_start(api_client, "conv-guided", "GUIDED")
    body = r.json()
    assert body["action"] == "RECOMMEND_DATASETS"
    # Guided pause = dataset cards awaiting explicit user approval; the
    # approval runs through /api/datasets/approve, not a pendingAction.
    assert body["candidates"] and body["recommendation"]
    assert "Choose a dataset below to continue" in body["response"]
    assert body["projectId"] is None
    assert any(e["stage"] == "WAITING_FOR_USER" for e in body["activity"])


def test_autonomous_mode_asks_when_candidates_are_close(api_client, monkeypatch):
    _stub_hf(monkeypatch, scores=(55, 53))
    r = _confirm_research_start(api_client, "conv-tie", "AUTONOMOUS")
    body = r.json()
    # §14: no arbitrary selection on a near-tie — pause with the comparison.
    assert body["action"] == "RECOMMEND_DATASETS"
    assert "strong candidates" in body["response"]
    assert any(e["stage"] == "WAITING_FOR_USER" for e in body["activity"])
    assert body.get("projectId") is None


def test_dataset_search_failure_is_honest(api_client, monkeypatch):
    from backend import hf_datasets as hf
    monkeypatch.setattr(hf, "search_datasets", lambda goal, limit=6: (_ for _ in ()).throw(RuntimeError("HF unreachable")))
    r = _confirm_research_start(api_client, "conv-fail", "AUTONOMOUS")
    body = r.json()
    assert "Dataset search failed" in body["response"]
    assert body["action"] != "START_RESEARCH"
    assert any(e["stage"] == "DATASET_SEARCH" and e["status"] == "failed" for e in body["activity"])


def test_in_chat_mode_switch(api_client):
    r = api_client.post("/api/chat", json={
        "message": "switch to autonomous mode", "conversationId": "conv-mode",
        "requestId": "req-mode-1", "messageId": "msg-mode-1",
    })
    body = r.json()
    assert body["action"] == "SET_RESEARCH_MODE"
    assert body["researchMode"] == "AUTONOMOUS"


def test_normal_question_gets_normal_answer_no_research(api_client, monkeypatch):
    _stub_hf(monkeypatch, scores=(62, 30))  # would happily launch if wrongly routed
    _stub_launch(monkeypatch)
    r = api_client.post("/api/chat", json={
        "message": "What is Python?", "conversationId": "conv-plain",
        "requestId": "req-plain-1", "messageId": "msg-plain-1",
        "researchMode": "AUTONOMOUS",
    })
    body = r.json()
    assert body["action"] not in ("START_RESEARCH", "RECOMMEND_DATASETS")
    assert body.get("projectId") is None
    assert body["response"].strip()


# ---------------------------------------------------------------------------
# 5. Explicit run-state machine in the orchestrator (§10)
# ---------------------------------------------------------------------------
def test_set_run_state_validates_and_persists(isolate_store):
    from agents.orchestrator import _set_run_state
    isolate_store.create_project("proj-state", "n", "objective", "d.csv", 60, None)
    _set_run_state("proj-state", "EDA")
    assert isolate_store.get_project("proj-state")["runState"] == "EDA"
    _set_run_state("proj-state", "NOT-A-STATE", note="oops")
    assert isolate_store.get_project("proj-state")["runState"] == "FAILED"


def _run_stub_pipeline(isolate_store, monkeypatch, tmp_path, exit_code):
    import pandas as pd
    import agents.orchestrator as orch

    class _StaticModel:
        def predict(self, X):
            return [0] * len(X)

    def fake_train(file_path, target_col, task_type="classification", test_path=None):
        baselines = [{
            "id": "base-1", "name": "Stub LR", "type": "Linear", "hyperparams": "stub",
            "metrics": {"f1": 0.5, "pr_auc": 0.5, "accuracy": 0.8, "precision": 0.5, "recall": 0.5},
            "trainingTime": "0s", "status": "COMPLETED",
        }]
        X_test = pd.DataFrame({"v1": [1, 2, 3, 4]})
        y_test = pd.Series([0, 1, 0, 0])
        return baselines, _StaticModel(), X_test, y_test

    ds = tmp_path / "train.csv"
    rows = ["v1,v2,is_fraud"] + [f"{i},{i % 5},{1 if i % 8 == 0 else 0}" for i in range(40)]
    ds.write_text("\n".join(rows) + "\n")
    pid = "proj-runstate"
    isolate_store.create_project(pid, "n", "Improve fraud detection on stub data", "train.csv", 60, None,
                                 dataset_path=str(ds))
    isolate_store.update_project(pid, {"maxExperiments": 1})

    monkeypatch.setattr(orch, "EXPERIMENTS_BASE_DIR", str(tmp_path / "experiments"))
    monkeypatch.setattr(orch, "search_literature", lambda *a, **k: [])
    monkeypatch.setattr(orch.tracker, "log_project_telemetry", lambda *a, **k: None)
    monkeypatch.setattr(orch, "train_baselines", fake_train)
    monkeypatch.setattr(orch, "execute_sandboxed_experiment", lambda script, path, timeout_sec=60, extra_env=None: {
        "sandboxMode": "Process Sandbox", "dockerAvailable": False, "exitCode": exit_code,
        "runtime": "0.1s", "stdout": "", "stderr": "", "metrics": {}, "success": exit_code == 0,
    })
    orch._orchestrate_pipeline(pid, str(ds), None, None)
    return isolate_store.get_project(pid)


def test_pipeline_run_state_reaches_completed(isolate_store, monkeypatch, tmp_path):
    proj = _run_stub_pipeline(isolate_store, monkeypatch, tmp_path, exit_code=0)
    # The experiment failed to improve (exit 0, no metrics) -> status COMPLETED
    # because core stages finished; runState must be a terminal state either way.
    assert proj["runState"] == "COMPLETED"


def test_pipeline_run_state_reaches_failed(isolate_store, monkeypatch, tmp_path):
    proj = _run_stub_pipeline(isolate_store, monkeypatch, tmp_path, exit_code=1)
    assert proj["status"] == "FAILED"
    assert proj["runState"] == "FAILED"
