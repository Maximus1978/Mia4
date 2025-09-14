"""Pipeline abstraction (ADR-0026) for model-specific generation flows.

Route now orchestrates via GenerationPipeline implementations rather than
embedding role-specific logic inline. This file defines lightweight
dataclasses and a Protocol contract; concrete pipelines live alongside.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable, Any


@dataclass
class PipelineSampling:
    requested_max_tokens: int | None = None
    effective_max_tokens: int | None = None
    cap_applied: bool = False
    cap_source: str | None = None
    merged: dict | None = None  # normalized sampling args passed to provider


@dataclass
class PipelineContext:
    request_id: str
    model_id: str
    provider: Any
    prompt: str
    sampling: PipelineSampling
    adapter: Any | None = None
    adapter_name: str | None = None
    fragments: list[str] = field(default_factory=list)
    reasoning_stats: dict | None = None
    reasoning_text: str | None = None
    stop_hit: str | None = None
    prompt_tokens: int = 0
    persona_len: int = 0
    system_prompt_version: int | None = None
    system_prompt_hash: str | None = None
    sampling_origin: str | None = None
    merged_sampling: dict | None = None
    # Convenience mirrors (transitional) for direct access
    # without drilling into nested sampling structure
    cap_applied: bool | None = None
    cap_source: str | None = None
    requested_max_tokens: int | None = None
    effective_max_tokens: int | None = None
    reasoning_mode: str | None = None
    # Runtime populated fields (post streaming)
    output_tokens: int = 0
    latency_ms: int | None = None
    decode_tps: float | None = None
    system_prompt_text: str | None = None  # for echo strip
    user_prompt: str | None = None  # original user prompt (pre framed)


@dataclass
class PipelineResult:
    final_text: str
    usage: dict
    reasoning_stats: dict | None
    sampling_summary: dict
    stop_reason: str | None


class GenerationPipeline(ABC):  # pragma: no cover - interface
    @abstractmethod
    def prepare(self, *args, **kwargs) -> PipelineContext:  # noqa: D401
        raise NotImplementedError

    @abstractmethod
    def stream(self, ctx: PipelineContext) -> Iterable[dict]:  # noqa: D401
        raise NotImplementedError

    @abstractmethod
    def finalize(self, ctx: PipelineContext) -> PipelineResult:  # noqa: D401
        raise NotImplementedError


__all__ = [
    "PipelineSampling",
    "PipelineContext",
    "PipelineResult",
    "GenerationPipeline",
    "GenerationPipeline",
]
