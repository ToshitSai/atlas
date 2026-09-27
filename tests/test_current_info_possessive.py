"""Regression: possessive latest-item questions are current facts, not news."""
from backend.current_info import extract_current_fact_request


def test_possessive_latest_entity_fact_is_parsed():
    request = extract_current_fact_request("What is Nova Author's latest book?")
    assert request is not None
    assert request.aspect == "latest"
    assert "Nova Author" in request.entity
