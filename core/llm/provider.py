"""ModelProvider interface definition and a DummyProvider for tests.

Adapters must not allocate heavy resources on import; call load() explicitly.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable, Dict, Any
from .types import GenerationResult


@dataclass(frozen=True)
class ModelInfo:
    id: str
    role: str
    capabilities: tuple[str, ...]
    context_length: int
    revision: str | None = None
    metadata: Dict[str, Any] | None = None


class ModelProvider(ABC):
    @abstractmethod
    def load(self) -> None:
        """Load underlying model weights/resources (idempotent)."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> GenerationResult:
        """Return GenerationResult for prompt."""

    @abstractmethod
    def stream(self, prompt: str, **kwargs: Any) -> Iterable[str]:
        """Yield incremental text chunks."""

    @abstractmethod
    def info(self) -> ModelInfo:
        """Return static model information."""

    def unload(self) -> None:  # optional hook
        """Release resources (default no-op)."""
        return None


class DummyProvider(ModelProvider):
    """Minimal echo provider used for wiring & tests."""

    def __init__(self, model_id: str = "dummy", role: str = "primary") -> None:
        self._loaded = False
        self._info = ModelInfo(
            id=model_id,
            role=role,
            capabilities=("chat",),
            context_length=128,
            revision=None,
            metadata={"provider": "dummy"},
        )

    def load(self) -> None:  # noqa: D401
        self._loaded = True

    def generate(
        self, prompt: str, **kwargs: Any
    ) -> GenerationResult:  # noqa: D401
        if not self._loaded:
            self.load()
        limit = int(kwargs.get("max_output_chars", 256))
        text = ("ECHO: " + prompt)[:limit]
        return GenerationResult.ok(
            text=text,
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(text.split()),
            total_ms=0,
            model_id=self._info.id,
            role=self._info.role,
            request_id="dummy",
        )

    def stream(self, prompt: str, **kwargs: Any):  # noqa: D401
        res = self.generate(prompt, **kwargs)
        for part in res.text.split():
            yield part + " "

    def info(self) -> ModelInfo:  # noqa: D401
        return self._info
