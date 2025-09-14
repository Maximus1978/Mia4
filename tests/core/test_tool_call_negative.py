import json
from core.llm.adapters import HarmonyChannelAdapter

CFG = {
    "reasoning": {"max_tokens": 32},
    "ngram": {"n": 3, "window": 32},
    "collapse": {"whitespace": True},
}


def _collect(adapter, chunks):
    events = []
    for c in chunks:
        events.extend(list(adapter.process_chunk(c)))
    events.extend(list(adapter.finalize()))
    return events


def test_tool_call_oversize_payload(monkeypatch):
    adapter = HarmonyChannelAdapter(CFG)
    big_args = {"a": "x" * 9000}
    payload = json.dumps({"tool": "echo", "arguments": big_args})
    stream = f"<|start|>assistant<|channel|>tool<|message|>{payload}<|end|>"
    events = _collect(adapter, [stream])
    # Expect raw tool channel event captured
    raw = [e for e in events if e["type"] == "tool_channel_raw"]
    assert raw, "tool_channel_raw missing"
    # Route converts oversize to error; adapter only surfaces raw tool channel.


def test_tool_call_malformed_json():
    adapter = HarmonyChannelAdapter(CFG)
    payload = '{"tool": "echo", "arguments": { invalid }'  # malformed
    stream = f"<|start|>assistant<|channel|>tool<|message|>{payload}<|end|>"
    events = _collect(adapter, [stream])
    raw = [e for e in events if e["type"] == "tool_channel_raw"]
    assert raw, "tool_channel_raw missing for malformed JSON"
