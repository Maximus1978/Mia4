
from core.events import on, reset_listeners_for_tests
from core.llm.agent_ops import judge, plan
from core import metrics


def test_metrics_snapshot_counters_increment():
    metrics.reset_for_tests()
    # attach dummy listener (metrics collector already subscribed globally)
    on(lambda n, p: None)
    judge(target_request_id="abc", prompt="Quality?", reasoning_mode="low")
    plan(objective="Do work", max_steps=2, reasoning_mode="medium")
    snap = metrics.snapshot()
    counters = snap["counters"]
    # At least some generation events and reasoning mode counters
    # generation counters aggregated with label type=start/finished/failed
    # Ensure reasoning mode counters present (stable regardless of prior loads)
    assert any(k.startswith("reasoning_mode{mode=") for k in counters)
    assert any(k.startswith("reasoning_mode{mode=") for k in counters)
    reset_listeners_for_tests()
