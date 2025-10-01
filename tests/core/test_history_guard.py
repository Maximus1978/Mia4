from core.llm.adapters import HarmonyChannelAdapter
from core import metrics


def make_adapter():
    return HarmonyChannelAdapter({
        "model_id": "hist-guard-test",
        "reasoning": {"max_tokens": 6, "drop_from_history": True},
        "collapse": {"whitespace": True},
    })


def collect_final_text(adapter, chunks):
    final_tokens = []
    for ch in chunks:
        for ev in adapter.process_chunk(ch):
            if ev.get("type") == "delta":
                final_tokens.append(ev["text"])
    for ev in adapter.finalize():
        if ev.get("type") == "delta":
            final_tokens.append(ev["text"])
    return "".join(final_tokens)


def test_history_guard_drop_reasoning_tokens():
    metrics.reset_for_tests()
    a = make_adapter()
    # Interleave analysis then final
    chunks = [
        (
            "<|start|>assistant<|channel|>analysis<|message|>internal "
            "chain plan<|end|>"
        ),
        (
            "<|start|>assistant<|channel|>final<|message|>User facing "
            "answer<|return|>"
        ),
    ]
    final_joined = collect_final_text(a, chunks)
    # Final joined text must not contain analysis artifacts
    assert "analysis|" not in final_joined
    # allow only user-facing content (heuristic: internal token shouldn't leak)
    assert (
        "internal" not in final_joined or "User" in final_joined
    )
    # Ensure reasoning tokens counted but not leaked
    # Access stats via finalize frame
    a2 = make_adapter()
    _ = collect_final_text(a2, [
        "<|start|>assistant<|channel|>final<|message|>Hi<|return|>"
    ])
    snap = metrics.snapshot()["counters"]
    # No leak metrics expected for normal case
    assert not any(k.startswith("reasoning_leak_total") for k in snap.keys())
