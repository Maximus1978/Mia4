from core.eventbus import subscribe, emit
from core import metrics


def test_eventbus_basic_dispatch():
    got = []
    subscribe("TestEvent", lambda p: got.append(p["value"]))
    subscribe("TestEvent", lambda p: got.append(p["value"] * 2))
    emit("TestEvent", {"value": 3})
    assert sorted(got) == [3, 6]
    snap = metrics.snapshot()["counters"]
    assert any("events_emitted_total" in k for k in snap)
