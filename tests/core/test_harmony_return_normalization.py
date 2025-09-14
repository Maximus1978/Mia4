from core.llm.adapters import HarmonyChannelAdapter


def test_return_token_normalization_flag():
    adapter = HarmonyChannelAdapter(
        {"reasoning": {"max_tokens": 8, "drop_from_history": True}}
    )
    # Simulate a final message ending with legacy <|return|>
    stream = (
        "<|start|>assistant<|channel|>final<|message|>Answer text<|return|>"
    )
    events = []
    for ch in stream.split("<"):
        if not ch:
            continue
        chunk = "<" + ch
        events.extend(list(adapter.process_chunk(chunk)))
    events.extend(list(adapter.finalize()))
    final_evt = [e for e in events if e["type"] == "final"][0]
    assert final_evt.get("normalized_return") is True
