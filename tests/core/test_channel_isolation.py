import re
import pytest

from core.llm.adapters import HarmonyChannelAdapter
from core import metrics


def make_adapter():
    cfg = {
        "model_id": "test-model",
        "reasoning": {"max_tokens": 8, "drop_from_history": True},
        "collapse": {"whitespace": True},
    }
    return HarmonyChannelAdapter(cfg)


def stream_all(adapter, chunks):
    out = []
    for ch in chunks:
        for ev in adapter.process_chunk(ch):
            out.append(ev)
    for ev in adapter.finalize():
        out.append(ev)
    return out


def test_no_analysis_in_final_tokens():
    metrics.reset_for_tests()
    a = make_adapter()
    chunks = [
        "<|start|>assistant<|channel|>analysis<|message|>think step one<|end|>",
        "<|start|>assistant<|channel|>final<|message|>Hello world<|return|>",
    ]
    events = stream_all(a, chunks)
    deltas = [e for e in events if e.get("type") == "delta"]
    assert deltas, "expected final deltas"
    for d in deltas:
        assert "analysis|" not in d["text"]
        assert "<|channel|>analysis" not in d["text"]
    snap = metrics.snapshot()["counters"]
    # no leak metric for normal case
    assert not any(k.startswith("reasoning_leak_total") for k in snap.keys())


def test_analysis_after_final_emits_metrics():
    metrics.reset_for_tests()
    a = make_adapter()
    chunks = [
        "<|start|>assistant<|channel|>final<|message|>Hi<|end|>",
        "<|start|>assistant<|channel|>analysis<|message|>late<|end|>",
    ]
    _ = stream_all(a, chunks)
    snap = metrics.snapshot()["counters"]
    assert any(
        k.startswith("harmony_unexpected_order_total{type=analysis_after_final}")
        for k in snap.keys()
    )
    assert any(
        k.startswith("reasoning_leak_total{reason=post_final_analysis}")
        for k in snap.keys()
    )


def test_final_frame_has_stats_and_no_service_markers():
    metrics.reset_for_tests()
    a = make_adapter()
    chunks = [
        "<|start|>assistant<|channel|>final<|message|>Answer<|return|>"
    ]
    events = stream_all(a, chunks)
    final_frames = [e for e in events if e.get("type") == "final"]
    assert len(final_frames) == 1
    # ensure no service markers in any accumulated final text pieces
    joined = "".join(a._final_token_texts)
    assert "<|channel|>" not in joined
    assert "<|message|>" not in joined

