import os
from core import metrics
from core.events import on, emit, reset_listeners_for_tests, GenerationStarted


def test_handler_exception_increments_metric():
    os.environ["MIA_LLAMA_FAKE"] = "1"
    reset_listeners_for_tests()
    metrics.reset_for_tests()

    # faulty handler that raises
    def boom(name, payload):  # noqa: D401
        raise RuntimeError("boom")

    on(boom)
    # also add a no-op to ensure continued dispatch
    on(lambda n, p: None)

    # Emit a generation started event (will go through core.events.emit path)
    emit(GenerationStarted(
        request_id="r1",
        model_id="m1",
        role="primary",
        prompt_tokens=1,
        correlation_id="r1",
    ))

    snap = metrics.snapshot()
    counters = snap["counters"]
    # handler_exceptions_total should have at least one entry
    # for GenerationStarted
    matching = [
        v
        for k, v in counters.items()
        if k.startswith(
            "handler_exceptions_total{event=GenerationStarted"
        )
    ]
    assert matching, f"No handler_exceptions_total counter for GenerationStarted: {counters}"  # noqa: E501
    assert sum(matching) >= 1
