from __future__ import annotations

import sys
import types

from core.metrics import reset_for_tests, snapshot
from core.llm.llama_cpp_provider import LlamaCppProvider


def _install_dummy_llama(monkeypatch, llama_cls):
    module = types.SimpleNamespace(Llama=llama_cls)
    monkeypatch.setitem(sys.modules, "llama_cpp", module)


def test_llama_provider_passes_gpu_args(monkeypatch):
    reset_for_tests()
    captured: dict[str, object] = {}

    class DummyLlama:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def __call__(self, *args, **kwargs):  # pragma: no cover
            return {}

    _install_dummy_llama(monkeypatch, DummyLlama)

    provider = LlamaCppProvider(
        model_path="dummy://model",
        model_id="model-test",
        role="primary",
        context_length=2048,
        temperature=None,
        top_p=None,
        top_k=None,
        repeat_penalty=None,
        min_p=None,
        max_output_tokens=None,
        n_threads=6,
        n_batch=128,
        n_gpu_layers=10,
    )

    provider.load()

    assert captured.get("n_gpu_layers") == 10
    assert captured.get("n_threads") == 6
    assert captured.get("n_batch") == 128
    assert provider._state.stub is False  # type: ignore[attr-defined]


def test_llama_provider_auto_fallback(monkeypatch):
    reset_for_tests()
    attempts: list[int | None] = []

    class FlakyLlama:
        def __init__(self, **kwargs):
            attempts.append(kwargs.get("n_gpu_layers"))
            if kwargs.get("n_gpu_layers") != 0:
                raise RuntimeError("CUDA error: OOM")

        def __call__(self, *args, **kwargs):  # pragma: no cover
            return {}

    _install_dummy_llama(monkeypatch, FlakyLlama)

    # Mock config to return require_gpu=False (allow fallback)
    from core.config.schemas.llm import PrimaryLLMConfig
    mock_primary = PrimaryLLMConfig(
        id="model-test",
        n_gpu_layers="auto",
        require_gpu=False,  # Allow CPU fallback
    )

    class MockLLMConfig:
        primary = mock_primary

    class MockConfig:
        llm = MockLLMConfig()

    import core.config
    monkeypatch.setattr(
        core.config, "get_config", lambda: MockConfig()
    )

    provider = LlamaCppProvider(
        model_path="dummy://model",
        model_id="model-test",
        role="primary",
        context_length=2048,
        temperature=None,
        top_p=None,
        top_k=None,
        repeat_penalty=None,
        min_p=None,
        max_output_tokens=None,
        n_threads=None,
        n_batch=None,
        n_gpu_layers="auto",
    )

    provider.load()

    assert attempts == [-1, 0]
    counters = snapshot()["counters"]
    assert counters.get("llama_gpu_fallback_total{model=model-test}") == 1
    assert provider._state.stub is False  # type: ignore[attr-defined]
