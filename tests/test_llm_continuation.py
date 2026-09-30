"""Regression coverage for recovering an answer that hits an output limit."""

from backend.llm import query_llm_with_continuation


def test_output_limit_is_continued_until_a_complete_answer():
    calls = []

    def limited_model(prompt, **kwargs):
        calls.append({"prompt": prompt, "max_tokens": kwargs.get("max_tokens")})
        if len(calls) == 1:
            return {
                "text": "## Analysis\nThe first required conclusion is",
                "finish_reason": "length",
            }
        return {
            "text": "that the evidence supports the hypothesis.\n\n## Final answer\nAll requested parts are complete.",
            "finish_reason": "stop",
        }

    result = query_llm_with_continuation(
        "Give a detailed, step-by-step technical analysis with a final answer.",
        query_fn=limited_model,
    )

    assert result["continuations"] == 1
    assert result["completed"] is True
    assert "The first required conclusion is\nthat the evidence" in result["text"]
    assert result["text"].endswith("All requested parts are complete.")
    assert len(calls) == 2
    assert "previous response was truncated" in calls[1]["prompt"].lower()
    # A detailed request must not get the old, short 1k-token default.
    assert calls[0]["max_tokens"] >= 2500


def test_code_fence_is_repaired_when_a_provider_cannot_continue():
    result = query_llm_with_continuation(
        "Explain this implementation.",
        max_continuations=1,
        query_fn=lambda *args, **kwargs: {
            "text": "```python\nprint('partial')",
            "finish_reason": "length",
        },
    )

    assert result["text"].endswith("```")
