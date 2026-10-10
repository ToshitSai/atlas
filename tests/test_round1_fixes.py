from backend.research_modes import parse_mode_from_message
from backend.constraints import detect, json_only
from backend.llm import engine_disclosure

def test_normal_language_never_switches_manual_mode():
    for text in ("Explain how to bake bread step by step", "walk me through it",
                 "step-by-step guide", "proceed", "manual"):
        assert parse_mode_from_message(text) is None

def test_explicit_mode_switch_still_works():
    assert parse_mode_from_message("switch the research mode to manual") == "MANUAL"

def test_json_only_removes_wrappers():
    c = detect("Output MUST be strictly valid JSON and NOTHING ELSE")
    assert c["json_only"]
    obj, text = json_only("Plaintext JSON:\n{\"a\": 1}\nExplanation: none")
    assert obj == {"a": 1} and text == '{"a":1}'

def test_engine_details_are_not_user_visible():
    assert engine_disclosure() == ""
