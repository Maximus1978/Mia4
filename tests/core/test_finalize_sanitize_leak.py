import re
from core.llm.adapters import HarmonyChannelAdapter
from core import metrics


def test_finalize_sanitize_emits_leak_metrics():
    # Reset metrics to isolate
    metrics.reset_for_tests()
    cfg = {
        "enabled": True,
        "reasoning": {"max_tokens": 16, "drop_from_history": True},
        "ngram": {"n": 3, "window": 64},
        "collapse": {"whitespace": True},
    }
    ad = HarmonyChannelAdapter(cfg)
    # Simulate having already processed some final tokens (bypass process_chunk):
    # We inject service markers that should trigger sanitation.
    ad._final_token_texts = ["Answer <|start|>assistant<|channel|>analysis<|message|> tail"]  # type: ignore[attr-defined]
    ad._final_tokens = 3  # bogus count; will be recomputed after sanitize
    ad._delivered_final_tokens = 0
    # Force finalize without additional buffering
    events = list(ad.finalize())
    # Ensure we got a final event
    assert any(e.get("type") == "final" for e in events)
    snap = metrics.snapshot()["counters"]
    # Filter reasoning_leak_total counters
    leak_keys = [k for k in snap if k.startswith("reasoning_leak_total")]
    # Expect at least the two reasons
    assert any("reason=service_marker_in_final" in k for k in leak_keys), leak_keys
    assert any("reason=finalize_sanitize" in k for k in leak_keys), leak_keys
    # Sanitized final tokens should not contain service pattern
    cleaned_final = "".join(ad._final_token_texts)  # type: ignore[attr-defined]
    assert not re.search(r"<\|[^|>]+\|>", cleaned_final), cleaned_final
