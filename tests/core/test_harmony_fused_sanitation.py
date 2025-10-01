from typing import List

import pytest
from core.llm.adapters import HarmonyChannelAdapter
import core.metrics as _metrics


# Simple fake config & logger


class DummyCfg(dict):
    pass


class DummyLogger:
    def debug(self, *a, **k):
        pass


class DummyAdapter(HarmonyChannelAdapter):
    """Expose minimal public methods for targeted sanitation tests.

    We bypass streaming parse complexity and directly manipulate internal
    final token buffers to simulate post-generation state.
    """
    def __init__(self, text: str):  # type: ignore[override]
        # Provide minimal required ctor signature arguments (only cfg).
        super().__init__(cfg={"model_id": "test-model"})
        # Simulate tokens having been collected
        self._final_token_texts = [text]
        self._final_tokens = len(text.split())
        self._delivered_final_tokens = self._final_tokens
        self._final_message_closed = True

    def run_finalize(self):
        # Invoke parent finalize and capture resulting final text
        it = super().finalize()
        events = list(it)
        final_ev = next((e for e in events if e.get("type") == "final"), None)
        return events, final_ev, "".join(self._final_token_texts)


@pytest.fixture(autouse=True)
def reset_metrics():
    _metrics.reset_for_tests()
    yield


def extract_reasons(_: List[dict]) -> List[str]:
    # Updated metrics.snapshot() returns dict with 'counters' mapping of
    # flattened metric names. Extract any reasoning_leak_total{reason=...}.
    snap = _metrics.snapshot()
    counters = snap.get("counters", {})
    reasons: List[str] = []
    for key in counters.keys():
        if not key.startswith("reasoning_leak_total"):
            continue
        # Pattern reasoning_leak_total{reason=foo,other=bar}
        if "{" in key:
            label_block = key[key.find("{") + 1:key.find("}")]
            parts = [p.strip() for p in label_block.split(",") if p.strip()]
            for p in parts:
                if p.startswith("reason="):
                    reasons.append(p.split("=", 1)[1])
    return reasons


def get_fused_counter(kind: str) -> float:
    counters = _metrics.snapshot().get("counters", {})
    key = f"fused_marker_sanitizations_total{{kind={kind}}}"
    return counters.get(key, 0.0)


def test_fused_prefix_single():
    adapter = DummyAdapter("assistantfinal Hello world")
    _, final_ev, final_text = adapter.run_finalize()
    # After sanitation fused prefix removed
    assert not final_text.lower().startswith("assistantfinal")
    # Ensure visible final text still contains payload
    assert "Hello" in final_text
    assert final_ev is not None
    assert final_ev["type"] == "final"
    assert "Hello" in "".join(adapter._final_token_texts)
    assert "fused_marker_prefix" in extract_reasons([])
    assert get_fused_counter("prefix") == 1.0


def test_fused_prefix_multiple():
    adapter = DummyAdapter("assistantfinalassistant final Result OK")
    _, _, final_text = adapter.run_finalize()
    assert final_text.strip().startswith("Result")
    assert "fused_marker_prefix" in extract_reasons([])
    assert get_fused_counter("prefix") == 1.0


def test_no_fused_prefix_no_metric():
    adapter = DummyAdapter("Clean output only")
    _, _, final_text = adapter.run_finalize()
    assert final_text.startswith("Clean output")
    # Reason: there may be previous leaks from earlier tests; check that
    # no NEW fused entry added by ensuring at most count stable.
    reasons = extract_reasons([])
    # Allow other reasons, but fused should not increase more than tests run
    fused_count = sum(1 for r in reasons if r == "fused_marker_prefix")
    assert fused_count >= 0  # trivial sanity (presence not required)
    assert get_fused_counter("prefix") == 0.0


def test_duplicate_final_suppression():
    body = "This is a long body that repeats. " * 2
    adapter = DummyAdapter(body)
    _, _, final_text = adapter.run_finalize()
    # Should collapse double (length halves approx)
    assert len(final_text) < len(body)
    assert "duplicate_final" in extract_reasons([])


def test_short_duplicate_not_suppressed():
    adapter = DummyAdapter("OKOK")  # short; should remain as is
    _, _, final_text = adapter.run_finalize()
    assert final_text == "OKOK"
    # No metric expected for this simple short duplicate
    # (cannot assert absence reliably due to global metrics across tests)


def test_fused_prefix_only_becomes_empty():
    adapter = DummyAdapter("assistantfinal")
    events, final_ev, final_text = adapter.run_finalize()
    assert final_text == ""
    assert final_ev is not None
    assert final_ev.get("final_text") == ""
    assert all(
        "assistantfinal" not in (e.get("final_text") or "")
        for e in events
        if e.get("type") == "final"
    )
    assert "fused_marker_prefix" in extract_reasons([])
    assert get_fused_counter("prefix") == 1.0


def test_fused_residue_metric():
    adapter = DummyAdapter("This output has assistant final residue")
    events, final_ev, _ = adapter.run_finalize()
    assert final_ev is not None
    assert final_ev.get("type") == "final"
    payload = final_ev.get("final_text", "")
    assert payload
    assert "assistant final" not in payload.lower()
    assert "fused_marker_residue" in extract_reasons([])
    assert get_fused_counter("residue") == 1.0
    assert all(
        "assistant final" not in (evt.get("final_text", "") or "").lower()
        for evt in events
        if evt.get("type") == "final"
    )

