from core.llm.adapters import HarmonyChannelAdapter
from core import metrics


def setup_adapter(extra_cfg=None):  # helper
    cfg = {
        "model_id": "test-model",
        "reasoning": {"max_tokens": 32, "drop_from_history": True},
        "collapse": {"whitespace": True},
        "commentary_retention": {
            "mode": "metrics_only",
            "store_to_history": False,
        },
    }
    if extra_cfg:
        cfg.update(extra_cfg)
    metrics.reset_for_tests()
    return HarmonyChannelAdapter(cfg)


def test_unexpected_extra_final():
    adapter = setup_adapter()
    # Simulate final then extra final tokens in a later chunk.
    first = "<|start|>assistant<|channel|>final<|message|>done<|end|>"
    _ = list(adapter.process_chunk(first))
    # second chunk after closure with another final header
    _ = list(
        adapter.process_chunk(
            "<|start|>assistant<|channel|>final<|message|>ignored<|end|>"
        )
    )
    list(adapter.finalize())
    snap = metrics.snapshot()
    assert any(
        k.startswith("harmony_unexpected_order_total{type=extra_final")
        for k in snap["counters"].keys()
    ), snap["counters"]


def test_unexpected_analysis_after_final():
    adapter = setup_adapter()
    first = "<|start|>assistant<|channel|>final<|message|>f<|end|>"
    list(adapter.process_chunk(first))
    list(
        adapter.process_chunk(
            "<|start|>assistant<|channel|>analysis<|message|>later<|end|>"
        )
    )
    adapter.finalize()
    snap = metrics.snapshot()
    keys = snap["counters"].keys()
    assert any("analysis_after_final" in k for k in keys), keys
    assert any("interleaved_final" in k for k in keys), keys


def test_commentary_retention_summary_and_tokens_ratio():
    adapter = setup_adapter()
    stream = (
        "<|start|>assistant<|channel|>commentary<|message|>Note alpha "
        "beta<|end|><|start|>assistant<|channel|>final<|message|>answer one "
        "two<|end|>"
    )
    events = list(adapter.process_chunk(stream)) + list(adapter.finalize())
    final_ev = [e for e in events if e["type"] == "final"][0]
    summary = final_ev.get("commentary_retention_summary")
    assert summary and summary["mode"] == "metrics_only"
    assert "ratio_to_final" in summary
    # With commentary (3 tokens) and final tokens (>0) ratio should be > 0
    assert summary["ratio_to_final"] > 0
    snap = metrics.snapshot()
    # Commentary tokens should have been counted (3 tokens: Note alpha beta)
    token_keys = [
        k
        for k in snap["counters"].keys()
        if k.startswith("commentary_tokens_total")
    ]
    assert token_keys, snap["counters"]
