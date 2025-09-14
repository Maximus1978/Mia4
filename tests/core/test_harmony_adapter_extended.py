from core.llm.adapters import HarmonyChannelAdapter


def _run_adapter(chunks, cfg=None):
    """Utility to feed chunks and collect events (analysis/delta/final)."""
    cfg = cfg or {
        "reasoning": {"max_tokens": 64, "drop_from_history": True},
        "collapse": {"whitespace": True},
        "ngram": {"n": 3, "window": 64},
    }
    adapter = HarmonyChannelAdapter(cfg)
    out = []
    for ch in chunks:
        out.extend(list(adapter.process_chunk(ch)))
    out.extend(list(adapter.finalize()))
    return out


def test_multi_analysis_blocks_hf01():
    """HF-01: multiple analysis channel messages before final."""
    text = (
        "<|start|>assistant<|channel|>analysis<|message|> шаг один <|end|>"
        "<|start|>assistant<|channel|>analysis<|message|> второй этап <|end|>"
        "<|start|>assistant<|channel|>final<|message|> итог ответа <|return|>"
    )
    events = _run_adapter([text])
    analysis = [e for e in events if e["type"] == "analysis"]
    final_tokens = [e for e in events if e["type"] == "delta"]
    summary = events[-1]
    assert summary["type"] == "final"
    # Expect reasoning tokens >0 and aggregated from both analysis messages
    assert len(analysis) >= 3  # "шаг", "один", "второй" at minimum
    assert summary["stats"]["reasoning_tokens"] == len(analysis)
    assert summary["stats"]["final_tokens"] == len(final_tokens)
    assert summary["stats"]["reasoning_ratio"] > 0


def test_plain_fallback_no_harmony_tokens_hf03():
    """HF-03: Provider emits no harmony tokens -> all final, reasoning=0."""
    # Intentionally no <|start|> tokens
    text = "Простой вывод без специальных токенов и структуры"
    events = _run_adapter([text])
    summary = events[-1]
    assert summary["type"] == "final"
    assert summary["stats"]["reasoning_tokens"] == 0
    assert summary["stats"]["final_tokens"] > 0
    assert summary["stats"]["reasoning_ratio"] == 0
    assert summary.get("parse_error") is None


def test_unterminated_channel_parse_error_hf04_hf10():
    """HF-04 / HF-10: Unterminated channel triggers parse_error metric flag."""
    # Start analysis but never close with <|end|>
    text = (
        "<|start|>assistant<|channel|>analysis<|message|> "
        "незаконченный блок"
    )
    events = _run_adapter([text])
    summary = events[-1]
    assert summary["type"] == "final"
    assert summary["parse_error"] is True
    # All tokens counted as reasoning, none final
    assert summary["stats"]["final_tokens"] == 0
    assert summary["stats"]["reasoning_tokens"] > 0
    assert summary["stats"]["reasoning_ratio"] == 1.0


def test_reasoning_cap_enforced():
    """Ensure max reasoning tokens cap is applied."""
    cfg = {
        "reasoning": {"max_tokens": 3, "drop_from_history": True},
        "collapse": {"whitespace": True},
        "ngram": {"n": 3, "window": 32},
    }
    # 5 tokens inside analysis should be truncated to 3
    text = (
        "<|start|>assistant<|channel|>analysis<|message|> "
        "один два три четыре пять <|end|>"
        "<|start|>assistant<|channel|>final<|message|> финал <|return|>"
    )
    events = _run_adapter([text], cfg)
    summary = events[-1]
    assert summary["stats"]["reasoning_tokens"] == 3
    # Final tokens may be zero if splitting consumed only analysis tokens first
    assert summary["stats"]["final_tokens"] >= 0
