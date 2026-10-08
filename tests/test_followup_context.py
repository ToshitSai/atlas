from backend.intent_router import rewrite_followup_query


def test_followup_rewrites_against_last_topic():
    history = [
        {'role': 'user', 'content': 'what is RAG'},
        {'role': 'assistant', 'content': 'RAG retrieves documents before generation.'},
    ]
    assert 'RAG' in rewrite_followup_query('how does it work?', history)


def test_topic_switch_does_not_inherit_old_topic():
    history = [{'role': 'user', 'content': 'what is RAG'}, {'role': 'assistant', 'content': 'retrieval augmented generation'}]
    assert rewrite_followup_query('Explain database indexes', history) == 'Explain database indexes'


def test_more_detail_followup_keeps_topic():
    history = [{'role': 'user', 'content': 'what is RAG'}, {'role': 'assistant', 'content': 'RAG retrieves documents before generation.'}]
    rewritten = rewrite_followup_query('give me more detail', history)
    assert 'RAG' in rewritten and rewritten.startswith('give me more detail')


def test_example_followup_keeps_topic():
    history = [{'role': 'user', 'content': 'what is RAG'}, {'role': 'assistant', 'content': 'RAG retrieves documents before generation.'}]
    rewritten = rewrite_followup_query('give me a real world example', history)
    assert 'RAG' in rewritten


def test_simplify_followup_keeps_topic():
    history = [{'role': 'user', 'content': 'what is RAG'}, {'role': 'assistant', 'content': 'RAG retrieves documents before generation.'}]
    rewritten = rewrite_followup_query('explain it simply', history)
    assert 'RAG' in rewritten
