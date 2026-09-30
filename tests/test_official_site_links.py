"""Regression coverage for direct, common website-link requests."""
import pytest

from backend.intent_router import classify_intent, handle_intent_message
from backend.web_search import clean_snippet, result_matches_query


@pytest.mark.parametrize("message,name,url", [
    ("what is the url for github", "GitHub", "https://github.com"),
    ("give me link to open instagram", "Instagram", "https://www.instagram.com"),
    ("give me the link to youtube", "YouTube", "https://www.youtube.com"),
    ("open google for me", "Google", "https://www.google.com"),
    ("link to wikipedia", "Wikipedia", "https://www.wikipedia.org"),
    ("link to netflix", "Netflix", "https://www.netflix.com"),
    ("open twitter for me", "X", "https://x.com"),
    ("amazon link please", "Amazon", "https://www.amazon.com"),
    ("reddit url", "Reddit", "https://www.reddit.com"),
    ("take me to linkedin", "LinkedIn", "https://www.linkedin.com"),
])
def test_common_site_links_are_direct_and_consistent(isolate_store, message, name, url):
    assert classify_intent(message, session_id=f"site-{name}") == "EXPLANATION"
    response = handle_intent_message(message, session_id=f"site-answer-{name}")
    assert response["action"] == "NONE"
    assert f"official URL for {name}" in response["response"]
    assert url in response["response"]
    lowered = response["response"].lower()
    assert "provider is configured" not in lowered
    assert "keyless reference" not in lowered
    assert "source:" not in lowered


def test_snippets_never_cut_words_or_run_into_urls():
    snippet = clean_snippet("word " * 100, limit=31)
    assert snippet.endswith("...")
    assert not snippet.endswith(" ")
    assert "word" in snippet


def test_search_relevance_rejects_song_when_user_asked_for_youtube():
    wrong = {"title": "Give Me Everything", "url": "https://example.com/song", "snippet": "A Pitbull song"}
    right = {"title": "YouTube", "url": "https://www.youtube.com", "snippet": "Video platform"}
    assert not result_matches_query("give me link to youtube", wrong)
    assert result_matches_query("give me link to youtube", right)
