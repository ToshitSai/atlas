"""Model Router test suite (offline).

Covers the 14-scenario routing matrix, capability-based selection, provider
health + sequential fallback, secret-free logging, and the safe-default
behaviour when classification fails. No network calls are made: provider
functions are monkeypatched where execution is exercised.

Run: py -3 -m pytest tests/test_model_router.py -q
  or: py -3 tests/test_model_router.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import llm as llm_mod
from backend import model_router as mr

# conftest's autouse `no_llm` fixture replaces llm_mod.query_llm with a None
# stub for hermeticity. Capture the real implementation at import time so the
# fallback test below can still exercise the genuine sequential preference path.
_REAL_QUERY_LLM = llm_mod.query_llm


# --- 14-scenario routing matrix ------------------------------------------- #
MATRIX = [
    ("Hello", mr.TASK_GENERAL, mr.COMPLEXITY_LOW),
    ("What is machine learning?", mr.TASK_GENERAL, None),
    ("Write a Python REST API with FastAPI that has 3 endpoints", mr.TASK_CODING, None),
    ("Why does my React application crash when deployed to production?", mr.TASK_DEBUGGING, None),
    ("Optimize this SQL query that joins 4 large tables and runs slowly", mr.TASK_CODING, None),
    ("Compute the derivative of x^3 + 2x and solve the integral of sin(x)", mr.TASK_MATHEMATICS, None),
    ("Summarize this PDF research paper", mr.TASK_DOCUMENT_ANALYSIS, None),
    ("Analyze this CSV for anomalies and find the distribution", mr.TASK_DATA_ANALYSIS, None),
    ("What are the latest AI developments this month?", mr.TASK_RESEARCH, None),
    ("Compare the latest RAG papers and do deep research on hallucination reduction", mr.TASK_DEEP_RESEARCH, None),
    ("Write a short poem about the ocean", mr.TASK_WRITING, None),
    ("Give me a step-by-step plan to learn backend engineering", mr.TASK_PLANNING, None),
]


def test_matrix():
    failures = []
    for message, expected_task, expected_cx in MATRIX:
        files = None
        if "PDF" in message:
            files = [{"name": "paper.pdf", "type": "application/pdf"}]
        if "CSV" in message:
            files = [{"name": "data.csv", "type": "text/csv"}]
        d = mr.classify_task(message, files=files)
        ok = d.task == expected_task and (expected_cx is None or d.complexity == expected_cx)
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures.append((message, expected_task, d.task, expected_cx, d.complexity))
        print(f"[{status}] {message[:55]!r:58} -> {d.task}/{d.complexity} cap={d.recommended_capability} "
              f"web={int(d.flags['needs_web'])} deep={int(d.flags['needs_deep_research'])} "
              f"mm={int(d.flags['needs_multimodal'])} lc={int(d.flags['needs_long_context'])}")
    assert not failures, f"matrix mismatches: {failures}"


def test_multimodal_image():
    d = mr.classify_task("What is in this image?", files=[{"name": "photo.png", "type": "image/png"}])
    assert d.task == mr.TASK_MULTIMODAL and d.flags["needs_multimodal"] is True


def test_web_flag_on_current_info():
    d = mr.classify_task("latest techniques for reducing hallucinations in RAG")
    assert d.flags["needs_web"] is True


def test_complex_code_long_context():
    long_msg = "Review this 500-line repository module and refactor it. " + ("x " * 2500)
    d = mr.classify_task(long_msg, files=[{"name": "app.py", "type": "text/x-python"}])
    assert d.task in (mr.TASK_CODING, mr.TASK_DEBUGGING)
    assert d.flags["needs_long_context"] is True
    assert d.complexity in (mr.COMPLEXITY_MEDIUM, mr.COMPLEXITY_HIGH)


# --- capability-based selection ------------------------------------------- #
def test_selection_prefers_coding_for_high_complexity_coding():
    d = mr.classify_task("Architect and implement a distributed task queue in Python with retries")
    d.complexity = mr.COMPLEXITY_HIGH
    order, top = mr.select_providers(d)
    assert order, "no providers configured to select from"
    # Strongest coding/reasoning family (anthropic) should lead a HIGH coding task.
    assert top["provider"] == "anthropic", f"expected anthropic first, got {top['provider']}"


def test_selection_prefers_fast_cheap_for_low_general():
    d = mr.classify_task("Hello")
    d.complexity = mr.COMPLEXITY_LOW
    order, top = mr.select_providers(d)
    # LOW general should NOT pick the most expensive reasoner first.
    assert top["provider"] in ("gemini", "mistral", "openai"), f"unexpected low-cost pick {top['provider']}"


def test_selection_multimodal_excludes_text_only():
    d = mr.classify_task("describe this image", files=[{"name": "a.png", "type": "image/png"}])
    order, top = mr.select_providers(d)
    # mistral-tiny has no multimodal capability; it must not be the top pick.
    assert top["provider"] != "mistral"


def test_selection_is_deterministic():
    d1 = mr.classify_task("Write a Python function to sort a list")
    d2 = mr.classify_task("Write a Python function to sort a list")
    o1, _ = mr.select_providers(d1)
    o2, _ = mr.select_providers(d2)
    assert o1 == o2


# --- provider health + sequential fallback -------------------------------- #
def test_health_cooldown_and_recovery():
    h = mr.ProviderHealth()
    assert h.is_available("openai") is True
    h.record("openai", False, "timeout")
    assert h.is_available("openai") is True  # one failure is not enough
    h.record("openai", False, "timeout")
    assert h.is_available("openai") is False  # cooling down
    h._state["openai"]["cooldown_until"] = 0.0  # simulate cooldown expiry
    assert h.is_available("openai") is True
    h.record("openai", True, "")
    assert h.snapshot()["openai"]["consecutive_failures"] == 0


def test_sequential_fallback_in_query_llm(monkeypatch=None):
    """Verify query_llm's preference path tries providers in order and falls
    back when the first fails, recording per-provider outcomes."""
    calls = []

    def fake_openai(prompt, system_prompt=None, timeout=12, max_tokens=None, return_details=False):
        calls.append("openai")
        return None  # simulate failure

    def fake_gemini(prompt, system_prompt=None, timeout=12, max_tokens=None, return_details=False):
        calls.append("gemini")
        return "gemini-answer"

    orig = (llm_mod.call_openai_api, llm_mod.call_gemini_api)
    llm_mod._PROVIDER_FUNCS["openai"] = fake_openai
    llm_mod._PROVIDER_FUNCS["gemini"] = fake_gemini
    # Ensure keys are 'configured' so the functions are invoked.
    saved_env = {k: os.environ.get(k) for k in ("OPENAI_API_KEY", "GEMINI_API_KEY")}
    os.environ["OPENAI_API_KEY"] = "test-key-not-real"
    os.environ["GEMINI_API_KEY"] = "test-key-not-real"
    try:
        llm_mod.set_llm_budget(20)
        llm_mod.begin_provider_outcomes()
        llm_mod.set_provider_preference(["openai", "gemini"])
        result = _REAL_QUERY_LLM("test prompt", "test system")
        outcomes = llm_mod.get_provider_outcomes()
        llm_mod.clear_provider_preference()
        llm_mod.clear_llm_budget()
    finally:
        llm_mod._PROVIDER_FUNCS["openai"], llm_mod._PROVIDER_FUNCS["gemini"] = orig
        for k, v in saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    assert result == "gemini-answer", f"expected fallback to gemini, got {result!r}"
    # openai is attempted first (with its bounded internal retry), then gemini.
    assert calls[0] == "openai" and calls[-1] == "gemini", f"expected ordered attempts, got {calls}"
    ok_map = {o["provider"]: o["ok"] for o in outcomes}
    assert ok_map.get("openai") is False and ok_map.get("gemini") is True


def test_finalize_updates_health_and_flags_fallback():
    d = mr.route("req-test-1", "Write a Python function", files=None)
    primary = d.provider
    # Simulate: primary failed, next provider answered.
    order = d.provider_order
    fallback_provider = next((p for p in order if p != primary), None)
    llm_mod.begin_provider_outcomes()
    if primary:
        llm_mod.record_provider_outcome(primary, False, "timeout")
    if fallback_provider:
        llm_mod.record_provider_outcome(fallback_provider, True, "")
    summary = mr.finalize("req-test-1", d)
    assert summary["provider"] == fallback_provider
    assert summary["fallbackUsed"] is True
    assert summary["latencyMs"] is not None
    # secret-free: no key material anywhere in the summary
    blob = repr(summary).lower()
    assert "api_key" not in blob and "test-key" not in blob


# --- safety / secrets ------------------------------------------------------ #
def test_router_failure_safe_default():
    orig = mr.select_providers
    mr.select_providers = lambda decision: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        d = mr.route("req-fail", "Hello")
    finally:
        mr.select_providers = orig
    assert d.task == mr.TASK_GENERAL
    assert d.complexity == mr.COMPLEXITY_LOW
    assert "fallback" in d.reason.lower() or "router" in d.reason.lower()


def test_logs_are_secret_free():
    os.environ["OPENAI_API_KEY"] = "sk-SUPER-SECRET-VALUE"
    try:
        mr.route("req-secret", "Explain gradient descent in detail")
        logs = mr.recent_routing_logs(50)
        blob = repr(logs).lower()
        assert "sk-super-secret-value" not in blob
        assert "api_key" not in blob
    finally:
        os.environ.pop("OPENAI_API_KEY", None)


def test_snapshot_shape():
    snap = mr.snapshot()
    assert snap["enabled"] is True
    assert isinstance(snap["registry"], list) and snap["registry"]
    assert "providerHealth" in snap
    # snapshot must not contain secrets
    assert "api_key" not in repr(snap).lower()


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for fn in tests:
        try:
            fn()
            print(f"[PASS] {fn.__name__}")
            passed += 1
        except Exception as exc:
            print(f"[FAIL] {fn.__name__}: {type(exc).__name__}: {exc}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    return failed


if __name__ == "__main__":
    print("=== 14-scenario routing matrix ===")
    test_matrix()
    print("\n=== unit tests ===")
    sys.exit(1 if _run_all() else 0)
