from core.llm.adapters import HarmonyChannelAdapter
from core import metrics


def test_sse_stream_never_mixes_analysis_into_delta():
    metrics.reset_for_tests()
    adapter = HarmonyChannelAdapter({
        "model_id": "sse-test",
        "reasoning": {"max_tokens": 8, "drop_from_history": True},
        "collapse": {"whitespace": True},
    })
    chunks = [
        "<|start|>assistant<|channel|>analysis<|message|>step one<|end|>",
        "<|start|>assistant<|channel|>analysis<|message|>step two<|end|>",
        "<|start|>assistant<|channel|>final<|message|>Public answer here<|return|>",
    ]
    deltas = []
    analysis = []
    for ch in chunks:
        for ev in adapter.process_chunk(ch):
            if ev.get("type") == "delta":
                deltas.append(ev["text"])
            if ev.get("type") == "analysis":
                analysis.append(ev["text"])
    for ev in adapter.finalize():
        if ev.get("type") == "delta":
            deltas.append(ev["text"])
    # Assert no analysis artifacts inside delta tokens
    for dt in deltas:
        assert "analysis|" not in dt
        assert "<|channel|>analysis" not in dt
    assert analysis, "expected separate analysis events"
    final_joined = "".join(deltas)
    # service markers stripped before emission
    assert "<|channel|>" not in final_joined
    snap = metrics.snapshot()["counters"]
    # Normal flow: no leak metrics
    assert not any(k.startswith("reasoning_leak_total") for k in snap.keys())
