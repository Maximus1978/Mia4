import pytest

from core.llm.adapters import HarmonyChannelAdapter
from core import metrics


@pytest.fixture()
def base_cfg():
    return {
        "enabled": True,
        "reasoning": {"max_tokens": 32, "drop_from_history": True},
        "ngram": {"n": 3, "window": 32},
        "collapse": {"whitespace": True},
    }


def _collect(adapter, chunks):  # noqa: D401
    out = []
    for ch in chunks:
        out.extend(list(adapter.process_chunk(ch)))
    out.extend(list(adapter.finalize()))
    return out


def test_parse_error_unknown_channel(base_cfg):  # noqa: D401
    metrics.reset_for_tests()
    # Unknown channel name after <|channel|> should count parse error
    chunks = [
        "<|start|>assistant<|channel|>weirdchan<|message|>Ignored<|end|>",
        "<|start|>assistant<|channel|>final<|message|>Hi<|end|>",
    ]
    adapter = HarmonyChannelAdapter(base_cfg)
    events = _collect(adapter, chunks)
    assert any(e["type"] == "final" for e in events)
    snap = metrics.snapshot()
    counters = snap.get("counters", {})
    # Current adapter only exposes harmony_parse_error_total{stage=...}
    assert any(
        k.startswith("harmony_parse_error_total") for k in counters.keys()
    ), f"expected parse error metric, snapshot={snap}"


def test_unexpected_multiple_final(base_cfg):  # noqa: D401
    metrics.reset_for_tests()
    # Two final channels -> unexpected order metric increment
    chunks = [
        "<|start|>assistant<|channel|>final<|message|>One<|end|>",
        "<|start|>assistant<|channel|>final<|message|>Two<|end|>",
    ]
    adapter = HarmonyChannelAdapter(base_cfg)
    _collect(adapter, chunks)
    snap = metrics.snapshot()
    counters = snap.get("counters", {})
    # Assert unexpected-order metric (extra_final) recorded
    assert any(
        k.startswith("harmony_unexpected_order_total{type=extra_final")
        for k in counters.keys()
    ), counters
