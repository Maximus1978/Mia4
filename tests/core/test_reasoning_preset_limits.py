from __future__ import annotations

from core.llm.adapters import HarmonyChannelAdapter

BASE_REASONING = " ".join(f"r{i}" for i in range(1000))  # large pool
FINAL_PART = "ANSWER final content"


def run_with_cap(cap: int) -> dict:
    # Construct multiple analysis segments then a final segment.
    reasoning_tokens_pool = BASE_REASONING.split()[: cap + 50]
    reasoning_str = " ".join(reasoning_tokens_pool)
    raw = (
        f"<|start|>assistant<|channel|>analysis<|message|>{reasoning_str}"
        "<|end|><|start|>assistant<|channel|>final<|message|>"
        f"{FINAL_PART}<|end|>"
    )
    adapter = HarmonyChannelAdapter({"reasoning": {"max_tokens": cap}})
    events = list(adapter.process_chunk(raw)) + list(adapter.finalize())
    stats = events[-1]["stats"]
    return stats


def test_reasoning_caps_increasing():
    caps = [128, 256, 512]
    stats_list = [run_with_cap(c) for c in caps]
    # Ensure reasoning_tokens <= cap and strictly increasing
    prev = -1
    for cap, stats in zip(caps, stats_list):
        r = stats["reasoning_tokens"]
        assert r <= cap
        assert r > prev
        prev = r


def test_reasoning_ratio_nonzero():
    cap = 128
    stats = run_with_cap(cap)
    assert stats["reasoning_tokens"] > 0
    # If final tokens missing due to provider segmentation, ratio may be 1.0
    assert stats["reasoning_ratio"] > 0
