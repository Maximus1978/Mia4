from core.llm.adapters import HarmonyChannelAdapter

CFG = {
    "collapse": {"whitespace": True},
    "ngram": {"n": 3, "window": 32},
    "reasoning": {"max_tokens": 20, "drop_from_history": True},
}


def test_single_tool_call_minimal():
    a = HarmonyChannelAdapter(CFG)
    events = list(a.process_chunk(
        "<|start|>assistant"
        "<|recipient|>math.add"
        "<|message|>{\\n  \"a\":1, \"b\":2\\n}<|end|>"
    ))
    assert any(e.get("type") == "tool_call" for e in events)
    tool = [e for e in events if e.get("type") == "tool_call"][0]
    assert tool["recipient"] == "math.add"
    assert "\"a\"" in tool["args_text"]


def test_tool_call_with_constrain_and_followed_by_final():
    a = HarmonyChannelAdapter(CFG)
    part1 = (
        "<|start|>assistant"
        "<|recipient|>search.web"
        "<|constrain|><|constrain|>"
    )
    part2 = (
        "<|message|>query: cats<|end|>"
        "<|channel|>final<|message|>Done<|end|>"
    )
    ev1 = list(a.process_chunk(part1))
    # incomplete -> no events yet
    assert ev1 == []
    ev2 = list(a.process_chunk(part2))
    # Should include tool_call and final delta tokens
    tool_calls = [e for e in ev2 if e.get("type") == "tool_call"]
    assert len(tool_calls) == 1
    tc = tool_calls[0]
    assert tc["recipient"] == "search.web"
    assert tc["constrain"] is True
    # finalize to flush stats
    list(a.finalize())


def test_multiple_tool_calls_streaming():
    a = HarmonyChannelAdapter(CFG)
    stream = (
        "<|start|>assistant<|recipient|>tool.one<|message|>{} <|end|>"
        "<|start|>assistant<|recipient|>tool.two<|message|>{} <|end|>"
        "<|start|>assistant<|channel|>final<|message|>Answer<|end|>"
    )
    out = list(a.process_chunk(stream))
    recips = [e["recipient"] for e in out if e.get("type") == "tool_call"]
    assert recips == ["tool.one", "tool.two"]
    list(a.finalize())
