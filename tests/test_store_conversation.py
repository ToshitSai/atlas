"""Unit tests for conversation-state storage (section 3) and pending actions."""
from database.store import store


def test_record_message_appends_separately(isolate_store):
    sid = "conv-1"
    isolate_store.record_message(sid, "user", "What is recall?")
    isolate_store.record_message(sid, "assistant", "Recall measures ...", intent="EXPLANATION", topic="recall")
    isolate_store.record_message(sid, "user", "Hi")

    msgs = isolate_store.get_messages(sid)
    assert len(msgs) == 3
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"]
    # Each message carries its own identity + metadata.
    first = msgs[0]
    for key in ("id", "conversation_id", "role", "content", "timestamp"):
        assert key in first
    assert msgs[1]["intent"] == "EXPLANATION"
    assert msgs[1]["topic"] == "recall"
    # ids are unique
    assert len({m["id"] for m in msgs}) == 3


def test_history_is_capped(isolate_store):
    sid = "conv-cap"
    for i in range(250):
        isolate_store.record_message(sid, "user", f"m{i}", max_history=200)
    msgs = isolate_store.get_messages(sid)
    assert len(msgs) == 200
    # Oldest trimmed, newest retained.
    assert msgs[-1]["content"] == "m249"
    assert msgs[0]["content"] == "m50"


def test_pending_action_roundtrip(isolate_store):
    sid = "conv-pend"
    assert isolate_store.get_session(sid)["pending_action"] is None
    isolate_store.set_pending_action(sid, "NEXT_EXPERIMENT", project_id="p1")
    pend = isolate_store.get_session(sid)["pending_action"]
    assert pend["type"] == "NEXT_EXPERIMENT" and pend["projectId"] == "p1"
    isolate_store.clear_pending_action(sid)
    assert isolate_store.get_session(sid)["pending_action"] is None


def test_sessions_are_isolated(isolate_store):
    isolate_store.record_message("a", "user", "hello A")
    isolate_store.record_message("b", "user", "hello B")
    assert isolate_store.get_messages("a")[0]["content"] == "hello A"
    assert isolate_store.get_messages("b")[0]["content"] == "hello B"
    assert len(isolate_store.get_messages("a")) == 1


def test_conversation_list_is_persisted_and_titled_from_first_user_message(isolate_store):
    """Regression: a completed exchange is a durable sidebar chat after reload."""
    sid = "conv-sidebar"
    isolate_store.record_message(sid, "user", "Improve fraud detection with a robust baseline")
    isolate_store.record_message(sid, "assistant", "Start with a stratified validation split.")

    chats = isolate_store.list_conversations()
    assert len(chats) == 1
    assert chats[0]["id"] == sid
    assert chats[0]["title"] == "Fraud detection model design"
    assert chats[0]["messageCount"] == 2

    # The file backend is the same persistent storage read by a new page/tab.
    # The shared fixture disables automatic file writes, so persist explicitly.
    isolate_store._save_file()
    from database.store import ResearchStore
    reloaded = ResearchStore(isolate_store.filepath)
    assert reloaded.list_conversations()[0]["id"] == sid
    assert [m["content"] for m in reloaded.get_messages(sid)] == [
        "Improve fraud detection with a robust baseline",
        "Start with a stratified validation split.",
    ]
