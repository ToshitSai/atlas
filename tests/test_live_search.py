"""Unit and Integration Tests for Atlas Live Web Search Engine (Gen-3)."""

import pytest
from backend.live_search import (
    is_safe_url,
    classify_search_intent,
    clean_search_snippet,
    calculate_authority_score,
    execute_live_web_search,
)


def test_ssrf_safety_checks():
    # Private / Loopback IPs should be rejected
    assert is_safe_url("http://localhost:8000/api") is False
    assert is_safe_url("http://127.0.0.1:8080") is False
    assert is_safe_url("http://169.254.169.254/latest/meta-data") is False
    assert is_safe_url("file:///etc/passwd") is False
    assert is_safe_url("ftp://example.com") is False

    # Public web URLs should be permitted
    assert is_safe_url("https://en.wikipedia.org/wiki/Artificial_intelligence") is True
    assert is_safe_url("https://www.python.org/downloads/") is True


def test_classify_search_intent():
    # Explicit on/off modes
    assert classify_search_intent("any query", explicit_mode="off") == (False, "off")
    assert classify_search_intent("any query", explicit_mode="on") == (True, "on")

    # Time-sensitive questions should trigger search
    needs_search, reason = classify_search_intent("Who is Mahesh Babu?")
    assert needs_search is True

    needs_search, reason = classify_search_intent("What is the latest Python version?")
    assert needs_search is True

    # Static facts or math should not require web search
    needs_search, _ = classify_search_intent("Solve 2 + 2")
    assert needs_search is False


def test_clean_search_snippet_and_authority():
    raw_html_snippet = "<b>Python 3.14</b> is the latest &amp; greatest version of Python."
    clean = clean_search_snippet(raw_html_snippet)
    assert "<b>" not in clean
    assert "&amp;" not in clean
    assert "Python 3.14" in clean

    # Authority scoring
    gov_score = calculate_authority_score("https://www.isro.gov.in/chandrayaan3.html")
    edu_score = calculate_authority_score("https://cs.stanford.edu/research")
    wiki_score = calculate_authority_score("https://en.wikipedia.org/wiki/Python")
    random_score = calculate_authority_score("https://randomblog12345.xyz/post")

    assert gov_score > 0.8
    assert edu_score > 0.8
    assert wiki_score > 0.7
    assert random_score < wiki_score


def test_live_search_execution():
    # Test keyless web search fallback for a known stable topic
    res = execute_live_web_search("Python programming language", limit=3, fetch_full_content=False)
    assert res is not None
    assert "results" in res
    assert len(res["results"]) > 0
    first = res["results"][0]
    assert first["url"].startswith("http")
    assert "python" in (first["title"] + first["snippet"]).lower()
