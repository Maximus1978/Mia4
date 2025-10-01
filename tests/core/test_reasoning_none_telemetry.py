import pytest

from core import metrics
from core.events import reset_listeners_for_tests, subscribe
from core.llm.adapters import HarmonyChannelAdapter


@pytest.fixture()
def reset_metrics_and_events():
    metrics.reset_for_tests()
    reset_listeners_for_tests()
    captured = []

    def handler(name, payload):
        captured.append((name, payload))

    unsubscribe = subscribe(handler)
    try:
        yield captured
    finally:
        unsubscribe()


def test_reasoning_none_emits_event_and_metric(reset_metrics_and_events):
    captured = reset_metrics_and_events
    adapter = HarmonyChannelAdapter({"model_id": "model-test"})
    adapter.set_context(request_id="req-123", model_id="model-actual")

    stream = "<|start|>assistant<|channel|>final<|message|>Hi there!<|return|>"
    list(adapter.process_chunk(stream))
    list(adapter.finalize())

    reasoning_events = [
        payload
        for name, payload in captured
        if name == "ReasoningSuppressedOrNone"
    ]
    assert reasoning_events, "ReasoningSuppressedOrNone event was not emitted"
    assert reasoning_events[0]["request_id"] == "req-123"
    assert reasoning_events[0]["model_id"] == "model-actual"
    snapshot = metrics.snapshot()
    assert (
        snapshot["counters"].get(
            "reasoning_none_total{reason=no-analysis-channel+drop_history}"
        )
        == 1.0
    )
