from core.llm.adapters import HarmonyChannelAdapter


def test_harmony_commentary_channel_adapter_basic():  # noqa: D401
    cfg = {
        "reasoning": {"max_tokens": 256, "drop_from_history": True},
        "collapse": {"whitespace": True},
    }
    adapter = HarmonyChannelAdapter(cfg)
    # Build a stream containing analysis, commentary, final (short tokens).
    stream = (
        "<|start|>assistant<|channel|>analysis<|message|>a b c<|end|>"
        "<|start|>assistant<|channel|>commentary<|message|>Plan: x<|end|>"
        "<|start|>assistant<|channel|>final<|message|>Answer ok.<|end|>"
    )
    events = list(adapter.process_chunk(stream)) + list(adapter.finalize())
    commentary = [e for e in events if e.get("type") == "commentary"]
    assert commentary, "expected commentary event"
    assert commentary[0]["text"].startswith("Plan:"), commentary
    final_ev = [e for e in events if e.get("type") == "final"][0]
    stats = final_ev["stats"]
    assert stats["reasoning_tokens"] == 3, stats  # a b c
    assert stats["final_tokens"] >= 2, stats


def test_commentary_basic():  # noqa: D401
    cfg = {
        "enabled": True,
        "reasoning": {"max_tokens": 16, "drop_from_history": True},
        "ngram": {"n": 3, "window": 32},
        "collapse": {"whitespace": True},
    }
    adapter = HarmonyChannelAdapter(cfg)
    # One analysis, one commentary, one final
    sample = (
        "<|start|>assistant<|channel|>analysis<|message|>think fast<|end|>"
        "<|start|>assistant<|channel|>commentary<|message|>Plan: do X<|end|>"
        "<|start|>assistant<|channel|>final<|message|>answer done<|return|>"
    )
    events = list(adapter.process_chunk(sample)) + list(adapter.finalize())
    kinds = [e["type"] for e in events]
    assert "commentary" in kinds, kinds
    assert any(e["type"] == "analysis" for e in events)
    assert any(e["type"] == "delta" for e in events)
    final = [e for e in events if e["type"] == "final"][0]
    # Commentary should not affect token counts
    assert final["stats"]["final_tokens"] >= 2
    assert final["stats"]["reasoning_tokens"] >= 2  # 'think' 'fast'
