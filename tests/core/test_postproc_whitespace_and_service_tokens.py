from core.llm.adapters import HarmonyChannelAdapter


def _run(chunks, cfg):
    ad = HarmonyChannelAdapter(cfg)
    out = []
    for c in chunks:
        out.extend(list(ad.process_chunk(c)))
    out.extend(list(ad.finalize()))
    return out


def test_whitespace_collapse_basic():
    # Final only (no harmony tokens) -> entire output final tokens,
    # collapsed whitespace
    chunks = ["word1", "   \n\t  word2   \n\n   ", "word3"]
    cfg = {"collapse": {"whitespace": True}, "reasoning": {"max_tokens": 10}}
    events = _run(chunks, cfg)
    joined = "".join(e.get("text", "") for e in events if e["type"] == "delta")
    assert "  " not in joined


def test_service_token_filtering_harmony_tokens_removed():
    # Provide Harmony formatted message containing analysis then final
    raw = (
        "<|start|>assistant<|channel|>analysis<|message|>some reasoning"
        " tokens<|end|><|start|>assistant<|channel|>final<|message|>final"
        " answer here<|end|>"
    )
    events = _run([raw], {"reasoning": {"max_tokens": 10}})
    combined = "".join(
        e.get("text", "") for e in events if e["type"] == "delta"
    )
    assert "<|start|>" not in combined and "<|channel|>" not in combined
