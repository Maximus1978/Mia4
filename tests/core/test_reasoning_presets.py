from core.llm.factory import apply_reasoning_overrides
from core.config.loader import get_config


def test_reasoning_overrides_known_mode():
    cfg = get_config()  # ensure loaded
    base = {"temperature": 0.1, "top_p": 0.5, "other": 42}
    out = apply_reasoning_overrides(base, "medium")
    assert out["temperature"] == cfg.llm.reasoning_presets["medium"][
        "temperature"
    ]
    assert out["top_p"] == cfg.llm.reasoning_presets["medium"]["top_p"]
    assert out["other"] == 42


def test_reasoning_overrides_unknown_mode():
    base = {"temperature": 0.2}
    out = apply_reasoning_overrides(base, "nope")
    assert out == base


def test_reasoning_overrides_none_mode():
    base = {"temperature": 0.3}
    out = apply_reasoning_overrides(base, None)
    assert out == base
