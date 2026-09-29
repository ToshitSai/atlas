"""Tests for the structured research-state endpoint (§14) and the §9 report
sections.

The research-state endpoint is the server-side structured research state: the
UI (or any API client) must be able to render the whole research experience
from it. Every value must come from real persisted artifacts — these tests
seed real artifacts and assert the exact numbers flow through, plus that
missing artifacts render as honest placeholders, never invented values.
"""
import pytest

from conftest import store_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _seed_project(store, pid="proj-rs"):
    store.create_project(pid, "Research: fraud study", "Train a fraud detection model",
                         "creditcard.csv", 60, None)
    return pid


def _seed_artifacts(store, pid="proj-rs"):
    """Seed a realistic, fully-populated run: dataset, 2 baselines, root node,
    one follow-up experiment, error analysis with bootstrap CI, literature."""
    store.save_dataset_report(pid, {
        "repoId": "mlg/credit-card-fraud", "filename": "creditcard.csv",
        "rowCount": 284807, "columnCount": 31, "targetCandidate": "Class",
        "taskType": "classification", "isImbalanced": True, "minorityClassPct": 0.17,
    })
    store.save_baselines(pid, [
        {"id": "b1", "name": "Logistic Regression", "type": "Linear", "status": "COMPLETED",
         "metrics": {"f1": 0.71, "pr_auc": 0.66, "precision": 0.75, "recall": 0.68}},
        {"id": "b2", "name": "Random Forest", "type": "Ensemble", "status": "COMPLETED",
         "metrics": {"f1": 0.76, "pr_auc": 0.72, "precision": 0.80, "recall": 0.73}},
    ])
    store.save_tree_nodes(pid, [
        {"experimentId": "exp-baseline", "parentId": None, "title": "Baseline: Random Forest",
         "hypothesis": "Establish baseline performance.", "status": "COMPLETED",
         "metricName": "PR-AUC", "metricValue": 0.72,
         "allMetrics": {"pr_auc": 0.72, "f1": 0.76}},
        {"experimentId": "exp-1", "parentId": "exp-baseline", "title": "XGBoost + class weights",
         "hypothesis": "Class weighting improves minority recall.", "status": "COMPLETED",
         "metricName": "PR-AUC", "metricValue": 0.81,
         "allMetrics": {"pr_auc": 0.81, "f1": 0.79}},
    ])
    store.save_error_analysis(pid, {
        "falsePositivesCount": 12, "falseNegativesCount": 9,
        "failureDiagnosis": "Minority-class recall remains the primary weakness.",
        "bootstrapCI": {"ci_lower": 0.77, "ci_upper": 0.85}, "bootstrapIterations": 200,
    })
    store.save_literature(pid, [
        {"title": "XGBoost: A Scalable Tree Boosting System", "url": "https://arxiv.org/abs/1603.02754", "year": "2016"},
        {"title": "Learning from Imbalanced Data", "url": "https://link.springer.com/article/10.1007/s10111-008-0083-4", "year": "2009"},
    ])
    store.save_report(pid, "# Report\n\nFindings below.")
    store.update_project(pid, {
        "researchQuestion": "How can fraud detection be improved on imbalanced transaction data?",
        "bestModel": "XGBoost + class weights", "bestMetric": "PR-AUC 0.81",
        "runState": "REPORT", "status": "COMPLETED",
        "stageStates": {
            "research_question": "COMPLETED", "dataset_eda": "COMPLETED",
            "literature_search": "COMPLETED", "baseline_training": "COMPLETED",
            "hypothesis_generation": "COMPLETED", "sandboxed_execution": "COMPLETED",
            "error_diagnostics": "COMPLETED", "research_report": "COMPLETED",
        },
        "agentLogs": [
            {"agent": "PLANNER_AGENT", "message": "Research goal understood.", "level": "INFO", "timestamp": "2026-09-29T00:00:00Z"},
            {"agent": "CODING_AGENT", "message": "Experiment 001 completed.", "level": "INFO", "timestamp": "2026-09-29T00:01:00Z"},
        ],
    })


@pytest.fixture
def api_client():
    TestClient = pytest.importorskip("fastapi.testclient").TestClient
    from backend.main import app
    with TestClient(app) as client:
        yield client


# ---------------------------------------------------------------------------
# §14 structured research state
# ---------------------------------------------------------------------------
def test_research_state_returns_structured_session(api_client, isolate_store):
    pid = _seed_project(isolate_store)
    _seed_artifacts(isolate_store, pid)

    r = api_client.get(f"/api/projects/{pid}/research-state")
    assert r.status_code == 200
    body = r.json()

    # The full §14 shape is present.
    for key in ("researchSession", "researchGoal", "researchQuestions", "literature",
                "datasets", "hypotheses", "experiments", "experimentResults",
                "analysis", "currentStage", "currentStatus", "researchHistory",
                "finalReport", "pipeline", "reasoning"):
        assert key in body, f"missing §14 key: {key}"

    assert body["researchGoal"] == "Train a fraud detection model"
    assert body["researchSession"]["status"] == "COMPLETED"
    assert body["researchSession"]["currentStage"] == "REPORT"
    assert body["researchQuestions"] == ["How can fraud detection be improved on imbalanced transaction data?"]
    assert len(body["literature"]) == 2
    assert body["datasets"][0]["rowCount"] == 284807
    assert len(body["experiments"]) == 2  # root + follow-up
    assert body["experimentResults"][0]["metricValue"] == 0.81  # follow-ups first? sorted? (checked below)
    assert body["analysis"]["bootstrapCI"]["ci_lower"] == 0.77
    assert len(body["researchHistory"]) == 2
    assert body["finalReport"].startswith("# Report")
    assert [r_["message"] for r_ in body["reasoning"]][:2] == [
        "Research goal understood.", "Experiment 001 completed."]


def test_research_state_pipeline_states_come_from_real_artifacts(api_client, isolate_store):
    pid = _seed_project(isolate_store)
    _seed_artifacts(isolate_store, pid)
    body = api_client.get(f"/api/projects/{pid}/research-state").json()

    stages = {s["id"]: s for s in body["pipeline"]}
    assert len(stages) >= 11

    # Completed stages carry REAL detail values, not invented ones.
    assert stages["literature"]["state"] == "COMPLETED"
    assert "2 relevant papers analyzed" == stages["literature"]["detail"]
    assert stages["dataset"]["detail"].startswith("mlg/credit-card-fraud — 284,807 rows")
    assert "best: XGBoost + class weights" in stages["baseline"]["detail"]
    assert stages["experiment"]["state"] == "COMPLETED"
    assert "0.81" in stages["experiment"]["detail"]
    assert "0.77" in stages["error-analysis"]["detail"] and "0.85" in stages["error-analysis"]["detail"]
    assert stages["report"]["detail"] == "Report ready"


def test_research_state_is_honest_when_artifacts_missing(api_client, isolate_store):
    """A fresh project must show honest pending states, never fake values (§15)."""
    pid = _seed_project(isolate_store, "proj-empty")
    r = api_client.get(f"/api/projects/{pid}/research-state")
    assert r.status_code == 200
    body = r.json()

    assert body["literature"] == []
    assert body["datasets"] == []
    assert body["experiments"] == []
    assert body["experimentResults"] == []
    assert body["analysis"] is None
    assert body["finalReport"] is None

    stages = {s["id"]: s for s in body["pipeline"]}
    assert stages["literature"]["state"] == "PENDING"
    assert stages["literature"]["detail"] == "Not available yet"
    assert stages["experiment"]["state"] == "PENDING"
    assert stages["experiment"]["detail"] == "Not available yet"
    assert stages["dataset"]["detail"] == "Not available yet"
    assert stages["report"]["state"] == "PENDING"


def test_research_state_404_for_unknown_project(api_client):
    assert api_client.get("/api/projects/proj-does-not-exist/research-state").status_code == 404


def test_running_project_shows_running_pipeline_state(api_client, isolate_store):
    """While the orchestrator runs, stages in RUNNING show running language."""
    pid = _seed_project(isolate_store, "proj-running")
    isolate_store.update_stage_state(pid, "literature_search", "RUNNING")
    isolate_store.update_stage_state(pid, "baseline_training", "RUNNING")
    body = api_client.get(f"/api/projects/{pid}/research-state").json()

    stages = {s["id"]: s for s in body["pipeline"]}
    assert stages["literature"]["state"] == "RUNNING"
    assert stages["literature"]["detail"] == "Searching..."
    assert stages["baseline"]["state"] == "RUNNING"
    assert stages["baseline"]["detail"] == "Training..."
    assert stages["experiment"]["state"] == "PENDING"


# ---------------------------------------------------------------------------
# §9 report sections
# ---------------------------------------------------------------------------
def _report_inputs():
    project = {"name": "Fraud Study", "objective": "Train a fraud detection model",
               "datasetName": "creditcard.csv", "bestModel": "XGBoost", "bestMetric": "PR-AUC 0.81",
               "budgetMins": 60}
    dataset_report = {"filename": "creditcard.csv", "rowCount": 284807, "columnCount": 31,
                      "targetCandidate": "Class", "taskType": "classification",
                      "missingValuesTotal": 0, "duplicateRows": 1081, "detectedIssues": []}
    baselines = [{"name": "Logistic Regression", "type": "Linear", "status": "COMPLETED",
                  "trainingTime": "1.2s", "metrics": {"f1": 0.71, "pr_auc": 0.66}}]
    tree_nodes = [
        {"experimentId": "exp-baseline", "parentId": None, "title": "Baseline: RF",
         "hypothesis": "baseline", "status": "COMPLETED", "metricName": "PR-AUC",
         "metricValue": 0.72, "hyperparams": "{}", "executionTime": "0.8s"},
        {"experimentId": "exp-1", "parentId": "exp-baseline", "title": "XGBoost + weights",
         "hypothesis": "weights help", "status": "COMPLETED", "metricName": "PR-AUC",
         "metricValue": 0.81, "hyperparams": "{}", "executionTime": "2.1s"},
    ]
    error_analysis = {"falsePositivesCount": 12, "falseNegativesCount": 9,
                      "failureDiagnosis": "recall weak", "bootstrapIterations": 200,
                      "bootstrapCI": {"ci_lower": 0.77, "ci_upper": 0.85}}
    return project, dataset_report, baselines, tree_nodes, error_analysis


def test_report_contains_all_required_sections():
    from backend.report_generator import generate_research_report
    project, dr, baselines, nodes, ea = _report_inputs()
    md = generate_research_report(project, dr, baselines, nodes, ea, literature=[])

    for section in ("## 1. Executive Summary", "## 2. Dataset Analysis", "## 3. Baseline Model Benchmarks",
                    "## 4. Autonomous Experimentation Tree", "## 5. Literature Review",
                    "## 6. Error Analysis", "## 7. Statistical Analysis", "## 8. Findings",
                    "## 9. Limitations", "## 10. Future Work"):
        assert section in md, f"report missing section: {section}"


def test_report_uses_real_numbers_and_honest_literature_note():
    from backend.report_generator import generate_research_report
    project, dr, baselines, nodes, ea = _report_inputs()

    md = generate_research_report(project, dr, baselines, nodes, ea, literature=[
        {"title": "XGBoost: A Scalable Tree Boosting System", "url": "https://arxiv.org/abs/1603.02754", "year": "2016"}])
    assert "[XGBoost: A Scalable Tree Boosting System](https://arxiv.org/abs/1603.02754) (2016)" in md
    assert "95% Bootstrap Confidence Interval" in md and "0.77" in md and "0.85" in md
    assert "mean 0.7650" in md  # mean of 0.72 and 0.81
    assert "XGBoost + weights** with PR-AUC = 0.81 (see experiment exp-1)" in md

    # Honest note when no papers were retrieved (§15).
    md_empty = generate_research_report(project, dr, baselines, nodes, ea, literature=[])
    assert "Literature search was unavailable in this run" in md_empty
