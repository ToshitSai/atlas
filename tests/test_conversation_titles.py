from database.store import store


def test_conversation_title_uses_substantive_topic_after_greeting(isolate_store):
    store.record_message("greeting-first", "user", "hi")
    store.record_message("greeting-first", "assistant", "Hello! What can I help with?")
    store.record_message("greeting-first", "user", "train a fraud detection model")

    conversation = store.list_conversations()[0]

    assert conversation["title"] == "Fraud detection model design"
