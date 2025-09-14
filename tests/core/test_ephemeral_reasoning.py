from core.llm.adapters import HarmonyChannelAdapter


def _run_adapter(chunks: list[str], cfg: dict):
    ad = HarmonyChannelAdapter(cfg)
    events = []
    for ch in chunks:
        for ev in ad.process_chunk(ch):  # type: ignore
            events.append(ev)
    for ev in ad.finalize():  # type: ignore
        events.append(ev)
    return events


def test_ephemeral_reasoning_drop_from_history_true():
    cfg = {
        "model_id": "test-model",
        "reasoning": {"max_tokens": 16, "drop_from_history": True},
        "collapse": {"whitespace": True},
    }
    # Two analysis tokens, one final token
    chunk = (
        "<|start|>assistant<|channel|>analysis<|message|>Think step<|end|>"
        "<|start|>assistant<|channel|>final<|message|>Answer<|return|>"
    )
    events = _run_adapter([chunk], cfg)
    final_ev = next(e for e in events if e.get("type") == "final")
    stats = final_ev["stats"]
    assert stats["reasoning_tokens"] == 2
    assert stats["final_tokens"] == 1
    # Reasoning text must be suppressed when drop_from_history = True
    assert final_ev["reasoning_text"] is None


def test_reasoning_retained_when_drop_from_history_false():
    cfg = {
        "model_id": "test-model",
        "reasoning": {"max_tokens": 16, "drop_from_history": False},
        "collapse": {"whitespace": True},
    }
    chunk = (
        "<|start|>assistant<|channel|>analysis<|message|>Plan path<|end|>"
        "<|start|>assistant<|channel|>final<|message|>Done<|return|>"
    )
    events = _run_adapter([chunk], cfg)
    final_ev = next(e for e in events if e.get("type") == "final")
    stats = final_ev["stats"]
    assert stats["reasoning_tokens"] == 2
    assert stats["final_tokens"] == 1
    # With drop_from_history False we expect reasoning_text present
    assert final_ev["reasoning_text"] == "Plan path"
