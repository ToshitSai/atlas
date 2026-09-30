from backend.intent_router import extract_research_topic


def test_command_style_research_topic_is_clean():
    assert extract_research_topic("do deep research for RAG and tell me") == "Retrieval-Augmented Generation (RAG)"
    assert extract_research_topic("research grouped patient validation") == "grouped patient validation"
    assert extract_research_topic("look into model calibration") == "model calibration"
