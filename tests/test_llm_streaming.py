"""Coverage for real token streaming (ISSUE 2).

These tests exercise the additive streaming layer in backend/llm.py and its
wiring into the general-answer path, without any network access: provider
streams are faked at the urllib boundary so the SSE parsing, per-provider
selection, and mid-stream commitment logic are all really executed.
"""

import backend.llm as L
from backend.llm import _iter_sse_json, query_llm_stream


class _FakeResp:
    """Minimal stand-in for a urllib streaming response (iterable + context mgr)."""

    def __init__(self, lines):
        self._lines = lines

    def __iter__(self):
        return iter(self._lines)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _sse(*contents):
    """Build OpenAI-style SSE data lines from content deltas."""
    lines = []
    for c in contents:
        lines.append(
            ('data: {"choices":[{"delta":{"content":%s}}]}\n' % _json_str(c)).encode("utf-8")
        )
    lines.append(b"data: [DONE]\n")
    return lines


def _json_str(s):
    import json
    return json.dumps(s)


def test_iter_sse_json_skips_non_data_and_stops_at_done():
    raw = [
        b"event: message\n",
        b"\n",
        b'data: {"a": 1}\n',
        b": heartbeat\n",
        b'data: {"b": 2}\n',
        b"data: [DONE]\n",
        b'data: {"never": "reached"}\n',
    ]
    assert list(_iter_sse_json(iter(raw))) == [{"a": 1}, {"b": 2}]


def test_stream_returns_none_without_a_token_sink_or_provider(monkeypatch):
    for env in L._PROVIDER_KEY_ENV.values():
        monkeypatch.delenv(env, raising=False)
    # No on_token -> never streams (caller falls back to query_llm).
    assert query_llm_stream("hi", on_token=None) is None
    # on_token but no configured provider -> None.
    assert query_llm_stream("hi", on_token=lambda t: None) is None


def test_openai_stream_emits_deltas_and_returns_full_text(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_urlopen(req, timeout=None):
        return _FakeResp(_sse("Hel", "lo ", "world"))

    monkeypatch.setattr(L.urllib.request, "urlopen", fake_urlopen)

    got = []
    text = query_llm_stream("say hello", on_token=got.append)
    assert text == "Hello world"
    assert got == ["Hel", "lo ", "world"]


def test_mid_stream_failure_commits_partial_and_does_not_restart(monkeypatch):
    # OpenAI emits one delta then the connection drops; Gemini is configured and
    # must NOT be called (that would duplicate already-emitted text).
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    gemini_called = {"n": 0}

    def fake_urlopen(req, timeout=None):
        url = getattr(req, "full_url", "") or ""
        if "generativelanguage" in url:
            gemini_called["n"] += 1
            return _FakeResp(_sse("SHOULD NOT APPEAR"))

        def gen():
            yield b'data: {"choices":[{"delta":{"content":"Partial answer"}}]}\n'
            raise RuntimeError("connection reset mid-stream")

        return _FakeResp(gen())

    monkeypatch.setattr(L.urllib.request, "urlopen", fake_urlopen)

    got = []
    text = query_llm_stream("go", on_token=got.append)
    assert text == "Partial answer"
    assert got == ["Partial answer"]
    assert gemini_called["n"] == 0


def test_failure_before_any_token_falls_through_to_next_provider(monkeypatch):
    # OpenAI errors before emitting; Gemini then succeeds. Selection order is
    # openai -> gemini -> anthropic -> mistral for the default 'main' role.
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def fake_urlopen(req, timeout=None):
        url = getattr(req, "full_url", "") or ""
        if "generativelanguage" in url:
            return _FakeResp(
                [b'data: {"candidates":[{"content":{"parts":[{"text":"From Gemini"}]}}]}\n']
            )
        raise RuntimeError("openai down before first token")

    monkeypatch.setattr(L.urllib.request, "urlopen", fake_urlopen)

    got = []
    text = query_llm_stream("go", on_token=got.append)
    assert text == "From Gemini"
    assert got == ["From Gemini"]


def test_explicit_selected_provider_is_honoured(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    L.set_selected_provider("anthropic")
    try:
        def fake_urlopen(req, timeout=None):
            url = getattr(req, "full_url", "") or ""
            assert "anthropic.com" in url, f"expected anthropic, got {url}"
            return _FakeResp(
                [
                    b'event: content_block_delta\n',
                    b'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"Claude "}}\n',
                    b'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"here"}}\n',
                ]
            )

        monkeypatch.setattr(L.urllib.request, "urlopen", fake_urlopen)
        got = []
        text = query_llm_stream("go", on_token=got.append)
        assert text == "Claude here"
        assert got == ["Claude ", "here"]
    finally:
        L.set_selected_provider("auto")


def test_general_answer_streams_when_given_a_token_sink(monkeypatch):
    import backend.intent_router as R

    monkeypatch.setattr(R, "any_provider_configured", lambda: True)
    monkeypatch.setattr(R, "lookup_known_answer", lambda *a, **k: None)

    def fake_stream(prompt, system_prompt=None, on_token=None, timeout=None, max_tokens=None, role="main"):
        for delta in ["Because ", "light ", "scatters."]:
            on_token(delta)
        return "Because light scatters."

    monkeypatch.setattr(R, "query_llm_stream", fake_stream)

    got = []
    out = R._general_answer("Why is the sky blue at noon?", None, "", on_token=got.append)
    assert out == "Because light scatters."
    assert got == ["Because ", "light ", "scatters."]
