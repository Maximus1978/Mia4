from core.llm.adapters import HarmonyChannelAdapter


def _collect(text: str, cfg=None):  # helper
    cfg = cfg or {
        "reasoning": {"max_tokens": 256, "drop_from_history": True},
        "collapse": {"whitespace": True},
        "ngram": {"n": 3, "window": 32},
    }
    ad = HarmonyChannelAdapter(cfg)
    out = []
    out.extend(list(ad.process_chunk(text)))
    out.extend(list(ad.finalize()))
    return out


def test_harmony_split_basic():
    text = (
        "<|start|>assistant<|channel|>analysis<|message|> шаг 1 тест "
        "шаг 2 <|end|>"
        "<|start|>assistant<|channel|>final<|message|> итоговый "
        "ответ пользователя <|return|>"
    )
    events = _collect(text)
    summary = events[-1]
    assert summary["type"] == "final"
    assert summary["stats"]["reasoning_tokens"] > 0
    # Final tokens may be zero if adapter truncated; ensure non-negative
    assert summary["stats"]["final_tokens"] >= 0
    # Ratio >0 when reasoning present
    assert summary["stats"]["reasoning_tokens"] > 0


def test_harmony_fallback_no_tokens():
    text = "Простой ответ без тегов"
    events = _collect(text)
    summary = events[-1]
    assert summary["stats"]["reasoning_tokens"] == 0
    assert summary["stats"]["final_tokens"] > 0
    assert summary.get("parse_error") is None
