import pytest
from core.llm.adapters import HarmonyChannelAdapter
from core import metrics

CFG = {
    "collapse": {"whitespace": True},
    "ngram": {"n": 3, "window": 32},
    "reasoning": {"max_tokens": 50, "drop_from_history": True},
}


def _snap():
    return metrics.snapshot()["counters"]


@pytest.fixture(autouse=True)
def _reset_metrics():
    metrics.reset_for_tests()
    yield
    metrics.reset_for_tests()


def test_extra_final_and_after_final():
    a = HarmonyChannelAdapter(CFG)
    # normal final
    list(
        a.process_chunk(
            "<|start|>assistant<|channel|>final<|message|>Answer<|end|>"
        )
    )
    list(a.finalize())
    # extra final
    list(
        a.process_chunk(
            "<|start|>assistant<|channel|>final<|message|>Again<|end|>"
        )
    )
    # analysis after final
    list(
        a.process_chunk(
            "<|start|>assistant<|channel|>analysis<|message|>More<|end|>"
        )
    )
    # commentary after final
    list(
        a.process_chunk(
            "<|start|>assistant<|channel|>commentary<|message|>Meta<|end|>"
        )
    )
    snap = _snap()
    assert snap.get(
        "harmony_unexpected_order_total{type=extra_final}", 0
    ) >= 1
    assert snap.get(
        "harmony_unexpected_order_total{type=analysis_after_final}", 0
    ) >= 1
    assert snap.get(
        "harmony_unexpected_order_total{type=commentary_after_final}", 0
    ) >= 1
    # interleaved_final counts when any post-final channel appears
    assert snap.get(
        "harmony_unexpected_order_total{type=interleaved_final}", 0
    ) >= 1
