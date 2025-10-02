"""Test require_gpu config enforcement (P0 GPU acceleration fix)."""
from __future__ import annotations

import sys
import types
import pytest

from core.llm.llama_cpp_provider import LlamaCppProvider


def _install_failing_llama(monkeypatch):
    """Install a Llama stub that always fails on GPU init."""

    class FailingLlama:
        def __init__(self, **kwargs):
            if kwargs.get("n_gpu_layers", 0) != 0:
                raise RuntimeError("CUDA error: out of memory")
            # CPU path succeeds
            pass

        def __call__(self, *args, **kwargs):  # pragma: no cover
            return {}

    module = types.SimpleNamespace(Llama=FailingLlama)
    monkeypatch.setitem(sys.modules, "llama_cpp", module)


def test_require_gpu_blocks_cpu_fallback(monkeypatch, tmp_path):
    """When require_gpu=true, GPU failure must raise ModelLoadError."""
    
    class FailingLlama:
        def __init__(self, **kwargs):
            if kwargs.get("n_gpu_layers", 0) != 0:
                raise RuntimeError("CUDA error: out of memory")

        def __call__(self, *args, **kwargs):  # pragma: no cover
            return {}

    module = types.SimpleNamespace(Llama=FailingLlama)
    monkeypatch.setitem(sys.modules, "llama_cpp", module)

    # Mock config to return require_gpu=True
    from core.config.schemas.llm import PrimaryLLMConfig
    mock_primary = PrimaryLLMConfig(
        id="test-model",
        n_gpu_layers="auto",
        require_gpu=True,
    )

    class MockLLMConfig:
        primary = mock_primary

    class MockConfig:
        llm = MockLLMConfig()

    def mock_get_config():
        return MockConfig()

    # Patch at the import location used in llama_cpp_provider.py
    import core.config
    monkeypatch.setattr(core.config, "get_config", mock_get_config)

    provider = LlamaCppProvider(
        model_path="dummy://model",
        model_id="test-model",
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

    # Expect hard failure (no stub fallback)
    with pytest.raises(RuntimeError, match="CUDA error"):
        provider.load()

    # Provider should not be loaded
    assert not provider._state.loaded  # type: ignore[attr-defined]


def test_require_gpu_false_allows_fallback(monkeypatch):
    """When require_gpu=false (default), CPU fallback is permitted."""
    _install_failing_llama(monkeypatch)

    # Mock config with require_gpu=False (default)
    from core.config.schemas.llm import PrimaryLLMConfig
    mock_primary = PrimaryLLMConfig(
        id="test-model",
        n_gpu_layers="auto",
        require_gpu=False,
    )

    class MockLLMConfig:
        primary = mock_primary

    class MockConfig:
        llm = MockLLMConfig()

    def mock_get_config():
        return MockConfig()

    monkeypatch.setattr("core.config.get_config", mock_get_config)

    provider = LlamaCppProvider(
        model_path="dummy://model",
        model_id="test-model",
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

    # Should succeed with CPU fallback
    provider.load()
    assert provider._state.loaded  # type: ignore[attr-defined]
    assert not provider._state.stub  # type: ignore[attr-defined]
