import sys
import types
from types import SimpleNamespace
from pathlib import Path
import importlib
import importlib.util

import pytest

TESTS_CORE_DIR = Path(__file__).resolve().parent
ROOT = TESTS_CORE_DIR.parents[1]

# Ensure repository root precedes namespace paths that shadow core package.
if str(TESTS_CORE_DIR) in sys.path:
    sys.path.remove(str(TESTS_CORE_DIR))
for candidate in (ROOT / "src", ROOT):
    candidate_str = str(candidate)
    if candidate.exists() and candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

core_mod = sys.modules.get("core")
if core_mod is None or getattr(core_mod.__spec__, "loader", None).__class__.__name__ == "NamespaceLoader":
    spec = importlib.util.spec_from_file_location("core", ROOT / "core" / "__init__.py")
    core_pkg = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(core_pkg)  # type: ignore[union-attr]
    sys.modules["core"] = core_pkg

_ORIG_CONFIG_MODULE = sys.modules.get("core.config")

if _ORIG_CONFIG_MODULE is None:
    fake_cfg_module = types.ModuleType("core.config")
    _llm_cfg = SimpleNamespace(
        primary=SimpleNamespace(max_output_tokens=64),
        system_prompt=SimpleNamespace(text="System base instructions"),
        reasoning_presets={"medium": {"reasoning_max_tokens": 256}},
        postproc={},
    )

    def _get_config():  # noqa: D401
        return SimpleNamespace(llm=_llm_cfg)

    fake_cfg_module.get_config = _get_config  # type: ignore[attr-defined]
    fake_cfg_module.clear_config_cache = lambda: None  # type: ignore[attr-defined]
    sys.modules["core.config"] = fake_cfg_module

from core.llm.pipeline.primary import PrimaryPipeline


@pytest.fixture(autouse=True)
def _restore_core_config():  # noqa: D401
    yield
    if _ORIG_CONFIG_MODULE is None:
        sys.modules.pop("core.config", None)
    else:
        sys.modules["core.config"] = _ORIG_CONFIG_MODULE


class _StreamProv:
    def __init__(self, chunks):  # noqa: D401
        self._chunks = chunks

    def info(self):  # noqa: D401
        return SimpleNamespace(
            id="model",
            role="primary",
            context_length=4096,
            metadata={},
        )

    def stream(self, prompt: str, **kwargs):  # noqa: D401
        for chunk in self._chunks:
            yield chunk


def test_harmony_stream_skips_raw_fallback():  # noqa: D401
    chunks = [
        "<|start|>assistant<|channel|>analysis<|message|>Need to",
        " think through options<|end|><|start|>assistant<|channel|>final<|message|>Hello",
        " world!<|return|>",
    ]
    provider = _StreamProv(chunks)
    pipe = PrimaryPipeline()
    ctx = pipe.prepare(
        request_id="req-ssot",
        model_id="model",
        provider=provider,
        prompt="user question?",
        session_messages=None,
        reasoning_mode="medium",
        user_sampling={"max_tokens": 64},
        passport_defaults={"max_output_tokens": 64},
        sampling_origin="custom",
    )

    stream_iter = iter(pipe.stream(ctx))
    first_event = next(stream_iter)
    assert first_event["type"] == "analysis"

    events = [first_event, *list(stream_iter)]
    delta_texts = [ev["text"] for ev in events if ev.get("type") == "delta"]
    assert delta_texts, "expected user-visible tokens from final channel"
    for text in delta_texts:
        assert "<|" not in text
        assert not text.lstrip().startswith(("analysis", "commentary", "assistant"))
