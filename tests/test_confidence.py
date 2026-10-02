from backend.confidence import assess_confidence


def test_established_explanation_is_high_without_fake_sources():
    result = assess_confidence("What is gradient descent?", {"intent": "EXPLANATION", "response": "Gradient descent iteratively updates parameters."})
    assert result["overall"]["level"] == "high"
    assert result["evidence"]["sources_used"] == 0


def test_dataset_specific_ml_prediction_is_not_high():
    result = assess_confidence("Will SMOTE improve my fraud model?", {"intent": "RESEARCH_START", "response": "SMOTE may help, depending on validation."})
    assert result["overall"]["level"] == "medium"
    assert result["verification"]
    assert "no experiment" in "; ".join(result["basis"]).lower()


def test_unretrieved_current_claim_is_low_and_honest():
    result = assess_confidence("What are the latest findings on RAG?", {"intent": "CURRENT_INFORMATION", "response": "I could not retrieve sources."})
    assert result["overall"]["level"] == "low"
    assert result["unknown"]


def test_multi_source_research_is_source_supported_not_experiment_claim():
    sources = [{"url": f"https://example.org/{n}"} for n in range(3)]
    result = assess_confidence("Research RAG", {"intent": "DEEP_RESEARCH", "response": "The sources report a trend.", "sources": sources})
    assert result["overall"]["level"] == "high"
    assert result["claims"][0]["kind"] == "source_supported"
    assert result["evidence"]["experiment_ids"] == []


def test_sources_do_not_turn_personal_ml_prediction_into_a_high_confidence_result():
    sources = [{"url": f"https://example.org/{n}"} for n in range(4)]
    result = assess_confidence("Will SMOTE improve my fraud model?", {"intent": "DEEP_RESEARCH", "response": "SMOTE may help.", "sources": sources})
    assert result["overall"]["level"] == "medium"
    assert "no experiment" in "; ".join(result["basis"]).lower()


def test_hypothesis_is_marked_proposed_not_confident_fact():
    result = assess_confidence("Improve my model", {"intent": "RESEARCH_START", "response": "Hypothesis: class weighting may improve recall."})
    assert result["claims"][0]["kind"] == "hypothesis"
    assert result["claims"][0]["status"] == "proposed"
    assert "level" not in result["claims"][0]
