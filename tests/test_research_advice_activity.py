from backend.intent_router import handle_intent_message


def test_ml_planning_records_only_real_router_and_generation_steps(isolate_store):
    result = handle_intent_message("train a fraud detection model", session_id="ml-advice-trace")

    assert result["intent"] == "RESEARCH_START"
    assert "plain english" in result["response"].lower()
    assert [step["label"] for step in result["activity"]] == [
        "ML objective identified",
        "Model plan generated",
    ]
    assert all(step["status"] == "completed" for step in result["activity"])
