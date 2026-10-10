from backend.model_router import classify_task, select_providers

def test_nontrivial_requests_exclude_tiny_model():
    for q in (
        "Sally has 3 brothers and each has 2 sisters. How many sisters?",
        "Output strictly valid JSON and nothing else",
        "Find the 2023 ICML paper titled Hyperbolic Attention Networks",
        "Research the latest RMSNorm paper",
    ):
        d = classify_task(q)
        assert "mistral" not in select_providers(d)[0]

def test_tiny_model_only_for_greeting():
    d = classify_task("hello")
    assert d.flags["cheapest_ok"] is True
