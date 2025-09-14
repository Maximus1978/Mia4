"""ModelProvider interface (no built-in dummy implementation).

All providers must implement the full contract; test suites now use real
lightweight model manifests (phi-mini, etc.) instead of a dummy stub.
Adapters must not allocate heavy resources on import; call load() explicitly.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable, Dict, Any
from .types import GenerationResult
# No direct event imports needed at interface level.


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
    
    # No dummy implementation.
