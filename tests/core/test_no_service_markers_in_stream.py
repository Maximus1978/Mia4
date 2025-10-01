import re
from core.llm.adapters import HarmonyChannelAdapter


def test_no_service_markers_in_delta_and_final():
    cfg = {
        "model_id": "mtest",
        "reasoning": {"max_tokens": 8},
        "collapse": {"whitespace": True},
    }
    ad = HarmonyChannelAdapter(cfg)
    # Simulate mixed chunks that should yield clean final output
    chunks = [
        "<|start|>assistant<|channel|>analysis<|message|>thinking step<|end|>",
        "<|start|>assistant<|channel|>final<|message|>Hello world<|return|>",
    ]
    events = []
    for ch in chunks:
        events.extend(list(ad.process_chunk(ch)))
    events.extend(list(ad.finalize()))
    # Collect delta text
    deltas = [e["text"] for e in events if e.get("type") == "delta"]
    assert deltas, "expected delta events"
    for d in deltas:
        assert "<|channel|>" not in d
        assert "<|start|>" not in d
        assert "<|message|>" not in d
        assert not re.search(r"<\|[^|>]+\|>", d)
    finals = [e for e in events if e.get("type") == "final"]
    assert finals, "expected final event"
    # Adapter final text lives in _final_token_texts; ensure sanitized
    joined = "".join(ad._final_token_texts)
    assert not re.search(r"<\|[^|>]+\|>", joined), joined
