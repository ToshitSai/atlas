"""GEN-3.3.12 — Real-Time Clock, Utility Routing and RAG Bypass Test Suite.

Tests:
  T1  — _is_datetime_query detects "time in india now"
  T2  — _is_datetime_query detects all required variations
  T3  — _extract_timezone maps India → Asia/Kolkata
  T4  — _extract_timezone maps London → Europe/London
  T5  — _extract_timezone maps New York → America/New_York
  T6  — _extract_timezone maps Tokyo → Asia/Tokyo
  T7  — _extract_timezone falls back to UTC for unknown
  T8  — handle_intent_message("time in india now") returns IST time
  T9  — handle_intent_message("current time in London") returns London time
  T10 — handle_intent_message("what time is it in Tokyo?") returns JST time
  T11 — handle_intent_message("what is today's date?") returns a date
  T12 — Response contains activityTier='none'
  T13 — Response contains taskCategory='TIME_AND_DATE'
  T14 — Response contains sources=[]
  T15 — Time query with uploaded docs: does NOT activate RAG
  T16 — Time query does NOT return stale resume context
  T17 — Frozen-clock test: timezone conversion independent of real time
  T18 — General knowledge query ("what is Python?") still works
  T19 — Greeting ("hi") still works without RAG
  T20 — Live-search query ("latest AI news") still routed to web search
"""

import os
import sys
import re
import datetime
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import backend.config  # noqa: F401 — loads env before anything else
from backend.intent_router import (
    _is_datetime_query,
    _extract_timezone,
    _DATETIME_QUERY_RE,
    handle_intent_message,
)

# ---------------------------------------------------------------------------
# T1-T2: Regex detection
# ---------------------------------------------------------------------------

TIME_QUERY_VARIANTS = [
    "time in india now",
    "what time is it in India?",
    "current indian time",
    "today's date in India",
    "what day is it today?",
    "current time in London",
    "time in New York",
    "what time is it in Tokyo?",
    "what is the time now",
    "time now",
    "what's today's date",
    "current date",
    "what is today's date?",
    "tell me the time",
    "Indian time",
    "Tokyo time now",
    "time in singapore",
    "time in dubai now",
    "london time now",
]

NON_TIME_VARIANTS = [
    "what is Python?",
    "hi",
    "hello",
    "explain machine learning",
    "what is the latest AI news?",
    "search the web for climate change",
    "what are the best jobs for a software engineer?",
    "2 + 2",
    "who created Atlas?",
    "what is an API?",
]


@pytest.mark.parametrize("query", TIME_QUERY_VARIANTS)
def test_t1_t2_datetime_regex_detects_time_queries(query):
    """T1/T2: _is_datetime_query must return True for all time/timezone variants."""
    assert _is_datetime_query(query.lower()), (
        f"Expected _is_datetime_query to return True for: {query!r}\n"
        f"Pattern: {_DATETIME_QUERY_RE.pattern}"
    )


@pytest.mark.parametrize("query", NON_TIME_VARIANTS)
def test_t2_datetime_regex_does_not_match_non_time(query):
    """T2b: _is_datetime_query must return False for non-time queries."""
    assert not _is_datetime_query(query.lower()), (
        f"Expected _is_datetime_query to return False for: {query!r}"
    )


# ---------------------------------------------------------------------------
# T3-T7: Timezone extraction
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("message,expected_iana,expected_label_fragment", [
    ("time in india now", "Asia/Kolkata", "India"),
    ("what time is it in India?", "Asia/Kolkata", "India"),
    ("current time in London", "Europe/London", "London"),
    ("time in New York", "America/New_York", "New York"),
    ("what time is it in Tokyo?", "Asia/Tokyo", "Tokyo"),
    ("time in Singapore", "Asia/Singapore", "Singapore"),
    ("time in Dubai", "Asia/Dubai", "Dubai"),
    ("time in Germany", "Europe/Berlin", "Central Europe"),
    ("time in Seoul", "Asia/Seoul", "Seoul"),
    ("time in Hong Kong", "Asia/Hong_Kong", "Hong Kong"),
    ("what time is it in Paris?", "Europe/Berlin", "Central Europe"),
    ("current time in Beijing", "Asia/Shanghai", "Beijing"),
    ("time in Sydney", "Australia/Sydney", "Sydney"),
])
def test_t3_t7_extract_timezone_maps_correctly(message, expected_iana, expected_label_fragment):
    """T3-T7: _extract_timezone maps location keywords to correct IANA zones."""
    iana, label = _extract_timezone(message)
    assert iana == expected_iana, (
        f"For '{message}': expected IANA={expected_iana!r}, got {iana!r}"
    )
    assert expected_label_fragment.lower() in label.lower(), (
        f"For '{message}': expected label to contain {expected_label_fragment!r}, got {label!r}"
    )


def test_t7_extract_timezone_fallback_to_utc():
    """T7: Unknown location falls back to UTC."""
    iana, label = _extract_timezone("time in Westeros")
    assert iana == "UTC"


# ---------------------------------------------------------------------------
# T8-T14: handle_intent_message integration
# ---------------------------------------------------------------------------

def _call_time(query: str) -> dict:
    """Helper: call handle_intent_message with a time query, no attachments."""
    return handle_intent_message(
        message=query,
        active_project_id=None,
        session_id="test-gen3312-clock",
        conversation_history=[],
    )


def test_t8_time_in_india_returns_ist():
    """T8: 'time in india now' returns IST time, not UTC, not resume content."""
    res = _call_time("time in india now")
    resp = res.get("response", "")
    assert "India" in resp or "IST" in resp, (
        f"Expected IST/India in response, got: {resp!r}"
    )
    # Confirm it has a time pattern (digit:digit AM/PM or HH:MM)
    assert re.search(r"\d+:\d+", resp), f"No time pattern found in: {resp!r}"
    # Must NOT contain resume/job content
    assert "generative ai" not in resp.lower(), f"Resume contamination detected: {resp!r}"
    assert "developer" not in resp.lower() or "time" in resp.lower(), (
        f"Suspicious response: {resp!r}"
    )


def test_t9_current_time_london():
    """T9: 'current time in London' returns London timezone response."""
    res = _call_time("current time in London")
    resp = res.get("response", "")
    assert re.search(r"\d+:\d+", resp), f"No time found: {resp!r}"
    assert "london" in resp.lower() or "gmt" in resp.lower() or "bst" in resp.lower() or "utc" in resp.lower(), (
        f"Expected London/GMT/BST in response: {resp!r}"
    )


def test_t10_time_in_tokyo_returns_jst():
    """T10: 'what time is it in Tokyo?' returns JST response."""
    res = _call_time("what time is it in Tokyo?")
    resp = res.get("response", "")
    assert re.search(r"\d+:\d+", resp), f"No time found: {resp!r}"
    assert "tokyo" in resp.lower() or "jst" in resp.lower(), (
        f"Expected Tokyo/JST in response: {resp!r}"
    )


def test_t11_today_date_returns_date():
    """T11: 'what is today's date?' returns a date string."""
    res = _call_time("what is today's date?")
    resp = res.get("response", "")
    # Should contain month name or year
    assert re.search(r"20\d\d", resp) or re.search(
        r"january|february|march|april|may|june|july|august|september|october|november|december",
        resp, re.I
    ), f"No recognizable date in: {resp!r}"


def test_t12_activity_tier_is_none():
    """T12: Time responses must return activityTier='none'."""
    res = _call_time("time in india now")
    assert res.get("activityTier") == "none", (
        f"Expected activityTier='none', got: {res.get('activityTier')!r}"
    )


def test_t13_task_category_is_time_and_date():
    """T13: Time responses must have taskCategory='TIME_AND_DATE'."""
    res = _call_time("time in india now")
    assert res.get("taskCategory") == "TIME_AND_DATE", (
        f"Expected taskCategory='TIME_AND_DATE', got: {res.get('taskCategory')!r}"
    )


def test_t14_sources_is_empty_for_time_query():
    """T14: Time responses must return empty sources list."""
    res = _call_time("time in india now")
    sources = res.get("sources", None)
    assert sources is not None, "Missing 'sources' key in response"
    assert sources == [], f"Expected sources=[], got: {sources!r}"


# ---------------------------------------------------------------------------
# T15-T16: RAG isolation — time query must not activate RAG
# ---------------------------------------------------------------------------

def test_t15_time_query_bypasses_rag_even_with_docs(tmp_path):
    """T15: If the user has uploaded docs, 'time in india now' must NOT trigger RAG."""
    from backend.rag_service import service as rag_svc

    owner = "test-gen3312-rag-bypass"
    # Upload a fake resume so user_has_docs=True
    fake_resume = b"TOSHIT SAI GALAM\nSoftware Engineer\nSkills: Python, AI"
    try:
        rag_svc.index_document(
            content=fake_resume,
            filename="resume.txt",
            mime_type="text/plain",
            owner_session=owner,
            session_id=owner,
        )
    except Exception as e:
        pytest.skip(f"RAG indexing not available in test env: {e}")

    res = handle_intent_message(
        message="time in india now",
        active_project_id=None,
        session_id=owner,
        conversation_history=[],
    )
    resp = res.get("response", "")

    # Must be a time response
    assert re.search(r"\d+:\d+", resp), f"Expected time, got: {resp!r}"
    # Must not be a resume/job response
    assert "software engineer" not in resp.lower(), f"RAG contamination: {resp!r}"
    assert "skills" not in resp.lower(), f"RAG contamination: {resp!r}"
    assert res.get("activityTier") == "none", f"Expected activityTier='none': {res}"
    assert res.get("sources", []) == [], f"Expected empty sources: {res.get('sources')}"

    # Cleanup
    try:
        for doc in rag_svc.list_documents(owner_session=owner):
            rag_svc.delete_document(doc["id"], owner_session=owner)
    except Exception:
        pass


def test_t16_no_stale_resume_context_for_time_query():
    """T16: Resume conversation followed by time query must not bleed resume content."""
    from backend.intent_router import handle_intent_message

    sid = "test-gen3312-stale-prevention"

    # Simulate a prior resume conversation via conversation_history
    stale_history = [
        {"role": "user", "content": "Based on my resume what roles can I apply?"},
        {"role": "assistant", "content": "Based on your resume you can apply for: AI Engineer, Full-Stack Developer, ML Researcher."},
    ]

    res = handle_intent_message(
        message="time in india now",
        active_project_id=None,
        session_id=sid,
        conversation_history=stale_history,
    )
    resp = res.get("response", "")

    assert re.search(r"\d+:\d+", resp), f"Expected IST time, got: {resp!r}"
    assert "ai engineer" not in resp.lower(), f"Stale history contamination: {resp!r}"
    assert "full-stack" not in resp.lower(), f"Stale history contamination: {resp!r}"


# ---------------------------------------------------------------------------
# T17: Frozen-clock timezone conversion
# ---------------------------------------------------------------------------

def test_t17_frozen_clock_timezone_conversion():
    """T17: Timezone conversion independent of system time — verify offset logic."""
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        pytest.skip("zoneinfo not available")

    # Kolkata is UTC+5:30
    utc_ref = datetime.datetime(2026, 11, 13, 10, 0, 0, tzinfo=datetime.timezone.utc)
    kolkata = utc_ref.astimezone(ZoneInfo("Asia/Kolkata"))
    assert kolkata.hour == 15, f"Expected 15:30 IST for 10:00 UTC, got {kolkata}"
    assert kolkata.minute == 30

    # London is UTC+0 (November = GMT, not BST)
    london = utc_ref.astimezone(ZoneInfo("Europe/London"))
    assert london.hour == 10

    # New York in November = UTC-5
    ny = utc_ref.astimezone(ZoneInfo("America/New_York"))
    assert ny.hour == 5

    # Tokyo is UTC+9
    tokyo = utc_ref.astimezone(ZoneInfo("Asia/Tokyo"))
    assert tokyo.hour == 19


# ---------------------------------------------------------------------------
# T18-T20: Regression — existing routes still work
# ---------------------------------------------------------------------------

def test_t18_general_knowledge_still_works():
    """T18: 'what is Python?' should not be treated as a time query."""
    assert not _is_datetime_query("what is python?")
    res = handle_intent_message(
        message="what is Python?",
        active_project_id=None,
        session_id="test-gen3312-general",
        conversation_history=[],
    )
    resp = res.get("response", "")
    assert len(resp) > 20, f"Expected non-trivial answer, got: {resp!r}"
    assert "python" in resp.lower() or "programming" in resp.lower() or "language" in resp.lower(), (
        f"Expected Python explanation, got: {resp!r}"
    )


def test_t19_greeting_works_without_rag():
    """T19: 'hi' must be a casual greeting, not a time query or RAG query."""
    assert not _is_datetime_query("hi")
    res = handle_intent_message(
        message="hi",
        active_project_id=None,
        session_id="test-gen3312-greeting",
        conversation_history=[],
    )
    resp = res.get("response", "")
    assert len(resp) > 0, "Empty greeting response"
    assert res.get("sources", []) == [] or res.get("sources") is None, (
        f"Greeting should have no sources: {res.get('sources')}"
    )


def test_t20_live_search_query_not_treated_as_time():
    """T20: 'latest AI news' must not match _is_datetime_query."""
    assert not _is_datetime_query("what is the latest AI news?")
    assert not _is_datetime_query("latest news on artificial intelligence")
