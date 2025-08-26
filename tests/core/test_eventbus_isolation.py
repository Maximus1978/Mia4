from core.eventbus import subscribe, emit


def test_eventbus_handler_isolation():
    calls = []

    def bad(_):
        calls.append("bad")
        raise RuntimeError("boom")

    def good(_):
        calls.append("good")

    subscribe("IsoEvent", bad)
    subscribe("IsoEvent", good)
    emit("IsoEvent", {})
    assert "good" in calls
